# Dark Cathedral

Documentación completa de la zona. Rama `dark-cathedral`, generador
`scripts/map/generate-dark-cathedral.py`, manifiesto
`server/YurOTS/ots/data/world/generated-dark-cathedral.json`. Semilla `--seed 76`.

Recreación de la **Dark Cathedral** de Tibia 7.6 en una zona que estaba vacía en z7–z9, con portal
desde la plaza de portales del templo. Resumen operativo en
[MAPEAR_DARK_CATHEDRAL.md](MAPEAR_DARK_CATHEDRAL.md). Referencias de planta en
`img/dark-cathedral-ref/` (`Dark_Cathedral_0.png` superficie, `Dark_Cathedral_1.png` piso -1,
`Resp-2DC.png` piso -2, `REFERENCIA_DARK_CATHEDRAL.md`).

**Reglas fijas (pedido de Gonzalo):** las coordenadas de portales, llegadas y escaleras **no se
mueven** entre iteraciones: llegada `148,335,7`, portal del templo `157,47,7`, vueltas `151,335,7` y
`147,345,9`, bajadas `148,295,7` y `128,336,7`, agujero al -2 `148,317,8`. Toda pared es de **una
casilla** (las salas se separan por exactamente una casilla) y nada se escribe fuera de la caja.

## Cajas (bounds)

Zona vacía en z7–z9; el generador **aborta** si encuentra casillas que no sean suyas (salvo que el
manifiesto tenga la misma caja, para poder re-ejecutarlo).

| Pisos | x (abs) | y (abs) | Local | Qué cubre |
|-------|---------|---------|-------|-----------|
| z7 | 118–177 | 284–353 | 0–59 × 0–69 | Jungla cerrada, nave, ruinas oeste/este, salón gris, explanada del portal, río del NE |
| z8 | 118–177 | 284–353 | 0–59 × 0–69 | Cripta -1: eje N-S, dos pasillos E-O, 16 salas, cueva natural del NE |
| z9 | 118–177 | 284–353 | 0–59 × 0–69 | Cripta -2: sala de columnas, octógono, brazos, anillo en zigzag, sala sur y final |

**Vecinos:** Valle de las Bestias (x 262–361, y 232–378, al este); Paso del Norte (x 370–469, al
este); Isla Natural (x 131–180, y 433–476, muy al sur); jungla de la ciudad / hydras (x 20–120,
y 60–160, al norte). La caja está aislada en zona vacía: no toca ninguna zona generada.

## Portales y llegada

| Qué | Coordenadas | Ítem |
|-----|-------------|------|
| Portal en la plaza del templo | `157,47,7` → llegada `148,335,7` | `1387` (teleport) |
| Llegada (explanada frente a la entrada sur de la nave) | `148,335,7` | — |
| Portal de vuelta, en la explanada | `151,335,7` → `157,48,7` | `1387` |
| Portal de vuelta, al fondo del -2 | `147,345,9` → `157,48,7` | `1387` |
| Carteles | `151,334,7` (llegada), `146,334,7` (nave), `136,340,7` (sala de los bancos), `146,292,7` (bajada de la jungla) | `1429` |

El portal de la plaza lo arma `scripts/map/temple-portals.py` (entrada `("catedral", 157, …)` en su
lista `PORTALS`, con la caja de la zona para reapuntar las vueltas). Los carteles viven en
`readables.xml`, bloque `DARK_CATHEDRAL_SIGNS`.

## Plantas por piso

Coordenadas absolutas (las locales del generador son `abs − (118,284)`).

### z7 — superficie

