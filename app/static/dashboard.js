function fmtTime(epochSeconds) {
  if (!epochSeconds) return "—";
  const d = new Date(epochSeconds * 1000);
  return d.toLocaleTimeString();
}

function setError(msg) {
  const box = document.getElementById("errorBox");
  if (!msg) {
    box.style.display = "none";
    box.textContent = "";
    return;
  }
  box.style.display = "block";
  box.textContent = msg;
}

function getApiKey() {
  return localStorage.getItem("THROTTLE_DASH_API_KEY") || "";
}

function saveApiKey(key) {
  localStorage.setItem("THROTTLE_DASH_API_KEY", key);
}

async function fetchJson(url) {
  const apiKey = getApiKey();
  const res = await fetch(url, {
    headers: apiKey ? { "x-api-key": apiKey } : {},
  });

  const data = await res.json().catch(() => null);

  if (!res.ok) {
    // Try to surface your standardized error envelope
    const code = data?.error?.code || res.status;
    const msg = data?.error?.message || "Request failed";
    throw new Error(`${code}: ${msg}`);
  }
  return data;
}

function renderKeyMap(elId, obj) {
  const el = document.getElementById(elId);
  const entries = Object.entries(obj || {});
  if (entries.length === 0) {
    el.innerHTML = `<div class="muted">No data yet.</div>`;
    return;
  }
  el.innerHTML = entries
    .sort((a, b) => b[1] - a[1])
    .map(
      ([
        k,
        v,
      ]) => `<div style="display:flex; justify-content:space-between; padding:6px 0; border-bottom:1px solid #1e2a44;">
        <div>${k}</div><div style="font-weight:700;">${v}</div>
      </div>`
    )
    .join("");
}

function renderEvents(events) {
  const tbody = document.getElementById("eventsTbody");
  const rows = (events || []).map((e) => {
    const retryAfter = e?.details?.retry_after ?? "—";
    const reset = e?.details?.reset ? fmtTime(e.details.reset) : "—";
    const count = e?.details?.count ?? "—";
    return `<tr>
      <td>${fmtTime(e.timestamp_epoch)}</td>
      <td>${e.path}</td>
      <td>${e.api_key}</td>
      <td>${retryAfter}</td>
      <td>${reset}</td>
      <td>${count}</td>
    </tr>`;
  });
  tbody.innerHTML =
    rows.join("") ||
    `<tr><td colspan="6" class="muted">No events yet.</td></tr>`;
}

async function refresh() {
  try {
    setError("");
    const [m, e] = await Promise.all([
      fetchJson("/admin/metrics"),
      fetchJson("/admin/events?limit=25"),
    ]);

    document.getElementById("kpiTotal").textContent = m.total_requests;
    document.getElementById("kpiAllowed").textContent = m.allowed_requests;
    document.getElementById("kpiBlocked").textContent = m.blocked_requests;
    document.getElementById("kpiAuthMissing").textContent = m.auth_missing;
    document.getElementById("kpiAuthInvalid").textContent = m.auth_invalid;

    renderKeyMap("byKey", m.requests_by_key);
    renderKeyMap("blockedByKey", m.blocked_by_key);
    renderEvents(e.events);

    document.getElementById("lastUpdated").textContent =
      "Last updated: " + new Date().toLocaleTimeString();
  } catch (err) {
    setError(err.message);
  }
}

// Hook up UI
document.getElementById("saveKeyBtn").addEventListener("click", () => {
  const key = document.getElementById("apiKey").value.trim();
  saveApiKey(key);
  refresh();
});

document
  .getElementById("refreshBtn")
  .addEventListener("click", () => refresh());

// On load: prefill api key and start auto-refresh
document.getElementById("apiKey").value = getApiKey();
refresh();
setInterval(refresh, 2000);
