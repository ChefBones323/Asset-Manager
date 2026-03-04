#!/usr/bin/env python3
"""
Manifest-Driven Execution Engine for Cognitive Control Plane.

This worker:
1. Polls the server for approved jobs
2. Validates the executable manifest (version, steps)
3. Enforces a strict command whitelist
4. Executes each step with rollback support
5. Maintains heartbeat and lease renewal
"""

import os
import sys
import time
import json
import shlex
import signal
import subprocess
import threading
import requests

API_BASE = os.environ.get("API_BASE", "http://localhost:5000")
WORKER_TOKEN = os.environ.get("WORKER_TOKEN", "")
WORKER_ID = os.environ.get("WORKER_ID", f"worker-{os.getpid()}")
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "5"))
HEARTBEAT_INTERVAL = 10
LEASE_SAFETY_MARGIN = 5

SAFE_COMMANDS = {"echo", "ls", "mkdir", "cat", "touch", "python3", "node"}

BLOCKED_PATTERNS = [
    "rm", "sudo", "chmod", "chown",
    ">", ">>", "&&", "||", ";",
    "`", "$(", "curl", "wget", "scp", "ssh",
]

shutdown_requested = False


def signal_handler(sig, frame):
    global shutdown_requested
    print("[WORKER] Shutdown signal received.")
    shutdown_requested = True


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def headers():
    return {
        "Authorization": f"Bearer {WORKER_TOKEN}",
        "Content-Type": "application/json",
        "X-Worker-Id": WORKER_ID,
    }


def send_update(job_id, logs, status=None):
    payload = {"id": job_id, "logs": logs, "workerId": WORKER_ID}
    if status:
        payload["status"] = status
    try:
        resp = requests.post(f"{API_BASE}/api/worker/update", json=payload, headers=headers(), timeout=10)
        return resp.json()
    except Exception as e:
        print(f"[WORKER] Failed to send update: {e}")
        return None


def send_heartbeat(job_id):
    try:
        resp = requests.post(
            f"{API_BASE}/api/worker/heartbeat",
            json={"jobId": job_id, "workerId": WORKER_ID},
            headers=headers(),
            timeout=10,
        )
        if resp.status_code == 200:
            return True
        else:
            print(f"[WORKER] Heartbeat rejected: {resp.status_code} {resp.text}")
            return False
    except Exception as e:
        print(f"[WORKER] Heartbeat failed: {e}")
        return False


def poll_next_job():
    try:
        resp = requests.get(f"{API_BASE}/api/worker/next", headers=headers(), timeout=10)
        if resp.status_code != 200:
            return None
        data = resp.json()
        if data.get("job") is None and "id" not in data:
            return None
        if "id" in data:
            return data
        return data.get("job")
    except Exception as e:
        print(f"[WORKER] Poll error: {e}")
        return None


def validate_manifest(manifest):
    if not manifest:
        return False, "Executable manifest is missing"
    if not isinstance(manifest, dict):
        return False, "Manifest is not a valid object"
    if manifest.get("version") != 1:
        return False, f"Unsupported manifest version: {manifest.get('version')}"
    steps = manifest.get("steps")
    if not steps or not isinstance(steps, list):
        return False, "Manifest steps array is missing or empty"
    return True, None


def check_command_safety(command):
    for pattern in BLOCKED_PATTERNS:
        if pattern in command:
            return False, f"Blocked pattern detected: '{pattern}'"

    try:
        tokens = shlex.split(command)
    except ValueError:
        return False, "Failed to parse command"

    if not tokens:
        return False, "Empty command"

    base_cmd = os.path.basename(tokens[0])
    if base_cmd not in SAFE_COMMANDS:
        return False, f"Command '{base_cmd}' is not in the safe whitelist"

    if base_cmd in ("python3", "node") and len(tokens) > 2:
        return False, f"Only single-script execution allowed for {base_cmd}"

    return True, None


def execute_command(command, timeout=60):
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except Exception as e:
        return -1, "", str(e)


def track_created_files(command):
    created = []
    try:
        tokens = shlex.split(command)
    except ValueError:
        return created

    base_cmd = os.path.basename(tokens[0]) if tokens else ""

    if base_cmd == "mkdir" and len(tokens) > 1:
        for t in tokens[1:]:
            if not t.startswith("-"):
                created.append(t)
    elif base_cmd == "touch" and len(tokens) > 1:
        for t in tokens[1:]:
            if not t.startswith("-"):
                created.append(t)

    return created


