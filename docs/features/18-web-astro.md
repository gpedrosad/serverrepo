# Web en Astro (nov 2026)

La web de retro76.cl pasó de un solo `web/index.html` (2.100 líneas, Tailwind por CDN y todo
armado con JavaScript) a un sitio estático en **Astro**: una página real por sección, CSS propio
compilado y JavaScript solo donde hay datos en vivo. Las APIs de `web/server.py` no cambiaron.

## Peso

| | Antes | Ahora |
|---|---|---|
| Portada | 94 KB de HTML + 407 KB de Tailwind (JS que arma el CSS en el navegador) | 14 KB de HTML con el CSS adentro + ~3 KB de JS |
| Fuentes | — | Ninguna descargada (fuentes del sistema) |
| Frameworks de JS | Tailwind runtime | Ninguno |

## Páginas

| URL | Archivo | Datos |
|---|---|---|
| `/` | `pages/index.astro` | `/api/data` (se renueva cada minuto) |
| `/top`, `/power`, `/pk`, `/muertes` | `pages/*.astro` | `/api/data` |
| `/gemas` | `pages/gemas.astro` | **Al compilar**, desde `web/data/gem-drops.json` (HTML puro; el buscador es JS chico) |
| `/items-nuevos` | `pages/items-nuevos.astro` | **Al compilar**, desde `src/data/new-items.json` (generado por `scripts/web/build-new-items.py`; stats del OTB). Solo español |
| `/quests` | `pages/quests.astro` | **Al compilar**, desde `src/data/quests.json` (registro manual de quests y propuestas). Solo español |
| `/spells` | `pages/[...lang]/spells.astro` | Lista, maná y ML en vivo de `/api/data` (`spells.xml`); la **explicación de cada hechizo** (es/en) sale **al compilar** de `src/data/spells.json`, por palabras. Hechizo nuevo o cambiado → actualizar su texto ahí |
| `/reglas`, `/info` | `pages/*.astro` | `/api/data` (OTINFO) |
| `/cuenta`, `/bugs` | `pages/*.astro` | Formularios a `/api/create-account` y `/api/bug-report` (mismo contrato) |
| `/premium` | `pages/premium.astro` | `/api/premium-config` y `/api/premium-order` |
| `/cliente` | `pages/cliente.astro` | Estático |
| `/character/<nombre>` | `pages/character.astro` | `/api/character/<nombre>` |
| `/wiki`, `/wiki/<tema>` | `pages/wiki/` | **Al compilar**, desde `src/wiki/*.md` (HTML puro; el buscador del índice es JS chico). Solo en español. Ver Wiki. |

Todas existen también en inglés bajo `/en` (ver Idiomas). Las páginas están en `src/pages/[...lang]/`.

Comunes: `layouts/Base.astro` (head con SEO, cabecera con el estado del server, navegación y el
[footer](17-web-footer.md)), `styles/site.css` (todo el CSS) y
`lib/client.js` (pedir `/api/data` una vez por página, escapar texto, links a personajes,
captcha de formularios).

`/items` y `/items-all` (catálogo privado con token) siguen siendo los HTML de siempre.

## Idiomas (español, inglés y portugués)

Cada página existe tres veces: en español en la raíz (`/top`), en inglés bajo `/en` (`/en/top`) y en
**portugués de Brasil** bajo `/pt` (`/pt/top`, nov 2026). Las páginas viven en `src/pages/[...lang]/` y
`getStaticPaths` (`langPaths()`) genera las tres; el selector **ES · EN · PT** de la cabecera lleva a la misma
página en otro idioma y el `<head>` declara las tres con `hreflang` (`pt-BR`).

- **Textos:** todos en `src/i18n.js` (`dict(lang)`). Una página nueva o un texto nuevo se agrega en los tres
  idiomas ahí. `LANGS`, `LANG_NAMES`, `localePath(lang, path)` y `navHref(lang, path)` (que deja en español las
  páginas que solo existen en español: wiki, items nuevos y quests, `ES_ONLY`).
- **JS del navegador:** solo recibe `dict(lang).js`, embebido en el HTML (`<script id="i18n">`);
  `lib/client.js` lo lee con `t('clave', {vars})`. `pageLang()` sale del `<html lang>`. Los links a personajes
  llevan el prefijo del idioma (`/en/character/...`, `/pt/character/...`).
- **Lo que manda el servidor en español** (mensajes de los formularios, "hace 4d", tipos de hechizo, nombres de
  planes y extras de premium) se traduce en el navegador: `serverText()` (mapa `js.server` y las plantillas
  `accountCreated` / `donationThanks`), `relTime()` (`relNow` / `relAgo`) y los mapas `kinds`, `planLabels`,
  `addonDesc`. Si se agrega un mensaje nuevo en `web/*.py`, sumarlo a `js.server` de inglés **y** portugués.
- **Reglas e info:** `OTINFO.en` y `OTINFO.pt` (traducciones de `OTINFO`), que `/api/data` entrega como
  `otinfo_en` / `otinfo_pt`; `otinfoFor(d)` elige. Si se cambia `OTINFO`, actualizar las dos.
