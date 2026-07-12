# Spell runtime — carga, safeCast y restauración de runas (jul 2026)

Documento del incidente/fix `33557889` (*fix(spells): restaurar runas rotas y safeCast anti-crash*).

Leer **antes** de agregar una runa/spell nueva o de tocar `spells.cpp` / `spells.xml`.

## Síntoma

Al castear ciertas runas (sobre todo **Soulfire** / `adevo res flam`, item `2308`) el server podía **crashear** o fallar en runtime. La causa raíz no era el daño del hechizo: faltaban scripts `.lua` cuyo nombre coincidiera con el `name` del XML (tras `tolower`), y el C++ llamaba `getSpellScript()->castSpell(...)` sin chequear si el script había cargado.

## Cómo carga YurOTS un spell

| Tipo | Clave en `spells.xml` | Path del script |
|------|------------------------|-----------------|
| Instant | `words="..."` | `data/spells/instant/<words>.lua` |
| Runa | `name="..."` (se guarda en **minúsculas**) | `data/spells/runes/<name en minúsculas>.lua` |

Reglas críticas:

1. El loader hace `tolower` del `name` de la runa. **Soulfire** → archivo `soulfire.lua`, no `soul fire.lua`.
2. Si el archivo no existe o no carga, `Spell`/`SpellScript` quedan con `loaded=false`.
3. El cast real exige `function onCast(...)` en el `.lua`.

Validación rápida (local):

```bash
# Debe reportar 0 problems para enabled=1
python3 - <<'PY'
import re
from pathlib import Path
datadir = Path('server/YurOTS/ots/data')
text = (datadir/'spells/spells.xml').read_text()
no_c = re.sub(r'<!--.*?-->', '', text, flags=re.S)
problems, ok = [], 0
for m in re.finditer(r'<(spell|rune)\s+([^>]+)/?>', no_c):
    tag, attrs_s = m.group(1), m.group(2)
    attrs = dict(re.findall(r'(\w+)="([^"]*)"', attrs_s))
    if attrs.get('enabled','0') != '1':
        continue
    if tag == 'spell':
        path = datadir/'spells/instant'/f"{attrs.get('words','')}.lua"
    else:
        path = datadir/'spells/runes'/f"{(attrs.get('name') or '').lower()}.lua"
    if not path.exists() or not re.search(r'function\s+onCast\s*\(', path.read_text(errors='replace')):
        problems.append(str(path))
    else:
        ok += 1
print(f'ok={ok} problems={len(problems)}')
for p in problems: print(p)
PY
```

## `SpellScript::safeCast` (anti-crash)

Antes: `game.cpp` / `monster.cpp` hacían `spell->getSpellScript()->castSpell(...)` directo → nullptr / script no cargado = crash.

Ahora todos los casts pasan por:

```cpp
SpellScript::safeCast(spell, creature, pos, var);
```

`safeCast` (`spells.cpp`):

1. Rechaza `spell` null o no `isLoaded()`.
2. Rechaza script null o no `isLoaded()`.
3. Solo entonces llama `castSpell`.

`castSpell` ya fallaba cerrado si faltaba `onCast` o si `lua_pcall` fallaba (ver también `DESINTEGRATE_RUNE.md`). Con `safeCast` el fallo se queda en **cast fallido** (no consume / no crashea), no en segfault.

Call sites:

- `game.cpp` — `creatureSaySpell`, `playerUseItemEx`, `playerUseBattleWindow`
- `monster.cpp` — ataques por runa/instant del monstruo

## Runas / scripts restaurados en el fix

| Nombre XML | Item / id | Script | Binding C++ (si aplica) |
|------------|-----------|--------|-------------------------|
| Soulfire | `2308` | `runes/soulfire.lua` | `doTargetExMagic` (DoT fuego) |
| Paralyze | `2278` | `runes/paralyze.lua` | `doParalyze` — 60s, speed 40 |
| Antidote | `2266` | `runes/antidote.lua` | `doCurePoison` |
| Animate Dead | `2316` | `runes/animate dead.lua` | `doAnimateDead` → skeleton |
| Convince Creature | `2290` | `runes/convince creature.lua` | `doConvinceCreature` |
| Chameleon | `2291` | `runes/chameleon.lua` | `doChameleon` — ~200s |
| Anchor | `2296` | `runes/anchor.lua` | `doAnchorRoot` — root 1s (`rootTicks`) |
| o fire field | `5017` (monster) | `runes/o fire field.lua` | área ground fire |
| old widow pox | `5032` (monster) | `runes/old widow pox.lua` | (ya existía; pasó de instant a rune) |

Detalle de Anchor: [`ANCHOR_RUNE.md`](ANCHOR_RUNE.md).

### Instant placeholder deshabilitado

`utani slow` (nombre XML “Paralyze”) estaba vacío/roto. El Paralyze real es la **runa 2278**.

- `spells.xml`: `enabled="0"` + comentario.
- Script stub: `instant/utani slow.lua` (`onCast` → `false`) por si alguien re-habilita el entry por error.

### Monster spell → rune

`old widow pox` dejó de ser instant monster (`words=...`) y pasó a rune id `5032`, alineado con el path `runes/old widow pox.lua`.

## Bindings Lua nuevos (`spells.h` / `spells.cpp`)

Registrados en el constructor de `SpellScript`:

| Lua | C++ |
|-----|-----|
| `doAnchorRoot` | `luaActionDoAnchorRoot` |
| `doCurePoison` | `luaActionDoCurePoison` |
| `doAnimateDead` | `luaActionDoAnimateDead` |
| `doConvinceCreature` | `luaActionDoConvinceCreature` |
| `doChameleon` | `luaActionDoChameleon` |
| `doParalyze` | `luaActionDoParalyze` |

Patrones comunes: mismo piso, `canThrowObjectTo`, puff en fallo, PZ / immunities donde corresponde.

## Checklist al tocar spells

1. Nombre del `.lua` = `tolower(name)` (runas) o `words` exactos (instants).
2. `function onCast` presente.
3. Si el efecto no se puede hacer solo en Lua → binding C++ + `lua_register`.
4. Rebuild del binario si tocaste `spells.cpp` / `.h` / `game.cpp` / `monster.cpp` (`make clean && make` si cambió un header compartido).
5. `docker compose -f docker-compose.prod.yml up -d yurots`
6. `python3 scripts/ot-probe.py 127.0.0.1 7171`
7. Probar in-game al menos: Soulfire (`2308`), Paralyze (`2278`), Antidote (`2266`).

## Archivos clave

| Archivo | Rol |
|---------|-----|
| `data/spells/spells.xml` | Catálogo enabled / ids / words |
| `data/spells/runes/*.lua` | Scripts de runas |
| `data/spells/instant/*.lua` | Scripts de instants |
| `source/spells.cpp` / `spells.h` | Loader, `safeCast`, bindings |
| `source/game.cpp` | Cast jugador / uso de runa |
| `source/monster.cpp` | Cast monstruo |
| `source/creature.h` | `rootTicks` (Anchor) |

## Estado de verificación (local, post-pull)

- Inventario XML↔Lua: **150** entries `enabled=1` con archivo + `onCast`; **0** faltantes.
- Docker local no estaba levantado al documentar → no se pudo `ot-probe` ni prueba in-game en esa sesión.
- El binario `source/yurots` local puede estar desfasado respecto al C++ nuevo: hace falta rebuild antes de probar casts.
