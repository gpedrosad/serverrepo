# Floor Hunt — campus de 16 salas (teleports, sin apilar z)

Zona de hunt **multi-sala** generada por código. Avance **solo por teleports** (`1387`). Las salas están en **z7**, separadas en XY (alas oeste / centro / este) para que no se vean teleports de otra sala. Fondo opaco (no void). No toca Alice ni el hunt maze plano.

| Sistema | Acceso templo viejo | Footprint |
|---------|---------------------|-----------|
| Hunt maze (plano) | `160, 54, 7` | X `280–349`, Y `243–400`, z7 |
| **Floor hunt (campus)** | `162, 54, 7` | 16 salas en z7 — envelope X `40–452`, Y `220–400` |
| Wave Arena | `159, 54, 7` | sala 7×7 oleadas — [`WAVE_ARENA.md`](../gameplay/WAVE_ARENA.md) |
| Alice Maze | barco `alice maze` | X `380–433`, Y `18–103`, z7 |

Script: `scripts/generate-floor-hunt.py`  
Manifiesto: `server/YurOTS/ots/data/world/generated-floor-hunt.json`

---

## Por qué campus (no torre apilada)

La versión anterior ponía 16 laberintos en la **misma huella XY** (z0–z15). El cliente mostraba teleports/suelos del piso de abajo a través del void (`100`).

Ahora:

1. Cada sala tiene **XY propio** con hueco entre footprints.
2. Todo en **z7** (sin stack vertical).
3. Fondos **opacos** (mármol/piedra/tierra/pasto) distintos por sala.

Al regenerar se **borra** la torre vieja `X200–245 Y339–400` en z0–z15.

---

## Teleports (cada sala)

Entrada sur (2×2):

```
        laberinto → norte: TELEPORT BAJAR (o templo en sala 15)
   ┌────┬────┐
   │LAND│EXP │   LAND = llegar
   ├────┼────┤   EXP  = express +2 salas (pares; atajo)
   │ UP │HOME│   UP   = sala anterior (sala 0 → templo)
   └────┴────┘   HOME = templo siempre
```

```
templo 162,54,7 --TP--> sala 0 Minotaur Courts
                         ↓ … 16 salas …
                        sala 15 Behemoth Throne --TP--> templo
```

---

## Las 16 salas

| # | Nombre | Ala | Fauna (resumen) | Extra |
|---|--------|-----|-----------------|-------|
| 0 | Minotaur Courts | oeste | Minotaur, Archer, Guard | entrada |
| 1 | Guard Barracks | oeste | Guard, Archer, Mage | |
| 2 | Cyclops Yard | oeste | Cyclops, Dwarf Soldier | express +2 |
| 3 | Dwarf Bastion | oeste | Dwarf Guard, Geomancer | |
| 4 | Beholder Vault | oeste | Beholder, Demon Skeleton | ★ hito + express |
| 5 | Bone Crypt | oeste | Demon Skeleton, Ghoul, Ghost | |
| 6 | Spider Catacombs | centro | Giant Spider, Vampire | express |
| 7 | Necro Cloister | centro | Necromancer, Priestess | |
| 8 | Hero Hall | este | Hero, Black Knight | ★ hito + express |
| 9 | Dragon Roost | este | Dragon | |
| 10 | Scarabs & Hex | este | Ancient Scarab, Warlock | express |
| 11 | Lord Lair | este | Dragon Lord | |
| 12 | Hydra Cistern | este | Hydra, Green Djinn | ★ hito + express |
| 13 | Lich Spire | este | Lich, Blue Djinn | |
| 14 | Demon Gate | este | Demon, Serpent Spawn | |
| 15 | Behemoth Throne | este | Behemoth, Fury | fondo → templo |

★ Hitos (4, 8, 12): packs×2 en algunas celdas.

---

## Coordenadas

| Qué | Pos |
|-----|-----|
| Portal templo | `162, 54, 7` → `40, 399, 7` |
| Landing sala 0 | `40, 399, 7` |
| Celdas / seed | `10×12` / sala, seed `421` |
| Spawns | `<!-- BEGIN FLOOR_HUNT -->` |

Orígenes `(originX, originYSouth)`: ver `FLOOR_ORIGINS` en el script / manifiesto.

---

## Regenerar

```bash
python3 scripts/generate-floor-hunt.py --dry-run
python3 scripts/generate-floor-hunt.py --replace
docker compose -f docker-compose.prod.yml restart yurots
python3 scripts/ot-probe.py 127.0.0.1 7171
```

---

## Relacionado

- Hunt maze plano: [`MAPEAR_HUNT_MAZE.md`](MAPEAR_HUNT_MAZE.md)
- Wave Arena: [`../gameplay/WAVE_ARENA.md`](../gameplay/WAVE_ARENA.md)
- Alice Maze: [`MAPEAR_LABERINTO.md`](MAPEAR_LABERINTO.md)
