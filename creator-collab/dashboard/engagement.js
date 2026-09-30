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
  const amount = (value, currency) => value == null ? '—' : `${esc(value)} ${esc(currency || '')}`.trim();
  const actions = [];
  if (item.outbox_id && ['DRAFTED', 'OWNER_REVIEW'].includes(item.reply_status)) {
    actions.push(`<button class="secondary dm-action" data-action="approve" data-outbox="${esc(item.outbox_id)}">APPROVE</button>`);
    actions.push(`<button class="secondary dm-action" data-action="cancel" data-outbox="${esc(item.outbox_id)}">CANCEL</button>`);
  }
  if (item.outbox_id && item.reply_status === 'APPROVED') {
    actions.push(`<button class="secondary dm-action" data-action="dispatch" data-outbox="${esc(item.outbox_id)}">SEND</button>`);
  }
  if (item.outbox_id && ['SENT', 'RECONCILE_REQUIRED'].includes(item.reply_status)) {
    actions.push(`<button class="secondary dm-action" data-action="reconcile" data-outbox="${esc(item.outbox_id)}">RECONCILE</button>`);
  }
  return `<article class="archive-card engagement-card dm-card" data-status="${esc(item.status)}"><div>
    <p class="card-kicker">${esc(item.display_name)} · ${esc(item.persona)}</p>
    <h2>${esc(item.intent)}</h2>
    <p><span class="status-pill">${esc(item.status)}</span></p>
    ${reason}
    <p><b>Conversation:</b> ${esc(item.conversation_ref)}</p>
    <p><b>Letzter Kontakt:</b> ${esc(item.last_contact)}</p>
    <p><b>Provider:</b> ${item.provider_verified ? 'verifiziert' : 'lokaler Test/Import'}</p>
    <p><b>Antwort:</b> ${esc(item.reply_status || 'noch nicht angelegt')}</p>
    <p><b>Owner Review:</b> ${item.owner_review ? `JA · ${esc(item.owner_review_reason)}` : 'NEIN'}</p>
    <p><b>Sales Signal:</b> ${item.sales_signal ? `JA (${esc(item.sales_signal_count)})` : 'NEIN'}</p>
    <p><b>Offer/Product:</b> ${esc(item.known_offer)}</p>
    <p><b>Payment:</b> ${esc(item.payment_status)}</p>
    <p><b>Erwartet/offen:</b> ${amount(item.expected_open_amount, item.expected_currency)}</p>
    <p><b>Bestätigter Umsatz:</b> ${amount(item.confirmed_revenue, item.confirmed_currency)}</p>
    <p><b>Reconciliation:</b> ${esc(item.reconciliation_state)}</p>
    <p><b>Nächste Aktion:</b> ${esc(item.next_action)}</p>
    <div class="action-row">${actions.join('')}</div>
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
        <div><strong>${esc(counts.open_conversations || 0)}</strong><span>Open Conversations</span></div>
        <div><strong>${esc(counts.owner_reviews || 0)}</strong><span>Owner Reviews</span></div>
        <div><strong>${esc(counts.sales_signals || 0)}</strong><span>Sales-Signale</span></div>
        <div><strong>${esc(counts.replies_pending || 0)} / ${esc(counts.replies_sent || 0)} / ${esc(counts.replies_reconcile || 0)}</strong><span>Pending / Sent / Reconcile</span></div>
        <div><strong>${esc(counts.open_payments || 0)}</strong><span>Open Payments</span></div>
        <div><strong>${esc(counts.confirmed_dm_revenue ?? '—')}</strong><span>Confirmed DM Revenue</span></div>
        <div><strong>${esc(counts.failures_needs_human || 0)}</strong><span>Failures / Needs Human</span></div>
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
      document.querySelectorAll('.dm-action').forEach(button => {
        button.addEventListener('click', async () => {
          button.disabled = true;
          try {
            await postJson(`/api/instagram-dm/${button.dataset.outbox}/reply/${button.dataset.action}`);
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
