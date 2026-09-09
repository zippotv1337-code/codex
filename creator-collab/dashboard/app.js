const cardsRoot = document.querySelector("#cards");
const readyCount = document.querySelector("#ready-count");
const targetDate = document.querySelector("#target-date");
const activeSummary = document.querySelector("#active-summary");
const attentionRoot = document.querySelector("#needs-attention");
const attentionSummary = document.querySelector("#attention-summary");
const plannedRoot = document.querySelector("#planned-summary");
const storyOpsRoot = document.querySelector("#story-ops");
const auditRoot = document.querySelector("#operations-audit");
const toast = document.querySelector("#toast");
const stageFilters = document.querySelectorAll("[data-stage-filter]");
let currentCards = [];
let currentAttention = [];
let activeStage = "ALL";
let previewState = null;
let pendingDecision = null;
let postingKitState = null;

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
  const canPrepareNativePost = approved && card.schedule_status !== "PUBLISHED";
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
            <p class="series">${escapeHtml(card.series)} · <span class="format-badge">${escapeHtml((card.format || "carousel").toUpperCase())}</span></p>
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
      <details class="caption-preview">
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
      ${canPrepareNativePost ? `<button class="posting-kit-button" type="button" data-open-posting-kit="${card.content_id}">POSTING-PAKET ÖFFNEN · für vorhandenen Composer</button>` : ""}
      ${canReschedule ? `<button type="button" class="reschedule-button" data-action="reschedule" data-content-id="${card.content_id}">VORGESCHLAGENEN TERMIN ÜBERNEHMEN · nur lokal</button>` : ""}
      ${canAuthorizeLive ? `<button type="button" class="live-authorize-button" data-action="live-authorize" data-content-id="${card.content_id}">LIVE-VERSAND SEPARAT FREIGEBEN · postet noch nicht</button>` : ""}
      ${canRearmPreflight ? `<button type="button" class="rearm-preflight-button" data-action="rearm-preflight" data-content-id="${card.content_id}">SICHEREN PREFLIGHT ERNEUT PRÜFEN · postet noch nicht</button>` : ""}
      ${card.live_publish_authorized ? '<p class="live-gate-status">Live-Versand für genau dieses Paket autorisiert · globale Meta-Gates bleiben maßgeblich</p>' : ""}
      <div class="decision-help"><b>APPROVE</b> nur lokale Queue · <b>LIVE-FREIGABE</b> separat · <b>CHANGE</b> Überarbeitung · <b>REJECT</b> Paket blockieren</div>
      <div class="decision-actions">
        <button type="button" class="approve-button" data-action="approve" data-content-id="${card.content_id}" ${canApprove ? "" : "disabled"}>${approved ? "Freigegeben" : "APPROVE"}</button>
        <button type="button" class="change-button" data-action="change" data-content-id="${card.content_id}">Bearbeiten / CHANGE</button>
        <button type="button" class="reject-button" data-action="reject" data-content-id="${card.content_id}">REJECT</button>
      </div>
    </article>`;
}

function attentionTemplate(card) {
  const status = statusMeta(card);
  const preview = card.assets.find(asset => asset.preview_url && !asset.excluded);
  const protectedPreview = card.privacy_blur || card.visibility_scope !== "PUBLIC_SFW";
  return `<article class="attention-card">
    <div class="attention-preview">${preview && !protectedPreview ? `<img src="${escapeHtml(preview.preview_url)}" alt="Vorschau ${escapeHtml(card.series)}" loading="lazy">` : '<span>NO PREVIEW ASSET<br>Keine öffentliche Vorschau</span>'}</div>
    <div><p class="card-kicker">${escapeHtml(card.creator_slug)} · ${escapeHtml(card.format || "carousel")}</p><h3>${escapeHtml(card.series)}</h3><p>${escapeHtml(card.attention_reason || "Prüfung erforderlich")}</p></div>
    <div class="attention-meta"><span class="status-pill status-${status.key}">${escapeHtml(status.label)}</span>${preview && !protectedPreview ? `<button type="button" data-large-preview="${card.content_id}">Vorschau</button>` : ''}<button type="button" class="change-button" data-action="change" data-content-id="${card.content_id}">Bearbeiten / CHANGE</button><button type="button" class="reject-button" data-action="reject" data-content-id="${card.content_id}">REJECT</button></div>
  </article>`;
}

function renderCards() {
  const visible = activeStage === "ALL"
    ? currentCards
    : currentCards.filter((card) => card.content_stage === activeStage);
  cardsRoot.innerHTML = visible.length
    ? visible.map(cardTemplate).join("")
    : '<div class="empty">Noch kein Paket in diesem Content-Bereich.</div>';
}

function renderAttention() {
  attentionRoot.innerHTML = currentAttention.length
    ? currentAttention.map(attentionTemplate).join("")
    : '<div class="empty">Keine offenen Aufmerksamkeitspunkte.</div>';
}

function renderPlanned() {
  const planned = currentCards.filter(card => ["LOCAL_SCHEDULED", "SCHEDULED", "NEEDS_RESCHEDULE_REVIEW"].includes(card.schedule_status));
  plannedRoot.innerHTML = planned.length
    ? planned.map(card => `<article class="planned-item"><span class="planned-dot" aria-hidden="true"></span><div><b>${escapeHtml(card.display_name)}</b><span>${escapeHtml(card.series)} · ${escapeHtml(card.format || "carousel")}</span></div><strong>${escapeHtml(card.planned_at || card.prime_time + " Uhr")}</strong></article>`).join("")
    : '<div class="empty">Keine lokalen Veröffentlichungen geplant.</div>';
}

function renderStoryOps(items) {
  if (!storyOpsRoot) return;
  const visible = items || [];
  storyOpsRoot.innerHTML = visible.length
    ? visible.map(item => `<article class="planned-item story-ops-item"><div class="attention-preview">${item.frames?.[0]?.asset?.preview_url ? `<img src="${escapeHtml(item.frames[0].asset.preview_url)}" alt="Story ${escapeHtml(item.series)}" loading="lazy">` : '<span>NO PREVIEW ASSET</span>'}</div><div><b>${escapeHtml(item.display_name)}</b><span>${escapeHtml(item.series)} · ${item.frames?.length || 0} Frames</span><span>${escapeHtml(item.date)} · ${escapeHtml(item.status)}${item.planned_at ? ` · ${escapeHtml(item.planned_at)}` : ''}</span></div><a class="text-link" href="/stories#story-${item.content_id}">Auswählen / Bearbeiten</a></article>`).join("")
    : '<div class="empty">Keine unveröffentlichte Story-Reserve vorhanden.</div>';
}

function renderAudit(audit) {
  if (!auditRoot) return;
  const primary = audit.next_actions?.[0] || {};
  const stats = [
    ["Review aktiv", audit.review?.active_count ?? 0],
    ["Needs Attention", audit.review?.needs_attention_count ?? 0],
    ["Story-Kits", audit.stories?.ready_package_count ?? 0],
    ["Analytics fällig", audit.analytics?.due_count ?? 0],
  ];
  auditRoot.innerHTML = `
    <article class="audit-primary">
      <span class="audit-priority">${escapeHtml(primary.priority || "OK")}</span>
      <div>
        <h3>${escapeHtml(primary.action || "Kein offener Schritt")}</h3>
        <p>${primary.blocked_by ? `Blocker: ${escapeHtml(primary.blocked_by)}` : "Lokal ohne Owner-Gate ausführbar."}</p>
      </div>
    </article>
    ${stats.map(([label, value]) => `<article class="audit-stat"><strong>${escapeHtml(value)}</strong><span>${escapeHtml(label)}</span></article>`).join("")}`;
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

function postText(card) {
  return [card.hook, card.caption, card.cta, card.hashtags.map((tag) => `#${String(tag).replace(/^#/, "")}`).join(" ")]
    .filter(Boolean)
    .join("\n\n");
}

