# Sistema de Trade

Esta documentación cubre el **trade jugador vs jugador** del cliente 7.6 usado por este proyecto.

No cubre el **NPC trade**. Ese flujo vive aparte en `game_npctrade`, `npc.cpp` y documentación específica como [NPC_CONFIRMATION.md](gameplay/NPC_CONFIRMATION.md).

## Resumen

El trade entre jugadores está implementado y funciona en tres capas:

- **Cliente**: selección de ítem + target de jugador, ventana de confirmación y acciones `accept/reject/inspect`.
- **Protocolo 7.6**: opcodes `0x7D`, `0x7E`, `0x7F` para abrir/counter/cerrar trade.
- **Servidor**: validación, reserva temporal del ítem ofrecido, cancelaciones automáticas y swap final.

Archivos principales:

- `server/YurOTS/ots/source/game.cpp`
- `server/YurOTS/ots/source/protocol76.cpp`
- `server/YurOTS/ots/source/player.h`
- `cliente-oficial-retro/windows/modules/game_playertrade/playertrade.lua`
- `cliente-oficial-retro/windows/modules/game_interface/gameinterface.lua`

## Flujo actual

1. El jugador elige `Trade with ...` sobre un ítem pickupable.
2. El cliente manda `ClientRequestTrade`.
3. `Game::playerRequestTrade(...)` valida:
   - que el partner exista y no sea el mismo jugador;
   - que ambos no estén ocupados en otro trade;
   - que el ítem exista, coincida con `itemid` y sea pickupable;
   - que el partner esté a **máximo 2 SQM** y en el mismo `z`;
   - que el ítem no esté ya comprometido en otro trade;
   - que un contenedor ofrecido no supere **100 ítems** contando su raíz.
4. El servidor deja el ítem marcado en `tradeItems`, hace `useThing()` para mantenerlo reservado y abre la ventana propia (`0x7D`).
5. Si el otro jugador responde con otro `requestTrade`, ambos reciben la contraoferta (`0x7E`).
6. Cuando ambos aceptan, `Game::playerAcceptTrade(...)` hace una validación previa de capacidad/espacio usando `addItem(..., true)` y `removeItem(..., true)`.
7. Si la validación pasa, remueve ambos ítems de sus dueños actuales y los agrega al otro jugador.
8. Si algo falla, el trade se cancela sin mover ítems.

## Cancelaciones automáticas

El trade se cancela si ocurre cualquiera de estos casos:

- uno de los dos cierra la ventana;
- uno de los dos se aleja más de **2 SQM**;
- el ítem ofrecido se mueve, se usa, se consume o cambia de contenedor;
- el contenedor raíz o un ítem interno invalida la oferta;
- el intercambio final falla por capacidad o falta de espacio.

La invalidación automática se apoya en `Game::autoCloseTrade(...)`, que es llamado desde múltiples caminos de movimiento/uso de ítems.

## Endurecimientos agregados en esta revisión

Durante esta revisión se corrigieron dos problemas importantes del server:

### 1. AcceptTrade inválido ya no deja al jugador “pegado” en trade

Antes, un `AcceptTrade` fuera de flujo podía dejar `tradeState = TRADE_ACCEPT` aunque no existiera un trade real. Eso bloqueaba nuevos trades hasta que otro evento limpiara el estado.

Ahora `Game::playerAcceptTrade(...)` primero valida:

- `tradePartner != 0`;
- que ambos jugadores sigan apuntándose mutuamente;
- que ambos tengan `tradeItem`;
- que el partner siga existiendo.

Si eso no se cumple, el trade se cierra y el estado se limpia.

### 2. Se bloqueó el trade remoto por paquete forzado

Antes no había una validación explícita de distancia entre los dos jugadores al iniciar el trade, así que un cliente modificado podía intentar abrir trade con alguien lejano.

Ahora el servidor exige que ambos estén:

- en el mismo piso;
- a una distancia máxima de **2 SQM**;
- tanto al abrir el trade como al aceptarlo.

## UI cliente

El módulo visual del trade está en:

- `cliente-oficial-retro/windows/modules/game_playertrade/playertrade.lua`
- `cliente-oficial-retro/windows/modules/game_playertrade/tradewindow.otui`

Comportamiento relevante:

- `Accept` arranca deshabilitado.
- Se habilita cuando llega la contraoferta.
- `Reject` manda cierre explícito.
- click sobre un ítem de la lista usa `inspectTrade`.

Mac y Windows usan el mismo patrón de módulos para este sistema.

## Limitaciones conocidas

- El sistema está pensado para **ítems pickupables**.
- El límite de contenedor es **100 ítems** por oferta.
- No hay una suite automática dedicada a player trade en este repo hoy.
- El build local completo del server sigue dependiendo del entorno C/C++ del proyecto; esta revisión fue validada por lectura de flujo y consistencia de código, no por una compilación exitosa en esta máquina.

## Prueba manual sugerida

Chequeo rápido recomendado en juego:

1. Jugador A ofrece un ítem simple a Jugador B.
2. Jugador B responde con otro ítem simple.
3. Ambos aceptan y se valida el swap.
4. Repetir alejándose más de 2 SQM antes de aceptar: el trade debe cancelarse.
5. Repetir moviendo uno de los ítems ofrecidos antes de aceptar: el trade debe cancelarse.
6. Repetir intentando aceptar con un cliente alterado sin contraoferta real: el estado no debe quedar bloqueado.

## Estado tras la revisión

Estado actual del player trade:

- flujo principal implementado;
- cancelación por distancia e invalidez de ítem implementada;
- cierre limpio de estados inválidos implementado;
- documentación separada de PvP y separada de NPC trade.
