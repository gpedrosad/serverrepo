# Ayuda para los que llegan: ataque más rápido y protección de novato

Desde el 27 nov 2026. Objetivo: que los que recién empiezan no abandonen por una muerte temprana o por lo lento
que se sube al principio.

## Ataque más rápido contra monstruos

El ataque básico (melee, distancia y wands) espera menos entre golpes a nivel bajo:

| Nivel | Menos espera | Espera sin arma especial (base 1333 ms) |
|---|---|---|
| hasta 8 | 40 % | 800 ms |
| 15 | 27 % | 970 ms |
| 20 | 18 % | 1090 ms |
| 25 | 9 % | 1210 ms |
| 30 o más | nada | 1333 ms |

- Baja en línea recta del nivel 8 al 30 (`NEWBIE_ATTACK_SPEED_*` en `const76.h`).
- **Solo contra monstruos.** No vale contra trainers (`trainer="1"`, incluido el dummy privado), jugadores ni
  summons de jugadores: no acelera el entrenamiento de skills ni da ventaja en PvP.
- Se aplica encima del delay del arma y de Frenzy / Rapid Fire. Nunca baja de 500 ms
  (`ATTACK_SPEED_BUFF_MIN_DELAY_MS`), y si el arma ya pegaba más rápido no la frena.
- Código: `Player::getNewbieAttackSpeedPercent()` y `Player::getAttackDelayMsAgainst()` en `player.cpp`. Lo usan
  `Game::checkCreatureAttacking()` (cada golpe) y `getInitialAttackDelayMs()` (primer golpe al elegir blanco).
  Los hechizos y runas no cambian.

## Protección de novato (hasta nivel 15, incluido)

Al morir con nivel 15 o menos **no se pierde nada**: ni mochila, ni equipo, ni exp, ni magic level, ni skills.
El Amulet of Loss tampoco se gasta. Del 16 al 30 se pierde solo 2 % de exp y todo lo demás como siempre
([NIVELES_BAJOS.md](NIVELES_BAJOS.md), `lowleveldiepercent`); desde el 31 rige `diepercent` de `config.lua`. Ese doc
tiene el resto de la ayuda a niveles bajos (menos daño de monstruos, más regen, menos fallos, más power hit).

- `Player::isNewbieProtected()` (`player.h`): `level <= NEWBIE_PROTECTION_MAX_LEVEL` y sin red ni pink skull.
  Con red o pink skull se pierde todo igual, como siempre.
- `getLostExperience()` devuelve 0 → `die()` y `preSave()` no bajan exp. `die()` además sale antes de la pérdida de
  skills y magic level. `dropLoot()` sale antes de soltar ítems y antes del AOL.
- Efecto lateral buscado: matar a un protegido no da exp de PvP (la exp del asesino sale de `getLostExperience()`),
  así no conviene cazar novatos.
- La Experience recovery rune no cambia: una muerte protegida no toca el storage `9110`.

### Avisos (en inglés, como todo lo que ve el jugador)

| Cuándo | Mensaje |
|---|---|
| Al entrar, nivel ≤ 15 | `Newbie protection: until level 15 you do not lose your backpack, items or level when you die. Monsters also fall faster to your attacks while you are low level.` |
| Al entrar después de morir protegido | `You died, but newbie protection kept your backpack, items and level.` (storage `9131` = 1, se borra al avisar) |
| Al llegar a nivel 15 | `Last level with newbie protection. From level 16 on you can lose your backpack, items and experience when you die.` |
| Al pasar de 15 | `Your newbie protection has ended. From now on you can lose your backpack, items and experience when you die. An Amulet of Loss keeps your items.` |

El aviso de muerte va al volver a entrar porque al morir el cliente 7.6 cierra la pantalla de juego.

## Prueba

Servidor de prueba aparte (copia de los datos, binario nuevo, puerto 7275) con los bots de
`scripts/ot/make-test-bots.py`. Para el ataque, en la copia hace falta un **Speed Dummy**: copiar
`elite trainer monk.xml` cambiando el nombre y `trainer="0"`, y sumarlo a `monsters.xml`. Volver a crear los bots
antes de cada corrida (las muertes quedan guardadas).

```bash
python3 scripts/ot/test-newbie-protection.py --port 7275
```

Resultado del 27 nov 2026 (en el VPS, todo OK):

| Qué se probó | Resultado |
|---|---|
| Aviso al entrar (Bot Novato, nivel 8) | Aparece |
| Golpes en 15 s | Trainer 11 (~1360 ms), Speed Dummy 19 (~790 ms): 1,73 veces más |
| Bot Novato muere con dragon lords | Al volver: aviso, mochila, exp 25600 y nivel 8 intactos |
| Control: Bot Mage (nivel 20) muere | Pierde la mochila y 2 % de exp (`lowleveldiepercent`, NIVELES_BAJOS.md), sin avisos |
| `/level 15` y `/level 16` | Aviso de último nivel protegido y de fin de la protección |

Error de la prueba que ya pasó: contar efectos (`0x83`) sin saber bien la casilla del bot mezcla los golpes del
monstruo con los del bot. La casilla se saca de lo que ve el GM (`0x6A` con el id del bot).

## Cambiar los números

Todo está en `const76.h` (bloque `NEWBIE_*`). Es C++: compilar y cambiar el binario según
`docs/systems/VPS_VULTR.md#cambios-de-c`. Si cambia el nivel de protección, actualizar también los textos de los
avisos (`player.cpp` y `protocol76.cpp`) y la wiki (`web/site/src/wiki/rates.md`).

## Relacionado

- Personajes nuevos arrancan en nivel 8 (`data/players/1-4.xml`, `docs/features/18-web-astro.md`).
- Padrinazgo usa el mismo corte de nivel 15 para el ahijado (`docs/gameplay/PADRINAZGO.md`).
- Trainers: `docs/gameplay/PRIVATE_TRAINER_DUMMY.md`.
