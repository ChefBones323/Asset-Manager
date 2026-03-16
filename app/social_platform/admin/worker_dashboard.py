import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from sqlalchemy import text

from app.social_platform.models.base import SessionLocal
from app.social_platform.models.event_models import Event

router = APIRouter(prefix="/admin", tags=["admin"])


def _readonly_session():
    session = SessionLocal()
    session.execute(text("SET TRANSACTION READ ONLY"))
    return session


def _get_worker_data() -> dict:
    session = _readonly_session()
    try:
        lease_events = (
            session.query(Event)
            .filter(Event.domain == "lease")
            .order_by(Event.timestamp.asc())
            .all()
        )

        leases = {}
        heartbeats = {}
        retry_counts = {}
        dead_letter_jobs = []
        workers = {}

        for event in lease_events:
            payload = event.payload or {}
            job_id = payload.get("job_id", "")
            worker_id = payload.get("worker_id", "")
            etype = event.event_type

            if etype == "lease_acquired":
                leases[job_id] = {
                    "lease_id": payload.get("lease_id"),
                    "job_id": job_id,
                    "worker_id": worker_id,
                    "acquired_at": payload.get("acquired_at"),
                    "expires_at": payload.get("expires_at"),
                    "released": False,
                    "recovered": False,
                }
                if worker_id:
                    workers.setdefault(worker_id, {
                        "worker_id": worker_id,
                        "first_seen": event.timestamp.isoformat() if event.timestamp else None,
                        "jobs_processed": 0,
                        "status": "active",
                    })
                    workers[worker_id]["jobs_processed"] += 1
                    workers[worker_id]["last_seen"] = event.timestamp.isoformat() if event.timestamp else None

            elif etype == "lease_released":
                if job_id in leases:
                    leases[job_id]["released"] = True

            elif etype == "lease_recovered":
                if job_id in leases:
                    leases[job_id]["recovered"] = True
                    leases[job_id]["released"] = True

            elif etype == "heartbeat_received":
                ts = payload.get("timestamp", event.timestamp.isoformat() if event.timestamp else None)
                heartbeats[job_id] = {
                    "job_id": job_id,
                    "worker_id": worker_id,
                    "timestamp": ts,
                }
                if worker_id in workers:
                    workers[worker_id]["last_heartbeat"] = ts
                    workers[worker_id]["last_seen"] = ts

            elif etype == "job_requeued":
                count = payload.get("retry_count", 0)
                retry_counts[job_id] = count

            elif etype == "job_dead_lettered":
                dead_letter_jobs.append({
                    "job_id": job_id,
                    "retry_count": payload.get("retry_count", 0),
                    "reason": payload.get("reason", "unknown"),
                    "timestamp": event.timestamp.isoformat() if event.timestamp else None,
                })

        now = datetime.now(timezone.utc)
        active_leases = []
        stale_leases = []
        for job_id, lease in leases.items():
            if lease["released"]:
                continue
            expires_str = lease.get("expires_at", "")
            try:
                expires_at = datetime.fromisoformat(expires_str)
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
                if now > expires_at:
                    stale_leases.append(lease)
                else:
                    active_leases.append(lease)
            except (ValueError, TypeError):
                stale_leases.append(lease)

        for wid, w in workers.items():
            has_active = any(l["worker_id"] == wid for l in active_leases)
            if has_active:
                w["status"] = "active"
            else:
                w["status"] = "idle"
        # Update worker status from registry and queue depth from job queue
        queue_depth = {}
        queue_stats = {}
        try:
            from app.social_platform.workers.worker_registry import (
                WorkerRegistry,
            )
            registry = WorkerRegistry()
            registry.sweep_unhealthy()
            for r in registry.list_workers():
                wid = str(r.get("id") or r.get("worker_id"))
                w = workers.setdefault(wid, {"worker_id": wid, "jobs_processed": 0, "status": "idle"})
                w["status"] = r.get("status", w.get("status", "idle"))
                if r.get("last_heartbeat"):
                    w["last_heartbeat"] = r.get("last_heartbeat")
                    w["last_seen"] = r.get("last_heartbeat")
        except Exception:
            pass

        try:
            from app.social_platform.queue.job_queue_service import (
                JobQueueService,
            )
            queue_service = JobQueueService()
            queue_depth = queue_service.get_queue_depth()
            queue_stats = queue_service.get_stats()
            dead_letter_jobs[:] = queue_service.list_dlq(limit=50)
        except Exception:
            pass

        return {
            "workers": list(workers.values()),
            "active_leases": active_leases,
            "stale_leases": stale_leases,
            "heartbeats": list(heartbeats.values()),
            "retry_counts": retry_counts,
            "dead_letter_queue": dead_letter_jobs,
            "total_leases": len(leases),
            "computed_at": now.isoformat(),
            "queue_depth": queue_depth,
            "queue_stats": queue_stats,
        }
    finally:
        session.close()


