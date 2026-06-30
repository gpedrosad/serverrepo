# 07. Seller: packs de fluids y venta de vials

## Que es

Ampliacion del Seller para vender backpacks ya armadas de fluids y permitir venta segura de vials vacios, incluida la opcion `sell all vials`.

## Por que valio la pena

- reduce clicks y friccion de resupply
- mejora mucho la experiencia early/mid game
- evita vender por error frascos con contenido
- hace que el Seller resuelva necesidades reales y no solo ventas unitarias

## Que conviene conservar al portarlo

- backpacks listas de mana/life fluid
- diferenciacion exacta entre vial vacio y fluid container con subtipo
- venta masiva de vials
- confirmacion antes de ejecutar

## Riesgos

- si no distinguis subtypes, el NPC puede comprar cosas que no debe
- si no validas capacidad/espacio, el player paga y no recibe bien el pack
- si cambias item ids o subtypes del datapack, hay que revisar la logica

## Portabilidad

Alta. Se adapta facil y se nota enseguida en la experiencia del jugador.

## Referencias actuales

- `docs/SELLER_FLUIDS.md`
