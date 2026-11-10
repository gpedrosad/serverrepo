# Sprites de criaturas: receta para crear y editar

Guía corta para hacer o cambiar el sprite de un monstruo **sin volver a investigar nada**. Está escrita
para que una IA (o una persona) la siga de arriba abajo. El método es siempre el mismo: tomar una
criatura que ya existe en el cliente 7.6, cambiarle los colores por algoritmo y agregarle un rasgo propio.

- Script que crea el look: `scripts/client-rme/add_recolor_look.py` (un *preset* por criatura).
- Herramienta para mirar, comparar y verificar: `scripts/client-rme/sprite_tool.py`.
- Ninguno necesita instalar nada (`python3` solo, sin Pillow) y cada comando tarda menos de 3 segundos.

El resto del monstruo (XML, ataques, loot, spawn) está en [`CUSTOM_MONSTER_WORKFLOW.md`](CUSTOM_MONSTER_WORKFLOW.md).

## 1. Los comandos, en orden

```bash
T=scripts/client-rme/sprite_tool.py
python3 $T looks                              # 1. looktype libre para el destino
python3 $T looks --all                        #    y qué look usa cada monstruo, para elegir el base
python3 $T inspect 18                         # 2. entender el base en texto (colores, partes, mapa)
#                                               3. escribir el preset en add_recolor_look.py (sección 4)
python3 $T inspect mi-preset                  # 4. comprobar en texto que las partes quedaron bien separadas
python3 $T sheet mi-preset /tmp/hoja.png      # 5. original | nuevo, ampliado (mirar la imagen)
python3 $T scene mi-preset /tmp/escena.png    # 6. a tamaño de juego sobre el mapa real (mirar la imagen)
python3 scripts/client-rme/add_recolor_look.py --preset mi-preset devtools/rme/rme-client-760   # 7. aplicar
python3 $T verify --expect 235                # 8. comprobar que no se rompió nada más
rm devtools/rme/rme-client-760/*.bak-*        # 9. borrar los respaldos antes de commitear
```

**Para gastar poco:** entender el sprite con `inspect` (texto, da coordenadas exactas) y mirar imágenes
solo dos veces por vuelta: la hoja y la escena. No hacen falta scripts sueltos ni ampliar cuadro por cuadro.

## 2. Datos fijos (no hay que redescubrirlos)

| Dato | Valor |
|------|-------|
| Cuadros de una criatura | 12: 4 direcciones × 3 cuadros de animación (quieto + 2 de caminar) |
| Índice del cuadro | `anim * 4 + direction` |
| Direcciones | 0 norte (de espaldas), 1 este, 2 sur (de frente), 3 oeste |
| Tamaño | 1×1 = cuadros de 32×32 px (12 sprites); 2×2 = cuadros de 64×64 px (48 sprites) |
| Píxel | `(r, g, b, a)` con `a` 0 o 255. **No hay transparencia parcial** |
| Índice del píxel | `y * w + x`, con `w` = 32 o 64 |
| Perspectiva | La figura va inclinada en diagonal, con la cabeza arriba a la izquierda. Es normal |
| Looktype máximo | 255 (viaja en un byte). Usados: 230 Black Dragon, 231 Frost Dragon, 232 Ice Monk, 233 Drowned Sailor, 234 Tide Priest |
| Formas admitidas | Solo 1×1 y 2×2 con 4 direcciones y 3 cuadros. `looks --all` marca las demás como "otra" (Slime, Rotworm, Wasp, Fire Elemental…): no sirven de base |

Ojo: algunas criaturas que parecen de una casilla están guardadas como 2×2 (el Monk, 57). `inspect` lo dice
en la primera línea.

## 3. Elegir base y destino

- **Destino:** el "Próximo libre sugerido" de `looks`. Ya descarta los que usa algún monstruo o NPC.
- **Base:** una criatura con la silueta que se busca. Sirve más una que lleve algo en la mano o tenga
  zonas de color bien separadas, porque ahí se cuelga el rasgo propio.
