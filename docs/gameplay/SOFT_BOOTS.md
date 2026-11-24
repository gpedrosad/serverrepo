# Soft Boots — regen, desgaste y recarga

Documentación del comportamiento **actual** en YurOTS / Retro76.

> **TL;DR:** Soft Boots (`2640`, clientId `3549`) equipadas en pies regeneran **+3 HP** y **+12 MP** cada **3 s**, duran **4 h** de uso, y al agotarse pasan a Worn Soft Boots (`2641`, clientId `3550`). Puestas **brillan** como los anillos: pasan a `20670` (clientId `6070`, con destellos). Se recargan a 4 h usando una **Azure Sunstone** (`20124`).

---

## Resumen

| Campo | Valor |
|-------|--------|
| Soft Boots | `2640` (`ITEM_SOFT_BOOTS`, clientId `3549`) |
| Worn Soft Boots | `2641` (`ITEM_WORN_SOFT_BOOTS`, clientId `3550`) |
| Puestas (brillan) | `20670` (`ITEM_SOFT_BOOTS_IN_USE`, clientId `6070`): mismo ítem, otro dibujo |
| Slot | `SLOT_FEET` (pies) |
| Peso | `8.0` oz (`items.xml`) |
| Duración | `14400000` ms = **4 horas** (`time` en `items.xml`) |
| Regen | cada `3000` ms: **+3 HP**, **+12 MP** (~60 HP/min, ~240 MP/min) |
| Penalidad al equipar | `3000` ms de duración consumidos al ponerlas |
| Al agotarse | `setID(2641)` + `clearDuration()` + refresh inventory |
| Recarga | **Azure Sunstone (`20124`)** — `soft_boots_recharge.lua` (`2641` → `2640`, restaura 4 h completas incluso puestas) |
| Imbue Yellow Gem | **No** (no están en tabla `BOOTS` de `gem_imbue.lua`) |

---

## Qué hacen (gameplay)

1. El jugador equipa Soft Boots (`2640`) en el slot de pies (`SLOT_FEET`).
2. Al equipar: si el item no tiene tiempo (`getTime() <= 0`), se restaura la duración completa (`newTime` = 4 h); luego se aplica la penalidad de equip (`SOFT_BOOTS_EQUIP_PENALTY_MS` = 1 tick = 3 s).
3. Mientras estén equipadas, cada tick del game loop llama `Player::checkSoftBoots()`:
   - consume duración (`useTime(thinkTicks)`);
   - cada 3 s suma mana/HP (sin pasar del max); si el think se atrasa, el `while` aplica catch-up;
   - si la duración llega a 0 → transforman a worn (`2641`).
4. Al desequipar pies: se resetea el acumulador interno `softBootsTick` (no se pierde el `time` restante del item).
5. El `time` se persiste en el XML del player y se muestra al mirarlas (`item.cpp`: *"It is brand new"* / *"It has N minutes left"* + descripción de regen).
6. Para recargar `2641` → `2640`: usar una **Azure Sunstone (`20124`)** sobre las botas gastadas (con *Use With*, incluso si están puestas, o click derecho teniéndolas en la mochila). `luaActionDoTransformItem` restaura automáticamente `newTime` (4 h) al transformar a `ITEM_SOFT_BOOTS`.

## Brillo puestas

Desde el 24 nov 2026 las Soft Boots brillan mientras están en los pies, igual que los anillos "in use".

- **Cómo funciona:** al ponerlas, el servidor las cambia por `20670`; al sacarlas vuelven a `2640`
  (`Item::setGlimmer` / `removeGlimmer`, los mismos que usan los anillos). El cambio se hace **antes** de
  avisarle al cliente (`sendThingMove`), así le llega el ítem ya brillando o ya apagado.
- **Dónde se aplica:** en los 5 movimientos del inventario (`Player::onThingMove`) y al entrar al juego
  (`addItemInventory`). También en `checkSoftBoots`: si en los pies hay unas `2640`, que es como vuelven
  al recargarlas puestas con la Azure Sunstone, las pasa a `20670`.
- **Qué es igual:** `20670` es el mismo ítem para todo:
  - en el OTB es copia del nodo de `2640`;
  - en `items.xml` tiene el mismo `time` y el mismo peso;
  - regenera, se gasta y muestra el mismo texto al mirarla.
  - Al gastarse pasa a `2641`, que ya no brilla.
