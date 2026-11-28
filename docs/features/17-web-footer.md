# Web: footer

Al final de cada página de retro76.cl, wiki incluida. Componente `web/site/src/components/SiteFooter.astro`,
estilos en `web/site/src/styles/site.css` (bloque `footer`), textos en `web/site/src/i18n.js` (`footer`, en
español e inglés).

| Parte | Qué es |
|---|---|
| Franja de ítems | 14 sprites del juego en pixel art (Demon Helmet, MPA, Crimson Wand…), apagados; se iluminan con brillo dorado al pasar el mouse. Salen de `web/assets/wiki/items/<id>.png` (lista `RELICS` del componente) |
| Marca | logo y "Retro76" |
| Columnas | Jugar (Cuenta, Cliente, Premium, Bugs), Comunidad (Live, Top, Power, PK, Muertes), Wiki (Novedades, Wiki, Items, Quests, Reglas, Info, Spells) |

Desde el 27 nov 2026, para dejarlo simple, no lleva la frase bajo el logo, el estado del servidor (ya está en la
cabecera) ni la barra legal (©, aviso de servidor no oficial de CipSoft y "Arriba ↑").

Sin imágenes grandes ni JavaScript propio. `Base.astro` acepta `footer={false}`
para una página sin footer.

**Historia:** hasta nov 2026 el footer era una escena animada del centro de Chillán en pixel art
(`web/assets/footer/`, venía de `~/proyectos/footer-endless`). Se sacó porque no tenía relación con el juego.
