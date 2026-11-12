# Valle de las Bestias — zona de caza del portal `158,47,7`

Reemplaza al **Hunt Maze** (nov 2026), que era un laberinto generado de piso crema y paredes de lava,
igual al viejo Alice Maze. Ahora es un valle natural que se recorre de sur a norte y después baja dos
pisos. Mantiene la progresión de caza del laberinto (de Minotauros a Demonios), pero repartida por
etapas con paisaje propio.

Generador: `scripts/map/generate-beast-valley.py` (usa las piezas, cuevas y validaciones de
`generate-north-pass.py`). Manifiesto: `server/YurOTS/ots/data/world/generated-beast-valley.json`.

## Recorrido

| Etapa | Piso | Paisaje | Monstruos |
|-------|------|---------|-----------|
| Llegada | z7 sur | claro con 2 portales de vuelta enmarcados, cartel | — |
| Campamento Minotauro | z7 | bosque con flores y hongos, camino de tierra en curva, 4 fogatas con ramas, piedras, barriles y cajones | Minotaur, Minotaur Archer, Minotaur Guard, Minotaur Mage |
| Colinas de los Cíclopes | z7 | pasto con rocas agrupadas, piedras sueltas, árboles secos | Cyclops, Dwarf Soldier, Dwarf Guard, Dwarf Geomancer |
| Ruinas Antiguas | z7 norte | patio de tierra con avenida de columnas, estatuas, braseros, altar y escombros; alrededor, cementerio de lápidas rotas entre árboles secos | Beholder, Demon Skeleton, Ghoul, Dwarf Guard |
| Catacumbas | z8 | cueva natural | Giant Spider, Vampire → Necromancer, Priestess → Hero, Black Knight |
| Abismo | z9 | cueva natural, más oscura | Dragon, Ancient Scarab → Dragon Lord, Warlock → Hydra, Lich, Green Djinn → Root Colossus → Demon, Behemoth, Fury, Serpent Spawn |

En la superficie la dificultad sube de sur a norte. En las cuevas sube con la distancia a la escalera:
lo más difícil queda al fondo de cada piso. Cada spawn mezcla los monstruos de su etapa.

Total local: 398 spawns y 767 monstruos (el laberinto tenía 720), incluido un Root Colossus. Sin troncos sueltos (4187/4201/4239 son
pedazos de un tronco largo y sueltos se ven cortados). El detalle por monstruo está en el
manifiesto (`monsters`).

## Coordenadas

| Qué | Pos |
|-----|-----|
| Portal (plaza del templo) | `158, 47, 7` → llegada `312, 360, 7` |
| Portales de vuelta en la llegada | `312, 365, 7` y `313, 365, 7` → `158, 48, 7` |
| Bajada a las Catacumbas | `312, 252, 7` |
| Portal de vuelta junto a la bajada | `319, 254, 7` → `158, 48, 7` |
| Bajada al Abismo | `344, 360, 8` |
| Portal final (fondo del Abismo) | `273, 244, 9` → `158, 48, 7` |
| Root Colossus (inicio del tramo final del Abismo) | `310, 254, 9`, respawn 300 s |
| Caja | x `262–361`, y `232–378`, z7–z9 |

Carteles en `readables.xml`, bloque `BEAST_VALLEY_SIGNS`. Spawns en `test-spawn.xml`, bloque
`BEAST_VALLEY_SPAWNS`.

### Root Colossus: progresión de dificultad

Un [Root Colossus](../gameplay/ROOT_COLOSSUS.md) de 4800 HP se ubica tras el sector Hydra/Lich,
en la transición hacia Behemoth/Demon. Para llegar se recorre la superficie y las Catacumbas antes
de entrar al Abismo. En seed 11 está a **141 pasos cardinales** desde la entrada de z9, en una sala
de 5×5 y a 6 casillas de los spawns vecinos. Drop raro: rootcleaver (axe 1H 49/31, 0,6%) y heartwood
maul (club 2H 52/28, 0,5%). Preparado localmente; falta cliente actualizado y prueba in-game.

`root_colossus_spawn()` selecciona una única ubicación al inicio del último cuarto de las casillas
ordenadas por distancia caminable. Exige espacio libre y separación de al menos 5 casillas de los
otros monstruos; si no lo encuentra, el generador falla antes de escribir. No agrega más ejemplares
ni modifica los spawns anteriores. Otra semilla puede cambiar la coordenada conservando la progresión.
La reubicación se hizo solo en spawns/manifiesto; no requirió cambiar `test.otbm`.

## Vecinos

| Zona | Dónde | Relación |
|------|-------|----------|
| Hell Quest | x 288–405, y 124–226, z7–z9 | Al norte; 5 casillas de separación |
| Paso del Norte | x 370–469, y 236–467, z7–z9 | Al este; 8 casillas de separación |
| Reloj de Arena | x 328–348, y 383–401, z5–z6 | Al sur y arriba; la caja termina en y 378 |
| Hunt Maze viejo | x 280–349, y 243–400, z7 | Borrado entero (también la parte bajo el Reloj) |

Alrededor del valle hay 8 casillas de bosque cerrado (z7) o roca (z8–z9): desde ningún punto caminable
se ve el borde negro.

## Reglas que valida el script (si algo falla no escribe nada)

- Bordes de tierra con su pieza exacta (`110–121`, una por casilla).
- Paredes de las cuevas con pieza única (cuevas armadas en bloques de 2×2).
- Se llega de la llegada a la bajada y a los portales; en z8, a la bajada al Abismo; en z9, al portal final.
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
`test.otbm.bak-beastvalley` la primera vez, no va a git), spawns, carteles y manifiesto. Si `test.otbm`
cambió en `main`, no mergear el binario: volver a correr el script sobre el mapa nuevo.

**Estado (2026-11-11):** cargado en el servidor de prueba de la ThinkPad ([`THINKPAD_TEST_SERVER.md`](../systems/THINKPAD_TEST_SERVER.md)); el servidor arranca y carga el mapa. Falta recorrerlo en el juego.

Antes de deployar un `test.otbm` nuevo, probar depots in-game ([`../gameplay/DEPOTS.md`](../gameplay/DEPOTS.md)).
