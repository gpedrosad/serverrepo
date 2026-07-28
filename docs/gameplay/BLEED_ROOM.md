# Bleed Room — mana drain + cadena de 10 mobs

Mini sala PvE desde el templo viejo. Mientras estás adentro **pierdes mana cada segundo**. Matás el monstruo actual → aparece el siguiente **más fuerte**. Cadena fija de **10**. El estado se muestra como en trainers (`MSG_SMALLINFO`).

| Sistema | Portal templo |
|---------|----------------|
| El Crisol | `157, 54, 7` |
| Wave Arena | `159, 54, 7` |
| Hunt maze | `160, 54, 7` |
| Arena de Fosos | `161, 54, 7` |
| Floor campus | `162, 54, 7` |
| Fish TP | agua `164, 54, 7` |
| Reloj de Arena | `166, 54, 7` |
| **Bleed Room** | `168, 54, 7` |

Retorno: TP sur de la sala → templo `169, 54, 7`. Cartel `168, 53, 7`.

---

## Flujo

1. Pisar el TP del templo `168, 54, 7`.
2. Landing `355, 391, 6`. Leech (NPC) al norte.
3. Si la sala estaba vacía → spawnea mob **1/10** y empieza el drain.
4. Cada ~1 s (think del NPC): `Bleed: 3/10 Beholder | mana 420 (-8/s)` (`MSG_SMALLINFO`).
5. Al matar el mob actual → spawnea el siguiente. Tras el 10 → `CLEAR` (~8 s) y reset.
6. Si todos salen → limpia mobs y vuelve a idle.
7. **Salida:** TP sur `355, 392, 6` → templo `169, 54, 7`.

No hay fee. Sala compartida: quien entre vive el mismo mob actual y el mismo drain.

---

## Layout (estética Alice, 5×5)

```
   N  [Leech]
      [  .  ]
      [Spawn]   pelea
      [Land ]   llegada
   S  [ TP  ] → templo 169,54,7
```

| Qué | Valor |
|-----|--------|
| Camino | `406` |
| Fondo | `100` (no walkable) |
| Z | `6` |
| Sala | `353–357, 388–392, 6` (5×5) |
| Leech | `355, 388, 6` |
| Spawn | `355, 390, 6` |
| Landing | `355, 391, 6` |
| TP retorno | `355, 392, 6` → `169, 54, 7` |

---

## Cadena (10)

| # | Mob |
|---|-----|
| 1 | Rat |
| 2 | Rotworm |
| 3 | Skeleton |
| 4 | Orc Warrior |
| 5 | Cyclops |
| 6 | Beholder |
| 7 | Dragon |
| 8 | Hero |
| 9 | Dragon Lord |
| 10 | Demon |

Drain: **8 mana / think** (~1 s), clamp a 0.

---

## Implementación

YurOTS actions **no** tienen `addEvent`. El tick lo lleva el NPC **Leech** (`onThink` ~1 s), igual que Chronos.

| Capa | Detalle |
|------|---------|
| Mapa | `scripts/map/generate-bleed-room.py` |
| NPC | `data/npc/leech.xml` + `data/npc/scripts/leech.lua` |
| Spawn | `data/world/npc.xml` → Leech `355,388,6` |
| C++ | `npc.cpp` / `npc.h`: `getPlayerMana`, `doPlayerAddMana` (bajo `YUR_NPC_EXT`) |

Bindings nuevos (Bleed Room):

| Lua | Rol |
|-----|-----|
| `getPlayerMana(cid)` | Mana actual |
| `doPlayerAddMana(cid, delta)` | Suma/resta mana (delta negativo = drain) + `sendStats` |

También reutiliza: `doSummonCreature`, `doRemoveCreature`, `doSendMagicEffect`, `getTopCreature`, `isMonster`.

Mensajes:

| Clase | Uso |
|-------|-----|
| `MSG_SMALLINFO` (`23`) | HUD cada think (estilo trainers) |
| `MSG_RED_INFO` (`18`) | Entrada / avance de mob / clear |

Diálogo Leech: `hi` → `status` / `bleed` / `mana` / `help`.

---

## Archivos

| Archivo | Rol |
|---------|-----|
| [`scripts/map/generate-bleed-room.py`](../../scripts/map/generate-bleed-room.py) | OTBM + cartel |
| `data/npc/scripts/leech.lua` | Drain, spawn, HUD |
| `data/npc/leech.xml` | Look / script |
| `data/world/npc.xml` | Posición Leech |
| `data/world/generated-bleed-room.json` | Manifiesto |
| `data/readables.xml` | Bloque `BLEED_ROOM_SIGNS` |
| `source/npc.cpp`, `source/npc.h` | Bindings mana |

---

## Regenerar

```bash
python3 scripts/map/generate-bleed-room.py --dry-run
python3 scripts/map/generate-bleed-room.py --replace
# Tras tocar C++ (bindings mana):
docker compose -f docker-compose.prod.yml run --rm yurots bash -c 'cd /app/YuroTS/ots/source && make -j2 yurots'
docker compose -f docker-compose.prod.yml restart yurots
python3 scripts/ot-probe.py 127.0.0.1 7171
```

Solo Lua/mapa (sin C++): restart OT alcanza.

---

## Probar

1. `/pos 168 54 7` → entrar.
2. Ver HUD `Bleed: 1/10 Rat | mana … (-8/s)` y mana bajando.
3. Matar Rat → Beholder chain hasta Demon.
4. Clear → reset; salir por TP sur.
