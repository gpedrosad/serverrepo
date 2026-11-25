# Follow, modo perseguir y "usar" de lejos (25 nov 2026)

Hasta nov 2026 el server **no atendía el follow**: el cliente mandaba el paquete `0xA2` al elegir "Follow" (menú
del botón derecho, lista de batalla, doble clic con la acción "follow") y el server lo ignoraba. Tampoco leía el
**modo perseguir** del ataque: de `0xA0` (modos de pelea) solo tomaba el primer byte.

## Cómo funciona

| Paquete del cliente | Qué hace el server |
|---|---|
| `0xA2` + id (Follow) | Guarda a quién se sigue (`Player::followCreatureId`) y arranca `Game::checkPlayerFollow` |
| `0xA0` modo, **perseguir**, seguro | Guarda el modo perseguir (`setChaseMode`); si ya está atacando, arranca el mismo evento |
| `0xA1` + id (atacar) | Corta el follow (seguir y atacar se excluyen, como en Tibia); con perseguir, el evento va al atacado |
| `0xBE` (Esc / "Stop Follow") | Corta el follow y el ataque |
| Caminar a mano (`0x64`–`0x6D`) | Corta el follow |

`checkPlayerFollow` corre cada **300 ms**:

1. Blanco: el del follow o, con perseguir, el que se está atacando.
2. Si el blanco desapareció, cambió de piso o salió de la pantalla (±8, ±6), el follow se corta y el server manda
   `0xA3` (el cliente saca el cuadrado).
3. Si ya está al lado (8 vecinos), se queda quieto.
4. Si el blanco se movió (o el jugador no está caminando), calcula el camino A* (`Map::getPathTo`, 400 nodos) a
   la casilla **libre más cercana pegada al blanco** (la del blanco la ocupa él y bloquea) y lo camina con la
   caminata automática de siempre (`playerAutoWalk` / `checkPlayerWalk`, a la velocidad del jugador). Si ya
   estaba caminando, solo cambia el rumbo.
5. Sin camino: "There is no way." una vez (no se repite mientras siga sin camino).

Archivos: `source/protocol76.cpp` (`parseFollow`, `parseModes`, `parseCancelMove`, `parseMove*`),
`source/game.cpp` (`playerFollowCreature`, `stopPlayerFollow`, `ensurePlayerFollowEvent`, `checkPlayerFollow`,
`playerSetAttackedCreature`), `source/player.h` (`followCreatureId`, `eventFollow`, `followLastTarget`,
`followNoWayShown`, `setChaseMode`, `isChasing`). Se agregaron miembros a `Player`: **`make clean && make`**.

## "Usar" de lejos (click derecho)

Antes, usar algo del mapa a más de 1 casilla (escalera de mano, puerta, palanca, cofre) daba "Too far away." y el
personaje no se movía. Ahora, como en Tibia, `Game::playerUseItem`:

1. Si la casilla está en el mismo piso, a más de 1 y a la vista (±8, ±6), calcula el camino a la casilla libre más
   cercana pegada al objeto (`Game::pathNextTo`, la misma función del follow) y lo camina.
2. Guarda el pedido (`Player::pendingUse*`). Cuando `checkPlayerWalk` termina el camino, hace el `UseItem` normal
   (sube la escalera, abre la puerta, etc.). Si al llegar sigue lejos (algo le cortó el paso), da "Too far away."
   como siempre.
3. Se cancela al caminar a mano, con Esc y al empezar un follow. Un "usar" nuevo reemplaza al anterior.

Sin camino posible, o en otro piso, queda como antes ("Too far away."). Solo el "usar" simple (`0x82`): "usar con"
(cuerda, pala, runas sobre el mapa) sigue pidiendo estar al lado.

```bash
python3 scripts/ot/test-use-far.py --port 7275     # escalera de mano de la cueva en cruz (56,165,9)
```

## Límites

- El A* solo da pasos en cruz (como el resto del server): el camino no va en diagonal.
- Si el cliente no estaba atacando, `0xA3` no le saca el cuadrado verde del follow (OTClient solo cancela con
  `0xA3` cuando ataca); se limpia con Esc o al elegir otro blanco.

## Probar

```bash
# server de PRUEBA con bots (make-test-bots.py ... 161 50 7), nunca en el que se juega
python3 scripts/ot/test-follow.py --port 7275 --start 161 50 7
```

Revisa: seguir a un jugador que se mueve (dos veces), que Esc lo corte, y el modo perseguir contra un Spit Nettle
en el claro de la Wave Arena (con perseguir llega al cuerpo a cuerpo; con "quieto" no se mueve).
