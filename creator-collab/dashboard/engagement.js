const root=document.querySelector('#engagement');const esc=v=>String(v??'—').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
function card(x){const evidence=x.reaction_data_known?`${esc(x.analytics_event_count)} Analytics-Snapshot(s), ${esc(x.known_comment_count)} Kommentar(e) als Summe`:'Keine echten Analytics oder Reaktionen vorhanden';return `<article class="archive-card engagement-card"><div><p class="card-kicker">${esc(x.display_name)} · ${esc(x.action_type)}</p><h2>${esc(x.prompt)}</h2><p>${esc(x.safety_note)}</p><p><b>Evidenz:</b> ${evidence}</p><p><b>Antwortentwürfe:</b> ${x.comment_texts_available?esc(x.reply_drafts.join(' · ')):'Keine – Kommentartexte sind nicht vorhanden.'}</p><p><b>Handlung:</b> ${esc(x.action_recommendation)}</p><p><b>Folgeidee:</b> ${esc(x.followup_idea)}</p><p><b>Nicht vor:</b> ${esc(x.not_before)}</p><a class="text-link" href="${esc(x.target_ref)}" target="_blank" rel="noopener">Bezug ansehen</a></div></article>`}
const messagesView=new URLSearchParams(location.search).get('view')==='messages';
document.querySelector('h1').textContent=messagesView?'Nachrichten':'Kommentare';
document.querySelector('.intro').textContent=messagesView?'Dein Bereich für Instagram-Direktnachrichten.':'Kommentartexte und vorhandene Hinweise zu deinen Beiträgen.';
if(messagesView){
  root.innerHTML='<section class="platform-landing"><p class="nav-label">INSTAGRAM · DIREKTNACHRICHTEN</p><h2>Noch keine Nachrichten verfügbar.</h2><p>Instagram-Direktnachrichten werden aktuell nicht synchronisiert. Es liegen keine echten Nachrichtentexte vor. Sobald sie verfügbar sind, können sie hier bearbeitet werden.</p><span class="connection-state">Postfach nicht verbunden</span></section>';
}else{
  fetch('/api/engagement?status=PROPOSED').then(r=>{if(!r.ok)throw new Error('Kommentare konnten nicht geladen werden');return r.json();}).then(p=>{
    root.innerHTML='<div class="comment-evidence-note"><b>Kommentartexte noch nicht verbunden</b><p>Vorhandene Summen und Aufgaben zu deinen Posts stehen unten. Sie sind keine eingelesenen Kommentare.</p></div>'+(p.items?.length?p.items.map(card).join(''):'<div class="empty">Noch keine Kommentartexte oder offenen Hinweise vorhanden.</div>');
  }).catch(e=>{root.innerHTML=`<div class="error">${esc(e.message)}</div>`});
}
