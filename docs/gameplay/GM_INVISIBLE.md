# `/invisible` del GM

`/invisible` (`commands.cpp`, `Commands::gmInvisible`) alterna `Player::gmInvisible`. Los jugadores con menos
`access` dejan de recibir al GM: el protocolo no lo manda en las casillas (`protocol76.cpp`) y sus movimientos
solo les llegan a él y a los de igual o más `access` (`game.cpp`). Al entrar al juego el GM está siempre visible.

## No le tapa el paso a nadie (19 nov 2026)

Antes, el GM invisible seguía ocupando su casilla: el que caminaba hacia ahí chocaba contra algo que no veía.

- `Tile::isBlocking` ya no cuenta a un GM invisible como criatura (`Tile::hasBlockingCreature`). Jugadores y
  monstruos pasan y se paran en su casilla.
- **Orden en la casilla:** el GM invisible va siempre **debajo** de las demás criaturas (`Tile::addThing`, y
  al prender `/invisible` se lo reacomoda). Así el *stackpos* de las criaturas que se ven es el mismo en el
  servidor y en los clientes que no lo ven. Si el GM quedara arriba, el cliente de un jugador que sale de esa
  casilla recibiría un *stackpos* corrido en uno y se desordenaría.
- **Lo que sigue igual:** los ítems que están debajo de las criaturas de esa casilla (cadáveres, cosas tiradas)
  tienen el *stackpos* corrido en uno para quien no ve al GM. Ya pasaba antes con el GM invisible parado sobre
  ítems. Si alguien no puede usar o agarrar algo del piso donde está el GM invisible, que el GM se corra.

## Se ve a sí mismo semitransparente (19 nov 2026)

El cliente no se enteraba de nada: el GM se veía igual estando invisible o no. Ahora, en el cliente
(`clienteretro`, `modules/game_shaders/shaders.lua`):

- Con el mensaje "You are invisible." le pone a su propio personaje el shader `outfit_ghost`
  (`data/shaders/outfit_ghost_fragment.frag`): el outfit con sus colores, lavado a gris azulado y al 45 %
  de opacidad.
- Con "You are visible again." o al salir del juego vuelve a `outfit_default`.

Si se cambia el texto de esos mensajes en `commands.cpp`, hay que cambiarlo también en `shaders.lua`.
