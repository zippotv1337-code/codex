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
  const preview = draft.asset_ready && draft.preview.asset_url
    ? `<div class="vertical-screen has-asset"><img src="${esc(draft.preview.asset_url)}" alt="9:16-Vorschau: ${esc(draft.title)}" /><span>9:16 · PUBLIC SFW</span></div>`
    : `<div class="vertical-screen"><span>9:16</span><b>Noch kein echtes Video/Bild</b><small>${esc(draft.title)}</small></div>`;
  const hashtags = Array.isArray(draft.hashtags) ? draft.hashtags.join(" ") : "—";
  return `<article class="channel-draft" data-brand="${esc(brand.slug)}" data-draft="${esc(draft.draft_id)}">
    <div class="vertical-preview">
      ${preview}
    </div>
    <div class="channel-draft-copy">
      <p class="card-kicker">${esc(draft.platform)} · ${esc(draft.format)}</p>
      <h2>${esc(draft.title)}</h2>
      <p><b>Hook:</b> ${esc(draft.hook)}</p>
      <p>${esc(draft.caption)}</p>
      <p><b>CTA:</b> ${esc(draft.cta || "—")}</p>
      <p class="channel-hashtags">${esc(hashtags)}</p>
      <div class="channel-badges"><span>${esc(draft.status)}</span><span>${esc(draft.approval_status)}</span><span>${esc(draft.upload_mode)}</span></div>
      ${draft.read_only ? `<p>Bereits veröffentlicht · kein erneuter Upload. Nachweis und Analytics stehen oben im Verlauf.</p>` : `<fieldset>
      <label>Review-Hinweis<input data-review-note maxlength="500" placeholder="Optionaler Änderungsgrund" value="${esc(draft.review_note || "")}" /></label>
      <div class="channel-review-actions">
        <button type="button" data-action="approve">APPROVE · lokal</button>
        <button type="button" data-action="change" class="secondary">CHANGE</button>
        <button type="button" data-action="reject" class="secondary">REJECT</button>
      </div>
      <label>Ausführungsweg<select data-upload-mode><option value="DRAFT_UPLOAD" ${draft.upload_mode === "DRAFT_UPLOAD" ? "selected" : ""}>Draft Upload</option><option value="DIRECT_POST" ${draft.upload_mode === "DIRECT_POST" ? "selected" : ""}>Direct Post</option></select></label>
      <button type="button" data-action="mode" class="channel-mode-button">Modus lokal prüfen und speichern</button>
      </fieldset>`}
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
    <article><p class="card-kicker">Historische Publikationsnachweise</p><h2>${Array.isArray(payload.external_actions) ? payload.external_actions.length : 0}</h2><p>Kein neuer Versand durch das Laden dieser Seite.</p></article>
  </section>`;
  root.setAttribute("aria-busy", "false");
}

async function load() {
  try { render(await api("/api/channels")); }
  catch (error) { root.innerHTML = `<div class="error">${esc(error.message)}</div>`; }
  await loadOperations();
}

