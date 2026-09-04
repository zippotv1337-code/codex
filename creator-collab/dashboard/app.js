const cardsRoot = document.querySelector("#cards");
const readyCount = document.querySelector("#ready-count");
const targetDate = document.querySelector("#target-date");
const toast = document.querySelector("#toast");
let currentCards = [];

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
  if (card.approved || card.status === "OWNER_APPROVED") return { key: "approved", label: "Freigegeben" };
  if (card.status === "SCHEDULED") return { key: "scheduled", label: "Geplant" };
  if (card.status === "READY_FOR_REVIEW") return { key: "ready", label: "Review bereit" };
  return { key: "pending", label: card.status.replaceAll("_", " ") };
}

function cardTemplate(card) {
  const assets = card.assets.map((asset) => `
    <div class="asset ${asset.top_pick ? "top" : ""} ${asset.preview_url ? "has-preview" : ""}" ${asset.preview_url ? `style="background-image:url('${escapeHtml(asset.preview_url)}')"` : ""} aria-label="${escapeHtml(asset.label)}, Qualität ${asset.quality} Prozent${asset.top_pick ? ", Top Pick" : ""}">
      <span class="quality">${asset.quality}%</span>
      ${asset.top_pick ? '<span class="asset-badge">TOP</span>' : ""}
      <span>${escapeHtml(asset.label)}</span>
    </div>`).join("");
  const approved = card.approved;
  const status = statusMeta(card);
  return `
    <article class="creator-card" data-persona="${escapeHtml(card.creator_slug)}">
      <div class="card-head">
        <div class="identity">
          <img class="avatar" src="/assets/${escapeHtml(card.creator_slug)}-avatar.png" alt="KI-generiertes Profilbild von ${escapeHtml(card.display_name)}" />
          <div>
            <p class="card-kicker">Morgen · ${escapeHtml(card.prime_time)} Uhr</p>
            <h2>${escapeHtml(card.display_name)}</h2>
            <p class="series">${escapeHtml(card.series)}</p>
          </div>
        </div>
        <span class="status-pill status-${status.key}">${escapeHtml(status.label)}</span>
      </div>
      <div class="asset-summary">
        <span><strong>${card.asset_count}</strong><small>Bilder vorhanden</small></span>
        <span><strong>Top ${card.top_pick_count}</strong><small>empfohlen</small></span>
      </div>
      <div class="asset-strip">${assets}</div>
      <div class="checklist">
        ${check("Carousel", card.checks.carousel, "5 Slides vorbereitet")}
        ${check("Caption", card.checks.caption, "Text vollständig")}
        ${check("Musik", card.checks.music, card.audio)}
        ${check("Prime Time", card.checks.prime_time, `${card.prime_time} Uhr · Berlin`)}
      </div>
      <details class="caption-preview">
        <summary>Caption ansehen</summary>
        <p>${escapeHtml(card.caption)}</p>
      </details>
      <button class="approve-button" data-approve="${card.content_id}" ${(!card.ready || approved) ? "disabled" : ""}>
        ${approved ? `Freigegeben · ${escapeHtml(card.prime_time)} Uhr` : `${escapeHtml(card.display_name)} freigeben`}
      </button>
    </article>`;
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
    const response = await apiFetch("/api/reviews", { headers: { Accept: "application/json" } });
    if (!response.ok) throw new Error(`Status ${response.status}`);
    const payload = await response.json();
    currentCards = payload.cards;
    readyCount.textContent = payload.cards.filter((card) => card.ready && !card.approved).length;
    targetDate.textContent = new Intl.DateTimeFormat("de-DE", { day: "2-digit", month: "2-digit" })
      .format(new Date(`${payload.date}T12:00:00`));
    cardsRoot.innerHTML = payload.cards.length
      ? payload.cards.map(cardTemplate).join("")
      : '<div class="error">Für morgen sind noch keine Freigabepakete vorhanden.</div>';
  } catch (error) {
    cardsRoot.innerHTML = `<div class="error">Die Freigabepakete konnten nicht geladen werden. ${escapeHtml(error.message)}</div>`;
  } finally {
    cardsRoot.setAttribute("aria-busy", "false");
  }
}

async function approveContent(contentId) {
  const button = document.querySelector(`[data-approve="${contentId}"]`);
  if (button) {
    button.disabled = true;
    button.textContent = "Wird freigegeben …";
  }
  const response = await apiFetch(`/api/reviews/${contentId}/approve`, { method: "POST" });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || "Freigabe fehlgeschlagen");
  await loadCards();
  showToast("Freigabe gespeichert · lokaler Mock-Draft angelegt");
  return payload;
}

cardsRoot.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-approve]");
  if (!button) return;
  try {
    await approveContent(Number(button.dataset.approve));
  } catch (error) {
    showToast(error.message);
    await loadCards();
  }
});

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
        return approveContent(id);
      },
    });
  } catch (error) {
    console.warn("WebMCP konnte nicht registriert werden", error);
  }
}

installLogoutButton();
loadCards().then(registerWebMcp);
