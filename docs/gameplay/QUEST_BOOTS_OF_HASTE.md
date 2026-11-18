# Quest de Boots of Haste: la casa de los teleports al sur del depot

Casa de entramado de madera justo al sur del depot (`x 127–136, y 61–66`, pisos 7 y 6). Cada piso está partido en
salas angostas por paredes; se pasa de una a otra por teleports (`1387`), arriba (`y 62`) y abajo (`y 65`).
Dos cofres: `128,62,7` y `128,62,6` (Boots of Haste y Blue Robe). Registro de quests: `boh` en
`web/site/src/data/quests.json`.

## Recorrido (destinos leídos del `test.otbm`)

Se entra por la puerta este del piso 7 (`136,62,7`). Cada sala tiene un teleport para seguir y otro para volver.

| Orden | Sala | Teleport para seguir | Monstruo (nov 2026) | Exp | Respawn |
|---|---|---|---|---:|---:|
| 1 | z7 `135, 62–65` (entrada) | `135,65,7` → `133,64,7` | Mutated Tiger (`135,63`) | 750 | 200 s |
| 2 | z7 `133, 62–65` | `133,62,7` → `131,64,7` | Emerald Scarab (`133,63`) | 1150 | 200 s |
| 3 | z7 `131, 62–65` | `131,62,7` → `129,64,7` | Ice Spider (`131,64`) | 1400 | 200 s |
| 4 | z7 `128–129, 62–65` (**cofre** `128,62,7`) | `129,62,7` → `135,64,6` | 2 Hellhound (`128,63` y `128,64`) | 1300 c/u | 200 s |
| 5 | z6 `134–135, 62–65` | `135,62,6` → `132,64,6` | Imperial Hero (`134,63`) | 2600 | 300 s |
| 6 | z6 `131–132, 62–65` | `132,62,6` → `129,64,6` | Black Dragon (`131,63`) | 2900 | 300 s |
| 7 | z6 `128–129, 62–65` (**cofre final** `128,62,6`) | — | Dark Hydra (`128,63`) | 3000 | 300 s |

Vueltas: `133,65,7` → `135,64,7`; `131,65,7` → `133,63,7`; `129,65,7` → `131,63,7`; `135,65,6` → `129,63,7`;
`132,65,6` → `135,63,6`; `129,65,6` → `132,63,6`.

**Antes (hasta nov 2026):** Angry Troll, Angry Minotaur Guard, Furious Cyclops, 4 Angry Orc Berserker, 2 Angry
Giant Spider, 2 Enraged Vampire y 2 Enraged Hydra, para nivel 60–80. Ahora son monstruos nuevos de sprite propio, de a
uno en las salas fuertes, y la quest figura para **nivel 80–100**.

## Detalles

- Las salas de 1 de ancho (`135`, `133`, `131`) solo tienen dos casillas libres, y las dos son llegadas de
  teleports: el monstruo queda en una de ellas, igual que antes.
- **Sin ventanas en la sala del Imperial Hero** (nov 2026): las dos ventanas de entramado (`1264`) de su pared
  este (`136,63,6` y `136,65,6`) pasaron a pared (`1043`): la sala queda cerrada.
  En el piso 7 quedan las ventanas de antes (`127,63`, `136,63`, `128–129,66`).
- Los spawns son a mano en `test-spawn.xml` (ningún generador los pisa), con un comentario arriba de cada piso.