- **Servidor:** `server.py` sirve `/en`, `/pt`, `/<idioma>/<página>` y `/<idioma>/character/<nombre>`
  (`LANG_PREFIXES`) y los suma al `sitemap.xml`.
- **Sin traducir:** los números siguen con formato chileno y los nombres de criaturas, ítems y hechizos quedan
  como en el juego. Los pagos premium siguen siendo por transferencia en Chile (pendiente: Pix).

### Detección del idioma (27 nov 2026)

`web/server.py` (`lang_redirect_target`) redirige con 302 las páginas en español que existen en los tres idiomas (portada,
páginas del sitio que no son solo en español y `/character/...`) a `/en/...` o `/pt/...`:

- Primero manda la cookie `lang` (un año), que pone el botón de idioma (`Base.astro`, `data-lang`). Así quien elige ES
  se queda en español aunque el navegador esté en portugués.
- Si no hay cookie, el `Accept-Language` del navegador: el de mayor `q` entre es/en/pt. Otro idioma (alemán, polaco...)
  va a inglés.
- Sin `Accept-Language` (buscadores) no redirige: indexan el español y ven los `hreflang`.
- La wiki y las demás páginas solo en español no se redirigen.

## Menú y portada (nov 2026)

- **Menú agrupado** (`Base.astro`): Inicio · **Rankings ▾** (Top, Power, PK, Muertes) · **Guía ▾** (Wiki, Spells,
  Gemas, Items, Quests, Info, Reglas) · **Ayuda ▾** (Cuenta, Cliente, Reportar bug) · Premium, y a la derecha los
  botones **Crear cuenta** y **Descargar**. Los grupos son `<details>` (abren sin JS); un script chico deja uno solo
  abierto y los cierra al tocar fuera o con Escape. En el celular el menú pasa a dos filas y los botones ocupan el ancho.
- **Portada:** arriba, **"Empieza a jugar en 3 pasos"** (crear cuenta → descargar Windows/macOS → entrar), con
  botones; debajo, "El servidor ahora" (jugando, récord, uptime), destacados y conectados.
- **Seguridad de la web:** ver [`../systems/WEB_SECURITY.md`](../systems/WEB_SECURITY.md).

## Wiki

Guías cortas para jugadores: gemas, monstruos furiosos, El Crisol, training, ítems especiales, etc.

- **Un archivo por tema:** `web/site/src/wiki/<slug>.md` → `retro76.cl/wiki/<slug>`. Cómo escribirlos
  (encabezado, secciones, tono, qué se puede usar): [`src/wiki/_GUIA.md`](../../web/site/src/wiki/_GUIA.md).
  Con `estado: borrador` el artículo no se publica (para lo que todavía no está en el juego).
- **Markdown:** lo convierte `src/lib/wiki.js` al compilar. Es un subconjunto chico más tres extras:
  `[[slug]]` (enlace a otro artículo; si no existe o es borrador queda como texto y la compilación
  avisa), `{item:2154}` (ícono del ítem) y `> **Ojo:**` / `> **Tip:**` (aviso en rojo / verde).
- **Íconos:** `python3 scripts/web/build-wiki-icons.py` recorta del atlas de ítems los que usan los
  artículos (`web/assets/wiki/items/<id>.png`, con `sips`, no compila) y escribe `src/wiki/_icons.json`.
  La wiki solo muestra íconos de esa lista. Correrlo antes de compilar si se agregó un `{item:N}` nuevo.
- **Solo en español:** las páginas de la wiki no tienen botón de idioma; desde `/en` el link "Wiki (ES)"
  lleva a la versión en español.
- `server.py` sirve `/wiki` y `/wiki/<slug>` desde `dist/` y los suma al `sitemap.xml`.

## Items nuevos

`/items-nuevos` es el catálogo público de ítems custom con sus stats (ataque, defensa, armadura,
peso), efecto y dónde se consigue. Es **solo en español**, como la wiki: desde `/en` el link
"Items (ES)" lleva a la misma página y no hay `/en/items-nuevos`.

- **Datos:** `web/site/src/data/new-items.json`, generado por `scripts/web/build-new-items.py`.
  Ese script lee `web/data/items_catalog.json` (la lista curada de `/items`, con stats del OTB)
  y la ficha de cada ítem (`META`: grupo, tipo, efecto, drop). Si un ítem está en el catálogo
  pero no en `META`, no se publica y el script avisa.
- **Imágenes:** `web/assets/items/custom/<serverId>.png`. Para los ítems nuevos, primero
  `python3.11 scripts/web/build-items-catalog.py` (recorta del atlas y actualiza stats) y después
  `python3 scripts/web/build-new-items.py`.
- **Servidor:** `items-nuevos` está en `SITE_PAGES` y en `ES_ONLY_PAGES` de `web/server.py`
  (el sitemap no genera `/en/items-nuevos`).

## Quests

`/quests` es el registro público de todas las quests y sistemas con recompensa, con nivel recomendado,
ubicación, recompensa y notas. También lista **propuestas** de quests nuevas con su nivel. Es solo en
español, como la wiki y los items nuevos.

