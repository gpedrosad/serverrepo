# Tapestries y otras cosas que se cuelgan en las paredes

Desde nov 2026 los ítems **hangable** se pueden colgar en las paredes, como en Tibia: se tiran sobre una pared con
gancho y el cliente los dibuja colgados. Antes el server no leía los flags `hangable` / `vertical` / `horizontal`
del `.otb` y la pared bloqueaba todo ("There is not enough room").

## Qué se cuelga y dónde

| Ítem (levantable, `hangable`) | id |
|------|----|
| purple / green / yellow / orange / red / blue / white tapestry | 1857 / 1860 / 1863 / 1866 / 1869 / 1872 / 1880 |
| cuckoo clock | 1881 |

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