- **Qué hace que no se vea "típico":** cambiar solo los colores no alcanza. Hace falta **un elemento
  agregado o reemplazado** que se note a tamaño de juego. Ejemplos ya hechos: la calavera del Necromancer
  pasó a ser una bola de fuego celeste (Tide Priest), y el Crypt Shambler ganó pañuelo, camiseta rayada
  y algas (Drowned Sailor).

## 4. Escribir el preset

Un preset es una entrada del diccionario `PRESETS` de `add_recolor_look.py`:

```python
"ash-ghoul": dict(source=18, target=235, recolor=recolor_ash_ghoul, name="Ash Ghoul",
                  frames_post=ash_ghoul_details, parts=_ghoul_part),
```

| Clave | Qué es |
|-------|--------|
| `source` / `target` | Looktype base y looktype libre de destino |
| `recolor(pixel)` | Devuelve el color nuevo de **un** píxel. Los transparentes se devuelven tal cual |
| `frames_post(original, recolored)` | Opcional. Recibe los 12 cuadros originales y los 12 ya recoloreados, y devuelve los 12 finales. Acá va el rasgo propio |
| `parts(pixel)` | Opcional pero conviene. Dice a qué parte pertenece un píxel; `inspect` lo usa para el mapa de partes |

Plantilla completa y probada (Ghoul → ghoul de ceniza con heridas como brasas). Copiarla, cambiar los
nombres y ajustar:

```python
ASH_BODY = [(0, (8, 8, 12)), (0.4, (58, 58, 66)), (0.75, (126, 124, 128)), (1, (206, 202, 196))]   # oscuro -> claro
EMBER = [(0, (120, 30, 0)), (0.5, (236, 110, 20)), (1, (255, 226, 120))]


def _ghoul_part(pixel):
    """Partes del Ghoul (18): contorno, heridas rojas o cuerpo."""
    if pixel[3] == 0:
        return None
    h, s, v = hsv(pixel)
    if v < 0.13:
        return "dark"
    if h < 0.04 and s > 0.6:
        return "wound"
    return "body"


def recolor_ash_ghoul(pixel):
    part = _ghoul_part(pixel)
    if part is None:
        return pixel                                           # transparente: no se toca
    _h, _s, v = hsv(pixel)
    if part == "dark":
        return pixel                                           # el contorno queda igual
    if part == "wound":
        return gradient(EMBER, (v - 0.13) / 0.27) + (255,)     # brillo de la parte (0.13-0.40) llevado a 0-1
    return gradient(ASH_BODY, v ** 0.9) + (255,)


def ash_ghoul_details(original, recolored):
    w = int(len(original[0]) ** 0.5)                           # 32 (1x1) o 64 (2x2)
    out = []
    for index, (orig, new) in enumerate(zip(original, recolored)):
        anim, direction = index // 4, index % 4
        new = list(new)
        parts = [_ghoul_part(p) for p in orig]
        wounds = _clusters(part_points(parts, "wound", w))
        if wounds:                                             # la brasa más grande late con la animación
            cx, cy = centroid(max(wounds, key=len))
            new[round(cy) * w + round(cx)] = ((255, 250, 200, 255), (255, 200, 90, 255), (255, 236, 150, 255))[anim]
        out.append(new)
    return out
```

Ayudas que ya existen en el script:

| Función | Para qué |
|---------|----------|
| `hsv(pixel)` | Tono, saturación y brillo de 0 a 1 |
| `gradient(stops, k)` | Color de una paleta `[(posición, (r, g, b)), …]` para `k` entre 0 y 1 |
| `part_points(parts, "nombre", w)` | Coordenadas `(x, y)` de los píxeles de una parte |
| `_clusters(points)` | Agrupa puntos que se tocan (también en diagonal). Devuelve una lista de grupos |
| `centroid(points)` | Centro de un grupo, con decimales |
| `_lum(pixel)` | Luminosidad percibida, de 0 a 1 |
| `CARD4` | Los 4 vecinos (arriba, abajo, izquierda, derecha) |

### Cómo separar las partes

