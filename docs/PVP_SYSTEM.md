# Sistema PvP

## Objetivo

Este documento describe el estado actual del PvP de `Retro76/YurOTS` tal como queda implementado hoy en el server retro 7.6 del repo.

La idea es que sirva como referencia de mantenimiento:

- que reglas existen realmente
- que parte es visual y que parte afecta frags/skulls
- donde vive cada regla en el codigo
- que configuracion manda el comportamiento

## Config actual

Valores vigentes en [server/YurOTS/ots/config.lua](/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/config.lua):

- `worldtype = "pvp"`
- `pzlocked = 10*1000`
- `pvpunderdogexp = "yes"`
- `pvpunderdogexp_percent = 50`
- `redunjust = 3`
- `banunjust = 6`
- `hittime = 1`
- `whitetime = 15`
- `redtime = 6*60`
- `fragtime = 5*60`

Interpretacion actual:

- `hittime`: 1 minuto
- `whitetime`: 15 minutos
- `redtime`: 6 horas
- `fragtime`: 5 horas por frag
- `pzlocked`: 10 segundos fuera de PZ despues de PvP valido

## Mapa mental rapido

El sistema PvP se reparte en 4 piezas:

1. Validacion de si un objetivo se puede atacar.
2. Resolucion de dano y PZ lock.
3. Logica de skulls y frags.
4. Visualizacion cliente de skulls y party.

Archivos clave:

- [game.cpp](/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/source/game.cpp)
- [player.cpp](/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/source/player.cpp)
- [player.h](/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/source/player.h)
- [protocol76.cpp](/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/source/protocol76.cpp)
- [protocol76.h](/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/source/protocol76.h)
- [const76.h](/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/source/const76.h)
- [commands.cpp](/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/source/commands.cpp)

## 1. Cuando se puede atacar

La seleccion de objetivo jugador -> jugador se controla en [game.cpp](/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/source/game.cpp:5319).

Hoy el server bloquea el ataque en estos casos:

- el objetivo no existe
- el objetivo tiene `access >= ACCESS_PROTECT`
- el mundo es `no-pvp`
- ambos son rookies y aplica la regla de rook
- ambos estan en training con regla `trainingNoPvp`
- el objetivo es summon de otro jugador en un contexto no permitido

Excepciones/restricciones especiales:

- si ambos estan en PvP Arena, el arena puede saltear restricciones de `no-pvp`/training
- si se intenta atacar dentro de training con bloqueo PvP, el player recibe mensaje de cancelacion
- si dos jugadores estan en la misma party, el sistema de skull/frags directamente no procesa PvP entre ellos

Documentacion relacionada:

- [docs/TRAINING_ZONE_NO_PVP.md](/Users/gonzalo/Desktop/yurots-principal/docs/TRAINING_ZONE_NO_PVP.md)

## 2. Dano, combate y PZ lock

La resolucion del dano ocurre por dos caminos principales:

- combate melee/distancia basico en [game.cpp](/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/source/game.cpp:554)
- runas/hechizos/ataques por area en [game.cpp](/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/source/game.cpp:338)

Reglas PvP relevantes:

- cuando hay dano PvP valido, el atacante entra en `pzLocked`
- el objetivo recibe o refresca `inFightTicks`
- mientras `pzLocked` siga activo, no puede entrar a PZ normalmente
- `!pz` muestra el tiempo restante

Referencias:

- [commands.cpp](/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/source/commands.cpp:906)
- [game.cpp](/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/source/game.cpp:4373)

Notas:

- el icono de espadas se manda desde `sendIcons()`
- el sistema usa `inFightTicks` y `pzLocked` separados: el lock practico termina cuando el tick baja de 1 segundo

## 3. Skull system real

Los skulls reales del server estan definidos en [const76.h](/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/source/const76.h:281):

- `SKULL_NONE = 0`
- `SKULL_YELLOW = 1`
- `SKULL_WHITE = 3`
- `SKULL_RED = 4`

Importante:

- `white` y `red` son estados reales del jugador
- `yellow` hoy se usa como derecho de retaliacion visual/contextual
- `yellow` no reemplaza al `skullType` persistido del target

### White skull

La logica principal vive en [game.cpp](/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/source/game.cpp:6752).

Comportamiento actual:

