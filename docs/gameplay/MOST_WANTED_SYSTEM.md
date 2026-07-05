# Most Wanted / Bounty System

## Objetivo

Agregar un NPC que permita contratar una caceria usando **saldo bancario** y mantener una lista dinamica **Most Wanted**:

- un jugador paga una recompensa desde su cuenta bancaria
- la recompensa se carga sobre un **target**
- si otro player mata a ese target en PvP valido, la recompensa **no se paga** en oro
- en cambio, la recompensa se **transfiere al killer**, que pasa a cargarla en su propia cabeza
- la web muestra la lista **Most Wanted** ordenada por recompensa descendente

La recompensa total del sistema solo puede:

- **subir** cuando alguien crea una bounty nueva
- **moverse** de un player a otro en kills PvP validos

No hay mint ni payout intermedio.

## Modelo de datos

Se eligio persistir la recompensa dentro del XML del player, usando el atributo root:

```xml
<player ... bounty="50000" ...>
```

### Por que en el player XML y no en un archivo aparte

- la web ya escanea `server/YurOTS/ots/data/players/*.xml`
- el estado sobrevive reinicios sin una segunda fuente de verdad
- el transfer en muerte PvP ocurre naturalmente sobre `victim` y `killer`
- evita sincronizar `players.xml` + `bounties.xml`

## Invariantes

Estas reglas se preservan en la implementacion:

- `bounty >= 0`
- solo se crea bounty usando `account.balance`
- no se puede crear bounty sobre un player del **mismo account**
- no se puede crear bounty sobre targets no atacables (`access` protegido / staff)
- una muerte por monstruo, field o sin killer player **no mueve** la bounty
- una muerte PvP valida mueve **todo** el bounty del muerto al killer
- si el killer ya tenia bounty, ambas se **acumulan**
- si falla un save critico, se intenta **rollback**

## Archivos tocados

### Core servidor

- `server/YurOTS/ots/source/player.h`
- `server/YurOTS/ots/source/player.cpp`
- `server/YurOTS/ots/source/ioplayerxml.cpp`
- `server/YurOTS/ots/source/bounty.h`
- `server/YurOTS/ots/source/bounty.cpp`
- `server/YurOTS/ots/source/npc.h`
- `server/YurOTS/ots/source/npc.cpp`
- `server/YurOTS/ots/source/game.cpp`

### NPC

- `server/YurOTS/ots/data/npc/bounty master.xml`
- `server/YurOTS/ots/data/npc/scripts/bounty_master.lua`
- `server/YurOTS/ots/data/world/npc.xml`

### Web

- `web/data.py`
- `web/index.html`
- `web/test_data.py`

## Flujo de alta de bounty

### NPC

NPC nuevo: `Bounty Master`

Spawn configurado en:

- `x=130, y=55, z=6`

Si ese tile quedara bloqueado en mapa, solo hay que mover la entrada en `data/world/npc.xml`.

### Comandos del NPC

- `bounty 10000 Nombre`
- `hunt 50000 Nombre`
- `hunt all Nombre`
- `status Nombre`
- `wanted Nombre`

### Secuencia tecnica

1. El NPC parsea monto + target.
2. Muestra confirmacion `yes/no`.
3. Lua llama a `doPlayerPlaceBounty(cid, amount, target)`.
4. C++ ejecuta `BountySystem::placeBounty(...)`.
5. Se carga la `Account` del sponsor.
6. Se carga el `Player` target desde XML.
7. Se valida:
   - monto > 0
   - balance suficiente
   - target existe
   - target atacable
   - target no pertenece a la misma cuenta
   - no hay overflow al acumular bounty
8. Se descuenta `account.balance`.
9. Se suma `player.bounty`.
10. Se persisten ambos cambios.
11. Se emite un `MSG_RED_TEXT` global anunciando:
   - quien puso la bounty
   - sobre quien
   - cuanto agrego
   - cuanto vale ahora matarlo

## Rollback en alta de bounty

Para evitar inconsistencias:

- si falla `saveAccount(sourceAccount)`, no se persiste nada
- si falla `savePlayer(target)`, se restaura:
  - el `bounty` anterior del target
  - el `balance` anterior del sponsor

Esto deja el sistema en estado original.

## Flujo de transferencia por kill PvP

Punto de integracion:

- `GameState::onAttackedCreature(...)` en `game.cpp`

### Reglas

- solo corre si la victima es `Player`
- solo corre si el killer final es `Player`
- soporta `summon -> master` usando la misma resolucion que el kill log
- si la victima tiene `bounty == 0`, no hace nada
- si el killer no es atacable/staff, no hace nada

### Secuencia tecnica

