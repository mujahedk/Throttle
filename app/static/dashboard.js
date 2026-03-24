function fmtTime(epochSeconds) {
  if (!epochSeconds) return "\u2014";
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

function showLocked() {
  document.getElementById("dataContent").style.display = "none";
  document.getElementById("lockedMsg").style.display = "";
}

function showUnlocked() {
  document.getElementById("dataContent").style.display = "";
  document.getElementById("lockedMsg").style.display = "none";
}

async function fetchJson(url) {
  const apiKey = getApiKey();
  const res = await fetch(url, {
    headers: apiKey ? { "x-api-key": apiKey } : {},
  });

  const data = await res.json().catch(() => null);

  if (!res.ok) {
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
      ([k, v]) =>
        `<div style="display:flex; justify-content:space-between; padding:6px 0; border-bottom:1px solid #1e2a44;">
          <div>${k}</div><div style="font-weight:700;">${v}</div>
        </div>`
    )
    .join("");
}

function renderEvents(events) {
  const tbody = document.getElementById("eventsTbody");
  const rows = (events || []).map((e) => {
    const retryAfter = e?.details?.retry_after != null ? `${e.details.retry_after}s` : "\u2014";
    const reset = e?.details?.reset ? fmtTime(e.details.reset) : "\u2014";
    const count = e?.details?.count ?? "\u2014";
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

    showUnlocked();

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
    const isAuthError =
      err.message.includes("AUTH_") ||
      err.message.includes("401") ||
      err.message.includes("403");
    if (isAuthError) {
      showLocked();
      setError("Invalid API key. Enter a valid key above.");
    } else {
      setError(err.message);
    }
  }
}

document.getElementById("saveKeyBtn").addEventListener("click", () => {
  const key = document.getElementById("apiKey").value.trim();
  saveApiKey(key);
  if (key) {
    refresh();
  } else {
    setError("");
    showLocked();
  }
});

document
  .getElementById("refreshBtn")
  .addEventListener("click", () => refresh());

// Init: pre-fill the input from storage; only fetch if a key is present
document.getElementById("apiKey").value = getApiKey();
if (getApiKey()) {
  refresh();
} else {
  showLocked();
}
setInterval(refresh, 2000);
