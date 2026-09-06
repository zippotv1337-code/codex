const cardsRoot = document.querySelector("#cards");
const readyCount = document.querySelector("#ready-count");
const targetDate = document.querySelector("#target-date");
const toast = document.querySelector("#toast");
const stageFilters = document.querySelectorAll("[data-stage-filter]");
let currentCards = [];
let activeStage = "ALL";
let previewState = null;
let pendingDecision = null;

const poseLabels = {
  FRONTAL: "Frontal",
  LEFT_3Q: "Links ¾",
  RIGHT_3Q: "Rechts ¾",
  FULL_BODY_ACTION: "Ganzkörper",
  CANDID: "Candid",
  UNASSIGNED: "Pose offen",
};
const instagramHandles = { "leona-voss": "leonavoss.ai", "mara-field": "mara.field.ai" };

const escapeHtml = (value) => String(value)
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;")
  .replaceAll("'", "&#039;");

function cookieValue(name) {
  return document.cookie.split(";")
    .map((value) => value.trim())
    .filter((value) => value.startsWith(`${name}=`))
    .map((value) => decodeURIComponent(value.substring(name.length + 1)))[0] || "";
}

function csrfHeaders() {
  const token = cookieValue("creator_ops_csrf");
  return token ? { "X-CSRF-Token": token } : {};
}

function showToast(message) {
  toast.textContent = message;
  toast.classList.add("show");
  window.setTimeout(() => toast.classList.remove("show"), 2800);
}

function check(label, ok, detail) {
  return `
    <div class="check">
      <i class="check-icon" aria-label="${ok ? "bereit" : "fehlt"}">${ok ? "✓" : "–"}</i>
      <div class="check-copy"><span>${escapeHtml(label)}</span>
        <small title="${escapeHtml(detail)}">${escapeHtml(detail)}</small>
      </div>
    </div>`;
}

function statusMeta(card) {
  if (card.schedule_status === "PUBLISHED") return { key: "published", label: "Veröffentlicht" };
  if (card.schedule_status === "PUBLISHING") return { key: "scheduled", label: "Veröffentlichung läuft" };
  if (card.schedule_status === "PUBLISH_DUE") return { key: "scheduled", label: "Veröffentlichung fällig" };
  if (card.schedule_status === "NEEDS_RESCHEDULE_REVIEW") return { key: "change", label: "Neue Zeit prüfen" };
  if (card.schedule_status === "FAILED_RETRYABLE") return { key: "change", label: "Erneut versuchen" };
  if (card.schedule_status === "BLOCKED_EXTERNAL_PUBLISHING") return { key: "rejected", label: "Extern blockiert" };
  if (card.schedule_status === "LOCAL_SCHEDULED") return { key: "scheduled", label: "Creator Ops terminiert" };
  if (card.approved || card.status === "OWNER_APPROVED") return { key: "approved", label: "Freigegeben" };
  if (card.status === "SCHEDULED") return { key: "scheduled", label: "Geplant" };
  if (card.status === "READY_FOR_REVIEW") return { key: "ready", label: "Review bereit" };
  if (card.status === "PARTIAL_READY") return { key: "change", label: "Änderung nötig" };
  if (card.status === "BLOCKED") return { key: "rejected", label: "Abgelehnt" };
  return { key: "pending", label: card.status.replaceAll("_", " ") };
}

