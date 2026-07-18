# Spell: `exori hur` (Whirlwind Throw) — target a distancia (jul 2026)

Cambio del strike direccional a **golpe físico al target de la battle list**, rango 5.

Leer también: [`SPELL_RUNTIME.md`](SPELL_RUNTIME.md) (carga Lua / bindings), [`SPELL_EXHAUSTION.md`](SPELL_EXHAUSTION.md) (exhaust ofensivo 2 s).

---

## Specs actuales

| Atributo | Valor |
|----------|--------|
| words | `exori hur` |
| XML name | Whirlwind Throw |
| maglv / mana | 3 / 40 |
| vocación | Knight (`id="4"`, incluye Elite Knight) |
| attackType | `ATTACK_PHYSICAL` |
| modo | **target** vía `doTargetMagic` (no área) |
| target | `creature->attackedCreature` (battle list) |
| rango | **5** Chebyshev (`max(dx,dy) ≤ 5`), mismo piso |
| LoS | sí (`creatureThrowRune` / `canThrowObjectTo`) |
| proyectil | `NM_ANI_LARGEROCK` |
| hit / damage effect | `NM_ME_DRAW_BLOOD` / `NM_ME_HIT_AREA` |
| daño min / max | `(level + maglv) * 1.0` / `(level + maglv) * 1.8` |
| exhaust | ofensivo normal (~2000 ms); **sin** `reduceExhaustion` |

Sin target, fuera de rango, otro piso, o target = self → `onCast` retorna `false` (no gasta mana).

`spells.xml` **no** cambió (sigue maglv/mana/voc iguales).

---

## Archivos tocados

| Archivo | Qué |
|---------|-----|
| `server/YurOTS/ots/data/spells/instant/exori hur.lua` | Rewrite: target + rango 5 |
| `server/YurOTS/ots/source/spells.h` | Declara `luaActionGetAttackedCreaturePos` |
| `server/YurOTS/ots/source/spells.cpp` | Registra `getAttackedCreaturePos` + implementación |

**Rebuild C++ obligatorio** si el binding es nuevo (sin él el Lua falla al castear).

---

## Binding nuevo: `getAttackedCreaturePos(cid)`

Devuelve tabla `{x,y,z}` del target actual del caster, o `nil` en cada eje si no hay `attackedCreature` / criatura inválida.

Reutilizable por otros instants que necesiten el target de battle list (monstruos y players). No confundir con `getPosition(name)`, que solo resuelve **players** por nombre (usado por `exura sio`).

---

## Cómo revertir

### Opción A — solo el spell (rápido, deja el binding)

Restaurar el Lua viejo. El binding C++ puede quedar (inofensivo si nadie lo llama).

```bash
git checkout HEAD -- "server/YurOTS/ots/data/spells/instant/exori hur.lua"
# o pegar el script de la sección "Script anterior" abajo
```

Reiniciar `yurots` (sin rebuild si solo tocás Lua).

### Opción B — revert completo (Lua + C++)

1. Restaurar `exori hur.lua` (script anterior abajo).
2. En `spells.h`: quitar `luaActionGetAttackedCreaturePos`.
3. En `spells.cpp`: quitar el `lua_register(..., "getAttackedCreaturePos", ...)` y toda la función `luaActionGetAttackedCreaturePos`.
4. Rebuild + restart:

```bash
docker compose -f docker-compose.prod.yml run --rm yurots bash -c 'cd /app/YuroTS/ots/source && make -j2 yurots'
docker compose -f docker-compose.prod.yml up -d yurots
python3 scripts/ot-probe.py 127.0.0.1 7171
```

Si el cambio ya está en un commit propio:

```bash
git revert <commit-sha>
# luego rebuild si el revert toca C++
```

---

## Script anterior (backup para revert)

Strike direccional con `doAreaMagic`. Bug conocido: el `4` (sur) estaba a **5 SQM** al sur; N/O/E a 1 SQM.

```lua
    area = {
    				{0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0},
    				{0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0},
    				{0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0},
    				{0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0},
    				{0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0},
    				{0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0},
    				{0, 0, 0, 0, 0, 0, 0, 2, 0, 3, 0, 0, 0, 0, 0, 0, 0},
    				{0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0},
    				{0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0},
    				{0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0},
    				{0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0},
    				{0, 0, 0, 0, 0, 0, 0, 0, 4, 0, 0, 0, 0, 0, 0, 0, 0},
    				{0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0}
    }

    attackType = ATTACK_PHYSICAL
    needDirection = true
    areaEffect = NM_ME_HIT_AREA
    animationEffect = NM_ANI_LARGEROCK

    hitEffect = NM_ME_DRAW_BLOOD
    damageEffect = NM_ME_HIT_AREA
    animationColor = RED
    offensive = true
    drawblood = true

    ExoriHurObject = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, 0, 0)

    function onCast(cid, creaturePos, level, maglv, var)
    centerpos = {x=creaturePos.x, y=creaturePos.y, z=creaturePos.z}
    ExoriHurObject.minDmg = (level * 1 + maglv * 1) * 1.0
    ExoriHurObject.maxDmg = (level * 1 + maglv * 1) * 1.8

    return doAreaMagic(cid, centerpos, needDirection, areaEffect, area, ExoriHurObject:ordered())
    end
```

---

## Checklist de prueba

1. Rebuild binario + `docker compose -f docker-compose.prod.yml up -d yurots`
2. `python3 scripts/ot-probe.py 127.0.0.1 7171`
3. Knight con ML ≥ 3, mana ≥ 40, **target en battle list**
4. Target a 1–5 SQM con LoS → proyectil rock + daño
5. Sin target / >5 SQM / sin LoS → no castea
6. Comparar vs `exori con` (sigue siendo strike 1 SQM direccional)

---

## Relacionado

| Spell | Rol |
|-------|-----|
| `exori con` | Brutal Strike — 1 SQM delante, Paladin/RP (`voc 3`), mana 30 |
| `exori` / `exori gran` | Área alrededor del caster |
| `exura sio` | Target por nombre (`getPosition`); solo players |
