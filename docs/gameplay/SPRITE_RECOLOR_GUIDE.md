# Sprites de criaturas: receta para crear y editar

Guía para hacer o cambiar el sprite de un monstruo **sin volver a investigar nada y gastando poco**.
Está escrita para que una IA (o una persona) la siga de arriba abajo. El método es siempre el mismo:
tomar una criatura que ya existe en el cliente 7.6, cambiarle los colores por partes y agregarle un
rasgo propio.

## Ficha rápida (leer esto alcanza para la mayoría de los casos)

```bash
T=scripts/client-rme/sprite_tool.py
grep -i "spider\|violet" docs/gameplay/SPRITE_BASES.md       # 1. elegir base por nombre o color (sin abrir imágenes)
python3 $T new ash-ghoul --base 18                           # 2. crea presets/ash_ghoul.py, ya funciona (sale igual al base)
python3 $T inspect ash-ghoul --colors 0 --frames 2           # 3. partes en texto, con coordenadas
#                                                              4. editar palettes y detail en el archivo (sección 4)
python3 $T check ash-ghoul                                   # 5. hoja + escena: mirar las 2 imágenes
python3 scripts/client-rme/add_recolor_look.py --preset ash-ghoul devtools/rme/rme-client-760   # 6. aplicar
python3 $T verify --expect 240                               # 7. TODO BIEN o la lista de problemas
rm devtools/rme/rme-client-760/*.bak-*                       # 8. borrar respaldos antes de commitear
```

Presupuesto: leer esta ficha y la sección 4, un archivo de preset de ejemplo si hace falta, y mirar
**2 imágenes por vuelta** (hoja y escena). No hace falta leer `add_recolor_look.py` ni `sprite_tool.py`,
ni escribir scripts sueltos, ni ampliar cuadro por cuadro. Cada comando tarda menos de 4 segundos y no
necesita instalar nada (`python3` solo, sin Pillow).

| Pieza | Qué es |
|-------|--------|
| `scripts/client-rme/presets/NOMBRE.py` | **Un archivo por criatura.** Es lo único que se escribe |
| `scripts/client-rme/sprite_kit.py` | Las piezas para escribir presets (partes, paletas, `Frame` para pintar) |
| `scripts/client-rme/sprite_tool.py` | Mirar, crear, comparar y verificar. `--help` lista los comandos |
| `scripts/client-rme/add_recolor_look.py` | El motor: aplica un preset a `Tibia.dat` / `Tibia.spr` |
| [`SPRITE_BASES.md`](SPRITE_BASES.md) | Catálogo de las 126 criaturas que sirven de base, con sus colores |

El resto del monstruo (XML, ataques, loot, spawn) está en [`CUSTOM_MONSTER_WORKFLOW.md`](CUSTOM_MONSTER_WORKFLOW.md).

## 1. Datos fijos (no hay que redescubrirlos)

| Dato | Valor |
|------|-------|
| Cuadros de una criatura | 12: 4 direcciones × 3 cuadros de animación (quieto + 2 de caminar) |
| Índice del cuadro | `anim * 4 + direction` |
| Direcciones | 0 norte (de espaldas), 1 este, 2 sur (de frente), 3 oeste |
| Tamaño | 1×1 = cuadros de 32×32 px (12 sprites); 2×2 = cuadros de 64×64 px (48 sprites) |
| Píxel | `(r, g, b, a)` con `a` 0 o 255. **No hay transparencia parcial** |
| Coordenadas | `(x, y)` con `(0, 0)` arriba a la izquierda; índice `y * w + x`, con `w` = 32 o 64 |
| Perspectiva | La figura va inclinada en diagonal, con la cabeza arriba a la izquierda. Es normal |
| Looktype máximo | 255 (viaja en un byte). Usados y libres: `sprite_tool.py looks` |
| Formas admitidas | Solo 1×1 y 2×2 con 4 direcciones y 3 cuadros (las de `SPRITE_BASES.md`). Slime, Rotworm, Wasp, Fire Elemental y los outfits de jugador tienen otra forma: no sirven |

