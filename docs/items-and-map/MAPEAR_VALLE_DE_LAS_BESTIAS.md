# Valle de las Bestias — zona de caza del portal `158,47,7`

Reemplaza al **Hunt Maze** (nov 2026). La **v3** (nov 2026) compacta el valle —la v1 era un campo
abierto de ~9.000 casillas con dos cuevas de ~6.000 y todos los monstruos mezclados— y da a cada
cueva un **segundo piso más largo y con más monstruos**. Son cuatro pisos:

| Piso | Qué hay |
|------|---------|
| z7 | Valle de bosque con camino, 3 zonas de caza en superficie y las 3 bocas de cueva |
| z8 | Entrada corta de cada cueva (Catacumbas, Quaras, Dragón) |
| z9 | Fondo largo de cada cueva (Cripta Profunda, Nido de las Quaras, Nido del Dragón) |
| z10 | Abismo: final de la progresión, Root Colossus y portal de vuelta |

Generador: `scripts/map/generate-beast-valley.py` (usa las piezas, cuevas y validaciones de
`generate-north-pass.py`). Manifiesto: `server/YurOTS/ots/data/world/generated-beast-valley.json`.

## Recorrido

| Etapa | Piso | Paisaje | Monstruos |
|-------|------|---------|-----------|
| Llegada | z7 sur | claro con 2 portales de vuelta enmarcados y cartel | — |
| Cruce del Valle | z7 | plaza de tierra con cartel y faroles | — |
| Campamento Minotauro | z7 oeste | claro de tierra, 4 fogatas con piedras, barriles y cajones | Minotaur, Archer, Guard, Mage |
| Cantera de los Cíclopes | z7 este | rocas agrupadas, piedras, troncos secos y escombros | Cyclops, Cyclops Drone, Cyclops Smith |
| Ruinas Antiguas | z7 norte | patio de tierra con avenida de columnas, estatuas, braseros, altar y cementerio de lápidas | Skeleton, Ghoul, Mummy, Demon Skeleton |
| Catacumbas | z8 | cueva de huesos, pilares y braseros | Ghoul, Skeleton → Vampire, Mummy, Demon Skeleton → Necromancer, Priestess, Vampire Bride |
| Cripta Profunda | z9 | catacumba larga y oscura | igual familia, 4 tramos y más monstruos |
| Cueva de las Quaras | z8 | cueva con mucho barro, hongos y huesos | Quara Constrictor, Mantassin → Pincher, Hydromancer → Predator |
| Nido de las Quaras | z9 | galería larga y húmeda | igual familia, 4 tramos y más monstruos |
| Guarida del Dragón | z8 | cueva con huesos de dragón, calaveras y braseros | Dragon Hatchling, Dragon → Wyrm → Dragon Lord, Black Dragon |
| Nido del Dragón | z9 | galería larga; al fondo baja al Abismo | igual familia, 4 tramos y más monstruos |
| Abismo | z10 | cueva de barro con braseros | Hydra, Dark Hydra → Behemoth, Serpent Spawn → Demon, Fury → Root Colossus y portal |

En la superficie la dificultad sube de sur a norte. En cada cueva sube con la distancia a la
escalera: lo más difícil queda al fondo. Cada zona mezcla **solo su familia**.

Total: **164 spawns y 498 monstruos**, de los cuales **43 spawns (z8)** y **68 spawns (z9)** son el
mismo tipo de cueva con más cantidad en el fondo. Detalle por monstruo en el manifiesto (`monsters`).

## Coordenadas

| Qué | Pos |
|-----|-----|
| Portal (plaza del templo) | `158, 47, 7` → llegada `312, 360, 7` |
| Portales de vuelta en la llegada | `312, 365, 7` y `313, 365, 7` → `158, 48, 7` |
| Boca de las Catacumbas | `312, 266, 7` |
| Boca de la Cueva de las Quaras | `291, 294, 7` |
| Boca de la Guarida del Dragón | `334, 288, 7` |
| Bajada de cada cueva al fondo (z8) | Catacumbas `326, 255, 8` · Quaras `301, 287, 8` · Dragón `344, 298, 8` |
| Llegada a cada fondo (z9) | Cripta `287, 273, 9` · Quaras `286, 312, 9` · Dragón `334, 306, 9` |
| Bajada del Nido del Dragón al Abismo | `346, 289, 9` |
| Llegada al Abismo | `334, 324, 10` |
| Root Colossus | `339, 347, 10`, respawn 300 s |
| Portal final (fondo del Abismo) | `323, 345, 10` → `158, 48, 7` |
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

## Reglas que valida el script (si algo falla no escribe nada)

- Bordes de tierra con su pieza exacta (`110–121`); caminos en pasos Manhattan para que converjan.
- Paredes de cada cueva con pieza única sobre el piso combinado de su piso.
- Se llega de la llegada a cada zona, a las tres bocas y a los portales del templo.
- En z8, la bajada de cada cueva se alcanza desde su boca; en z9, la bajada del Nido del Dragón.
- En z10, el portal final y la sala del Root Colossus.
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

**Estado (2026-11-14):** v3 generada y validada localmente (`check-map-load.py`: 0 errores). Falta
deploy y recorrido in-game (entradas, escaleras, fondos y portal del Abismo). Antes de deployar un
`test.otbm` nuevo, probar depots in-game ([`../gameplay/DEPOTS.md`](../gameplay/DEPOTS.md)).
