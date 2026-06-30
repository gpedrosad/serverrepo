# 06. Economia apoyada en banco

## Que es

Uso real del banco como infraestructura del server y no solo como deposito opcional.

En esta base termina impactando en varias cosas:

- NPCs que pueden cobrar desde mano + banco
- Banker con balance, deposit, withdraw y transfer
- Bounty financiada desde bank balance
- Golden amulet que manda el oro del loot directo al banco

## Por que valio la pena

- reduce friccion y viajes administrativos
- le da sentido fuerte al banco
- simplifica la vida del jugador sin regalar items
- abre nuevas features economicas encima

## Que conviene conservar al portarlo

- pago mixto inventario + banco
- mensajes claros de cuanto se desconto de cada lado
- banker con comandos simples
- auto-bank solo para oro, no para todo el loot

## Riesgos

- si banco e inventario no persisten con cuidado, aparecen perdidas o duplicaciones
- auto-bankear demasiado sin feedback puede restar sensacion de loot
- conviene no mezclar esta feature con items no monetarios

## Portabilidad

Media. La idea vale mucho, pero toca persistencia, NPCs y economia base.

## Referencias actuales

- `server/YurOTS/ots/source/player.cpp`
- `server/YurOTS/ots/source/game.cpp`
- `server/YurOTS/ots/data/npc/scripts/banker.lua`
- `docs/MOST_WANTED_SYSTEM.md`
