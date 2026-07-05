# NPC: Confirmación de compra/venta

Se modificó el sistema de NPCs para que, antes de concretar cualquier transacción de compra o venta, el NPC le pida confirmación al jugador con un mensaje del estilo:

> **NPC**: Do you want to buy 1x rope for 50 gold? (yes/no)
> **Player**: yes
> **NPC**: Here you are.

Si el jugador dice `no`, el NPC responde "Maybe next time." y la transacción se cancela.

## 1. Archivos modificados

### `server/YurOTS/ots/source/npc.h`
Sin cambios en la clase `Npc` (se removió el struct `PendingTransaction` que causaba crash por cambio de layout bajo QEMU i386).

### `server/YurOTS/ots/source/npc.cpp`

**Includes nuevos:**
```cpp
#include "item.h"
#include <cctype>
#include <map>
```

**Estado global de transacciones pendientes:**
```cpp
struct PendingTransaction {
    int cid;
    int itemid;
    int count;
    int cost;
    bool isSell;
    PendingTransaction() : cid(0), itemid(0), count(0), cost(0), isSell(false) {}
};

static std::map<unsigned long, PendingTransaction> pendingTrades;
```

Se usa un `std::map` global indexado por el ID del NPC. Cada NPC puede tener una transacción pendiente a la vez. Se eligió un mapa global en vez de un miembro de la clase `Npc` porque agregar miembros a `Npc` causaba heap corruption (`malloc(): invalid size`) bajo la emulación QEMU i386 de Docker en Apple Silicon.

**`Npc::onCreatureSay` (interceptación de "yes"/"no"):**

Antes de pasar el mensaje del jugador al script Lua del NPC, se chequea si hay una transacción pendiente para este NPC y este jugador. Si la hay:

- `"yes"` / `"si"` / `"y"` → ejecuta la transacción (compra o venta según `isSell`), la elimina del mapa, y retorna sin pasar el mensaje al script Lua.
- `"no"` / `"n"` → cancela la transacción, dice "Maybe next time.", y retorna.
- Cualquier otra cosa → pasa el mensaje al script Lua normalmente (el NPC responde como siempre).

**`luaBuyItem` y `luaSellItem` (cambio de ejecución inmediata a diferida):**

Antes: `buy(cid, itemid, count, cost)` cobraba, daba el item, y decía "Here you are." inmediatamente.

Ahora: `buy(cid, itemid, count, cost)` guarda la transacción en `pendingTrades[npcID]` y el NPC dice `"Do you want to buy Nx ITEM for Y gold? (yes/no)"`. La transacción se ejecuta solo cuando el jugador responde `"yes"`.

Lo mismo aplica para `sell()` → `"Do you want to sell Nx ITEM for Y gold? (yes/no)"`.

El nombre del item se obtiene de `Item::items[itemid].name` (definido en `items.h`/`items.otb`).

## 2. Flujo de una transacción

```
Player: "hi"
NPC:    "Hello! I sell ropes (50gp), shovels (20gp)..."
Player: "rope"
        └─ luaBuyItem(cid, 2120, 1, 50)
           └─ pendingTrades[npcID] = {cid, 2120, 1, 50, isSell=false}
NPC:    "Do you want to buy 1x rope for 50 gold? (yes/no)"
Player: "yes"
        └─ onCreatureSay intercepta "yes"
           └─ player->getCoins(50) → OK
              player->removeCoins(50) → OK
              player->TLMaddItem(2120, 1)
NPC:    "Here you are."
```

## 3. Compatibilidad

- **No requiere modificar ningún script Lua de NPC.** Todos los NPCs existentes (`seller.lua`, `loot.lua`, `runes.lua`, etc.) siguen usando `buy()` y `sell()` igual que antes. El cambio es transparente: ahora `buy()`/`sell()` no ejecutan directo sino que guardan la transacción y preguntan.
- Los scripts Lua que llaman `buy()` o `sell()` múltiples veces en una sola respuesta del NPC (ej: vender 2 items distintos) solo la última transacción queda pendiente (se sobreescribe). Esto es aceptable porque el NPC solo puede tener una transacción pendiente a la vez.
- Los NPCs que no usan `buy()`/`sell()` (ej: boat, oracle, guild) no se ven afectados.
- Se acepta `"yes"`, `"si"`, `"y"` como confirmación y `"no"`, `"n"` como cancelación.

## 4. Por qué no se usó un miembro en la clase Npc

La primera implementación agregó un `struct PendingTransaction` como miembro de `Npc` en `npc.h`. Esto cambiaba el `sizeof(Npc)` y causaba `malloc(): invalid size (unsorted)` (heap corruption) durante `loadNpcs()` bajo QEMU i386 emulado en Apple Silicon. El crash ocurría al crear NPCs con `new Npc(...)`.

La causa raíz probable es que el código legacy asume tamaños fijos de objetos en algún path (posiblemente herencia de `Creature` o el allocator custom `allocator.h`). Usar un `std::map` global evita tocar el layout de `Npc` y es igual de funcional.

## 5. Testing

Loguear con account `111111` / pass `tibia`, ir a un NPC vendedor (ej: Seller en templo), decir `hi`, pedir un item (ej: `rope`), y el NPC preguntará `"Do you want to buy 1x rope for 50 gold? (yes/no)"`. Responder `yes` para concretar o `no` para cancelar.
