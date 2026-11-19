# Elvenbane

Documentación completa de la zona. Rama `elvenbane`, generador
`scripts/map/generate-elvenbane.py`, manifiesto
`server/YurOTS/ots/data/world/generated-elvenbane.json`. Semilla `--seed 76`.

**Regla (pedido de Gonzalo, 15-11-2026):** *Elvenbane usa en todas partes el estilo de
escalera de mano de la entrada.* No se usan escaleras de piedra (`1385`), de madera (`1396`/`432`)
ni rampas (`3685`/`3687`). Las 19 conexiones entre pisos son escalera de mano:

- **Entrada** (única excepción de ids, mismo estilo visual de “bajada + escalera de mano”):
  buraco `469` arriba + `1386` abajo, rodeado de 4 piedras `1285`.
- **Las otras 18:** hueco con marco de madera `409` arriba + `1386` abajo, sin piedras.

Ver también [STAIRS.md](../gameplay/STAIRS.md) y el resumen operativo en
[MAPEAR_ELVENBANE.md](MAPEAR_ELVENBANE.md). Referencias de planta: `img/elvenbane-ref/`.

## Cajas (bounds)

Elvenbane ocupa una zona que estaba vacía en z4–z10. No se pisa nada fuera de estas cajas
(el generador se niega a escribir si encuentra tiles preexistentes, salvo `--force`).

| Pisos | x | y | Qué cubre |
|-------|---|---|-----------|
| z7 | 4–84 | 282–362 | Isla del castillo + agua + tierra firme de la entrada |
| z8 | 30–67 | 288–349 | Túnel N–S + sótano -1 bajo el castillo |
| z9 y z10 | 33–67 | 291–322 | Sótano -2 y prisión -3 |
| z4, z5, z6 | 38–62 | 296–317 | Adarve, torretas y torre central |

Castillo (muralla): esquina NO `40,298`, tamaño 21×18, hasta `60,315`.

La caja de z7 se agrandó a **x 4–84 / y 282–362** (antes 12–82 / 282–362) para que entren el brazo
noreste de la isla (llega a x 74) y el suroeste de la tierra firme (llega a x 11). Cada ampliación se
verificó vacía en z4–z10 con el parser antes de escribir; al norte no se pasa de y 282 (en y 260,
z10, hay tiles de otra zona que no se tocan).

**Vecinos:** Valle de las Bestias (x 262–361, y 232–378, al este; Elvenbane termina en x 84 de caja, tierra hasta x 74);
Reloj de Arena (x 328–348, y 383–401, sureste); templo / plaza de portales (x 146–178, y 36–62,
noroeste). El portal de la plaza es `157,47,7`. Si se mergean ramas, no mergear el `.otbm`
binario: correr los generadores en secuencia sobre el mapa de `main` y después `temple-portals.py`.
Otras ramas también pueden querer el slot `157`: resolverlo al unir.

## Portales y llegada

| Qué | Coordenadas |
|-----|-------------|
| Portal en la plaza del templo | `157,47,7` → llegada `39,346,7` |
| Llegada (claro en la tierra firme, al sur de la bajada) | `39,346,7` |
| Portales de vuelta, junto a la llegada | `41,347,7` y `42,347,7` → `157,48,7` |
| Carteles | junto a la llegada y a la bajada (`readables.xml`, bloque `ELVENBANE_SIGNS`) |

Entre la llegada, la bajada `39,340` y los portales de vuelta hay un corredor caminable de 1–2
casillas. El anillo de piedra de los portales queda libre de bosque.

## Plantas por piso

Plantas tomadas de los minimapas de TibiaWiki (3 px = 1 sqm), convertidas a ASCII en
`img/elvenbane-ref/elvenbane_ascii.md` (`~` agua, `.` pasto, `T` árbol, `_` piedra, `#` pared,
`=` tierra de cueva, `^` roca, `S` cambio de piso).

