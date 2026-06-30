# Reemplazo de sesion por personaje

## Objetivo

Permitir que un personaje vuelva a entrar aunque ya tenga una sesion activa.
Antes el login devolvia `You are already logged in.`.

Ahora, cuando `allowclones = 0`, el comportamiento por defecto es:

1. Encontrar la sesion activa del personaje.
2. Forzar `logout()` de esa sesion para removerla del mapa y guardar el player.
3. Hacer `shutdown()` del socket viejo para destrabar su `ReceiveLoop`.
4. Continuar con el nuevo login del mismo personaje.

## Switch de rollback

En [server/YurOTS/ots/config.lua](/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/config.lua:56) quedaron estas flags:

```lua
allowclones = 0
replaceconnectedcharacter = 1
```

- `allowclones = 0`: sigue impidiendo clones simultaneos del mismo char.
- `replaceconnectedcharacter = 1`: habilita el reemplazo de sesion.
- `replaceconnectedcharacter = 0`: vuelve al comportamiento viejo y rechaza con `already logged in`.

## Archivos tocados

- [server/YurOTS/ots/source/otserv.cpp](/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/source/otserv.cpp:302)
- [server/YurOTS/ots/source/protocol.h](/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/source/protocol.h:38)
- [server/YurOTS/ots/source/protocol.cpp](/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/source/protocol.cpp:57)
- [server/YurOTS/ots/config.lua](/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/config.lua:56)

## Motivo tecnico

No alcanza con sacar el rechazo del login:

- El player online sigue vivo en `Player::listPlayer`.
- El socket viejo puede dejar un `ReceiveLoop` bloqueado en `recv()`.
- Si se crea otra instancia del mismo personaje sin bajar la anterior, se arriesga duplicacion de estado o saves inconsistentes.

Por eso el cambio baja primero la sesion vieja, guarda el estado y solo despues deja pasar la nueva.

## Riesgos a vigilar

- Si dos clientes intentan tomar el mismo char repetidamente, vas a ver reconexiones forzadas en cascada.
- La sesion vieja se puede cortar en medio de combate; esto ya usa la misma ruta de `kick/logout` que existe en el server.
- Si aparece un bug de reconexion, revisar la consola por la linea:

```text
Replacing active session for player: <name>
```

## Verificacion recomendada

1. Entrar con un personaje.
2. Intentar entrar con el mismo personaje desde otro cliente.
3. Confirmar que el segundo entra y el primero queda afuera.
4. Repetir con el personaje en movimiento y con backpack abierta.
5. Si algo falla, poner `replaceconnectedcharacter = 0` y reiniciar el server.
