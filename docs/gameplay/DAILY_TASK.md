# Daily Task — Huntmaster

NPC de contratos diarios de caza en el temple. El jugador elige **1 de 3** opciones según su rango de level, mata monstruos (progreso en storage) y cobra **oro o exp** (no ambos). Racha de días consecutivos aumenta la recompensa.

## Por qué existe

Enganche de login diario: contratos distintos cada día, elección (agency), feedback al matar, recompensa notable sin romper economía.

## Flujo

1. `hi` → Huntmaster (temple, cerca de Tonka).
2. `task` → 3 contratos del día (estables, no reroll).
3. `1` / `2` / `3` → acepta uno.
4. Al matar el monstruo objetivo (o variante Angry/Furious/Enraged), C++ incrementa el contador.
5. Al completar: `reward` → `gold` o `exp` → `yes`.
6. Streak: días seguidos cobrando → hasta **+50%** (día 6+).

## Archivos

| Archivo | Rol |
|---------|-----|
| `data/npc/scripts/lib/daily_task.lua` | Catálogo, brackets, ofertas, streak, claim |
| `data/npc/scripts/huntmaster.lua` | Diálogo |
| `data/npc/huntmaster.xml` | Definición NPC |
| `data/world/npc.xml` | Spawn `138,50,7` |
| `source/npc.cpp` | `doPlayerAddExp`, `doPlayerAddMoney` |
| `source/player.cpp` | `tryProgressDailyTask` (+ catálogo sync) |
| `source/game.cpp` | Hook al dar exp por kill de monstruo |

## Storage (`9200–9215`)

| Key | Uso |
|-----|-----|
| `9200` | Fecha `YYYYMMDD` |
| `9201` | Estado: `0` idle, `1` oferta, `2` activa, `3` lista, `4` cobrada |
| `9202` | Monster catalog id |
| `9203` | Kills requeridos |
| `9204` | Kills actuales |
| `9205` | Streak |
| `9206` | Última fecha de cobro |
| `9207–9212` | Oferta: id+count opciones 1–3 |
| `9213` / `9214` | Gold / exp del contrato aceptado |
| `9215` | Índice de bracket |

## Brackets y balance

| Bracket | Levels | Pool | Kills | Oro | Exp |
|---------|--------|------|-------|-----|-----|
| Novice | 1–20 | Rat, Spider, Troll, Rotworm, Orc | 100–160 | 800–2k | 8k–20k |
| Adventurer | 21–40 | Minotaur, Orc Warrior, Cyclops, Dwarf Guard, Larva | 70–110 | 3k–6k | 40k–90k |
| Hunter | 41–70 | Dragon, Hero, Ancient Scarab, Behemoth, Giant Spider | 55–90 | 8k–15k | 120k–280k |
| Elite | 71–100 | Dragon Lord, Hydra, Behemoth, Warlock, Demon Skeleton | 45–75 | 15k–30k | 150k–350k |
| Legend | 101+ | Demon, Warlock, Fury, Behemoth, Hydra | 40–70 | 25k–45k | 120k–280k |

- Exp del reward es **flat** (`addExp`), no pasa por `expmul`.
- 1 daily / personaje / día.
- Trainers (`trainer=1`) no cuentan.
- Crédito: jugadores que reciben exp del kill (share de daño).

## Catálogo monstruo (sync Lua ↔ C++)

IDs en `daily_task.lua` `DAILY_MONSTERS` y `DAILY_TASK_MONSTER_NAMES[]` en `player.cpp` **deben coincidir**.

## Keywords

`task` / `mission` / `daily`, `1`–`3`, `status` / `report`, `reward` / `claim`, `gold` / `exp`, `streak`, `help`, `bye`.

## Rebuild

Cambio C++ → rebuild + restart + probe:

```bash
docker compose -f docker-compose.prod.yml run --rm yurots bash -c 'cd /app/YuroTS/ots/source && make -j2 yurots'
docker compose -f docker-compose.prod.yml up -d yurots
python3 scripts/ot-probe.py 127.0.0.1 7171
```

Solo Lua/XML (sin tocar source): restart del container alcanza.

## Test plan

1. Char mid-level: `task` → 3 opciones → elige `1`.
2. Matar monstruo incorrecto → no sube.
3. Matar objetivo / Enraged → mensajes `kills/required`.
4. Completar → `reward` → `exp` → `yes`.
5. Segundo `task` el mismo día → “come back tomorrow”.
6. Trainer monk → no cuenta.
7. Streak en 2º día seguido → bonus visible al claim.
