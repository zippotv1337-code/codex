const root = document.querySelector('#analytics-root');
const metricFields = [
  ['reach', 'Reach'], ['views', 'Views'], ['likes', 'Likes'], ['comments', 'Kommentare'],
  ['shares', 'Shares'], ['saves', 'Saves'], ['profile_visits', 'Profilbesuche'],
  ['follows', 'Follows'], ['link_clicks', 'Link-Klicks'],
];
const esc = value => String(value ?? '—').replaceAll('&', '&amp;').replaceAll('<', '&lt;')
  .replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&#39;');
const fmt = value => value == null ? 'UNKNOWN' : String(value);
const csrf = () => (document.cookie.match(/(?:^|;\s*)creator_ops_csrf=([^;]+)/) || [])[1];

function metricRow(metrics) {
  return `<div class="metric-row">${metricFields.map(([key, label]) =>
    `<span>${label} <b>${fmt(metrics[key])}</b></span>`).join('')}</div>`;
}

function windowCard(publication, window) {
  const canCapture = window.status === 'DUE';
  return `<section class="analytics-window">
    <div class="analytics-window-head"><b>${window.window_hours}h</b>
      <span class="status-badge ${esc(window.status.toLowerCase())}">${esc(window.status)}</span></div>
    <small>${window.captured_at ? esc(window.captured_at) : canCapture ? 'Werte jetzt aus Instagram Insights übertragen' : 'Noch nicht fällig'}</small>
    ${metricRow(window.metrics)}
    ${canCapture ? captureForm(publication, window) : ''}
  </section>`;
}

function captureForm(publication, window) {
  return `<details class="analytics-capture"><summary>Echte ${window.window_hours}h-Werte eintragen</summary>
    <form data-analytics-capture="${publication.id}" data-window="${window.window_hours}">
      <p>Nur sichtbare Instagram-Insights übertragen. Leere Felder bleiben UNKNOWN; mindestens ein echter Wert ist nötig.</p>
      <div class="analytics-input-grid">${metricFields.map(([key, label]) =>
        `<label>${label}<input type="number" min="0" inputmode="numeric" name="${key}"></label>`).join('')}</div>
      <label>Notiz (optional)<textarea name="note" maxlength="500" placeholder="z. B. Insight-Fenster manuell abgelesen"></textarea></label>
      <button type="submit">Echte Werte speichern</button>
    </form>
  </details>`;
}

function personaCards(personas) {
  if (!personas.length) return '<div class="empty">Noch keine echten Veröffentlichungen für den Vergleich.</div>';
  return personas.map(persona => `<article class="analytics-persona-card">
    <p class="card-kicker">${esc(persona.persona)}</p>
    <h2>${persona.publications} echte Veröffentlichung${persona.publications === 1 ? '' : 'en'}</h2>
    <p>${persona.captured_publications} mit mindestens einem echten Snapshot.</p>
    ${metricRow(persona.metrics)}
  </article>`).join('');
}

function leaderboard(items, label) {
  if (!items.length) return `<p class="muted">${label}: UNKNOWN — noch keine ausreichenden echten Werte.</p>`;
  return `<ol class="analytics-ranking">${items.map(item => `<li><b>${esc(item.persona)}</b> · ${esc(item.title)}
    <span>Score ${esc(item.score)} · ${esc(item.window_hours)}h</span></li>`).join('')}</ol>`;
}

function pattern(label, pattern) {
  return `<li><b>${label}:</b> ${pattern ? `${esc(pattern.value)} · ${esc(pattern.sample_size)} echte Posts` : 'UNKNOWN'}</li>`;
}

function learningPanel(learning) {
  return `<section class="control-panel analytics-learning">
    <p class="card-kicker">Learning · echte Signale</p>
    <h2>${esc(learning.status)}</h2><p>${esc(learning.reason)}</p>
    <div class="analytics-learning-grid"><div><h3>Top 7 Tage</h3>${leaderboard(learning.leaderboards.last_7_days, 'Letzte 7 Tage')}</div>
    <div><h3>Top 30 Tage</h3>${leaderboard(learning.leaderboards.last_30_days, 'Letzte 30 Tage')}</div></div>
    <h3>Muster</h3><ul class="analytics-patterns">${pattern('Format', learning.patterns.format)}${pattern('Thema', learning.patterns.theme)}${pattern('Hook', learning.patterns.hook)}${pattern('Postingzeit', learning.patterns.posting_time)}</ul>
    <h3>Nächster kleiner Schritt</h3><ul class="analytics-patterns">${learning.recommendations.map(item => `<li><b>${esc(item.decision)}:</b> ${esc(item.reason)}</li>`).join('')}</ul>
  </section>`;
}

function render(payload) {
  const instagram = payload.instagram;
  const fiverr = payload.fiverr;
  root.innerHTML = `<section class="revenue-summary">
    <div><small>ECHTE POSTS</small><strong>${instagram.published_count}</strong><span>${instagram.captured_windows} Fenster erfasst</span></div>
    <div><small>FÄLLIGE FENSTER</small><strong>${instagram.due_windows}</strong><span>${instagram.unknown_until_owner_import} bleiben UNKNOWN</span></div>
    <div><small>FIVERR</small><strong>${esc(fiverr.status)}</strong><span>keine erfundenen Werte</span></div>
  </section>
  <section class="analytics-persona-grid">${personaCards(instagram.by_persona)}</section>
  ${learningPanel(instagram.learning)}
  <section class="analytics-list">${instagram.publications.length ? instagram.publications.map(publication => `<article class="control-panel analytics-publication">
    <p class="card-kicker">${esc(publication.persona)} · ${esc(publication.format)} · ${esc(publication.published_at)}</p>
    <h2>${esc(publication.title)}</h2>
    ${publication.external_url ? `<a class="text-link" href="${esc(publication.external_url)}" target="_blank" rel="noopener">Instagram-Post öffnen</a>` : ''}
    <div class="analytics-windows">${publication.windows.map(window => windowCard(publication, window)).join('')}</div>
  </article>`).join('') : '<div class="empty">Keine echten Veröffentlichungen gefunden.</div>'}</section>
  <section class="control-panel"><p class="card-kicker">Fiverr / Revenue</p>
    <div class="metric-row"><span>Real <b>${Number(fiverr.real_revenue_eur).toFixed(2)} €</b></span><span>Dry Run <b>${Number(fiverr.mock_revenue_eur).toFixed(2)} €</b></span><span>Events <b>${fiverr.events.length}</b></span></div>
    <p>${esc(fiverr.data_policy)}</p></section>`;
}

async function load() {
  const response = await fetch('/api/analytics', {headers: {Accept: 'application/json'}});
  if (!response.ok) throw new Error('Analytics konnten nicht geladen werden.');
  render(await response.json());
}

root.addEventListener('submit', async event => {
  const form = event.target;
  if (!form.matches('[data-analytics-capture]')) return;
  event.preventDefault();
  const button = form.querySelector('[type="submit"]');
  button.disabled = true;
  const body = new FormData(form);
  body.set('window_hours', form.dataset.window);
  try {
    const response = await fetch(`/api/analytics/${form.dataset.analyticsCapture}/capture`, {
      method: 'POST', headers: {...(csrf() ? {'X-CSRF-Token': decodeURIComponent(csrf())} : {})}, body,
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || 'Analytics konnten nicht gespeichert werden.');
    await load();
  } catch (error) {
    button.disabled = false;
    const notice = document.createElement('p');
    notice.className = 'error'; notice.textContent = error.message;
    form.prepend(notice);
  }
});

load().catch(error => { root.innerHTML = `<div class="error">${esc(error.message)}</div>`; });
