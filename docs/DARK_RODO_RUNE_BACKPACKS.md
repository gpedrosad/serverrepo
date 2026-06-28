# Dark Rodo rune backpacks

## Objetivo

Agregar venta de backpacks de runas al NPC `dark rodo` cuando el jugador diga `backpacks`.

## Archivos tocados

- `/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/data/npc/scripts/runes.lua`
- `/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/source/npc.cpp`
- `/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/source/npc.h`

## Cambio funcional

El NPC ahora responde a:

- `backpacks`
- `rune backpacks`
- `bps`

Y ofrece estas opciones:

- `bp hmm` = `810 gp`
- `bp uh` = `810 gp`
- `bp gfb` = `1210 gp`
- `bp explosion` = `1210 gp`
- `bp sd` = `1810 gp`

Cada backpack incluye:

- `1 backpack`
- `20 runes`

Tambien se agregaron aliases mas largos:

- `bp ultimate healing`
- `bp sudden death`
- `backpack of uh`
- `backpack of sd`
- `backpack of explosion`
- `backpack of gfb`
- `backpack of hmm`

## Precios

Los precios siguen la logica actual del NPC:

- `bp hmm`: `20 x 40 gp` + `10 gp backpack` = `810 gp`
- `bp uh`: `20 x 40 gp` + `10 gp backpack` = `810 gp`
- `bp gfb`: `20 x 60 gp` + `10 gp backpack` = `1210 gp`
- `bp explosion`: `20 x 60 gp` + `10 gp backpack` = `1210 gp`
- `bp sd`: `20 x 90 gp` + `10 gp backpack` = `1810 gp`

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