Ojo: algunas criaturas que parecen de una casilla están guardadas como 2×2 (el Monk, 57). `SPRITE_BASES.md`
y `inspect` lo dicen.

## 2. Elegir base y destino

- **Base:** buscar en [`SPRITE_BASES.md`](SPRITE_BASES.md) por nombre o por color. Conviene una con la
  silueta buscada, zonas de color bien separadas y, mejor, algo en la mano o en la cabeza donde colgar el
  rasgo propio. Las marcadas como *estudiadas* ya tienen el clasificador de partes probado: es más barato.
- **Destino:** `new` usa solo el próximo libre (el que sugiere `looks`). Ya descarta los que usa algún
  monstruo o NPC. `--target N` para elegir otro.
- **Qué hace que no se vea "típico":** cambiar solo los colores no alcanza. Hace falta **un elemento
  agregado o reemplazado** que se note a tamaño de juego. Ejemplos ya hechos: la calavera del Necromancer
  pasó a ser una bola de fuego celeste (Tide Priest); el Crypt Shambler ganó pañuelo, camiseta rayada y
  algas (Drowned Sailor); el Monk, capucha roja y costuras en rombo (Trainer Monk).

## 3. Lo que crea `new`

`python3 scripts/client-rme/sprite_tool.py new ash-ghoul --base 18` escribe `presets/ash_ghoul.py` con:

- `parts`: el clasificador de partes del base. Si el base está estudiado, `BASE_PARTS[18]`. Si no, un
  primer corte automático por familia de color (`dark`, `gray`, `orange`, `green`…) con las reglas
  escritas, para ajustarlas.
- `palettes`: una línea comentada por parte con sus colores de hoy (oscuro, medio, claro) y cuánto
  ocupa. Comentada = queda igual que en el base.
- `detail(f)`: vacío, con un ejemplo comentado.
- `PRESET = dict(name, source, target, parts, palettes, detail)`.

Funciona tal cual desde el primer momento (sale idéntico al base), así que se puede ir probando de a un
cambio con `check`.

## 4. Escribir el preset

Ejemplo completo y probado (Ghoul → ghoul de ceniza con grietas de brasa y ceniza que cae):

```python
from sprite_kit import *  # noqa: F401,F403

parts = BASE_PARTS[18]                       # body, dark (contorno) y wound (heridas rojas)

palettes = {
    "body": [(8, 8, 12), (58, 58, 66), (126, 124, 128), (206, 202, 196)],   # ceniza, de oscuro a claro
    "wound": [(120, 30, 0), (236, 110, 20), (255, 226, 120)],              # brasas
}


def detail(f):
    """La brasa más grande late con la animación y cae ceniza del borde de abajo."""
    ember = f.biggest("wound")
    if ember:
        cx, cy = centroid(ember)
        f.set(round(cx), round(cy), ((255, 250, 200), (255, 200, 90), (255, 236, 150))[f.anim])
    for x, y in f.underside()[2::9][:3]:
        f.hang(x, y, [(150, 146, 140), (96, 92, 90)][:1 + (x + f.anim) % 2])


PRESET = dict(name="Ash Ghoul", source=18, target=240, parts=parts, palettes=palettes, detail=detail)
```

### `PRESET`

| Clave | Qué es |
|-------|--------|
| `name`, `source`, `target` | Nombre, looktype base y looktype de destino |
| `parts` | Clasificador: `parts(pixel)` devuelve el nombre de la parte, o `None` si es transparente |
| `palettes` | Colores nuevos por parte (abajo). Una parte que no figura queda igual |
| `detail` | Opcional: `detail(f)` pinta el rasgo propio en cada cuadro (abajo) |
| `recolor`, `frames_post` | Forma vieja, a mano: `recolor(pixel)` píxel por píxel y `frames_post(originales, nuevos)` con los 12 cuadros. La usan los presets anteriores a `sprite_kit`; no hace falta para uno nuevo |

