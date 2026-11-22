# Reloj de Arena — desafío contrarreloj de 6 oleadas

Sala chica (11×9) compartida manejada por el NPC **Chronos** (v2, nov 2026). Funciona como un **reloj de arena real** (contrarreloj dinámico):

- **Sala dormida cuando está vacía (`IDLE`):** no spawnea ni borra monstruos sin jugadores.
- **Al entrar (`PREP`, 15 s):** cuenta regresiva de preparación antes de la oleada 1.
- **Contrarreloj (`ACTIVE`):** empezás con **90 s de arena** en el reloj y 6 oleadas estrictamente crecientes.
  - Apenas limpiás todos los enemigos de la oleada actual, **se suma el bonus de arena** (+40 a +65 s), la sala descansa **5 s** (`BETWEEN`, sin descontar arena) y sale enseguida la siguiente oleada.
  - Si completás las **6 oleadas** antes de quedarte sin arena → **Victoria**: récord personal de mejor tiempo + **premio diario de Chronos** (requiere participar en al menos 3 oleadas limpias de la ronda).
  - Si se acaba la arena → los monstruos de la ronda vuelven al polvo y hay **15 s** de descanso (`COOLDOWN`).
- **Summons de jugadores protegidos:** Chronos registra los monstruos que invoca (`wave_mobs`) y las variantes rage; los summons previos de jugadores no bloquean el avance ni se borran entre oleadas.

**v1 → v2 (nov 2026):** la v1 usaba reloj de pared (`os.time() % 390`) con 60 s fijos por oleada, orden de dificultad invertido (Ancient Scarab en la 1, Amazons en la 2, Demon + Fury = 17.400 HP en 60 s en la 6), sin recompensas, spawneando 24/7 al vacío y borrando monstruos a mitad de pelea (y summons de jugadores).

