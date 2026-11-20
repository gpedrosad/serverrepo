# Tapestries y otras cosas que se cuelgan en las paredes

Desde nov 2026 los ítems **hangable** se pueden colgar en las paredes, como en Tibia: se tiran sobre una pared con
gancho y el cliente los dibuja colgados. Antes el server no leía los flags `hangable` / `vertical` / `horizontal`
del `.otb` y la pared bloqueaba todo ("There is not enough room").

## Qué se cuelga y dónde

| Ítem (levantable, `hangable`) | id |
|------|----|
| purple / green / yellow / orange / red / blue / white tapestry | 1857 / 1860 / 1863 / 1866 / 1869 / 1872 / 1880 |
| cuckoo clock | 1881 |
| **brazil / chile / usa / argentina tapestry** (nov 2026) | 20275 / 20276 / 20277 / 20278 |
| **pirate banner / war banner / royal banner** (nov 2026) | 20279 / 20280 / 20281 |

### Banderas y estandartes (nov 2026)

Copias del purple tapestry (1857, mismos flags: `hangable`, levantable) con dibujo propio en sus 3 patrones
(enrollado, pared horizontal, pared vertical). Los dibuja `scripts/client-rme/make_flag_tapestries.py`: para cada
píxel de tela calcula `(u, v)` dentro de la bandera siguiendo la inclinación de cada patrón (en la pared horizontal
cada fila se corre a la derecha; en la vertical, cada columna hacia abajo) y le aplica la sombra del original; la
vara pasa a madera. Para agregar otro diseño: una función `design(u, v) -> (r, g, b)` en `DESIGNS`, una entrada en
`NEW_ITEMS` de `add_custom_items.py` (`prototype=1857, tiles=2, frames=3, decor=True`) con un client id de
`--candidates`, y la venta en Obi.

| Ítem | Server / client id (sacrificado) | Dibujo |
|------|------|--------|
| brazil tapestry | 20275 / 3123 (broken boots) | verde, rombo amarillo, círculo azul |
| chile tapestry | 20276 / 3118 (broken green glas) | blanco y rojo, cuadro azul con estrella |
| usa tapestry | 20277 / 3117 (broken brown glas) | franjas rojas y blancas, cantón azul con estrellas |
| argentina tapestry | 20278 / 3112 (rotten meat) | celeste, blanco y celeste, sol |
| pirate banner | 20279 / 3111 (fishbone) | negro con calavera y huesos |
| war banner | 20280 / 3106 (old twig) | rojo sangre, espadas cruzadas, borde dorado |
| royal banner | 20281 / 3103 (horn 3957) | violeta, corona dorada con joya, borde dorado |

**Exhibición en el local de Obi (173,46,7):** versiones **fijas** de las 7 (server **20320–20326**, mismo client id
y dibujo; `fixed=True` en `add_custom_items.py` les saca `moveable`/`pickupable` del OTB, así que no hace falta
publicar el cliente). Colgadas por `scripts/map/obi-banners.py` (re-ejecutable, agrega el ítem al nodo de la casilla
sin tocar el resto): Brasil, Chile y USA en la pared norte por dentro (173/174/177,43; en 176,43 hay una antorcha),
Argentina en la pared oeste (172,44) y los 3 estandartes en la pared sur mirando a la calle (173/174/176,49). Hacen
falta fijas porque esas paredes están al alcance desde la calle: una bandera común se la llevaría cualquiera.
Ojo: **20282–20296 son las piezas del muelle** (`dock_bridge_art.py`, no están en `NEW_ITEMS`): mirar el OTB antes
de elegir server ids nuevos.

Los vende **Obi** (muebles) a **1500 gp** ("flags", "banners", "banderas"; "brazil tapestry", "bandera de chile"...);
el resto de sus muebles sigue a 500. Para verlos hay que publicar el cliente (`publish_client.py`): un cliente sin
actualizar los muestra como el ítem sacrificado. `sprite_tool.py verify` marca "ítems idénticos" en FALLA: es
esperado (solo cambiaron esos 7 client ids).

- **Pared con gancho:** flag `horizontal` del `.otb` (`hookSouth`: lo colgado mira al sur) o `vertical` (`hookEast`:
  mira al este). Por ejemplo `stone wall` 1050 (horizontal) y 1049 (vertical), `brick wall` 1026. Las esquinas y los
  postes no tienen gancho.
- El sprite del tapestry trae 3 variantes (enrollado, en pared horizontal, en pared vertical); el **cliente** elige
  según el gancho de la pared. El server no transforma el ítem: sigue siendo el mismo y se puede volver a levantar.
- **Una cosa colgada por pared.**
- Las versiones fijas del mapa (1855/1856, 1858/1859...) son decoración `unmoveable` y no cambian.

### Trofeos de jefes (nov 2026)

Tapestries con el jefe de frente (cuadro quieto mirando al sur de su looktype, recortado y centrado) sobre terciopelo
de un color que contraste, con borde dorado. Mismo generador que las banderas (`TROPHIES` en
`make_flag_tapestries.py`) y mismos flags (colgable, levantable). **Rare del 5 %** de su jefe (`<item id="..."
chance="5000"/>` al principio del `<loot>`). Los de **monstruos de caza** (Black Dragon, Dark Hydra...) van al **0,5 %**,
también en sus variantes rage; si se regeneran con `rage-variants.py`, la línea del base se copia sola. No se resaltan como rare en el mensaje de loot (eso es C++:
`isRareLootItem` en `game.cpp`).

