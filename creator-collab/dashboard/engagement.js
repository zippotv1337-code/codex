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

function botHealthTemplate(health) {
  const jobs = health.jobs || {};
  const provider = health.provider || {};
  const state = (value, ready = 'bereit') => value === true ? ready : value === false ? 'nicht bereit' : 'unbekannt';
  const badge = (label, value, tone) => `<span class="dm-health-badge ${tone}"><b>${esc(label)}</b> ${esc(value)}</span>`;
  const readinessTone = value => value === true ? 'config' : value === false ? 'bad' : 'warn';
  const providerStatus = {
    LAST_SYNCED: 'Zuletzt synchronisiert', ERROR: 'Fehler beim letzten Sync',
    NOT_CONFIGURED: 'Nicht konfiguriert', PARTIAL_CONFIG: 'Persona-Konfiguration unvollständig',
    UNKNOWN: 'Noch nicht verifiziert',
  }[provider.status] || provider.status || 'Unbekannt';
  const providerTone = provider.status === 'LAST_SYNCED' ? 'ok' : provider.status === 'ERROR' ? 'bad' : 'warn';
  const personaCards = (health.personas || []).map(item => {
    const syncTone = item.sync_status === 'SYNCED' ? 'ok' : item.sync_status === 'ERROR' ? 'bad' : 'warn';
    return `<div class="dm-health-persona">
      <h3>${esc(item.persona === 'leona-voss' ? 'Leona' : item.persona === 'mara-field' ? 'Mara' : item.persona)}</h3>
      <p>${esc(item.account || 'Konto unbekannt')}</p>
      <div class="dm-health-badges">
        ${badge('Read', state(item.read_ready, 'konfiguriert'), readinessTone(item.read_ready))}
        ${badge('Write', state(item.write_ready, 'konfiguriert'), readinessTone(item.write_ready))}
        ${badge('Sync', item.sync_status || 'UNKNOWN', syncTone)}
      </div>
      <small>Letzter erfolgreicher Provider-Read: ${esc(item.last_sync_success_at || 'noch keiner')}</small>
      ${item.last_sync_error ? `<small class="dm-health-error">Letzter Sync-Fehler: ${esc(item.last_sync_error)}</small>` : ''}
    </div>`;
  }).join('');
  const action = health.last_action;
  const sent = health.last_successful_message;
  const error = health.last_error;
  const worker = health.worker || {};
  return `<section class="dm-bot-health" aria-label="Bot-Status">
    <div class="dm-health-heading"><div><p class="nav-label">BOT HEALTH · LIVE BACKEND</p><h2>Instagram-DM-Bot</h2></div>
      ${badge('Bot', health.bot_online === 'WEB_RUNTIME_ONLINE' ? 'Web-Laufzeit erreichbar' : 'Status unbekannt', health.bot_online === 'WEB_RUNTIME_ONLINE' ? 'config' : 'warn')}
    </div>
    <div class="dm-health-badges">
      ${badge('DM mode', health.dm_mode || 'UNKNOWN', 'config')}
      ${badge('Send', state(health.send_enabled, 'aktiv'), health.send_enabled === true ? 'ok' : health.send_enabled === false ? 'bad' : 'warn')}
      ${badge('Auto-Reply', state(health.auto_reply_enabled, 'aktiv'), health.auto_reply_enabled === true ? 'ok' : health.auto_reply_enabled === false ? 'bad' : 'warn')}
      ${badge('Provider', `${provider.name || 'unbekannt'} · ${providerStatus}`, providerTone)}
      ${badge('DB', health.database || 'unbekannt', health.database === 'ok' ? 'ok' : 'bad')}
      ${badge('Queue', health.queue || 'unbekannt', health.queue === 'DB_OUTBOX_READABLE' ? 'ok' : 'warn')}
    </div>
    <div class="dm-health-personas">${personaCards || '<p>Keine Persona-Readiness verfügbar.</p>'}</div>
    <div class="dm-health-jobs">
      <div><strong>${esc(jobs.active ?? '—')}</strong><span>Aktive Jobs</span></div>
      <div><strong>${esc(jobs.retry ?? '—')}</strong><span>Retry-Jobs</span></div>
      <div><strong>${esc(jobs.blocked ?? '—')}</strong><span>BLOCKED / Abgleich</span></div>
      <div><strong>${esc(jobs.needs_owner ?? '—')}</strong><span>NEEDS_OWNER</span></div>
      <div><strong>${esc(jobs.failed ?? '—')}</strong><span>FAILED</span></div>
    </div>
    <div class="dm-health-detail">
      <p><b>Letzte Bot-Aktion:</b> ${action ? `${esc(action.action)} · ${esc(action.result)} · ${esc(action.persona)} · ${esc(action.timestamp)}${action.job_id ? ` · Job ${esc(action.job_id)}` : ''}` : 'Noch keine erfasst'}</p>
      <p><b>Letzte erfolgreiche Nachricht:</b> ${sent ? `${esc(sent.persona)} · ${esc(sent.timestamp)} · Job ${esc(sent.job_id)} (${esc(sent.status)})` : 'Noch keine bestätigt'}</p>
      <p><b>Letzter Fehler:</b> ${error ? `${esc(error.persona)} · ${esc(error.timestamp)} · ${esc(error.code)}` : 'Keiner gespeichert'}</p>
      <p><b>DM-Ausführung:</b> ${worker.mode === 'INLINE_WEBHOOK_AND_ON_DEMAND' && worker.dedicated_worker === false ? 'Inline per Webhook oder manuellem Sync · kein eigener DM-Worker' : 'Unbekannt'}</p>
      <small>Read/Write zeigen die Provider-Konfiguration. Ein erfolgreicher Sync bestätigt den letzten Read; ein Live-Write wird erst durch eine gesendete Nachricht belegt. Stand: ${esc(health.checked_at)}</small>
    </div>
  </section>`;
}

