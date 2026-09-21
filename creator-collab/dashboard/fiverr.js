const root = document.querySelector('#fiverr-root');
const esc = value => String(value ?? '—').replaceAll('&', '&amp;').replaceAll('<', '&lt;')
  .replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&#39;');
const metric = (label, value, note='') => `<div><small>${esc(label)}</small><strong>${esc(value)}</strong><span>${esc(note)}</span></div>`;

function gigCard(gig) {
  const metrics = gig.metrics || {};
  const packages = gig.packages || {};
  return `<article class="control-panel">
    <p class="card-kicker">${esc(gig.status)} · ${esc(gig.gig_key)}</p>
    <h2>${esc(gig.title)}</h2>
    <div class="metric-row"><span>Impressionen <b>${esc(metrics.impressions ?? 'UNKNOWN')}</b></span><span>Klicks <b>${esc(metrics.clicks ?? 'UNKNOWN')}</b></span><span>Orders <b>${esc(metrics.orders ?? 'UNKNOWN')}</b></span></div>
    <p>Basic <b>${esc(packages.basic_usd ?? 'UNKNOWN')} USD</b> · Standard <b>${esc(packages.standard_usd ?? 'UNKNOWN')} USD</b> · Premium <b>${esc(packages.premium_usd ?? 'UNKNOWN')} USD</b></p>
    ${gig.public_url ? `<a class="text-link" href="${esc(gig.public_url)}" target="_blank" rel="noopener">Öffentlichen Gig öffnen</a>` : '<p class="muted">Öffentliche Gig-URL noch nicht bestätigt.</p>'}
  </article>`;
}

function render(payload) {
  if (payload.status === 'NOT_CONFIGURED') {
    root.innerHTML = '<div class="empty">Fiverr ist noch nicht synchronisiert.</div>'; return;
  }
  root.innerHTML = `<section class="revenue-summary">
    ${metric('ACCOUNT', payload.status, '@'+payload.username)}
    ${metric('SESSION', payload.session_status, payload.write_provider)}
    ${metric('AKTIVE GIGS', payload.active_gig_count, 'letzter Sync '+(payload.last_successful_sync || 'UNKNOWN'))}
  </section>
  <section class="control-panel"><p class="card-kicker">Nächster Schritt</p><h2>${esc(payload.next_action)}</h2><p>Letzter Schreibtest: ${esc(payload.last_write_test)} · Letzter Gate: ${esc(payload.last_human_gate)}</p>${payload.last_error ? `<p class="error">${esc(payload.last_error)}</p>` : ''}</section>
  <section class="analytics-list">${payload.gigs.length ? payload.gigs.map(gigCard).join('') : '<div class="empty">Noch kein Gig-Snapshot.</div>'}</section>
  ${payload.human_gates.length ? `<section class="control-panel"><p class="card-kicker">FIVERR HUMAN GATE</p>${payload.human_gates.map(g => `<p><b>Seite:</b> ${esc(g.page_url)}<br><b>Aktion:</b> ${esc(g.action)}<br><b>Warum:</b> ${esc(g.reason)}<br><b>Danach:</b> ${esc(g.after_action)}<br><b>Kosten:</b> ${g.costs_money ? 'JA' : 'NEIN'}</p>`).join('')}</section>` : ''}`;
}

fetch('/api/fiverr', {headers:{Accept:'application/json'}}).then(async response => {
  const payload = await response.json(); if (!response.ok) throw new Error(payload.error || 'Fiverr-Status nicht verfügbar.'); return payload;
}).then(render).catch(error => { root.innerHTML = `<div class="error">${esc(error.message)}</div>`; });
