# Isla natural — zona de caza del portal `156,47,7`

Rehecha el 2026-11-12 y ampliada el 2026-11-14 con dos pisos más de cueva. La isla anterior era una
mancha de ruido de 64×58 con 13 Cyclops repartidos y una cueva grande sin orden (con monstruos rage).
Ahora es una **herradura** chica alrededor de una laguna: se entra por una punta, se sigue un único
sendero y se sale por la otra punta o por el fondo de la cueva. Tierra: 566 casillas (antes 1475).
Cueva: 888 casillas de piso en z8–z10 (276 en z8 antes de esta ampliación; 651 en la isla vieja).

Generador: `scripts/map/generate-natural-island.py` (usa las piezas, cuevas y validaciones de
`generate-north-pass.py`). Manifiesto: `server/YurOTS/ots/data/world/generated-natural-island.json`.
Reemplaza también a `link-island-temple.py` y `spawn-island-cave.py`, que se borraron.

## Recorrido

| Etapa | Piso | Paisaje | Monstruos |
|-------|------|---------|-----------|
| Llegada | z7, punta suroeste | cartel y portal de vuelta | — |
| Campamento del oeste | z7 | fogata, piedras, huesos, sobre el sendero de tierra | 3 Cyclops |
| Campamento del norte | z7 | igual | 4 Cyclops |
| Campamento del este | z7 | igual | 4 Cyclops |
| Boca de la cueva | z7, punta sureste | agujero entre piedras, cartel y portal de vuelta | — |
| Sala de los Golems | z8 | cueva | 3 Stone Golem, 1 Gazer |
| Galería | z8 | cueva | 2 Stone Golem, 2 Crypt Shambler, 1 Gazer |
| Cripta | z8 | cueva | 3 Crypt Shambler, 2 Stalker |
| Guarida del Grorlam | z8 | sala final del piso, bajada a z9 | 1 Grorlam (respawn 1800 s), 2 Crypt Shambler |
| Sala de los Wyverns | z9 | cueva | 2 Wyvern, 1 Dragon Hatchling |
| Galería de los Murciélagos | z9 | cueva | 3 Mutated Bat, 1 Mutated Rat |
| Cámara de los Hatchlings | z9 | cueva | 2 Dragon Hatchling, 1 Wyvern |
| Descenso | z9 | sala con bajada a z10 | 2 Mutated Rat, 1 Mutated Bat |
| Sala de los Mutantes | z10 | cueva | 3 Mutated Rat, 1 Mutated Human |
| Galería de Cristal | z10 | cueva | 1 Emerald Scarab (respawn 600 s), 2 Mutated Bat |
| Sala de los Hatchlings | z10 | cueva | 2 Dragon Hatchling, 1 Wyvern |
| Cámara de la Reina | z10 | sala final con portal al templo | 1 Old Widow (respawn 1800 s), 2 Giant Spider |

El sendero de tierra une todo en orden: 36 pasos de la llegada a la cueva. La cueva encadena z8 → z9 →
z10: cada sala se alcanza solo pasando por la anterior y la bajada está siempre en la última sala del
piso. Respawn de 90–120 s salvo el Grorlam, el Emerald Scarab y la Old Widow. Total: 54 monstruos,
ninguno rage, sin troncos sueltos. Los monstruos se colocan con su huella (2×2) para que el sprite no
quede metido en la pared.

## Coordenadas

| Qué | Pos |
|-----|-----|
| Portal (plaza del templo) | `156, 47, 7` → llegada `147, 462, 7` |
| Portal de vuelta en la llegada | `147, 465, 7` → `156, 48, 7` |
| Campamentos (fogatas) | `145, 452, 7` · `155, 445, 7` · `166, 452, 7` |
| Agujero de la cueva | `163, 463, 7` (escalera en `163, 463, 8`, sale a `163, 464, 7`) |
| Portal de vuelta junto a la cueva | `166, 461, 7` → `156, 48, 7` |
| Salas z8 (centro) | `164, 454, 8` · `155, 447, 8` · `144, 453, 8` · `152, 462, 8` |
| Bajada z8 → z9 | agujero `155, 463, 8`, escalera en `155, 463, 9` |
| Salas z9 (centro) | `164, 465, 9` · `164, 453, 9` · `153, 446, 9` · `142, 452, 9` |
| Bajada z9 → z10 | agujero `142, 455, 9`, escalera en `142, 455, 10` |
| Salas z10 (centro) | `147, 467, 10` · `163, 466, 10` · `166, 451, 10` · `149, 446, 10` |
| Portal final (Cámara de la Reina) | `149, 442, 10` → `156, 48, 7` |
| Caja | x `131–180`, y `433–476`, z7–z10 (tierra en x `141–170`, y `441–468`) |

Carteles en `readables.xml`, bloque `NATURAL_ISLAND_SIGNS` (llegada `145, 461, 7`, cueva `160, 460, 7`).
Spawns en `test-spawn.xml`, bloque `NATURAL_ISLAND_SPAWNS`.

## Regenerar

```bash
python3 scripts/map/generate-natural-island.py --dry-run --preview /tmp/isla   # valida y dibuja isla-z7..z10.png
python3 scripts/map/generate-natural-island.py                                 # mapa, spawns, carteles, manifiesto
python3 scripts/map/temple-portals.py                                          # portal de la plaza y vueltas
python3 scripts/map/check-map-load.py
```

El generador borra primero la caja de la isla vieja (x `124–187`, y `426–483`, z7–z10) y sus spawns. Antes
de escribir valida: piezas de costa y de borde de tierra exactas, todo caminable conectado, campamentos y
salas en orden de recorrido, portales alcanzables y nada a la vista del borde de la caja.

## Cómo está hecho

- **Primero el recorrido, después el terreno.** La línea del sendero (un arco) y los campamentos se fijan
  antes; la tierra es solo una franja alrededor de esa línea, con un poco de ruido en el borde.
- **Sendero en bloques de 2×2**, así el borde pasto/tierra siempre tiene una única pieza válida.
- **Árboles:** el dibujo ocupa 2×2 hacia arriba y a la izquierda; el generador no pone uno que tape un
  portal, un cartel o una piedra, y saca los que encierran un rincón.
- **Cueva:** discos (salas) unidos por pasillos de 3 de ancho sobre la grilla de bloques de
  `generate-north-pass.py`. Cada piso se encadena con el anterior: la salida del piso es un agujero en la
  última sala y el piso siguiente arranca con la escalera en esa misma casilla. El portal final va en la
  casilla más lejana de la última sala del último piso.
- **Spawns con huella:** cada monstruo se coloca probando su bloque `SIZE` (2×2) completo dentro del piso
  caminable, lejos de la escalera y del portal, y sin pisar la huella de otro. Primero eligen los más
  grandes y cerca del centro de su sala.

Falta probarla jugando (dificultad de los campamentos de 4 Cyclops, del Grorlam con dos Shamblers y del
descenso a wyverns/mutantes hasta la Old Widow).
