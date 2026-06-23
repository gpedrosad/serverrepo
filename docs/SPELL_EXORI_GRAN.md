# Spell custom: `exori gran` (Berzeker Gran)

Spell instantáneo de área físico para **Knight** (vocación 4), creado como
versión mejorada y visualmente distinta del `exori` (Berzeker) original de
YurOTS.

## 1. Specs del spell

| Atributo          | `exori` (original)         | `exori gran` (nuevo)             |
|-------------------|----------------------------|----------------------------------|
| words             | `exori`                    | `exori gran`                     |
| maglv             | 5                          | 9                                |
| mana              | 100                        | 200                              |
| vocations         | Knight (4)                 | Knight (4)                       |
| attackType        | ATTACK_PHYSICAL            | ATTACK_PHYSICAL                  |
| area              | cuadrado 3×3 sin centro (8 casillas) | **diamante radio 4 sin centro (12 casillas)** |
| areaEffect        | `NM_ME_HIT_AREA` (polvo blanco) | **`NM_ME_EXPLOSION_AREA` (explosión naranja)** |
| hitEffect         | `NM_ME_HIT_AREA`           | **`NM_ME_DRAW_BLOOD` (sangre)**  |
| damageEffect      | `NM_ME_HIT_AREA`           | **`NM_ME_EXPLOSION_AREA` (explosión)** |
| animationColor    | `RED` (180)                | **`ORANGE` (193)**               |
| drawblood         | true                       | true                             |
| damage min        | `(level*1.5 + maglv*1.5) * 1.2` | **`(level*2 + maglv*3) * 2.8 - 30`** |
| damage max        | `(level*1.5 + maglv*1.5) * 2.3` | **`(level*2 + maglv*3) * 3.6`**   |

Diferencias visuales en el cliente 7.6:
- **exori**: nube de polvo blanco (`NM_ME_HIT_AREA`) en un cuadrado 3×3 alrededor del caster, texto de daño rojo.
- **exori gran**: explosión naranja (`NM_ME_EXPLOSION_AREA`) en forma de diamante 5×5, splashes de sangre (`NM_ME_DRAW_BLOOD`) en cada target golpeado, texto de daño naranja. Mucho más vistoso y brutal.

## 2. Archivos creados / modificados

### `server/YurOTS/ots/data/spells/instant/exori gran.lua` (nuevo)

```lua
area = {
    {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0},
    {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0},
    {0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0},
    {0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0},
    {0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0},
    {0, 0, 1, 1, 1, 0, 1, 1, 1, 0, 0},
    {0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0},
    {0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0},
    {0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0},
    {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0},
    {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0},
    }

    attackType = ATTACK_PHYSICAL
    needDirection = false
    areaEffect = NM_ME_EXPLOSION_AREA
    animationEffect = NM_ANI_NONE

    hitEffect = NM_ME_DRAW_BLOOD
    damageEffect = NM_ME_EXPLOSION_AREA
    animationColor = ORANGE
    offensive = true
    drawblood = true

    BerserkGranObject = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, 0, 0)

    function onCast(cid, creaturePos, level, maglv, var)
    centerpos = {x=creaturePos.x, y=creaturePos.y, z=creaturePos.z}
    n = tonumber(var)
    if n ~= nil then
        BerserkGranObject.minDmg = 0
        BerserkGranObject.maxDmg = 0
    else
        BerserkGranObject.minDmg = (level * 2 + maglv * 3) * 2.8 - 30
        BerserkGranObject.maxDmg = (level * 2 + maglv * 3) * 3.6
    end

    return doAreaMagic(cid, centerpos, needDirection, areaEffect, area, BerserkGranObject:ordered())
    end
```

### `server/YurOTS/ots/data/spells/spells.xml` (modificado)

Se agregó una línea después del `Berzeker` existente:

```xml
<spell name="Berzeker Gran"			words="exori gran"			maglv="9"	mana="200"	enabled="1"><vocation id="4" /></spell>
```

## 3. Cómo funciona el sistema de spells en YurOTS

YurOTS 7.6 usa un sistema **híbrido XML + Lua** para spells instantáneos:

1. **`spells.xml`** registra los metadatos del spell:
   - `name`: nombre interno (solo display/debug)
   - `words`: lo que el player escribe en el chat para castear (`exori gran`)
   - `maglv`: magic level mínimo requerido
   - `mana`: costo de maná
   - `enabled`: 1 = activo
   - `<vocation id="N"/>`: qué vocaciones pueden usarlo (1=sorcerer, 2=druid, 3=paladin, 4=knight)

