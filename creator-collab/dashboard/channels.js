const root = document.querySelector("#channels-root");
const toast = document.querySelector("#toast");
const esc = (value) => String(value ?? "—").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;");

function cookieValue(name) {
  return document.cookie.split(";").map(value => value.trim()).filter(value => value.startsWith(`${name}=`)).map(value => decodeURIComponent(value.slice(name.length + 1)))[0] || "";
}

function showToast(message) {
  toast.textContent = message;
  toast.classList.add("show");
  window.setTimeout(() => toast.classList.remove("show"), 2800);
}

async function api(path, options = {}) {
  const method = (options.method || "GET").toUpperCase();
  const response = await fetch(path, {
    credentials: "same-origin",
    ...options,
    headers: {
      ...(options.headers || {}),
      ...(method === "POST" ? {"X-CSRF-Token": cookieValue("creator_ops_csrf")} : {}),
    },
  });
  if (response.status === 401) {
    window.location.assign("/login");
    throw new Error("Anmeldung erforderlich");
  }
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || `Status ${response.status}`);
  return payload;
}

function accountTemplate(account) {
  const state = account.connection_status === "CONNECTED" ? "connected" : "blocked";
  return `<article class="channel-account ${state}"><div><b>${esc(account.platform.toUpperCase())}</b><span>${esc(account.public_handle || "Noch kein Projektkonto verbunden")}</span></div><em>${esc(account.connection_status.replaceAll("_", " "))}</em></article>`;
}

function draftTemplate(brand, draft) {
  const blockers = draft.direct_post_blockers.length
    ? draft.direct_post_blockers.map(item => `<li>${esc(item.replaceAll("_", " "))}</li>`).join("")
    : "<li>Alle lokalen Gates erfüllt</li>";
  return `<article class="channel-draft" data-brand="${esc(brand.slug)}" data-draft="${esc(draft.draft_id)}">
    <div class="vertical-preview">
      <div class="vertical-screen"><span>9:16</span><b>${draft.asset_ready ? "Asset bereit" : "Noch kein echtes Video/Bild"}</b><small>${esc(draft.title)}</small></div>
    </div>
    <div class="channel-draft-copy">
      <p class="card-kicker">${esc(draft.platform)} · ${esc(draft.format)}</p>
      <h2>${esc(draft.title)}</h2>
      <p><b>Hook:</b> ${esc(draft.hook)}</p>
      <p>${esc(draft.caption)}</p>
      <div class="channel-badges"><span>${esc(draft.status)}</span><span>${esc(draft.approval_status)}</span><span>${esc(draft.upload_mode)}</span></div>
      <label>Review-Hinweis<input data-review-note maxlength="500" placeholder="Optionaler Änderungsgrund" value="${esc(draft.review_note || "")}" /></label>
      <div class="channel-review-actions">
        <button type="button" data-action="approve">APPROVE · lokal</button>
        <button type="button" data-action="change" class="secondary">CHANGE</button>
        <button type="button" data-action="reject" class="secondary">REJECT</button>
      </div>
      <label>Ausführungsweg<select data-upload-mode><option value="DRAFT_UPLOAD" ${draft.upload_mode === "DRAFT_UPLOAD" ? "selected" : ""}>Draft Upload</option><option value="DIRECT_POST" ${draft.upload_mode === "DIRECT_POST" ? "selected" : ""}>Direct Post</option></select></label>
      <button type="button" data-action="mode" class="channel-mode-button">Modus lokal prüfen und speichern</button>
      <details><summary>Direct-Post-Gates</summary><ul>${blockers}</ul></details>
    </div>
  </article>`;
}

function render(payload) {
  root.innerHTML = payload.brands.map(brand => `<section class="channel-workspace">
    <div class="section-heading"><div><p class="eyebrow">${esc(brand.kind)}</p><h2>${esc(brand.display_name)}</h2><p>${esc(brand.disclosure)}</p></div><span class="section-count">${esc(brand.identity_status.replaceAll("_", " "))}</span></div>
    <div class="channel-account-grid">${brand.accounts.map(accountTemplate).join("")}</div>
    <div class="channel-draft-grid">${brand.drafts.map(draft => draftTemplate(brand, draft)).join("")}</div>
  </section>`).join("") + `<section class="channel-data-grid">
    <article><p class="card-kicker">Analytics</p><h2>${payload.analytics.length}</h2><p>${payload.analytics.length ? "Echte Messpunkte gespeichert" : "Noch keine echten Werte · UNKNOWN/NULL"}</p></article>
    <article><p class="card-kicker">Errorlog</p><h2>${payload.errors.length}</h2><p>${payload.errors.length ? "Lokale Fehler protokolliert" : "Keine lokalen Kanalfehler"}</p></article>
    <article><p class="card-kicker">Externe Aktionen</p><h2>${esc(payload.external_actions)}</h2><p>Diese Seite bereitet nur lokal vor.</p></article>
  </section>`;
  root.setAttribute("aria-busy", "false");
}

async function load() {
  try { render(await api("/api/channels")); }
  catch (error) { root.innerHTML = `<div class="error">${esc(error.message)}</div>`; }
}

root.addEventListener("click", async event => {
  const button = event.target.closest("[data-action]");
  if (!button) return;
  const card = button.closest("[data-brand][data-draft]");
  if (!card) return;
  const action = button.dataset.action;
  const form = new URLSearchParams();
  if (action === "mode") form.set("mode", card.querySelector("[data-upload-mode]").value);
  else form.set("note", card.querySelector("[data-review-note]").value);
  button.disabled = true;
  try {
    await api(`/api/channels/${encodeURIComponent(card.dataset.brand)}/drafts/${encodeURIComponent(card.dataset.draft)}/${action}`, {method: "POST", headers: {"Content-Type": "application/x-www-form-urlencoded"}, body: form});
    showToast("Lokaler Milo-Status gespeichert · nichts veröffentlicht");
    await load();
  } catch (error) {
    showToast(error.message);
    button.disabled = false;
  }
});

load();
