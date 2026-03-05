import uuid

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from app.social_platform.policies.policy_registry import (
    get_global_registry,
    PolicyNotFoundError,
)
from app.social_platform.policies.policy_validator import validate_policy
from app.social_platform.infrastructure.event_store import EventStore
from app.social_platform.platform.execution_engine import ExecutionEngine
from app.social_platform.domains.social.governance_service import GovernanceService

router = APIRouter(prefix="/admin", tags=["admin"])


def _get_execution_engine() -> ExecutionEngine:
    event_store = EventStore()
    engine = ExecutionEngine(event_store)
    return engine


class CreatePolicyProposalRequest(BaseModel):
    actor_id: str
    policy_id: str
    timestamp_weight: float = 0.40
    reaction_weight: float = 0.25
    trust_weight: float = 0.20
    policy_weight: float = 0.15
    max_age_hours: int = 72
    min_trust_threshold: float = -20.0
    description: str = ""


@router.get("/feed_policies")
async def list_feed_policies():
    registry = get_global_registry()
    return {
        "policies": registry.list_policies(),
        "active_count": len(registry.list_active_policies()),
        "total_count": len(registry.list_policies()),
    }


@router.get("/feed_policies/{policy_id}")
async def get_feed_policy(policy_id: str):
    registry = get_global_registry()
    policy = registry.get_policy(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return policy


@router.post("/feed_policies/validate")
async def validate_feed_policy(request: CreatePolicyProposalRequest):
    policy_dict = {
        "policy_id": request.policy_id,
        "timestamp_weight": request.timestamp_weight,
        "reaction_weight": request.reaction_weight,
        "trust_weight": request.trust_weight,
        "policy_weight": request.policy_weight,
        "max_age_hours": request.max_age_hours,
        "min_trust_threshold": request.min_trust_threshold,
    }
    errors = validate_policy(policy_dict)
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "policy": policy_dict,
    }


