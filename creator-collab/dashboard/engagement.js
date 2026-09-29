const root = document.querySelector('#engagement');
const esc = value => String(value ?? '—')
  .replaceAll('&', '&amp;')
  .replaceAll('<', '&lt;')
  .replaceAll('>', '&gt;')
  .replaceAll('"', '&quot;');

function commentCard(item) {
  const evidence = item.reaction_data_known
    ? `${esc(item.analytics_event_count)} Analytics-Snapshot(s), ${esc(item.known_comment_count)} Kommentar(e) als Summe`
    : 'Keine echten Analytics oder Reaktionen vorhanden';
  return `<article class="archive-card engagement-card"><div>
    <p class="card-kicker">${esc(item.display_name)} · ${esc(item.action_type)}</p>
    <h2>${esc(item.prompt)}</h2>
    <p>${esc(item.safety_note)}</p>
    <p><b>Evidenz:</b> ${evidence}</p>
    <p><b>Antwortentwürfe:</b> ${item.comment_texts_available ? esc(item.reply_drafts.join(' · ')) : 'Keine – Kommentartexte sind nicht vorhanden.'}</p>
    <p><b>Handlung:</b> ${esc(item.action_recommendation)}</p>
    <p><b>Folgeidee:</b> ${esc(item.followup_idea)}</p>
    <p><b>Nicht vor:</b> ${esc(item.not_before)}</p>
    <a class="text-link" href="${esc(item.target_ref)}" target="_blank" rel="noopener">Bezug ansehen</a>
  </div></article>`;
}

function dmCard(item) {
  const reason = item.handoff_reason
    ? `<p><b>Handoff-Grund:</b> ${esc(item.handoff_reason)}</p>`
    : '<p><b>Handoff:</b> nicht erforderlich</p>';
  return `<article class="archive-card engagement-card dm-card" data-status="${esc(item.status)}"><div>
    <p class="card-kicker">${esc(item.display_name)} · ${esc(item.persona)}</p>
    <h2>${esc(item.intent)}</h2>
    <p><span class="status-pill">${esc(item.status)}</span></p>
    ${reason}
    <p><b>Eingang:</b> ${esc(item.received_at)}</p>
  </div></article>`;
}

const messagesView = new URLSearchParams(location.search).get('view') === 'messages';
document.querySelector('h1').textContent = messagesView ? 'Nachrichten' : 'Kommentare';
document.querySelector('.intro').textContent = messagesView
  ? 'Eingehende Instagram-DMs lokal prüfen. Antworten und Versand sind in P0 vollständig deaktiviert.'
  : 'Kommentartexte und vorhandene Hinweise zu deinen Beiträgen.';

if (messagesView) {
  document.querySelector('.mode').innerHTML = '<span></span> SEND DISABLED · READ-ONLY P0';
  fetch('/api/instagram-dm', {headers: {Accept: 'application/json'}})
    .then(response => {
      if (!response.ok) throw new Error('DM-P0-Daten konnten nicht geladen werden');
      return response.json();
    })
    .then(payload => {
      const counts = payload.counts || {};
      const cards = payload.items?.length
        ? payload.items.map(dmCard).join('')
        : '<div class="empty">Noch keine lokal erfassten Inbound-DMs.</div>';
      root.innerHTML = `<section class="dm-readonly-banner">
        <p class="nav-label">INSTAGRAM · DIREKTNACHRICHTEN</p>
        <h2>SEND DISABLED / READ-ONLY P0</h2>
        <p>Keine Antwort-, Link-, Payment-, Preview- oder Delivery-Aktion ist in diesem Stand erreichbar.</p>
      </section>
      <section class="dm-summary" aria-label="DM-Übersicht">
        <div><strong>${esc(counts.open || 0)}</strong><span>Offen</span></div>
        <div><strong>${esc(counts.needs_human || 0)}</strong><span>Needs Human</span></div>
        <div><strong>${esc(counts.events || 0)}</strong><span>Inbound Events</span></div>
      </section>
      <section class="archive-grid">${cards}</section>`;
    })
    .catch(error => {
      root.innerHTML = `<div class="error">${esc(error.message)}</div>`;
    });
} else {
  fetch('/api/engagement?status=PROPOSED')
    .then(response => {
      if (!response.ok) throw new Error('Kommentare konnten nicht geladen werden');
      return response.json();
    })
    .then(payload => {
      root.innerHTML = '<div class="comment-evidence-note"><b>Kommentartexte noch nicht verbunden</b><p>Vorhandene Summen und Aufgaben zu deinen Posts stehen unten. Sie sind keine eingelesenen Kommentare.</p></div>'
        + (payload.items?.length ? payload.items.map(commentCard).join('') : '<div class="empty">Noch keine Kommentartexte oder offenen Hinweise vorhanden.</div>');
    })
    .catch(error => {
      root.innerHTML = `<div class="error">${esc(error.message)}</div>`;
    });
}
