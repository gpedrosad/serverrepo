# Peso de runas como Tibia RL

## Objetivo

Hacer que las runas pesen como en Tibia RL 7.6 y no queden artificialmente pesadas por una multiplicacion extra de cargas.

## Diagnostico

Los datos en `server/YurOTS/ots/data/items/items.xml` ya tenian pesos tipo Tibia 7.6 para cada runa:

- HMM `2311` = `1.2`
- GFB `2304` = `2.1`
- Magic Wall `2293` = `8.0`

El problema estaba en `server/YurOTS/ots/source/item.cpp`: `Item::getWeight()` detectaba runas y multiplicaba ese peso por las cargas restantes.

Eso inflaba la capacidad consumida. Ejemplos con la logica anterior:

- HMM `5x`: `1.2 * 5 = 6.0 oz`
- GFB `3x`: `2.1 * 3 = 6.3 oz`
- Magic Wall `4x`: `8.0 * 4 = 32.0 oz`

## Cambio aplicado

Se dejo la logica asi:

- items stackeables: siguen pesando `weight * count`
- runas: usan el `weight` base del item, sin multiplicar por cargas
- resto de items: sin cambios

Con esto, las runas pasan a usar directamente el peso declarado en `items.xml`, que es el comportamiento esperado para imitarlas como en Tibia RL dentro de este proyecto.

## Antes y despues

- HMM `5x`: `6.0 oz` -> `1.2 oz`
- GFB `3x`: `6.3 oz` -> `2.1 oz`
- Magic Wall `4x`: `32.0 oz` -> `8.0 oz`
- Sudden Death `2x`: `4.2 oz` -> `2.1 oz`

## Archivos tocados

- `server/YurOTS/ots/source/item.cpp`
- `server/YurOTS/ots/data/items/items.xml`
- `OTINFO`

## Nota

La documentacion que decia "oz por carga" quedo corregida porque describia una interpretacion que hacia las runas mucho mas pesadas de lo esperado.
