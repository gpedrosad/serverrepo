import{g as s,$ as n,e as t}from"./client.C1Gwyfwj.js";s().then(l=>{const e=(l.otinfo||[]).filter(i=>i.title!=="REGLAS"&&i.title!=="PREMIUM");if(!e.length){n("info").innerHTML='<p class="empty">Sin información publicada.</p>';return}n("info").innerHTML=e.map(i=>`
      <h2 class="label">${t(i.title)}</h2>
      <ul style="list-style:none;margin-bottom:1.75rem">${i.lines.map(o=>`<li class="muted" style="padding:.2rem 0">${t(o)}</li>`).join("")}</ul>`).join("")}).catch(()=>{n("info").innerHTML='<p class="empty">Sin conexión con el servidor.</p>'});
