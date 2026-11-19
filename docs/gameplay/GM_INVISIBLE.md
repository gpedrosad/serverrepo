# `/invisible` del GM

`/invisible` (`commands.cpp`, `Commands::gmInvisible`) alterna `Player::gmInvisible`. Los jugadores con menos
`access` dejan de recibir al GM: el protocolo no lo manda en las casillas (`protocol76.cpp`) y sus movimientos
solo les llegan a él y a los de igual o más `access` (`game.cpp`). Al entrar al juego el GM está siempre visible.

## Pasa por encima de jugadores y monstruos (19 nov 2026)

`Creature::canMovedTo` ignora las criaturas de la casilla de destino cuando el que camina es un GM invisible.

- **Orden en la casilla:** el GM invisible va siempre **debajo** de las demás criaturas (`Tile::addThing`; al
  prender `/invisible` se lo reacomoda). Así el *stackpos* de las criaturas que se ven es el mismo en el servidor
  y en los clientes que no lo ven: si el GM quedara arriba, el cliente de un jugador que sale de esa casilla
  recibiría un *stackpos* corrido en uno y se desordenaría.
- Su propio cliente, al entrar a una casilla con otros, lo pone arriba. Por eso el servidor le manda esa casilla
  entera (`onTileUpdated`, en `Game::thingMoveInternal`) y quedan con el mismo orden.
- Al revés también: un GM invisible no le tapa el paso a nadie (`Tile::hasBlockingCreature`).
- **Lo que sigue igual:** los ítems que están debajo de las criaturas de esa casilla (cadáveres, cosas tiradas)
  tienen el *stackpos* corrido en uno para quien no ve al GM. Ya pasaba antes con el GM invisible parado sobre
  ítems. Si alguien no puede usar o agarrar algo del piso donde está el GM invisible, que el GM se corra.

## Se ve como un Ghost (19 nov 2026)

Con `/invisible` el servidor le pone el looktype **48** (el del monstruo Ghost, `GM_GHOST_LOOKTYPE` en
`const76.h`) y le manda la casilla: solo él (y los de igual o más `access`) lo ven así. Con `/invisible` otra vez
vuelve a `oldlooktype`. Si cambia el outfit estando invisible (`parseSetOutfit`), el nuevo queda guardado para
cuando vuelva a ser visible. En disco se guarda `lookmaster`, así que el Ghost nunca queda grabado.

Primero se probó un shader semitransparente en el cliente, pero este OTClientV8 (3.2) no tiene
`creature:setOutfitShader` (en el binario solo están `createOutfitShader` y `setShader`): se sacó
(`clienteretro` `1df2b7b`).
