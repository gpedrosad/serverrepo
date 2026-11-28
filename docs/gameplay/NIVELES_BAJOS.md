# Ayuda para niveles bajos

Para que los nuevos no se frustren ni se vayan en los primeros niveles. Todo se apaga solo al
pasar el nivel 30, y lo de daño y regen baja **de a poco**: el jugador no nota un corte.

| Qué | Hasta nivel 15 | Del 16 al 30 | Desde el 31 |
|---|---|---|---|
| Exp perdida al morir | 2 % | 2 % | 7 % (`diepercent`) |
| Power / mega hit contra monstruos | 16 % / 2 % (el doble) | baja de a poco (nivel 30 ≈ 8,5 % / 1 %) | 8 % / 1 % |
| Golpe fallado contra un monstruo | 70 % de tirar otra vez | baja de a poco (nivel 30 ≈ 4 %) | normal |
| Daño que reciben de monstruos | 60 % | sube de a poco (nivel 30 ≈ 98 %) | 100 % |
| Training por día | +2 h (gratis 4 h, premium 8 h) | baja de a poco (nivel 30 ≈ +7 min) | 2 h / 6 h |
| Regen de vida y maná | +40 %, **sin necesidad de comer** | baja de a poco (nivel 30 ≈ +2 %); desde el 16 hay que comer | normal |

Solo baja la exp perdida; ML, skills, equipo y mochila se pierden igual que siempre (`diepercent`).

## Cómo funciona

- **Rampa** (`Player::lowLevelHelp()`, `player.h`): 100 hasta la mitad de `lowlevel` (15),
  después `(31 − nivel) × 100 / 16` y 0 desde el 31. La usan el daño, la regen, los fallos, el power hit y el training.
- **Muerte** (`Player::getLostExperience()`): hasta `lowlevel` usa `lowleveldiepercent`. Ese mismo
  valor es la base de la exp que gana quien mata a un jugador (`game.cpp`), así que matar niveles
  bajos da menos exp, y la Zagan rune devuelve sobre lo que de verdad se perdió.
- **Daño** (`applyLowLevelShield`, `game.cpp`): se aplica después de los amuletos y la counter stance,
  en el golpe cuerpo a cuerpo y a distancia (`creatureMakeDamage`) y en hechizos, runas, áreas y
  daño por tiempo de monstruos (`creatureMakeMagic`). Solo si el atacante es un **monstruo**: los
  summons de jugadores y el PvP no cambian. Mínimo 1 de daño.
- **Fallar menos** (`GameState::onAttack`, `game.cpp`): golpe cuerpo a cuerpo o a distancia de un
  jugador contra un monstruo que quedó en 0 (falló el arma a distancia, o lo paró la defensa o la
  armadura): con `lowlevelmisscut` % × la rampa se tira el golpe otra vez, una sola vez. Las
  municiones no se gastan de más (`getWeaponDamage` no consume). PvP y summons no cambian.
- **Power y mega hit** (`GameState::applyPowerHit`, `game.cpp`): si el objetivo de la tirada es un
  monstruo, las chances de `powerhitchance` y `megahitchance` suben `lowlevelpowerhitboost` % × la
  rampa. Vale para melee, distancia, runas y hechizos. Contra jugadores no cambia.
- **Training** (`getTrainingDailyLimitMs`, `player.cpp`): al límite diario (gratis o premium) se le
  suman `lowleveltrainingminutes` × la rampa. Si sube de nivel en el día, el límite se recalcula.
- **Sin comer** (`game.cpp`, bucle de regen): hasta `lowlevelnofood` regenera aunque tenga el
  estómago vacío. Si comió, la comida se gasta igual que siempre. Fuera de PZ, como siempre.
- **Regen** (`Player::lowLevelRegenExtra`, `player.cpp`): el extra se guarda en centésimas y suma
  +1 de vez en cuando, así el número que sube casi no cambia a la vista.

## Ajustar

Valores por defecto en `luascript.cpp`. Se pueden pisar desde `config.lua` (no están escritos ahí
porque el `config.lua` del VPS tiene un cambio local):

```lua
lowlevel = 30               -- 0 apaga todo
lowleveldiepercent = 2      -- % de exp perdida hasta `lowlevel`
lowlevelmonsterdamage = 60  -- % del daño de monstruos con la ayuda completa (100 = sin cambio)
lowlevelregenbonus = 40     -- % extra de regen con la ayuda completa (0 = sin cambio)
lowlevelnofood = 15         -- hasta este nivel regenera sin comer (0 = siempre hay que comer)
lowlevelmisscut = 70        -- % de segunda tirada al fallar contra monstruos (0 = sin cambio)
lowlevelpowerhitboost = 100 -- % extra de chance de power/mega hit contra monstruos (100 = el doble)
lowleveltrainingminutes = 120 -- minutos extra de training por día (0 = sin cambio)
```
