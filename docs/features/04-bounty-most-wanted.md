# 04. Bounty / Most Wanted

## Que es

Sistema de recompensas entre jugadores financiado desde banco, con visibilidad publica en web y transferencia de la bounty al killer en PvP valido.

La gracia no es solo "pagar por matar", sino convertir la bounty en una carga social que se mueve entre players.

## Por que valio la pena

- genera historias y cacerias organicas
- le da vida al PvP sin forzar wars
- conecta NPC, banco, persistencia y web en una sola feature
- hace que la web tenga contenido vivo

## Que conviene conservar al portarlo

- la bounty sale de riqueza existente
- no debe imprimirse oro nuevo al cobrarla
- no permitir misma cuenta contra misma cuenta
- persistencia robusta
- ranking publico ordenado y filtrado

## Riesgos

- exploits si no validas account sharing
- inconsistencias si guardas sponsor y target sin rollback
- toxicidad si la UI publica expone personajes que deberian estar ocultos

## Portabilidad

Media. La idea es fuerte, pero requiere tocar persistencia, kills PvP, banco y web o UI publica.

## Referencias actuales

- `docs/MOST_WANTED_SYSTEM.md`
