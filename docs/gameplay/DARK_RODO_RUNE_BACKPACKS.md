# Dark Rodo rune backpacks

## Objetivo

Agregar venta de backpacks de runas al NPC `dark rodo` cuando el jugador diga `backpacks`.

## Archivos tocados

- `server/YurOTS/ots/data/npc/scripts/runes.lua`
- `server/YurOTS/ots/source/npc.cpp`
- `server/YurOTS/ots/source/npc.h`

## Cambio funcional

El NPC ahora responde a:

- `backpacks`
- `rune backpacks`
- `bps`

Y ofrece estas opciones (precios actuales, nov 2026: 20 runas al precio suelto, la mochila va de regalo):

- `bp hmm` = `300 gp` (20 × 15)
- `bp uh` = `4000 gp` (20 × 200)
- `bp gfb` = `900 gp` (20 × 45)
- `bp explosion` = `700 gp` (20 × 35)
- `bp sd` = `5000 gp` (20 × 250)
- `bp blank` = `200 gp` (20 × 10)

Los precios salen de la tabla de runas de `runes.lua` (`backpackPrice`), así que si cambia el precio suelto cambia también el de la mochila. Los valores viejos de este documento (810/1210/1810, y después 20 × precio × cargas + 10, que cobraba la bp de UH al doble) ya no aplican.

Tambien hay aliases mas largos: `bp ultimate healing`, `bp sudden death`, `backpack of uh`, `backpack of sd`, etc. "bp mana" / "bp smp" no las vende Dark Rodo: deriva al Seller.

## Cambio tecnico

Se agrego un helper generico de compra de backpack con contenido en el core NPC.

Nuevo binding Lua:

- `buyItemBackpack(cid, backpackItemId, contentItemId, contentCountOrSubtype, contentItemCount, cost)`

Esto permite vender containers llenos con items que usan:

- charges
- subtype
- count especial al crear el item

## Como probar

1. Hablar con `dark rodo`
2. Decir `backpacks`
3. Verificar que liste las opciones
4. Decir `bp sd`
5. Confirmar con `yes`
6. Verificar que llegue una backpack con 20 SD
7. Repetir con `bp uh`, `bp explosion`, `bp hmm` y `bp gfb`

## Que revisar si algo falla

- Si cobra pero no entrega la backpack, revisar `buyItemBackpack` y `addItemBackpackToPlayer(...)` en `npc.cpp`
- Si el contenido sale con charges incorrectas, revisar el `contentCountOrSubtype` usado en `runes.lua`
- Si el NPC no reconoce el comando, revisar los aliases en `runes.lua`
