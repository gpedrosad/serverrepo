# Mapear con código — gauntlet de TPs 3×3 + sala final quest

**40 salas puzzle 3×3** (4 TPs/esquina, 1 correcto) + **sala final 3×3** con Wrath, cofre de soft boots y **un solo TP** al templo.

**Acceso:** barco → decir `gauntlet` a `Nimral`/`Fargum` (20 gp). Ver [`BOAT_TRAVEL.md`](../gameplay/BOAT_TRAVEL.md).

Relacionado:

- [BOAT_TRAVEL.md](../gameplay/BOAT_TRAVEL.md) — destino `Gauntlet` + Nimral en sala 0
- [MAPEAR_LABERINTO.md](MAPEAR_LABERINTO.md) — laberinto procedural
- `scripts/generate-tp-gauntlet.py` — generador
- `data/actions/scripts/quest.lua` — cofres por `uniqueId`
- [SOFT_BOOTS.md](../gameplay/SOFT_BOOTS.md) — premio `3549`

---

## Resumen

| Pieza | Detalle |
|-------|---------|
| Salas puzzle | 40 × 3×3, suelo `406`, void `100` |
| TPs por sala puzzle | 4 esquinas; 1 correcto, 3 falsos |
| Sala Fury | puzzle `#34` |
| Última puzzle | TP correcto → landing de la sala final |
| Sala final | **3×3** igual que las demás |
| Wrath | centro de la sala final |
| Cofre | SW — `uniqueId`/`premio` = `3549` (soft boots) |
| TP | **uno solo** en SE → templo |
| Barco | aterrizaje sala 0; Nimral solo ahí |

```
generate-tp-gauntlet.py --replace  →  restart yurots  →  hi / gauntlet / yes
```

---

## Sala final (3×3)

```
   .  L  .     L = landing (desde última puzzle)
   .  W  .     W = Wrath
   C  .  T     C = cofre soft boots (SW)
               T = único TP → templo (SE)
```

No hay pasillo angosto: mismo cuadrado 3×3 que el resto del gauntlet.

---

## Cómo llegar (barco)

1. `Nimral`/`Fargum` → `hi` → `gauntlet` → `yes` (20 gp).
2. Aterrizás en `452, 41, 7` (sala 0).
3. Nimral de vuelta solo en `450, 41, 7`.

---

## Instancia actual (jul 2026)

| Campo | Valor |
|-------|-------|
| Script | `python3 scripts/generate-tp-gauntlet.py --replace` |
| Semilla | `76` |
| Salas puzzle | `40` (grid 7×6) |
| Fury | sala `#34` |
| Sala final | origen ~`450, 77, 7` (sur del grid) |
| Wrath | centro de esa 3×3 |
| Cofre | esquina SW → soft boots (`3549`) |
| TP templo | esquina SE |
| Manifiesto | `generated-tp-gauntlet.json` (`solutionPath` + `finalRoom`) |

### Solución GM

```bash
python3 -c "import json; m=json.load(open('server/YurOTS/ots/data/world/generated-tp-gauntlet.json')); print([(s.get('room'), s.get('correctCorner') or s.get('action')) for s in m['solutionPath']])"
```

---

## Regenerar

```bash
python3 scripts/generate-tp-gauntlet.py --dry-run
python3 scripts/generate-tp-gauntlet.py --replace
docker compose -f docker-compose.prod.yml restart yurots
```

Opciones: `--rooms N`, `--seed S`. Barco/Nimral no los regenera el OTBM (`boat.lua` / `npc.xml`).

**Importante:** `--replace` limpia el footprint (incluye el pasillo viejo si quedó). No toca templo ni depots.
