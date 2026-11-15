# Dark Cathedral — catedral en ruinas con cripta de dos pisos

Recreación de la **Dark Cathedral** de Tibia 7.6 en una zona vacía del mapa, accesible por el portal
de la plaza de portales del templo (`157,47,7`). Generada con `scripts/map/generate-dark-cathedral.py`
(patrón idempotente: parchea `test.otbm`, escribe `test-spawn.xml`, `readables.xml` y el manifiesto
`generated-dark-cathedral.json`).

## Cómo se llega

1. Plaza del templo → portal **Catedral Oscura** en `157,47,7` (al lado de la Isla Natural).
2. Se llega a `236,428,7`, frente a la entrada sur de la nave.
3. El portal de vuelta al templo está en `233,430,7` (y otro al fondo de la cripta, `236,431,9`).

## Pisos

| Piso | Contenido |
|------|-----------|
| **z7** superficie | Jungla cerrada alrededor. Nave NEGRA (norte-sur) con entrada al sur. Edificio grande de ladrillo al oeste (varias salas), sala rectangular gris al sur con bancos y escombros, salas chicas al este. Franja de jungla en arco al norte. Dos bajadas: una en la jungla norte y otra al oeste junto a la sala gris. |
| **z8** cripta (-1) | Pasillos y salas de ladrillo naranja sobre roca marrón, piso de piedra gris. Conecta las dos bajadas de z7 y tiene una bajada al -2. |
| **z9** cripta profunda (-2) | Planta simétrica: sala grande al norte, cruz central con la escalera de subida, brazos oeste/este con salas, sala grande central al sur y salas laterales. Portal de vuelta al fondo. |

## Coordenadas

| Elemento | Posición |
|----------|----------|
| Caja | `x 200–271`, `y 380–451`, `z 7–9` |
| Llegada (portal de la plaza) | `236,428,7` |
| Portal de vuelta (superficie) | `233,430,7` → `157,48,7` |
| Portal de vuelta (fondo) | `236,431,9` → `157,48,7` |
| Bajada A (jungla norte) | agujero `236,389,7` → escalera `236,389,8` |
| Bajada B (oeste) | agujero `224,430,7` → escalera `224,430,8` |
| Bajada al -2 | agujero `236,414,8` → escalera `236,414,9` |
| Nave (negra) | interior `x 232–239`, `y 394–425`, entrada sur `235–236,426` |
| Edificio oeste (ladrillo) | interior `x 209–228`, `y 392–420` |
| Salas este (ladrillo) | interior `x 247–263`, `y 392–418` |
| Sala gris sur | interior `x 226–246`, `y 433–442` |

## Escaleras

Cada bajada usa el patrón estándar del mapa: **agujero `432` arriba + escalera `1385` abajo** en la
misma casilla (la escalera sube al norte). Al bajar se aterriza en `(x, y+1)` del piso de abajo; al
subir en `(x, y-1)` del piso de arriba. Ambas llegadas quedan en piso libre (validado).

## Spawns (84 monstruos)

| Piso | Zona | Monstruos |
|------|------|-----------|
| z7 | Edificio oeste | Bandit, Smuggler, Wild Warrior |
| z7 | Salas este | Bandit, Wild Warrior, Hunter |
| z7 | Sala gris sur | Smuggler, Hunter, Bandit |
| z7 | Jungla norte | Wild Warrior, Hunter, Bandit |
| z8 | Sala oeste 1 | Bandit, Smuggler |
| z8 | Sala oeste 2 | Wild Warrior, Bandit |
| z8 | Cueva oeste (no-muertos) | Rotworm, Skeleton, Ghoul |
| z8 | Sala este 1 | Slime, Poison Spider |
| z8 | Sala este 2 | Assassin, Bandit, Smuggler |
| z8 | Sala este 3 | Bat, Centipede, Poison Spider |
| z9 | Sala grande norte | Monk, Dark Monk, Ghost |
| z9 | Brazo oeste | Dark Monk, Ghost |
| z9 | Brazo este | Witch, Hunter, Dark Monk |
| z9 | Sala central sur | Mummy, Witch, Hunter, Stone Golem |
| z9 | Salas laterales sur | Ghost, Dark Monk |

## Cómo regenerar

```bash
python3 scripts/map/generate-dark-cathedral.py --dry-run --preview /tmp/catedral   # valida y dibuja
python3 scripts/map/generate-dark-cathedral.py                                      # escribe mapa, spawns, carteles, manifiesto
python3 scripts/map/temple-portals.py                                               # portal de la plaza (dueño único de portales del templo)
python3 scripts/map/check-map-load.py
python3 scripts/map/validate-tele-dest.py server/YurOTS/ots/data/world/test.otbm
```

Re-ejecutable: borra la caja `z7–z9` y reemplaza los bloques `DARK_CATHEDRAL_SPAWNS` y
`DARK_CATHEDRAL_SIGNS`. Hace backup `test.otbm.bak-darkcathedral` la primera vez.

## Reglas respetadas

- Paredes de ladrillo (naranja, `1027/1028/1030/1033`) y piedra (gris, `1049/1050/1051/1053`) con el
  modelo de roomkit (post / horizontal / vertical / esquina SE).
- Criptas con piso de piedra gris `415` y fondo de roca `101`; nave con mármol negro `407`; ruinas con
  tierra `103`; jungla con pasto `4756`.
- Cada casilla de pared tiene una única pieza (sin esquinas internas); todo piso caminable se alcanza
  desde la llegada (BFS); no se ve el borde de la caja desde el interior.
- Sin monstruos "rage" (Angry/Furious/Enraged): solo bandit, smuggler, wild warrior, assassin, slime,
  poison spider, bat, rotworm, scorpion, centipede, skeleton, ghoul, ghost, mummy, monk, dark monk,
  witch, hunter, stone golem.

## Imágenes

- `docs/items-and-map/img/dark-cathedral-z7.png` — superficie.
- `docs/items-and-map/img/dark-cathedral-z8.png` — cripta (-1).
- `docs/items-and-map/img/dark-cathedral-z9.png` — cripta profunda (-2).

Referencia original (layout de la wiki y minimapa de Gonzalo):
`docs/items-and-map/img/dark-cathedral-ref/`.