1. Se identifica `killNotifyPlayer`.
2. Se llama `BountySystem::transferBountyOnKill(victim, killer, ...)`.
3. Si la victima tenia bounty:
   - `victim.bounty = 0`
   - `killer.bounty += oldVictimBounty`
4. Se persiste primero el killer.
5. Se persiste despues la victima.
6. Si todo sale bien:
   - se loguea en consola / `server.log`
   - se avisa al killer y a la victima

## Rollback en transferencia PvP

Si falla el save del killer:

- se restauran ambos valores en memoria
- no queda persistido ningun cambio

Si falla el save de la victima despues de guardar killer:

- se restauran ambos valores en memoria
- se intenta regrabar el killer con su bounty anterior

## Semantica funcional final

Ejemplo:

1. `A` pone `50k` sobre `B`
2. `B` queda con `bounty=50000`
3. `C` mata a `B`
4. `B` queda con `0`
5. `C` pasa a `50000`
6. `D` mata a `C`
7. `D` pasa a `50000`

Si antes `D` ya tenia `20000`, termina con `70000`.

## Web: lista Most Wanted

La web lee `bounty` desde `parse_player(...)` en `web/data.py`.

Se expone un nuevo bloque en el payload:

```json
"most_wanted": [
  {
    "name": "Beta",
    "level": 18,
    "vocation_short": "S",
    "bounty": 12000,
    "bounty_fmt": "12.000"
  }
]
```

### Orden

Se ordena por:

1. `bounty desc`
2. `level desc`
3. `name asc`

### Filtro publico

La lista respeta el mismo filtrado publico que el resto del sitio:

- no muestra staff
- no muestra chars ocultos de ranking

## UI web

Se agrego:

- panel `Wanted`
- tabla `Most Wanted`
- snapshot rapido del top wanted en la home

## Cobertura automatizada agregada

Archivo:

- `web/test_data.py`

### Casos cubiertos

1. `parse_player` lee `bounty` cuando existe.
2. `parse_player` usa `0` cuando el atributo no existe.
3. `build_payload` genera `most_wanted`.
4. `most_wanted` sale ordenado por recompensa.
5. players ocultos no aparecen en la lista publica.

### Comando

```bash
python3 -m unittest web/test_data.py
```

## Validaciones de sintaxis ejecutadas

### Python

```bash
PYTHONPYCACHEPREFIX=/private/tmp/codex-pyc python3 -m py_compile web/data.py web/server.py web/test_data.py
```

### Lua

```bash
lua -e "assert(loadfile('server/YurOTS/ots/data/npc/scripts/bounty_master.lua'))"
```

## Pruebas manuales recomendadas

### Caso 1: alta simple

1. Loguear `Player A` con bank balance suficiente.
2. Hablar con `Bounty Master`.
3. Decir `bounty 10000 Player B`.
4. Confirmar `yes`.
5. Verificar:
   - baja `account.balance` de `Player A`
   - `Player B` queda con `bounty=10000`
   - todos los players online reciben mensaje rojo global
   - web muestra a `Player B` en `Most Wanted`

### Caso 2: acumulacion

1. Repetir con otro sponsor o mismo sponsor.
2. Poner `bounty 15000 Player B`.
3. Verificar total `25000`.

### Caso 3: target inexistente

1. `bounty 10000 Nadie`
2. Debe fallar sin tocar bank ni XML.

### Caso 4: misma cuenta

1. Intentar bounty sobre otro char del mismo account.
2. Debe rechazar.

### Caso 5: kill PvP valido

1. `Player C` mata a `Player B`.
2. Verificar:
   - `Player B.bounty == 0`
   - `Player C.bounty += oldBountyB`
   - log en consola / `server.log`
   - web actualizada

### Caso 6: killer ya wanted

1. Dar bounty previa a `Player C`.
2. Hacer que mate a `Player B`.
3. Verificar suma acumulada.

### Caso 7: muerte por monstruo

1. Dar bounty a `Player B`.
2. Matarlo con monstruo o field.
3. Verificar que la bounty siga sobre `Player B`.

### Caso 8: kill por summon

1. `Player C` mata a `Player B` usando summon.
2. Verificar que la bounty pase a `Player C`.

## Riesgos y notas

- El spawn del NPC se dejo configurado, pero conviene validar en mapa que el tile sea caminable.
- La build completa del server en esta maquina no pudo validarse end-to-end porque el toolchain local ya falla antes de entrar en este feature por headers base (`lua.h`) y otros errores legacy del proyecto.
- La logica nueva se dejo encapsulada en `bounty.cpp` para que cualquier ajuste futuro no tenga que duplicarse entre NPC y PvP kill handling.

## Resumen

El sistema implementado convierte la bounty en una **carga transferible** entre players, financiada desde banco, persistida por player XML, visible en la web y protegida con rollback en los puntos criticos de persistencia.