### Partes

- Para un base estudiado: `parts = BASE_PARTS[n]` (ver la sección 6).
- Para otro: `parts_by_rules(("ojos", lambda h, s, v: ...), …, ("resto", None))`. `h`, `s` y `v` van de
  0 a 1. Gana la primera regla que se cumple, así que va primero lo más específico (ojos, piel) y al
  final el resto.
- Los umbrales salen de `inspect`: el "Resumen por parte" y el "Resumen por letra de color" dan, para
  cada grupo, cuántos píxeles tiene y entre qué valores se mueven `h`, `s` y `v`.
- **Revisar el mapa de `inspect` después de cada cambio de reglas.** Una letra suelta donde no corresponde
  (calavera en medio de la capucha) es un umbral mal puesto y después sale como una mota de otro color.

### Paletas

- Cada parte usa su paleta, de oscuro a claro, con 3 a 5 colores `(r, g, b)`.
- La posición en la paleta sale de la luminosidad del píxel **llevada a 0-1 dentro de su parte**, así se
  conservan las sombras y el volumen y cada parte usa la paleta entera. No hace falta normalizar a mano.
- `"parte": (paleta, 0.8)` aclara y `(paleta, 1.2)` oscurece. Un color solo, `(r, g, b)`, la pinta pareja.
- Si el sprite va a vivir en un suelo oscuro, subir el extremo claro para que no se pierda.

### `detail(f)`: el rasgo propio

`f` es un cuadro (`sprite_kit.Frame`). Datos: `f.anim` (0 quieto, 1 y 2 caminar), `f.direction` (0 norte,
1 este, 2 sur, 3 oeste), `f.w` (32 o 64), `f.orig` (píxeles del base), `f.px` (los nuevos), `f.parts`.

| Para | Usar |
|------|------|
| Encontrar un objeto o la cara | `f.biggest("parte")`: el grupo más grande; `centroid(grupo)` da su centro |
| Todos los grupos de una parte | `f.groups("parte", min_size=5)`, del más grande al más chico |
| Puntos de una o más partes | `f.points("piel", "herida")` |
| Sacar brazos y bordes finos | `f.thick(puntos)`: solo los que tienen sus 4 vecinos adentro |
| Pintar un píxel | `f.set(x, y, (r, g, b))` (ignora lo que cae fuera del cuadro) |
| Pintar una zona | `f.fill(puntos, (r, g, b))` o `f.fill(puntos, paleta)` según la luz del base |
| Bola de luz o fuego | `f.orb(cx, cy, radio, paleta)`; para que lata, `radio = (2.6, 3.1, 2.8)[f.anim]` |
| Resplandor | `f.glow(cx, cy, radio, ancho, (r, g, b))`: aclara la silueta alrededor, no el fondo |
| Ojos que brillan | `f.eyes(cara, color, halo=None)`: dos de frente, uno de perfil en el borde, ninguno de espaldas ni al oeste |
| Cosas que cuelgan | `f.underside()` da los bordes de abajo; `f.hang(x, y, [colores])` cuelga una tira |
| Chispas que giran | `f.set(*f.around(cx, cy, distancia, ángulo), color)`, con el ángulo según `f.anim` |
| ¿Hay silueta ahí? | `f.opaque(x, y)` |

## 5. Trucos que ya funcionaron

Los presets de ejemplo están en `scripts/client-rme/presets/`: conviene copiar de ahí antes que inventar.

