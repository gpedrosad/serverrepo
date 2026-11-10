import{g as d,$ as l,e as t}from"./client.C1Gwyfwj.js";d().then(n=>{const e=n.spells?.sections||[];if(!e.length){l("spells").innerHTML='<p class="empty">No hay datos de hechizos.</p>';return}l("spells").innerHTML=e.map((a,o)=>`
      <details class="fold"${o===0?" open":""}>
        <summary><strong>${t(a.label)}</strong> <span class="faint small">${a.count} hechizos</span></summary>
        <div class="fold-body table-scroll">
          <table>
            <thead><tr><th>Nombre</th><th>Palabras</th><th class="n">Mana</th><th class="n">ML</th><th class="wide-only">Tipo</th></tr></thead>
            <tbody>${(a.spells||[]).map(s=>`
              <tr><td>${t(s.name)}</td><td class="mono muted">${t(s.words)}</td><td class="n key">${s.mana}</td>
              <td class="n">${s.maglv}</td><td class="faint wide-only">${t(s.kind)}</td></tr>`).join("")}</tbody>
          </table>
        </div>
      </details>`).join("")}).catch(()=>{l("spells").innerHTML='<p class="empty">Sin conexión con el servidor.</p>'});