- si `A` pega a `B` y no es muerte, `A` recibe `white skull` solo si:
  - `B` tiene `SKULL_NONE`
  - `A` estaba en `SKULL_NONE`
- la duracion por golpe inicial sale de `hittime`
- si `A` mata a `B` en un asesinato injustificado pero todavia no llega a red, `A` queda `white` por `whitetime`

Caveat actual del codigo:

- hoy el white por hit no se refresca automaticamente en cada golpe posterior si el atacante ya seguia white; solo se setea al entrar desde `SKULL_NONE`

### Red skull

Tambien en [game.cpp](/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/source/game.cpp:6771).

Comportamiento:

- cada asesinato injustificado suma 1 frag (`skullKills`)
- al llegar a `redunjust`, el killer recibe `SKULL_RED`
- la duracion del red sale de `redtime`

### Ban por frags

Si `skullKills >= banunjust`:

- `player->banned = true`
- el personaje queda bloqueado al login

Referencias:

- [game.cpp](/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/source/game.cpp:6777)
- [otserv.cpp](/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/source/otserv.cpp:375)

## 4. Yellow skull de retaliacion

Este es el cambio nuevo mas importante del sistema.

### Que significa

`Yellow skull` ahora significa:

- "este jugador te agredio recientemente"
- "si lo matas dentro de la ventana de retaliacion, no te suma frag"

No significa:

- pertenecer a tu party
- un skull persistido del target
- una cuenta global visible igual para todos

### Como funciona

La victima recibe un `yellow` personal sobre su agresor cuando hay agresion PvP no letal en [game.cpp](/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/source/game.cpp:6754).

Regla actual:

- si `A` pega a `B`, entonces `B` gana `yellow skull` personal sobre `A`
- la ventana dura `hittime`
- el `yellow` se guarda en `B.yellowSkullTicks[A]`
- solo afecta como `B` ve a `A`

Implementacion:

- estado: [player.h](/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/source/player.h:430)
- tick y expiracion: [player.cpp](/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/source/player.cpp:3655)
- alta: [player.cpp](/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/source/player.cpp:3671)
- consulta: [player.cpp](/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/source/player.cpp:3689)
- dibujo en protocolo: [protocol76.cpp](/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/source/protocol76.cpp:89)

### Consecuencia sobre frags

Un asesinato ya no suma frag si el killer tenia `yellow` valido sobre la victima.

La condicion injusta actual es:

- la victima tiene `SKULL_NONE`
- el killer NO tiene `yellow skull` sobre la victima

Referencia:

- [game.cpp](/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/source/game.cpp:6771)

### Prioridad visual

El cliente ve:

- `yellow` si el viewer tiene retaliacion valida sobre el target
- incluso si el target ya estaba `white`, el viewer puede verlo `yellow` para remarcar que hay derecho de respuesta
- salvo que el target tenga `red`, en cuyo caso se mantiene `red`

Referencia:

- [protocol76.cpp](/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/source/protocol76.cpp:97)

### Persistencia

`yellow` no se persiste.

Eso es deliberado:

- es una ventana efimera de combate
- vive en memoria
- expira por tick
- no se guarda en XML del player

## 5. Como se cuentan los frags

El contador persistente es `skullKills`.

Se guarda junto con:

- `skullType`
- `skullTicks`
- `absolveTicks`

en el nodo `<skull />` del XML del player.

Referencias:

- carga: [ioplayerxml.cpp](/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/source/ioplayerxml.cpp:362)
- guardado: [ioplayerxml.cpp](/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/source/ioplayerxml.cpp:789)

El decay de frags funciona asi:

- cada `fragtime` baja 1 frag
- si quedan frags, se reinicia `absolveTicks`
- si no quedan, `absolveTicks` vuelve a 0

Referencia:

- [player.cpp](/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/source/player.cpp:3637)

Comando util:

- `!frags` muestra frags actuales y tiempo hasta perder el siguiente

Referencia:

- [commands.cpp](/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/source/commands.cpp:1040)

## 6. Party

La party vive en `player->party` y usa `opcode 0x91` como canal de iconos.

### Reglas actuales

- solo el lider puede invitar
- una party nueva nace cuando el lider invita por primera vez
- `revoke`, `join`, `pass leadership`, `leave` y `disband` ya limpian mejor estados colgados
- los miembros de una misma party no se pueden dañar via `onPvP`

Referencias principales:

- invite/revoke/join/pass leadership: [protocol76.cpp](/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/source/protocol76.cpp:3156)
- leave/disband: [game.cpp](/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/source/game.cpp:6800)

### Relacion entre party y skulls

Regla nueva importante:

- la party ya no usa `yellow skull`
- la party usa sus iconos propios
- `skull` y `party` son canales distintos y no deben pisarse

Eso evita dos bugs historicos:

- perder el skull real al salir de party
- confundir "miembro de party" con "objetivo de retaliacion"

## 7. Summons y autoria del PvP

El sistema atribuye el PvP al master cuando corresponde.

En [game.cpp](/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/source/game.cpp:6734):

- si la criatura agresora tiene master, `onPvP` sustituye al summon por su owner

Consecuencias:

- el owner recibe skulls/frags/bandera de retaliacion
- no el summon

Ademas:

- en reglas `no-pvp` o training, los summons de player se tratan como entidades PvP y pueden ser bloqueados igual que un player

## 8. Exp por matar jugadores

El server tiene recompensa de exp por PvP.

### Reparto base por dano

El sistema ya acumula dano recibido por atacante usando `totaldamagelist`.

Referencias:

- alta de dano: [creature.cpp](/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/source/creature.cpp:205)
- calculo de exp: [creature.cpp](/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/source/creature.cpp:255)

### Underdog exp PvP

Adicionalmente, en mundo `pvp` normal:

- el killer puede ganar una parte de la exp perdida por la victima
- el porcentaje actual es `50%`
- se escala por proporcion de dano

No aplica en:

- `no-pvp`
- `pvp-enforced`

Referencia:

- [game.cpp](/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/source/game.cpp:1047)

## 9. Zonas y excepciones

### Training no PvP

Si ambos estan dentro del contexto bloqueado de training:

- no hay dano PvP entre players
- no deberia escalar a skull/frags
- se envia mensaje explicito al intentar atacar

Ver:

- [docs/TRAINING_ZONE_NO_PVP.md](/Users/gonzalo/Desktop/yurots-principal/docs/TRAINING_ZONE_NO_PVP.md)

### PvP Arena

Si ambos estan en PvP Arena:

- el arena puede permitir combate donde otras reglas lo bloquearian
- el dano letal se enruta con manejo especial de `arenaLosers`

Referencia:

- [game.cpp](/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/source/game.cpp:560)

### Rook

Hay chequeo especifico para rook vs rook en la seleccion de objetivo.

Referencia:

- [game.cpp](/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/source/game.cpp:5319)

## 10. Protocolo cliente

Para el cliente 7.6, el server usa:

- `0x90` para skull
- `0x91` para party/shield

Referencias:

- [protocol76.cpp](/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/source/protocol76.cpp:3131)
- [protocol76.cpp](/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/source/protocol76.cpp:3142)

Nota importante para este repo:

- el server retro no implementa el sistema moderno de `unjustified points` tipo Tibia 10+
- la fuente de verdad del PvP aqui es el protocolo 7.6 de skull/party y la logica del server

## 11. Estado actual y deuda tecnica conocida

El sistema ya soporta:

- `white skull`
- `red skull`
- frags persistentes con decay
- `yellow skull` de retaliacion sin frag
- separacion correcta entre `party` y `skull`
- PZ lock y `!pz`
- exp PvP por kill

Pendientes/observaciones:

- el `white skull` por hit no refresca su timer en cada golpe sucesivo si el atacante ya seguia white
- el panel moderno de `unjustified points` del cliente no representa el contrato real de este server retro
- conviene agregar smoke tests manuales/automatizados para:
  - none -> hit -> victim sees yellow
  - victim kills aggressor under yellow -> no frag
  - same kill without yellow -> frag
  - party leave/disband -> skull visual correcto

## 12. Smoke test manual sugerido

1. Crear `Player A` y `Player B` fuera de training/PZ.
2. Hacer que `A` pegue una vez a `B`.
3. Verificar:
   - `A` recibe white si antes estaba none
   - `B` ve a `A` con yellow
   - `!pz` en `A` muestra lock activo
4. Hacer que `B` mate a `A` dentro del minuto de `yellow`.
5. Verificar:
   - `B` no suma frag
   - `A` muere normal
6. Repetir pero dejando expirar el `yellow`.
7. Verificar:
   - matar a `A` ya vuelve a sumar frag si era asesinato injustificado