| Piso | Nombre | Layout |
|------|--------|--------|
| z7 sur | Tierra firme / entrada | Bosque denso con montañitas de roca (`4566`+`906`/`903`), brazo de agua al oeste (`WEST_ARM`, x 26→35) y el suroeste del ASCII `entrance` (recorte cols 10–52 → x 11–53), llegada del portal, 2 portales de vuelta y el buraco de la entrada `39,340`. Costa con orilla `4644–4655`. |
| z7 norte | Isla del castillo | **Silueta tomada de la máscara de tierra del ASCII `ground`** (la del minimapa), alineada a la muralla: castillo + lóbulo de bosque largo al **noreste/este** (cols 44–60 del ASCII, hasta x 74) + **costa oeste de varias casillas** (cols 10–22, x 27–39) + franja sur y explanada de piedra. No se come la costa con ruido: la silueta es la del minimapa (sin islotes sueltos ni bolsones). Agua continua entre isla y tierra firme (canal y 321–325): el único acceso es el túnel de z8. |
| z8 | Túnel + sótano -1 | Pasillo largo N–S desde la entrada (sur) hasta el sótano rectangular bajo el castillo (norte). Sube al patio y baja al -2. |
| z9 | Sótano -2 | Salas bajo el castillo. Sube al -1 y baja a la prisión. |
| z10 | Prisión -3 | Celdas 2×3 al norte y al centro (las que el minimapa dibuja cerradas se abren como piso, `PRISON_DOORS`) y sala grande al sur. |
| z6 | Adarve (piso +1) | Anillo de muralla en las 4 esquinas + torre central. |
| z5 | Piso +2 | 4 torretas de esquina + torre central. |
| z4 | Cima (piso +3) | 4 torretas + cima de la torre (el Dragon). |

z7: pasto `4756` (costa `4526`), agua `4608`, piedra `431`, paredes `1049–1053`, montañitas de
roca `4566` con pared `906` al norte y `903` al oeste. z8–z10: tierra `351`/`352` y paredes de
cueva `356–367`. Vegetación (solo fuera de la muralla, sobre pasto): pinos `4009` con separación
Chebyshev ≥ 2 entre anclas (las copas 2x2 se tocan pero no se superponen), arbolitos `2768`,
arbustos `2767`/`2786`, flores `4158`/`4150`/`2740`. Ninguna casilla con vegetación que bloquee
tiene otra al lado (así el bosque se ve lleno y el pasto queda siempre transitable); ~44 % de las
casillas de bosque con algo encima, sin claros grandes.

**Poison fields (`1490`) en el primer piso de la torre (z6):** la quest clásica dice que el
primer piso de la torre central está cubierto de poison fields. Van en **todas las casillas
caminables del interior de la torre** en z6 salvo las dos escaleras: **27 casillas**, x 48–53,
y 303–307 (el adarve y las torretas quedan sin field). `1490` sólo tiene `block_pathfind`, así
que no rompe el BFS ni los spawns, y `destroyfield.lua` ya lo limpia.

## Escaleras (las 19 conexiones)

Al usar `1386` se sube a `(x, y+1, z-1)` (`LADDERS_UP` en `data/actions/scripts/teleport.lua`).
Al bajar por `409` o `469` se cae en la misma casilla `(x, y, z+1)`, porque `1386` no está en
`STAIRS_LANDING` (offset 0). Las dos llegadas de cada par son caminables.

Por qué este tipo: en Tibia clásico la entrada de Elvenbane es un buraco rodeado de cuatro
piedras, con escalera de mano abajo (TibiaWiki / TibiaQA). Gonzalo pidió primero “otro tipo de
escaleras” (no las rampas `3685` ni las de piedra claras `1385`) y después que *la escalera del
principio esté en todas partes*. Quedó escalera de mano en los 19 links.

| Etiqueta | Arriba (bajada) | Abajo (1386) | Llegada al subir | Llegada al bajar |
|----------|-----------------|--------------|------------------|------------------|
| entrada | `469` en `39,340,7` | `39,340,8` | `39,341,7` | `39,340,8` |
| sotano→patio | `409` en `57,303,7` | `57,303,8` | `57,304,7` | `57,303,8` |
| sotano→-2 | `409` en `58,313,8` | `58,313,9` | `58,314,8` | `58,313,9` |
| -2→-3 | `409` en `42,312,9` | `42,312,10` | `42,313,9` | `42,312,10` |
| patio→adarve NO | `409` en `42,299,6` | `42,299,7` | `42,300,6` | `42,299,7` |
| patio→adarve NE | `409` en `57,299,6` | `57,299,7` | `57,300,6` | `57,299,7` |
| patio→adarve SO | `409` en `43,312,6` | `43,312,7` | `43,313,6` | `43,312,7` |
| patio→adarve SE | `409` en `57,312,6` | `57,312,7` | `57,313,6` | `57,312,7` |
| torre→adarve | `409` en `53,304,6` | `53,304,7` | `53,305,6` | `53,304,7` |
| adarve→torreta NO | `409` en `43,299,5` | `43,299,6` | `43,300,5` | `43,299,6` |
| adarve→torreta NE | `409` en `58,299,5` | `58,299,6` | `58,300,5` | `58,299,6` |
| adarve→torreta SO | `409` en `42,313,5` | `42,313,6` | `42,314,5` | `42,313,6` |
| adarve→torreta SE | `409` en `58,313,5` | `58,313,6` | `58,314,5` | `58,313,6` |
| torre adarve→2 | `409` en `48,304,5` | `48,304,6` | `48,305,5` | `48,304,6` |
| torreta NO→3 | `409` en `42,299,4` | `42,299,5` | `42,300,4` | `42,299,5` |
| torreta NE→3 | `409` en `57,299,4` | `57,299,5` | `57,300,4` | `57,299,5` |
| torreta SO→3 | `409` en `42,312,4` | `42,312,5` | `42,313,4` | `42,312,5` |
| torreta SE→3 | `409` en `58,312,4` | `58,312,5` | `58,313,4` | `58,312,5` |
| torre 2→3 | `409` en `52,303,4` | `52,303,5` | `52,304,4` | `52,303,5` |

