# 05. Confirmacion universal en NPCs

## Que es

Capa comun para que compras y ventas con NPC pidan confirmacion `yes/no` antes de ejecutar la transaccion.

No fue pensado como parche de un NPC puntual, sino como mejora transversal de UX para todo el sistema comercial.

## Por que valio la pena

- reduce compras accidentales
- baja errores al vender loot o consumibles
- mejora scripts viejos sin reescribirlos
- deja al server con una UX comercial mas prolija

## Que conviene conservar al portarlo

- confirmacion antes de ejecutar
- soporte tanto para buy como sell
- integracion centralizada si el motor lo permite
- mensajes cortos y consistentes

## Riesgos

- algunos NPCs complejos pueden disparar multiples operaciones seguidas
- mal manejo del estado pendiente puede dejar "transacciones fantasma"
- en bases legacy a veces conviene estado externo y no tocar clases centrales

## Portabilidad

Alta. Es de las mejores mejoras costo/beneficio para portar primero.

## Referencias actuales

- `docs/NPC_CONFIRMATION.md`
