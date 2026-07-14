# Magic Wall — duración y decay

Doc de la runa **Magic Wall** (`2293` → field `1498`) y del timer de decay de fields/sólidos mágicos.

**Estado jul 2026:** duración objetivo **15 segundos**. Cambio local; **no deployar al VPS hasta autorización explícita**.

---

## Comportamiento esperado

| Qué | Valor |
|-----|--------|
| Runa | `2293` (4 charges en `spells.xml`) |
| Field en el tile | item id `1498` |
| Duración desde el lanzamiento | **15 s** (`durationTicks = 15000`) |
| Conjuro | `adevo grav tera` (crea la runa; no coloca el wall) |
| Relanzar MW sobre otra | reemplaza el field y **reinicia** el timer a 15 s |

Relacionado: `Desintegrate` destruye `1498` / wild growth `1497` — ver [`DESINTEGRATE_RUNE.md`](DESINTEGRATE_RUNE.md). `Destroy Field` **no** quita MW.

---

## Cómo funciona el timer (YurOTS)

1. Lua (`magic wall.lua`) llama `doTargetGroundMagic(..., durationTicks, itemid, transformCount)`.
2. C++ (`SpellScript::luaActionDoTargetGroundSpell` + `internalLoadTransformVec`) arma un `TransformMap`:
   - key = `itemid` (`1498`)
   - `ti.first` = `durationTicks` (ms)
3. Se crea un `MagicEffectItem` con ese mapa. Su `getDecayTime()` lee `durationTicks` del mapa (**no** el `decayTime` del OTB para el countdown de la runa).
4. Al colocar el field en el tile, `Game::startDecay(magicItem)` lo encola.
5. `Game::checkDecay` corre cada `DECAY_INTERVAL` ms y resta ese intervalo a cada bloque. Cuando el tiempo llega a ≤ 0, el item decae / desaparece.

### Redondeo crítico en `startDecay`

```cpp
if(dtime < DECAY_INTERVAL)
    dtime = DECAY_INTERVAL;
dtime = (dtime / DECAY_INTERVAL) * DECAY_INTERVAL;
```

Cualquier duración que **no** sea múltiplo de `DECAY_INTERVAL` se redondea **hacia abajo**.

| `DECAY_INTERVAL` | `durationTicks` | Duración real |
|------------------|-----------------|---------------|
| 10000 (histórico) | 15000 | **10 s** (roto) |
| 10000 | 20000 | 20 s |
| 5000 (actual) | 15000 | **15 s** |

Por eso no alcanza con tocar solo el Lua si el interval es 10 s.

---

## Bugs que había (antes del fix)

1. **Duración 20 s** en Lua (`durationTicks = 20000`), no 15.
2. **`DECAY_INTERVAL = 10000`**: poner 15 s en Lua habría dado 10 s efectivos por el redondeo.
3. **Relanzar MW sobre MW existente**: el código hacía `transform()` in-place y **no** llamaba `startDecay` de nuevo. Como `isDecaying` seguía `true`, un segundo cast heredaba el tiempo restante del wall viejo.

---

## Fix aplicado (local, pendiente de deploy)

| Archivo | Cambio |
|---------|--------|
| `server/YurOTS/ots/data/spells/runes/magic wall.lua` | `durationTicks = 15000` |
| `server/YurOTS/ots/source/game.h` | `DECAY_INTERVAL` `10000` → `5000` |
| `server/YurOTS/ots/source/game.cpp` | Al pisar un field existente: remove + `FreeThing` + crear field nuevo + `startDecay` (timer completo) |
| `server/YurOTS/ots/source/magic.h` | `getDecayTime()` marcado `virtual` (override correcto vs `Item`) |

### Side effect de `DECAY_INTERVAL = 5000`

Afecta **todos** los items que usan `startDecay` / `checkDecay` (corpses, fields fire/energy/poison, splashes, etc.): el tick de decay es más frecuente (cada 5 s en vez de 10 s). Las duraciones que ya eran múltiplos de 10 s siguen igual en total; la granularidad intermedia es mayor.

Si algo “desaparece raro” tras el rebuild, sospechar primero este interval antes de tocar data de jugadores.

---

## Cómo probar (local)

1. Rebuild C++ + restart: `docker compose -f docker-compose.prod.yml up -d yurots` (o rebuild `make` si corresponde).
2. `python3 scripts/ot-probe.py 127.0.0.1 7171`
3. In-game: tirar Magic Wall en sqm libre → cronometrar hasta que desaparezca → debe ser ~15 s (± un tick de 5 s según alineación del scheduler).
4. Tirar MW, esperar ~5–8 s, tirar otra en el **mismo** tile → el nuevo wall debe vivir ~15 s desde el segundo cast, no el resto del primero.

**No deployar al VPS** hasta que el usuario lo autorice. Deploy: `DEPLOY_I_READ_README=yes ./scripts/deploy-vps.sh`.

---

## Si “se rompe” después — checklist

| Síntoma | Qué mirar |
|---------|-----------|
| Wall dura ~10 s | ¿`DECAY_INTERVAL` volvió a `10000`? ¿`durationTicks` no es múltiplo del interval? |
| Wall dura ~20 s | ¿Lua sigue en `20000` o no se recargó el script (hace falta restart; spells no hot-reload)? |
| Wall no desaparece | ¿`startDecay` no se llama? ¿`getDecayTime()` devuelve 0? ¿`canDecay` / `isRemoved`? |
| Relanzar no renueva tiempo | ¿Volvió el path `transform()` sin recrear el item? Ver bloque de fields en `game.cpp` (cerca de `getMagicItem`). |
| Corpses / fire fields raros | Side effect de `DECAY_INTERVAL` 5 s — no asumir que el bug es solo MW. |
| Solo Lua cambiado, C++ viejo | Rebuild obligatorio: `game.h` / `game.cpp` no aplican sin recompilar el binario. |

---

## Archivos clave

- `server/YurOTS/ots/data/spells/runes/magic wall.lua`
- `server/YurOTS/ots/data/spells/spells.xml` (registro rune / conjuro)
- `server/YurOTS/ots/source/spells.cpp` (`luaActionDoTargetGroundSpell`, `internalLoadTransformVec`)
- `server/YurOTS/ots/source/magic.cpp` / `magic.h` (`MagicEffectItem::getDecayTime`, `decay`)
- `server/YurOTS/ots/source/game.cpp` / `game.h` (`startDecay`, `checkDecay`, `DECAY_INTERVAL`, colocación de fields)

OTB: el item `1498` tiene decay propio en `items.otb`, pero el countdown de la runa lo manda el `TransformMap` de Lua, no ese valor OTB.
