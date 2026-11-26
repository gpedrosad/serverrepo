# Gruta de los Gárgolas (Gargoyle Grotto)

Cueva subterránea de caza al este del mapa (hueco vacío del este, al norte de los Pozos del Infierno), de
nivel 25–55. **Hecha con mapkit** con la **receta nueva `cave`** (ficha + tema `caverna`), la primera zona
subterránea del motor: pasillo de tierra en zigzag cavado en la roca, paredes de tierra y roca alrededor.
Guía: [MAPAS.md](MAPAS.md).

## Cómo se llega

Por **portal** desde la plaza del templo: `164,51,7` → `552,104,8` (llegada dentro de la cueva, en la
cámara de entrada). La vuelta está al lado: `553,104,8` → `164,52,7` (llegada del portal en la plaza). Es
la segunda zona en la **fila espejo y=51** de la plaza (después del Pantano de los Kongra en `163,51,7`).

## Cómo es

| Qué | Dónde / cuánto |
|-----|----------------|
| Caja de la zona (roca de relleno incluida) | `x 500–599, y 84–183, z8` |
| Techo (roca en z7 sobre la caja) | `x 500–599, y 84–183, z7` (el piso de arriba estaba vacío) |
| Llegada (portal) | cámara de entrada al norte, `552,104,8`; cartel `550,106,8` |
| Recorrido | pasillo de tierra de 4–6 de ancho en S: filas y ≈ 100 / 114 / 128 / 142 / 156, columnas x ≈ 520 / 580 |
| Salas | ensanches a mitad de cada tramo largo, una al final del recorrido y la cámara de entrada |
| Piso | tierra con paleta barro/alterno; decoración de piedras, huesos y hongos (nada que se levante ni se empuje) |
| Paredes | de tierra `356–367` (salen de dónde está el piso); roca `101` alrededor |
| Caminable | 1.893 casillas, 281 pasos de la llegada al fondo |

## Monstruos

56 monstruos en 36 spawns (bloque `GARGOYLE_GROTTO_SPAWNS` de `test-spawn.xml`), 1 cada ~34 casillas.
Etapas por distancia (de la llegada al fondo), propuestas por jev y validadas por Python:

| Etapa (de la llegada al fondo) | Monstruos | Por spawn | Spawntime | Separación |
|---|---|---|---|---|
| 1 | Stone Troll | 1 | 85 s | 12 |
| 2 | Gazer, Stone Troll | 1 | 105 s | 11 |
| 3 | Gargoyle, Stone Golem | 2 | 140 s | 10 |
| 4 | Earth Elemental, Stone Golem | 2 | 175 s | 9 |

Reparto real: Stone Troll 11, Gazer 5, Gargoyle 9, Stone Golem 20, Earth Elemental 11. Nada a menos de
6 casillas de la llegada.

## Archivos

| Archivo | Qué es |
|---------|--------|
| `scripts/map/zones/caverna-de-los-gargolas.json` | La ficha (caja, recorrido, rol portal, monstruos) |
| `scripts/map/zones/caverna-de-los-gargolas.decisions.json` | Decisiones de jev (etapas, cartel, semilla elegida) |
| `scripts/map/mapkit/cave.py` | La receta `cave` (ribbon + carve_cave, paredes, techo) |
| `scripts/map/mapkit/themes.json` | Tema `caverna` (piso, roca, pared `356–367`, decoración) |
| `server/YurOTS/ots/data/world/generated-gargoyle-grotto.json` | Manifiesto de dueño de las casillas (semilla, medidas) |
| `test-spawn.xml` / `readables.xml` | Bloques `GARGOYLE_GROTTO_SPAWNS` / `GARGOYLE_GROTTO_SIGNS` |
| `scripts/map/temple-portals.py` | Portal `164,51,7` y vuelta `553,104,8` (PORTALS + RETURNS) |

## Por qué es distinta del Bosque y el Pantano

Las dos zonas anteriores usan la misma receta `island` con el tema `bosque-isla`: isla alargada de pasto
con sendero de tierra y bosque. La Gruta es **bajo tierra** (z8, con techo de roca en z7): piso de tierra
en pasillo de 4–6 de ancho, paredes de tierra `356–367` y roca `101`, sin pasto ni árboles. Monstruos de
piedra (Gárgolas, Golems) en vez de Cíclopes/Kongra. La receta es otra (`cave` vs `island`) y el tema es
otro (`caverna` vs `bosque-isla`).

## Cómo regenerar

```bash
python3.11 scripts/map/mapkit/build.py scripts/map/zones/caverna-de-los-gargolas.json --preview /tmp/gargolas.png
python3.11 scripts/map/mapkit/build.py scripts/map/zones/caverna-de-los-gargolas.json --write
python3 scripts/map/temple-portals.py
python3 scripts/map/check-map-load.py
python3 scripts/map/check-upper-view.py --box 500 84 599 183 --z 8
```

Con las decisiones guardadas sale el mismo mapa (semilla 1, puntaje 99,8). `--redecide` vuelve a preguntar
a jev; `--no-jev` usa lo guardado o los valores de la ficha.