@router.post("/feed_policies/propose")
async def propose_feed_policy(request: CreatePolicyProposalRequest):
    policy_dict = {
        "policy_id": request.policy_id,
        "timestamp_weight": request.timestamp_weight,
        "reaction_weight": request.reaction_weight,
        "trust_weight": request.trust_weight,
        "policy_weight": request.policy_weight,
        "max_age_hours": request.max_age_hours,
        "min_trust_threshold": request.min_trust_threshold,
        "description": request.description,
        "created_by": request.actor_id,
    }

    errors = validate_policy(policy_dict)
    if errors:
        raise HTTPException(status_code=400, detail={"errors": errors})

    try:
        actor_id = uuid.UUID(request.actor_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid actor_id format")

    engine = _get_execution_engine()
    gov = GovernanceService(engine)

    result = gov.create_governance_proposal(
        actor_id=actor_id,
        title=f"Feed policy proposal: {request.policy_id}",
        description=request.description or f"Create feed policy '{request.policy_id}'",
        proposal_type="create_feed_policy",
        domain="feed_policy",
        payload={"policy": policy_dict},
        quorum=1,
        approval_threshold=0.5,
    )

    return {"status": "proposed", "governance_proposal": result, "policy": policy_dict}


@router.post("/feed_policies/{policy_id}/approve")
async def approve_feed_policy(policy_id: str, actor_id: str = Query(...)):
    try:
        approver = uuid.UUID(actor_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid actor_id format")

    registry = get_global_registry()
    policy = registry.get_policy(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found in registry")

    engine = _get_execution_engine()
    gov = GovernanceService(engine)

    governance_proposal_id = policy.get("governance_proposal_id")
    if governance_proposal_id:
        gov.vote(
            actor_id=approver,
            proposal_id=uuid.UUID(governance_proposal_id),
            vote="for",
            weight=1.0,
            reason=f"Approve feed policy {policy_id}",
        )
        result = gov.execute_approved(
            proposal_id=uuid.UUID(governance_proposal_id),
            actor_id=approver,
        )
        return {"status": "approved_via_governance", "result": result}

    engine._event_store.append_event(
        domain="feed_policy",
        event_type="feed_policy_approved",
        actor_id=approver,
        payload={
            "policy_id": policy_id,
            "approved_by": str(approver),
        },
    )

    return {"status": "approved", "policy_id": policy_id}


@router.get("/feed_policies_ui", response_class=HTMLResponse)
async def feed_policies_ui():
    return _FEED_POLICIES_HTML


_FEED_POLICIES_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Feed Policies</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
:root{--bg:#0f1117;--surface:#1a1d27;--border:#2a2d3a;--text:#e4e4e7;--muted:#71717a;--accent:#6366f1;--accent-hover:#818cf8;--green:#22c55e;--red:#ef4444;--yellow:#eab308;--blue:#3b82f6;--mono:"JetBrains Mono","Fira Code",monospace}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:var(--bg);color:var(--text);min-height:100vh}
header{background:var(--surface);border-bottom:1px solid var(--border);padding:16px 24px;display:flex;align-items:center;justify-content:space-between}
header h1{font-size:18px;font-weight:600}
.content{padding:24px;max-width:1100px}
.section{margin-bottom:32px}
.section h2{font-size:15px;font-weight:600;color:var(--accent);margin-bottom:12px}
table{width:100%;border-collapse:collapse;background:var(--surface);border:1px solid var(--border);border-radius:8px;overflow:hidden;font-size:13px}
thead{background:#1f2230}
th{text-align:left;padding:10px 12px;font-size:11px;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);font-weight:600;border-bottom:1px solid var(--border)}
td{padding:8px 12px;border-bottom:1px solid var(--border);font-family:var(--mono);font-size:12px}
tr:last-child td{border-bottom:none}
.status-badge{display:inline-block;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600}
.status-badge.active{background:#22c55e20;color:var(--green)}
.status-badge.pending{background:#eab30820;color:var(--yellow)}
.weight-bar{display:flex;height:20px;border-radius:4px;overflow:hidden;margin:4px 0}
.weight-bar .seg{display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:600;color:#fff;min-width:20px}
.weight-bar .ts{background:var(--blue)}
.weight-bar .react{background:var(--green)}
.weight-bar .trust{background:var(--yellow)}
.weight-bar .pol{background:var(--accent)}
.form-section{background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:20px;margin-bottom:24px}
.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.field{display:flex;flex-direction:column;gap:4px}
.field label{font-size:11px;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);font-weight:600}
.field input{background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:8px 12px;color:var(--text);font-size:13px;outline:none;font-family:var(--mono)}
.field input:focus{border-color:var(--accent)}
button{background:var(--accent);color:#fff;border:none;border-radius:6px;padding:8px 16px;font-size:13px;font-weight:500;cursor:pointer}
button:hover{background:var(--accent-hover)}
button.secondary{background:var(--border);color:var(--text)}
button.approve-btn{background:var(--green);font-size:11px;padding:4px 10px}
.msg{padding:12px;border-radius:6px;margin-bottom:12px;font-size:13px}
.msg.error{background:#ef444420;color:var(--red);border:1px solid #ef444440}
.msg.success{background:#22c55e20;color:var(--green);border:1px solid #22c55e40}
.empty{color:var(--muted);padding:16px;text-align:center}
.summary{display:flex;gap:16px;margin-bottom:24px}
.summary-card{background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:16px 20px;min-width:120px}
.summary-card .label{font-size:11px;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);font-weight:600;margin-bottom:4px}
.summary-card .value{font-size:24px;font-weight:700;font-family:var(--mono);color:var(--green)}
</style>
</head>
<body>
<header>
  <h1>Feed Policies</h1>
  <button data-testid="btn-refresh" onclick="loadPolicies()">Refresh</button>
</header>
<div class="content">
  <div class="summary" id="summary" data-testid="summary-cards"></div>

  <div class="section">
    <h2>Create Policy Proposal</h2>
    <div class="form-section">
      <div id="form-msg" data-testid="form-message"></div>
      <div class="form-grid">
        <div class="field">
          <label>Policy ID</label>
          <input type="text" id="inp-policy-id" data-testid="input-policy-id" placeholder="community_default" />
        </div>
        <div class="field">
          <label>Actor ID (UUID)</label>
          <input type="text" id="inp-actor-id" data-testid="input-actor-id" placeholder="UUID" />
        </div>
        <div class="field">
          <label>Timestamp Weight</label>
          <input type="number" id="inp-ts-weight" data-testid="input-ts-weight" value="0.40" step="0.01" min="0" max="1" />
        </div>
        <div class="field">
          <label>Reaction Weight</label>
          <input type="number" id="inp-react-weight" data-testid="input-react-weight" value="0.25" step="0.01" min="0" max="1" />
        </div>
        <div class="field">
          <label>Trust Weight</label>
          <input type="number" id="inp-trust-weight" data-testid="input-trust-weight" value="0.20" step="0.01" min="0" max="1" />
        </div>
        <div class="field">
          <label>Policy Weight</label>
          <input type="number" id="inp-pol-weight" data-testid="input-pol-weight" value="0.15" step="0.01" min="0" max="1" />
        </div>
        <div class="field">
          <label>Max Age (hours)</label>
          <input type="number" id="inp-max-age" data-testid="input-max-age" value="72" min="1" />
        </div>
        <div class="field">
          <label>Min Trust Threshold</label>
          <input type="number" id="inp-min-trust" data-testid="input-min-trust" value="-20" step="1" />
        </div>
      </div>
      <div class="field" style="margin-top:12px">
        <label>Description</label>
        <input type="text" id="inp-description" data-testid="input-description" placeholder="Policy description" />
      </div>
      <div style="margin-top:16px;display:flex;gap:8px">
        <button data-testid="btn-validate" onclick="validatePolicy()">Validate</button>
        <button data-testid="btn-propose" onclick="proposePolicy()">Propose Policy</button>
      </div>
    </div>
  </div>

  <div class="section">
    <h2>Registered Policies</h2>
    <div id="policies-table" data-testid="table-policies"></div>
  </div>
</div>
<script>
function getFormData() {
  return {
    actor_id: document.getElementById('inp-actor-id').value.trim(),
    policy_id: document.getElementById('inp-policy-id').value.trim(),
    timestamp_weight: parseFloat(document.getElementById('inp-ts-weight').value),
    reaction_weight: parseFloat(document.getElementById('inp-react-weight').value),
    trust_weight: parseFloat(document.getElementById('inp-trust-weight').value),
    policy_weight: parseFloat(document.getElementById('inp-pol-weight').value),
    max_age_hours: parseInt(document.getElementById('inp-max-age').value),
    min_trust_threshold: parseFloat(document.getElementById('inp-min-trust').value),
    description: document.getElementById('inp-description').value.trim(),
  };
}

function showMsg(text, type) {
  const el = document.getElementById('form-msg');
  el.innerHTML = '<div class="msg ' + type + '">' + text + '</div>';
  setTimeout(() => el.innerHTML = '', 5000);
}

async function validatePolicy() {
  const data = getFormData();
  try {
    const res = await fetch('/admin/feed_policies/validate', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
    const result = await res.json();
    if (result.valid) showMsg('Policy is valid', 'success');
    else showMsg('Validation errors: ' + result.errors.join('; '), 'error');
  } catch(e) { showMsg('Request failed: ' + e.message, 'error'); }
}

async function proposePolicy() {
  const data = getFormData();
  if (!data.actor_id || !data.policy_id) { showMsg('Actor ID and Policy ID are required', 'error'); return; }
  try {
    const res = await fetch('/admin/feed_policies/propose', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
    if (res.ok) {
      const result = await res.json();
      showMsg('Policy proposed via governance: ' + result.policy.policy_id, 'success');
      loadPolicies();
    } else {
      const err = await res.json();
      const detail = err.detail;
      if (typeof detail === 'object' && detail.errors) showMsg('Errors: ' + detail.errors.join('; '), 'error');
      else showMsg('Error: ' + (detail || 'Unknown'), 'error');
    }
  } catch(e) { showMsg('Request failed: ' + e.message, 'error'); }
}

async function approvePolicy(policyId) {
  const actorId = document.getElementById('inp-actor-id').value.trim();
  if (!actorId) { showMsg('Enter an Actor ID to approve', 'error'); return; }
  try {
    const res = await fetch('/admin/feed_policies/' + policyId + '/approve?actor_id=' + actorId, {method:'POST'});
    if (res.ok) { showMsg('Policy approved via governance: ' + policyId, 'success'); loadPolicies(); }
    else { const err = await res.json(); showMsg('Error: ' + (err.detail || 'Unknown'), 'error'); }
  } catch(e) { showMsg('Request failed: ' + e.message, 'error'); }
}

async function loadPolicies() {
  try {
    const res = await fetch('/admin/feed_policies');
    const data = await res.json();
    renderSummary(data);
    renderPolicies(data.policies || []);
  } catch(e) {}
}

function renderSummary(data) {
  document.getElementById('summary').innerHTML =
    '<div class="summary-card"><div class="label">Total Policies</div><div class="value">' + data.total_count + '</div></div>' +
    '<div class="summary-card"><div class="label">Active</div><div class="value">' + data.active_count + '</div></div>';
}

function renderPolicies(policies) {
  const el = document.getElementById('policies-table');
  if (!policies.length) { el.innerHTML = '<div class="empty">No policies registered</div>'; return; }
  let h = '<table><thead><tr><th>Policy ID</th><th>Status</th><th>Weights</th><th>Version</th><th>Max Age</th><th>Min Trust</th><th>Actions</th></tr></thead><tbody>';
  policies.forEach(p => {
    const status = (p.status === 'active' && p.approved) ? 'active' : 'pending';
    const approveBtn = status === 'pending' ? '<button class="approve-btn" data-testid="btn-approve-' + p.policy_id + '" onclick="approvePolicy(\\'' + p.policy_id + '\\')">Approve</button>' : '';
    h += '<tr data-testid="row-policy-' + p.policy_id + '">' +
      '<td>' + p.policy_id + '</td>' +
      '<td><span class="status-badge ' + status + '">' + status + '</span></td>' +
      '<td>' + weightBar(p) + '</td>' +
      '<td>' + (p.version || '-').substring(0,8) + '</td>' +
      '<td>' + (p.max_age_hours || '-') + 'h</td>' +
      '<td>' + (p.min_trust_threshold !== undefined ? p.min_trust_threshold : '-') + '</td>' +
      '<td>' + approveBtn + '</td>' +
      '</tr>';
  });
  el.innerHTML = h + '</tbody></table>';
}

function weightBar(p) {
  const ts = ((p.timestamp_weight||0)*100).toFixed(0);
  const re = ((p.reaction_weight||0)*100).toFixed(0);
  const tr = ((p.trust_weight||0)*100).toFixed(0);
  const po = ((p.policy_weight||0)*100).toFixed(0);
  return '<div class="weight-bar">' +
    '<div class="seg ts" style="width:' + ts + '%" title="Timestamp: ' + ts + '%">' + ts + '</div>' +
    '<div class="seg react" style="width:' + re + '%" title="Reaction: ' + re + '%">' + re + '</div>' +
    '<div class="seg trust" style="width:' + tr + '%" title="Trust: ' + tr + '%">' + tr + '</div>' +
    '<div class="seg pol" style="width:' + po + '%" title="Policy: ' + po + '%">' + po + '</div>' +
  '</div>';
}

loadPolicies();
</script>
</body>
</html>"""
