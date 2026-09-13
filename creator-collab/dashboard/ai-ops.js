const esc = value => String(value ?? '—').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const when = value => value ? new Date(value).toLocaleString('de-DE') : 'Noch kein Signal';
const badge = status => `<span class="ops-badge" data-status="${esc(status)}">${esc(status)}</span>`;
const roles = {codex:['Codex','Integration · Review · Entscheidungen'],local_ai:['Local AI','Begrenzte lokale Routinearbeit'],vps:['VPS Watcher','Leichter externer Wächter · noch nicht verbunden']};
let pending = false;
async function api(path, method='GET') {
  const csrf = document.cookie.split(';').map(v=>v.trim()).find(v=>v.startsWith('creator_ops_csrf='))?.split('=').slice(1).join('=') || '';
  const response = await fetch(path,{method,credentials:'same-origin',headers:method==='POST'?{'X-CSRF-Token':decodeURIComponent(csrf)}:{}});
  if(response.status===401){location.assign('/login');throw new Error('Anmeldung erforderlich');}
  const data = await response.json();
  if(!response.ok) throw new Error(data.error || 'Status konnte nicht geladen werden');
  return data;
}
function render(data) {
  document.querySelector('#ops-agents').innerHTML=data.agents.map(a=>`<article class="ops-agent">${badge(a.status)}<h2>${esc(roles[a.id][0])}</h2><p>${esc(roles[a.id][1])}</p><dl><dt>Aktuelle Aufgabe</dt><dd>${esc(a.task || 'Keine aktive Aufgabe')}</dd><dt>Heartbeat</dt><dd>${esc(when(a.heartbeat))}</dd><dt>Letzter Erfolg</dt><dd>${esc(when(a.last_success))}</dd><dt>Letzter Hinweis</dt><dd>${esc(a.last_error || 'Keine Meldung')}</dd></dl></article>`).join('');
  document.querySelector('#ops-queue').innerHTML=data.tasks.map(t=>`<article class="ops-task"><span class="ops-priority">${esc(t.priority)}</span><div><b>${esc(t.title)}</b><p>${esc(t.agent)} · ${esc(t.project)} · Voraussetzung: ${esc(t.dependencies.join(', ') || 'keine')} · Versuch ${esc(t.attempts || 0)}/2</p><p>Quelle: ${esc(t.source)} · Owner-Gate: ${t.owner_gate?'ja':'nein'} · Schritt: ${esc(t.checkpoint || 'noch nicht begonnen')}</p>${t.result?`<details><summary>Ergebnis ansehen</summary><pre>${esc(JSON.stringify(t.result,null,2))}</pre></details>`:''}</div>${badge(t.status)}</article>`).join('');
  document.querySelector('#ops-progress').textContent=`${data.tasks.filter(t=>t.status==='DONE').length} / ${data.tasks.length} erledigt`;
  const notice=document.querySelector('#ops-notice');notice.hidden=!data.data_notice;notice.textContent=data.data_notice || '';
  document.querySelector('#ops-source').textContent=`${data.sync.status} · ${data.sync.reason} · ${data.sync.source_commit || 'Archiv ohne verifizierten Git-HEAD'}\n${data.sync.source_fingerprint || ''}`;
  document.querySelector('#ops-handoff').textContent=data.handoff;
  document.querySelector('#ops-pause').textContent=data.pause_note+' Besitzer-Aktivität pausiert automatisch; nach 30 Sekunden Ruhe geht ein laufender Worker weiter.';
  document.querySelector('#ops-updated').textContent=`Geprüft: ${new Date().toLocaleTimeString('de-DE')} · Steuerung: ${data.control}`;
}
async function load() {try {render(await api('/api/ai-ops'));}catch(error){document.querySelector('#ops-feedback').textContent=error.message;}}
document.querySelector('.ops-buttons').addEventListener('click',async event=>{
  const button=event.target.closest('[data-command]');if(!button||pending)return;
  pending=true;document.querySelectorAll('[data-command]').forEach(b=>b.disabled=true);
  try{
    render(await api(`/api/ai-ops/${button.dataset.command}`,'POST'));
    if(button.dataset.command==='resume') await api('/api/ai-ops/start','POST');
    document.querySelector('#ops-feedback').textContent={start:'Start angefordert. Der lokale Worker läuft im Hintergrund – deshalb öffnet sich kein PowerShell-Fenster. Status und Ergebnis erscheinen hier.',pause:'Pause angefordert. Der laufende sichere Schritt wird zuerst abgeschlossen.',resume:'Fortsetzung am gespeicherten Schritt angefordert.',stop:'Beenden angefordert. Queue und Ergebnisse bleiben erhalten.'}[button.dataset.command];
    await load();
  }catch(error){document.querySelector('#ops-feedback').textContent=error.message;}
  finally{pending=false;document.querySelectorAll('[data-command]').forEach(b=>b.disabled=false);}
});
load().then(()=>{document.querySelector('#ops-feedback').textContent='Live-Status · Aktualisierung alle 10 Sekunden. Kein Agent wird als verbunden erfunden.';});
setInterval(()=>{if(!document.hidden&&!pending)load();},10000);