const operationsRoot = document.querySelector("#operations-root");
const metricKeys = ["views", "likes", "comments", "shares", "saves", "profile_visits", "follows", "link_clicks"];
function safeLink(value) {
  try { const url = new URL(value); return url.protocol === "https:" && ["www.tiktok.com", "www.instagram.com"].includes(url.hostname) ? url.href : ""; }
  catch { return ""; }
}
async function loadOperations() {
  try {
    const data = await api("/api/channel-operations");
    const push = await api("/api/meta-push");
    const packageCards = push.packages.length
      ? push.packages.map(item => {
        const blocked = item.local_blocker || (item.external_url ? "bereits extern bestätigt" : "");
        return `<article class="summary meta-push-package" data-meta-content="${esc(item.content_id)}">
          <div><p class="card-kicker">${esc(item.display_name)} · Paket ${esc(item.content_id)}</p>
          <h3>${esc(item.title)}</h3><p>Status: <b>${esc(item.status)}</b> · Versuche: ${esc(item.attempts)}</p>
          <p>${blocked ? `Blockiert: ${esc(blocked.replaceAll("_", " "))}` : "Bereit für genau einen kontrollierten Einzelversand"}</p>
          <div class="meta-push-actions"><button type="button" data-meta-action="preflight" data-content-id="${esc(item.content_id)}">Einzelpaket prüfen</button>
          ${blocked ? "" : `<button type="button" data-meta-action="push" data-content-id="${esc(item.content_id)}" class="primary">Dieses Paket senden</button>`}</div></div>
        </article>`;
      }).join("")
      : "<p>Kein lokal freigegebenes Einzelpaket in der Queue.</p>";
    operationsRoot.innerHTML = `<section class="channel-data-grid">
      <article><p>Projektaccounts</p><h2>${data.summary.accounts}</h2><p>${data.summary.api_connected} API-Verbindungen bestätigt</p></article>
      <article><p>Verlauf</p><h2>${data.summary.native_receipts}</h2><p>Vorhandene native Nachweise · kein API-Proof</p></article>
      <article><p>Analytics</p><h2>${data.summary.due_windows} fällig</h2><p>${data.summary.captured_windows} Messfenster erfasst</p></article>
    </section><h2>Accounts · technische Verbindung</h2><div class="channel-account-grid">${data.accounts.map(account => `<article class="channel-account blocked"><div>
      <b>${esc(account.display_name)} · ${esc(account.platform)}</b><span>@${esc(account.username)}</span>
      <p>${esc(account.connection_status)} · Token: ${esc(account.token_status)}</p>
      <p>Scopes: ${esc(account.scopes.join(", ") || "nicht konfiguriert")}</p>
      <p>Letzter Sync: ${esc(account.last_sync_at || "noch keiner")}</p>
      <p>Follower ${esc(account.profile.follower_count ?? "UNKNOWN")} · Likes ${esc(account.profile.likes_count ?? "UNKNOWN")}</p>
      ${account.id === "milo-der-zug:tiktok" ? `<button data-sync="${esc(account.id)}">Account prüfen / lesend synchronisieren</button>` : `<a href="/analytics">Bestehende Instagram-Analytics öffnen</a>`}
      ${account.last_error ? `<p>Hinweis: ${esc(account.last_error)}</p>` : ""}
    </div></article>`).join("")}</div>
    <h2>Veröffentlicht · 24h / 72h / 7 Tage</h2>${data.publications.map(post => `<article class="summary">
      <h3>${esc(post.title)}</h3><p>${esc(post.creator_id)} · ${esc(post.format)} · ${esc(post.transport)}</p>
      ${safeLink(post.permalink) ? `<a href="${esc(safeLink(post.permalink))}" target="_blank" rel="noopener noreferrer">TikTok-Beitrag öffnen</a>` : ""}
      <p>Historischer Nachweis aus der Kontositzung; öffentliche Sichtbarkeit hier nicht erneut geprüft.</p>
      <div class="channel-account-grid">${post.windows.map(window => `<section>
        <b>${window.hours}h · ${esc(window.status)}</b><p>${esc(new Date(window.due_at).toLocaleString("de-DE"))}</p>
        <form data-metrics data-post="${esc(post.external_post_id)}" data-hours="${window.hours}"><fieldset ${window.status === "WAITING" ? "disabled" : ""}>
          <legend>Echte Messwerte · leer = UNKNOWN</legend>
          ${metricKeys.map(key => `<label>${esc(key)}<input name="${key}" type="number" min="0" step="1" placeholder="UNKNOWN" value="${esc(window.metrics[key] ?? "")}" /></label>`).join("")}
          <button type="submit">Beobachtete Werte speichern</button>
        </fieldset></form></section>`).join("")}</div>
      <p>Learning: ${esc(post.learning)} · Noch keine belastbare Gewinner-Aussage.</p>
    </article>`).join("") || "<p>Noch keine bestätigten Kanalpublikationen.</p>"}
    <h2>Meta Graph · kontrollierter Einzelversand</h2>
    <section class="summary meta-push-panel"><p>Frischer Preflight vor jedem Versand. Automatischer Scheduler bleibt unverändert deaktiviert. Es wird niemals mehr als das ausgewählte Paket angesprochen.</p>
      <p>Graph-Version: ${push.graph_version_configured ? "konfiguriert" : "fehlt"} · Manifest: ${push.manifest_present ? "vorhanden" : "fehlt"} · Proof: ${esc(push.api_proof)}</p>
      <div class="meta-push-packages">${packageCards}</div>
      <p class="muted">App-ID und App-Geheimcode allein reichen nicht: je Persona werden ein echter Instagram-Nutzer-Token, die passende Nutzer-ID, Berechtigungen und öffentliche HTTPS-JPEGs benötigt.</p>
    </section>
    <h2>Video & Musik</h2><div class="channel-account-grid">${data.media.map(item => `<article class="summary"><h3>${esc(item.provider)} · ${esc(item.model)}</h3><p>${esc(item.status)} · ${item.credential_present ? "Credential vorhanden" : "Credential fehlt"}</p><p>Nur Brief-Vorbereitung. Live-Generator nicht implementiert; keine Kosten ausgelöst.</p></article>`).join("")}</div>
    <section class="summary"><h2>Local AI · Milo</h2><p>Status: ${esc(data.local_ai.status)} · ${esc(data.local_ai.result?.model || "noch kein Modellnachweis")}</p><p>${esc(data.local_ai.result?.output_path || "Neuer begrenzter Brief-Task wartet in AI Ops.")}</p><a href="/ai-ops">Lokalen Qwen-Lauf öffnen</a><p>Bildpixel-QA separat erforderlich. Das Modell arbeitet hier nur mit Metadaten.</p></section>`;
  } catch (error) { operationsRoot.textContent = `Betriebsstand konnte nicht geladen werden: ${error.message}`; }
}
operationsRoot.addEventListener("click", async event => {
  const button = event.target.closest("[data-sync]");
  if (button) {
    button.disabled = true;
    try {
      const result = await api("/api/channel-operations/sync", {method: "POST", headers: {"Content-Type": "application/x-www-form-urlencoded"}, body: new URLSearchParams({account_id: button.dataset.sync})});
      showToast(result.error || result.status);
      await loadOperations();
    } catch (error) { showToast(error.message); button.disabled = false; }
    return;
  }
  const metaButton = event.target.closest("[data-meta-action]");
  if (!metaButton) return;
  metaButton.disabled = true;
  const contentId = metaButton.dataset.contentId;
  const path = metaButton.dataset.metaAction === "preflight" ? "/api/meta-push/preflight" : "/api/meta-push/push-one";
  try {
    const result = await api(path, {method: "POST", headers: {"Content-Type": "application/x-www-form-urlencoded"}, body: new URLSearchParams({content_id: contentId})});
    const status = result.status || result.dispatch?.status || result.error || "abgeschlossen";
    showToast(`Meta ${metaButton.dataset.metaAction}: ${status}`);
    await loadOperations();
  } catch (error) { showToast(error.message); metaButton.disabled = false; }
});
operationsRoot.addEventListener("submit", async event => {
  const form = event.target.closest("[data-metrics]");
  if (!form) return;
  event.preventDefault();
  const body = new URLSearchParams(new FormData(form));
  body.set("post_id", form.dataset.post); body.set("hours", form.dataset.hours);
  try {
    await api("/api/channel-operations/metrics", {method: "POST", headers: {"Content-Type": "application/x-www-form-urlencoded"}, body});
    showToast("Echte Messung lokal gespeichert"); await loadOperations();
  } catch (error) { showToast(error.message); }
});

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