- **Sprite:** `scripts/client-rme/make_soft_boots_glow.py`. Son las botas (`3549`) con los destellos
  dorados del time ring in use (`3090`), en el mismo formato: 2 capas × 4 cuadros. La apariencia del
  cliente (flags `0x10`) es la del ring in use (`appearance=2206` en `add_custom_items.py`).
- **Cliente:** el ícono "Soft Boots active" del panel de condiciones (`game_inventory/inventory.lua`, en
  Mac y Windows) acepta `3549` y `6070`. Antes miraba solo `3549`, y con las botas brillando se habría
  apagado.
- **Prueba:** `scripts/ot/test-soft-boots-glow.py`, en un server aparte (7275) con los bots. Revisa que:
  - brillen al entrar y al ponerlas;
  - no brillen en la mochila;
  - al mirarlas digan su regeneración;
  - pasen a worn al gastarse;
  - vuelvan a brillar al recargarlas puestas.

  La mochila de los bots tiene otra mochila en el lugar 0: hay que soltar en un lugar vacío, si no las
  mete adentro.

---

## Constantes C++ (`server/YurOTS/ots/source/const76.h`)

```cpp
ITEM_SOFT_BOOTS             = 2640, // clientId 3549
ITEM_WORN_SOFT_BOOTS        = 2641, // clientId 3550

#define SOFT_BOOTS_INTERVAL_MS      3000
#define SOFT_BOOTS_MANA_GAIN        12
#define SOFT_BOOTS_HP_GAIN          3
#define SOFT_BOOTS_DURATION_MS      (240 * 60 * 1000)  // 4 h (duración real en items.xml)
#define SOFT_BOOTS_EQUIP_PENALTY_MS 3000               // 1 tick de regen
```

---

## Archivos clave

| Archivo | Rol |
|---------|-----|
| `source/const76.h` | IDs (`2640`/`2641`/`20670`) y macros de balance |
| `source/player.h` / `player.cpp` | `onSoftBootsEquipped`, `checkSoftBoots`, hooks en `onThingMove` y brillo (`setGlimmer`) |
| `source/item.cpp` | `setGlimmer` / `removeGlimmer` (`2640` ↔ `20670`) |
| `source/actions.cpp` | `luaActionDoTransformItem`: restaura `newTime` al transformar a `ITEM_SOFT_BOOTS` |
| `source/item.cpp` | Descripción al look (regen / recarga con Azure Sunstone) y persistencia de `time` |
| `source/game.cpp` | Llama `checkSoftBoots(thinkTicks)` en el think del player |
| `data/items/items.xml` y `items-zagan-test.xml` | `time="14400000"` y `weight="8.0"` en `2640`/`2641` |
| `data/actions/scripts/soft_boots_recharge.lua` | Recarga con Azure Sunstone (`20124`: `2641` → `2640`) |
| `data/monster/deathslicer.xml` | Drop de worn `2641` (`chance="2000"`) |
| `OTINFO`, `OTINFO.en`, `web/site/src/wiki/soft-boots.md` | Info pública y wiki |

---

## Errores que ya pasaron (nov 2026)

- **Confusión `clientId` vs `serverId`:** originalmente `const76.h`, `items.xml`, `items-zagan-test.xml`, `soft_boots_recharge.lua` y `deathslicer.xml` usaban **`3549`/`3550`** (que son los **client IDs** de las botas, pero en server ID son `closed door` / `open door`). Como resultado, las Soft Boots reales (`2640`) no regeneraban, no tenían duración ni desgaste, y la Azure Sunstone no podía recargar las `2641`. Corregido en nov 2026: todo apunta a `2640`/`2641`, y `3549`/`3550` quedan limpiamente como puertas.
- **`doTransformItem` sin restaurar duración:** al recargar `2641` → `2640` con *Use With* sobre unas botas equipadas, `setID` dejaba `time = 0` y el siguiente tick las volvía a gastar al instante. Corregido restaurando `newTime` dentro de `luaActionDoTransformItem`.

---

## Referencias

- Feature catalog: [`docs/features/12-soft-boots.md`](../features/12-soft-boots.md)
- Azure Sunstone y bosses que la dropean: [`docs/gameplay/CAMBIOS_SI_A_TODO.md`](CAMBIOS_SI_A_TODO.md)
- Gemas / botas imbuibles: [`docs/gameplay/GEMS.md`](GEMS.md)
