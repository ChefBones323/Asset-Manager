import asyncio
import json
import uuid
import time
from datetime import datetime, timezone
from typing import Optional, AsyncGenerator

from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse, HTMLResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.social_platform.models.base import SessionLocal
from app.social_platform.models.event_models import Event

router = APIRouter(prefix="/admin", tags=["admin"])

RATE_LIMIT_PER_SECOND = 50
POLL_INTERVAL_SECONDS = 1.0


def _readonly_session() -> Session:
    session = SessionLocal()
    session.execute(text("SET TRANSACTION READ ONLY"))
    return session


def _query_events(
    session: Session,
    domain: Optional[str] = None,
    actor_id: Optional[uuid.UUID] = None,
    event_type: Optional[str] = None,
    after_timestamp: Optional[datetime] = None,
    after_event_id: Optional[uuid.UUID] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Event]:
    from sqlalchemy import or_, and_, tuple_

    query = session.query(Event)
    if domain:
        query = query.filter(Event.domain == domain)
    if actor_id:
        query = query.filter(Event.actor_id == actor_id)
    if event_type:
        query = query.filter(Event.event_type == event_type)
    if after_timestamp and after_event_id:
        query = query.filter(
            or_(
                Event.timestamp > after_timestamp,
                and_(
                    Event.timestamp == after_timestamp,
                    Event.event_id > after_event_id,
                ),
            )
        )
    elif after_timestamp:
        query = query.filter(Event.timestamp > after_timestamp)
    query = query.order_by(Event.timestamp.asc(), Event.event_id.asc())
    query = query.offset(offset).limit(limit)
    return query.all()


def _count_events(
    session: Session,
    domain: Optional[str] = None,
    actor_id: Optional[uuid.UUID] = None,
    event_type: Optional[str] = None,
) -> int:
    query = session.query(Event)
    if domain:
        query = query.filter(Event.domain == domain)
    if actor_id:
        query = query.filter(Event.actor_id == actor_id)
    if event_type:
        query = query.filter(Event.event_type == event_type)
    return query.count()


def _format_sse(data: dict, event_name: str = "event") -> str:
    payload = json.dumps(data, default=str)
    return f"event: {event_name}\ndata: {payload}\n\n"


async def _stream_events(
    domain: Optional[str],
    actor_id: Optional[uuid.UUID],
    event_type: Optional[str],
    request: Request,
) -> AsyncGenerator[str, None]:
    cursor_timestamp: Optional[datetime] = None
    cursor_event_id: Optional[uuid.UUID] = None

    yield _format_sse({"status": "connected", "filters": {
        "domain": domain,
        "actor_id": str(actor_id) if actor_id else None,
        "event_type": event_type,
    }}, "control")

    while True:
        if await request.is_disconnected():
            break

        session = _readonly_session()
        try:
            events = _query_events(
                session,
                domain=domain,
                actor_id=actor_id,
                event_type=event_type,
                after_timestamp=cursor_timestamp,
                after_event_id=cursor_event_id,
                limit=RATE_LIMIT_PER_SECOND,
            )

            if not events:
                yield _format_sse({"type": "heartbeat", "timestamp": datetime.now(timezone.utc).isoformat()}, "heartbeat")
                await asyncio.sleep(POLL_INTERVAL_SECONDS)
                continue

            batch: list[dict] = []
            for event in events:
                batch.append(event.to_dict())
                cursor_timestamp = event.timestamp
                cursor_event_id = event.event_id

            if len(batch) > RATE_LIMIT_PER_SECOND:
                yield _format_sse({
                    "type": "batch",
                    "count": len(batch),
                    "events": batch,
                }, "batch")
            else:
                for event_data in batch:
                    yield _format_sse(event_data, "event")

        finally:
            session.close()

        await asyncio.sleep(POLL_INTERVAL_SECONDS)


