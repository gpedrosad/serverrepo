# Valle de las Bestias — zona de caza del portal `158,47,7`

Reemplaza al **Hunt Maze** (nov 2026). La **v3** (nov 2026) compacta el valle —la v1 era un campo
abierto de ~9.000 casillas con dos cuevas de ~6.000 y todos los monstruos mezclados— y da a cada
cueva un **segundo piso más largo y con más monstruos**. La **v4** (16 nov 2026) convierte todas las
cuevas en **pasillos largos y angostos** y hace que los monstruos salgan **sueltos al entrar y de a 2 al
fondo**. Cómo se arma un lugar así y cuántos monstruos pone: [ZONAS_DE_CAZA.md](ZONAS_DE_CAZA.md).
Son cuatro pisos:

| Piso | Qué hay |
|------|---------|
| z7 | Valle de bosque con camino, 3 zonas de caza en superficie y las 3 bocas de cueva |
| z8 | Entrada de cada cueva (Catacumbas, Quaras, Dragón) |
| z9 | Fondo largo de cada cueva (Cripta Profunda, Nido de las Quaras, Nido del Dragón) |
| z10 | Abismo: final de la progresión, Root Colossus y portal de vuelta |

Generador: `scripts/map/generate-beast-valley.py` (usa las piezas, cuevas y validaciones de
`generate-north-pass.py`). Manifiesto: `server/YurOTS/ots/data/world/generated-beast-valley.json`.

## Recorrido

| Etapa | Piso | Paisaje | Monstruos |
|-------|------|---------|-----------|
| Llegada | z7 sur | claro con 2 portales de vuelta enmarcados y cartel | — |
| Cruce del Valle | z7 | plaza de tierra con cartel y faroles | — |
| Campamento Minotauro | z7 oeste | claro de tierra, 4 fogatas con piedras, barriles y cajones | Minotaur sueltos → Minotaur/Archer sueltos → Guard/Mage de a 2 |
| Cantera de los Cíclopes | z7 este | rocas agrupadas, piedras, troncos secos y escombros | Cyclops sueltos → Cyclops/Drone sueltos → Drone/Smith de a 2 |
| Ruinas Antiguas | z7 norte | patio de tierra con avenida de columnas, estatuas, braseros, altar y cementerio de lápidas | Skeleton/Ghoul sueltos → Ghoul/Mummy sueltos → Mummy/Demon Skeleton de a 2 |
| Catacumbas | z8 | pasillo en zigzag por el norte (filas y 20 / 34 / 48), huesos, pilares y braseros | Skeleton/Ghoul sueltos → Ghoul/Mummy sueltos → Vampire/Mummy/Demon Skeleton de a 2 → Necromancer/Priestess/Vampire Bride de a 2 |
| Cripta Profunda | z9 | pasillo todavía más largo, 3 filas al norte | Mummy/Vampire sueltos → de a 2 → Necromancer/Priestess sueltos → de a 2 → Bride/Priestess/Demon Skeleton de a 2 (5 tramos) |
| Cueva de las Quaras | z8 | pasillo largo y angosto en zigzag hacia el sur, con barro, hongos y huesos | Constrictor **sueltas** → Constrictor/Mantassin sueltas → Mantassin/Pincher de a 2 → Pincher/Hydromancer de a 2 |
| Nido de las Quaras | z9 | pasillo todavía más largo, cruza al este y vuelve | Pincher/Hydromancer sueltas → de a 2 → Predator sueltos → Predator de a 2 (5 tramos) |
| Guarida del Dragón | z8 | pasillo que baja hacia el sur (x 60) y vuelve por el este (x 85), con huesos de dragón y braseros | Hatchling sueltos → Hatchling/Dragon sueltos → Dragon/Wyrm de a 2 → Wyrm/Dragon Lord/Black Dragon de a 2 |
| Nido del Dragón | z9 | 3 filas en el medio del piso (y 74 / 60 / 46); al fondo baja al Abismo | Dragon/Wyrm sueltos → de a 2 → Dragon Lord/Wyrm sueltos → Dragon Lord/Black Dragon de a 2 (5 tramos) |
| Abismo | z10 | 4 filas de cueva de barro con braseros (y 46 / 60 / 74 / 88) | Hydra sueltas → Hydra/Serpent de a 2 → Behemoth/Serpent sueltos → Behemoth/Dark Hydra de a 2 → Demon/Fury sueltos → Demon/Behemoth/Fury de a 2 → Root Colossus y portal |

