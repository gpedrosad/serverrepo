# Hunt Maze — laberinto de caza aparte del Alice Maze

Laberinto **separado** (no es Alice Maze ni el gauntlet). Misma geometría 2 sqm (`406` / `100`) que [`MAPEAR_LABERINTO.md`](MAPEAR_LABERINTO.md).

| Sistema | Footprint | Acceso |
|---------|-----------|--------|
| **Alice Maze** (intacto) | X `380–433`, Y `18–103` | Barco `alice maze` → `413 103 7` |
| **Hunt Maze** (este doc) | X `280–349`, Y `243–400` | Portal templo viejo `160,54,7` |
| **Floor hunt** | X `200–245`, Y `339–400`, z0–15 (16 pisos) | Portal templo `162,54,7` — ver [`MAPEAR_FLOOR_HUNT.md`](MAPEAR_FLOOR_HUNT.md) |
| **Wave Arena** | X `174–180`, Y `386–392` | Portal templo `159,54,7` — ver [`../gameplay/WAVE_ARENA.md`](../gameplay/WAVE_ARENA.md) |
| Gauntlet | ~`450+` | Barco `gauntlet` |

---

## Hunt Maze — coordenadas

| Qué | Pos |
|-----|-----|
| Portal (templo viejo) | `160, 54, 7` → landing |
| Llegada | `280, 399, 7` |
| Retorno (apenas llegás, 1 paso sur) | `281, 400, 7` → `161, 54, 7` |
| Escape norte (opcional) | `316, 243, 7` → `161, 54, 7` |
| Celdas / seed | `18 × 40`, seed `230` |
| Spawns | bloque `<!-- BEGIN HUNT_MAZE -->` |

Alice Maze **no se regenera** con este script (hay assert anti-solape).

---

## Regenerar solo el hunt maze

```bash
python3 scripts/generate-hunt-maze.py --dry-run
python3 scripts/generate-hunt-maze.py --replace
docker compose -f docker-compose.prod.yml restart yurots
python3 scripts/ot-probe.py 127.0.0.1 7171
```

Para regenerar Alice (aparte):

```bash
python3 scripts/generate-maze.py --replace
```

Manifiesto: `server/YurOTS/ots/data/world/generated-hunt-maze.json`

---

## Caza

Spawns progresivos (poco usados en el mapa): rats / spiders → orc/war wolf/amazon → valkyrie/assassin → mummy/gazer → blue djinn al fondo.