La entrada lleva 4 piedras `1285` en oeste, este, noroeste y noreste; el sur queda libre (es la
llegada de la `1386`). En Tibia oficial el buraco empieza como montículo `468` y la pala lo abre a
`469` (`shovel.lua`); en este OT `469` no tiene decay configurado, así que queda abierto.

`resolve_stair()` mueve un `S` del ASCII si la llegada caería en pared. Reubicadas (todas a 1
casilla, guardadas en `relocated` del manifiesto): `sotano→patio` 57,302→57,303; `sotano→-2`
57,313→58,313; `torreta NE→3` 58,299→57,299; `torre 2→3` 53,303→52,303.

## Spawns

50 spawns, 81 monstruos, todos sobre casilla caminable, lejos de llegadas y escaleras. Bloque
`ELVENBANE_SPAWNS` en `test-spawn.xml`.

| Piso | Spawns | Monstruos (cantidad) |
|------|--------|----------------------|
| z7 | 15 | Wasp 4, Orc 4, Orc Spearman 2, Orc Warrior 8, Elf 2, Elf Scout 1, Minotaur 4, Minotaur Guard 1, Orc Berserker 1 |
| z8 | 9 | Troll 4, Orc 4, Orc Spearman 2, Orc Warrior 4, Dwarf 1, Minotaur 2 |
| z9 | 6 | Orc 4, Minotaur 4, Orc Warrior 4 |
| z10 | 6 | Minotaur 4, Orc Warrior 4, Minotaur Guard 2 |
| z6 | 3 | Minotaur 2, Orc Warrior 1 (sobre los poison fields) |
| z5 | 6 | **Dragon 1** (torre central), Elf 1, Elf Scout 1, Orc Warrior 2, Orc Shaman 1, Elf Arcanist 1 |
| z4 | 5 | **Uno fuerte y distinto por cima** (fijos, `TOWER_TOPS`): Black Knight (torreta NO, `43,301`), Dragon Lord (NE, `59,301`), Hydra (SO, `43,314`), Behemoth (SE, `57,314`) con respawn 15 min, y **Demon** en la cima de la torre central (`49,308`, 30 min) |

La dificultad sube de la entrada hacia el castillo y de los sótanos hacia la cima. El **Dragon está
en la torre central de z5**, el piso inmediatamente arriba de los poison fields de z6 (como la quest
clásica). Desde nov 2026 las cimas de z4 no se sortean: cada torre tiene su monstruo fuerte fijo, en la
casilla más lejos de su escalera (antes había Orc Berserker, Hunter, Minotaur Archer, Minotaur Mage y Demon
Skeleton, y la torreta SE quedaba vacía).

## Cómo regenerar

Worktree: `~/proyectos/serverrepo-elvenbane`, rama `elvenbane`. No compilar, no docker, no deploy,
no `git push`.

```bash
python3 scripts/map/generate-elvenbane.py --dry-run
# valida (escaleras, BFS, orilla, 919, spawns) y no escribe

python3 scripts/map/generate-elvenbane.py --preview docs/items-and-map/img/elvenbane
# escribe test.otbm, test-spawn.xml, el manifiesto y dibuja z4..z10.png

python3 scripts/map/temple-portals.py
# portal 157,47,7 en la plaza y el cartel

python3 scripts/map/check-map-load.py
python3 scripts/map/validate-tele-dest.py server/YurOTS/ots/data/world/test.otbm
```

Determinista con `--seed 76`. La primera escritura hace backup `test.otbm.bak-elvenbane` (no va a
git). Si `test.otbm` cambió en `main`, no mergear el binario: correr el generador sobre el mapa
nuevo y después `temple-portals.py`.

## Validaciones (última corrida, 2026-11-15)

El propio generador, si algo falla, no escribe el `.otbm`.

