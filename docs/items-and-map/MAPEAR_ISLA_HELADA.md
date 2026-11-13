# Isla del Hielo Eterno (Frozen Isle) — destino de barco

Reemplaza al **Alice Maze** (nov 2026), que era un laberinto generado de piso crema y paredes de lava.
Es un **sendero angosto y progresivo**: 2 casillas caminables que suben de sur a norte por etapas,
cada una más difícil, con desvíos escondidos que premian explorar.

Generador: `scripts/map/generate-frozen-isle.py` (usa las piezas y validaciones de
`generate-north-pass.py`). Manifiesto: `server/YurOTS/ots/data/world/generated-frozen-isle.json`.

## Recorrido

| Etapa | Dónde | Qué hay | Monstruos |
|-------|-------|---------|-----------|
| Puerto | sur, llegada `395 104 7` | Nimral (`397 103 7`), barriles, fogata, bote | — |
| Bosque Nevado | zigzag entre pinos | desvío del leñador al oeste: cofre **crystal coin** (uid `2160`) | Winter Wolf, Polar Bear |
| Lago Congelado | paso de hielo en zigzag sobre el agua | desvío al **islote del Yeti**: cofre **frozen starlight** (uid `2361`) | Frost Troll, Yeti (1800 s) |
| Monasterio de Escarcha | patio de piedra con columnas, altar, estatuas y braseros | — | Ice Monk |
| Paso de montaña | sendero entre rocas | bajada `392 15 7` | Ice Monk |
| Grutas de Escarcha (z8) | túneles de hielo en serpentina con salas | bajada a z9 `412 53 8` | Ice Spider |
| Guarida (z9) | sala grande con pilares de roca y, al fondo, la cámara del tesoro | cofres **crimson wand** (uid `20123`) y **crimson helmet** (uid `20113`); portal al templo `130 53 6` | Frost Dragon, Ice Spider |

Los cofres del crimson wand y el crimson helmet son los mismos que había al final del Alice Maze
(mismo uniqueId): quien ya los sacó no puede repetirlos (`quest.lua` guarda el storage por uid).

Carteles en `readables.xml`, bloque `FROZEN_ISLE_SIGNS`. Spawns en `test-spawn.xml`, bloque
`FROZEN_ISLE_SPAWNS` (41 spawns, 63 monstruos).

## Compactado (nov 2026)

Los zigzags cruzaban la isla de lado a lado: 291 pasos por el sendero de z7 y 461 por la serpentina de las
grutas. Ahora los tramos son más cortos y la serpentina tiene 5 bandas en vez de 9, en x 18–59 (antes 10–65):

| | Antes | Ahora |
|---|---:|---:|
| Recorrido más largo z7 | 291 pasos | 161 |
| Recorrido más largo z8 | 461 pasos | 165 |
| Caminable z7 / z8 | 948 / 1.191 | 699 / 496 |
| Monstruos | 79 | 63 (menos salas en las grutas: 26 Ice Spider en vez de 42) |

El desvío del leñador sale de la primera curva hacia el oeste (cofre crystal coin en `373 95 7`); el del
islote sigue en el paso de hielo. Los cofres conservan su uniqueId.

## Criaturas de 8.60 (nov 2026)

Además de los monstruos de arriba, el generador pone 23 criaturas traídas del cliente 8.60
([IMPORTAR_CRIATURA_DE_OTRA_VERSION.md](../gameplay/IMPORTAR_CRIATURA_DE_OTRA_VERSION.md)). Van con un rng aparte
(`seed + 860`) y lejos de los spawns de antes, así esos quedaron exactamente donde estaban. El mapa no cambió.

| Etapa | Criaturas |
|---|---|
| Bosque Nevado | Chakoya Tribewarden 2, Toolshaper 2, Windcaller 2, Husky (bosque o lago) 2 |
| Lago Congelado | Barbarian Headsplitter 1, Skullhunter 1 |
| Paso de montaña | Barbarian Brutetamer 1, Bloodwalker 2, Frost Giant 2, Frost Giantess 1 |
| Grutas (z8) | Ice Golem 3, Crystal Spider 2 |
| Guarida (z9) | Frost Dragon Hatchling 2 |

Total de la isla: 86 monstruos (antes 63).

## Caja y vecinos

- Caja: **x 356–433, y 2–117, z7–z9** (el Alice Maze ocupaba x 380–433, y 16–103, z7). Alrededor de
  la isla hay 9 casillas de mar: desde ningún punto caminable se ve el borde negro.
- La plataforma del Gauntlet (x 434–437, y 101–103) queda afuera y no se toca.
- Los Ice Monk, Ice Spider y Frost Dragon son looks custom (232, 235, 231): se ven solo con el
  `Tibia.dat`/`Tibia.spr` nuevo del cliente.

## Reglas que valida el script (si algo falla no escribe nada)

- Costa: cada orilla con su pieza (`4644–4655`). La orilla es intransitable (la pieza es agua para el
  server), por eso el paso de hielo tiene 4 de tierra para dejar 2 caminables.
- Nieve sobre el patio (`4737–4748`) y hielo con borde de nieve (`684–695`, una pieza por casilla).
- Paredes de las cuevas con pieza única (túneles armados en bloques de 2x2).
- El sendero llega del puerto a la bajada, de z8 a z9, a los 4 cofres y al portal.
- Árboles y rocas grandes nunca tapan el sendero (se dibujan una casilla hacia arriba-izquierda).

**Estado (2026-11-11):** cargado en el servidor de prueba de la ThinkPad ([`THINKPAD_TEST_SERVER.md`](../systems/THINKPAD_TEST_SERVER.md)); el servidor arranca y carga el mapa. Falta recorrerlo en el juego.

## Regenerar

```bash
python3 scripts/map/generate-frozen-isle.py --dry-run --preview /tmp/isla.png   # valida y dibuja
python3 scripts/map/generate-frozen-isle.py                                    # escribe
```

Re-ejecutable y determinista (misma semilla = mismo mapa). Escribe `test.otbm` (backup
`test.otbm.bak-frozenisle` la primera vez), spawns, carteles, el Nimral del puerto en `npc.xml` y el
destino en `boat.lua` (`Frozen Isle`: `frozen isle`, `frozen`, `isla helada`, `hielo`).
Después: `python3 scripts/npc/run_npc_tests.py` (el barco tiene golden).