| Elemento | Caja | Notas |
|----------|------|-------|
| Nave (negra) | `145–152 × 305–332` | Mármol negro `407`, paredes de piedra `1049–1053`, 8 columnas de piedra, 2 filas de bancos `1662+1663`, estatuas `1442` en la entrada, entrada al sur `148–149,333` y brecha al norte `148–149,304` |
| Edificio oeste | `125–140 × 308–329` | 5 salas de tierra `103` con paredes de ladrillo, escombros, ataúdes `1410+1411`, cofre `1740` |
| Ruinas este | `156–168 × 308–321` | 4 salas chicas de tierra `103`, paredes de ladrillo |
| Sala gris del sur (bancos) | `135–150 × 339–345` | Losa `431`, dos filas de 6 bancos completos, escombros |
| Sala gris del oeste (bajada B) | `126–132 × 333–338` | Losa `431`, braseros `1486`, agujero `432` en `128,336` |
| Explanada de la llegada | `143–154 × 334–337` | Losa `431`, portal de vuelta y cartel |
| Rellano de la bajada A | `145–152 × 293–297` | Losa `431`, agujero `432` en `148,295`, braseros, camino de piedra hasta la brecha norte de la nave |
| Río | esquina NE (`x ≥ 156`, `y ≤ 296`) | Agua `4608` con orilla `4644–4655`; **no** hay marco de mar: el borde es jungla |
| Jungla | resto de la caja | Árboles `2701–2708`/`4009` plantados al azar (nunca dos copas pegadas), arbustos `2767`/`2786`, pinitos `2768`, y tapizado bajo `4158`/`4150`/`2740`/`4183`/`4171`/`4181`; franja de monte cerrado en el borde |

### z8 — cripta (-1)

| Elemento | Caja | Notas |
|----------|------|-------|
| Eje N-S | `147–149 × 295–308` · `146–148 × 308–322` · `146–148 × 323–341` | Tres tramos con quiebre; arriba en la escalera de la jungla, abajo entra en la sala T |
| Pasillo norte | `127–148 × 304–305` (oeste) y `149–165 × 306–307` (este) | En dos tramos, a distinta altura |
| Pasillo sur | `132–165 × 328–329` | Cruza el eje |
| Salas | A `128–134 × 296–302` · B `136–141 × 297–302` · C `127–133 × 307–314` · D `135–140 × 307–314` · K `150–155 × 309–315` · L `157–162 × 309–315` · M `127–133 × 316–326` · N `135–140 × 316–326` · O `150–156 × 317–326` · P `158–163 × 317–326` · Q `128–133 × 331–338` · R `135–141 × 331–336` (+ cola en L hasta `y 339`) · S `151–156 × 331–336` · U `158–163 × 331–336` | Losa `431` en pasillos y salas grises, tierra `103` en las otras; puertas de una casilla |
| Antecámara de la cueva | J `151–157 × 299–304` | Tierra, conecta el pasillo este con la cueva |
| Sala del fondo | T `141–155 × 343–348` | Losa `431`, cierre del eje |
| Cueva natural | `151–168 × 288–308` (143 casillas) | Seis cámaras irregulares unidas por pasillos (discos + conectores), piso de cueva `351`/`352`/`355`, paredes de roca `356–367`; boca de dos casillas en `154–155,298` hacia la antecámara J. Deja una casilla de pared contra las salas de ladrillo |

### z9 — cripta (-2)

| Elemento | Caja | Notas |
|----------|------|-------|
| Sala de las columnas | `135–160 × 292–308` | Losa `431`, 30 columnas (ítem `1514`) en 5 filas alternadas |
| Cuello | `145–150 × 309–313` | Mármol blanco `406` |
| Octógono de la escalera | `143–152 × 314–320` | Mármol blanco `406`, esquinas cortadas; escalera `1385` en `148,317`; **sin escombros** |
| Brazos de la cruz | `126–143 × 316–318` (oeste) y `152–163 × 316–318` (este) | Losa `431` |
| Salas en H (oeste) | `126–131 × 308–314` · `134–139 × 308–314` · `126–131 × 320–325` · `134–139 × 320–325` | Cuatro salas |
| Salas rombo (este) | `156–160 × 308–314` y `156–160 × 320–326` | Rectángulos con esquinas cortadas |
| Sala oval (este) | `162–169 × 310–324` | Elipse (borde escalonado como en 7.6) |
| Anillo en zigzag (oeste) | baja `142–143 × 318–328` · sale `134–143 × 328–329` · baja `134–135 × 329–336` · vuelve `134–143 × 336–337` | Espejado al este (`152–153`, `152–163`, `166–167`, `152–163`) |
| Salas del anillo | `126–132 × 327–332` y `126–132 × 334–339` (oeste); `163–169` (este) | Dos por lado |
| Pasillo central | `145–150 × 321–329` | Une el octógono con la sala grande del sur (cierra el hueco de roca) |
| Sala grande central sur | `142–153 × 330–341` | Mármol negro `407`; guardia de dark monks + demon skeleton |
| Sala final | `144–151 × 343–347` | Mármol negro `407`, portal de vuelta `147,345,9` |

