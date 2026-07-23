# Floor Hunt — torre de 16 pisos con teleports

Zona de hunt **multi-piso** generada por código. Avance **solo por teleports** (`1387`). No toca Alice ni el hunt maze plano.

| Sistema | Acceso templo viejo | Footprint |
|---------|---------------------|-----------|
| Hunt maze (plano) | `160, 54, 7` | X `280–349`, Y `243–400`, z7 |
| **Floor hunt** | `162, 54, 7` | X `200–245`, Y `339–400`, **z0–z15** (16 pisos) |
| Wave Arena | `159, 54, 7` | sala 7×7 oleadas — [`WAVE_ARENA.md`](../gameplay/WAVE_ARENA.md) |
| Alice Maze | barco `alice maze` | X `380–433`, Y `18–103`, z7 |

Script: `scripts/generate-floor-hunt.py`  
Manifiesto: `server/YurOTS/ots/data/world/generated-floor-hunt.json`

---

## Teleports (cada piso)

Entrada sur (2×2):

```
        laberinto → norte: TELEPORT BAJAR (o templo en z15)
   ┌────┬────┐
   │LAND│EXP │   LAND = llegar
   ├────┼────┤   EXP  = express +2 pisos (pisos pares; atajo)
   │ UP │HOME│   UP   = subir (z0 → templo)
   └────┴────┘   HOME = templo siempre
```

```
templo 162,54,7 --TP--> z0 Rat Cellars
                         ↓ … 16 pisos …
                        z15 Djinn Depths --TP--> templo
```

---

## Los 16 pisos

| z | Nombre | Fauna (resumen) | Extra |
|---|--------|-----------------|-------|
| 0 | Rat Cellars | Rat, Cave Rat, Hyaena | entrada |
| 1 | Damp Tunnels | Cave Rat, Hyaena, Poison Spider | |
| 2 | Spider Nest | Poison Spider, Centipede | express +2 |
| 3 | Larva Pits | Centipede, Larva, Scorpion | |
| 4 | Spear Halls | Larva, Scorpion, Orc Spearman | ★ hito (packs×2) + express |
| 5 | Wolf Den | Orc Spearman, Bandit, War Wolf | |
| 6 | Bandit Vault | Bandit, War Wolf, Dworc | express |
| 7 | Amazon Wing | War Wolf, Amazon, Bandit | |
| 8 | Valkyrie March | Amazon, Valkyrie, Stalker | ★ hito + express |
| 9 | Stalker Dark | Valkyrie, Stalker, Assassin | |
| 10 | Assassin Row | Stalker, Assassin, Hunter | express |
| 11 | Hunter Gallery | Assassin, Hunter, Mummy | |
| 12 | Mummy Crypt | Hunter, Mummy, Terror Bird | ★ hito + express |
| 13 | Terror Aviary | Mummy, Terror Bird, Gazer | |
| 14 | Gazer Spire | Terror Bird, Gazer, Blue Djinn | express |
| 15 | Djinn Depths | Gazer, Blue Djinn | fondo → templo |

★ Hitos (z4, z8, z12): más densidad de spawns.

---

## Coordenadas

| Qué | Pos |
|-----|-----|
| Portal templo | `162, 54, 7` → `200, 399, 0` |
| Landing / piso | `200, 399, z` |
| TP home | `201, 400, z` → `163, 54, 7` |
| TP up | `200, 400, z` |
| TP express (si hay) | `201, 399, z` → landing z+2 |
| TP down | `224, 339, z` |
| Celdas / seed | `12×16` / piso, seed `421` |

---

## Regenerar

```bash
python3 scripts/generate-floor-hunt.py --dry-run
python3 scripts/generate-floor-hunt.py --replace
docker compose -f docker-compose.prod.yml restart yurots
python3 scripts/ot-probe.py 127.0.0.1 7171
```

Limpia z0–z15 en la huella + portal `162,54,7`.

---

## Probar

```
/pos 162 54 7      # portal → z0
/pos 200 399 4     # hito Spear Halls
/pos 200 399 8     # hito Valkyrie
/pos 200 399 15    # Djinn Depths
```