function localDateTimeValue(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const offset = date.getTimezoneOffset() * 60_000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 16);
}

function openPostingKit(card) {
  const overlay = document.querySelector("#posting-kit-dialog");
  const selected = previewSlides(card);
  postingKitState = { card, selected };
  document.querySelector("#posting-kit-title").textContent = `${card.display_name} · Posting-Paket`;
  document.querySelector("#posting-kit-copy").textContent = `${card.series} · ${selected.length} ausgewählte Carousel-Slides. Der Composer bleibt vollständig in deiner Hand.`;
  document.querySelector("#posting-kit-assets").innerHTML = selected.map((asset, index) => `
    <label class="posting-kit-asset ${asset.preview_url ? "has-preview" : ""}" ${asset.preview_url ? `style="background-image:url('${escapeHtml(asset.preview_url)}')"` : ""}>
      <input name="asset_id" form="native-reconcile-form" type="checkbox" value="${asset.id}" checked />
      <span>TOP ${asset.top_pick_order || index + 1}</span>
      <small>${escapeHtml(poseLabels[asset.pose_slot] || asset.label)} · Bild ${asset.id}</small>
    </label>`).join("");
  document.querySelector('#native-reconcile-form [name="published_at"]').value = localDateTimeValue(card.planned_at);
  overlay.hidden = false;
  overlay.setAttribute("aria-hidden", "false");
  document.body.classList.add("posting-kit-open");
  document.querySelector("[data-posting-kit-close]").focus();
}