En la superficie la dificultad sube de sur a norte. En cada cueva sube con la distancia a la
escalera: lo más difícil queda al fondo. Cada zona mezcla **solo su familia**.

Total (v4): **175 spawns y 263 monstruos** (49 en z7, 69 en z8, 103 en z9, 42 en z10 con el Root
Colossus). En la v3 eran 441. En las cuevas sale un monstruo cada 33–50 casillas; en los claros de la
superficie, uno cada 9–15. Detalle por monstruo y por zona en el manifiesto (`monsters`, `density`).

| Piso | Zona | Casillas | Spawns | Monstruos |
|------|------|----------|--------|-----------|
| z7 | Campamento / Cantera / Ruinas | 157 / 132 / 320 | 10 / 11 / 16 | 13 / 15 / 21 |
| z8 | Catacumbas / Quaras / Dragón | 1.067 / 1.018 / 955 | 16 / 15 / 14 | 25 / 22 / 22 |
| z9 | Cripta / Nido de las Quaras / Nido del Dragón | 1.159 / 1.252 / 1.205 | 21 / 24 / 21 | 33 / 36 / 34 |
| z10 | Abismo | 1.708 | 26 + Root Colossus | 41 + 1 |

**Quaras (nov 2026):** salían 3–4 por spawn, con centros cada 6 casillas y 17 grupos en z8 alrededor de
la escalera (130 quaras en total). Primero pasaron a ir de a 2 (58). Después (v4) las dos cuevas dejaron
de ser manchas redondas (~340 y ~420 casillas) y pasaron a ser **pasillos largos y angostos** (4–6 de ancho)
en zigzag: z8 baja hacia el sur desde la boca (~1.000 casillas caminables) y z9 sale de debajo de esa
bajada y cruza al este (~1.250). Cada etapa trae su propia separación (4.º campo de `CAVE_STAGES` /
`DEEP_STAGES`, 10–13 casillas) y la cantidad crece por tramos: primero quaras sueltas, al fondo de a 2.
Nada a menos de 6 casillas de las escaleras (`STAIR_CLEAR`). Eran 64 quaras, una cada ~35 casillas
(antes, una cada ~13).

**Las demás cuevas (v4, 16 nov 2026):** Catacumbas, Cripta, Guarida y Nido del Dragón y el Abismo pasaron
por lo mismo: eran manchas de ~330–520 casillas con grupos de 2–4 cada 6 casillas (284 monstruos entre
todas) y ahora son pasillos de 950–1.700 casillas con 156 monstruos, sueltos al entrar y de a 2 al fondo.
Los claros de la superficie no cambian de forma, pero pasaron de grupos de 3 (93 monstruos) a sueltos y de
a 2 al fondo (49). Las cuevas del mismo piso se cavan con 3 casillas de roca entre ellas
(`CAVE_SEPARATION`). Las Quaras quedaron con la misma forma; al sacar las garras de dragón (abajo), que
bloqueaban casillas, sus spawns se sortearon de nuevo y quedaron 58.

**Sin piezas de dragón cortadas (16 nov 2026):** la cabeza `2247`, el cráneo `3125` y la garra `3122` son
partes del esqueleto grande de dragón y solas se ven cortadas en el suelo. El valle las cambia por huesos
enteros (`CUT_DRAGON_PIECES`: `2248` calavera con huesos, `2320` calavera; los props del dragón usan
el esqueleto `3133`). Las pone
`decorate_cave` de `generate-north-pass.py`, que el Paso del Norte sigue usando como antes.

