# Spell: `exori vis hur` (Energy Strike Hur) — jul 2026

Strike de energía a **target de battle list** (rango 5), para Sorcerer/Druid.
Daño como `exori vis`, visual como **Heavy Magic Missile**, targeting como `exori hur`.

Dependencias: [`SPELL_EXORI_HUR.md`](SPELL_EXORI_HUR.md) (`getAttackedCreaturePos`), [`SPELL_RUNTIME.md`](SPELL_RUNTIME.md), [`SPELL_EXHAUSTION.md`](SPELL_EXHAUSTION.md).

---

## Specs

| Atributo | `exori vis` | `exori vis hur` (nuevo) |
|----------|-------------|-------------------------|
| words | `exori vis` | `exori vis hur` |
| maglv / mana | 3 / 20 | **4 / 30** |
| vocación | Sorc + Druid (1, 2) | igual (MS/ED vía `promoted=1`) |
| modo | área 1 SQM direccional | **target** `doTargetMagic` |
| target | dirección facing | battle list (`getAttackedCreaturePos`) |
| rango | 1 | **5** Chebyshev + LoS |
| attackType | `ATTACK_ENERGY` | igual |
| proyectil | ninguno | **`NM_ANI_FIRE`** (HMM) |
| hit / damage | explosion + energy | igual HMM (`NM_ME_EXPLOSION_DAMAGE` / `NM_ME_ENERGY_DAMAGE`) |
| animationColor | RED | **LIGHT_BLUE** (HMM) |
| daño min / max | `(level+maglv)*0.8` / `(level+maglv)*1.0` | **igual** |
| exhaust | `reduceExhaustion` (baja a ~1 s) | **igual** |

Sin target / fuera de rango / sin LoS / self → no castea (no gasta mana).

---

## Archivos

| Archivo | Acción |
|---------|--------|
| `server/YurOTS/ots/data/spells/instant/exori vis hur.lua` | **nuevo** |
| `server/YurOTS/ots/data/spells/spells.xml` | entrada Instant nueva |
| `docs/gameplay/SPELL_EXORI_VIS_HUR.md` | este doc |
| `docs/INDEX.md` / `AGENTS.md` | enlace |

**No toca C++** por sí solo. Requiere que `getAttackedCreaturePos` ya esté en el binario (cambio de `exori hur`). Si el binding no está compilado, el cast falla en Lua.

Si `LEARN_SPELLS` está activo, los players deben **aprender** el spell nuevo.

---

## Cómo revertir

```bash
# 1) Quitar script
rm "server/YurOTS/ots/data/spells/instant/exori vis hur.lua"

# 2) En spells.xml, borrar la línea:
# <spell name="Energy Strike Hur" words="exori vis hur" .../>

# 3) (opcional) quitar enlaces en INDEX.md / AGENTS.md / este doc

# 4) Reiniciar yurots — sin rebuild C++ si solo se quita este spell
docker compose -f docker-compose.prod.yml up -d yurots
python3 scripts/ot-probe.py 127.0.0.1 7171
```

O con git (si ya está commiteado en un commit propio):

```bash
git revert <commit-sha>
# o restaurar solo esos paths desde el commit anterior
```

No hace falta tocar `getAttackedCreaturePos` al revertir solo este spell (`exori hur` sigue usándolo).

---

## Checklist de prueba

1. Binario con `getAttackedCreaturePos` + restart `yurots`
2. `python3 scripts/ot-probe.py 127.0.0.1 7171`
3. Sorc o Druid ML ≥ 4, mana ≥ 30, target en battle list a 1–5 SQM con LoS
4. Debe verse proyectil tipo HMM + daño energy
5. Sin target / >5 SQM → no castea
6. Exhaust reducido como `exori vis` (más rápido que un SD)

---

## Relacionado

| Spell | Rol |
|-------|-----|
| `exori vis` | Energy Strike melee direccional |
| `exori hur` | Whirlwind Throw físico target rango 5 |
| HMM rune | Misma animación (`NM_ANI_FIRE` + energy hit) |