function closePostingKit() {
  const overlay = document.querySelector("#posting-kit-dialog");
  overlay.hidden = true;
  overlay.setAttribute("aria-hidden", "true");
  document.body.classList.remove("posting-kit-open");
  postingKitState = null;
}

async function copyPostingText(kind) {
  if (!postingKitState) return;
  const value = kind === "hashtags"
    ? postingKitState.card.hashtags.map((tag) => `#${String(tag).replace(/^#/, "")}`).join(" ")
    : postText(postingKitState.card);
  if (!navigator.clipboard?.writeText) throw new Error("Zwischenablage ist in diesem Browser nicht verfügbar");
  await navigator.clipboard.writeText(value);
  showToast(kind === "hashtags" ? "Hashtags kopiert" : "Caption kopiert");
}

async function reconcileNativePost(event) {
  event.preventDefault();
  if (!postingKitState) return;
  const values = new FormData(event.currentTarget);
  const publishedAt = String(values.get("published_at") || "");
  const parsed = new Date(publishedAt);
  if (Number.isNaN(parsed.getTime())) throw new Error("Bitte einen gültigen Veröffentlichungszeitpunkt angeben");
  values.set("published_at", parsed.toISOString());
  const response = await apiFetch(`/api/reviews/${postingKitState.card.content_id}/reconcile-native`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams(values),
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || "Live-Link konnte nicht gespeichert werden");
  closePostingKit();
  await loadCards();
  showToast("Sichtbarer Instagram-Post lokal bestätigt · keine Plattformaktion ausgelöst");
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
    currentCards = payload.active_cards || payload.cards || [];
    currentAttention = payload.needs_attention || [];
    readyCount.textContent = payload.cards.filter((card) => card.can_approve ?? (card.ready && !card.approved && card.status === "READY_FOR_REVIEW")).length;
    activeSummary.textContent = `${currentCards.length} aktiv`;
    attentionSummary.textContent = `${currentAttention.length} offen`;
    const dates = (payload.dates || []).slice().sort();
    targetDate.textContent = dates.length ? `${dates.length} Termine` : "Keine";
    targetDate.title = dates.map(value => new Intl.DateTimeFormat("de-DE", { day: "2-digit", month: "2-digit" }).format(new Date(`${value}T12:00:00`))).join(" · ");
    renderCards();
    renderAttention();
    renderPlanned();
    Promise.all([fetch('/api/health').then(r => r.json()), fetch('/api/external-readiness').then(r => {
      if (!r.ok) throw new Error('Status nicht erreichbar'); return r.json();
    })]).then(([health, readiness]) => {
      const identity = readiness.fiverr.identity_status === 'OWNER_REPORTED_VERIFIED'
        ? 'Verifizierung laut Owner erledigt · Gig zuletzt Entwurf, Live-Status offen'
        : 'Profil-/Live-Status prüfen';
      document.querySelector('#platform-status').innerHTML = `<article class="planned-item"><div><b>ZippoWorkz ${health.status === 'ok' ? 'erreichbar' : 'Status prüfen'}</b><span>Meta: ${readiness.meta.status === 'DEFERRED_OWNER_VERIFICATION' ? 'zurückgestellt · persönliche Verifizierung offen' : escapeHtml(readiness.meta.status)}</span><span>Fiverr: ${identity}</span></div><a class="text-link" href="/revenue">Fiverr / Revenue öffnen</a></article>`;
    }).catch(() => {document.querySelector('#platform-status').textContent = 'Betriebsstatus nicht erreichbar. Unter Betrieb / Status prüfen.';});
    fetch("/api/operations-audit", { headers: { Accept: "application/json" } })
      .then(response => response.ok ? response.json() : null)
      .then(data => data ? renderAudit(data) : null)
      .catch(() => {
        if (auditRoot) auditRoot.innerHTML = '<div class="error">Operations-Audit konnte nicht geladen werden.</div>';
      });
    fetch("/api/stories", { headers: { Accept: "application/json" } })
      .then(response => response.ok ? response.json() : { items: [] })
      .then(data => renderStoryOps(data.items))
      .catch(() => renderStoryOps([]));
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

async function handleCardAction(event) {
  const preview = event.target.closest("[data-large-preview]");
  if (preview) {
    const card = [...currentCards, ...currentAttention].find(item => item.content_id === Number(preview.dataset.largePreview));
    if (card) openLargePreview(card);
    return;
  }
  const postingKit = event.target.closest("[data-open-posting-kit]");
  if (postingKit) {
    const card = currentCards.find((item) => item.content_id === Number(postingKit.dataset.openPostingKit));
    if (card) openPostingKit(card);
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
}

cardsRoot.addEventListener("click", handleCardAction);
attentionRoot.addEventListener("click", handleCardAction);
for (const target of [attentionRoot, storyOpsRoot]) target.addEventListener('error', event => {
  if (event.target.tagName === 'IMG') {
    const fallback = document.createElement('span');
    fallback.textContent = 'NO PREVIEW ASSET';
    event.target.replaceWith(fallback);
  }
}, true);

document.querySelector("#decision-form").addEventListener("submit", (event) => {
  event.preventDefault();
  closeDecisionDialog(document.querySelector("#decision-note").value.trim());
});
document.querySelector("[data-decision-cancel]").addEventListener("click", () => closeDecisionDialog());
document.querySelector("#decision-dialog").addEventListener("click", (event) => {
  if (event.target.id === "decision-dialog") closeDecisionDialog();
});

document.querySelector("#posting-kit-dialog").addEventListener("click", (event) => {
  if (event.target.id === "posting-kit-dialog" || event.target.closest("[data-posting-kit-close]")) closePostingKit();
});
document.querySelector("#posting-kit-dialog").addEventListener("click", async (event) => {
  const copy = event.target.closest("[data-posting-copy]");
  if (!copy) return;
  try {
    await copyPostingText(copy.dataset.postingCopy);
  } catch (error) {
    showToast(error.message);
  }
});
document.querySelector("#native-reconcile-form").addEventListener("submit", async (event) => {
  try {
    await reconcileNativePost(event);
  } catch (error) {
    event.preventDefault();
    showToast(error.message);
  }
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
  if (event.key === "Escape" && postingKitState) {
    closePostingKit();
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
