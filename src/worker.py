#!/usr/bin/env python3
"""
Manifest-Driven Execution Engine for Cognitive Control Plane.

Environment variables:
  WORKER_TOKEN    Bearer token for API auth (required)
  API_BASE        Backend base URL (default: http://localhost:5000)
  WORKER_ID       Identifier for this worker process (default: worker-<pid>)
  POLL_INTERVAL   Seconds between polls when idle (default: 5)
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
from datetime import datetime

API_BASE = os.environ.get("API_BASE", "http://localhost:5000")
WORKER_TOKEN = os.environ.get("WORKER_TOKEN", os.environ.get("API_TOKEN", ""))
WORKER_ID = os.environ.get("WORKER_ID", f"worker-{os.getpid()}")
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "5"))
HEARTBEAT_INTERVAL = 10
LEASE_SAFETY_MARGIN = 5

SAFE_COMMANDS = {"echo", "ls", "mkdir", "cat", "touch", "python3", "node"}

BLOCKED_PATTERNS = [
    "rm", "sudo", "chmod", "chown",
    ">>", "&&", "||", ";",
    "`", "$(", "curl", "wget", "scp", "ssh",
]

shutdown_requested = False


def signal_handler(sig, frame):
    global shutdown_requested
    log("Shutdown signal received.")
    shutdown_requested = True


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def log(msg: str) -> None:
    ts = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[{ts}] [WORKER] {msg}", flush=True)


def auth_headers() -> dict:
    return {
        "Authorization": f"Bearer {WORKER_TOKEN}",
        "Content-Type": "application/json",
        "X-Worker-Id": WORKER_ID,
    }


# ---------------------------------------------------------------------------
# Job normalization
# ---------------------------------------------------------------------------

def normalize_job(response_json) -> dict | None:
    """
    Accepts either:
      { "job": {...} }   — wrapped shape from /api/worker/next when no job
      { "id": "...", ... } — direct job object returned from /api/worker/next
      None / {} / { "job": null }

    Returns a normalized job dict with guaranteed keys:
      id, type, intent, payload, executableManifest, status
    or None if no valid job is available.
    """
    if not isinstance(response_json, dict):
        return None

    # Unwrap {"job": {...}} wrapper if present
    if "job" in response_json and "id" not in response_json:
        inner = response_json.get("job")
        if not inner:
            return None
        response_json = inner

    job = response_json

    if not isinstance(job, dict) or not job.get("id"):
        return None

    manifest = job.get("executableManifest") or {}

    # Resolve type with fallback chain
    job_type = (
        job.get("type")
        or job.get("intent")
        or manifest.get("jobType")
    )

    if not job_type:
        log(f"RAW JOB has no resolvable type: {json.dumps(job)}")
        return None

    # Resolve payload with fallback chain
    payload = job.get("payload") or manifest.get("payload") or {}

    # Inject normalized fields onto the job object
    job["type"] = job_type
    job["intent"] = job.get("intent") or job_type
    job["payload"] = payload
    job["executableManifest"] = manifest

    return job


# ---------------------------------------------------------------------------
# API calls
# ---------------------------------------------------------------------------

def fetch_job() -> dict | None:
    url = f"{API_BASE}/api/worker/next"
    log(f"Polling {url}")
    try:
        resp = requests.get(url, headers=auth_headers(), timeout=10)
        if resp.status_code != 200:
            log(f"Poll returned HTTP {resp.status_code}: {resp.text[:200]}")
            return None

        try:
            raw = resp.json()
        except ValueError:
            log(f"Malformed JSON response: {resp.text[:200]}")
            return None

        log(f"RAW JOB RESPONSE: {json.dumps(raw)}")

        job = normalize_job(raw)
        if not job:
            log("No valid job received")
            return None

        log(f"Normalized job id={job['id']} type={job['type']}")
        return job

    except requests.Timeout:
        log("Poll timed out")
        return None
    except requests.ConnectionError as e:
        log(f"Poll connection error: {e}")
        return None
    except Exception as e:
        log(f"Unexpected poll error: {e}")
        return None


def send_heartbeat(job_id: str) -> bool:
    try:
        resp = requests.post(
            f"{API_BASE}/api/worker/heartbeat",
            json={"jobId": job_id, "workerId": WORKER_ID},
            headers=auth_headers(),
            timeout=10,
        )
        return resp.status_code == 200
    except Exception as e:
        log(f"Heartbeat failed for {job_id}: {e}")
        return False


def report_complete(job_id: str, logs: str) -> None:
    try:
        resp = requests.post(
            f"{API_BASE}/api/worker/{job_id}/complete",
            json={"workerId": WORKER_ID, "logs": logs},
            headers=auth_headers(),
            timeout=10,
        )
        if resp.status_code == 200:
            log(f"Reported completion for {job_id}")
        else:
            log(f"Complete report failed HTTP {resp.status_code}: {resp.text[:200]}")
            # Fallback to legacy update endpoint
            _fallback_update(job_id, logs, "Completed")
    except Exception as e:
        log(f"Failed to report completion for {job_id}: {e}")
        _fallback_update(job_id, logs, "Completed")


def report_failed(job_id: str, error: str, logs: str) -> None:
    try:
        resp = requests.post(
            f"{API_BASE}/api/worker/{job_id}/fail",
            json={"workerId": WORKER_ID, "error": error, "logs": logs},
            headers=auth_headers(),
            timeout=10,
        )
        if resp.status_code == 200:
            log(f"Reported failure for {job_id}: {error}")
        else:
            log(f"Fail report HTTP {resp.status_code}: {resp.text[:200]}")
            _fallback_update(job_id, f"[FAILURE] {error}\n{logs}", "Failed")
    except Exception as e:
        log(f"Failed to report failure for {job_id}: {e}")
        _fallback_update(job_id, f"[FAILURE] {error}\n{logs}", "Failed")


def _fallback_update(job_id: str, logs: str, status: str | None = None) -> None:
    """Legacy update endpoint as fallback."""
    payload: dict = {"id": job_id, "logs": logs, "workerId": WORKER_ID}
    if status:
        payload["status"] = status
    try:
        requests.post(
            f"{API_BASE}/api/worker/update",
            json=payload,
            headers=auth_headers(),
            timeout=10,
        )
    except Exception as e:
        log(f"Fallback update also failed for {job_id}: {e}")


# ---------------------------------------------------------------------------
# Manifest execution
# ---------------------------------------------------------------------------

def check_command_safety(command: str) -> tuple[bool, str]:
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
        return False, f"Command '{base_cmd}' is not in the safe whitelist: {sorted(SAFE_COMMANDS)}"

    if base_cmd in ("python3", "node") and len(tokens) > 2:
        return False, f"Only single-script execution allowed for {base_cmd}"

    return True, ""


def execute_shell_step(step: dict) -> tuple[bool, str]:
    """Execute a shell step. Returns (success, log_output)."""
    step_id = step.get("id", "unknown")
    command = step.get("command", "")

    log(f"Executing step {step_id} [shell]: {command}")

    safe, block_reason = check_command_safety(command)
    if not safe:
        msg = f"[STEP {step_id}] BLOCKED: {block_reason}"
        log(msg)
        return False, msg

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        msg = f"[STEP {step_id}] Command timed out: {command}"
        log(msg)
        return False, msg
    except Exception as e:
        msg = f"[STEP {step_id}] Execution error: {e}"
        log(msg)
        return False, msg

    rc = result.returncode
    stdout = result.stdout.strip()
    stderr = result.stderr.strip()

    lines = [f"[STEP {step_id}] completed rc={rc}"]
    if stdout:
        lines.append(f"  stdout: {stdout}")
        log(f"Step {step_id} completed rc={rc} stdout={stdout}")
    else:
        log(f"Step {step_id} completed rc={rc}")
    if stderr:
        lines.append(f"  stderr: {stderr}")

    output = "\n".join(lines)

    if rc != 0:
        return False, output

    return True, output


def execute_manifest(manifest: dict) -> tuple[bool, str]:
    """
    Execute all steps in a manifest.
    Returns (success, accumulated_logs).
    """
    steps = manifest.get("steps") or []
    accumulated = []

    for step in steps:
        step_type = step.get("type", "unknown")

        if step_type == "shell":
            success, output = execute_shell_step(step)
            accumulated.append(output)
            if not success:
                return False, "\n".join(accumulated)

        elif step_type == "log":
            message = step.get("message", "")
            step_id = step.get("id", "unknown")
            entry = f"[STEP {step_id}] log: {message}"
            log(entry)
            accumulated.append(entry)

        else:
            step_id = step.get("id", "unknown")
            msg = f"[STEP {step_id}] Unsupported step type: {step_type}"
            log(msg)
            accumulated.append(msg)
            return False, "\n".join(accumulated)

    return True, "\n".join(accumulated)


# ---------------------------------------------------------------------------
# Job type dispatch (pre-execution hook for named job types)
# ---------------------------------------------------------------------------

def dispatch_by_type(job: dict) -> None:
    """Log type-specific context before manifest execution."""
    job_type = job.get("type", "unknown")
    payload = job.get("payload", {})

    if job_type == "test_job":
        message = payload.get("message", "(no message)")
        log(f"Running test job: {message}")

    elif job_type == "create_post":
        log(f"Simulating post creation: {json.dumps(payload)}")

    elif job_type == "send_notification":
        recipient = payload.get("recipient", "unknown")
        log(f"Simulating notification to: {recipient}")

    else:
        log(f"Job type '{job_type}' — executing manifest steps")


# ---------------------------------------------------------------------------
# Main job runner
# ---------------------------------------------------------------------------

def run_job(job: dict) -> None:
    job_id = job["id"]
    job_type = job.get("type", "unknown")

    log(f"Received job: {job_type} (id={job_id})")
    dispatch_by_type(job)

    manifest = job.get("executableManifest") or {}

    # Validate manifest
    if not manifest or manifest.get("version") != 1:
        reason = f"Invalid or missing manifest (version={manifest.get('version')})"
        log(f"Job {job_id} escalated: {reason}")
        report_failed(job_id, reason, f"[MANIFEST ERROR] {reason}")
        return

    steps = manifest.get("steps")
    if not steps or not isinstance(steps, list):
        reason = "Manifest steps array is missing or empty"
        log(f"Job {job_id} escalated: {reason}")
        report_failed(job_id, reason, f"[MANIFEST ERROR] {reason}")
        return

    # Start heartbeat thread
    heartbeat_active = True

    def heartbeat_loop():
        while heartbeat_active and not shutdown_requested:
            time.sleep(HEARTBEAT_INTERVAL)
            if heartbeat_active and not shutdown_requested:
                ok = send_heartbeat(job_id)
                if not ok:
                    log(f"Heartbeat rejected for {job_id}, stopping heartbeat")
                    break

    hb_thread = threading.Thread(target=heartbeat_loop, daemon=True)
    hb_thread.start()

    try:
        if shutdown_requested:
            report_failed(job_id, "Worker shutdown", "[WORKER] Shutdown before execution")
            return

        success, exec_logs = execute_manifest(manifest)

        if success:
            completion_log = f"[MANIFEST] All steps completed successfully. Job type: {job_type}\n{exec_logs}"
            report_complete(job_id, completion_log)
            log(f"Completed job: {job_type}")
        else:
            report_failed(job_id, "Step execution failed", exec_logs)
            log(f"Failed job: {job_type}")

    finally:
        heartbeat_active = False


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    if not WORKER_TOKEN:
        print("[WORKER] ERROR: WORKER_TOKEN environment variable is required", file=sys.stderr)
        sys.exit(1)

    log(f"Worker started")
    log(f"ID: {WORKER_ID}")
    log(f"API: {API_BASE}")
    log(f"Poll interval: {POLL_INTERVAL}s")
    log(f"Heartbeat interval: {HEARTBEAT_INTERVAL}s")
    log(f"Safe commands: {', '.join(sorted(SAFE_COMMANDS))}")

    while not shutdown_requested:
        try:
            job = fetch_job()
            if job:
                run_job(job)
            else:
                time.sleep(POLL_INTERVAL)
        except Exception as e:
            log(f"Unhandled error in main loop: {e}")
            time.sleep(POLL_INTERVAL)

    log("Shutting down gracefully.")


if __name__ == "__main__":
    main()
