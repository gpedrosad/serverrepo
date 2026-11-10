# Escaleras, escaleras de mano, trampillas y agujeros (click derecho)

Script: `data/actions/scripts/teleport.lua`, registrado en `data/actions/actions.xml` para cada
ítem que se puede "usar" para cambiar de piso.

| Ítem | Qué es | Al usarlo |
|---|---|---|
| `1386`, `3678` | Escalera de mano (sube) | Piso de arriba, una casilla al sur (`x, y+1, z-1`) |
| `408`, `410`, `427`, `429` | Trampilla | Piso de abajo |
| `409`, `428` | Escalera de mano (baja) | Piso de abajo |
| `411`, `423`, `432` | Escalera (baja) | Piso de abajo |
| `294`, `383`, `385`, `392`, `469`, `470`, `479`, `480`, `482`, `484`, `485`, `489` | Agujeros | Piso de abajo |
| `430` | Rejilla de cloaca | Piso de abajo |

**Al bajar se aterriza igual que bajando caminando** (`Game::thingMove`, `game.cpp`): si en la
casilla de abajo hay una escalera de subida, el jugador queda al costado de ella según hacia dónde
sube. La tabla `STAIRS_LANDING` del script tiene esas escaleras (flags `floorchange_*` de
`items.otb`):

| Escalera de abajo sube hacia | Ítems | Se aterriza |
|---|---|---|
| norte | 1385, 1394, 1396, 1404, 3685, 3687 | una al sur |
| sur | 1392, 1402, 3683 | una al norte |
| este | 1388, 1398, 3679 | una al oeste |
| oeste | 1390, 1400, 3681, 3688 | una al este |
| diagonales | 1553, 1555, 1557, 1559 | en diagonal, al lado opuesto |

Si se agregan escaleras nuevas al `items.otb` (cliente propio), sumarlas a `STAIRS_LANDING`.

## Bugs arreglados (nov 2026)

- **"Quedas en medio de la escalera":** el script mandaba a `x, y, z+1`, justo encima de la
  escalera de subida del piso de abajo. Pasaba en 30 escaleras/trampillas, entre ellas el **puente
  principal** (`141-142, 59` y `141-142, 74`, piso 6 → aterriza en `y 60` / `y 75`, piso 7).
- **Agua que te tiraba un piso abajo:** el agua de las cuevas (`493`, pisos 8-10, más de 3.000
  casillas) estaba registrada en `teleport.lua`. Click derecho sobre ella te llevaba al piso de
  abajo, casi siempre dentro de roca (`Game::teleport` no revisa si la casilla está bloqueada).
  Se sacó del `actions.xml`.

Comprobado simulando cada uso sobre el mapa (`test.otbm`): las 205 escaleras/agujeros dejan en
una casilla que existe, no está bloqueada y no es otra escalera.

## Pendiente (mapa)

- Escalera de mano que baja en `194, 150, 8`: abajo (`194, 150, 9`) es roca. Usarla o pisarla te
  deja dentro de la roca. Hay que arreglarla en el mapa (sacarla o hacer la cueva de abajo).