| Truco | Cómo | Dónde verlo |
|-------|------|-------------|
| Cambiar un detalle que identifica (ojos, lengua) | Clasificar el rojo intenso aparte y darle un color fijo | `frost_dragon.py`, `ice_spider.py` |
| Reemplazar un objeto por un orbe | El grupo más grande de la parte clara, disco que late, resplandor, lengua de fuego y chispas | `tide_priest.py` |
| Encontrar la cabeza | El grupo de piel "gruesa" que está más arriba (sin brazos finos) | `drowned_sailor.py` |
| Cara en sombra con ojos | Pintar la cara oscura y encima los ojos | `ice_monk.py` |
| Ropa rayada | Franjas que siguen la diagonal: `((y + x // 3) // 2) % 2` | `drowned_sailor.py` |
| Costuras en rombo | Oscurecer `(x + y) % 6 == 0 or (x - y) % 6 == 0` | `sparring_monk.py` |
| Capucha | Los píxeles de túnica del primer 30 % de la silueta medida sobre `x + y` (la diagonal) | `sparring_monk.py` |
| Prenda sobre la cabeza | Pintar la mitad de arriba de la cabeza; de espaldas, más | `drowned_sailor.py` (pañuelo) |
| Parches cosidos | Cuadrados de 4×4 en posiciones relativas a la silueta, con puntadas en las esquinas | `novice_monk.py` |
| Cosas que cuelgan | Desde el borde de abajo, hacia abajo sobre transparente | `drowned_sailor.py` (algas, gotas) |
| Brasas / grietas de magma | Las luces de la parte roja o las heridas a una paleta de fuego | `ashen_lord.py`, `hellhound.py` |

Reglas para que se vea bien a tamaño de juego:

- Un rasgo de 1 o 2 píxeles solo se nota si tiene mucho contraste (claro sobre oscuro). Si no, que ocupe
  unos 5×5 píxeles.
- Lo que cambia entre cuadros de animación debe moverse 1 píxel como mucho. Más que eso parpadea.
- Tratar cada dirección aparte: de espaldas y mirando al oeste casi nunca se ve la cara.
- Se puede pintar fuera de la silueta, pero no fuera del cuadro (32 o 64 píxeles).
- **Nunca usar `random`.** Para variar, usar fórmulas con `x`, `y`, `f.anim` y `f.direction`
  (ej. `(x * 7 + y * 13 + f.direction * 3) % 9 == 0`). El resultado tiene que salir igual cada vez, porque
  `verify` comprueba que cada preset vuelva a generar exactamente su look.

## 6. Bases ya estudiadas

Si el base es uno de estos, reusar lo que ya está. Las de `BASE_PARTS` traen el clasificador listo.

| Base | Forma | Partes y umbrales | Dónde |
|------|-------|-------------------|-------|
| Necromancer (9) | 1×1 | `skin` cara: `0.03 < h < 0.13, s > 0.3, v > 0.35`. `light` (calavera, manos, botas, ribete): `v ≥ 0.3, h < 0.5`. `robe`: el resto, con brillo solo de 0 a 0.3 | `BASE_PARTS[9]` |
| Ghoul (18) | 1×1 | `dark` contorno: `v < 0.13`. `wound` heridas: `h < 0.04, s > 0.6`. `body`: el resto | `BASE_PARTS[18]` |
| Monk (57) | 2×2 | `skin` cara y manos: `0.06 ≤ h ≤ 0.10, 0.28 ≤ s ≤ 0.47, v > 0.74`. `belt`: `0.095 ≤ h ≤ 0.13, s > 0.47, v > 0.76`. `outline`: `v < 0.22`. `robe`: el resto | `BASE_PARTS[57]` |
| Crypt Shambler (100) | 1×1 | `dark` contorno: `v < 0.13`. `pants` verde: `0.2 < h < 0.55, s > 0.25`. `wound`: `(h < 0.04 o h > 0.93), s > 0.6`. `skin`: el resto | `BASE_PARTS[100]` |
| Dragon (34) | 2×2 | Ojos, lengua y garras: `(h < 0.09 o h > 0.95), s > 0.6, v > 0.5`. Panza y alas: `0.06 < h < 0.2, s > 0.35`. Cuerpo verde: el resto | `frost_dragon.py` |
| Giant Spider (38) | 2×2 | Ojos verdes: `0.25 < h < 0.48, s > 0.35`. Articulaciones amarillas: `0.10 < h < 0.20, s > 0.55, v > 0.55`. Rayas rojas: `(h < 0.045 o h > 0.96), s > 0.6`. Cuerpo marrón: `0.03 < h < 0.14, s > 0.35`. Sombras azules: `h > 0.5, s > 0.3` | `ice_spider.py` |
| War Wolf (3) | 2×2 | Casi todo gris: se pinta por luminosidad. Ojos: `0.1 ≤ h ≤ 0.2, s > 0.3, v > 0.45`. Contorno: luminosidad < 0.12 | `hellhound.py` |
| Demon (35) | 2×2 | Contorno: `v < 0.16`. Fuego y ojos: `0.11 ≤ h ≤ 0.33, s > 0.3`. Cuernos, alas y garras: `0.04 ≤ h < 0.11, s > 0.2`. Luces de la piel: `(h < 0.04 o h > 0.9), s > 0.45, v > 0.86`. Piel roja: el resto | `ashen_lord.py` |

