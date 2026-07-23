# El Crisol — bosses diarios + armas exclusivas

Hub con **3 puertas** (Bronce / Plata / Oro). Cada día rota elite/boss. La puerta Oro dropea un **arma Zagan exclusiva** con efecto C++.

| Sistema | Portal templo |
|---------|----------------|
| **El Crisol** | `157, 54, 7` |
| Wave Arena | `159, 54, 7` |
| Hunt maze | `160, 54, 7` |
| Floor campus | `162, 54, 7` |

Carteles `1433` + `readables.xml` en `y=53`. No ocupar `158,54,7` (retorno Wave).

---

## Flujo

1. TP `157, 54, 7` → hub `85, 92, 0`.
2. Palanca INFO `7203`: bosses + rare del día.
3. Bronce `7200` / Plata `7201` / Oro `7202`: pack + elite/boss → arena.
4. Salida: TP sur de arena → hub → templo `156, 54, 7`.

---

## Rotación diaria + armas

| Día | Oro (boss) | Arma | Id | Delay | Efecto |
|-----|------------|------|----|-------|--------|
| 1 | Ashlord | ashlord emberblade | `20112` | 1100ms | Trail fuego; 20% burn DoT |
| 2 | Frostwarden | frostwarden chillblade | `20138` | 1200ms | 18% chill (slow) 4s PvP |
| 3 | Bonepriest | bonepriest reaver | `20154` | default | 15% mana drain |
| 4 | Ironhide | ironhide crusher | `20121` | 1700ms | 22% root 2.5s PvP |
| 5 | Venomqueen | venomqueen fang | `20100` | 950ms | 25% poison DoT |
| 6 | Stormcaller | stormcaller maul | `20110` | 1000ms | Trail energy; 20% burst |
| 7 | Bloodreaver | bloodreaver saber | `20122` | 1200ms | 30% life leech 25% dmg |

Loot exclusive: `chance="4500"` (~4.5%) solo en ese boss.

```bash
python3 scripts/otb/patch-crucible-rares-otb.py
# symlink: scripts/patch-crucible-rares-otb.py
```

Tras tocar C++: `make clean && make` (se agregó `chillTicks` en `creature.h`).

---

## Archivos

| Archivo | Rol |
|---------|-----|
| `scripts/map/generate-crucible.py` (symlink `scripts/generate-crucible.py`) | OTBM + carteles + readables |
| `scripts/otb/patch-crucible-rares-otb.py` (symlink `scripts/patch-crucible-rares-otb.py`) | Stats/nombres OTB de las 7 armas |
| `data/actions/scripts/crucible.lua` | Palancas / rotación |
| `data/monster/crucible *.xml` | Bosses + loot |
| `source/const76.h`, `game.cpp`, `player.cpp`, `item.cpp`, `creature.h` | Gameplay |
