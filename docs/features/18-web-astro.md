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
| `/spells`, `/reglas`, `/info` | `pages/*.astro` | `/api/data` (spells, OTINFO) |
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

## Idiomas (español e inglés)

Cada página existe dos veces: en español en la raíz (`/top`) y en inglés bajo `/en` (`/en/top`).
Las páginas viven en `src/pages/[...lang]/` y `getStaticPaths` genera las dos versiones; el
botón de la cabecera lleva a la misma página en el otro idioma y el `<head>` declara las dos con
`hreflang`.

- **Textos:** todos en `src/i18n.js` (`dict(lang)`). Una página nueva o un texto nuevo se agrega
  en los dos idiomas ahí.
- **JS del navegador:** solo recibe `dict(lang).js`, embebido en el HTML (`<script id="i18n">`);
  `lib/client.js` lo lee con `t('clave', {vars})`. Los links a personajes llevan el prefijo del
  idioma (`/en/character/...`).
- **Lo que manda el servidor en español** (mensajes de los formularios, "hace 4d", tipos de
  hechizo, nombres de planes y extras de premium) se traduce en el navegador: `serverText()`,
  `relTime()` y los mapas `server`, `kinds`, `planLabels`, `addonDesc` de `i18n.js`. Si se agrega
  un mensaje nuevo en `web/*.py`, sumarlo a `js.server` del inglés.
- **Reglas e info:** `OTINFO.en` (traducción de `OTINFO`), que `/api/data` entrega como
  `otinfo_en`. Si se cambia `OTINFO`, actualizar también `OTINFO.en`.
- **Sin traducir:** los números siguen con formato chileno (`3.267.392`) y los nombres de
  criaturas, ítems y hechizos quedan como en el juego (en inglés).

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
