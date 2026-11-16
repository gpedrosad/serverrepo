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

## Frozen Isle: llegada corregida y desplegada (13 nov 2026)

La bajada `412,53,8` lleva a **`412,54,9`**, al sur de la subida 1385. Allí había pared 357.
Se extendió el piso en un bloque de 2×2 y se recompusieron las paredes; el generador ahora inicia
el BFS desde `y+1` y rechaza una llegada bloqueada. Los cuatro destinos de ambas escaleras están
libres según mapa/OTB, y el `onUse` real confirma las dos bajadas en LuaJIT con bindings sustituidos.
Las regresiones están en `scripts/map/test-frozen-isle.py`. El 13 nov se probaron ambas escaleras
caminando en ambos sentidos y usando la bajada a z9 con un cliente de protocolo conectado a una
copia aislada del servidor en la ThinkPad (7173), cargando el mapa nuevo. Todas las llegadas correctas. Desplegado en la ThinkPad (`a526166`), con probe posterior OK.
Ver [revisión y corrección](../items-and-map/REVISION_ESTETICA_HIELO_2026_11_13.md).

## Valle de las Bestias: bajadas sobre roca (15 nov 2026)

Las bajadas `432` de las tres cuevas (z8 → z9) y la del Nido del Dragón (z9 → z10) caían sobre roca: el
generador cavaba cada piso de abajo desde una boca fija, lejos de la bajada. Ahora la cueva de abajo se
cava desde debajo de la bajada, con la `1385` en la misma x, y, y el generador valida cada par.
Probado con un bot GM en una copia aislada (puerto 7275): baja y sube por las 5 escaleras. Detalle en
[MAPEAR_VALLE_DE_LAS_BESTIAS.md](../items-and-map/MAPEAR_VALLE_DE_LAS_BESTIAS.md#escaleras-entre-pisos).

## Pendiente (mapa)

- Escalera de mano que baja en `194, 150, 8`: abajo (`194, 150, 9`) es roca. Usarla o pisarla te
  deja dentro de la roca. Hay que arreglarla en el mapa (sacarla o hacer la cueva de abajo).

## Elvenbane: escalera de mano en todas partes

Pedido de Gonzalo (15-11-2026): *«esa escalera del principio es la que debe estar en todas partes»*.
En Elvenbane las 19 conexiones entre pisos usan **escalera de mano**, no `1385` (piedra clara),
`1396`/`432` (madera) ni `3685`/`3687` (rampas).

| Par | Dónde | Al usarla / al bajar |
|-----|-------|----------------------|
| `469` arriba + `1386` abajo | Solo la **entrada** (`39,340`, z7↔z8), buraco rodeado de 4 piedras `1285` (O, E, NO, NE), sur libre | `1386` sube a `(x, y+1, z-1)`; bajar por `469` cae en `(x, y, z+1)` (offset 0) |
| `409` arriba + `1386` abajo | Las **otras 18** (túnel, sótanos, patio, adarve, torretas y torre). Sin piedras | Igual: `1386` → `(x, y+1, z-1)`; `409` → misma casilla abajo |

`409` y `469` ya están en `actions.xml` → `teleport.lua`. `1386` está en `LADDERS_UP`.
Detalle, coordenadas de cada link y cómo regenerar: [`ELVENBANE.md`](../items-and-map/ELVENBANE.md).
