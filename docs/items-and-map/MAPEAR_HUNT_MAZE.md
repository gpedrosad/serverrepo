# Hunt Maze — laberinto de caza aparte del Alice Maze

Laberinto **separado** (no es Alice Maze ni el gauntlet). Misma geometría 2 sqm (`406` / `100`) que [`MAPEAR_LABERINTO.md`](MAPEAR_LABERINTO.md).

| Sistema | Footprint | Acceso |
|---------|-----------|--------|
| ~~Alice Maze~~ → **Isla del Hielo Eterno** (nov 2026) | X `356–433`, Y `2–117`, z7–z9 | Barco `frozen isle` → `395 104 7` — ver [`MAPEAR_ISLA_HELADA.md`](MAPEAR_ISLA_HELADA.md) |
| **Hunt Maze** (este doc) | X `280–349`, Y `243–400` | Portal plaza del templo `158,47,7` |
| **Wave Arena** | X `174–180`, Y `386–392` | Portal plaza del templo `166,47,7` — ver [`../gameplay/WAVE_ARENA.md`](../gameplay/WAVE_ARENA.md) |
| Gauntlet | ~`450+` | Barco `gauntlet` |

---

## Hunt Maze — coordenadas

| Qué | Pos |
|-----|-----|
| Portal (plaza del templo) | `158, 47, 7` → landing |
| Llegada | `280, 399, 7` |
| Retorno (apenas llegás, 1 paso sur) | `281, 400, 7` → `158, 48, 7` |
| Escape norte (opcional) | `316, 243, 7` → `158, 48, 7` |
| Celdas / seed | `18 × 40`, seed `230` |
| Spawns | bloque `<!-- BEGIN HUNT_MAZE -->` |

Este script no toca la zona del ex Alice Maze, hoy Isla del Hielo Eterno (hay assert anti-solape).

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

Progresión mid→hard (sin rats): **Minotaur** en la entrada → Guard/Mage → Cyclops/Dwarf → Beholder/Demon Skeleton → Spider/Vampire → Necro/Hero → Dragon/Dragon Lord → Hydra/Lich → Demon/Behemoth/Fury al fondo.