Carteles, portales y escombros se colocan sólo sobre piso; el octógono, el pasillo central y las
llegadas de escalera quedan limpios (el generador excluye esas casillas del decorado).

## Escaleras y agujeros

Patrón estándar del mapa: **agujero `432` arriba + escalera `1385` abajo** en la misma casilla. La
escalera `1385` tiene `floorchange_north`: sube a `(x, y−1, z−1)`. El agujero `432` tiene
`floorchange_down` y, como la casilla de abajo es `1385` (que no está en `STAIRS_LANDING` con
offset), se cae a `(x, y+1, z+1)`. Ver `docs/gameplay/STAIRS.md` y `PIEZAS_DE_MAPA.md`.

| Etiqueta | Arriba (agujero) | Abajo (escalera) | Llegada al subir | Llegada al bajar |
|----------|------------------|------------------|------------------|------------------|
| Bajada A (jungla norte) | `432` en `148,295,7` | `1385` en `148,295,8` | `148,294,7` (rellano) | `148,296,8` (eje) |
| Bajada B (oeste) | `432` en `128,336,7` | `1385` en `128,336,8` | `128,335,7` (sala gris) | `128,337,8` (sala Q) |
| Bajada al -2 | `432` en `148,317,8` | `1385` en `148,317,9` | `148,316,8` (eje) | `148,318,9` (octógono) |

Las cuatro llegadas de cada par son piso libre y el generador lo valida antes de escribir. El -2 se
recorre en anillo: se sale por donde se entró o por el portal del fondo.

## Spawns

Bloque `DARK_CATHEDRAL_SPAWNS` en `test-spawn.xml`. 128 bloques de un monstruo cada uno (radio 2),
todos sobre piso caminable y lejos de escaleras, llegadas y portales. Sólo monstruos 7.6 existentes
en `data/monster`.

| Piso | Bloques | Monstruos (cantidad) |
|------|---------|----------------------|
| z7 | 23 | Bandit 9, Smuggler 5, Wild Warrior 5, Hunter 4 |
| z8 | 64 | Bandit 14, Wild Warrior 8, Rotworm 7, Ghoul 6, Skeleton 6, Smuggler 5, Assassin 4, Centipede 4, Bat 3, Poison Spider 3, Slime 3, Dark Monk 1 |
| z9 | 41 | Dark Monk 12, Monk 8, Ghost 8, Witch 6, Hunter 4, Mummy 1, Stone Golem 1, Demon Skeleton 1 |

La dificultad sube con el piso: bandidos y contrabandistas arriba; slimes, arañas y no-muertos en la
cripta; monjes, dark monks, fantasmas y brujas abajo. Los dark monks + demon skeleton de la sala
central sur hacen de "guardia del -3" (la escalera al -3 de la Dark Cathedral original no se
replica).

## Elección de ítems

**Paredes.** La pieza de cada casilla de pared sale de `PIECE_BY_NEIGHBORS`, una tabla con las 16
combinaciones de vecinos (oeste, norte, este, sur) **medida sobre las paredes de piedra del propio
`test.otbm`**: 1049 vertical, 1050 horizontal, 1051 esquina NO, 1053 esquina SE (ladrillo: 1030,
1028, 1027, 1033). Con eso los extremos quedan cerrados y las esquinas se ven como en el resto del
mapa; con la tabla vieja (sólo oeste/norte) los extremos junto a las puertas quedaban como bloques
sueltos.

