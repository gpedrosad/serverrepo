# 12. Soft Boots con regen y desgaste real

> Doc técnico canónico: [`docs/gameplay/SOFT_BOOTS.md`](../gameplay/SOFT_BOOTS.md).

## Que es

Version util y clara de Soft Boots (implementada y activa en este server):

- regen cada `3` segundos
- `+3 HP` y `+12 MP`
- duracion total de `4` horas
- al agotarse pasan a `worn soft boots` (`3550`)
- IDs: soft `3549`, worn `3550`
- flag C++: `YUR_SOFT_BOOTS`

## Por que valio la pena

- le da valor real a un item iconico
- agrega una pequena capa economica y de decision
- el beneficio se siente mientras se usa

## Que conviene conservar al portarlo

- beneficio facil de percibir
- desgaste real
- transformacion a version agotada
- activacion al equiparlo, no solo por tenerlo en backpack

## Riesgos

- si la regen es demasiado fuerte, pisa otras fuentes de sustain
- si no se comunica el desgaste, parece bug
- si la duracion se resetea mal, puede explotarse
- en esta base, IDs `3549`/`3550` tambien estan cableados como doors en actions/XML — ver pitfall en el doc gameplay

## Portabilidad

Alta. Se adapta facil y suele gustar mucho.

## Referencias actuales

- [`docs/gameplay/SOFT_BOOTS.md`](../gameplay/SOFT_BOOTS.md)
- `OTINFO`
- `server/YurOTS/ots/source/player.cpp` (`checkSoftBoots`, `onSoftBootsEquipped`)
- `server/YurOTS/ots/source/const76.h`
- `server/YurOTS/ots/data/items/items.xml`
