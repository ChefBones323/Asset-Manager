import uuid
from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse

from app.social_platform.domains.social.feed_explain_service import FeedExplainService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/feed_explain")
async def feed_explain(
    user_id: str = Query(..., description="User UUID"),
    content_id: str = Query(..., description="Content UUID"),
    policy_scope: Optional[str] = Query(None, description="Policy scope filter"),
):
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        return {"error": "Invalid user_id format"}
    try:
        cid = uuid.UUID(content_id)
    except ValueError:
        return {"error": "Invalid content_id format"}

    service = FeedExplainService()
    return service.explain(uid, cid, policy_scope=policy_scope)


@router.get("/feed_debugger", response_class=HTMLResponse)
async def feed_debugger_ui():
    return _FEED_DEBUGGER_HTML


_FEED_DEBUGGER_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Feed Debugger</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
:root{--bg:#0f1117;--surface:#1a1d27;--border:#2a2d3a;--text:#e4e4e7;--muted:#71717a;--accent:#6366f1;--accent-hover:#818cf8;--green:#22c55e;--red:#ef4444;--yellow:#eab308;--blue:#3b82f6;--mono:"JetBrains Mono","Fira Code",monospace}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:var(--bg);color:var(--text);min-height:100vh}
header{background:var(--surface);border-bottom:1px solid var(--border);padding:16px 24px}
header h1{font-size:18px;font-weight:600}
.form-section{background:var(--surface);border-bottom:1px solid var(--border);padding:16px 24px;display:flex;gap:12px;align-items:flex-end;flex-wrap:wrap}
.field{display:flex;flex-direction:column;gap:4px}
.field label{font-size:11px;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);font-weight:600}
.field input{background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:8px 12px;color:var(--text);font-size:13px;min-width:200px;outline:none}
.field input:focus{border-color:var(--accent)}
button{background:var(--accent);color:#fff;border:none;border-radius:6px;padding:8px 16px;font-size:13px;font-weight:500;cursor:pointer}
button:hover{background:var(--accent-hover)}
.result{padding:24px;max-width:900px}
.error-msg{color:var(--red);padding:24px;font-size:14px}
.card{background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:20px;margin-bottom:16px}
.card h2{font-size:15px;font-weight:600;margin-bottom:12px;color:var(--accent)}
.rank-badge{display:inline-flex;align-items:center;justify-content:center;width:48px;height:48px;border-radius:50%;background:var(--accent);color:#fff;font-size:20px;font-weight:700;margin-right:16px}
.rank-row{display:flex;align-items:center;margin-bottom:16px}
.rank-info{font-size:14px}
.rank-info .score{font-family:var(--mono);font-size:18px;font-weight:600;color:var(--green)}
.bar-chart{margin-top:12px}
.bar-row{display:flex;align-items:center;margin-bottom:8px;gap:12px}
.bar-label{width:140px;font-size:12px;color:var(--muted);text-align:right;font-family:var(--mono)}
.bar-track{flex:1;height:24px;background:var(--bg);border-radius:4px;overflow:hidden;position:relative}
.bar-fill{height:100%;border-radius:4px;transition:width .5s ease}
.bar-fill.ts{background:var(--blue)}
.bar-fill.react{background:var(--green)}
.bar-fill.trust{background:var(--yellow)}
.bar-fill.policy{background:var(--accent)}
.bar-value{width:60px;font-family:var(--mono);font-size:12px;color:var(--text)}
.kv-grid{display:grid;grid-template-columns:160px 1fr;gap:6px 16px;font-size:13px}
.kv-grid .k{color:var(--muted);font-family:var(--mono)}
.kv-grid .v{color:var(--text);font-family:var(--mono)}
.loading{padding:24px;color:var(--muted);font-size:14px}
</style>
</head>
<body>
<header><h1>Feed Debugger</h1></header>
<div class="form-section">
  <div class="field">
    <label>User ID</label>
    <input type="text" id="input-user-id" data-testid="input-user-id" placeholder="UUID" />
  </div>
  <div class="field">
    <label>Content ID</label>
    <input type="text" id="input-content-id" data-testid="input-content-id" placeholder="UUID" />
  </div>
  <div class="field">
    <label>Policy Scope</label>
    <input type="text" id="input-policy-scope" data-testid="input-policy-scope" placeholder="optional" />
  </div>
  <button data-testid="btn-explain" onclick="runExplain()">Explain Ranking</button>
</div>
<div id="result" data-testid="result-container"></div>
<script>
async function runExplain() {
  const userId = document.getElementById('input-user-id').value.trim();
  const contentId = document.getElementById('input-content-id').value.trim();
  const policyScope = document.getElementById('input-policy-scope').value.trim();
  const container = document.getElementById('result');
  if (!userId || !contentId) { container.innerHTML = '<div class="error-msg">User ID and Content ID are required.</div>'; return; }
  container.innerHTML = '<div class="loading">Computing ranking explanation...</div>';
  const params = new URLSearchParams({user_id: userId, content_id: contentId});
  if (policyScope) params.set('policy_scope', policyScope);
  try {
    const res = await fetch('/admin/feed_explain?' + params);
    const data = await res.json();
    if (data.error) { container.innerHTML = '<div class="error-msg">' + data.error + '</div>'; return; }
    renderExplanation(data);
  } catch(err) {
    container.innerHTML = '<div class="error-msg">Request failed: ' + err.message + '</div>';
  }
}

function renderExplanation(d) {
  const container = document.getElementById('result');
  const bd = d.score_breakdown || {};
  const maxWeight = Math.max(bd.timestamp_weight||0, bd.reaction_weight||0, bd.trust_weight||0, bd.policy_weight||0, 0.01);
  const pct = v => Math.round((v / maxWeight) * 100);
  const raw = d.raw_inputs || {};
  const weights = d.weights_used || {};
  const components = d.score_components || {};

  container.innerHTML = '<div class="result">' +
    '<div class="card">' +
      '<div class="rank-row">' +
        '<div class="rank-badge" data-testid="text-rank-position">' + d.rank_position + '</div>' +
        '<div class="rank-info">' +
          '<div>Rank <strong>#' + d.rank_position + '</strong> of ' + d.total_entries + ' entries</div>' +
          '<div class="score" data-testid="text-final-score">Score: ' + d.final_score + '</div>' +
        '</div>' +
      '</div>' +
    '</div>' +

    '<div class="card">' +
      '<h2>Weight Contributions</h2>' +
      '<div class="bar-chart">' +
        barRow('Timestamp', bd.timestamp_weight, pct(bd.timestamp_weight||0), 'ts') +
        barRow('Reactions', bd.reaction_weight, pct(bd.reaction_weight||0), 'react') +
        barRow('Trust', bd.trust_weight, pct(bd.trust_weight||0), 'trust') +
        barRow('Policy', bd.policy_weight, pct(bd.policy_weight||0), 'policy') +
      '</div>' +
    '</div>' +

    '<div class="card">' +
      '<h2>Score Components</h2>' +
      '<div class="kv-grid">' +
        kv('Timestamp Score', components.timestamp_score) +
        kv('Reaction Score', components.reaction_score) +
        kv('Trust Score', components.trust_score_component) +
        kv('Policy Score', components.policy_score) +
      '</div>' +
    '</div>' +

    '<div class="card">' +
      '<h2>Raw Inputs</h2>' +
      '<div class="kv-grid">' +
        kv('Timestamp', raw.timestamp) +
        kv('Reaction Count', raw.reaction_count) +
        kv('Trust Score', raw.trust_score) +
        kv('Policy Weight', raw.policy_weight) +
      '</div>' +
    '</div>' +

    '<div class="card">' +
      '<h2>Weights Used</h2>' +
      '<div class="kv-grid">' +
        kv('timestamp_weight', weights.timestamp_weight) +
        kv('reaction_weight', weights.reaction_weight) +
        kv('trust_weight', weights.trust_weight) +
        kv('policy_weight_factor', weights.policy_weight_factor) +
      '</div>' +
    '</div>' +

    '<div class="card">' +
      '<h2>Metadata</h2>' +
      '<div class="kv-grid">' +
        kv('Content ID', d.content_id) +
        kv('Policy Scope', d.policy_scope) +
        kv('Manifest ID', d.policy_manifest_id || 'none') +
        kv('Tie-break Rule', d.tie_break_rule) +
      '</div>' +
    '</div>' +
  '</div>';
}

function barRow(label, value, pct, cls) {
  const v = value !== undefined ? (value * 100).toFixed(1) + '%' : '0%';
  return '<div class="bar-row" data-testid="bar-' + cls + '">' +
    '<div class="bar-label">' + label + '</div>' +
    '<div class="bar-track"><div class="bar-fill ' + cls + '" style="width:' + pct + '%"></div></div>' +
    '<div class="bar-value">' + v + '</div>' +
  '</div>';
}

function kv(key, value) {
  return '<div class="k">' + key + '</div><div class="v">' + (value !== undefined && value !== null ? value : '-') + '</div>';
}
</script>
</body>
</html>"""