Cómo se cava un pasillo: `QUARA_PATH8` / `QUARA_PATH9` (y `CAT_PATH*`, `DRAGON_PATH*`, `ABYSS_PATH`) son tramos rectos y `QUARA_ROOMS*` / `rooms_along()` son ensanches;
`ribbon()` les da ancho variable y un zigzag de ±1, y `carve_cave` solo cava dentro de una franja de 5
alrededor del recorrido (`RIBBON_BAND`). Los tramos paralelos van a **14 casillas** como mínimo: con menos
las franjas se tocan y la cueva hace atajos que rompen la progresión. La última sala de z8 tiene que tener
3×5 de piso (ahí cae la bajada): en un tramo horizontal de 4 de alto no entra y la bajada cae en una esquina.

Cada cueva y piso sortea sus spawns con su propio generador (`cave_rng`): cambiar una cueva no mueve los
spawns de las otras. (Cuando se hizo el cambio, nov 2026, las Catacumbas, el Dragón y el Abismo se
sortearon una vez de nuevo, con las mismas reglas.)

## Coordenadas

| Qué | Pos |
|-----|-----|
| Portal (plaza del templo) | `158, 47, 7` → llegada `312, 360, 7` |
| Portales de vuelta en la llegada | `312, 365, 7` y `313, 365, 7` → `158, 48, 7` |
| Boca de las Catacumbas | `312, 266, 7` |
| Boca de la Cueva de las Quaras | `291, 294, 7` |
| Boca de la Guarida del Dragón | `334, 288, 7` |
| Bajada de cada cueva al fondo (z8) | Catacumbas `304, 280, 8` · Quaras `284, 356, 8` · Dragón `347, 307, 8` |
| Escalera de subida de cada fondo (z9) | justo debajo de su bajada: `304, 280, 9` · `284, 356, 9` · `347, 307, 9` |
| Bajada del Nido del Dragón al Abismo | `316, 278, 9` (subida en `316, 278, 10`) |
| Root Colossus | `340, 307, 10`, respawn 300 s |
| Portal final (fondo del Abismo) | `275, 321, 10` → `158, 48, 7` |
| Caja | x `262–361`, y `232–378`, z7–z10 |

Carteles en `readables.xml`, bloque `BEAST_VALLEY_SIGNS`. Spawns en `test-spawn.xml`, bloque
`BEAST_VALLEY_SPAWNS`.

### Root Colossus: progresión de dificultad

Un [Root Colossus](../gameplay/ROOT_COLOSSUS.md) de 4800 HP custodia el portal final del Abismo,
después de Demon/Fury. Se llega recorriendo el valle, una cueva de dos pisos y el Abismo. Drop raro:
rootcleaver (axe 1H 49/31, 0,6 %) y heartwood maul (club 2H 52/28, 0,5 %).

`root_colossus_spawn()` busca una sala de 3×3 libre en el último tercio del Abismo, separada del
portal y de los demás spawns; si no la encuentra, el generador falla antes de escribir. Otra semilla
puede cambiar la coordenada conservando la progresión.

## Vecinos

| Zona | Dónde | Relación |
|------|-------|----------|
| Hell Quest | x 288–405, y 124–226, z7–z9 | Al norte; el valle empieza en y 232 |
| Paso del Norte | x 370–469, y 236–467, z7–z9 | Al este; el valle termina en x 361 |
| Reloj de Arena | x 328–348, y 383–401, z5–z6 | Al sur y arriba; la caja termina en y 378 |
| Torre del Barquero | x 174–180, y 61–67 | Lejos, al noroeste |
| Hunt Maze viejo | x 280–349, y 243–400, z7 | Borrado entero |

