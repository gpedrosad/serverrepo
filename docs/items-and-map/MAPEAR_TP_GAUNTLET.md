# Mapear con código — gauntlet de TPs 3×3 + sala final quest

**40 salas puzzle 3×3** (4 TPs/esquina, 1 correcto) + **sala final 3×3** con Wrath, dos cofres (demon armor + fury cape) y **un solo TP** al templo.

**Acceso:** barco → decir `gauntlet` a `Nimral`/`Fargum` (20 gp). Ver [`BOAT_TRAVEL.md`](../gameplay/BOAT_TRAVEL.md).

Relacionado:

- [BOAT_TRAVEL.md](../gameplay/BOAT_TRAVEL.md) — destino `Gauntlet` + Nimral en sala 0
- [GEMS.md](../gameplay/GEMS.md) — demon armor acepta hasta **6** emerald imbuements
- [SOFT_BOOTS.md](../gameplay/SOFT_BOOTS.md) — por qué **no** usar `3549` como premio de quest
- `scripts/generate-tp-gauntlet.py` — generador

---

## Sala final (3×3)

```
   F  L  .     F = cofre fury cape (NW, uniqueId 20114)
   .  W  .     L = landing / W = Wrath
   D  .  T     D = cofre demon armor (SW, uniqueId 2494)
               T = único TP → templo (SE)
```

| Cofre | UniqueId / premio |
|-------|-------------------|
| SW | `2494` demon armor |
| NW | `20114` fury cape |

Demon armor puede imbuirse con Big Emerald hasta **6/6** (otras armaduras siguen en 4/4). Ver `gem_imbue.lua` + `ITEM_EMERALD_SKILL_AID_MAX`.

---

## Regenerar

```bash
python3 scripts/generate-tp-gauntlet.py --replace
docker compose -f docker-compose.prod.yml restart yurots   # mapa/spawns
# Si cambió const76.h / item.cpp: rebuild C++ también
```
