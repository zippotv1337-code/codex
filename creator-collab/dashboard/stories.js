const root = document.querySelector('#stories');
const notice = document.querySelector('#story-notice');
const esc = value => String(value ?? '').replaceAll('&', '&amp;').replaceAll('<', '&lt;')
  .replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&#39;');
const labels = {READY_FOR_OWNER_REVIEW:'Review offen', APPROVED:'Lokal freigegeben',
  CHANGE_REQUESTED:'Änderung angefordert', REJECTED:'Abgelehnt', PAUSED:'Pausiert',
  LOCAL_PLANNED:'Lokal vorgemerkt', NEEDS_SCHEDULE:'Zeit fehlt'};
const kinds = {NORMAL:'Normal', TEASER:'Teaser', POLL:'Poll', COMMUNITY:'Frage', FRAGE:'Frage', LINK:'Link', BTS:'BTS'};
let packages = [];
let reviewReady = false;

function localInput(value) {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  return new Date(date - date.getTimezoneOffset() * 60000).toISOString().slice(0,16);
}
function frame(item) {
  return `<div class="story-frame">${item.asset.preview_url
    ? `<img class="story-media" src="${esc(item.asset.preview_url)}" alt="${esc(kinds[item.kind] || item.kind)} · ${esc(item.asset.pose_slot)}">`
    : '<span class="story-no-preview">NO PREVIEW ASSET</span>'}
    <span class="story-kind">${esc(kinds[item.kind] || item.kind)}</span>
    <div class="story-overlay"><b>${esc(item.copy)}</b><small>${esc(item.interaction)}</small>
    ${item.link ? `<small>${esc(item.link)}</small>` : ''}</div></div>`;
}
function frameEditor(item, index) {
  return `<fieldset class="story-frame-editor"><legend>Slide ${index + 1}</legend>
    <label>Story-Typ<select name="kind-${index}">${Object.entries(kinds).map(([value,label]) =>
      `<option value="${value}" ${item.kind === value ? 'selected' : ''}>${label}</option>`).join('')}</select></label>
    <label>Text<textarea name="copy-${index}" maxlength="1000" required>${esc(item.copy)}</textarea></label>
    <label>Poll / Frage / Interaktion<textarea name="interaction-${index}" maxlength="1000">${esc(item.interaction)}</textarea></label>
    <label>Link (optional, HTTPS)<input name="link-${index}" type="url" maxlength="1000" value="${esc(item.link || '')}"></label></fieldset>`;
}
function card(item) {
  const disabled = item.can_review ? '' : 'disabled';
  const mayPlan = item.can_review && ['APPROVED','LOCAL_PLANNED','NEEDS_SCHEDULE'].includes(item.status);
  const color = ['PAUSED','REJECTED'].includes(item.status) ? 'rejected' : item.status === 'APPROVED' ? 'approved' : 'ready';
  return `<article id="story-${item.content_id}" class="story-card" data-persona="${esc(item.creator_slug)}">
    <header><p class="card-kicker">${esc(item.display_name)} · Reserve vom ${esc(item.date)}</p>
    <h2>${esc(item.series)}</h2><span class="status-pill status-${color}">${esc(labels[item.status] || item.status)}</span></header>
    <div class="story-frames">${item.frames.map(frame).join('')}</div>
    <dl class="posting-details"><div><dt>CTA</dt><dd>${esc(item.cta)}</dd></div>
    <div><dt>Geplante Zeit</dt><dd>${esc(item.planned_at ? new Date(item.planned_at).toLocaleString('de-DE') : 'Noch nicht geplant')}</dd></div>
    <div><dt>Highlight</dt><dd>${esc(item.highlight || 'Keine Zuordnung')}</dd></div></dl>
    <p class="qa-warning">${item.can_review ? 'Lokale Vorbereitung; kein automatischer Versand aus dieser Ansicht.' : 'Echte Vorschauen fehlen. Freigabe und Planung bleiben gesperrt.'}
    ${item.published_assets_excluded} veröffentlichte Assets ausgeschlossen. Native KI-Kennzeichnung beim Versand prüfen.</p>
    <details class="story-edit"><summary>Bearbeiten · Texte und Story-Typen</summary>
      <form data-story-edit="${item.content_id}" class="story-editor">
      ${item.frames.map(frameEditor).join('')}
      <label>CTA<input name="cta" maxlength="500" value="${esc(item.cta)}"></label>
      <label>Highlight (optional)<input name="highlight" maxlength="80" value="${esc(item.highlight || '')}"></label>
      <button type="submit">Änderungen speichern</button></form></details>
    <div class="decision-actions story-actions">
      <button type="button" data-story-action="approve" data-content-id="${item.content_id}" ${disabled}>APPROVE</button>
      <button type="button" data-story-action="change" data-content-id="${item.content_id}">CHANGE</button>
      <button type="button" data-story-action="reject" data-content-id="${item.content_id}">REJECT</button>
      <button type="button" data-story-action="pause" data-content-id="${item.content_id}">NICHT POSTEN / PAUSIEREN</button>
    </div>
    <form data-story-plan="${item.content_id}" class="story-plan">
      <label>Termin (Zeitzone dieses Geräts)<input type="datetime-local" name="planned_at" required value="${esc(localInput(item.planned_at))}"></label>
      <button type="submit" ${mayPlan ? '' : 'disabled'}>PLANEN · lokal</button>
      ${mayPlan ? '' : '<small>Zum Planen zuerst lokal freigeben.</small>'}</form>
  </article>`;
}
async function loadStories() {
  const response = await fetch('/api/stories', {headers:{Accept:'application/json'}});
  if (!response.ok) throw new Error('Story-Reserve nicht erreichbar. Bitte Anmeldung und Server prüfen.');
  const result = await response.json();
  packages = result.items || [];
  reviewReady = result.review_schema === 'story-review-v1';
  root.innerHTML = packages.length ? packages.map(card).join('') : '<div class="empty">Keine unveröffentlichte Story-Reserve vorhanden.</div>';
  if (!reviewReady) {
    notice.textContent = 'Update gespeichert, Server-Neustart erforderlich. Vorschauen sind verfügbar; Änderungen bleiben bis dahin gesperrt.';
    root.querySelectorAll('button, input, textarea, select').forEach(element => {element.disabled = true;});
  }
}
async function save(id, action, fields = {}) {
  if (!reviewReady) throw new Error('Bitte zuerst den ZippoWorkz-Server neu starten.');
  const csrf = (document.cookie.match(/(?:^|;\s*)creator_ops_csrf=([^;]+)/) || [])[1];
  const response = await fetch(`/api/stories/${id}/${action}`, {method:'POST',
    headers:{'Content-Type':'application/x-www-form-urlencoded', ...(csrf ? {'X-CSRF-Token':decodeURIComponent(csrf)} : {})},
    body:new URLSearchParams({fields:JSON.stringify(fields)})});
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || 'Speichern fehlgeschlagen');
  await loadStories();
  notice.textContent = 'Gespeichert. Der Status bleibt auch nach dem Neuladen erhalten. Kein Live-Post ausgelöst.';
}
root.addEventListener('click', async event => {
  const button = event.target.closest('[data-story-action]');
  if (!button) return;
  button.disabled = true;
  save(Number(button.dataset.contentId), button.dataset.storyAction)
    .catch(error => {notice.textContent = error.message; button.disabled = false;});
});
root.addEventListener('submit', async event => {
  const form = event.target;
  if (!form.matches('[data-story-edit], [data-story-plan]')) return;
  event.preventDefault();
  const button = form.querySelector('[type="submit"]');
  button.disabled = true;
  const data = new FormData(form);
  try {
    if (form.dataset.storyEdit) {
      const id = Number(form.dataset.storyEdit);
      const item = packages.find(item => item.content_id === id);
      await save(id, 'edit', {cta:data.get('cta'), highlight:data.get('highlight'), frames:item.frames.map((_, i) =>
        ({kind:data.get(`kind-${i}`), copy:data.get(`copy-${i}`), interaction:data.get(`interaction-${i}`), link:data.get(`link-${i}`)}))});
    } else {
      await save(Number(form.dataset.storyPlan), 'plan', {planned_at:new Date(data.get('planned_at')).toISOString()});
    }
  } catch (error) {notice.textContent = error.message; button.disabled = false;}
});
loadStories().then(() => {
  if (/^#story-\d+$/.test(location.hash)) document.querySelector(location.hash)?.scrollIntoView();
}).catch(error => {notice.textContent = error.message; root.innerHTML = '<div class="error">Story-Reserve konnte nicht geladen werden.</div>';});
root.addEventListener('error', event => {
  if (event.target.tagName === 'IMG') {
    const message = document.createElement('span');
    message.className = 'story-no-preview'; message.textContent = 'NO PREVIEW ASSET';
    event.target.replaceWith(message);
  }
}, true);
