# Pantano de los Kongra (Kongra Swamp)

Isla de pantano/selva al noreste del mapa (océano del noreste, al este del Bosque de los Cíclopes), hunt de
nivel 15–45. **Hecha con mapkit** (ficha + tema `bosque-isla` + receta `island` con rol de llegada `portal`).
Guía: [MAPAS.md](MAPAS.md).

## Cómo se llega

Por **portal** desde la plaza del templo: `163,51,7` → `783,30,7` (llegada en el claro del portal, oeste de
la isla). La vuelta está al lado: `782,30,7` → `163,52,7` (llegada del portal en la plaza). Es la primera
zona en la **fila espejo y=51** de la plaza (la fila y=47 se llenó; ver [CAMBIAR-MAPA.md](../CAMBIAR-MAPA.md)).

## Cómo es

| Qué | Dónde / cuánto |
|-----|----------------|
| Caja de la zona (agua de relleno incluida) | `x 765–850, y 10–140, z7` |
| Tierra | dentro de `x 775–840, y 18–132` |
| Llegada (portal) | claro abierto al oeste, `783,30,7`; cartel `779,30,7` |
| Sendero | tierra de 3–5 de ancho en S: filas (y ≈ 30, 48, 66, 84) y bajada al sur hasta `≈805,102` |
| Claros (elegidos por jev) | campamento de cazador (fogata) → anillo de hongos → guarida de lobos → pradera → guarida del oso (fondo) |
| Bosque | borde cerrado de arbustos y árboles (no hay atajos); adentro, pasto con árboles sueltos |
| Caminable | 1.413 casillas, 229 pasos de la llegada al fondo |

## Monstruos

43 monstruos en 27 spawns (bloque `KONGRA_SWAMP_SPAWNS` de `test-spawn.xml`), 1 cada ~33 casillas.
Etapas por distancia (de la llegada al fondo), propuestas por jev y validadas por Python:

| Etapa (de la llegada al fondo) | Monstruos | Por spawn | Spawntime | Separación |
|---|---|---|---|---|
| 1 | Snake, Wasp | 1 | 85 s | 13 |
| 2 | Poison Spider, Swamp Troll | 1 | 105 s | 12 |
| 3 | Sibang, Carniphila | 2 | 140 s | 10 |
| 4 | Kongra, Merlkin | 2 | 170 s | 9 |

Reparto real: Snake 3, Wasp 2, Poison Spider 3, Swamp Troll 3, Sibang 9, Carniphila 9, Kongra 7, Merlkin 7.
Nada a menos de 6 casillas de la llegada.

## Archivos

| Archivo | Qué es |
|---------|--------|
| `scripts/map/zones/pantano-de-los-kongra.json` | La ficha (caja, recorrido, claros, rol portal, monstruos) |
| `scripts/map/zones/pantano-de-los-kongra.decisions.json` | Decisiones de jev (etapas, claros, cartel, semilla elegida) |
| `server/YurOTS/ots/data/world/generated-kongra-swamp.json` | Manifiesto de dueño de las casillas (semilla, medidas) |
| `test-spawn.xml` / `readables.xml` | Bloques `KONGRA_SWAMP_SPAWNS` / `KONGRA_SWAMP_SIGNS` |
| `scripts/map/temple-portals.py` | Portal `163,51,7` y vuelta `782,30,7` (PORTALS + RETURNS) |

## Cómo regenerar

```bash
python3.11 scripts/map/mapkit/build.py scripts/map/zones/pantano-de-los-kongra.json --preview /tmp/kongra.png
python3.11 scripts/map/mapkit/build.py scripts/map/zones/pantano-de-los-kongra.json --write
python3 scripts/map/temple-portals.py
python3 scripts/map/check-map-load.py
```

Con las decisiones guardadas sale el mismo mapa (semilla 1, puntaje 87,4). `--redecide` vuelve a preguntar a
jev; `--no-jev` usa lo guardado o los valores de la ficha.
