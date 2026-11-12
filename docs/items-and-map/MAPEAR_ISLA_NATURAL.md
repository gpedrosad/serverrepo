# Isla natural — zona de caza del portal `156,47,7`

Rehecha el 2026-11-12. La isla anterior era una mancha de ruido de 64×58 con 13 Cyclops repartidos y una
cueva grande sin orden (con monstruos rage). Ahora es una **herradura** chica alrededor de una laguna: se
entra por una punta, se sigue un único sendero y se sale por la otra punta o por el fondo de la cueva.
Tierra: 566 casillas (antes 1475). Cueva: 276 casillas de piso (antes 651).

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
| Guarida del Grorlam | z8 | sala final con portal al templo | 1 Grorlam (respawn 1800 s), 2 Crypt Shambler |

El sendero de tierra une todo en orden: 36 pasos de la llegada a la cueva y 50 de la escalera al portal
final. Las salas de la cueva están en anillo, cada una se alcanza solo pasando por la anterior. Respawn de
90–120 s salvo el Grorlam. Total: 28 monstruos, ninguno rage, sin troncos sueltos.

## Coordenadas

| Qué | Pos |
|-----|-----|
| Portal (plaza del templo) | `156, 47, 7` → llegada `147, 462, 7` |
| Portal de vuelta en la llegada | `147, 465, 7` → `156, 48, 7` |
| Campamentos (fogatas) | `145, 452, 7` · `155, 445, 7` · `166, 452, 7` |
| Agujero de la cueva | `163, 463, 7` (escalera en `163, 463, 8`, sale a `163, 464, 7`) |
| Portal de vuelta junto a la cueva | `166, 461, 7` → `156, 48, 7` |
| Salas (centro) | `164, 454, 8` · `155, 447, 8` · `144, 453, 8` · `152, 462, 8` |
| Portal final (Guarida del Grorlam) | `155, 463, 8` → `156, 48, 7` |
| Caja | x `131–180`, y `433–476`, z7–z8 (tierra en x `141–170`, y `441–468`) |

Carteles en `readables.xml`, bloque `NATURAL_ISLAND_SIGNS` (llegada `145, 461, 7`, cueva `160, 460, 7`).
Spawns en `test-spawn.xml`, bloque `NATURAL_ISLAND_SPAWNS`.

## Regenerar

```bash
python3 scripts/map/generate-natural-island.py --dry-run --preview /tmp/isla   # valida y dibuja isla-z7.png / isla-z8.png
python3 scripts/map/generate-natural-island.py                                 # mapa, spawns, carteles, manifiesto
python3 scripts/map/temple-portals.py                                          # portal de la plaza y vueltas
python3 scripts/map/check-map-load.py
```

El generador borra primero la caja de la isla vieja (x `124–187`, y `426–483`, z7–z8) y sus spawns. Antes
de escribir valida: piezas de costa y de borde de tierra exactas, todo caminable conectado, campamentos y
salas en orden de recorrido, portales alcanzables y nada a la vista del borde de la caja.

## Cómo está hecho

- **Primero el recorrido, después el terreno.** La línea del sendero (un arco) y los campamentos se fijan
  antes; la tierra es solo una franja alrededor de esa línea, con un poco de ruido en el borde.
- **Sendero en bloques de 2×2**, así el borde pasto/tierra siempre tiene una única pieza válida.
- **Árboles:** el dibujo ocupa 2×2 hacia arriba y a la izquierda; el generador no pone uno que tape un
  portal, un cartel o una piedra, y saca los que encierran un rincón.
- **Cueva:** discos (salas) unidos por pasillos de 3 de ancho sobre la grilla de bloques de
  `generate-north-pass.py`; el portal final va en la casilla más lejana de la última sala.

Falta probarla jugando (dificultad de los campamentos de 4 Cyclops y del Grorlam con dos Shamblers).
