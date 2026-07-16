# Seller: fluids, potions y backpacks llenas

Documentación del NPC `seller` (`data/npc/scripts/seller.lua`) para compra de fluids/potions unitarios, **backpacks llenas (BPs)** y venta de vials vacíos.

## Resumen

| Oferta | Cómo pedirla | Precio | Contenido |
|--------|--------------|--------|-----------|
| Mana fluid | `mana fluid`, `3 mana fluid` | 100 gp c/u | vial subtype `7` |
| Life fluid | `life fluid`, `2 life` | 60 gp c/u | vial subtype `10` |
| Strong mana potion (SMP) | `smp`, `strong mana`, `strong mana potion` | 250 gp c/u | vial subtype `14` |
| BP mana fluid | `bp mana`, `bp mana fluid`, `backpack mana fluid` | **2010 gp** | 1× backpack `1988` + 20× mana fluid |
| BP life fluid | `bp life`, `bp life fluid`, `backpack life fluid` | **1210 gp** | 1× backpack + 20× life fluid |
| BP strong mana / SMP | `bp smp`, `bp strong mana`, `backpack strong mana potion` | **5010 gp** | 1× backpack + 20× SMP |
| Empty vial (vende el jugador) | `vial` / `flask` / `frasco` | 10 gp c/u | solo subtype `0` |
| Sell all empty vials | `sell all vials` | 10 gp × N | solo subtype `0` |

Fórmula de precio de BP:

```
cost = (unitPrice × 20) + backpack(10 gp)
```

| BP | Cálculo |
|----|---------|
| Mana fluid | `20 × 100 + 10 = 2010` |
| Life fluid | `20 × 60 + 10 = 1210` |
| Strong mana potion | `20 × 250 + 10 = 5010` |

---

## Lógica de venta de backpacks (BPs)

### Flujo

```
Jugador: "bp smp"
    │
    ▼
sellerMatchFluidBackpack(msg)     -- ANTES del catálogo unitario
    │  prefixes × aliases
    │  ej. "bp " + "smp" → match
    ▼
getPlayerFreeSlots(cid) < 1 ? → "not enough space"
    ▼
buyFluidBackpack(cid, 1988, 2006, fluidSubtype, 20, cost)
    │
    ▼
C++ (npc.cpp): PendingTransaction isFluidBackpackBuy
NPC: "Buy a backpack of <fluid name> for <cost> gp? (yes or si)"
    │
    ▼ yes / si
addFluidBackpackToPlayer → 1 backpack 1988 con 20 vials del subtype
```

Es el mismo binding C++ que usan mana/life: `buyFluidBackpack`. No hace falta tocar C++ para agregar otro fluid BP; solo una fila en `SELLER_FLUID_BACKPACKS`.

### Matching (`sellerMatchFluidBackpack`)

1. Se evalúa **antes** de `SELLER_BUYS`, para que `backpack mana fluid` no compre una backpack vacía (`1988`).
2. Prefijos reconocidos:

```lua
'bp ', 'bp of ', 'bp de ',
'backpack ', 'backpack of ', 'backpack de ',
'mochila ', 'mochila de '
```

3. Cada entrada de `SELLER_FLUID_BACKPACKS` tiene `aliases` + `fluidSubtype` + `cost`.
4. Orden importa: **aliases más específicos primero** (strong mana / smp antes que `mana`), para no ambiguar con mana fluid.

Tabla actual en Lua:

| aliases | subtype | cost |
|---------|---------|------|
| `strong mana potion`, `strong mana`, `smp` | `14` (`FLUID_STRONG_MANA`) | 5010 |
| `mana fluid`, `manafluid`, `mana` | `7` (`FLUID_MANAFLUID`) | 2010 |
| `life fluid`, `lifefluid`, `life` | `10` (`FLUID_LIFEFLUID`) | 1210 |

### Core C++ (referencia)

| Función Lua | Rol |
|-------------|-----|
| `buyFluidBackpack(cid, bpId, fluidItemId, subtype, count, cost)` | Confirma y entrega BP llena |
| `buyFluidQty(cid, itemid, subtype, qty, cost)` | Compra unitaria de fluids |
| `sellFluid(cid, itemid, subtype, count, cost)` | Venta de vials (vacíos = subtype 0) |
| `getPlayerFluidCount(cid, itemid, subtype)` | Cuenta vials exactos |

Implementación: `npc.cpp` → `luaBuyFluidBackpack` / `addFluidBackpackToPlayer`.  
Confirmación: ver `docs/gameplay/NPC_CONFIRMATION.md`.

Nombre del fluid en el prompt: `Item::getFluidTypeName(subtype)` (`"strong mana potion"`, `"manafluid"`, `"lifefluid"`).

### Capacidad

- Pre-check Lua: `getPlayerFreeSlots(cid) < 1` → aborta sin prompt.
- La BP ocupa **1 slot** en el inventario del jugador; los 20 fluids van *dentro* de esa backpack.
- Si al confirmar falla capacidad/espacio, C++ reembolsa el oro.

---

## Compra unitaria

Catálogo `SELLER_BUYS` (vía `npcFindCatalogBuyEntry` + `buyFluidQty` / `buy`):

- SMP: keys `strong mana potion`, `strong mana`, `smp` → subtype `14`, 250 gp
- Mana fluid / life fluid / supplies / armas / gear de knight

Fallbacks sueltos al final de `onCreatureSay`:

- mensaje con `life` → life fluid
- mensaje con `mana` → mana fluid (SMP ya se resolvió arriba por catálogo/BP)

---

## Venta de vials vacíos

- `vial` / `flask` / `frasco` → 1 empty vial (subtype `0`) a 10 gp
- `sell all vials` / `sell all flasks` / `sell all frascos` → todos los empty vials

Usa `getExactItemCount` / `removeExactItems` para no vender mana/life/SMP por error.

---

## Archivos

| Archivo | Rol |
|---------|-----|
| `server/YurOTS/ots/data/npc/scripts/seller.lua` | Catálogo, match de BPs, help |
| `server/YurOTS/ots/source/npc.cpp` | `buyFluidBackpack`, pending trade, entrega |
| `server/YurOTS/ots/source/player.cpp` | `getExactItemCount` / `removeExactItems` |
| `server/YurOTS/ots/source/const76.h` | `FLUID_STRONG_MANA = 14` |

---

## Cómo probar

1. `hi` → `bp smp` → `yes` → backpack con 20 strong mana potions; cobró 5010 gp.
2. `bp strong mana potion` / `backpack of smp` → mismo resultado.
3. `smp` / `2 strong mana` → compra unitaria a 250 gp.
4. `bp mana fluid` / `bp life` → siguen en 2010 / 1210.
5. `backpack` solo → backpack vacía a 10 gp (no un pack de fluids).
6. `sell all vials` → solo vacíos; SMP/mana/life no se venden.

## Si falla

- Cobra y no entrega BP → `addFluidBackpackToPlayer` en `npc.cpp`
- No reconoce `bp smp` → orden/aliases en `SELLER_FLUID_BACKPACKS`
- `smp` compra mana fluid → el entry de SMP debe estar en `SELLER_BUYS` y `sellerTryBuy` debe correr antes del fallback `mana`
- `sell all vials` toca potions → subtype vacío debe ser `0` y usarse `sellFluid`/`getPlayerFluidCount` exactos
)