Alrededor del valle hay bosque cerrado (z7) y roca (z8–z10): desde ningún punto caminable se ve el
borde negro. El espacio libre de la caja que no es valle se rellena con pinares, arbustos y piedras
que bloquean el paso; no quedan claros abiertos.

## Escaleras entre pisos

Bajada `432` en el piso de arriba y, **en la misma x, y del piso de abajo**, la escalera `1385`, que se
activa al pisarla y sube hacia el norte. Al bajar se cae al sur de la `1385`; al pisarla se vuelve a la
casilla al norte de la `432`. (La `1385` no se usa con clic: no tiene action.)

**Error que ya pasó (v3, nov 2026):** cada fondo (z9) y el Abismo se cavaban desde una boca fija; las
bajadas de z8 y la del Nido del Dragón caían sobre roca y las subidas de abajo no tenían bajada encima.
No se podía bajar a ningún fondo. Ahora `build_caves()` elige la bajada dentro de la zona donde puede
empezar la cueva de abajo (`stair_down`, `mouth_zone`) y cava esa cueva desde ahí (con un pasillo hasta
su recorrido `spine`). Por eso la caja del fondo de las Catacumbas está 16 casillas más al este y la del
Abismo (z10) pisa en x, y la del Nido del Dragón. Probado con un bot GM: baja y sube por las 5 escaleras.

## Reglas que valida el script (si algo falla no escribe nada)

- Bordes de tierra con su pieza exacta (`110–121`); caminos en pasos Manhattan para que converjan.
- Paredes de cada cueva con pieza única sobre el piso combinado de su piso.
- Se llega de la llegada a cada zona, a las tres bocas y a los portales del templo.
- En z8, la bajada de cada cueva se alcanza desde su boca; en z9, la bajada del Nido del Dragón.
- En z10, el portal final y la sala del Root Colossus.
- Cada bajada `432` tiene la `1385` justo debajo, sobre piso de cueva y con salida al sur; cada `1385`
  tiene la `432` encima y la casilla al norte de arriba se puede pisar.
- Ninguna casilla caminable a menos de media pantalla del borde de la caja.
- Árboles y rocas grandes nunca tapan el camino (se dibujan una casilla hacia arriba-izquierda).

## Regenerar

```bash
python3 scripts/map/generate-beast-valley.py --dry-run --preview /tmp/valle.png   # valida y dibuja
python3 scripts/map/generate-beast-valley.py                                     # escribe
python3 scripts/map/temple-portals.py                                            # cartel y portal de la plaza
python3 scripts/map/check-map-load.py                                            # que el server cargue el mapa
```

Re-ejecutable y determinista (misma semilla = mismo mapa). Escribe `test.otbm` (backup
`test.otbm.bak-beastvalley` la primera vez, no va a git), spawns, carteles y manifiesto. Si
`test.otbm` cambió en `main`, no mergear el binario: volver a correr el script sobre el mapa nuevo.

**Estado (2026-11-16):** v4, todas las cuevas en pasillo y spawns sueltos → de a 2 (z7 igual de forma;
z8, z9 y z10 cavados de nuevo salvo las Quaras; `check-map-load.py`: 0 errores; el script valida escaleras,
paredes y bordes; falta recorrido in-game). **Antes (2026-11-15):** cuevas de quaras en pasillo largo y angosto (z8 y z9 se cavan de nuevo solo en las
quaras; z7 y z10 iguales; `check-map-load.py`: 0 errores; falta recorrido in-game). Antes: escaleras arregladas y quaras de a 2 (`check-map-load.py`: 0 errores; bot GM
baja y sube por las 5 escaleras en un server de prueba). La regeneración deja z7 igual y cambia z8 solo en
las bajadas y su decoración; z9 y z10 se cavan de nuevo. Falta recorrido in-game de los fondos. Antes de deployar un
`test.otbm` nuevo, probar depots in-game ([`../gameplay/DEPOTS.md`](../gameplay/DEPOTS.md)).