def attempt_rollback(created_files, job_id):
    logs = []
    for f in created_files:
        try:
            if os.path.isfile(f):
                os.remove(f)
                logs.append(f"[ROLLBACK] Removed file: {f}")
            elif os.path.isdir(f):
                os.rmdir(f)
                logs.append(f"[ROLLBACK] Removed directory: {f}")
            else:
                logs.append(f"[ROLLBACK] Not found, skipping: {f}")
        except Exception as e:
            logs.append(f"[ROLLBACK] Failed to remove {f}: {e}")
    return "\n".join(logs)


def run_job(job):
    job_id = job["id"]
    manifest = job.get("executableManifest")

    valid, reason = validate_manifest(manifest)
    if not valid:
        send_update(job_id, f"[MANIFEST ERROR] {reason}", "Escalated")
        print(f"[WORKER] Job {job_id} escalated: {reason}")
        return

    steps = manifest["steps"]
    requires_rollback = manifest.get("requiresRollback", False)
    all_created_files = []

    heartbeat_active = True

    def heartbeat_loop():
        while heartbeat_active and not shutdown_requested:
            time.sleep(HEARTBEAT_INTERVAL)
            if heartbeat_active and not shutdown_requested:
                ok = send_heartbeat(job_id)
                if not ok:
                    print(f"[WORKER] Heartbeat rejected for {job_id}, stopping heartbeat.")
                    break

    hb_thread = threading.Thread(target=heartbeat_loop, daemon=True)
    hb_thread.start()

    try:
        for step in steps:
            if shutdown_requested:
                send_update(job_id, "[WORKER] Shutdown requested, pausing execution.", "Escalated")
                return

            step_id = step.get("id", "unknown")
            step_type = step.get("type", "unknown")
            command = step.get("command", "")

            if step_type != "shell":
                send_update(job_id, f"[STEP {step_id}] Unsupported step type: {step_type}", "Escalated")
                return

            safe, block_reason = check_command_safety(command)
            if not safe:
                send_update(
                    job_id,
                    f"[STEP {step_id}] BLOCKED: {block_reason}\nCommand: {command}",
                    "Escalated",
                )
                print(f"[WORKER] Job {job_id} step {step_id} blocked: {block_reason}")
                return

            send_update(job_id, f"[STEP {step_id}] Starting: {command}")

            created = track_created_files(command)
            all_created_files.extend(created)

            returncode, stdout, stderr = execute_command(command)

            if returncode == 0:
                output_log = f"[STEP {step_id}] Completed (exit 0)"
                if stdout.strip():
                    output_log += f"\n[STDOUT] {stdout.strip()}"
                send_update(job_id, output_log)
            else:
                error_log = f"[STEP {step_id}] Failed (exit {returncode})"
                if stderr.strip():
                    error_log += f"\n[STDERR] {stderr.strip()}"
                if stdout.strip():
                    error_log += f"\n[STDOUT] {stdout.strip()}"

                if requires_rollback and all_created_files:
                    rollback_log = attempt_rollback(all_created_files, job_id)
                    error_log += f"\n{rollback_log}"

                send_update(job_id, error_log, "Failed")
                print(f"[WORKER] Job {job_id} step {step_id} failed")
                return

        send_update(job_id, "[MANIFEST] All steps completed successfully.", "Completed")
        print(f"[WORKER] Job {job_id} completed successfully")

    finally:
        heartbeat_active = False


def main():
    if not WORKER_TOKEN:
        print("[WORKER] ERROR: WORKER_TOKEN environment variable is required")
        sys.exit(1)

    print(f"[WORKER] Starting manifest-driven execution engine")
    print(f"[WORKER] ID: {WORKER_ID}")
    print(f"[WORKER] API: {API_BASE}")
    print(f"[WORKER] Poll interval: {POLL_INTERVAL}s")
    print(f"[WORKER] Heartbeat interval: {HEARTBEAT_INTERVAL}s")
    print(f"[WORKER] Safe commands: {', '.join(sorted(SAFE_COMMANDS))}")

    while not shutdown_requested:
        job = poll_next_job()
        if job:
            print(f"[WORKER] Picked up job: {job['id']}")
            run_job(job)
        else:
            time.sleep(POLL_INTERVAL)

    print("[WORKER] Shutting down gracefully.")


if __name__ == "__main__":
    main()
