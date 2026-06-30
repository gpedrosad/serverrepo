# 02. No PvP dentro de training

## Que es

Bloqueo completo de PvP dentro de la training zone, sin tocar el PvP del resto del server.

La proteccion se pensó en capas:

- no deja fijar target valido ahi
- anula dano si algo intenta pasar igual
- evita efectos visuales engañosos

## Por que valio la pena

- evita grief en una zona pensada para progreso pasivo
- elimina discusiones de "me pego en training"
- conserva el PvP general del server sin convertir todo en no-PvP

## Que conviene conservar al portarlo

- bloqueo de seleccion de target
- bloqueo de dano real
- bloqueo de efectos ofensivos confusos
- soporte para player, summon y player vs summon

## Riesgos

- si cubris solo melee y no spells/runes, queda agujero
- si la zona esta mal definida, podes bloquear PvP fuera de training
- si el cliente muestra efectos pero no dano, parece bug

## Portabilidad

Alta. La regla es simple; cambia solo el punto de integracion segun el motor.

## Referencias actuales

- `docs/TRAINING_ZONE_NO_PVP.md`
