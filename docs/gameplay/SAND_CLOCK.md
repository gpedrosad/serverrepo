# Reloj de Arena — sala compartida con fases globales

Una sola sala. Todos los que entran viven el **mismo** evento: cada **120 s** cambia la fase y el pack de mobs. El countdown se muestra como en trainers (`quedan X s` / `X min Y s`) vía `MSG_SMALLINFO`.

| Sistema | Portal templo |
|---------|----------------|
| El Crisol | `157, 54, 7` |
| Wave Arena | `159, 54, 7` |
| Hunt maze | `160, 54, 7` |
| Arena de Fosos | `161, 54, 7` |
| Floor campus | `162, 54, 7` |
| Fish TP | agua `164, 54, 7` |
| **Reloj de Arena** | `166, 54, 7` |

Retorno: TP sur de la sala → templo `167, 54, 7`. Cartel `166, 53, 7`.

---

## Flujo

1. Pisar el TP del templo `166, 54, 7`.
2. Landing `338, 392, 6`. Chronos (NPC) ya está en la sala.
3. Mensaje de entrada: fase actual + tiempo restante.
4. Cada ~1 s (think del NPC): `Reloj: quedan X s | fase: Name` (mismo estilo que training).
5. Al cambiar la fase: limpia mobs de la sala, spawnea el pack nuevo, anuncia a todos.
6. Salida: TP `338, 398, 6` → templo `167, 54, 7`.

No hay fee, no hay instancias. El reloj es **global** (`os.time()`): si entrás a mitad de fase, ves el mismo countdown y los mismos mobs que el resto.

---

## Layout

| Z | Rol |
|---|-----|
| **z6** | Sala de juego (`406` path) |
| **z5** | Fondo neutro (`405`) |
| **z7** | Portal templo + pad `407` + cartel |

| Coord | Uso |
|-------|-----|
| `330–346, 385–399, 6` | Sala (path) |
| `338, 392, 6` | Landing |
| `338, 398, 6` | TP retorno |
| `338, 387, 6` | Chronos (`npc.xml`) |

Tiles simples a propósito (mismo patrón Fish / Fosos / Crisol): un rectángulo de path, sin laberintos ni fosos.

---

## Fases (ciclo 120 s)

Orden fijo, loop infinito según reloj de pared:

| # | Nombre | Pack |
|---|--------|------|
| 1 | Scarab Nest | Angry Scarab×3, Furious Ancient Scarab×1, Bone Beast×2 |
| 2 | Huntress Rage | Angry Amazon×3, Furious Valkyrie×2, Angry Hunter×1 |
| 3 | Orc Legion | Angry Orc Berserker×3, Angry Orc Shaman×2, Furious Orc Leader×1 |
| 4 | Steel & Venom | Angry Hero×2, Angry Gargoyle×2, Furious Giant Spider×1, Angry Black Knight×1 |
| 5 | Necropolis | Angry Vampire×2, Furious Necromancer×1, Angry Lich×1, Furious Warlock×1 |
| 6 | Abyssal Peak | Angry Demon×1, **Fury**×1, **Wrath**×1 (customs raros) |

Packs usan variantes rage (`Angry` / `Furious` / `Enraged`) y, en el climax, los customs **Fury** / **Wrath**. No se spawnean bosses de quest ni Crucible diarios (evita diluir El Crisol).

Cambio de fase: cloud → rings → pop/energy por spawn; puff si falla el summon.

Índice de fase:

```lua
math.mod(math.floor(os.time() / 120), 6) + 1
```

---

## Implementación

YurOTS actions **no** tienen `addEvent`. El tick global lo lleva el NPC **Chronos** (`onThink` ~1 s).

| Capa | Detalle |
|------|---------|
| Mapa | `scripts/map/generate-sand-clock.py` |
| NPC | `data/npc/chronos.xml` + `data/npc/scripts/chronos.lua` |
| Spawn | `data/world/npc.xml` → Chronos `338,387,6` |
| C++ | `npc.cpp` / `npc.h` bajo `YUR_NPC_EXT`: `doSummonCreature`, `doRemoveCreature`, `doSendMagicEffect`, `getTopCreature`, `isMonster` |

Bindings nuevos (solo monstruos en remove; nunca player/NPC):

| Lua | Rol |
|-----|-----|
| `doSummonCreature(name, {x,y,z})` | Spawnea; retorna creature id |
| `doRemoveCreature(cid)` | Quita monstruo |
| `doSendMagicEffect({x,y,z}, type)` | FX |
| `getTopCreature({x,y,z})` | id o 0 |
| `isMonster(cid)` | boolean |

Mensajes:

| Clase | Uso |
|-------|-----|
| `MSG_SMALLINFO` (`23` / `0x17`) | Countdown cada think (como trainers) |
| `MSG_RED_INFO` (`18` / `0x12`) | Entrada / cambio de fase |

Diálogo Chronos: `hi` → `time` / `fase` / `reloj` / `help`.

---

## Archivos

| Archivo | Rol |
|---------|-----|
| [`scripts/map/generate-sand-clock.py`](../../scripts/map/generate-sand-clock.py) | OTBM + cartel |
| `data/npc/scripts/chronos.lua` | Fases, spawn, timer |
| `data/npc/chronos.xml` | Look / script |
| `data/world/npc.xml` | Posición Chronos |
| `data/world/generated-sand-clock.json` | Manifiesto |
| `data/readables.xml` | Bloque `SAND_CLOCK_SIGNS` |
| `source/npc.cpp`, `source/npc.h` | Bindings Lua |

---

## Regenerar / deploy

```bash
python3 scripts/map/generate-sand-clock.py --dry-run
python3 scripts/map/generate-sand-clock.py --replace
```

- Solo Lua/NPC XML: restart OT.
- Si tocaste `npc.cpp` / `npc.h`: **rebuild C++** (`make clean && make` si cambió el header de forma que afecte ABI; al menos `make -j2 yurots`) + restart + `python3 scripts/ot-probe.py 127.0.0.1 7171`.
- Deploy mapa: checklist depots ([`DEPOTS.md`](DEPOTS.md)); preguntar antes de VPS.

---

## Probar

1. Entrar por `166, 54, 7`.
2. Ver mensaje de fase + línea `Reloj: quedan …` cada segundo.
3. Esperar cambio de fase (~hasta 120 s) o hablar con Chronos (`time`).
4. Confirmar que al cambiar limpia mobs viejos y spawnea los nuevos.
5. Salir por el TP sur → `167, 54, 7`.

Relacionado: [`FISH_TP.md`](FISH_TP.md), [`SVAR_ARENA.md`](SVAR_ARENA.md), [`WAVE_ARENA.md`](WAVE_ARENA.md), [`../CAMBIAR-MAPA.md`](../CAMBIAR-MAPA.md).