| Familia | Vertical | Horizontal | Esquina NO | Esquina SE | Dónde |
|---------|----------|------------|------------|------------|-------|
| Piedra | `1049` | `1050` | `1051` | `1053` | Nave (z7) |
| Ladrillo | `1030` | `1028` | `1027` | `1033` | Ruinas (z7), cripta z8 y z9 |

El **suelo bajo la pared** se toma del piso más cercano (BFS desde las salas), así no aparecen
manchas de pasto entre las paredes de las ruinas.

**Columnas.** Las del laberinto del -2 son el ítem `1514` ("pillar", bloquea). Se probaron
`1515` (mármol: es la columna tumbada), `1549`/`1551`/`1560` (doradas, de palacio) y `3766`
("pillar") con `scripts/map/render-pieces.py`; `1514` es la que se lee como columna alta vista desde
arriba. En la nave de z7 las columnas son casillas de pared aisladas (poste de piedra `1051`).

**Bancas.** Siempre el par `1662` + `1663` (mitad derecha). Hay 16 bancos completos: 4 en la nave
(dos filas de dos) y 12 en la sala gris del sur (dos filas de seis). El generador **falla** si
encuentra una mitad sola.

**Pisos.** `407` mármol negro (nave, sala sur del -2, sala final), `431` losa gris (pasillos y salas
de la cripta, explanada, rellanos, salón), `406` mármol blanco (cuello y octógono), `103` tierra
(salas de las ruinas y algunas de la cripta), cueva `351`/`352`/`355`, roca de relleno `101`.

**Bordes.** El agua del río del NE usa las piezas de orilla `4644–4655` con `pieces_for()`. La
jungla no tiene borde de pasto contra tierra porque no hay tierra suelta al aire: los suelos de
tierra están dentro de las paredes.

**Clip de la caja.** `clip()` descarta cualquier casilla fuera de `0–59 × 0–69` locales, y el
generador purga además la roca de relleno que se hubiera escapado una casilla en corridas viejas:
0 casillas fuera de la caja.

## Cómo regenerar

Worktree: `~/proyectos/serverrepo-darkcathedral`, rama `dark-cathedral`. No compilar, no docker, no
deploy, no `git push`.

```bash
python3.11 scripts/map/generate-dark-cathedral.py --dry-run --preview /tmp/dc
# valida (conectividad, escaleras, paredes, bancas, ids, monstruos) y dibuja /tmp/dc-z7..z9.png

python3.11 scripts/map/generate-dark-cathedral.py
# escribe test.otbm, test-spawn.xml, readables.xml y el manifiesto

python3 scripts/map/temple-portals.py       # portal 157,47,7 y el cartel de la plaza
python3 scripts/map/check-map-load.py
python3 scripts/map/validate-tele-dest.py server/YurOTS/ots/data/world/test.otbm
```

Determinista con `--seed 76`. La primera escritura hace backup `test.otbm.bak-darkcathedral` (no va a
git). Archivos que toca: `server/YurOTS/ots/data/world/test.otbm`, `test-spawn.xml`,
`generated-dark-cathedral.json`, `server/YurOTS/ots/data/readables.xml` y (con `--preview`) los PNG
del doc. Si `test.otbm` cambió en `main`, no mergear el binario: correr el generador sobre el mapa
nuevo y después `temple-portals.py`.

## Validaciones (última corrida, 2026-11-15)

El generador, si algo falla, no escribe el `.otbm`.

