# Rate de experiencia (expmul)

## Cambio 2026-07-05

| Tramo de nivel | Antes | Ahora |
|----------------|-------|-------|
| 1–40 | ×5 | ×5 (sin cambio) |
| 41–70 | ×4 | ×4 (sin cambio) |
| 71–100 | ×3 | **×2** |
| 101+ | ×2 | **×1** (RL) |

**Motivo:** frenar el progreso en niveles altos. Los tramos bajos/medios se mantienen igual; a partir de 71 la curva baja más fuerte y en 101+ la exp de monstruos es rate real de Tibia.

**Estado:** aplicado en `config.lua` y `OTINFO` (web pública). Requiere **restart del OT** para entrar en vivo.

## Config

```lua
-- server/YurOTS/ots/config.lua
expmul = 3   -- fallback si no hay tiers (no aplica con la config actual)

expmulmin  = {"9", "41", "71", "101"}
expmulmax  = {"40", "70", "100", "0"}   -- 0 = sin tope superior
expmulrate = {"5", "4", "2", "1"}

premmyexpbonus = 10   -- +10% exp de monstruos para premium
```

Los niveles **1–8** usan el rate del primer tramo (×5), igual que 9–40. Ver `LuaScript::getExpMulForLevel()` en `luascript.cpp`.

## Bonus de los primeros niveles (desde el 27 nov 2026)

Encima del tramo, hasta el nivel 20 se suma un bonus que baja **nivel a nivel**
(`LuaScript::applyLowLevelExpBonus`, `luascript.cpp`; se aplica en `creature.cpp` y en la exp de party de `game.cpp`):

| Nivel | 8 | 9 | 10 | 12 | 15 | 18 | 20 | 21+ |
|-------|---|---|----|----|----|----|----|-----|
| Bonus | +60 % | +55 % | +50 % | +41 % | +27 % | +13 % | +4 % | — |
| Rate (free) | ×8 | ×7,75 | ×7,5 | ×7 | ×6,4 | ×5,7 | ×5,2 | ×5 |

`lowlevelexpbonus = 60` (bonus en el nivel 8) y `lowlevelexplevel = 20` (último nivel con bonus), por defecto en el
binario; se pueden pisar en `config.lua`. El premium (+10 %) se suma después. Ver [NIVELES_BAJOS.md](NIVELES_BAJOS.md).

## Premium

Sobre el multiplicador del tramo, premium suma **+10%** (`creature.cpp` → `PREMMY_EXP_BONUS`).

Ejemplos:

| Nivel | Free | Premium (+10%) |
|-------|------|----------------|
| 50 | ×4 | ×4.4 |
| 80 | ×2 | ×2.2 |
| 120 | ×1 | ×1.1 |

## Otros rates (sin cambio en este ajuste)

| Rate | Valor |
|------|-------|
| Loot | ×1 (`lootmul`, desde el 12 nov 2026; antes ×3) |
| Skills | ×4 |
| ML | ×3 (×6 premium) — ver [`ML_RATE.md`](ML_RATE.md) |
| Regen HP al comer | ×5 |
| Regen mana al comer | ×1 |

## Deploy

Solo datos; no hace falta rebuild del binario:

```bash
# Local
docker compose -f docker-compose.prod.yml restart yurots

# ThinkPad (con OK de Gonzalo): ver docs/systems/THINKPAD_TEST_SERVER.md
# (respaldo, git merge --ff-only origin/main, docker restart -t 45 yurots)
```

Verificar:

```bash
python3 scripts/ot-probe.py 127.0.0.1 7171
```

La web lee rates desde `OTINFO` vía `web/server.py` — se actualiza al recargar, sin rebuild web.

## Archivos

- `server/YurOTS/ots/config.lua` — `expmulmin`, `expmulmax`, `expmulrate`
- `server/YurOTS/ots/source/luascript.cpp` — carga tiers y `getExpMulForLevel()`
- `server/YurOTS/ots/source/creature.cpp` — aplica multiplicador + bonus premium
- `OTINFO` — sección `RATES` (in-game / web pública)

## Historial

| Fecha | Cambio |
|-------|--------|
| 2026-11-27 | Bonus de exp hasta el nivel 20, nivel a nivel: +60 % en el 8 → +4 % en el 20 |
| 2026-07-05 | 71–100 ×3→×2, 101+ ×2→×1 |
| (anterior) | Tiers 9–40 ×5, 41–70 ×4, 71–100 ×3, 101+ ×2 |
