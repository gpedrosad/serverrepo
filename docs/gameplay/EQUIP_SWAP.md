# Cambiar equipo arrastrando desde la mochila

Desde nov 2026, arrastrar un ítem de la mochila (o de cualquier contenedor) **sobre un slot ocupado** los
**intercambia**: el ítem nuevo queda puesto y el que estaba puesto vuelve a la mochila. Antes decía "Sorry, not
enough room." y había que sacar primero lo que estaba puesto.

- Lo hace `Game::thingMoveInternal` (contenedor → inventario), que ya devolvía `toItem` al contenedor; lo que se
  cambió es la validación `Game::onPrepareMoveThing(Player*, const Container*, const Item*, slots_t, ...)`.
- Siguen valiendo las reglas del slot (`onPrepareMoveThing(player, item, slot)`): si el arma nueva es de dos manos
  y tenés escudo, "First remove the two-handed item.".
- **No se intercambia** si lo que está puesto es la propia mochila de donde sale el ítem (o la contiene): no se
  puede meter una mochila dentro de sí misma.
- **Parte de un stack** (ej. 5 de 10 flechas sobre otras municiones): el resto se queda en la mochila y lo puesto
  necesita un lugar más; con la mochila llena no se hace (si no, `Container::addItem` no lo agrega y se perdería).
- Mover de slot a slot no cambió.

## GM: usa todos los ítems (nov 2026)

Además de wands, rods y hechizos ([SPELL_RUNTIME.md](SPELL_RUNTIME.md)), un GM (`access >= accessprotect`) usa:

| Qué | Dónde |
|-----|-------|
| Throwing stars de paladín | `Game::creatureMakeDamage` y `Player::getPaladinStarId` |
| Bonos de mago de starbinder hood, fury cape y kilnfire leggings | `isMageVoc` en `player.cpp` |
| Strong mana potion (sin vocación ni nivel 50) | `data/actions/scripts/fluids.lua` (`getPlayerAccess(cid) >= 2`) |
| Destroy field (sin nivel mágico 3) | `data/actions/scripts/destroyfield.lua` |

Las runas ya no le pedían nivel mágico al GM (`game.cpp`).