function cardTemplate(card) {
  const protectedPreview = card.privacy_blur || card.visibility_scope === "ADULT_ONLY";
  const assets = card.assets.map((asset) => `
    <div class="asset ${asset.top_pick ? "top" : ""} ${asset.excluded ? "excluded" : ""} ${asset.preview_url ? "has-preview" : ""} ${protectedPreview ? "privacy-blur" : ""}" ${asset.preview_url ? `style="background-image:url('${escapeHtml(asset.preview_url)}')"` : ""} aria-label="${escapeHtml(asset.label)}, ${escapeHtml(poseLabels[asset.pose_slot] || asset.pose_slot)}, Qualität ${asset.quality} Prozent${asset.top_pick ? ", Top Pick" : ""}${asset.excluded ? ", bereits veröffentlicht und ausgeschlossen" : ""}">
      <span class="quality">${asset.quality}%</span>
      ${asset.top_pick ? `<span class="asset-badge">TOP ${asset.top_pick_order}</span>` : ""}
      ${asset.excluded ? '<span class="excluded-badge">VERÖFFENTLICHT</span>' : ""}
      <span>${escapeHtml(poseLabels[asset.pose_slot] || asset.label)}</span>
    </div>`).join("");
  const approved = card.approved;
  const canApprove = card.can_approve ?? (card.ready && !approved && card.status === "READY_FOR_REVIEW");
  const canReschedule = card.schedule_status === "NEEDS_RESCHEDULE_REVIEW" && Boolean(card.suggested_at);
  const canAuthorizeLive = Boolean(card.can_authorize_live_publish);
  const canRearmPreflight = Boolean(card.can_rearm_preflight);
  const status = statusMeta(card);
  const audioDetails = card.audio_options.map((option) => {
    const review = ["REVIEW_REQUIRED", "VERIFY_BEFORE_USE", "MOCK_ONLY"].includes(option.license_status)
      ? " (vor Nutzung prüfen)"
      : option.license_status === "SAFE_NO_AUDIO" ? " (sicherer Fallback)" : "";
    return `${escapeHtml(option.label)}${option.selected ? " ✓ gewählt" : ""}${review}`;
  }).join(" · ");
  return `
    <article class="creator-card ${protectedPreview ? "privacy-protected" : ""}" data-persona="${escapeHtml(card.creator_slug)}" data-stage="${escapeHtml(card.content_stage)}">
      <div class="card-head">
        <div class="identity">
          <img class="avatar" src="/assets/${escapeHtml(card.creator_slug)}-avatar.png" alt="KI-generiertes Profilbild von ${escapeHtml(card.display_name)}" />
          <div>
            <p class="card-kicker">${escapeHtml(card.date)} · ${escapeHtml(card.prime_time)} Uhr</p>
            <h2>${escapeHtml(card.display_name)}</h2>
            <p class="series">${escapeHtml(card.series)}</p>
            ${card.style_reference ? `<span class="style-ref">Style Ref: ${escapeHtml(card.style_reference)} · ${escapeHtml(card.reference_strength)}</span>` : ""}
          </div>
        </div>
        <div class="status-stack">
          <span class="stage-pill stage-${escapeHtml(card.content_stage.toLowerCase())}">${escapeHtml(card.content_stage.replaceAll("_", " "))}</span>
          <span class="status-pill status-${status.key}">${escapeHtml(status.label)}</span>
        </div>
      </div>
      <div class="asset-summary">
        <span><strong>${card.asset_count}</strong><small>Bilder vorhanden</small></span>
        <span><strong>Top ${card.top_pick_count}</strong><small>empfohlen</small></span>
        <span><strong>${card.excluded_published_count}</strong><small>veröffentlicht / raus</small></span>
      </div>
      <div class="asset-strip">${assets}</div>
      ${protectedPreview ? '<button class="reveal-button" type="button" data-reveal>Geschützte Vorschau einmal anzeigen</button>' : ""}
      <div class="checklist">
        ${check("Carousel", card.checks.carousel, `${card.top_pick_count} Slides ausgewählt · ${card.available_asset_count} Kandidaten verfügbar`)}
        ${check("Caption", card.checks.caption, "Text vollständig")}
        ${check("Musik", card.checks.music, card.audio)}
        ${check("Prime Time", card.checks.prime_time, `${card.prime_time} Uhr · Berlin`)}
        ${check("Pose-Matrix", card.checks.pose_matrix, "5 klar unterschiedliche Blickwinkel")}
        ${check("Sichtbarkeit", card.checks.public_scope, card.visibility_scope)}
      </div>
      ${card.qa_reasons.length ? `<p class="qa-warning">Noch offen: ${escapeHtml(card.qa_reasons.join(", "))}</p>` : ""}
      <details class="caption-preview" open>
        <summary>Posting-Details</summary>
        <dl class="posting-details">
          <div><dt>Hook</dt><dd>${escapeHtml(card.hook)}</dd></div>
          <div><dt>Caption</dt><dd>${escapeHtml(card.caption)}</dd></div>
          <div><dt>CTA</dt><dd>${escapeHtml(card.cta)}</dd></div>
          <div><dt>Hashtags</dt><dd>${escapeHtml(card.hashtags.map(x => `#${x.replace(/^#/, "")}`).join(" "))}</dd></div>
          <div><dt>Musik A / B / ohne</dt><dd>${audioDetails}</dd></div>
          <div><dt>Prime Time</dt><dd>${escapeHtml(card.prime_time)} Uhr · ${escapeHtml(card.schedule_source)}</dd></div>
          <div><dt>Terminierung</dt><dd>${escapeHtml(card.schedule_status.replaceAll("_", " "))}${card.suggested_at ? ` · Vorschlag ${escapeHtml(card.suggested_at)}` : ""}</dd></div>
        </dl>
      </details>
      <button class="large-preview-button" type="button" data-large-preview="${card.content_id}">Große Instagram-Vorschau</button>
      ${canReschedule ? `<button type="button" class="reschedule-button" data-action="reschedule" data-content-id="${card.content_id}">VORGESCHLAGENEN TERMIN ÜBERNEHMEN · nur lokal</button>` : ""}
      ${canAuthorizeLive ? `<button type="button" class="live-authorize-button" data-action="live-authorize" data-content-id="${card.content_id}">LIVE-VERSAND SEPARAT FREIGEBEN · postet noch nicht</button>` : ""}
      ${canRearmPreflight ? `<button type="button" class="rearm-preflight-button" data-action="rearm-preflight" data-content-id="${card.content_id}">SICHEREN PREFLIGHT ERNEUT PRÜFEN · postet noch nicht</button>` : ""}
      ${card.live_publish_authorized ? '<p class="live-gate-status">Live-Versand für genau dieses Paket autorisiert · globale Meta-Gates bleiben maßgeblich</p>' : ""}
      <div class="decision-help"><b>APPROVE</b> nur lokale Queue · <b>LIVE-FREIGABE</b> separat · <b>CHANGE</b> Überarbeitung · <b>REJECT</b> Paket blockieren</div>
      <div class="decision-actions">
        <button type="button" class="approve-button" data-action="approve" data-content-id="${card.content_id}" ${canApprove ? "" : "disabled"}>${approved ? "Freigegeben" : "APPROVE"}</button>
        <button type="button" class="change-button" data-action="change" data-content-id="${card.content_id}">CHANGE</button>
        <button type="button" class="reject-button" data-action="reject" data-content-id="${card.content_id}">REJECT</button>
      </div>
    </article>`;
}

function renderCards() {
  const visible = activeStage === "ALL"
    ? currentCards
    : currentCards.filter((card) => card.content_stage === activeStage);
  cardsRoot.innerHTML = visible.length
    ? visible.map(cardTemplate).join("")
    : '<div class="empty">Für diesen Filter gibt es morgen kein Paket.</div>';
}

function previewSlides(card) {
  const selected = card.assets.filter(asset => asset.top_pick && !asset.excluded)
    .sort((a, b) => a.top_pick_order - b.top_pick_order);
  return selected.length ? selected : card.assets.filter(asset => !asset.excluded).slice(0, 3);
}

function renderLargePreview() {
  if (!previewState) return;
  const { card, slides, index } = previewState;
  const asset = slides[index];
  const image = document.querySelector("#preview-image");
  image.style.backgroundImage = asset?.preview_url ? `url('${asset.preview_url}')` : "";
  image.classList.toggle("has-preview", Boolean(asset?.preview_url));
  document.querySelector("#preview-fallback").hidden = Boolean(asset?.preview_url);
  document.querySelector("#preview-counter").textContent = `${index + 1}/${slides.length}`;
  document.querySelector("#preview-dots").innerHTML = slides.map((_, position) => `<i class="${position === index ? "active" : ""}"></i>`).join("");
  document.querySelector("#preview-meta").textContent = `${poseLabels[asset?.pose_slot] || asset?.label || "Motiv"} · Qualität ${asset?.quality ?? "—"}% · ${card.prime_time} Uhr`;
}

function openLargePreview(card) {
  const overlay = document.querySelector("#large-preview");
  const slides = previewSlides(card);
  previewState = { card, slides, index: 0 };
  document.querySelector("#preview-avatar").src = `/assets/${card.creator_slug}-avatar.png`;
  document.querySelector("#preview-avatar").alt = `Profilbild von ${card.display_name}`;
  document.querySelector("#preview-handle").textContent = instagramHandles[card.creator_slug] || card.creator_slug;
  document.querySelector("#preview-title").textContent = card.display_name;
  document.querySelector("#preview-caption").textContent = card.caption;
  document.querySelector("#preview-series").textContent = card.series;
  overlay.hidden = false;
  overlay.setAttribute("aria-hidden", "false");
  document.body.classList.add("preview-open");
  renderLargePreview();
  document.querySelector("[data-preview-close]").focus();
}

function closeLargePreview() {
  const overlay = document.querySelector("#large-preview");
  overlay.hidden = true;
  overlay.setAttribute("aria-hidden", "true");
  document.body.classList.remove("preview-open");
  previewState = null;
}

async function apiFetch(url, options = {}) {
  const method = (options.method || "GET").toUpperCase();
  const response = await fetch(url, {
    credentials: "same-origin",
    ...options,
    headers: {
      ...(options.headers || {}),
      ...(method === "POST" ? csrfHeaders() : {}),
    },
  });
  if (response.status === 401) {
    window.location.assign("/login");
    throw new Error("Anmeldung erforderlich");
  }
  return response;
}

async function loadCards() {
  cardsRoot.setAttribute("aria-busy", "true");
  try {
    const response = await apiFetch("/api/review-queue", { headers: { Accept: "application/json" } });
    if (!response.ok) throw new Error(`Status ${response.status}`);
    const payload = await response.json();
    currentCards = payload.cards;
    readyCount.textContent = payload.cards.filter((card) => card.can_approve ?? (card.ready && !card.approved && card.status === "READY_FOR_REVIEW")).length;
    targetDate.textContent = payload.dates?.length
      ? payload.dates.map(value => new Intl.DateTimeFormat("de-DE", { day: "2-digit", month: "2-digit" }).format(new Date(`${value}T12:00:00`))).join(" / ")
      : "keine";
    renderCards();
  } catch (error) {
    cardsRoot.innerHTML = `<div class="error">Die Freigabepakete konnten nicht geladen werden. ${escapeHtml(error.message)}</div>`;
  } finally {
    cardsRoot.setAttribute("aria-busy", "false");
  }
}

function requestDecisionNote(action) {
  const overlay = document.querySelector("#decision-dialog");
  const note = document.querySelector("#decision-note");
  document.querySelector("#decision-title").textContent = action === "change" ? "Paket ändern" : "Paket ablehnen";
  document.querySelector("#decision-copy").textContent = action === "change"
    ? "Notiere kurz, was angepasst werden soll."
    : "Notiere kurz, warum dieses Paket nicht verwendet werden soll.";
  document.querySelector("[data-decision-save]").textContent = action === "change"
    ? "Änderung speichern"
    : "Ablehnung speichern";
  note.value = "";
  overlay.hidden = false;
  overlay.setAttribute("aria-hidden", "false");
  document.body.classList.add("decision-open");
  window.setTimeout(() => note.focus(), 0);
  return new Promise((resolve) => {
    pendingDecision = { resolve };
  });
}

function closeDecisionDialog(value = null) {
  if (!pendingDecision) return;
  const overlay = document.querySelector("#decision-dialog");
  overlay.hidden = true;
  overlay.setAttribute("aria-hidden", "true");
  document.body.classList.remove("decision-open");
  const resolve = pendingDecision.resolve;
  pendingDecision = null;
  resolve(value);
}

async function ownerDecision(contentId, action) {
  let note = "";
  const button = document.querySelector(`[data-action="${action}"][data-content-id="${contentId}"]`);
  if (["live-authorize", "rearm-preflight"].includes(action)) {
    if (button?.dataset.sensitiveConfirm !== "armed") {
      button.dataset.sensitiveConfirm = "armed";
      button.textContent = action === "live-authorize"
        ? "ZWEITER KLICK: LIVE-FREIGABE BESTÄTIGEN"
        : "ZWEITER KLICK: PREFLIGHT ERNEUT AKTIVIEREN";
      window.setTimeout(() => {
        if (button.dataset.sensitiveConfirm === "armed") {
          delete button.dataset.sensitiveConfirm;
          button.textContent = action === "live-authorize"
            ? "LIVE-VERSAND SEPARAT FREIGEBEN · postet noch nicht"
            : "SICHEREN PREFLIGHT ERNEUT PRÜFEN · postet noch nicht";
        }
      }, 8000);
      return { cancelled: true };
    }
    delete button.dataset.sensitiveConfirm;
  } else if (!["approve", "reschedule"].includes(action)) {
    const response = await requestDecisionNote(action);
    if (response === null) return { cancelled: true };
    note = response;
  }
  if (button) {
    button.disabled = true;
    button.textContent = "Wird gespeichert …";
  }
  const response = await apiFetch(`/api/reviews/${contentId}/${action}`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ note }),
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || "Freigabe fehlgeschlagen");
  await loadCards();
  const messages = {
    approve: "Freigabe gespeichert · Creator Ops hält den Termin lokal",
    reschedule: "Neuer Termin lokal übernommen · kein Live-Post",
    "live-authorize": "Separate Live-Autorisierung gespeichert · noch nichts veröffentlicht",
    "rearm-preflight": "Sicherer Preflight erneut aktiviert · noch nichts veröffentlicht",
  };
  showToast(messages[action] || "Owner-Entscheidung lokal gespeichert");
  return payload;
}

cardsRoot.addEventListener("click", async (event) => {
  const preview = event.target.closest("[data-large-preview]");
  if (preview) {
    const card = currentCards.find(item => item.content_id === Number(preview.dataset.largePreview));
    if (card) openLargePreview(card);
    return;
  }
  const reveal = event.target.closest("[data-reveal]");
  if (reveal) {
    reveal.closest(".creator-card")?.classList.add("privacy-revealed");
    reveal.remove();
    return;
  }
  const button = event.target.closest("[data-action]");
  if (!button) return;
  try {
    await ownerDecision(Number(button.dataset.contentId), button.dataset.action);
  } catch (error) {
    showToast(error.message);
    await loadCards();
  }
});

document.querySelector("#decision-form").addEventListener("submit", (event) => {
  event.preventDefault();
  closeDecisionDialog(document.querySelector("#decision-note").value.trim());
});
document.querySelector("[data-decision-cancel]").addEventListener("click", () => closeDecisionDialog());
document.querySelector("#decision-dialog").addEventListener("click", (event) => {
  if (event.target.id === "decision-dialog") closeDecisionDialog();
});

document.querySelector("#large-preview").addEventListener("click", (event) => {
  if (event.target.matches("[data-preview-close]") || event.target.id === "large-preview") return closeLargePreview();
  if (!previewState) return;
  if (event.target.matches("[data-preview-prev]")) previewState.index = (previewState.index - 1 + previewState.slides.length) % previewState.slides.length;
  if (event.target.matches("[data-preview-next]")) previewState.index = (previewState.index + 1) % previewState.slides.length;
  renderLargePreview();
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && pendingDecision) {
    closeDecisionDialog();
    return;
  }
  if (!previewState) return;
  if (event.key === "Escape") closeLargePreview();
  if (event.key === "ArrowLeft") { previewState.index = (previewState.index - 1 + previewState.slides.length) % previewState.slides.length; renderLargePreview(); }
  if (event.key === "ArrowRight") { previewState.index = (previewState.index + 1) % previewState.slides.length; renderLargePreview(); }
});

stageFilters.forEach((button) => button.addEventListener("click", () => {
  activeStage = button.dataset.stageFilter;
  stageFilters.forEach((candidate) => candidate.classList.toggle("active", candidate === button));
  renderCards();
}));

function installLogoutButton() {
  if (!cookieValue("creator_ops_csrf")) return;
  const button = document.createElement("button");
  button.type = "button";
  button.textContent = "Abmelden";
  button.style.cssText = "position:fixed;right:16px;bottom:16px;z-index:50;border:1px solid rgba(60,50,40,.15);background:rgba(255,255,255,.92);padding:9px 12px;border-radius:999px;box-shadow:0 8px 24px rgba(0,0,0,.08);cursor:pointer;font:inherit;";
  button.addEventListener("click", async () => {
    await apiFetch("/logout", { method: "POST" });
    window.location.assign("/login");
  });
  document.body.appendChild(button);
}

async function registerWebMcp() {
  const context = document.modelContext;
  if (!context?.registerTool) return;
  try {
    await context.registerTool({
      name: "approve_creator_draft",
      title: "Creator-Draft freigeben",
      description: "Gibt genau ein sichtbares, review-bereites Creator-Paket frei und legt nur einen lokalen Mock-Draft an.",
      inputSchema: {
        type: "object",
        properties: { content_id: { type: "integer" } },
        required: ["content_id"],
        additionalProperties: false,
      },
      annotations: { readOnlyHint: false, untrustedContentHint: false },
      async execute(input) {
        const id = Number(input?.content_id);
        if (!Number.isInteger(id) || !currentCards.some((card) => card.content_id === id)) {
          throw new Error("Unbekannte Content-ID");
        }
        return ownerDecision(id, "approve");
      },
    });
  } catch (error) {
    console.warn("WebMCP konnte nicht registriert werden", error);
  }
}

installLogoutButton();
loadCards().then(registerWebMcp);
