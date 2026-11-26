# Bosque de los Cíclopes (Cyclops Woods)

Isla de bosque al noreste del mapa (océano del noreste, al norte de la Caldera Azul), hunt de nivel 20–40.
**Hecha con mapkit** (ficha + tema `bosque-isla` + receta `island` con rol de llegada `portal`, en vez del
puerto). Guía: [MAPAS.md](MAPAS.md).

## Cómo se llega

Por **portal** desde la plaza del templo: `169,47,7` → `688,30,7` (llegada en el claro del portal, oeste de
la isla). La vuelta está al lado: `687,30,7` → `169,48,7` (llegada del portal en la plaza). El portal queda
en la casilla `169,47` de la plaza, el espejo de `155,47` (que ya tenía portal `155,47` + obelisco `155,50`);
acá el obelisco queda en `169,50` y **no se toca**.

## Cómo es

| Qué | Dónde / cuánto |
|-----|----------------|
| Caja de la zona (agua de relleno incluida) | `x 670–747, y 10–140, z7` |
| Tierra | dentro de `x 680–737, y 18–132` |
| Llegada (portal) | claro abierto al oeste, `688,30,7`; cartel `687,27,7` |
| Sendero | tierra de 3–5 de ancho en S: filas (y ≈ 30, 48, 66, 84) y bajada al sur hasta `≈706,102` |
| Claros (fallback de la ficha) | guarida de lobos → guarida del oso → campamento de cazador (fogata) → pradera → anillo de hongos |
| Bosque | borde cerrado de arbustos y árboles (no hay atajos); adentro, pasto con árboles sueltos |
| Caminable | 1.248 casillas, 201 pasos de la llegada al fondo |

## Monstruos

29 monstruos en 22 spawns (bloque `CYCLOPS_WOODS_SPAWNS` de `test-spawn.xml`), 1 cada ~43 casillas.
Etapas por distancia (de la llegada al fondo), del fallback de la ficha (validado por Python):

| Etapa (de la llegada al fondo) | Monstruos | Por spawn | Spawntime | Separación |
|---|---|---|---|---|
| 1 | Tarantula, Cyclops | 1 | 90 s | 12 |
| 2 | Cyclops, Cyclops Drone | 1 | 110 s | 11 |
| 3 | Cyclops Drone, Cyclops Smith | 1 | 140 s | 11 |
| 4 | Cyclops Smith, Giant Spider | 2 | 180 s | 10 |

Reparto real: Tarantula 3, Cyclops 5, Cyclops Drone 5, Cyclops Smith 9, Giant Spider 7.
Nada a menos de 6 casillas de la llegada.

## Archivos

| Archivo | Qué es |
|---|---|
| `scripts/map/zones/bosque-de-los-ciclopes.json` | La ficha (caja, recorrido, claros, rol portal, monstruos) |
| `scripts/map/zones/bosque-de-los-ciclopes.decisions.json` | Decisiones guardadas (fallback de la ficha; se commitea) |
| `server/YurOTS/ots/data/world/generated-cyclops-woods.json` | Manifiesto de dueño de las casillas (semilla, medidas) |
| `test-spawn.xml` / `readables.xml` | Bloques `CYCLOPS_WOODS_SPAWNS` / `CYCLOPS_WOODS_SIGNS` |
| `scripts/map/temple-portals.py` | Portal `169,47,7` y vuelta `687,30,7` (PORTALS + RETURNS) |

## Cómo regenerar

```bash
python3.11 scripts/map/mapkit/build.py scripts/map/zones/bosque-de-los-ciclopes.json --preview /tmp/ciclopes.png
python3.11 scripts/map/mapkit/build.py scripts/map/zones/bosque-de-los-ciclopes.json --write
python3 scripts/map/temple-portals.py
python3 scripts/map/check-map-load.py
```

Con las decisiones guardadas sale el mismo mapa (semilla 6, puntaje 86,3). `--redecide` vuelve a preguntar a
jev; `--no-jev` usa lo guardado o los valores de la ficha.