| Chequeo | Cómo | Resultado |
|---------|------|-----------|
| Pares de escalera | 18× `409+1386` y 1× `469+1386`; ambas llegadas caminables | 0 errores |
| Sin ids viejos | no quedan `432`, `1396`, `3685`, `1385`, `3687` en la caja | 0 |
| BFS multi-piso | desde `39,346,7`, siguiendo `409`/`469` hacia abajo y `1386` hacia `(x,y+1,z-1)` | 2312 caminables, 2312 alcanzables, 0 perdidas |
| Spawns | 81 monstruos sobre piso caminable | 0 errores |
| Orilla | `pieces_for()` exacto en toda la costa pasto↔agua | OK |
| Ground `919` | se veía como vacío negro | 0 |
| Patio del castillo | sin árboles/arbustos/flores dentro de la muralla 21×18 | OK |
| Poison fields | interior de la torre z6 con `1490` salvo escaleras | 27/27 |
| Dragon | 1 en la torre central de z5 (`48,306`), 0 en z4 | OK |
| `check-map-load.py` | carga offline del mapa | 0 errores |
| `validate-tele-dest.py` | destinos de los teleport | OK |
| Idempotencia | dos corridas del generador | mismo md5 del `.otbm` |

Falta deploy y recorrido in-game. Antes de deployar un `test.otbm` nuevo, probar depots
([DEPOTS.md](../gameplay/DEPOTS.md)).

## Renders

Minimapas en planta (los escribe el generador, van al repo):

```bash
python3 scripts/map/generate-elvenbane.py --preview docs/items-and-map/img/elvenbane
```

Quedan `docs/items-and-map/img/elvenbane/z4.png` … `z10.png`. No usan sprites de cliente.

Los renders con sprites de 7.6 se arman aparte, sobre el `test.otbm`, con
`scripts/map/game_render.py` / `render_area.py` (en el box de revisión:
`/workspace/elvenbane/review/render_area.py`, sprites en `devtools/rme/rme-client-760/`).
No van al git. Caja de recorte (BOX7 con padding) y escala:

```bash
# pisos z4–z10, escala 14
python3 render_area.py server/YurOTS/ots/data/world/test.otbm /tmp/elv-r8 \
  16 284 76 362 4,5,6,7,8,9,10 14

# close-ups de escaleras, 9×9 casillas, escala 24
python3 render_area.py …/test.otbm /tmp/elv-stairs-r8/entrada 35 336 43 344 7,8 24   # 39,340
python3 render_area.py …/test.otbm /tmp/elv-stairs-r8/patio   53 299 61 307 7,8 24   # 57,303
python3 render_area.py …/test.otbm /tmp/elv-stairs-r8/adarve  38 296 46 304 6,7 24   # 42,299
python3 render_area.py …/test.otbm /tmp/elv-stairs-r8/torre   48 299 56 307 4,5 24   # 52,303
```

Salida (última pasada, 15-11-2026, commit de mapa `834bf52`):
`/workspace/serverrepo-renders/elvenbane/final/`

| Archivo | Qué muestra |
|---------|-------------|
| `z4.jpg` … `z10.jpg` | Cada piso, caja 16–76 × 284–362, escala 14 |
| `z7-crop.jpg` | z7 recortado 15 px a la derecha y abajo |
| `isla.jpg` | Castillo e isla (recorte de z7) |
| `main.jpg` | Tierra firme, llegada y buraco de entrada (recorte de z7) |
| `upper.jpg` | z6, z5 y z4 lado a lado |
| `under.jpg` | z8, z9 y z10 lado a lado |
| `stairs-entrada.jpg` | Entrada `469` + 4 piedras / `1386` abajo |
| `stairs-patio.jpg` | Sótano→patio `409` / `1386` en `57,303` |
| `stairs-adarve.jpg` | Patio→adarve NO `409` / `1386` en `42,299` |
| `stairs-torre.jpg` | Torre 2→3 `409` / `1386` en `52,303` |

## Qué queda distinto de la referencia (TibiaWiki)

Cerca, no idéntico:

- La isla sigue la máscara del minimapa; el brazo noreste llega hasta x 74 (el ASCII termina en
  x 77 con dos islotes sueltos que se descartan para no dejar tierra aislada).
- La tierra firme usa el recorte cols 10–52 del ASCII `entrance` (x 11–53): falta el extremo más
  al oeste (cols 0–9, x 1–10) porque el borde del mapa no deja margen para la cámara.
- En Tibia oficial el buraco de la entrada es un montículo `468` que se abre con pala y se vuelve a
  cerrar; acá el `469` queda abierto (no hay decay configurado para 469).


## Estado

Generada y validada en local (15-11-2026). Sin push ni deploy.
