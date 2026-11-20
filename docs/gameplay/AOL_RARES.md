# AOL y armas rare: no se llevan juntos

Desde nov 2026 un jugador **no puede tener un Amulet of Loss (2173) y un arma rare a la vez**, en ningún lado de su
inventario: ni puesto, ni en la mochila, ni en bolsas dentro de ella. Si tiene un arma rare, tiene que arriesgarla.

## Armas rare

`Player::isAolRestrictedRare` (`player.cpp`):

| Grupo | Ítems |
|-------|-------|
| El Crisol | venomqueen fang 20100, stormcaller maul 20110, ashlord emberblade 20112, ironhide crusher 20121, bloodreaver saber 20122, frostwarden chillblade 20138, bonepriest reaver 20154 |
| Armas de 8.x | emerald sword 20157, avenger 20158, arcane staff 20159, arbalest 20160 |
| Root Colossus | rootcleaver 20163, heartwood maul 20164 |
| Rares Zagan | medusa sword 20105, sword of silence 20139, windsting axe 20130, nightglass dagger 20137 |
| Otras | black fire sword 20193, crimson wand 20123 |

Para sumar otra: agregar su id al `switch`.

## Dónde se controla

- **Al mover algo a tu inventario desde afuera** (del suelo, de un cuerpo, del depot o de un contenedor ajeno, a un
  slot o a una mochila propia): si con eso quedarías con AOL y rare juntos, no se mueve y avisa
  ("No puedes llevar un Amulet of Loss si tienes un arma rare." / "No puedes llevar un arma rare si tienes un Amulet
  of Loss."). Se revisa también lo que viene dentro de una mochila o bolsa (`Player::aolRareConflict`, llamado desde
  los `Game::onPrepareMoveThing` de suelo→inventario, →mochila y contenedor→slot). Mover cosas dentro del propio
  inventario no se controla (no cambia lo que tenés).
- **Comprar el AOL** en la NPC (`aol.lua`): al confirmar, si llevás un rare, no te lo vende (`npc.cpp`).
- **Red de seguridad al morir** (`Player::dropLoot`): si de todos modos tenés AOL y rare juntos (llegó por trade, un
  cofre de quest u otro camino sin control), **el AOL no protege**: se muere como sin AOL (porcentajes normales de
  pérdida).