Portal en la plaza del templo: `168, 47, 7` (cartel `168, 46, 7`).
Retorno: portal al sur de la sala → templo `168, 48, 7`.
Portales del templo: tabla completa en [`CAMBIAR-MAPA.md`](../CAMBIAR-MAPA.md#portales-del-templo-plaza-z7--nov-2026).

---

## Qué ve el jugador

1. Al entrar, en rojo: las reglas y el estado actual de la sala.
2. Cada segundo, abajo de la pantalla (`MSG_SMALLINFO`):
   - `Reloj de Arena | Preparacion | oleada 1 (Dunas) en 12 s | arena inicial: 1 min 30 s`
   - `Reloj de Arena | Oleada 3/6: Escarabajos | quedan 3 enemigo(s) | Arena: 2 min 48 s`
   - `Reloj de Arena | Oleada 3 limpia! Siguiente (Necropolis) en 4 s | Arena: 3 min 38 s`
3. Al empezar y al limpiar cada oleada, en rojo (`MSG_RED_INFO`), con el tiempo de arena ganado.
4. **Braseros del norte:** 6, tres a cada lado de Chronos. Se encienden del 1 al N según la oleada activa; hacen burst de energía y fuego al ganar; se apagan en `IDLE`, `PREP` y `COOLDOWN`.
5. Cartel en la sala (junto a la salida) y Chronos (`hi` → `reglas`, `premio`, `record`, `estado`).

---

## Oleadas y tiempos

Arena inicial: **90 s**. Presupuesto máximo total de combate: `90 + 40 + 45 + 50 + 55 + 65 = 345 s` (5 min 45 s).

| # | Nombre | Monstruos | HP total | Bonus al limpiar |
|---|--------|-----------|----------|------------------|
| 1 | Dunas | 2 Scarab, 2 Mummy | 1.120 | +40 s |
| 2 | Horda | 2 Orc Berserker, 1 Orc Shaman, 1 Orc Leader, 1 Orc Warlord | 1.935 | +45 s |
| 3 | Escarabajos | 2 Ancient Scarab, 2 Scarab | 2.640 | +50 s |
| 4 | Necropolis | 2 Vampire, 1 Necromancer, 1 Lich, 1 Vampire Bride | 3.560 | +55 s |
| 5 | Acero | 1 Hero, 1 Black Knight, 1 Dragon Lord | 5.100 | +65 s |
| 6 | Guardian del Tiempo | 1 Demon | 8.200 | **Victoria** |

**Monstruos normales, sin variantes rage en el spawn.** Si algún monstruo revive como Angry/Furious/Enraged, también cuenta como enemigo de la oleada.

### Premio diario y récords (storage `9400–9402`)

Al completar la oleada 6 antes de que se acabe la arena:

- **Premio diario** (1 vez por día `YYYYMMDD`, requiere haber estado en ≥ **3** oleadas limpias de esa ronda):
  - `10.000 gp` (vía `doPlayerAddMoney`)
  - `40.000 exp` flat (vía `doPlayerAddExp`)
  - `2 gemas pequeñas` aleatorias (`2145–2150`, sin oro)
- **Récords personales:** mejor tiempo de combate y total de victorias.

| Storage | Uso |
|---------|-----|
| `9400` | `YYYYMMDD` del último premio diario cobrado |
| `9401` | mejor tiempo personal (segundos de combate en las 6 oleadas) |
| `9402` | total de victorias |

---

## Sala

Sala en el **distrito de eventos** (x≥560, lejos del mapa principal).

| Coord | Uso |
|-------|-----|
| `600–610, 320–328, 6` | Piso de arena (11×9), paredes de arenisca alrededor |
| `605, 327, 6` | Llegada |
| `605, 328, 6` | Portal de salida (entre dos estatuas de arenisca) |
| `606, 328, 6` | Cartel con las reglas |
| `605, 320, 6` | Chronos (`npc.xml`) |
| `600–602` y `608–610, 320, 6` | Braseros de las oleadas 1–6 |
| `602, 324` y `608, 324, 6` | Columnas de arenisca (cobertura) |
| `592–618, 313–335`, z6 / z5 | Tierra alrededor (bloquea) y techo de madera |

## Implementación

YurOTS actions no tienen `addEvent`. El tick global lo lleva el NPC **Chronos** (`onThink` ~1 s).

| Capa | Detalle |
|------|---------|
| Mapa | `scripts/map/generate-sand-clock.py` |
| NPC | `data/npc/chronos.xml` + `data/npc/scripts/chronos.lua` |
| Spawn | `data/world/npc.xml` → Chronos `605,320,6` |
| C++ | `npc.cpp` / `npc.h`: `doSummonCreature`, `doRemoveCreature`, `doSendMagicEffect`, `getTopCreature`, `isMonster`, `doPlayerAddMoney`, `doPlayerAddExp`, `doPlayerAddItem` |

## Archivos

| Archivo | Rol |
|---------|-----|
| [`scripts/map/generate-sand-clock.py`](../../scripts/map/generate-sand-clock.py) | OTBM + cartel |
| `data/npc/scripts/chronos.lua` | Máquina de estados contrarreloj, oleadas, premio diario, récords |
| `data/npc/chronos.xml` | Look / script |
| `data/world/npc.xml` | Posición Chronos (`605,320,6`) |
| `data/world/generated-sand-clock.json` | Manifiesto |
| `data/readables.xml` | Bloque `SAND_CLOCK_SIGNS` |
| `scripts/npc/scenarios/chronos.txt` | Prueba automatizada completa (`IDLE → PREP → 6 oleadas → victoria/premio → timeout → IDLE`) |

## Probar

```bash
python3 scripts/npc/run_npc_tests.py chronos
```

El escenario en `scripts/npc/scenarios/chronos.txt` usa las coordenadas reales (`605, 327, 6`) y prueba: sala vacía (`IDLE`), entrada con summon propio (`Demon Skeleton` protegido), cuenta regresiva `PREP`, limpieza de las 6 oleadas con bonus de arena y pausas `BETWEEN`, jugador que entra tarde (<3 oleadas, sin premio diario), entrega del premio diario + récord personal, diálogo con Chronos, timeout por fin de arena y reseteo a `IDLE` al salir.

Relacionado: [`WAVE_ARENA.md`](WAVE_ARENA.md), [`../CAMBIAR-MAPA.md`](../CAMBIAR-MAPA.md).
