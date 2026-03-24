from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_page():
    """
    Serve a simple HTML page. The page loads /static/dashboard.js
    which calls /admin/metrics + /admin/events and renders the UI.

    We keep this route public so you can open it in a browser easily.
    The admin APIs remain protected by x-api-key.
    """
    html = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>Throttle Dashboard</title>
  <style>
    body { font-family: ui-sans-serif, system-ui, -apple-system; margin: 0; background: #0b0f19; color: #e7eaf0; }
    .wrap { max-width: 1100px; margin: 0 auto; padding: 20px; }
    .row { display: flex; gap: 12px; flex-wrap: wrap; }
    .card { background: #121a2a; border: 1px solid #1e2a44; border-radius: 14px; padding: 14px; }
    .kpi { flex: 1 1 160px; min-width: 160px; }
    .kpi .label { font-size: 12px; opacity: 0.8; }
    .kpi .value { font-size: 26px; font-weight: 700; margin-top: 6px; }
    .panel { flex: 1 1 340px; min-width: 340px; }
    input { background: #0b1220; border: 1px solid #24314f; color: #e7eaf0; padding: 10px; border-radius: 10px; width: 320px; }
    button { background: #2a66ff; border: none; color: white; padding: 10px 12px; border-radius: 10px; cursor: pointer; }
    button:disabled { opacity: 0.6; cursor: not-allowed; }
    .muted { opacity: 0.75; font-size: 12px; }
    table { width: 100%; border-collapse: collapse; }
    th, td { text-align: left; padding: 10px; border-bottom: 1px solid #1e2a44; font-size: 13px; }
    th { opacity: 0.85; font-weight: 600; }
    .error { background: #2a1212; border: 1px solid #5a1f1f; color: #ffd1d1; padding: 10px 12px; border-radius: 12px; margin: 12px 0; display:none; }
    a { color: #8fb3ff; }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="row" style="justify-content: space-between; align-items: center;">
      <div>
        <h1 style="margin: 0 0 6px 0;">Throttle Dashboard</h1>
        <div class="muted">Live view of metrics + rate limit events.</div>
      </div>
      <div class="card" style="display:flex; gap:10px; align-items:center;">
        <input id="apiKey" placeholder="Enter x-api-key (e.g. dev_key_123)" />
        <button id="saveKeyBtn">Save</button>
      </div>
    </div>

    <div id="errorBox" class="error"></div>

    <div id="lockedMsg" class="card" style="margin-top:20px; text-align:center; padding:40px 20px;">
      <div style="font-size:15px; opacity:0.6;">Enter a valid API key above to view dashboard data.</div>
    </div>

    <div id="dataContent" style="display:none;">
      <div class="row" style="margin-top: 14px;">
        <div class="card kpi"><div class="label">Total Requests</div><div class="value" id="kpiTotal">&mdash;</div></div>
        <div class="card kpi"><div class="label">Allowed</div><div class="value" id="kpiAllowed">&mdash;</div></div>
        <div class="card kpi"><div class="label">Blocked (429)</div><div class="value" id="kpiBlocked">&mdash;</div></div>
        <div class="card kpi"><div class="label">Auth Missing</div><div class="value" id="kpiAuthMissing">&mdash;</div></div>
        <div class="card kpi"><div class="label">Auth Invalid</div><div class="value" id="kpiAuthInvalid">&mdash;</div></div>
      </div>

      <div class="row" style="margin-top: 12px;">
        <div class="card panel">
          <div style="display:flex; justify-content: space-between; align-items:center;">
            <div style="font-weight:700;">Requests by Key</div>
            <div class="muted" id="lastUpdated">Last updated: &mdash;</div>
          </div>
          <div id="byKey" style="margin-top:10px;"></div>
        </div>
        <div class="card panel">
          <div style="font-weight:700;">Blocked by Key</div>
          <div id="blockedByKey" style="margin-top:10px;"></div>
        </div>
      </div>

      <div class="card" style="margin-top: 12px;">
        <div style="display:flex; justify-content: space-between; align-items:center;">
          <div style="font-weight:700;">Recent Rate Limit Events</div>
          <button id="refreshBtn">Refresh</button>
        </div>
        <div style="overflow:auto; margin-top:10px;">
          <table>
            <thead>
              <tr>
                <th>Time</th>
                <th>Path</th>
                <th>API Key</th>
                <th>Retry-After</th>
                <th>Reset</th>
                <th>Count</th>
              </tr>
            </thead>
            <tbody id="eventsTbody"></tbody>
          </table>
        </div>
      </div>
    </div>
  </div>

  <script src="/static/dashboard.js"></script>
</body>
</html>
"""
    return HTMLResponse(content=html)