## 7. Mirar el resultado

```bash
python3 $T check mi-preset                                    # hoja + escena + cuántos píxeles cambiaron
python3 $T check mi-preset --area 150,40,170,52,7 --at "154,46,s;158,46,e;162,46,s,orig"
python3 $T inspect mi-preset --new --frames 2                 # el sprite nuevo en texto, sin abrir imagen
```

- **Hoja:** a la izquierda el original y a la derecha el nuevo. Columnas: norte, este, sur, oeste. Filas:
  los 3 cuadros de animación.
- **Escena:** el sprite sobre el mapa real (`test.otbm`) a tamaño de juego ×2. Sin opciones usa la bodega
  del naufragio, con el original al lado.
  - `--area x1,y1,x2,y2,z`: otra zona, en casillas.
  - `--at "x,y,dir[,cual[,anim]]"`, separadas por `;`: `dir` es `n`, `e`, `s` o `w`; `cual` es `new`
    (por omisión), `orig` o un número de looktype; `anim` es 0, 1 o 2. Elegir casillas caminables.
- `check` avisa si el sprite nuevo quedó igual al base (paletas todavía comentadas).
- `sheet` y `scene` hacen lo mismo por separado, con la ruta de salida que se quiera.

Qué revisar en la escena: que se distinga del original de un vistazo, que el rasgo propio se lea y que no
se pierda contra el suelo donde va a vivir.

Para el doc del monstruo, las mismas dos imágenes sirven:
`docs/gameplay/img/NOMBRE.png` (hoja) y `docs/gameplay/img/NOMBRE-LUGAR.png` (escena).

## 8. Aplicar y verificar

```bash
python3 scripts/client-rme/add_recolor_look.py --preset mi-preset devtools/rme/rme-client-760
python3 scripts/client-rme/sprite_tool.py verify --expect 240
rm devtools/rme/rme-client-760/*.bak-*
```

`verify` compara `Tibia.dat` / `Tibia.spr` de RME contra el último commit (`--base REF` para otra
referencia) y termina con `TODO BIEN` o con la lista de problemas. Comprueba:

- Cantidades de ítems, looktypes, efectos y proyectiles sin cambios.
- Ítems, efectos y proyectiles idénticos byte a byte.
- Qué looktypes cambiaron (con `--expect` falla si no son exactamente esos).
- Todos los sprites viejos idénticos.
- Cada preset vuelve a generar exactamente el look que está en el archivo.
- No quedaron respaldos `.bak-*`.

Contra una referencia vieja (`--base` de hace varios commits) es normal que marque ítems o efectos si
otros cambios los tocaron en el medio (ej. un pack de efectos): comparar contra el commit justo anterior.