async function loadBotHealth() {
  const node = document.querySelector('#dm-bot-health');
  if (!node) return;
  try {
    const response = await fetch('/api/instagram-dm/health', {headers: {Accept: 'application/json'}});
    if (!response.ok) throw new Error('Bot-Status nicht erreichbar');
    node.innerHTML = botHealthTemplate(await response.json());
  } catch (_) {
    node.innerHTML = '<section class="dm-bot-health"><div class="dm-health-heading"><h2>Instagram-DM-Bot</h2><span class="dm-health-badge bad"><b>Bot</b> STATUS NICHT VERFÜGBAR</span></div><p>Der Live-Status konnte nicht geladen werden. Verbindung und Backend prüfen.</p></section>';
  }
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
  ? 'Instagram-DMs, sichere Antworten und Sales-Signale in einem Arbeitsbereich.'
  : 'Kommentartexte und vorhandene Hinweise zu deinen Beiträgen.';

if (messagesView) {
  document.querySelector('.mode').innerHTML = '<span></span> DM-STATUS WIRD GELADEN';
  fetch('/api/instagram-dm', {headers: {Accept: 'application/json'}})
    .then(response => {
      if (!response.ok) throw new Error('DM-Daten konnten nicht geladen werden');
      return response.json();
    })
    .then(payload => {
      const counts = payload.counts || {};
      const cards = payload.items?.length
        ? payload.items.map(dmCard).join('')
        : '<div class="empty">Noch keine lokal erfassten Inbound-DMs.</div>';
      const readiness = payload.provider || {};
      document.querySelector('.mode').innerHTML = `<span></span> ${esc(payload.mode || 'DM-STATUS UNBEKANNT')}`;
      root.innerHTML = `<div id="dm-bot-health" aria-live="polite">Bot-Status wird geladen …</div>
      <section class="dm-readonly-banner">
        <p class="nav-label">INSTAGRAM · MESSAGES & SALES</p>
        <h2>${payload.send_enabled ? 'AUTONOMER SICHERER ANTWORTPFAD' : 'PROVIDER NOCH NICHT SCHREIBBEREIT'}</h2>
        <p>Webhook-Credentials: ${readiness.webhook_ready ? 'vorhanden' : 'nicht vollständig konfiguriert'} · Auto-Reply: ${payload.send_enabled ? 'aktiv' : 'inaktiv'}.</p>
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
      loadBotHealth();
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
  setInterval(loadBotHealth, 30_000);
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
