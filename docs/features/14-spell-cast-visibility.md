# 14. Visibilidad correcta del casteo

## Que es

Fix para que las palabras magicas solo aparezcan cuando el spell realmente sale.

Antes podia verse el texto aunque el cast fallara por exhausted u otra validacion.

## Por que valio la pena

- mejora mucho la sensacion de pulido
- evita confundir a players con casts "fantasma"
- alinea mejor feedback visual con resultado real

## Que conviene conservar al portarlo

- el texto del spell debe depender del exito real del cast
- cubrir no solo exhausted, tambien invalid target y fallos del script

## Riesgos

- si algun spell custom depende de devolver `false` de forma rara, hay que revisarlo
- si hay spells que fallan silenciosamente, conviene acompanar esto con mejor feedback

## Portabilidad

Alta. Es una de esas mejoras chicas que elevan mucho la calidad percibida.

## Referencias actuales

- `docs/SPELL_CAST_VISIBILITY.md`
