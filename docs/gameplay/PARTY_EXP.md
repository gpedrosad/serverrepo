# Experiencia compartida y bonus en party (nov 2026)

Al matar un monstruo cuando una party tiene **2 o más miembros vivos cerca**, la experiencia del monstruo se reparte entre los miembros cercanos (incluyendo a quien tankea o cura sin pegar) y suma un **bonus extra por party** que aparece diferenciado sobre el personaje.

## Reglas

- **Solo monstruos:** no aplica en PvP (`attackedplayer`) ni en criaturas sin exp (trainers, fauna).
- **Cercanía:** cuenta cada miembro de la misma `party`, conectado y vivo (`health > 0`), dentro de **30 casillas** en X/Y del monstruo muerto y hasta **±1 piso** en Z.
- **Mínimo 2 miembros cerca:** si solo hay 1 miembro de la party cerca (o los demás están lejos/muertos), no se comparte ni se da bonus — aplica la exp normal individual por daño.
- **Reparto + tasas propias:** la parte de daño que hizo la party al monstruo se divide en partes iguales entre los miembros cercanos; sobre esa parte cada uno aplica su propio multiplicador de nivel (`expmul`) y su bonus premium (+10 %).
- **Bonus extra por party:**

| Miembros de la party cerca | Bonus extra sobre la exp base | Config (`config.lua`) |
|---------------------------:|------------------------------:|-----------------------|
| 1 (solo / resto lejos)     | 0 % (sin compartir)           | — |
| 2                          | **+25 %**                     | `partyexpbonus2 = 25` |
| 3                          | **+50 %**                     | `partyexpbonus3 = 50` |
| 4 o más                    | **+75 %**                     | `partyexpbonus4 = 75` |

- **Daily Task:** todos los miembros cercanos que reciben exp compartida suman progreso en su contrato diario (salvo trainers).
- **Visual diferenciada:** sobre cada jugador que recibe exp salen dos textos flotantes (sin spamear el chat):
  - **Blanco (`0xD7`):** exp base recibida (ej. `1750`).
  - **Celeste brillante (`35`, `COLOR_PARTY_EXP`):** exp extra por party con signo `+` (ej. `+437`).

## Configuración opcional (`config.lua`)

Todas las claves tienen valor por defecto en `luascript.cpp` (no hace falta agregarlas al `config.lua` del repo):

```lua
partyexprange = 30
partyexpfloordiff = 1
partyexpbonus2 = 25
partyexpbonus3 = 50
partyexpbonus4 = 75
```

## Código

| Archivo | Qué |
|---------|-----|
| `server/YurOTS/ots/source/const76.h` | `COLOR_PARTY_EXP = 35` (celeste brillante). |
| `server/YurOTS/ots/source/luascript.h`, `luascript.cpp` | Parámetros `PARTY_EXP_*` con defaults. |
| `server/YurOTS/ots/source/game.h` | `ExpGainDisplay { creature, baseExp, partyBonusExp }` en `CreatureState::expGains`. |
| `server/YurOTS/ots/source/game.cpp` | `applyMonsterExpRates`, `getPartyExpBonusPercent`, `getNearbyPartyMembers`, `recordExpAward`, reparto en `onAttackedCreature` y doble `sendAnimatedText` en muertes mágicas y físicas. |
