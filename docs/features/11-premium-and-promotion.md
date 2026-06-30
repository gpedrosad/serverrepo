# 11. Premium y promotion con perks reales

## Que es

Escalera simple de progreso/estatus:

- premium con beneficios jugables concretos
- promotion como siguiente paso de identidad y regen

En esta base premium y promotion no son solo un flag cosmetico; afectan regen y, en premium, tambien exp adicional contra monstruos.

## Por que valio la pena

- hace que premium se sienta util
- hace que promotion tenga peso real
- permite monetizacion o rewards del staff con impacto claro

## Que conviene conservar al portarlo

- perks comprensibles
- diferencia clara entre premium y promoted
- requisitos simples de comunicar
- persistencia limpia de premium time y promoted state

## Riesgos

- si premium da demasiado poder, se siente pay to win
- si promotion casi no cambia nada, el sistema pierde interes
- la prioridad de cola conviene tratarla como opcion de config, no como verdad fija

## Nota de esta copia

El motor soporta premium/promotion y bonus reales.
La prioridad de cola existe como patron, pero hoy la config actual esta con `queuepremmy = "yes"`, asi que no esta actuando como bypass premium.

## Portabilidad

Media. El concepto es bueno, pero depende mucho del modelo economico del otro server.

## Referencias actuales

- `server/YurOTS/ots/data/npc/scripts/promote.lua`
- `server/YurOTS/ots/source/player.cpp`
- `server/YurOTS/ots/source/creature.cpp`
- `server/YurOTS/ots/config.lua`