`Tibia.dat` y `Tibia.spr` de `devtools/rme/rme-client-760/` sí van a git.

## 9. Editar un sprite que ya existe

Cambiar su archivo en `presets/` y volver a aplicarlo con `--replace`:

```bash
python3 $T check tide-priest                                  # ver el cambio antes de escribir nada
python3 scripts/client-rme/add_recolor_look.py --preset tide-priest devtools/rme/rme-client-760 --replace
python3 $T verify --expect 234
rm devtools/rme/rme-client-760/*.bak-*
```

- `--replace` rehace solo los sprites de ese look. Los ids no cambian y el resto del archivo queda igual.
- Sin `--replace` el script no toca un look que ya tiene sprites (por eso es seguro correrlo dos veces).
- Si el look ya se repartió a los jugadores, hay que volver a aplicar el preset con `--replace` en la base
  del cliente y publicar otra vez (sección 10). Hasta entonces verán el sprite anterior.

## 10. Después del sprite

1. Monstruo: XML, ataques, `monsters.xml`, paleta de RME y doc propio. Ver
   [`CUSTOM_MONSTER_WORKFLOW.md`](CUSTOM_MONSTER_WORKFLOW.md) (checklist en §10).
2. **Dejar lo aprendido para la próxima vez** (sistema *self-learning* de `AGENTS.md`):
   - Docstring del preset: qué base, qué cambia y el doc del monstruo.
   - Si el base es nuevo y se separó en partes: su clasificador en `BASE_PARTS` de `sprite_kit.py` y una
     fila en la sección 6.
   - Un truco nuevo que valga la pena: una fila en la sección 5. Un error que costó: en la sección 11.
   - `python3 scripts/client-rme/sprite_tool.py bases --write` para regenerar `SPRITE_BASES.md`.
3. Cliente de jugadores, **antes** del spawn: aplicar el preset a la base del cliente, regenerar y
   publicar ([`CUSTOM_MONSTER_WORKFLOW.md`](CUSTOM_MONSTER_WORKFLOW.md) §6.6). Con un cliente viejo el
   monstruo se ve invisible. Para comprobar que una copia del cliente ya tiene los looks:
   `sprite_tool.py --things CARPETA_DEL_CLIENTE/data/things/760 looks`.

## 11. Errores que ya pasaron

| Qué pasó | Cómo evitarlo |
|----------|---------------|
| Un punto dorado en la capucha del Tide Priest: el brillo violeta de la capucha entró en la parte "claro" | Revisar el mapa de partes de `inspect`. Se arregló pidiendo `h < 0.5` |
| Los ojos no se veían: la cara era casi tan clara como los ojos | Oscurecer la paleta de la parte donde va un detalle brillante |
| El ojo de perfil quedaba metido en la cara | De perfil va en el borde; `f.eyes` ya lo hace así |
| El doc decía "2 o 3 píxeles" y el código hacía siempre 3 | Después de ajustar el código, releer el doc del monstruo |
| Cambié el preset y el archivo no cambió | El look ya existía: usar `--replace` |
| Quedaron `Tibia.*.bak-*` sin borrar | `verify` avisa; borrarlos antes de commitear |
| Una criatura de la escena quedó sobre una pared | Elegir casillas caminables en `--at` |
| `ice_monk_eyes` usa ancho 64 fijo | Solo sirve para bases 2×2. En código nuevo, `f.w` o `f.eyes` |
| Se spawnearon looks nuevos sin publicar el cliente | El monstruo sale invisible. El cliente va primero (sección 10) |
| IA generativa para repintar la hoja (nano banana) | No sirve para sprites animados: cambia la silueta y los detalles entre cuadros. Detalle en [`CUSTOM_MONSTER_WORKFLOW.md`](CUSTOM_MONSTER_WORKFLOW.md) §6.5 |
