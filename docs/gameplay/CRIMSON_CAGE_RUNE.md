# Crimson Cage Rune (20273)

Runa que se tira sobre una criatura y la **encierra en un cuadrado de paredes rojas** (las 8 casillas de
alrededor) durante **3 segundos**. Las paredes son magic walls recoloreadas: bloquean el paso y los
proyectiles, igual que la Magic Wall.

![Magic wall original, pared roja (3 cuadros) y la runa](img/crimson-cage.png)

## Datos

| Qué | Valor |
|-----|-------|
| Runa | server `20273` "crimson cage rune", client `2892` (era un broken bottle, server 2022) |
| Pared | server `20274` "crimson wall", client `2878` (era un broken bottle, server 2010); 2x2, 3 cuadros, luz roja (3, 180) |
| Conjuro | `adevo grav res`: ML 16, 350 de maná, sorcerer / druid / paladin (y sus promociones); da 2 cargas |
| Usar la runa | ML 10, 2 cargas, peso 2.1 |
| Duración | 3000 ms exactos por pared |
| GM | `/i crimson cage rune` |

## Comportamiento

- Hay que apuntar a una criatura (jugador o monstruo), en el mismo piso y con línea de tiro. No sirve sobre
  uno mismo ni sobre un GM; sobre un tile vacío avisa `You can only use this rune on creatures.` y no gasta carga.
- Pone una pared en cada casilla de alrededor del blanco que esté libre. **Se salta** las casillas:
  - con una criatura (no la empuja);
  - que ya bloquean: paredes del mapa, otra magic wall, muebles;
  - de PZ y de casas (en una casa la pared se podría guardar con los ítems de la casa).
- Un field de fuego, energía o veneno en esa casilla se reemplaza por la pared.
- Si no entra ninguna pared: `There is no room for a cage there.`, puff, no gasta carga.
- Efectos: proyectil de fuego del que la tira al blanco, sonido rojo sobre el blanco, `NM_ME_MAGIC_BLOOD` en
  cada pared. El blanco (si es jugador) lee `You are trapped in a crimson cage.`
- PvP: mismas reglas que Anchor. No se usa desde PZ ni sobre alguien en PZ; contra un jugador deja al que la
  tira con PZ lock y a los dos en combate. Exhaust ofensivo (2 s).

## Por qué no usa el decay normal

La Magic Wall se va por `Game::startDecay`, que avanza de a `DECAY_INTERVAL` (5 s, ver
[MAGIC_WALL.md](MAGIC_WALL.md)): 3 s se redondearía a 5. Por eso cada pared tiene su propio evento del
scheduler (`makeTask(3000, …)`) que la saca.

El evento guarda su propia referencia a la pared (`useThing`); si al cumplirse los 3 s la pared ya no está
(`isRemoved`), solo suelta esa referencia. Así no queda un puntero colgado ni se borra una pared nueva puesta
después en la misma casilla.

## Archivos

| Archivo | Qué |
|---------|-----|
| `server/YurOTS/ots/source/spells.cpp` | `luaActionDoCrimsonCage`, `placeCrimsonCageWall`, `removeCrimsonCageWall` |
| `server/YurOTS/ots/source/spells.h` | declaración |
| `server/YurOTS/ots/source/const76.h` | `ITEM_CRIMSON_CAGE_RUNE`, `ITEM_CRIMSON_CAGE_WALL` |
| `server/YurOTS/ots/data/spells/runes/crimson cage.lua` | `doCrimsonCage(cid, pos)` |
| `server/YurOTS/ots/data/spells/instant/adevo grav res.lua` | conjuro (`makeRune(cid, 20273, 2)`) |
| `server/YurOTS/ots/data/spells/spells.xml` | `<rune name="Crimson Cage" id="20273">` y el conjuro |
| `server/YurOTS/ots/data/items/items-zagan-test.xml` | peso de la runa |
| `scripts/client-rme/recolor_crimson_cage.py` | sprites: magic wall y su runa pasadas a rojo |
| `scripts/client-rme/add_custom_items.py` | `NEW_ITEMS`: runa y pared (`decor=True`, copias de 2293 y 1498) |

Regenerar los sprites e instalarlos:

```bash
python3.11 scripts/client-rme/recolor_crimson_cage.py --preview /tmp/crimson_cage.png
python3.11 scripts/client-rme/add_custom_items.py --things devtools/rme/rme-client-760
```

## Ajustes fáciles

- Duración: `CRIMSON_CAGE_MS` en `spells.cpp` (rebuild).
- Cargas, ML, maná y vocaciones: `spells.xml` (restart).
- Que la pared se pueda romper con Desintegrate: agregar `ITEM_CRIMSON_CAGE_WALL` al chequeo de
  `luaActionDoDesintegrate` (hoy solo 1497 / 1498).

## Pendiente

- Probarla in-game: encerrar a un jugador y a un monstruo, cronometrar los 3 s, tirarla al lado de una pared del mapa.
- No hay NPC que la venda: se consigue con el conjuro o con `/i`.
