# Push a `main` (jul 2026) — **no deploy VPS**

Push de trabajo local a `origin/main`. **No** se corrió `deploy-vps.sh` ni se tocó producción.

Fecha: 2026-07-15 (noche CL).

---

## Commits incluidos en este push

| SHA | Mensaje |
|-----|---------|
| `219e191` | `feat(spells): exori hur a target y nuevo exori vis hur.` |
| `e3c3120` | `feat(npc): no comprar imbues y SMP en Seller.` |
| `2b704dc` | `docs: anotar SHAs del push main (sin VPS).` |
| `1031f54` | `docs: corregir SHAs post-rebase del push main.` |

| Tema | Resumen |
|------|---------|
| Spells | `exori hur` → target battle list rango 5; nuevo `exori vis hur` (Sorc/Druid, visual HMM); binding C++ `getAttackedCreaturePos` |
| Docs spells | `SPELL_EXORI_HUR.md`, `SPELL_EXORI_VIS_HUR.md`, `SPELL_EXHAUSTION.md` + enlaces INDEX/AGENTS/RUNTIME |
| NPC sell | NPCs **no compran** ítems con imbue de gema (AID 9020–9074) |
| Seller | Strong Mana Potion / SMP + backpack SMP; docs fluids |
| Gems | Crimson Wand en whitelist Violet de `gem_imbue.lua`; docs |
| Huntmaster | Spawn documentado `138,53,6` (`npc.xml`) |

---

## Archivos por área

### Spells (requiere **rebuild C++** en el próximo deploy)

- `server/YurOTS/ots/source/spells.h`
- `server/YurOTS/ots/source/spells.cpp` — `getAttackedCreaturePos`
- `server/YurOTS/ots/data/spells/instant/exori hur.lua`
- `server/YurOTS/ots/data/spells/instant/exori vis hur.lua` (**nuevo**)
- `server/YurOTS/ots/data/spells/spells.xml`
- `docs/gameplay/SPELL_EXORI_HUR.md` (incluye script viejo + revert)
- `docs/gameplay/SPELL_EXORI_VIS_HUR.md` (incluye revert)
- `docs/gameplay/SPELL_EXHAUSTION.md`
- `docs/gameplay/SPELL_RUNTIME.md`, `SPELL_CAST_VISIBILITY.md`
- `docs/INDEX.md`, `AGENTS.md`

### NPC / seller / gems (rebuild C++ por `npc.cpp`)

- `server/YurOTS/ots/source/npc.cpp` — count/remove sellable ignora imbues
- `server/YurOTS/ots/data/npc/scripts/seller.lua` — SMP
- `server/YurOTS/ots/data/actions/scripts/gem_imbue.lua` — Crimson Wand + Violet
- `server/YurOTS/ots/data/world/npc.xml` — spawn Huntmaster
- `docs/gameplay/GEMS.md`, `SELLER_FLUIDS.md`, `DAILY_TASK.md`
- `docs/features/07-seller-fluid-packs-and-vials.md`

---

## Estado VPS

| | |
|---|---|
| Push git | **sí** → `origin/main` |
| Deploy VPS | **no** (explícito) |
| Rebuild prod | pendiente hasta que se autorice deploy |

Cuando se autorice deploy:

1. `DEPLOY_I_READ_README=yes ./scripts/deploy-vps.sh`
2. Rebuild C++ en el container (`spells.*` + `npc.cpp`)
3. `python3 scripts/ot-probe.py` contra el VPS
4. Probar: `exori hur` / `exori vis hur` con target; vender item imbued a NPC (debe rechazar); comprar SMP al Seller

---

## Revert rápido

| Qué | Cómo |
|-----|------|
| Solo `exori hur` | Ver [`SPELL_EXORI_HUR.md`](gameplay/SPELL_EXORI_HUR.md) |
| Solo `exori vis hur` | Ver [`SPELL_EXORI_VIS_HUR.md`](gameplay/SPELL_EXORI_VIS_HUR.md) |
| Todo el push | `git revert` de los commits de este push (o `git log` + revert rango) |

---

## Nota para agentes

No asumir que prod tiene estos cambios hasta que haya deploy autorizado y probe OK. Data de jugadores en VPS sigue sagrada.
