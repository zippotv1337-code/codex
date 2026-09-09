const root = document.querySelector("#control-root");
const toast = document.querySelector("#toast");
const esc = (v) => String(v ?? "—").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;");

function cookieValue(name) {
  return document.cookie.split(";").map(v => v.trim()).filter(v => v.startsWith(`${name}=`)).map(v => decodeURIComponent(v.substring(name.length + 1)))[0] || "";
}
function showToast(message) { toast.textContent = message; toast.classList.add("show"); window.setTimeout(() => toast.classList.remove("show"), 2600); }
function capability(item) { return `<li><span><b>${esc(item.label)}</b><small>${esc(item.id)}</small></span><em class="cap-${esc(item.state.toLowerCase())}">${esc(item.state.replaceAll("_", " "))}</em></li>`; }
function queueItem(item) { return `<li><span><b>${esc(item.persona)}</b><small>${esc(item.series)}</small></span><em>${esc(item.status.replaceAll("_", " "))}</em></li>`; }

function render(payload) {
  const s = payload.state;
  const paused = s.status === "PAUSED";
  root.innerHTML = `
    <section class="control-hero">
      <div><p class="card-kicker">Autopilot-Status</p><h2>${esc(s.status)}</h2><p>${esc(s.continuation_point)}</p></div>
      <div class="contract-note"><b>Kompatibilitätsvertrag v${esc(payload.contract.schema_version)}</b><span>Baseline: aktuelles stabiles Modell</span><span>Rückwärtskompatibel: ja</span></div>
    </section>
    <section class="control-actions" aria-label="Sichere Autopilot-Steuerung">
      <button data-command="run-once" ${paused ? "disabled" : ""}>Sicheren Lauf prüfen</button>
      <button data-command="checkpoint">Checkpoint sichern</button>
      <button data-command="${paused ? "resume" : "pause"}" class="secondary">${paused ? "Fortsetzen" : "Pausieren"}</button>
    </section>
    <p class="control-warning">Diese Steuerung verarbeitet nur lokale, reversible Aufgaben. Owner-Gates bleiben gesperrt.</p>
    <section class="control-panel"><p class="card-kicker">Lokaler Hintergrundbetrieb</p><h2>Health &amp; Recovery</h2>
      <p>Letzter Healthcheck: ${esc(payload.local_ops?.maintenance?.last_healthcheck?.checked_at)} · ${esc(payload.local_ops?.maintenance?.last_healthcheck?.overall)}</p>
      <p>Wochenbackup: ${esc(payload.local_ops?.maintenance?.last_weekly_backup?.verified_at)} · Monatsbackup: ${esc(payload.local_ops?.maintenance?.last_monthly_backup?.verified_at)}</p>
      <p>Scheduler: ${esc(payload.local_ops?.maintenance?.last_run?.status)} · zuletzt ${esc(payload.local_ops?.maintenance?.last_run?.checked_at)} · Watchdog: ${esc(payload.local_ops?.watchdog?.status)} · zuletzt ${esc(payload.local_ops?.watchdog?.checked_at)}</p>
      <p>Datenbank: ${esc(payload.local_ops?.maintenance?.last_healthcheck?.checks?.Database)} · Runtime: ${esc(payload.local_ops?.maintenance?.last_healthcheck?.checks?.Runtime)} · Windows-Aufgaben: ${esc(payload.local_ops?.tasks?.status)}</p>
      <p>Letzter Wartungsfehler: ${esc(payload.local_ops?.last_failure?.status)} · ${esc(payload.local_ops?.last_failure?.checked_at)}</p>
      <small>Messzeitpunkte beachten; keine Live-Garantie. Pausieren stoppt lokale Wartung. Kein Plattformversand durch Hintergrundjobs.</small></section>
    <div class="control-grid">
      <section class="control-panel"><p class="card-kicker">Fähigkeiten</p><h2>Capability Matrix</h2><ul class="control-list">${payload.capabilities.map(capability).join("")}</ul></section>
      <section class="control-panel"><p class="card-kicker">Nächster sicherer Schritt</p><h2>Arbeitsqueue</h2><ul class="control-list">${payload.queue.length ? payload.queue.map(queueItem).join("") : "<li>Keine lokale Arbeit offen.</li>"}</ul></section>
    </div>
    <section class="control-panel owner-gates"><p class="card-kicker">Nie automatisch</p><h2>Owner-Gates</h2><p>${payload.owner_gates.map(esc).join(" · ")}</p><small>Letzter Befehl: ${esc(s.last_command)} · Läufe: ${esc(s.run_count)} · Checkpoint: ${esc(s.checkpoint_at)}</small></section>`;
  root.setAttribute("aria-busy", "false");
}

async function api(url, options = {}) {
  const method = options.method || "GET";
  const token = cookieValue("creator_ops_csrf");
  const response = await fetch(url, { credentials: "same-origin", ...options, headers: { ...(options.headers || {}), ...(method === "POST" && token ? { "X-CSRF-Token": token } : {}) } });
  if (response.status === 401) { window.location.assign("/login"); throw new Error("Anmeldung erforderlich"); }
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || `Status ${response.status}`);
  return payload;
}

async function load() { try { render(await api("/api/control-plane")); } catch (error) { root.innerHTML = `<div class="error">${esc(error.message)}</div>`; } }
root.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-command]");
  if (!button) return;
  button.disabled = true;
  try { render(await api(`/api/control-plane/${button.dataset.command}`, { method: "POST" })); showToast("Lokaler Speicherstand aktualisiert"); }
  catch (error) { showToast(error.message); await load(); }
});
load();
