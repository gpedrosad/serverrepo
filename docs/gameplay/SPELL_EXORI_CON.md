# Spell: `exori con` (Ethereal Spear)

Hecho de cero en nov 2026 con la idea de las versiones nuevas (8.x en adelante): el paladin **lanza una
lanza etérea** contra el blanco marcado. El daño depende del skill de distancia y no gasta munición.
Reemplaza a "Brutal Strike", que era un golpe en la casilla de adelante (en las versiones nuevas, Brutal
Strike es `exori ico`, de knight).

Leer también: [`SPELL_RUNTIME.md`](SPELL_RUNTIME.md), [`SPELL_EXORI_HUR.md`](SPELL_EXORI_HUR.md) (el de knight,
hecho igual).

## Specs

| Atributo | Valor |
|----------|-------|
| words / nombre | `exori con` / Ethereal Spear |
| maglv / mana | 4 / 25 |
| vocación | Paladin (`id="3"`, incluye Royal Paladin) |
| daño | físico, al blanco de la battle list (`doTargetMagic`, con línea de vista) |
| alcance | 7 casillas a los costados y 5 arriba y abajo (lo que entra en la pantalla 7.6), mismo piso |
| mínimo | `nivel / 5 + distancia × 0.7` |
| máximo | `nivel / 5 + distancia + 5` |
| proyectil | `NM_ANI_ENCHANTED_SPEAR` (16): la lanza azul que brilla de la [Enchanted Spear](ENCHANTED_SPEAR.md) |
| efecto al pegar | sangre + chispa de energía |
| exhaust | ofensivo normal (2 s) |

La fórmula es la de TFS 1.x. Ejemplo a nivel 100 con distancia 90: 83 a 115.

Si falla (sin blanco, otro piso, fuera de alcance), `onCast` devuelve `false` y no gasta maná.

Con un cliente que no tiene el proyectil 16 el daño llega igual, pero no se ve la lanza.

## Archivos

| Archivo | Qué |
|---------|-----|
| `server/YurOTS/ots/data/spells/instant/exori con.lua` | El hechizo |
| `server/YurOTS/ots/source/spells.cpp` / `spells.h` | `getAttackedCreaturePos`, `getPlayerSkill` |
| `server/YurOTS/ots/data/spells/spells.xml` | nombre Ethereal Spear, maglv 4, mana 25 |

**Necesita el binario compilado con `getPlayerSkill`** (nov 2026).

## Probar

1. Paladin: marcar un monstruo a 5–7 casillas a un costado y decir `exori con`. Se ve la lanza azul.
2. Sin blanco, a 6 casillas arriba o detrás de una pared: no pasa nada y no gasta maná.
3. Con más skill de distancia pega más.
