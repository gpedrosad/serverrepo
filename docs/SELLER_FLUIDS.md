# Seller fluids y vials

## Objetivo

Se amplió el NPC `seller` para:

- vender `backpack of mana fluid`
- vender `backpack of life fluid`
- permitir `sell all vials`
- vender solamente `empty vials`, sin confundirlas con mana/life fluids

## Archivos tocados

- `/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/data/npc/scripts/seller.lua`
- `/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/source/npc.cpp`
- `/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/source/npc.h`
- `/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/source/player.cpp`
- `/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/source/player.h`

## Cambios funcionales

### Nuevas compras

- `bp mana fluid`
- `bp of mana fluid`
- `backpack of mana fluid`
- `bp manafluid`

Precio:

- `2010 gp` = `20 x mana fluid (100 gp)` + `1 backpack (10 gp)`

Contenido:

- `1 backpack`
- `20 mana fluids`

Tambien se agrego:

- `bp life fluid`
- `bp of life fluid`
- `backpack of life fluid`
- `bp lifefluid`

Precio:

- `1210 gp` = `20 x life fluid (60 gp)` + `1 backpack (10 gp)`

Contenido:

- `1 backpack`
- `20 life fluids`

### Venta de vials vacios

Antes el seller usaba el `itemid 2006` sin distinguir subtipo, asi que podia terminar aceptando cualquier fluid container.

Ahora:

- `vial`
- `flask`
- `frasco`

solo venden `empty vials` por:

- `10 gp` cada una

### Venta masiva

Se agrego:

- `sell all vials`
- `sell all flasks`
- `sell all frascos`

El NPC cuenta todos los `empty vials` del jugador y arma una sola confirmacion por el total.

## Cambios tecnicos

### `npc.cpp` / `npc.h`

Se agregaron bindings Lua nuevos:

- `buyFluidBackpack(cid, backpackItemId, fluidItemId, fluidSubtype, fluidCount, cost)`
- `sellFluid(cid, itemid, subtype, count, cost)`
- `getPlayerFluidCount(cid, itemid, subtype)`

Tambien se extendio `PendingTransaction` para soportar:

- ventas por subtipo de fluid
- compra especial de backpack llena

### `player.cpp` / `player.h`

Se agregaron helpers para trabajar con fluid containers exactos:

- `getExactItemCount(id, subtype)`
- `removeExactItems(id, subtype, count)`

Esto evita borrar accidentalmente mana/life fluids cuando el NPC compra vials vacios.

## Como probar

1. Hablar con el seller y decir `bp mana fluid`
2. Confirmar con `yes`
3. Verificar que llegue una backpack con 20 mana fluids
4. Repetir con `bp life fluid`
5. Darse vials vacios y decir `sell all vials`
6. Confirmar con `yes`
7. Verificar que desaparezcan solo los vials vacios
8. Verificar que mana/life fluids no se vendan al usar `vial` o `sell all vials`

## Que revisar si falla

- Si el NPC cobra pero no entrega la backpack, revisar `addFluidBackpackToPlayer(...)` en `npc.cpp`
- Si el NPC dice que no hay espacio, revisar capacidad y slots libres del jugador
- Si `sell all vials` no encuentra items, revisar que el subtype vacio siga siendo `0`
- Si el script Lua no reconoce frases, revisar `seller.lua`
- Si hay errores de compilacion, revisar las nuevas firmas en `npc.h` y `player.h`

## Riesgos conocidos

- La venta masiva nueva aplica especificamente a `itemid 2006` subtype `0`
- Si en el futuro el datapack usa otro contenedor o subtype para vials vacios, hay que actualizar esa parte
- La logica de backpack llena fue agregada en el core del NPC, no como hack solo de Lua
