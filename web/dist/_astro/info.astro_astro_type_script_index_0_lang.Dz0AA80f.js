import{g as a,o as r,$ as t,e,t as o}from"./client.Cjj18tIK.js";const c=new Set(["REGLAS","RULES","REGRAS","PREMIUM"]);a().then(s=>{const i=r(s).filter(n=>!c.has(n.title));if(!i.length){t("info").innerHTML=`<p class="empty">${e(o("noInfo"))}</p>`;return}t("info").innerHTML=i.map(n=>`
      <h2 class="label">${e(n.title)}</h2>
      <ul style="list-style:none;margin-bottom:1.75rem">${n.lines.map(l=>`<li class="muted" style="padding:.2rem 0">${e(l)}</li>`).join("")}</ul>`).join("")}).catch(()=>{t("info").innerHTML=`<p class="empty">${e(o("serverDown"))}</p>`});