@router.get("/workers/legacy")
async def worker_health():
    return _get_worker_data()


@router.get("/worker_dashboard", response_class=HTMLResponse)
async def worker_dashboard_ui():
    return _WORKER_DASHBOARD_HTML


_WORKER_DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Worker Health Dashboard</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
:root{--bg:#0f1117;--surface:#1a1d27;--border:#2a2d3a;--text:#e4e4e7;--muted:#71717a;--accent:#6366f1;--green:#22c55e;--red:#ef4444;--yellow:#eab308;--blue:#3b82f6;--mono:"JetBrains Mono","Fira Code",monospace}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:var(--bg);color:var(--text);min-height:100vh}
header{background:var(--surface);border-bottom:1px solid var(--border);padding:16px 24px;display:flex;align-items:center;justify-content:space-between}
header h1{font-size:18px;font-weight:600;display:flex;align-items:center;gap:8px}
header h1 .dot{width:8px;height:8px;border-radius:50%;background:var(--green);animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}
.summary{display:flex;gap:16px;padding:16px 24px;flex-wrap:wrap}
.summary-card{background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:16px 20px;min-width:140px}
.summary-card .label{font-size:11px;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);font-weight:600;margin-bottom:4px}
.summary-card .value{font-size:24px;font-weight:700;font-family:var(--mono)}
.summary-card .value.green{color:var(--green)}
.summary-card .value.yellow{color:var(--yellow)}
.summary-card .value.red{color:var(--red)}
.section{padding:0 24px 24px}
.section h2{font-size:15px;font-weight:600;margin-bottom:12px;color:var(--accent)}
table{width:100%;border-collapse:collapse;background:var(--surface);border:1px solid var(--border);border-radius:8px;overflow:hidden;font-size:13px}
thead{background:#1f2230}
th{text-align:left;padding:10px 12px;font-size:11px;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);font-weight:600;border-bottom:1px solid var(--border)}
td{padding:8px 12px;border-bottom:1px solid var(--border);font-family:var(--mono);font-size:12px}
tr:last-child td{border-bottom:none}
.status-badge{display:inline-block;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600}
.status-badge.active{background:#22c55e20;color:var(--green)}
.status-badge.idle{background:#71717a20;color:var(--muted)}
.status-badge.stale{background:#ef444420;color:var(--red)}
.status-badge.dead{background:#ef444440;color:var(--red)}
.refresh-info{font-size:12px;color:var(--muted)}
.empty{color:var(--muted);padding:16px;text-align:center}
</style>
</head>
<body>
<header>
  <h1><span class="dot" data-testid="status-dot"></span> Worker Health Dashboard</h1>
  <span class="refresh-info" data-testid="text-refresh-info">Auto-refresh: 5s</span>
</header>
<div class="summary" id="summary" data-testid="summary-cards"></div>
<div class="section">
  <h2>Workers</h2>
  <div id="workers-table" data-testid="table-workers"></div>
</div>
<div class="section">
  <h2>Active Leases</h2>
  <div id="leases-table" data-testid="table-leases"></div>
</div>
<div class="section">
  <h2>Heartbeats</h2>
  <div id="heartbeats-table" data-testid="table-heartbeats"></div>
</div>
<div class="section">
  <h2>Stale Leases</h2>
  <div id="stale-table" data-testid="table-stale"></div>
</div>
<div class="section">
  <h2>Dead-Letter Queue</h2>
  <div id="deadletter-table" data-testid="table-deadletter"></div>
</div>
<script>
async function refresh() {
  try {
    const res = await fetch('/admin/workers/legacy');
    const d = await res.json();
    renderSummary(d);
    renderWorkers(d.workers || []);
    renderLeases(d.active_leases || []);
    renderHeartbeats(d.heartbeats || []);
    renderStale(d.stale_leases || []);
    renderDeadLetter(d.dead_letter_queue || []);
  } catch(e) {}
}

function renderSummary(d) {
  const el = document.getElementById('summary');
  const wc = (d.workers||[]).length;
  const ac = (d.active_leases||[]).length;
  const sc = (d.stale_leases||[]).length;
  const dlc = (d.dead_letter_queue||[]).length;
  const rc = Object.values(d.retry_counts||{}).reduce((a,b)=>a+b,0);
  el.innerHTML =
    summaryCard('Workers', wc, 'green') +
    summaryCard('Active Leases', ac, ac > 0 ? 'green' : 'yellow') +
    summaryCard('Stale Leases', sc, sc > 0 ? 'red' : 'green') +
    summaryCard('Total Retries', rc, rc > 0 ? 'yellow' : 'green') +
    summaryCard('Dead Letters', dlc, dlc > 0 ? 'red' : 'green');
}

function summaryCard(label, value, color) {
  return '<div class="summary-card" data-testid="card-' + label.toLowerCase().replace(/\\s+/g,'-') + '"><div class="label">' + label + '</div><div class="value ' + color + '">' + value + '</div></div>';
}

function renderWorkers(workers) {
  const el = document.getElementById('workers-table');
  if (!workers.length) { el.innerHTML = '<div class="empty">No workers registered</div>'; return; }
  let h = '<table><thead><tr><th>Worker ID</th><th>Status</th><th>Jobs</th><th>Last Heartbeat</th><th>Last Seen</th></tr></thead><tbody>';
  workers.forEach(w => {
    h += '<tr data-testid="row-worker-' + w.worker_id + '"><td>' + w.worker_id + '</td><td><span class="status-badge ' + w.status + '">' + w.status + '</span></td><td>' + w.jobs_processed + '</td><td>' + (w.last_heartbeat || '-') + '</td><td>' + (w.last_seen || '-') + '</td></tr>';
  });
  el.innerHTML = h + '</tbody></table>';
}

function renderLeases(leases) {
  const el = document.getElementById('leases-table');
  if (!leases.length) { el.innerHTML = '<div class="empty">No active leases</div>'; return; }
  let h = '<table><thead><tr><th>Job ID</th><th>Worker</th><th>Lease ID</th><th>Acquired</th><th>Expires</th></tr></thead><tbody>';
  leases.forEach(l => {
    h += '<tr data-testid="row-lease-' + l.job_id + '"><td>' + l.job_id + '</td><td>' + l.worker_id + '</td><td>' + (l.lease_id||'').substring(0,8) + '...</td><td>' + (l.acquired_at||'-') + '</td><td>' + (l.expires_at||'-') + '</td></tr>';
  });
  el.innerHTML = h + '</tbody></table>';
}

function renderHeartbeats(hbs) {
  const el = document.getElementById('heartbeats-table');
  if (!hbs.length) { el.innerHTML = '<div class="empty">No heartbeats recorded</div>'; return; }
  let h = '<table><thead><tr><th>Job ID</th><th>Worker</th><th>Last Heartbeat</th></tr></thead><tbody>';
  hbs.forEach(hb => {
    h += '<tr data-testid="row-heartbeat-' + hb.job_id + '"><td>' + hb.job_id + '</td><td>' + hb.worker_id + '</td><td>' + (hb.timestamp||'-') + '</td></tr>';
  });
  el.innerHTML = h + '</tbody></table>';
}

function renderStale(leases) {
  const el = document.getElementById('stale-table');
  if (!leases.length) { el.innerHTML = '<div class="empty">No stale leases detected</div>'; return; }
  let h = '<table><thead><tr><th>Job ID</th><th>Worker</th><th>Expired At</th></tr></thead><tbody>';
  leases.forEach(l => {
    h += '<tr data-testid="row-stale-' + l.job_id + '"><td>' + l.job_id + '</td><td>' + l.worker_id + '</td><td>' + (l.expires_at||'-') + '</td></tr>';
  });
  el.innerHTML = h + '</tbody></table>';
}

function renderDeadLetter(jobs) {
  const el = document.getElementById('deadletter-table');
  if (!jobs.length) { el.innerHTML = '<div class="empty">No dead-letter entries</div>'; return; }
  let h = '<table><thead><tr><th>Job ID</th><th>Retries</th><th>Reason</th><th>Timestamp</th></tr></thead><tbody>';
  jobs.forEach(j => {
    h += '<tr data-testid="row-deadletter-' + j.job_id + '"><td>' + j.job_id + '</td><td>' + j.retry_count + '</td><td>' + j.reason + '</td><td>' + (j.timestamp||'-') + '</td></tr>';
  });
  el.innerHTML = h + '</tbody></table>';
}

refresh();
setInterval(refresh, 5000);
</script>
</body>
</html>"""