@router.get("/events")
async def stream_events(
    request: Request,
    domain: Optional[str] = Query(None, description="Filter by domain"),
    actor_id: Optional[str] = Query(None, description="Filter by actor UUID"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    stream: bool = Query(True, description="Enable SSE streaming"),
    limit: int = Query(50, ge=1, le=500, description="Page size for history mode"),
    offset: int = Query(0, ge=0, description="Offset for history mode"),
):
    parsed_actor_id = None
    if actor_id:
        try:
            parsed_actor_id = uuid.UUID(actor_id)
        except ValueError:
            return {"error": "Invalid actor_id format"}

    if stream:
        return StreamingResponse(
            _stream_events(domain, parsed_actor_id, event_type, request),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    session = _readonly_session()
    try:
        events = _query_events(
            session,
            domain=domain,
            actor_id=parsed_actor_id,
            event_type=event_type,
            limit=limit,
            offset=offset,
        )
        total = _count_events(session, domain, parsed_actor_id, event_type)
        return {
            "events": [e.to_dict() for e in events],
            "total": total,
            "limit": limit,
            "offset": offset,
            "filters": {
                "domain": domain,
                "actor_id": actor_id,
                "event_type": event_type,
            },
        }
    finally:
        session.close()


@router.get("/event_stream", response_class=HTMLResponse)
async def event_stream_ui():
    return _EVENT_STREAM_HTML


_EVENT_STREAM_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Event Stream Inspector</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
:root{--bg:#0f1117;--surface:#1a1d27;--border:#2a2d3a;--text:#e4e4e7;--muted:#71717a;--accent:#6366f1;--accent-hover:#818cf8;--green:#22c55e;--red:#ef4444;--yellow:#eab308;--blue:#3b82f6;--mono:"JetBrains Mono","Fira Code","Cascadia Code",monospace}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:var(--bg);color:var(--text);min-height:100vh;display:flex;flex-direction:column}
header{background:var(--surface);border-bottom:1px solid var(--border);padding:16px 24px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px}
header h1{font-size:18px;font-weight:600;display:flex;align-items:center;gap:8px}
header h1 .dot{width:8px;height:8px;border-radius:50%;background:var(--green);animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}
.dot.disconnected{background:var(--red);animation:none}
.dot.paused{background:var(--yellow);animation:none}
.controls{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.filters{background:var(--surface);border-bottom:1px solid var(--border);padding:12px 24px;display:flex;gap:12px;align-items:flex-end;flex-wrap:wrap}
.filter-group{display:flex;flex-direction:column;gap:4px}
.filter-group label{font-size:11px;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);font-weight:600}
.filter-group input,.filter-group select{background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:6px 10px;color:var(--text);font-size:13px;min-width:160px;outline:none;transition:border-color .2s}
.filter-group input:focus,.filter-group select:focus{border-color:var(--accent)}
button{background:var(--accent);color:#fff;border:none;border-radius:6px;padding:7px 14px;font-size:13px;font-weight:500;cursor:pointer;transition:background .2s}
button:hover{background:var(--accent-hover)}
button.secondary{background:var(--border);color:var(--text)}
button.secondary:hover{background:#3a3d4a}
button.danger{background:var(--red)}
button.danger:hover{background:#dc2626}
.toggle-group{display:flex;border:1px solid var(--border);border-radius:6px;overflow:hidden}
.toggle-group button{border-radius:0;border:none;padding:6px 14px;font-size:12px}
.toggle-group button.active{background:var(--accent)}
.toggle-group button:not(.active){background:var(--surface);color:var(--muted)}
.stats{background:var(--surface);border-bottom:1px solid var(--border);padding:8px 24px;display:flex;gap:24px;font-size:12px;color:var(--muted)}
.stats .stat{display:flex;align-items:center;gap:6px}
.stats .stat-value{color:var(--text);font-weight:600;font-family:var(--mono)}
main{flex:1;overflow:auto;padding:0}
#event-list{display:flex;flex-direction:column}
.event-card{border-bottom:1px solid var(--border);padding:12px 24px;display:grid;grid-template-columns:180px 100px 180px 1fr;gap:12px;align-items:start;transition:background .15s;font-size:13px}
.event-card:hover{background:var(--surface)}
.event-ts{font-family:var(--mono);font-size:11px;color:var(--muted);white-space:nowrap}
.event-domain{display:inline-block;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.3px}
.event-domain.platform{background:#3b82f620;color:var(--blue)}
.event-domain.content{background:#22c55e20;color:var(--green)}
.event-domain.trust{background:#eab30820;color:var(--yellow)}
.event-domain.governance{background:#ef444420;color:var(--red)}
.event-domain.feed{background:#6366f120;color:var(--accent)}
.event-domain.audit{background:#71717a20;color:var(--muted)}
.event-domain.lease{background:#f9731620;color:#f97316}
.event-domain.knowledge{background:#06b6d420;color:#06b6d4}
.event-type{font-weight:500;color:var(--text)}
.event-actor{font-family:var(--mono);font-size:11px;color:var(--muted)}
.event-payload-toggle{background:none;border:1px solid var(--border);color:var(--muted);padding:2px 8px;font-size:11px;border-radius:4px;cursor:pointer;margin-top:4px}
.event-payload-toggle:hover{color:var(--text);border-color:var(--accent)}
.event-payload{display:none;grid-column:1/-1;margin-top:4px;padding:12px;background:var(--bg);border-radius:6px;border:1px solid var(--border);font-family:var(--mono);font-size:12px;line-height:1.6;overflow-x:auto;white-space:pre-wrap;word-break:break-all}
.event-payload.open{display:block}
.json-key{color:#6366f1}.json-str{color:#22c55e}.json-num{color:#eab308}.json-bool{color:#ef4444}.json-null{color:#71717a}
.empty-state{display:flex;flex-direction:column;align-items:center;justify-content:center;padding:80px 24px;color:var(--muted)}
.empty-state svg{width:48px;height:48px;margin-bottom:16px;opacity:.5}
.pagination{display:flex;align-items:center;gap:12px;padding:16px 24px;border-top:1px solid var(--border);background:var(--surface);justify-content:center}
.pagination button{min-width:80px}
.pagination .page-info{font-size:13px;color:var(--muted);font-family:var(--mono)}
</style>
</head>
<body>
<header>
  <h1><span class="dot" id="status-dot" data-testid="status-dot"></span> Event Stream Inspector</h1>
  <div class="controls">
    <div class="toggle-group" data-testid="mode-toggle">
      <button class="active" id="btn-stream-mode" data-testid="btn-stream-mode" onclick="setMode('stream')">Stream</button>
      <button id="btn-history-mode" data-testid="btn-history-mode" onclick="setMode('history')">History</button>
    </div>
    <button id="btn-pause" data-testid="btn-pause" onclick="togglePause()">Pause Stream</button>
    <button class="secondary" data-testid="btn-clear" onclick="clearEvents()">Clear</button>
  </div>
</header>
<div class="filters">
  <div class="filter-group">
    <label>Domain</label>
    <input type="text" id="filter-domain" data-testid="input-domain" placeholder="e.g. content, trust" />
  </div>
  <div class="filter-group">
    <label>Actor ID</label>
    <input type="text" id="filter-actor" data-testid="input-actor-id" placeholder="UUID" />
  </div>
  <div class="filter-group">
    <label>Event Type</label>
    <input type="text" id="filter-event-type" data-testid="input-event-type" placeholder="e.g. content_created" />
  </div>
  <button data-testid="btn-apply-filters" onclick="applyFilters()">Apply</button>
  <button class="secondary" data-testid="btn-reset-filters" onclick="resetFilters()">Reset</button>
</div>
<div class="stats" id="stats-bar">
  <div class="stat">Events: <span class="stat-value" id="stat-count" data-testid="text-event-count">0</span></div>
  <div class="stat">Rate: <span class="stat-value" id="stat-rate" data-testid="text-event-rate">0</span>/s</div>
  <div class="stat">Status: <span class="stat-value" id="stat-status" data-testid="text-stream-status">Connecting</span></div>
</div>
<main>
  <div id="event-list" data-testid="event-list"></div>
  <div id="empty-state" class="empty-state" data-testid="text-empty-state">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M12 6v6l4 2M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z"/></svg>
    <p>Waiting for events...</p>
  </div>
  <div id="pagination" class="pagination" style="display:none" data-testid="pagination">
    <button class="secondary" id="btn-prev" data-testid="btn-prev" onclick="prevPage()" disabled>Previous</button>
    <span class="page-info" id="page-info" data-testid="text-page-info">Page 1</span>
    <button class="secondary" id="btn-next" data-testid="btn-next" onclick="nextPage()">Next</button>
  </div>
</main>
<script>
let mode = 'stream';
let paused = false;
let eventSource = null;
let events = [];
let eventCount = 0;
let rateWindow = [];
let historyOffset = 0;
const PAGE_SIZE = 50;

function getFilters() {
  return {
    domain: document.getElementById('filter-domain').value.trim() || null,
    actor_id: document.getElementById('filter-actor').value.trim() || null,
    event_type: document.getElementById('filter-event-type').value.trim() || null,
  };
}

function buildQueryString(extra) {
  const f = getFilters();
  const params = new URLSearchParams();
  if (f.domain) params.set('domain', f.domain);
  if (f.actor_id) params.set('actor_id', f.actor_id);
  if (f.event_type) params.set('event_type', f.event_type);
  if (extra) Object.entries(extra).forEach(([k,v]) => { if (v !== null && v !== undefined) params.set(k, v); });
  return params.toString();
}

function setMode(m) {
  mode = m;
  document.getElementById('btn-stream-mode').classList.toggle('active', m === 'stream');
  document.getElementById('btn-history-mode').classList.toggle('active', m === 'history');
  document.getElementById('btn-pause').style.display = m === 'stream' ? '' : 'none';
  document.getElementById('pagination').style.display = m === 'history' ? '' : 'none';
  if (m === 'stream') { startStream(); }
  else { stopStream(); loadHistory(); }
}

function togglePause() {
  paused = !paused;
  document.getElementById('btn-pause').textContent = paused ? 'Resume Stream' : 'Pause Stream';
  const dot = document.getElementById('status-dot');
  if (paused) { dot.classList.add('paused'); dot.classList.remove('disconnected'); }
  else { dot.classList.remove('paused'); }
  document.getElementById('stat-status').textContent = paused ? 'Paused' : 'Streaming';
}

function clearEvents() {
  events = [];
  eventCount = 0;
  renderEvents();
}

function applyFilters() {
  if (mode === 'stream') { startStream(); }
  else { historyOffset = 0; loadHistory(); }
}

function resetFilters() {
  document.getElementById('filter-domain').value = '';
  document.getElementById('filter-actor').value = '';
  document.getElementById('filter-event-type').value = '';
  applyFilters();
}

function startStream() {
  stopStream();
  events = [];
  eventCount = 0;
  renderEvents();
  const qs = buildQueryString({stream: 'true'});
  eventSource = new EventSource('/admin/events?' + qs);
  const dot = document.getElementById('status-dot');
  dot.classList.remove('disconnected', 'paused');
  document.getElementById('stat-status').textContent = 'Connecting';

  eventSource.addEventListener('control', function(e) {
    document.getElementById('stat-status').textContent = 'Streaming';
  });

  eventSource.addEventListener('event', function(e) {
    const data = JSON.parse(e.data);
    eventCount++;
    rateWindow.push(Date.now());
    if (!paused) { events.unshift(data); if (events.length > 500) events.length = 500; renderEvents(); }
    updateStats();
  });

  eventSource.addEventListener('batch', function(e) {
    const data = JSON.parse(e.data);
    const batchEvents = data.events || [];
    eventCount += batchEvents.length;
    for (let i = 0; i < batchEvents.length; i++) rateWindow.push(Date.now());
    if (!paused) { events.unshift(...batchEvents.reverse()); if (events.length > 500) events.length = 500; renderEvents(); }
    updateStats();
  });

  eventSource.addEventListener('heartbeat', function() {});

  eventSource.onerror = function() {
    dot.classList.add('disconnected');
    document.getElementById('stat-status').textContent = 'Disconnected';
  };
}

function stopStream() {
  if (eventSource) { eventSource.close(); eventSource = null; }
}

async function loadHistory() {
  const qs = buildQueryString({stream: 'false', limit: PAGE_SIZE, offset: historyOffset});
  try {
    const res = await fetch('/admin/events?' + qs);
    const data = await res.json();
    events = data.events || [];
    const total = data.total || 0;
    eventCount = total;
    renderEvents();
    document.getElementById('stat-status').textContent = 'History';
    document.getElementById('stat-count').textContent = total;
    const page = Math.floor(historyOffset / PAGE_SIZE) + 1;
    const totalPages = Math.ceil(total / PAGE_SIZE) || 1;
    document.getElementById('page-info').textContent = 'Page ' + page + ' / ' + totalPages;
    document.getElementById('btn-prev').disabled = historyOffset === 0;
    document.getElementById('btn-next').disabled = historyOffset + PAGE_SIZE >= total;
  } catch (err) {
    document.getElementById('stat-status').textContent = 'Error';
  }
}

function prevPage() { historyOffset = Math.max(0, historyOffset - PAGE_SIZE); loadHistory(); }
function nextPage() { historyOffset += PAGE_SIZE; loadHistory(); }

function updateStats() {
  const now = Date.now();
  rateWindow = rateWindow.filter(t => now - t < 1000);
  document.getElementById('stat-count').textContent = eventCount;
  document.getElementById('stat-rate').textContent = rateWindow.length;
}

function syntaxHighlight(obj) {
  const str = JSON.stringify(obj, null, 2);
  if (!str) return '';
  return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/"([^"]+)"(?=\\s*:)/g, '<span class="json-key">"$1"</span>')
    .replace(/:\\s*"([^"]*)"/g, ': <span class="json-str">"$1"</span>')
    .replace(/:\\s*(\\d+\\.?\\d*)/g, ': <span class="json-num">$1</span>')
    .replace(/:\\s*(true|false)/g, ': <span class="json-bool">$1</span>')
    .replace(/:\\s*(null)/g, ': <span class="json-null">$1</span>');
}

function domainClass(d) {
  const known = ['platform','content','trust','governance','feed','audit','lease','knowledge'];
  return known.includes(d) ? d : '';
}

function renderEvents() {
  const list = document.getElementById('event-list');
  const empty = document.getElementById('empty-state');
  if (events.length === 0) { list.innerHTML = ''; empty.style.display = ''; return; }
  empty.style.display = 'none';
  const html = events.map((ev, i) => {
    const ts = ev.timestamp ? new Date(ev.timestamp).toISOString().replace('T',' ').replace('Z','') : '';
    const actorShort = ev.actor_id ? ev.actor_id.substring(0,8) : '';
    return '<div class="event-card" data-testid="card-event-' + i + '">' +
      '<span class="event-ts" data-testid="text-event-ts-' + i + '">' + ts + '</span>' +
      '<span class="event-domain ' + domainClass(ev.domain) + '" data-testid="text-event-domain-' + i + '">' + (ev.domain||'') + '</span>' +
      '<span class="event-type" data-testid="text-event-type-' + i + '">' + (ev.event_type||'') + '</span>' +
      '<div><span class="event-actor" data-testid="text-event-actor-' + i + '">' + actorShort + '...</span>' +
      '<button class="event-payload-toggle" data-testid="btn-toggle-payload-' + i + '" onclick="togglePayload(' + i + ')">payload</button>' +
      '</div>' +
      '<div class="event-payload" id="payload-' + i + '" data-testid="text-event-payload-' + i + '">' + syntaxHighlight(ev.payload) + '</div>' +
      '</div>';
  }).join('');
  list.innerHTML = html;
}

function togglePayload(i) {
  const el = document.getElementById('payload-' + i);
  if (el) el.classList.toggle('open');
}

setInterval(updateStats, 1000);
startStream();
</script>
</body>
</html>"""