| Trofeo | Server / client id (sacrificado) | Lo suelta |
|--------|------|-----------|
| demodras trophy | 20330 / 3021 (starlight) | Demodras |
| orshabaal trophy | 20331 / 3014 (star amulet) | Orshabaal |
| old widow trophy | 20332 / 1780 (stone) | Old Widow |
| ashen lord trophy | 20333 / 2872 (backpack) | Ashen Lord |
| fallen emperor trophy | 20334 / 2832 (book) | The Fallen Emperor |
| elvenbane trophy | 20335 / 2831 (book) | Lord of Elvenbane |
| black dragon trophy | 20341 / 2965 | Black Dragon y sus variantes Angry/Furious/Enraged (0,5 %) |
| dark hydra trophy | 20342 / 2951 | Dark Hydra y sus variantes Angry/Furious/Enraged (0,5 %) |
| root colossus trophy | 20343 / 2906 | Root Colossus y sus variantes Angry/Furious/Enraged (0,5 %) |
| emerald scarab trophy | 20344 / 2852 | Emerald Scarab y sus variantes Angry/Furious/Enraged (0,5 %) |
| frost dragon trophy | 20345 / 2851 | Frost Dragon y sus variantes Angry/Furious/Enraged (0,5 %) |
| hellhound trophy | 20346 / 3020 | Hellhound y sus variantes Angry/Furious/Enraged (0,5 %) |
| imperial hero trophy | 20347 / 3002 | Imperial Hero y sus variantes Angry/Furious/Enraged (0,5 %) |
| red kongra trophy | 20348 / 2984 | Red Kongra (0,5 %) |
| elvenbane ranger trophy | 20349 / 2971 | Elvenbane Ranger (5 %) |
| elven archmage trophy | 20350 / 2970 | Elven Archmage (5 %) |
| orc warchief trophy | 20351 / 3077 | Orc Warchief (5 %) |
| thornwarden trophy | 20352 / 3011 | Thornwarden (5 %) |

**Client ids sacrificables casi agotados:** después de estos trofeos quedan ~5 en `--candidates`. Para más ítems
nuevos habría que agregar client ids al final del `.dat` (OTClientV8 lo soporta) en vez de reciclar ítems viejos.

## Luces de colores (nov 2026)

No se cuelgan: se apoyan en el suelo o en una mesa. Copias del candelabro (2042) y la lámpara (2045) **encendidos**,
con la llama recoloreada por `scripts/client-rme/make_color_lights.py` (candelabro: solo la llama animada; lámpara:
todo el vidrio, como un farol), luz nivel 6 del color de la llama y **sin pudrición** (`nodecay=True` en
`add_custom_items.py` saca los attrs de decay: las bases se apagan solas a los 180 s, estas nunca). Los vende Obi a
**2500 gp** ("lights", "luces").

| Luz | Server / client id (sacrificado) | Color de luz (r·36+g·6+b) |
|-----|------|------|
| blue candelabrum | 20336 / 2825 (book) | 17 (azul) |
| green candelabrum | 20337 / 2821 (book) | 31 (verde) |
| violet candelabrum | 20338 / 2818 (document) | 113 (violeta) |
| magenta lamp | 20339 / 2814 (parchment) | 184 (magenta) |
| cyan lamp | 20340 / 2966 (drum) | 29 (celeste) |

## Casas

- Al cargar las casas (`Houses::Load`), cada casa toma como propias sus **paredes con gancho hacia adentro**: la de
  arriba de una casilla de la casa si tiene gancho al sur, y la de la izquierda si tiene gancho al este
  (`House::wallTiles`). Así lo colgado **se guarda en `houseitems.xml`** y sobrevive a los reinicios.
- Esas paredes **no cuentan para el precio** de `!buyhouse` (sale de `tiles`), pero `!leavehouse` sí cuenta lo
  colgado como objeto que hay que sacar antes de dejar la casa.
- Colgar o descolgar en una pared de casa: solo el dueño, subowners, doorowners e invitados, o un GM
  (`canUseHouseWall` en `game.cpp`). Desde afuera de la casa nadie puede sacarlo.
- Fuera de las casas (murallas de la ciudad) cualquiera puede colgar, pero como cualquier ítem tirado en el mapa
  **no se guarda** al reiniciar.

## Código

| Pieza | Dónde |
|-------|-------|
| Flags `hangable`, `hookSouth`, `hookEast` | `items.h`, `items.cpp` (de `FLAG_HANGABLE`, `FLAG_HORIZONTAL`, `FLAG_VERTICAL`) |
| `Tile::hasHook*`, `hasHangable` | `tile.cpp` |
| Se puede mover a la pared | `Item::canMovedTo` (`item.cpp`) y `Game::onPrepareMoveThing` (camino libre con `canThrowObjectTo(..., 0)`) |
| Paredes de la casa | `Houses::Load` y `SaveHouseItems` (`houses.cpp`) |