- **Datos:** `web/site/src/data/quests.json` (manual). Cada quest tiene `type` (`cofre`, `grupo`,
  `arena`, `diaria`), `level_label`, `level_min`, `players`, `where`, `reward`, `note`, `reward_ids`
  (íconos de la recompensa) y, si aplica, `chests`. Las propuestas van en `proposals` con `why`; los
  items sin drop de monstruo van en `pending_items` con la quest propuesta.
- **Mantenimiento:** al agregar una quest al mapa, sumarla al JSON y actualizar los contadores de la
  página. Los niveles de las quests clásicas son estimados según monstruos y recompensa; las puertas
  reales de nivel son las de Hell Quest (80/100). La Arena PvP se retiró en nov 2026.
- **Servidor:** `quests` está en `SITE_PAGES` y `ES_ONLY_PAGES` de `web/server.py`.

## Diseño

Página editorial oscura en vez de "cards":
- Sin cajas con borde y degradé, sin pastillas de colores ni animaciones de entrada.
- Secciones separadas por un título chico y una línea fina; datos en tablas con números
  monoespaciados y alineados a la derecha.
- Un solo acento dorado (`--accent`, las monedas del juego); verde y rojo solo para en
  línea/fuera de línea y resultados de formularios.
- Texto base de 15 px (antes casi todo era de 10-12 px). Formularios con etiquetas visibles.
- Premium: un solo formulario visible (plan, extras, pago) con el total que se actualiza solo,
  en vez de tres pasos ocultos.

Tokens de color y medidas: arriba de `styles/site.css`.

Pulido del 27 nov 2026 (skill ui-taste, modo polish, sin rediseño):
- Había dos reglas `.steps` y la segunda (código muerto de un premium viejo) pisaba la grilla de "Empieza a jugar en 3
  pasos": en móvil las 3 tarjetas quedaban apretadas y la página se desbordaba en horizontal. Se borró; ahora el texto
  de cada paso va en `--muted` a 14 px.
- Móvil (≤ 480 px): marca arriba y debajo, en una fila, estado a la izquierda y botón de idioma a la derecha.
- Botones sin cortar la etiqueta en dos líneas (`white-space: nowrap`); el teléfono de WhatsApp tampoco se corta (`.nowrap`).
- Los encabezados de columnas numéricas (`th.n`) van en la letra normal; solo los números de las celdas son monoespaciados.
- Las listas numeradas (`ol.numbered`, `.wiki-body ol`) ya no sacan el número fuera del borde del contenido.
- Footer en el mismo sistema que el resto: fondo `--bg-raise` liso, sin resplandor radial, sin degradé en el logo ni
  halo al pasar el mouse; los íconos de ítems bajan a otra fila en móvil en vez de cortarse.
- Faltaba la imagen del Private trainer dummy en premium (`assets/premium/20155-small.png` y `@2x`, sacadas del sprite
  `assets/items/custom/20155.png`, el 2x sin suavizar).

## Compilar

**No se compila en la Mac mini.** Se compila en la ThinkPad:

```bash
scripts/web/build-site.sh
```

Copia `web/site` (y `web/data/gem-drops.json`) a `thinkpad:~/build/retro76-web`, corre
`npm ci && npm run build` con el Node de nvm y trae `web/dist/` y `package-lock.json`.

- **`web/dist/` va versionado en git** a propósito: así el servidor no necesita Node y el deploy no
  cambia (se actualiza el repo y `server.py` lo sirve). Después de tocar `web/site`, compilar y commitear
  `web/dist` en el mismo commit.
- **Astro 5 (no 7):** la ThinkPad tiene un i5-3320M (2012, sin AVX2) y Astro 7 trae binarios
  nativos (compilador en Rust y Rolldown) que se caen con "Illegal instruction"; ni sus versiones
  WASM funcionaron. Astro 5 usa el compilador en WebAssembly y Rollup/esbuild, que corren en
  cualquier x86-64, y para un sitio estático el resultado es el mismo.

## Cómo lo sirve `web/server.py`

- `/` y las páginas de `SITE_PAGES` → `web/dist/<página>.html` (`Cache-Control: no-cache`).
- `/character/<nombre>` → `web/dist/character.html`.
- `/_astro/*` → JS de Astro con hash en el nombre (`max-age` de un año, `immutable`).
- `/assets/*`, `/data/*`, `/downloads/*` y las APIs, igual que antes.
- `sitemap.xml` incluye las páginas nuevas.

## Embudo premium

Los eventos siguen siendo los de `web/analytics.py` (`PREMIUM_EVENTS`): `tab_view` al abrir la
página, `checkout_open` al tocar "Elegir" o entrar al formulario, `plan_select` y `step2` al
elegir plan, `amulet_toggle` al marcar un extra, `step3` al llegar al nombre del personaje,
`receipt_selected`, `submit_click` y `submit_fail`.

## Pendiente

- Falta la imagen del extra "Private trainer dummy" (`assets/premium/20155-small.png`); ya
  faltaba antes. La página la oculta en vez de mostrarla rota.
