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
| Abismo | z9 | cueva natural, más oscura | Dragon, Ancient Scarab → Dragon Lord, Warlock → Hydra, Lich, Green Djinn → Demon, Behemoth, Fury, Serpent Spawn |

En la superficie la dificultad sube de sur a norte. En las cuevas sube con la distancia a la escalera:
lo más difícil queda al fondo de cada piso. Cada spawn mezcla los monstruos de su etapa.

Total: 397 spawns y 766 monstruos (el laberinto tenía 720). Sin troncos sueltos (4187/4201/4239 son
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
| Caja | x `262–361`, y `232–378`, z7–z9 |

Carteles en `readables.xml`, bloque `BEAST_VALLEY_SIGNS`. Spawns en `test-spawn.xml`, bloque
`BEAST_VALLEY_SPAWNS`.

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

**Estado (2026-11-11):** cargado en el servidor de prueba de la ThinkPad ([`THINKPAD_TEST_SERVER.md`](../systems/THINKPAD_TEST_SERVER.md)); el servidor arranca y carga el mapa. Falta recorrerlo en el juego. No está en el VPS.

Antes de deployar un `test.otbm` nuevo, probar depots in-game ([`../gameplay/DEPOTS.md`](../gameplay/DEPOTS.md)).
