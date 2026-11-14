# Cuevas de Bambú (bajo Bamboo Camp)

Bajada opcional desde el claro de **Bamboo Camp** (isla de los Kongras/Dworcs) a una cueva de tres
salas con monstruos que suben de dificultad. Reemplaza el hueco vacío que quedó al sacar las casas
de bambú (nov 2026).

## Recorrido

| Piso | Qué hay |
|---|---|
| z7 | Escalera de bajada en `172,99,7`, en el pasto del claro. |
| z8 | Pozo de 5×5 en `170-174,97-101`: escalera de subida `1385` en `172,99` y bajada `432` en `172,101`. La llegada real desde z7 es `172,100,8`; desde z8 a z9, `172,102,9`. |
| z9 | Cueva de tres salas: sala 1 (entrada), pasillo, sala 2, pasillo y sala 3 (jefe). |

Las escaleras usan el mismo criterio que `docs/gameplay/STAIRS.md`: la subida `1385` tiene
`floorchange_north`, así que al bajar se aterriza una casilla al sur. Las dos llegadas están
validadas como caminables.

## Salas y monstruos

| Sala | Coordenadas (z9) | Monstruos | Dificultad |
|---|---|---|---|
| 1 | `170-180, 93-102` | Dworc Venomsniper ×2, Dworc Fleshhunter ×2, Orc Warrior ×2 | Suave |
| 2 | `184-194, 92-100` | Kongra ×2, Sibang ×2, Orc Berserker ×2 | Media |
| 3 | `198-208, 86-96` | Orc Warlord ×1, Orc Leader ×1, Orc Shaman ×1, Orc Berserker ×2 | Jefe |

Los pasillos son `181-183,97-99` y `195-197,94-96`. Hay seis fogatas (item `1423`) repartidas para
iluminar; no bloquean el paso.

## Generador

`scripts/map/generate-bamboo-depths.py` construye el pozo z8 y la cueva z9 sobre el hueco debajo del
campamento, sin tocar el pasillo de mármol negro ni la zona de lava/demonios del este/sur.

```bash
python3 scripts/map/generate-bamboo-depths.py --dry-run --preview /tmp/cuevas-bambu.png
python3 scripts/map/generate-bamboo-depths.py
```

El generador:
- borra las cajas z8 (`169-175,96-102`) y z9 (`169-209,85-103`) antes de reinsertar;
- reemplaza el bloque `BAMBOO_DEPTHS_SPAWNS` de `test-spawn.xml`;
- valida llegadas, conectividad de las tres salas y que ningún spawn caiga en una casilla bloqueada.

## Verificación

```bash
python3 scripts/map/check-map-load.py
python3 scripts/map/validate-tele-dest.py server/YurOTS/ots/data/world/test.otbm
python3 scripts/sync-houses-with-map.py --dry-run
```

Pendiente: prueba in-game de las dos escaleras y de la aparición de los 17 monstruos (17 slots).
