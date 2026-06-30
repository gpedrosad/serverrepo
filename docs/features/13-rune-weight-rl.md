# 13. Peso de runas tipo RL

## Que es

Ajuste para que las runas pesen como items completos tipo RL y no queden infladas por una multiplicacion extra sobre las cargas.

## Por que valio la pena

- mejora la sensacion retro
- evita que mages carguen un castigo artificial de cap
- ordena mejor resupply y movilidad

## Que conviene conservar al portarlo

- definir si el peso declarado representa la runa completa o el peso por carga
- usar una sola interpretacion en todo el motor
- alinear texto, formulas y datos

## Riesgos

- si el motor interpreta distinto que el datapack, las runas quedan absurdamente pesadas o demasiado livianas
- si cambias pesos sin revisar cap general, podes alterar el meta de carry

## Portabilidad

Alta. Es un ajuste pequeño con impacto muy claro.

## Referencias actuales

- `docs/RUNE_WEIGHT_RL.md`
