# Training bonus parchment

## Objetivo

Agregar un parchment especial que da `+5 hours` de training por el dia actual.

## Item objetivo

- Item: `parchment`
- Item id: `1953`
- Position: `135 130 9`

## Comportamiento

Al hacer `use` sobre ese parchment exacto:

- el jugador recibe `+5 hours` de training para hoy
- el bonus aplica solo durante el dia actual
- cada jugador puede reclamarlo una sola vez por dia

Si el jugador ya lo uso hoy:

- no vuelve a sumar tiempo
- recibe mensaje indicando que ya lo reclamo

## Mensajes

El bonus parchment responde en ingles:

- `The parchment blesses your training. You received +5 hours of training time for today.`
- `The parchment is empty. You have already claimed your +5 hours of training for today.`

## Archivos tocados

- `/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/data/actions/scripts/rwitems.lua`
- `/Users/gonzalo/Desktop/yurots-principal/server/YurOTS/ots/source/player.cpp`

## Storages usados

- `9102`: fecha del bonus diario
- `9103`: minutos extra de training para ese dia

## Detalle tecnico

El sistema original del training ya usaba:

- `9100`: fecha del dia de training
- `9101`: tiempo usado ese dia

Se extendio el calculo del limite diario para sumar el bonus si:

- `STORAGE_TRAINING_BONUS_DATE == hoy`

Entonces el limite diario pasa a ser:

- `trainingdailyminutes + 300`

## Como probar

1. Ir al parchment en `135 130 9`
2. Hacer `use`
3. Verificar el mensaje en ingles
4. Entrar a training zone
5. Verificar que el mensaje de entrada muestre un limite de hoy mayor al base
6. Volver a hacer `use` el mismo dia
7. Verificar que ya no entregue otro bonus

## Riesgos / cosas a revisar

- El comportamiento especial aplica solo a ese parchment en esa posicion exacta
- Otros parchments `1953` siguen funcionando como `rwitems`
- Si se mueve el parchment en el mapa, hay que actualizar la posicion en `rwitems.lua`
