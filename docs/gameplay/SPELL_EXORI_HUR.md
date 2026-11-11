# Spell: `exori hur` (Whirlwind Throw)

Rehecho de cero en nov 2026 con la idea de las versiones nuevas (8.x en adelante): el knight **lanza su
arma de melee** contra el blanco marcado y el daño depende del arma y del skill, no del magic level.

Leer también: [`SPELL_RUNTIME.md`](SPELL_RUNTIME.md) (carga Lua / bindings), [`SPELL_EXHAUSTION.md`](SPELL_EXHAUSTION.md)
(exhaust ofensivo 2 s), [`SPELL_EXORI_CON.md`](SPELL_EXORI_CON.md) (el de paladin, hecho igual).

## Specs

| Atributo | Valor |
|----------|-------|
| words / nombre | `exori hur` / Whirlwind Throw |
| maglv / mana | 3 / 40 |
| vocación | Knight (`id="4"`, incluye Elite Knight) |
| daño | físico, al blanco de la battle list (`doTargetMagic`, con línea de vista) |
| alcance | 5 casillas (`max(dx, dy) ≤ 5`), mismo piso |
| necesita | espada, hacha o maza en una mano (arcos, escudos o sin arma: no se lanza) |
| mínimo | `nivel / 5 + (skill + ataque del arma) / 3` |
| máximo | `nivel / 5 + skill + ataque del arma` |
| proyectil | espada → cuchillo arrojadizo (8), hacha → estrella arrojadiza (7), maza → roca (11) |
| exhaust | ofensivo normal (2 s) |

La fórmula es la de TFS 1.x. El skill es el del arma que tiene en la mano (sword, axe o club).
Ejemplo a nivel 100: espada de ataque 30 con skill 90 → 60 a 140.

Si falla (sin arma de melee, sin blanco, otro piso, fuera de alcance), `onCast` devuelve `false` y no
gasta maná.

En 7.6 no existe el proyectil del arma girando de las versiones nuevas. Para tenerlo habría que agregar
proyectiles al cliente (como el pack "ice", ver [`CLIENT_EFFECTS.md`](CLIENT_EFFECTS.md)) y repartir el
cliente.

## Antes (jul 2026)

Daño `(nivel + magic level) × 1.0–1.8`, siempre con el proyectil de roca y sin mirar el arma.

## Archivos

| Archivo | Qué |
|---------|-----|
| `server/YurOTS/ots/data/spells/instant/exori hur.lua` | El hechizo |
| `server/YurOTS/ots/source/spells.cpp` / `spells.h` | `getAttackedCreaturePos`, `getPlayerWeapon`, `getPlayerSkill` |
| `server/YurOTS/ots/data/spells/spells.xml` | maglv, mana, vocación |

**Necesita el binario compilado con `getPlayerWeapon` y `getPlayerSkill`** (nov 2026). Con un binario
viejo el hechizo da error de Lua al lanzarse y no hace nada.

## Probar

1. Knight con espada, hacha y maza: marcar un monstruo a 3–5 casillas y decir `exori hur`. Cambia el
   proyectil según el arma.
2. Sin arma, con un arco o sin blanco: no pasa nada y no gasta maná.
3. A 6 casillas o detrás de una pared: no se lanza.