1. Correr `inspect LOOK`. El "Resumen por letra de color" da, para cada familia de color, cuántos píxeles
   tiene y entre qué valores se mueven su tono (`h`), saturación (`s`) y brillo (`v`). De ahí salen los
   umbrales del clasificador.
2. Escribir `_xxx_part` con el caso más específico primero (ojos, piel) y el más general al final (cuerpo).
3. Registrar el preset y correr `inspect mi-preset`. Ahora el mapa usa una letra por parte y cada cuadro
   lista las partes con sus grupos, por ejemplo: `light: 79 px en 9 grupo(s); el mayor tiene 22 px, x 15-19,
   y 5-10, centro (16.8, 7.5)`.
4. **Revisar que no haya letras sueltas donde no corresponde.** Una letra de "calavera" en medio de la
   capucha es un umbral mal puesto, y después sale como una mota de otro color.

### Cómo armar la paleta

- Cada parte usa su propia paleta, de oscuro a claro, con 3 a 5 colores.
- La posición en la paleta sale del brillo original, así se conservan las sombras y el volumen.
- **Llevar el brillo de la parte al rango 0-1.** Si la túnica solo va de `v` 0 a 0.3 (lo dice el "Resumen
  por parte"), usar `(v / 0.3)`. Si no, toda la parte cae en el extremo oscuro de la paleta y queda plana.
- El exponente ajusta el contraste: menor que 1 aclara (`** 0.8`), mayor que 1 oscurece (`** 1.15`).
- Si el sprite va a vivir en un suelo oscuro, subir el extremo claro de la paleta para que no se pierda.

## 5. Trucos que ya funcionaron

Todos están en `add_recolor_look.py`; conviene copiar de ahí antes que inventar.

| Truco | Cómo | Dónde verlo |
|-------|------|-------------|
| Cambiar un detalle que identifica (ojos, lengua) | Clasificar el rojo intenso aparte y darle un color fijo | `recolor_frost` |
| Encontrar un objeto o la cara | El **grupo más grande** de una parte (`max(grupos, key=len)`) | `tide_priest_details` (calavera, cara) |
| Encontrar la cabeza | El grupo de piel "gruesa" que está más arriba. Gruesa = píxeles con los 4 vecinos de piel, así no cuentan los brazos | `drowned_sailor_details` |
| Reemplazar un objeto por un orbe | Disco con degradé desde el centro; el radio cambia con `anim` para que lata | `tide_priest_details` |
| Resplandor | Mezclar hacia el color de la luz solo los píxeles **opacos** cercanos, con más fuerza cuanto más cerca | `tide_priest_details` |
| Chispas o llama que se mueven | Píxeles sueltos cuya posición depende de `anim` (ángulo o desplazamiento) | `tide_priest_details` |
| Ojos que brillan | Fila a un tercio de la cara desde arriba. Dos de frente (sur), uno de perfil (este) en el borde, ninguno de espaldas | `tide_priest_details`, `ice_monk_eyes` |
| Cara en sombra | Pintar toda la cara de un color oscuro y encima los ojos | `ice_monk_eyes` |
| Ropa rayada | Franjas que siguen la diagonal: `((y + x // 3) // 2) % 2` | `drowned_sailor_details` |
| Prenda sobre la cabeza | Pintar la mitad de arriba de la cabeza; de espaldas, más | `drowned_sailor_details` (pañuelo) |
| Cosas que cuelgan | Desde el borde de abajo de la silueta, pintar hacia abajo en píxeles transparentes | `drowned_sailor_details` (algas, gotas) |
| Motas fijas | Tomar 3 píxeles del cuerpo repartidos y pintarlos con luz y sombra | `drowned_sailor_details` (percebes) |

Reglas para que se vea bien a tamaño de juego:

- Un rasgo de 1 o 2 píxeles solo se nota si tiene mucho contraste (claro sobre oscuro). Si no, que ocupe
  unos 5×5 píxeles.
- Lo que cambia entre cuadros de animación debe moverse 1 píxel como mucho. Más que eso parpadea.
- Tratar cada dirección aparte: de espaldas y mirando al oeste casi nunca se ve la cara.
- Se puede pintar fuera de la silueta, pero no fuera del cuadro (32 o 64 píxeles).
- **Nunca usar `random`.** Para variar, usar fórmulas con `x`, `y`, `anim` y `direction`
  (ej. `(x * 7 + y * 13 + direction * 3) % 9 == 0`). El resultado tiene que salir igual cada vez, porque
  `verify` comprueba que cada preset vuelva a generar exactamente su look.

## 6. Bases ya estudiadas

Umbrales que ya se probaron. Si el base es uno de estos, reusar el clasificador.

| Base | Forma | Partes y umbrales | Clasificador |
|------|-------|-------------------|--------------|
| Dragon (34) | 2×2 | Ojos, lengua y garras: `(h < 0.09 o h > 0.95), s > 0.6, v > 0.5`. Panza y alas: `0.06 < h < 0.2, s > 0.35`. Cuerpo verde: el resto | dentro de `recolor_frost` |
| Monk (57) | 2×2 | Cara y manos: `0.06 ≤ h ≤ 0.10, 0.28 ≤ s ≤ 0.47, v > 0.74`. Cinturón: `0.095 ≤ h ≤ 0.13, s > 0.47, v > 0.76`. Túnica marrón: el resto | `_is_skin`, `recolor_ice_monk` |
| Crypt Shambler (100) | 1×1 | Contorno: `v < 0.13`. Pantalón verde: `0.2 < h < 0.55, s > 0.25`. Heridas: `(h < 0.04 o h > 0.93), s > 0.6`. Piel: el resto | `_shambler_part` |
| Necromancer (9) | 1×1 | Cara: `0.03 < h < 0.13, s > 0.3, v > 0.35`. Claro (calavera, manos, botas, ribete): `v ≥ 0.3, h < 0.5`. Túnica: el resto, con brillo solo de 0 a 0.3 | `_necro_part` |
| Ghoul (18) | 1×1 | Contorno: `v < 0.13`. Heridas: `h < 0.04, s > 0.6`. Cuerpo: el resto | plantilla de la sección 4 (no está en el script) |

## 7. Mirar el resultado

```bash
python3 $T sheet mi-preset /tmp/hoja.png
python3 $T scene mi-preset /tmp/escena.png
python3 $T scene mi-preset /tmp/escena.png --area 150,40,170,52,7 --at "154,46,s;158,46,e;162,46,s,orig"
```

- **`sheet`:** a la izquierda el original y a la derecha el nuevo. Columnas: norte, este, sur, oeste.
  Filas: los 3 cuadros de animación. Con un número de look en vez de un preset, muestra solo ese look.
- **`scene`:** dibuja el sprite sobre el mapa real (`test.otbm`) a tamaño de juego ×2. Sin opciones usa
  la bodega del naufragio, con el original al lado para comparar.
  - `--area x1,y1,x2,y2,z`: otra zona, en casillas.
  - `--at "x,y,dir[,cual[,anim]]"`, separadas por `;`: dónde va cada criatura. `dir` es `n`, `e`, `s` o
    `w`; `cual` es `new` (por omisión), `orig` o un número de looktype; `anim` es 0, 1 o 2.
  - Elegir casillas donde se pueda caminar: si no, la criatura queda dibujada sobre una pared.
- `inspect mi-preset --new` muestra en texto el sprite **nuevo** (por colores), para confirmar un detalle
  píxel a píxel sin abrir una imagen.

Qué revisar en la escena: que se distinga del original de un vistazo, que el rasgo propio se lea y que no
se pierda contra el suelo donde va a vivir.

Para el doc del monstruo, las mismas dos imágenes sirven:
`docs/gameplay/img/NOMBRE.png` (hoja) y `docs/gameplay/img/NOMBRE-LUGAR.png` (escena).

## 8. Aplicar y verificar

```bash
python3 scripts/client-rme/add_recolor_look.py --preset mi-preset devtools/rme/rme-client-760
python3 scripts/client-rme/sprite_tool.py verify --expect 235
rm devtools/rme/rme-client-760/*.bak-*
```

`verify` compara `Tibia.dat` / `Tibia.spr` de RME contra el último commit (`--base main` para otra
referencia) y termina con `TODO BIEN` o con la lista de problemas. Comprueba:

- Cantidades de ítems, looktypes, efectos y proyectiles sin cambios.
- Ítems, efectos y proyectiles idénticos byte a byte.
- Qué looktypes cambiaron (con `--expect` falla si no son exactamente esos).
- Todos los sprites viejos idénticos.
- Cada preset vuelve a generar exactamente el look que está en el archivo.
- No quedaron respaldos `.bak-*`.

`Tibia.dat` y `Tibia.spr` de `devtools/rme/rme-client-760/` sí van a git.

## 9. Editar un sprite que ya existe

Cambiar la paleta o el retoque en el preset y volver a aplicarlo con `--replace`:

```bash
python3 $T sheet tide-priest /tmp/hoja.png                # ver el cambio antes de escribir nada
python3 scripts/client-rme/add_recolor_look.py --preset tide-priest devtools/rme/rme-client-760 --replace
python3 $T verify --expect 234
rm devtools/rme/rme-client-760/*.bak-*
```

- `--replace` rehace solo los sprites de ese look. Los ids no cambian y el resto del archivo queda igual.
- Sin `--replace` el script no toca un look que ya tiene sprites (por eso es seguro correrlo dos veces).
- Si el look ya se repartió a los jugadores, hay que volver a aplicar el preset con `--replace` en la base
  del cliente y publicar otra vez (sección 10). Hasta entonces verán el sprite anterior.
- `add_black_dragon_look.py` es el script original del Black Dragon y queda como referencia. Para editar
  el 230 se usa el preset `black-dragon`, que genera lo mismo.

## 10. Después del sprite

1. Monstruo: XML, ataques, `monsters.xml`, paleta de RME y doc propio. Ver
   [`CUSTOM_MONSTER_WORKFLOW.md`](CUSTOM_MONSTER_WORKFLOW.md) (checklist en §10).
2. Anotar el preset en el docstring de `add_recolor_look.py`, el look usado en la tabla de la sección 2
   y, si el base es nuevo, sus umbrales en la sección 6.
3. Cliente de jugadores, **antes** del spawn: aplicar el preset a `client-local/data/things/760/`,
   correr `build_zagan_test_assets.py` y publicar en el updater
   ([`CUSTOM_MONSTER_WORKFLOW.md`](CUSTOM_MONSTER_WORKFLOW.md) §6.6). Con un cliente viejo el monstruo se
   ve invisible.

## 11. Errores que ya pasaron

| Qué pasó | Cómo evitarlo |
|----------|---------------|
| Un punto dorado en la capucha del Tide Priest: el brillo violeta de la capucha entró en la parte "claro" | Revisar el mapa de partes de `inspect`. Se arregló pidiendo `h < 0.5` |
| Los ojos no se veían: la cara era casi tan clara como los ojos | Oscurecer la paleta de la parte donde va un detalle brillante |
| El ojo de perfil quedaba metido en la cara | De perfil va en el borde (`xs[-1]`), no un píxel adentro |
| El doc decía "2 o 3 píxeles" y el código hacía siempre 3 | Después de ajustar el código, releer el doc del monstruo |
| Cambié el preset y el archivo no cambió | El look ya existía: usar `--replace` |
| Quedaron `Tibia.*.bak-*` sin borrar | `verify` avisa; borrarlos antes de commitear |
| Una criatura de la escena quedó sobre una pared | Elegir casillas caminables en `--at` |
| `ice_monk_eyes` usa ancho 64 fijo | Solo sirve para bases 2×2. En código nuevo: `w = int(len(original[0]) ** 0.5)` |
| IA generativa para repintar la hoja (nano banana) | No sirve para sprites animados: cambia la silueta y los detalles entre cuadros. Detalle en [`CUSTOM_MONSTER_WORKFLOW.md`](CUSTOM_MONSTER_WORKFLOW.md) §6.5 |
