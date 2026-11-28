# Ayuda para niveles bajos

Para que los nuevos no se frustren ni se vayan en los primeros niveles. Todo se apaga solo al
pasar el nivel 30, y lo de daño y regen baja **de a poco**: el jugador no nota un corte.

| Qué | Hasta nivel 15 | Del 16 al 30 | Desde el 31 |
|---|---|---|---|
| Exp perdida al morir | **nada** ([protección de novato](NEWBIE_PROTECTION.md)) | 2 % | 7 % (`diepercent`) |
| Exp de monstruos | +60 % en el 8, baja nivel a nivel (15 = +27 %) | 20 = +4 %; normal desde el 21 | normal |
| Power / mega hit contra monstruos | 16 % / 2 % (el doble) | baja de a poco (nivel 30 ≈ 8,5 % / 1 %) | 8 % / 1 % |
| Golpe fallado contra un monstruo | 70 % de tirar otra vez | baja de a poco (nivel 30 ≈ 4 %) | normal |
| Daño que reciben de monstruos | 60 % | sube de a poco (nivel 30 ≈ 98 %) | 100 % |
| Regen de vida y maná | +40 %, **sin necesidad de comer** | baja de a poco (nivel 30 ≈ +2 %); desde el 16 hay que comer | normal |

Además, dos ayudas que no van por nivel del personaje:

| Qué | Cómo |
|---|---|
| **Training de bienvenida** | Una sola vez por personaje: **22 h extra** (24 h con las 2 h del día), que se gastan después del límite diario y pueden durar varios días. Se entrega la primera vez que entra a la sala, si es nivel 30 o menos. Cuando se termina, queda lo normal (2 h, premium 6 h). |
| **Primeros skills rápidos** | Skills (espada, maza, hacha, distancia, escudo, puños) **x4** hasta skill 20, y después en escala: ≈ x3,25 en 25, x2,5 en 30, x1,75 en 35, **normal desde 40**. Magic level **x4** hasta ML 15, normal en 30. Se suma a los rates de siempre y al premium. |

Hasta el 15 la [protección de novato](NEWBIE_PROTECTION.md) no quita nada al morir (exp, ML, skills, equipo ni mochila) y además se pega más rápido a los monstruos hasta el 30. Del 16 al 30 solo baja la exp perdida; ML, skills, equipo y mochila se pierden igual que siempre (`diepercent`).

## Cómo funciona

- **Rampa** (`Player::lowLevelHelp()`, `player.h`): 100 hasta la mitad de `lowlevel` (15),
  después `(31 − nivel) × 100 / 16` y 0 desde el 31. La usan el daño, la regen, los fallos y el power hit.
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
- **Training de bienvenida** (`Player::checkTraining`, `player.cpp`): storage `9125` guarda los ms
  que le quedan (`-1` = no le tocó o ya la gastó). Mientras le quede, al pasar el límite del día no lo
  saca de la sala: descuenta de la bolsa. Los mensajes de la sala muestran lo que queda de la bolsa.
- **Skills rápidos** (`applyFastSkill`, `player.cpp`): en `addSkillTryInternal` (todos los skills,
  también escudo y puños) y en `addManaSpent` (ML), según el nivel actual de ese skill.
- **Sin comer** (`game.cpp`, bucle de regen): hasta `lowlevelnofood` regenera aunque tenga el
  estómago vacío. Si comió, la comida se gasta igual que siempre. Fuera de PZ, como siempre.
- **Regen** (`Player::lowLevelRegenExtra`, `player.cpp`): el extra se guarda en centésimas y suma
  +1 de vez en cuando, así el número que sube casi no cambia a la vista.

## Curación

`exura` y `exura gran` curan un extra fijo a los jugadores de nivel bajo, con la misma rampa (completa hasta el
15, se apaga en el 31). El extra con la ayuda completa es **+25 a +45** en `exura` y **+55 a +95** en `exura gran`.
Va en `data/spells/lib/spells.lua` (`lowLevelHealHelp`) y en los dos scripts de `data/spells/instant/`. Es Lua: con
reiniciar el server alcanza. Los monstruos que usan `exura` no lo reciben (`getPlayerSkill` les da -1). La rampa
está copiada en Lua con `lowlevel = 30` fijo: si se cambia `lowlevel` en `config.lua`, cambiar también
`LOW_LEVEL_HEAL_TOP`.

| Nivel / ML | `exura` antes → ahora | `exura gran` antes → ahora |
|---|---|---|
| 8 / 1 | 1–6 → 26–51 | 5–11 → 60–106 |
| 15 / 4 | 3–13 → 28–58 | 12–25 → 67–120 |
| 20 / 8 | 5–21 → 22–52 | 19–38 → 57–103 |
| 25 / 10 | 6–26 → 15–43 | 24–48 → 44–83 |
| 31 / 12 (normal) | 7–32 | 29–58 |

Ojo: los personajes nuevos nacen con magic level 0 y `exura` pide ML 1 (`exura gran` ML 4).

## Elfos más suaves

El pueblo élfico al lado del templo (106–113, 62–80) es la primera caza de muchos y los elfos mataban niveles 10–11
(registro de juego del 28 nov). Bajó su daño ~35 % (28 nov 2026):

| Monstruo | Antes | Ahora |
|---|---|---|
| Elf | melee 12–48 + flecha 15–30 | melee 5–30 + flecha 5–20 |
| Elf Scout | 2 flechas 10–70 | 2 flechas 5–45 |
| Elf Arcanist | maglevel 40 (HMM 37–80), flechas 10–70 y 10–30 | maglevel 25 (HMM 27–58), flechas 5–45 y 5–20 |

El arca sudden death del Elf Arcanist (20–70 fijo) no cambió porque lo comparten los Blue Elf Arcanist.
Vida, exp y loot iguales.

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
lowlevelexpbonus = 60       -- % de exp extra en el nivel 8; baja nivel a nivel (0 = sin cambio)
lowlevelexplevel = 20       -- último nivel con bonus de exp
welcometrainingminutes = 1320 -- bolsa de training de bienvenida, una vez (22 h; 0 = sin bolsa)
fastskillboost = 300        -- % extra en skills y ML con la ayuda completa (300 = x4; 0 = sin cambio)
fastskillfull = 20          -- skills: completa hasta este nivel de skill
fastskillend = 40           -- skills: normal desde este nivel
fastmlfull = 15             -- ML: completa hasta este ML
fastmlend = 30              -- ML: normal desde este ML
```