| Chequeo | Cómo | Resultado |
|---------|------|-----------|
| Caja vacía | `load_tiles()` sobre x118–177 × y284–353 × z7–z9 (o manifiesto propio) | 0 casillas ajenas |
| BFS z7 | desde `148,335,7` | 2017 caminables, todas alcanzables |
| BFS z8 | desde `148,296,8` (llegada de la bajada A) | 1259 caminables, todas alcanzables |
| BFS z9 | desde `148,318,9` (llegada del agujero) | 1413 caminables, todas alcanzables |
| Escaleras | 3 pares `432`+`1385`; las 6 llegadas son piso libre | 0 errores |
| Paredes | una sola pieza por casilla; ninguna casilla de piso con pieza de pared | 0 errores |
| Bancas | cada `1662` con su `1663` a la derecha y viceversa | 16 pares, 0 sueltas |
| Simetría -2 | zigzag, salas laterales, sala sur y final espejados (`mirror(x) = 59−x`) | OK |
| Ids | todos los ítems existen en `items-zagan-test.otb` | 0 errores |
| Monstruos | todos registrados en `monsters.xml` | 0 errores |
| Spawns | cada bloque sobre piso caminable | 0 errores (128) |
| Clip | casillas dentro de la caja | 0 fuera |
| `check-map-load.py` | carga offline del mapa | 0 errores |
| `validate-tele-dest.py` | destinos de los teleport | OK |

Falta deploy y recorrido in-game. Antes de deployar un `test.otbm` nuevo, probar depots
([DEPOTS.md](../gameplay/DEPOTS.md)) y las escaleras de las dos bajadas.

## Renders

El generador dibuja los PNG del doc con el mismo pipeline que el juego (`game_render`, con la altura
de paredes y columnas):

```bash
python3.11 scripts/map/generate-dark-cathedral.py --dry-run \
  --preview docs/items-and-map/img/dark-cathedral --preview-scale 0.45
```

Quedan `docs/items-and-map/img/dark-cathedral-z7.png`, `-z8.png` y `-z9.png` (van al repo). Sin
`--preview` el script no toca imágenes. Para revisar de cerca, `--preview /tmp/dc` deja los tres
pisos a tamaño real (32 px por casilla).

Referencias usadas para comparar: `img/dark-cathedral-ref/Dark_Cathedral_0.png` (superficie),
`Dark_Cathedral_1.png` (piso -1, salas A–T) y `Resp-2DC.png` (piso -2 con respawns).

## Qué queda distinto de la referencia (TibiaWiki)

Cerca, no idéntico:

- **Superficie.** La referencia tiene ríos en arco al norte y al este formando casi una isla; acá el
  borde es jungla cerrada y sólo queda un río en la esquina noreste. Las ruinas son más compactas
  (caben en 60×70) y el conjunto se lee como claro de jungla, no como la explanada extensa original.
- **Piso -1.** La referencia tiene 20 salas etiquetadas A–T repartidas en un plano más ancho; acá hay
  16 salas A–U más la antecámara J y la cueva, en una versión compacta. La cueva natural (G–J en la
  referencia) es una masa de 143 casillas con seis cámaras: se lee como cueva, pero es más chica que
  la red original.
- **Piso -2.** La referencia no es simétrica: brazo oeste con 4 salas, brazo este con 2 rombos y una
  sala oval grande, cruz central y anillo sur. Acá se respetó esa idea (el anillo y las salas
  laterales quedan espejados; los brazos no, como en el original), pero las proporciones son más
  chicas y la sala oval es una elipse de 8×15 (en la referencia es más ancha).
- **No hay -3.** La escalera al -3 y las 6 palancas de la Dark Cathedral original no se replican: en
  su lugar, la sala grande del sur tiene la guardia fuerte (2 dark monks + demon skeleton + mummy +
  witch).
- **Monstruos.** Sólo los 7.6 existentes en este server; no hay Dark Magician, Bonelord ni Rukor Zad.
- **El portal del templo** comparte el slot `157` con otras ramas: si se mergean, hay que resolverlo
  en la plaza (el script `temple-portals.py` es el único dueño de esa fila).

## Estado

Generada, validada y commiteada en local (rama `dark-cathedral`, 2026-11-15). Sin push ni deploy.
