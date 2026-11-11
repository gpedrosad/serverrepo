# Reloj de Arena — sala de oleadas que suben de nivel

Una sala chica (11×9) compartida. Todos los que entran viven el **mismo** ciclo, que corre según la hora
real aunque no haya nadie:

**descanso de 30 s → oleada 1 → 2 → … → 6 (60 s cada una, cada una más fuerte) → descanso otra vez.**

Ciclo completo: 6 min 30 s. Rehecha en nov 2026: antes era una sala de 17×15 de piso blanco que cambiaba
de "fase" cada 120 s sin orden de dificultad claro, y se entraba en cualquier punto del ciclo sin saber
qué venía.

Portal en la plaza del templo: `168, 47, 7` (cartel `168, 46, 7`: "6 oleadas que suben de nivel. Entra en el descanso").

Retorno: portal al sur de la sala → templo `168, 48, 7`.

Portales del templo: plaza `155,43–169,52` (z7), tabla completa en [`CAMBIAR-MAPA.md`](../CAMBIAR-MAPA.md#portales-del-templo-plaza-z7--nov-2026). Los maneja `scripts/map/temple-portals.py`.

---

## Qué ve el jugador

1. Al entrar, en rojo: las reglas y en qué momento del ciclo está ("Ahora: Oleada 3 de 6: Orcos…").
2. Cada segundo, abajo de la pantalla:
   - `Reloj de Arena | Descanso | la oleada 1 (Escarabajos) empieza en 12 s`
   - `Reloj de Arena | Oleada 3 de 6: Orcos | quedan 42 s | despues: Acero`
3. Al empezar cada oleada, en rojo: `Reloj de Arena: oleada 3 de 6: Orcos.`
4. **Braseros del norte:** 6, tres a cada lado de Chronos. Echan fuego uno por oleada ya empezada (en la
   oleada 4, los 4 primeros, de izquierda a derecha). En el descanso están apagados.
5. Cartel en la sala (junto a la salida) y Chronos (`hi`, `reglas`, `oleada`) explican lo mismo.

Al empezar una oleada se van los monstruos que quedaron de la anterior, sin exp ni botín. Para empezar
desde la 1, entrar en el descanso.

No hay costo ni turnos.

---

## Oleadas

| # | Nombre | Monstruos |
|---|--------|-----------|
| 1 | Escarabajos | Scarab ×3, Ancient Scarab ×1 |
| 2 | Cazadoras | Amazon ×2, Valkyrie ×2 |
| 3 | Orcos | Orc Berserker ×2, Orc Shaman ×1, Orc Leader ×1 |
| 4 | Acero | Hero ×1, Black Knight ×1, Gargoyle ×1 |
| 5 | Necropolis | Vampire ×2, Necromancer ×1, Lich ×1 |
| 6 | Abismo | Demon ×1, Fury ×1 |

**Monstruos normales, sin variantes rage** (Angry / Furious / Enraged): pedido de Gonzalo, nov 2026.
Menos monstruos que antes porque la sala es más chica. Salieron Bone Beast, Hunter, Giant Spider, Warlock
y **Wrath** (Wrath sigue al final del Gauntlet).

Estado del ciclo (en `chronos.lua`):

```lua
t = os.time() % (REST_SEC + 6 * WAVE_SEC)   -- 30 + 6*60 = 390
-- t < 30: descanso; si no, oleada floor((t - 30) / 60) + 1
```

---

## Sala

| Coord | Uso |
|-------|-----|
| `333–343, 388–396, 6` | Piso de arena (11×9), paredes de arenisca alrededor |
| `338, 395, 6` | Llegada |
| `338, 396, 6` | Portal de salida (entre dos estatuas de arenisca) |
| `339, 396, 6` | Cartel con las reglas |
| `338, 388, 6` | Chronos (`npc.xml`) |
| `333–335` y `341–343, 388, 6` | Braseros de las oleadas 1–6 |
| `335, 392` y `341, 392, 6` | Columnas de arenisca (cobertura) |
| `325–351, 381–403`, z6 / z5 | Tierra alrededor (bloquea) y techo de madera: desde adentro no se ve negro |

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
| `MSG_RED_INFO` (`18` / `0x12`) | Entrada (reglas + estado) y cambio de oleada |

Diálogo Chronos: `hi` → `reglas` / `help` (las reglas) y `oleada` / `time` / `fase` / `reloj` (estado actual).

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
python3 scripts/map/generate-sand-clock.py --dry-run     # valida (llegada, salida, Chronos y spawns alcanzables)
python3 scripts/map/generate-sand-clock.py               # escribe mapa, cartel y manifiesto
python3 scripts/map/temple-portals.py                    # portal y cartel de la plaza
python3 scripts/map/check-map-load.py
python3 scripts/map/validate-tele-dest.py server/YurOTS/ots/data/world/test.otbm
python3 scripts/npc/run_npc_tests.py chronos             # ciclo completo de oleadas
```

Las coordenadas de la sala, los braseros y los spawns están en el generador y en `chronos.lua`: si se
mueve algo, cambiarlo en los dos.

- Solo Lua/NPC XML: restart OT.
- Si tocaste `npc.cpp` / `npc.h`: **rebuild C++** (`make clean && make` si cambió el header de forma que afecte ABI; al menos `make -j2 yurots`) + restart + `python3 scripts/ot-probe.py 127.0.0.1 7171`.
- Deploy mapa: checklist depots ([`DEPOTS.md`](DEPOTS.md)); preguntar antes de VPS.

---

## Probar

1. Entrar por `168, 47, 7`: llegan las reglas y el estado en rojo.
2. Ver la línea `Reloj de Arena | …` abajo, cada segundo.
3. En el descanso, la sala vacía y los braseros apagados; al empezar la oleada 1, 3 Scarab y 1 Ancient
   Scarab, y el primer brasero con fuego.
4. Al cambiar de oleada se van los monstruos viejos y llegan los nuevos; se enciende un brasero más.
5. Después de la oleada 6, descanso.
6. Salir por el portal sur → `168, 48, 7`.

La prueba de NPC (`scripts/npc/run_npc_tests.py chronos`) recorre el ciclo entero con dos jugadores en la
sala: mensajes, monstruos, braseros y limpieza.

**Estado (2026-11-11):** cargado en el servidor de prueba de la ThinkPad ([`THINKPAD_TEST_SERVER.md`](../systems/THINKPAD_TEST_SERVER.md)); el servidor arranca y carga el mapa. Falta recorrerlo en el juego. No está en el VPS.

Relacionado: [`WAVE_ARENA.md`](WAVE_ARENA.md), [`../CAMBIAR-MAPA.md`](../CAMBIAR-MAPA.md).
