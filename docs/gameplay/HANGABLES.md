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
