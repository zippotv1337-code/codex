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
    <p><b>Provider:</b> ${item.provider_verified ? 'verifiziert' : 'lokaler Test/Import'}</p>
    <p><b>Antwort:</b> ${esc(item.reply_status || 'noch nicht angelegt')}</p>
    ${item.outbox_id && ['ACKNOWLEDGED', 'UNKNOWN'].includes(item.reply_status)
      ? `<button class="secondary dm-reconcile" data-outbox="${esc(item.outbox_id)}">Provider-Status prüfen</button>`
      : ''}
  </div></article>`;
}

function cookie(name) {
  const prefix = `${name}=`;
  return document.cookie.split(';').map(value => value.trim())
    .find(value => value.startsWith(prefix))?.slice(prefix.length) || '';
}

async function postJson(url, payload = {}) {
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      'X-CSRF-Token': decodeURIComponent(cookie('creator_ops_csrf')),
    },
    body: JSON.stringify(payload),
  });
  const body = await response.json();
  if (!response.ok) throw new Error(body.error || 'Aktion fehlgeschlagen');
  return body;
}

const messagesView = new URLSearchParams(location.search).get('view') === 'messages';
document.querySelector('h1').textContent = messagesView ? 'Nachrichten' : 'Kommentare';
document.querySelector('.intro').textContent = messagesView
  ? 'Provider-verifizierte Instagram-DMs, sichere Antworten und Sales-Signale in einem Arbeitsbereich.'
  : 'Kommentartexte und vorhandene Hinweise zu deinen Beiträgen.';

if (messagesView) {
  document.querySelector('.mode').innerHTML = '<span></span> PROVIDER VERIFIED · P1';
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
      const readiness = payload.provider || {};
      root.innerHTML = `<section class="dm-readonly-banner">
        <p class="nav-label">INSTAGRAM · MESSAGES & SALES</p>
        <h2>${payload.send_enabled ? 'AUTONOMER SICHERER ANTWORTPFAD' : 'PROVIDER NOCH NICHT SCHREIBBEREIT'}</h2>
        <p>Webhook: ${readiness.webhook_ready ? 'bereit' : 'nicht vollständig konfiguriert'} · Auto-Reply: ${payload.send_enabled ? 'aktiv' : 'inaktiv'}.</p>
        <button id="dm-sync" class="secondary">Provider jetzt lesen</button>
      </section>
      <section class="dm-summary" aria-label="DM-Übersicht">
        <div><strong>${esc(counts.open || 0)}</strong><span>Offen</span></div>
        <div><strong>${esc(counts.needs_human || 0)}</strong><span>Needs Human</span></div>
        <div><strong>${esc(counts.delivered || 0)}</strong><span>Zugestellt</span></div>
        <div><strong>${esc(counts.custom_requests || 0)}</strong><span>Custom Requests</span></div>
        <div><strong>${esc(counts.sales_signals || 0)}</strong><span>Sales-Signale</span></div>
        <div><strong>${esc(counts.uncertain || 0)}</strong><span>Reconcile nötig</span></div>
      </section>
      <section class="archive-grid">${cards}</section>`;
      document.querySelector('#dm-sync')?.addEventListener('click', async event => {
        event.currentTarget.disabled = true;
        try {
          await postJson('/api/instagram-dm/sync');
          location.reload();
        } catch (error) {
          event.currentTarget.disabled = false;
          event.currentTarget.textContent = error.message;
        }
      });
      document.querySelectorAll('.dm-reconcile').forEach(button => {
        button.addEventListener('click', async () => {
          button.disabled = true;
          try {
            await postJson(`/api/instagram-dm/${button.dataset.outbox}/reply/reconcile`);
            location.reload();
          } catch (error) {
            button.disabled = false;
            button.textContent = error.message;
          }
        });
      });
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
