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

function showToast(message) {
  toast.textContent = message;
  toast.classList.add("show");
  window.setTimeout(() => toast.classList.remove("show"), 2800);
}

function check(label, ok, detail) {
  return `
    <div class="check">
      <div class="check-title"><span>${escapeHtml(label)}</span><i aria-label="${ok ? "bereit" : "fehlt"}">${ok ? "✓" : "–"}</i></div>
      <small title="${escapeHtml(detail)}">${escapeHtml(detail)}</small>
    </div>`;
}

function cardTemplate(card) {
  const assets = card.assets.map((asset) => `
    <div class="asset ${asset.top_pick ? "top" : ""}" aria-label="${escapeHtml(asset.label)}, Qualität ${asset.quality} Prozent${asset.top_pick ? ", Top Pick" : ""}">
      <span class="quality">${asset.quality}%</span>
      ${asset.top_pick ? '<span class="asset-badge">TOP</span>' : ""}
      <span>${escapeHtml(asset.label)}</span>
    </div>`).join("");
  const approved = card.approved;
  return `
    <article class="creator-card" data-persona="${escapeHtml(card.creator_slug)}">
      <div class="card-head">
        <div>
          <p class="card-kicker">${escapeHtml(card.display_name)} · morgen</p>
          <h2>${escapeHtml(card.display_name)}</h2>
          <p class="series">${escapeHtml(card.series)}</p>
        </div>
        <span class="status-pill ${approved ? "approved" : ""}">${approved ? "Freigegeben" : "Review bereit"}</span>
      </div>
      <div class="asset-summary">
        <span><strong>${card.asset_count}</strong> Bilder vorhanden</span>
        <span><strong>${card.top_pick_count}</strong> empfohlen</span>
      </div>
      <div class="asset-strip">${assets}</div>
      <div class="checklist">
        ${check("Carousel", card.checks.carousel, "Instagram · 5 Slides")}
        ${check("Caption", card.checks.caption, "KI-Hinweis enthalten")}
        ${check("Musik", card.checks.music, card.audio)}
        ${check("Prime Time", card.checks.prime_time, `${card.prime_time} Uhr · Berlin`)}
      </div>
      <p class="caption-preview">${escapeHtml(card.caption)}</p>
      <button class="approve-button" data-approve="${card.content_id}" ${(!card.ready || approved) ? "disabled" : ""}>
        ${approved ? `Freigegeben · ${escapeHtml(card.prime_time)} Uhr` : "Freigeben"}
      </button>
    </article>`;
}

async function loadCards() {
  cardsRoot.setAttribute("aria-busy", "true");
  try {
    const response = await fetch("/api/reviews", { headers: { Accept: "application/json" } });
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
  const response = await fetch(`/api/reviews/${contentId}/approve`, { method: "POST" });
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

loadCards().then(registerWebMcp);
