# Stairs: rollback al comportamiento default

> **Estado actual: REVERTIDO (comportamiento default restaurado)**
>
> El server volvio al flujo original: bajar automaticamente al pisar tiles
> con `floorChangeDown()`. El parche temporal de la seccion anterior fue
> removido.

## Problema que resuelve hoy

La idea pedida fue:

- no bajar automaticamente al pisar stairs
- dejar la bajada fuera del movimiento implicito

Eso hoy se resolvio de forma global en el motor, no como feature aislada por
item, tile o mapa.

## Donde esta el parche

Archivo principal:

- `server/YurOTS/ots/source/game.cpp`

Punto exacto:

- `Game::thingMoveInternal(...)`
- bloque de "change level begin"

Linea clave actual:

```cpp
if(false && toTile->floorChangeDown())
```

Referencia:

- [server/YurOTS/ots/source/game.cpp](/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/source/game.cpp:3090)

## Que hacia el comportamiento default

Originalmente, si el player caminaba sobre un tile con `floorChangeDown()`,
el motor:

1. detectaba que el tile implicaba bajar piso
2. buscaba el tile correspondiente un nivel mas abajo
3. teletransportaba al player a la posicion correcta segun los flags de piso

La logica de soporte sigue existiendo en:

- [server/YurOTS/ots/source/tile.cpp](/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/source/tile.cpp:149)
- `Tile::floorChangeDown()`

O sea: el parche actual **no elimina** la mecanica original; solo la deja
muerta desde el flujo de movimiento.

## Impacto real del parche

Este cambio no afecta solo "unas stairs".

Afecta **todo item/tile del mapa** que use `floorChangeDown()`:

- stairs
- agujeros u otros descensos implementados con ese flag
- cualquier contenido futuro del mapa que dependa del comportamiento default

Por eso conviene tratarlo como parche delicado del core.

## Como volver al comportamiento default

### Cambio minimo

Editar:

- `server/YurOTS/ots/source/game.cpp`

Buscar:

```cpp
if(false && toTile->floorChangeDown())
```

Y dejarlo asi:

```cpp
if(toTile->floorChangeDown())
```

No hace falta tocar `tile.cpp`, porque la logica original ya esta viva ahi.

### Resumen tecnico

- rollback = una sola linea
- no requiere cambiar mapa
- no requiere cambiar XML de items
- si es un cambio de C++, requiere recompilar el server

## Checklist de rollback

1. Cambiar la condicion en `game.cpp`.
2. Recompilar el server.
3. Reiniciar el server.
4. Probar stairs normales.
5. Probar cualquier hole/tile de bajada relevante del mapa.
6. Verificar que no haya descensos dobles o posiciones diagonales mal resueltas.

## Checklist de prueba funcional

Despues del rollback conviene probar:

1. Subir y bajar por stairs clasicas.
2. Bajar por diagonales donde el tile inferior define `floorChange(NORTH|SOUTH|EAST|WEST)`.
3. Agujeros o descensos especiales si el mapa los usa.
4. Movimiento rapido sobre stairs para confirmar que no haya teleports incorrectos.
5. Zonas con protection zone y training por si hay interacciones de posicion no previstas.

## Riesgos si se deja como esta

- El comportamiento default del mapa queda alterado globalmente.
- Un mapper puede usar `floorChangeDown()` esperando OT clasico y el server no va a responder.
- La razon del cambio queda escondida en una condicion `if(false && ...)` si no se consulta esta documentacion.

## Recomendacion de largo plazo

Si mas adelante quieren "stairs manuales" sin romper el default del motor, lo
correcto es una de estas opciones:

1. restaurar el core default
2. mover la excepcion a `use` / click sobre stairs concretas
3. crear un flag de config o un actionid por stairs especiales

Eso evita que una preferencia puntual de UX quede embebida como hack global del
movimiento base.

## Archivos relacionados

- [server/YurOTS/ots/source/game.cpp](/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/source/game.cpp:3090)
- [server/YurOTS/ots/source/tile.cpp](/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/source/tile.cpp:149)
- [server/YurOTS/ots/source/item.cpp](/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/source/item.cpp:497)
