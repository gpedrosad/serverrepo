import{g as h,$ as e,e as t,t as n}from"./client.Cjj18tIK.js";const y=JSON.parse(document.getElementById("spell-info")?.textContent||"{}");h().then(o=>{const a=o.spells?.sections||[];if(!a.length){e("spells").innerHTML=`<p class="empty">${t(n("noSpells"))}</p>`;return}const[d,c,r,p,i]=n("spellCols"),m=n("kinds"),$=s=>{const l=y[s.words];return`
              <tr class="${l?"spell-row":""}"><td><strong>${t(s.name)}</strong></td><td class="mono muted">${t(s.words)}</td><td class="n key">${s.mana}</td>
              <td class="n">${s.maglv}</td><td class="faint wide-only">${t(m[s.kind]||s.kind)}</td></tr>`+(l?`<tr class="spell-desc"><td colspan="5">${t(l)}</td></tr>`:"")};e("spells").innerHTML=a.map((s,l)=>`
      <details class="fold"${l===0?" open":""}>
        <summary><strong>${t(s.label)}</strong> <span class="faint small">${t(n("spellsCount",{n:s.count}))}</span></summary>
        <div class="fold-body table-scroll">
          <table class="spells-table">
            <thead><tr><th>${d}</th><th>${c}</th><th class="n">${r}</th><th class="n">${p}</th><th class="wide-only">${i}</th></tr></thead>
            <tbody>${(s.spells||[]).map($).join("")}</tbody>
          </table>
        </div>
      </details>`).join("")}).catch(()=>{e("spells").innerHTML=`<p class="empty">${t(n("serverDown"))}</p>`});