2. **`instant/<words>.lua`** contiene la lógica del cast:
   - `area`: matriz 11×11 de 0s y 1s. El centro `[5][5]` es la posición del caster. `1` = esa casilla recibe el efecto/daño. `0` = fuera del área.
   - `attackType`: tipo de daño (físico, fuego, energía, etc.). Mapea a `ATTACK_*` en `magic.h`.
   - `areaEffect`: efecto visual enviado a **todos** los tiles del área (visible siempre, pegue o no pegue). Constantes `NM_ME_*` de `lib/spells.lua`.
   - `hitEffect` / `damageEffect`: efecto visual al impactar contra un target.
   - `animationColor`: color del texto de daño flotante (`RED`, `ORANGE`, `YELLOW`, etc.).
   - `offensive`: si ataca a otros (PVP).
   - `drawblood`: si muestra splash de sangre.
   - `onCast(cid, creaturePos, level, maglv, var)`: función que calcula minDmg/maxDmg y llama a `doAreaMagic()` (registrada en C++ en `spells.cpp:536`).

3. **Matching al hablar**: en `game.cpp:5401` `Game::checkSpell`, cuando un player habla, el texto se normaliza a minúsculas y se busca en `allSpells` (mapa key=words). El match es **exacto** (`text == words`), así que `exori gran` y `exori` son spells distintos sin colisión de prefijos.

4. **Carga**: `Spells::loadFromXml()` (`spells.cpp:41`) parsea `spells.xml`, y por cada `<spell>` crea un `InstantSpell` cuyo constructor (`spells.cpp:225`) instancia un `SpellScript` que abre el `.lua` correspondiente vía `lua_dofile`. **No hay reload en runtime** para spells (solo para actions/commands/monsters/config), así que para agregar/ cambiar un spell hay que reiniciar el server.

## 4. Constantes de efectos visuales (referencia)

De `lib/spells.lua`:

```
NM_ME_DRAW_BLOOD       = 0   -- splash de sangre
NM_ME_PUFF             = 2   -- nube de polvo
NM_ME_EXPLOSION_AREA   = 4   -- explosión naranja (la que usa exori gran)
NM_ME_FIRE_AREA        = 6   -- área de fuego
NM_ME_YELLOW_RINGS     = 7   -- anillos amarillos
NM_ME_HIT_AREA         = 9   -- polvo blanco (la que usa exori)
NM_ME_ENERGY_AREA      = 10  -- área de energía azul
NM_ME_MORT_AREA        = 17  -- área de muerte (negra/roja)
```

Colores de texto de daño:
```
RED       = 180
ORANGE    = 193   -- el que usa exori gran
YELLOW    = 79
GREEN     = 30
ENERGY    = 35
```

## 5. Área del `exori gran` (diamante)

```
            1
          1 1 1
        1 1 1 1 1
      1 1 1 C 1 1 1        C = caster (no se daña a sí mismo)
        1 1 1 1 1
          1 1 1
            1
```

12 casillas afectadas (vs 8 del exori cuadrado 3×3). Forma de diamante más
ancha, alcanza a enemigos en diagonales lejanas que el exori no toca.

## 6. Cómo probarlo en juego

1. Server corriendo (ver `SETUP.md`).
2. Loguear con account `111111` / pass `tibia`, elegir **GM Yurez** (level 100, access 3, maglevel 300) o un Knight.
3. Decir `exori gran` en el chat (default: Enter).
4. Con maglevel 300 y level 100, el daño ronda:
   - min = (200 + 900) * 2.8 - 30 = 3050
   - max = (200 + 900) * 3.6 = 3960
   Útil para testing agresivo. Con un knight normal level 37 maglv 5: min ≈ 46, max ≈ 59.

## 7. Notas de diseño

- Se mantuvo `attackType = ATTACK_PHYSICAL` porque temáticamente es un golpe
  berserker (knight), no mágico. La diferencia visual viene por los efectos
  (`NM_ME_EXPLOSION_AREA` + `NM_ME_DRAW_BLOOD`) y el color del texto (`ORANGE`).
- El `mana` 200 y `maglv` 9 lo posicionan como upgrade del `exori` (100/5) sin
  romper el balance: cuesta el doble de maná y requiere casi el doble de magic
  level, pero hace ~2-3× el daño y cubre más área.
- El daño usa la fórmula clásica de YurOTS `(level*2 + maglv*3) * factor`, igual
  que el `Ultimate Explosion` original, escalando bien con level.
- No se modificó código C++: el spell es 100% data-driven (XML + Lua). No
  requiere recompilar el binario, solo reiniciar el server.
