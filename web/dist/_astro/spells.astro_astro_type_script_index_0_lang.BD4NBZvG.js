import{g as h,$ as a,e as s,t as l}from"./client.PbclRlB1.js";h().then(d=>{const e=d.spells?.sections||[];if(!e.length){a("spells").innerHTML=`<p class="empty">${s(l("noSpells"))}</p>`;return}const[o,c,i,p,r]=l("spellCols"),m=l("kinds");a("spells").innerHTML=e.map((n,$)=>`
      <details class="fold"${$===0?" open":""}>
        <summary><strong>${s(n.label)}</strong> <span class="faint small">${s(l("spellsCount",{n:n.count}))}</span></summary>
        <div class="fold-body table-scroll">
          <table>
            <thead><tr><th>${o}</th><th>${c}</th><th class="n">${i}</th><th class="n">${p}</th><th class="wide-only">${r}</th></tr></thead>
            <tbody>${(n.spells||[]).map(t=>`
              <tr><td>${s(t.name)}</td><td class="mono muted">${s(t.words)}</td><td class="n key">${t.mana}</td>
              <td class="n">${t.maglv}</td><td class="faint wide-only">${s(m[t.kind]||t.kind)}</td></tr>`).join("")}</tbody>
          </table>
        </div>
      </details>`).join("")}).catch(()=>{a("spells").innerHTML=`<p class="empty">${s(l("serverDown"))}</p>`});
