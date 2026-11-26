# Render de mapas sin GUI (maprender, sharp)

> Creado: 26 nov 2026. Código: `scripts/map/render/` (Node + [sharp](https://sharp.pixelplumbing.com/) 0.35.5 / libvips 8.18).
> Lee los mismos archivos que el resto de las herramientas de mapa: `test.otbm`, `items-zagan-test.otb`,
> `devtools/rme/rme-client-760/Tibia.dat|.spr` y `test-spawn.xml`. No escribe nada en el mapa.

## Resumen para agentes con poca atención

1. **Lo que se puede medir lo mide el código, no un modelo.** Cambios entre mapas → `diff`. ¿Se puede caminar? →
   `layer walk` / `ascii` / `check-reachable.py`. Monstruos por zona → `layer density` (devuelve los puntos calientes
   en JSON). Un modelo de visión **no** encuentra un pilar corrido una casilla (probado: 0 de 4 aciertos).
2. **Para mirar vos (el modelo caro)**: imágenes chicas. Claude cobra ~ancho×alto/750 tokens por imagen:
   72×101 casillas a 4 px ≈ 250 tokens; a 8 px ≈ 900; a 32 px ≈ 10.000. Empezá por `--px 4` u `8` y `--grid 10`,
   y subí a 16–32 solo en un recorte chico.
3. **Para que mire un modelo barato**: `ask` (≈US$0,00003 por imagen con `deepseek-v4.1-flash`, razonamiento
   apagado). Sirve para criterio ("¿se ve natural?", "¿dónde está el bote?"), no para medir.
4. **ASCII no siempre es más barato**: 72×101 casillas en texto = ~1.700–2.200 tokens; la misma zona como JPEG de
   318×417 px = ~300 tokens. ASCII conviene en recortes chicos (≲30×30) o cuando hacen falta coordenadas exactas.
5. **Proponer antes de escribir**: `--cells` dibuja casillas propuestas encima del mapa sin tocarlo; `compare
   --variant a=cells:a.json --variant b=cells:b.json --diff` pone variantes lado a lado en **una** imagen.
6. Clave de OpenRouter: solo mapas, en `~/.config/retro76/openrouter.env`; nunca imprimirla ni commitearla.

## Instalación

```bash
cd scripts/map/render && npm ci      # instala sharp 0.35.5 fijado (binarios para macOS arm64/x64 y Linux)
node scripts/map/render/maprender.mjs help
```

`node_modules/` está en `scripts/map/render/.gitignore`. Necesita Node ≥ 20 (probado con Node 26).

## Comandos

Todos imprimen **una línea de JSON** (ruta, tamaño en px y bytes, conteos), así el agente no tiene que abrir la
imagen para saber qué salió. Si no se pasa `--out`, la imagen va a `$TMPDIR/maprender/`.

Región (en todos los que dibujan): `--r x0,y0,x1,y1,z` | `--c x,y,z[,radio]` (radio 15) | `--floor z` (piso entero).
Mapa: `--map ruta.otbm` o `--map git:REF` (p. ej. `git:HEAD~1`, `git:910b45fb`; `actual` = `test.otbm`).
Salida: `--out f.png|.webp|.jpg|.avif`, `--quality 80`, `--width N`, `--max-side N`, `--grid 10` (reglas con
coordenadas cada 10 casillas), `--mark x,y;x,y` (recuadro rojo en casillas).

```bash
M="node scripts/map/render/maprender.mjs"

# Render con sprites reales. --px 32|16|8|4|2|1 (8 por defecto). --above 2 = como el cliente, con techos.
$M region --r 184,250,261,380,7 --px 8 --grid 10 --out /tmp/lobos.png
$M region --c 150,50,7,20 --px 16 --above 2 --out /tmp/city-techos.png

# Minimapa (color de minimapa del .dat, 1 px por casilla); un piso entero en ~60 ms
$M minimap --floor 7 --out /tmp/z7.png

# Capas
$M layer walk    --r 184,250,261,380,7 --px 4 --grid 10      # transitable / bloqueado / agua / escaleras / TP / PZ
$M layer walk    --c 150,50,7,12 --px 8 --over render         # solo lo no transitable, teñido sobre los sprites
$M layer density --floor 7 --px 2 --radius 5                  # monstruos de test-spawn.xml (JSON: hotspots)
$M layer items   --c 150,50,7,30 --px 4                       # ítems que no son suelo ni borde, por casilla
$M layer mods    --base git:910b45fb --r 184,250,261,380,7 --px 4   # verde = nueva, amarillo = cambiada, rojo = borrada

# Texto: un carácter por casilla (' ' vacío, '.' camina, ',' PZ, '#' bloquea, '~' agua/lava, '>' escalera, 'T' TP)
$M ascii --c 150,50,7,12

# Resumen de cambios (todos los pisos, zonas con bbox) — barato y exacto
$M diff --base git:HEAD~1
$M diff --base git:e3bac72e --map git:4920985b      # → piso 7: 2 casillas cambiadas en 142..144,75

# Variantes de la misma región en UNA imagen (otro mapa, otro commit, celdas propuestas o imágenes sueltas)
$M compare --r 184,250,261,380,7 --px 4 --grid 20 --diff \
   --variant "v1=git:910b45fb" --variant "mapkit=actual"
$M compare --r 186,262,204,274,7 --px 16 --diff --variant actual=actual --variant "bote+1=cells:/tmp/bote.json"

# Evaluar con un modelo barato (imagen optimizada + pregunta corta → JSON validado, costo en el log)
$M ask --r 184,255,255,355,7 --px 8 --grid 10 --max-side 768 \
   --q "Rate how natural this forest island looks (0-10) and name the 2 weakest spots by tile coords." \
   --expect '{"score":"number","weak":"array"}'
$M ask --image /tmp/variantes.png --model segunda --q "..." --expect '{"best":"A|B","why":"string"}'

# Una casilla en JSON (ids, capa, bloquea, PZ, casa)
$M tile 150,50,7
```

### Proponer sin escribir: `--cells`

Casillas que reemplazan a las del mapa solo en memoria: `[[x, y, z, [ids...]], ...]` o `{"x,y,z": [ids]}`
(lista vacía = casilla borrada). Sirve con `region`, `minimap`, `layer`, `ascii`, `diff`, `ask` y como variante
`cells:archivo.json` en `compare`. Desde Python (p. ej. la vista previa de mapkit, que hoy usa el render en
Python puro):

```python
import json, subprocess
cells_json = json.dumps([[x, y, z, ids] for (x, y, z), ids in cells.items()])
subprocess.run(["node", "scripts/map/render/maprender.mjs", "region", "--r", f"{x0},{y0},{x1},{y1},{z}",
                "--px", "8", "--cells", "-", "--out", "/tmp/zona.png"], input=cells_json.encode(), check=True)
```

### Muchos trabajos seguidos: `batch`

Carga assets y mapa una vez (~0,6 s) y procesa un JSON por línea; responde una línea por trabajo.
Las opciones son las mismas que en la línea de comandos, sin los guiones; `args` = argumentos sueltos.

```bash
printf '%s\n' \
  '{"cmd":"region","c":"150,50,7,10","px":8,"out":"/tmp/a.webp"}' \
  '{"cmd":"layer","args":["walk"],"r":"184,250,261,380,7","px":2,"out":"/tmp/b.png"}' \
  '{"cmd":"ascii","r":"188,266,200,270,7","cells":[[194,268,7,[]]]}' \
  | node scripts/map/render/maprender.mjs batch
```

## Modelos de visión: qué usar y cuánto cuesta

`ask` copia las convenciones de `scripts/map/mapkit/jev.py`: clave en `OPENROUTER_API_KEY` o
`~/.config/retro76/openrouter.env`; cada llamada queda en `~/.cache/retro76/jev-log.jsonl` (`key:
"maprender-ask"`, tokens, costo, segundos, bytes de imagen); el JSON se valida contra `--expect` y si no sirve se
reintenta una vez; sin clave devuelve `{"ok":false,"meta":{"skipped":true}}` (código de salida 2) y el que llama
sigue con su fallback. Extras: **caché de respuestas** en `~/.cache/retro76/maprender-ask/` (misma imagen +
pregunta + modelo = gratis, `"cached":true`) y **tope diario** `MAPRENDER_VISION_MAX_USD` (0,20 por defecto,
contador en `~/.cache/retro76/maprender-spent.json`). `--model` acepta un id de OpenRouter o un alias:

| Alias | Modelo | Respuestas correctas (prueba de abajo) | Costo medido por imagen |
|---|---|---|---|
| `normal` (defecto) | `deepseek/deepseek-v4.1-flash-1017` | 4/4 | US$0,00003–0,00008, ~0,7 s |
| `barato` | `inclusionai/ling-3.0-flash-vl` | 5/6 (falló el bote a 4 px) | US$0,00001–0,00004, ~0,8 s |
| `gemma` | `google/gemma-3-27b-it` | 5/6 (falló el bote a 4 px) | US$0,00003–0,00004, ~1 s |
| `segunda` | `anthropic/claude-haiku-5.5` | 2/2 | US$0,0001, ~0,8 s |
| `jev` | `typesafe/jev-router` | 3/4 sin razonamiento; 0/2 con razonamiento | US$0,00006–0,00013, 2,5–4 s |

Prueba (26 nov 2026): render del Claro de los Lobos (`184,255,255,355,7`) con reglas, pregunta de respuesta
conocida: "¿el camino de tierra es continuo?" (sí) y "¿en qué casilla está el bote?" (192–196,268; vale ±4).
Imagen JPEG q70 de 318×417 (4 px/casilla, 18 KB) y de 567×768 (8 px/casilla, 42 KB): **300–600 tokens de
entrada** según el modelo. Otros resultados:

- `qwen/qwen3.7-flash` (el más barato de la lista): 0/2, y a 4 px dijo que el camino estaba cortado. Descartado.
- `~z-ai/glm-flash-latest` 2/2 pero US$0,00011; `mistral-small-3.2` 1/2; `gemini-2.5-flash-lite` 1/2;
  `openai/gpt-5-nano` rechaza `reasoning: {enabled:false}` (razonamiento obligatorio).
- **Con razonamiento encendido** (`jev-router` y `qwen` por defecto) gastaron los 400 tokens de salida pensando y
  no devolvieron nada. Por eso `ask` manda `--reasoning none` por defecto.
- Cambio sutil (pilar de `142,75` movido a `144,75`, `compare` de dos commits): **ningún** modelo lo ubicó
  (gemma, ling, glm, haiku). Para eso está `diff` / `compare --diff`, que lo da exacto y gratis.
- Gasto total de todas las pruebas de este doc: **~US$0,003** (34 llamadas).

Tokens para Claude (el agente que mira la imagen con Read): ≈ ancho × alto / 750.

| Qué | Tamaño | Bytes | Tokens aprox. |
|---|---|---|---|
| Claro 72×101 casillas, 4 px + reglas (PNG) | 342×537 | 15 KB | ~245 (Claude) / ~300 (deepseek) |
| Lo mismo a 8 px + reglas (PNG) | 654×1061 | 313 KB | ~925 (Claude) |
| Lo mismo en ASCII | 8.192 caracteres | — | 1.700 (deepseek) / 2.170 (ling) |
| Minimapa del piso 7 entero (753×477 casillas) | 753×477 | 40 KB | ~480 (Claude) |

## Arquitectura

```
OTBM / OTB / DAT / SPR ──► lib/assets.mjs (parsers JS, sin dependencias)
                               │  GameMap: casillas por piso y fila (+ firma del contenido para diff)
                               │  Sprites: cada sprite se decodifica una vez y se reduce una vez por escala
                               ▼
                           lib/render.mjs (dibujo en RGBA crudo, JS)
                               │  region (sprites), minimapa, walk, densidad, diff, ASCII
                               ▼
                           lib/image.mjs (sharp/libvips)
                               │  PNG/WebP/JPEG(mozjpeg)/AVIF, reescalado, reglas y títulos en SVG, grillas
                               ▼
                           maprender.mjs (CLI, JSON por línea, batch)  ──►  lib/vision.mjs (OpenRouter)
```

- **Orden de dibujo** igual que `scripts/map/kb/mapdata.py` y `scripts/map/game_render.py`: por fila y columna;
  en la casilla ground → borde → bottom → común → top (estable); ítems grandes hacia arriba-izquierda; offset del
  .dat (flag 0x18) y elevación (0x19, tope 24 px) como `game_render.py`; patrón por posición (`x % px`, `y % py`);
  cuadro 0 de las animaciones. Pisos de arriba (`--above`) corridos una casilla arriba-izquierda, como el cliente.
- **Escalas chicas sin pasar por 32 px**: cada sprite se reduce a 16/8/4/2/1 px (promedio con alfa) una sola vez
  y se pega a esa escala. Por eso un piso entero a 4 px tarda ~60 ms en vez de dibujar 24.000×15.000 px y achicar.
- **Transitabilidad** (`walk`) con los flags del OTB, como el servidor: `block_solid` en el suelo = agua/lava
  (`~`), en otro ítem = bloqueado (`#`); `floorchange_*` o flag 0x17 del .dat = escalera; grupo teleport = TP;
  grupo magicfield = campo; flag de casilla 1 = PZ.
- **Diff**: cada casilla guarda una firma (FNV-1a) de todo su contenido OTBM, incluidos atributos de ítems
  (action id, destino de teleport, texto, contenido de cofres), así `diff` también ve cambios que no cambian el sprite.
  `zones` agrupa los cambios en bloques de 8×8 casillas conectados (bbox + conteo).
- **Densidad**: monstruos (`test-spawn.xml`, centro + desplazamiento) o ítems por casilla, suma en ventana de
  radio `--radius` (imagen integral), paleta tipo inferno y máximos locales separados (`hotspots`).

### Caché

- **Sprites**: en memoria, decodificados una vez y reducidos una vez por escala (el render típico decodifica
  ~1.900 de 15.751 sprites).
- **Respuestas de `ask`**: en disco por hash de imagen + pregunta + modelo.
- **Render incremental por bloques: probado y descartado.** Se implementó un caché en disco de bloques de 32×32
  casillas (firma del contenido + gzip). Medido: 192×192 casillas a 32 px = 291 ms directo vs 1.201 ms con caché
  fría y 259 ms caliente; a 8 px 33 vs 85/21 ms; piso 8 entero a 4 px 28 vs 81/43 ms. Dibujar es tan rápido como
  leer el caché, así que no vale la complejidad ni los ~40 MB en disco. Si algún día se arma un visor web con
  mosaicos fijos, ahí sí convendría (como hace `build-monster-map.py`).
- **Mapa**: no se cachea en disco; parsear el OTBM en JS tarda ~0,55 s. Para muchas imágenes seguidas, `batch`.

## Decisiones técnicas y alternativas (medido el 26 nov 2026, Mac arm64)

El trabajo se divide en dos: **componer** los sprites (millones de pegados chicos con transparencia) y
**codificar/escalar/rotular** la imagen final. Componer se hace en JS a mano en un `Uint8Array` (ninguna librería
gana ahí: la llamada por sprite cuesta más que el pegado). La librería solo entra al final.

| Opción | Composición 100×100 casillas a 32 px | PNG 3200×3200 | WebP q80 | JPEG q70 | Reducir a 800 + JPEG | Instalación |
|---|---|---|---|---|---|---|
| **JS + sharp 0.35.5** (elegido) | **87 ms** | 134 ms (8,7 MB) | 635 ms (2,3 MB) | 443 ms (1,3 MB, mozjpeg) | **15 ms** | 19 MB, binarios precompilados |
| JS + @napi-rs/canvas 1.2.1 | (igual, JS) | 406 ms (8,1 MB) | 616 ms | 36 ms (1,8 MB) | 4 ms | 28 MB |
| JS + jimp 1.6.0 (JS puro) | (igual, JS) | 779 ms (23,8 MB) | — | 948 ms | 221 ms | 4 MB |
| Python puro (`mapdata.Renderer`) | **2.610 ms** | 380 ms (zlib) | — | — | — | nada |
| Python + Pillow 12 | — | 256 ms | 1.575 ms | 24 ms | 35 ms | pip (no está instalado en el repo) |
| pyvips | — | — | — | — | — | necesita libvips del sistema (brew/apt) |

Por qué sharp:

1. Lo pidió el usuario y es el estándar en Node; libvips es rápido y con poca memoria.
2. Trae **SVG (librsvg) y tipografías**: reglas con coordenadas y títulos de variantes sin otra dependencia.
3. **Formatos para modelos**: JPEG mozjpeg (30 % más chico que libjpeg común), WebP y AVIF; reescalado con kernel
   elegible (`nearest` para agrandar pixel art, `mitchell` para achicar).
4. Binarios precompilados para macOS y Linux x64 (la ThinkPad), sin compilar nada.
5. @napi-rs/canvas era la alternativa seria (más rápido en JPEG, también rotula), pero pesa más y no tiene AVIF ni
   el pipeline de libvips; jimp es lento; Python puro es 30× más lento al componer y no reduce por escala.

Lo que más ahorra no es la librería sino **no dibujar a 32 px lo que se va a mirar a 4–8 px** (sprites reducidos
de antemano) y mandar imágenes de ≤768 px de lado.

## Mediciones con los assets reales (`maprender.mjs bench`)

| Qué | Tiempo |
|---|---|
| Cargar OTB + DAT + SPR | 17–32 ms |
| Parsear `test.otbm` (578.033 casillas, 15 pisos) | 540–600 ms (Python `load_tiles`: 1,1 s) |
| 100×100 casillas a 32 px (3200×3200) | dibujo 87 ms; PNG 130 ms / WebP 650 ms / JPEG 445 ms |
| 100×100 casillas a 8 px (800×800) | dibujo 10 ms; PNG 9 ms (468 KB) / WebP 37 ms (102 KB) / JPEG 28 ms (75 KB) |
| 100×100 casillas a 4 px (400×400) | dibujo 5 ms; PNG 3 ms (90 KB) / WebP 9 ms (27 KB) / JPEG 10 ms (24 KB) |
| Minimapa piso 7 entero (753×477) | 60 ms + PNG 5 ms (40 KB) |
| Piso 7 entero con sprites a 4 px (3012×1908) | 63 ms |
| Capa walk piso 7 entero a 1 px | 16 ms |
| Un comando completo desde la terminal (Node + carga + render + archivo) | 0,55–0,8 s |

## Validación

- **Píxel por píxel igual a `mapdata.Renderer().area()`** (30×30 casillas de la ciudad a 32 px, 921.600 píxeles,
  0 distintos) apagando offsets y elevación, que `mapdata` no aplica.
- Probado con el Claro de los Lobos (`184–261, 250–380, z7`), la ciudad (`150,50,7`) con techos, minimapa y
  densidad del piso 7 entero, `diff`/`compare` entre `4920985b`, `910b45fb` y el mapa actual (Claro v1 → mapkit:
  4.593 casillas nuevas y 2.928 cambiadas, una sola zona `184,250–261,380`), el pilar `e3bac72e → 4920985b`
  (2 casillas en `142..144,75`) y `--cells` (bote corrido una casilla).

## Errores que ya pasaron

- **El bote corrido una casilla se rompe**: sus piezas tienen patrón por posición (`x % px`), así que moverlas un
  número impar de casillas cambia el dibujo (el cliente hace lo mismo). El render lo muestra; mover piezas con
  patrón de a pares o elegir la variante correcta.
- **Diff con borde a 4 px**: el recuadro de 1 px tapaba toda la imagen. A menos de 8 px `compare --diff` tiñe.
- **Modelos de visión con razonamiento**: gastan todos los tokens pensando y devuelven vacío. `--reasoning none`.
- **`jev-router` con imágenes**: funciona (eligió `deepseek-v4.1-flash`), pero es más caro y lento que pedir
  ese modelo directo. Para imágenes, usar `--model normal`.

## Pendiente / límites conocidos

- No dibuja criaturas ni NPCs (para eso está `game_render.py` con outfits); la densidad de monstruos sí.
- Cuadro 0 de las animaciones; apilables y fluidos usan el patrón por posición, no la cantidad ni el color real.
- Sin luz ni oscuridad de pisos subterráneos.
- La vista previa de mapkit (`mapkit/__init__.py: preview`) sigue en Python puro; el snippet de `--cells` de
  arriba sirve para pasarla a este render cuando quien mantiene mapkit lo decida.
- Los aciertos de los modelos salen de una muestra chica (2 preguntas, 2 tamaños). Si se usa `ask` en un bucle,
  medir de nuevo con preguntas del caso real y anotar acá.
