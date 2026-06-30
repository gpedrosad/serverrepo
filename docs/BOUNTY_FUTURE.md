# Bounty System — idea de implementacion futura

> **Estado actual: NO IMPLEMENTADO**
>
> El archivo `bounty.cpp` existe en disco pero esta excluido del build
> via `Makefile`. La API publica (`bounty.h`) esta completa pero nunca
> se llama desde ningun lado. No hay NPC, comando ni handler de muerte
> que lo dispare.

## Resumen funcional

Sistema de recompensa por matar a un jugador especifico.

- **placeBounty**: un jugador (sponsor) pone oro del banco sobre la cabeza de un target. El oro se descuenta del balance de la cuenta del sponsor y se acumula en un contador del target.
- **getBountyByName**: cualquier GM o NPC puede consultar cuanto tiene acumulado un target.
- **transferBountyOnKill**: cuando el target muere a manos de un attacker, el oro acumulado se transfiere al attacker (menos comision si la hubiera).

## Diseno esperado

- `Player::bountyValue` (`uint64_t`) — persistido en el XML de save del player.
- `Player::getBountyValue()` / `Player::setBountyValue(v)` — accessors.
- `BountySystem::placeBounty(...)` — debita del `Account::balance` del sponsor, acredita al `bountyValue` del target.
- `BountySystem::getBountyByName(...)` — consulta el save del target.
- `BountySystem::transferBountyOnKill(victim, killer, ...)` — mueve el bounty del victim al killer, persiste ambos.

## Lo que se hizo antes y se desactivo

- `server/YurOTS/ots/source/bounty.h` — API publica completa (namespace `BountySystem`, 3 funciones + enum de errores).
- `server/YurOTS/ots/source/bounty.cpp` — implementacion de las 3 funciones (179 lineas). Llama a `IOPlayer` y `IOAccount` para persistir.
- **Stubs temporales** en `player.h` / `player.cpp` (ya borrados):
  - `Player::getBountyValue() / setBountyValue(v)` (inline en el header).
  - Miembro `uint64_t bountyValue;`.
  - `bountyValue = 0;` en el constructor.
  - Estos stubs existieron solo para que `bounty.cpp` linkee; ahora que `bounty.cpp` esta fuera del build, los stubs no son necesarios.

## Checklist para implementarlo de verdad

1. **Persistir bounty en el save del player**
   - Agregar a `Player::bountyValue` (`uint64_t`).
   - Agregar accessors `getBountyValue()` / `setBountyValue(v)`.
   - Modificar `IOPlayer::savePlayer` / `loadPlayer` para serializar/deserializar el campo.
   - Verificar que players con bounty al login la conserven.

2. **Re-activar el build**
   - En `server/YurOTS/ots/source/Makefile`, linea 27:
     ```
     SRCS = $(filter-out mdump.cpp bounty.cpp, $(wildcard *.cpp))
     ```
     Sacar `bounty.cpp` del `filter-out`. Volver a agregar los accessors de Player (paso 1) **antes** de recompilar, si no el link falla con undefined references.

3. **Hookear la transferencia al morir**
   - En `Game::onAttackedCreature` o `Game::onCreatureDie` (donde hoy se procesa la muerte del player), justo despues de aplicar el danio letal, llamar:
     ```
     BountySystem::transferBountyOnKill(victim, killer, NULL, NULL);
     ```
   - Validar que el killer es attackable y distinto del victim (ya esta en `bounty.cpp:140-142`).

4. **Exponer la colocacion de bounty**
   - Opcion A: comando de GM `/bounty <nombre> <cantidad>` en `commands.cpp`.
   - Opcion B: NPC especifico (crear `bounty master.xml` + script lua en `data/npc/scripts/bounty_master.lua`).
   - En ambos casos, internamente llamar `BountySystem::placeBounty(game, sponsor, amount, targetName)`.

5. **Test funcional minimo**
   - Sponsor A pone 1000gp de bounty sobre Target B.
   - Verificar en save de B: `bountyValue = 1000`.
   - Verificar save de A: `Account::balance -= 1000`.
   - Killer C mata a B. Verificar save de C: `bountyValue += 1000` (si el sistema lo permite) o `balance += 1000` (si se paga al bank directo). Verificar save de B: `bountyValue = 0`.
   - Reiniciar server, relogear A, B, C: los valores tienen que coincidir.

## Riesgos / cosas a flagear

- **Persistencia**: si `IOPlayer` no serializa `bountyValue`, se pierde entre logins. Es el riesgo #1 — leer bien el flujo de save/load antes de implementar.
- **Race conditions**: el debito al sponsor y el credito al target deben transaccionarse juntos. `bounty.cpp` ya hace rollback manual en `placeBounty` (lineas 100-110) — respetarlo si se modifica.
- **Target deslogueado al matarlo**: `bounty.cpp:125-126` carga el target desde disco si no esta online. Verificar que la ruta de IO no se rompe si el save esta corrupto.
- **Killer == sponsor**: ya esta bloqueado en `transferBountyOnKill` (linea 140).
- **Bounty sobre si mismo**: ya esta bloqueado en `placeBounty` (linea 84).
- **Acumulacion**: limite a `uint64_t` max — `bounty.cpp:31-34` ya lo chequea.
- **Persistencia de `Account::balance`**: el sponsor paga de su cuenta de banco. Si esa economia no esta bien atada, la plata sale del aire.

## Archivos clave

- `server/YurOTS/ots/source/bounty.h` — API publica.
- `server/YurOTS/ots/source/bounty.cpp` — implementacion (179 lineas).
- `server/YurOTS/ots/source/player.h` — agregar accessors + miembro.
- `server/YurOTS/ots/source/player.cpp` — constructor (init), `onDie` si se hookea ahi.
- `server/YurOTS/ots/source/game.cpp` — `onAttackedCreature` / `onCreatureDie` (donde se llama `transferBountyOnKill`).
- `server/YurOTS/ots/source/commands.cpp` — si se expone como comando GM.
- `server/YurOTS/ots/data/npc/bounty master.xml` + `data/npc/scripts/bounty_master.lua` — si se expone como NPC.
- `server/YurOTS/ots/source/ioplayer.cpp` / `ioplayerxml.cpp` — serializacion del save.
- `server/YurOTS/ots/source/Makefile` (linea 27) — activar/desactivar el build.

## Estado del build hoy

- `bounty.cpp` excluido del build.
- `Player` sin metodos de bounty.
- Binario actual linkea sin undefined references y arranca OK.
- Cualquier reversión del `filter-out` sin volver a poner los accessors de Player rompe el link.
