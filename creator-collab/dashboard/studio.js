/* Shared navigation for the existing ZippoWorkz pages. */
(() => {
  const main = document.querySelector("main.shell");
  if (!main) return;
  document.body.classList.add("studio");
  const query = new URLSearchParams(location.search);
  const area = query.get("area");
  const path = location.pathname;
  const escape = value => String(value ?? "").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;");
  const icons = {
    grid:'<rect x="3" y="3" width="7" height="7" rx="2"/><rect x="14" y="3" width="7" height="7" rx="2"/><rect x="3" y="14" width="7" height="7" rx="2"/><rect x="14" y="14" width="7" height="7" rx="2"/>',
    instagram:'<rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="12" cy="12" r="4"/><path d="M17.5 6.5h.01"/>',
    work:'<rect x="3" y="7" width="18" height="14" rx="3"/><path d="M8 7V4h8v3M3 12l9 3 9-3"/>',
    meta:'<path d="M3 16C0 5 7 3 12 12s11 8 9-1C19 2 14 7 12 12S4 24 3 16Z"/>',
    heart:'<path d="M20 5c-4-4-8 1-8 1S8 1 4 5c-5 5 8 15 8 15S25 10 20 5Z"/>',
    link:'<path d="m10 14 4-4M8 16l-2 2a4 4 0 0 1-6-6l6-6a4 4 0 0 1 6 0M16 8l2-2a4 4 0 0 1 6 6l-6 6a4 4 0 0 1-6 0" transform="translate(1 0) scale(.9)"/>',
    lock:'<rect x="5" y="10" width="14" height="11" rx="3"/><path d="M8 10V6a4 4 0 0 1 8 0v4M12 14v3"/>',
    settings:'<circle cx="12" cy="12" r="4"/><path d="M12 2v3m0 14v3M2 12h3m14 0h3M5 5l2 2m10 10 2 2M5 19l2-2M17 7l2-2"/>',
    arrow:'<path d="m9 5 7 7-7 7"/>',
  };
  const icon = name => '<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round">'+icons[name]+'</svg>';
  const emblem = '<svg viewBox="0 0 52 52" aria-hidden="true"><defs><linearGradient id="zw-blue" x2=".7" y2="1"><stop stop-color="#7fcdff"/><stop offset="1" stop-color="#2765f5"/></linearGradient></defs><path d="M11 10h25c9 0 9 8 3 13L20 37h18l5 6H17c-10 0-12-8-4-14l18-13H16Z" fill="url(#zw-blue)"/><path d="m20 37 9-7h7l7 13H24Z" fill="#416bff" opacity=".65"/></svg>';
  const activeInstagram = !area && ["/","/stories","/engagement","/archive","/analytics","/collections","/top3"].includes(path);
  const groups = [
    {name:"Instagram", key:"instagram", selected:activeInstagram, children:[
      ["/","Beiträge"],["/stories","Stories"],["/engagement?view=comments","Kommentare"],["/engagement?view=messages","Nachrichten"],["/archive","Veröffentlicht"],["/analytics","Insights"],["/collections","Mediathek"]]},
    {name:"Fiverr",key:"work",selected:["/revenue","/offer"].includes(path),children:[["/revenue","Übersicht & Umsatz"],["/offer","Angebot & Gig"]]},
    {name:"Meta",key:"meta",selected:area==="meta",children:[["/?area=meta","Verbindung"],["/control","Betrieb & Freigaben"]]},
    {name:"Fanbase",key:"heart",selected:area==="fanbase",children:[["/?area=fanbase","Übersicht"]]},
    {name:"Linktree",key:"link",selected:area==="linktree",children:[["/?area=linktree","Links & Profil"]]},
    {name:"18+ Bereich",key:"lock",selected:area==="adult",children:[["/?area=adult","Privater Bereich"]]},
  ];
  const selectedHref = location.pathname + location.search;
  const sidebar = document.createElement("aside");
  sidebar.className = "studio-sidebar";
  sidebar.id = "studio-sidebar";
  sidebar.innerHTML = '<a class="studio-brand" href="/" aria-label="ZippoWorkz Startseite"><span class="studio-emblem">'+emblem+'</span><span>Zippo<span class="brand-blue">Workz</span><small>CREATOR WORKSPACE</small></span></a>'+
    '<div class="studio-workspace"><span class="workspace-avatar">Z</span><span>Mein Workspace<small>Leona & Mara</small></span><span class="workspace-local">Lokal</span></div>'+
    '<nav aria-label="Plattformen"><p class="nav-label">WORKSPACE</p><a class="sidebar-overview" href="/">'+icon("grid")+'<span>Übersicht</span></a><p class="nav-label">PLATTFORMEN</p>'+
    groups.map(group=>'<details class="platform-group" '+(group.selected?'open':'')+'><summary>'+icon(group.key)+'<span>'+group.name+'</span>'+icon("arrow")+'</summary><div class="platform-children">'+group.children.map(([href,label])=>{
      const active=href===selectedHref || (path==="/engagement" && !location.search && label==="Kommentare");
      return '<a href="'+href+'"'+(active?' class="selected" aria-current="page"':'')+'>'+label+'</a>';
    }).join("")+'</div></details>').join("")+'</nav>'+
    '<div class="sidebar-bottom"><a href="/control">'+icon("settings")+'Einstellungen & Betrieb</a><span class="workspace-signature"><i></i> ZippoWorkz · auf diesem Gerät</span></div>';
  document.body.prepend(sidebar);
  const bar = document.createElement("div");
  bar.className="studio-toolbar";
  const section= area ? ({meta:"Meta",fanbase:"Fanbase",linktree:"Linktree",adult:"18+ Bereich"}[area] || "Workspace") : (activeInstagram ? "Instagram" : ["/revenue","/offer"].includes(path) ? "Fiverr" : "Workspace");
  const labels={"/":"Beiträge","/stories":"Stories","/archive":"Veröffentlicht","/analytics":"Insights","/collections":"Mediathek","/top3":"Top 3","/revenue":"Übersicht & Umsatz","/offer":"Angebot & Gig","/control":"Betrieb","/engagement":query.get("view")==="messages"?"Nachrichten":"Kommentare"};
  bar.innerHTML='<button type="button" class="sidebar-toggle" aria-label="Navigation öffnen" aria-controls="studio-sidebar" aria-expanded="false">'+icon("grid")+'</button><div class="studio-breadcrumb">'+escape(section)+'<span>/</span><b>'+escape(area?"Übersicht":labels[path]||"Übersicht")+'</b></div><div class="toolbar-right"><span class="toolbar-status"><i></i> Lokal</span><span class="owner-avatar">Z</span></div>';
  main.prepend(bar);
  const mobileBrand=document.createElement('a');
  mobileBrand.className='studio-mobile-brand';
  mobileBrand.href='/';
  mobileBrand.innerHTML='Zippo<span>Workz</span>';
  bar.querySelector('.sidebar-toggle').after(mobileBrand);
  const toggle=bar.querySelector("button");
  toggle.addEventListener("click",()=>{
    const open=document.body.classList.toggle("sidebar-open");
    toggle.setAttribute("aria-expanded",String(open));
  });
  document.addEventListener("keydown",event=>{
    if(event.key==="Escape"){document.body.classList.remove("sidebar-open");toggle.setAttribute("aria-expanded","false");}
  });
  const title=main.querySelector("h1");
  if(title) title.textContent=labels[path]||"Workspace";
  if(path==="/" && !area){
    document.body.classList.add("studio-feed");
    main.querySelector(".intro").textContent="Gute Inhalte. Dein Stil. Alles an einem Ort.";
    const focus=document.createElement("section");
    focus.className="studio-focus";
    focus.innerHTML='<div class="focus-copy"><p class="nav-label">DEINE CREATOR</p><h2>Die nächste Story <br>beginnt hier.</h2><p>Leona & Mara · Content prüfen, planen und vorbereiten.</p><div class="creator-chips"><span><img src="/assets/leona-voss-avatar.png" alt="">Leona Voss</span><span><img src="/assets/mara-field-avatar.png" alt="">Mara Field</span></div></div><div class="mix-panel"><div class="mix-head"><span>Instagram Content-Mix</span><span class="mix-target">Ziel</span></div><div class="mix-numbers"><div><strong>70<span>%</span></strong><small>Alltag & Persönlichkeit</small></div><div><strong>30<span>%</span></strong><small>Sexy & sinnlich</small></div></div><div class="mix-bar" role="img" aria-label="Ziel: 70 Prozent Alltag und 30 Prozent sexy, sinnlicher SFW-Teaser"><i></i><i></i></div><p>Glamour, Flirt & erotische Andeutung – öffentlich SFW.<br>Explizite Inhalte gehören in den getrennten 18+ Bereich.</p></div>';
    main.querySelector(".topbar").after(focus);
    main.querySelector("#today-heading").textContent="Bereit für deinen Blick";
    main.querySelector('#today-heading').previousElementSibling.textContent="CONTENT-RESERVE";
    main.querySelector('[data-stage-filter="TEASER"]').textContent="Sexy / Teaser · 30 %";
    main.querySelector('[data-stage-filter="ALLTAG"]').textContent="Alltag · 70 %";
    main.querySelector('[data-stage-filter="ADULT_18"]').hidden=true;
    const feed=main.querySelector('#cards').closest('.workspace-section');
    const audit=main.querySelector('.operations-audit');
    feed.after(audit);
    const platformStatus=main.querySelector('#platform-status').closest('.workspace-section');
    main.querySelector('footer').before(platformStatus);
  }
  if(area){
    document.body.classList.add("studio-platform");
    Array.from(main.children).forEach(child=>{if(child!==bar)child.hidden=true;});
    const data={
      meta:["Meta","Verbindungen an einem Ort.","Die persönliche Meta-Verifizierung ist zurückgestellt. Den vorhandenen Betriebsstatus und die Freigaben findest du unter Betrieb.","/control","Betriebsstatus ansehen","Verifizierung offen"],
      fanbase:["Fanbase","Raum für deine Community.","Für Fanbase ist hier noch keine Verbindung eingerichtet. Sobald ein konkretes Profil angebunden ist, finden Inhalte und Ergebnisse in diesem Bereich ihren Platz.",null,null,"Nicht verbunden"],
      linktree:["Linktree","Ein Einstieg für alle deine Links.","Hier ist noch kein Linktree-Profil hinterlegt. Es werden deshalb keine Profil-Links oder Klickzahlen angezeigt.",null,null,"Nicht verbunden"],
      adult:["18+ Bereich","Ein eigener, privater Content-Bereich.","Explizite Inhalte bleiben außerhalb des öffentlichen Instagram-Feeds. Der 30-%-Anteil im Instagram-Mix steht für SFW-Glamour und sinnliche Teaser. Eine 18+-Plattform ist derzeit nicht verbunden.",null,null,"Getrennt · nicht verbunden"],
    }[area];
    const panel=document.createElement("section");panel.className="platform-landing";
    panel.innerHTML=data?'<span class="platform-large-icon">'+icon(area==="adult"?"lock":area==="fanbase"?"heart":area==="linktree"?"link":"meta")+'</span><p class="nav-label">'+data[0]+'</p><h1>'+data[1]+'</h1><p>'+data[2]+'</p><span class="connection-state">'+data[5]+'</span>'+(data[3]?'<a class="studio-primary-link" href="'+data[3]+'">'+data[4]+'</a>':''):'<h1>Bereich nicht gefunden</h1><a href="/">Zurück zu Instagram</a>';
    main.append(panel);
  }
})();
