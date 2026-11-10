# Zagan Test Items

Pack del directorio `Zagan+Square` más sprites custom en `zagan-test/custom-sprites/`: **54+ items** (desde `20100`; el builder asigna ids nuevos al final).

Los 5 primeros (equipo base):

- `20100` vexon blade
- `20101` quarry ward
- `20102` morlen crest
- `20103` ashlar plate
- `20104` basalt greaves

Sprites custom adicionales:

- `20152` fox machina helmet
- `20153` chillan shield

Cada item hereda slot/atributos del prototipo OTB duplicado (arma, escudo, casco, armor, legs, runa, anillo, etc.).

## Scripts

- `scripts/install-zagan-test-env.sh`: reconstruye e instala el pack test
- `scripts/play-zagan-test-client.sh`: abre `client-local-zagan-test`
- `scripts/open-rme-zagan-test.sh`: abre `rme-zagan-test-root` con assets/items test
- `scripts/start-local-zagan-test.sh`: arranca el server local usando `items-zagan-test.otb/xml`

## Assets generados

- `zagan-test/manifest.json`
- `zagan-test/previews/`
- `server/YurOTS/ots/data/items/items-zagan-test.otb`
- `server/YurOTS/ots/data/items/items-zagan-test.xml`

## Aurora Blade — nueva (nov 2026)

Espada 1H rápida pensada para el hueco entre la bright sword y las rares del Crisol.

| Dato | Valor |
|------|-------|
| Prototipo | bright sword `2407` (atk 36 / def 30, 1H) |
| Velocidad | **1250 ms** por golpe (default `PLAYER_ATTACK_DELAY_MS` = 1333 ms; ~6 % más rápida) |
| Sprite | `zagan-test/custom-sprites/aurora_blade.png` (32×32, PNG con alpha) |
| Preview | `docs/items-and-map/img/aurora-blade.png` |
| Builder | entrada `aurora_blade.png` en `CUSTOM_ITEM_DEFS` |
| C++ | `AURORA_BLADE_ATTACK_DELAY_MS 1250` en `const76.h`; `Player::getAttackDelayMs()` la detecta por nombre porque el server id lo asigna el builder. Las gemas ruby siguen reduciendo el delay. |

**Pendiente:** correr `./scripts/install-zagan-test-env.sh` en la máquina con el pack Zagan para generar el OTB/DAT/SPR y probar in-game. El 32×32 vive en `devtools/zagan-test/custom-sprites/` (esa carpeta está gitignoreada; el PNG se agregó con `git add -f`).

## Aurora Shield — nueva (nov 2026)

Escudo kite que completa el set visual de la Aurora Blade.

| Dato | Valor |
|------|-------|
| Server id | **`20160`** (fijo en `CUSTOM_ITEM_SERVER_IDS`; el builder ya no lo reasigna) |
| Prototipo | guardian shield `2515` (def 30, shield) |
| C++ | Sin lógica extra: hereda defensa/stats del prototipo |
| Sprite | `zagan-test/custom-sprites/aurora_shield.png` (32×32, PNG con alpha) |
| Preview | `docs/items-and-map/img/aurora-shield.png` |
| Builder | entrada `aurora_shield.png` en `CUSTOM_ITEM_DEFS` |
| Drop | **Ice Monk**, dentro de la bolsa, `chance="250"` (0,25 %) |
| Look | Borde amarillo/dorado con degradé y campo morado radial, sin gema central ni el emblema/patrón "G" del guardian shield |

**Pendiente:** mismo build que la Aurora Blade: correr `./scripts/install-zagan-test-env.sh` en la máquina con el pack Zagan y probar in-game. El 32×32 está en `devtools/zagan-test/custom-sprites/` (gitignoreado; agregado con `git add -f`).

---

## Producción (VPS)

El OTB/XML Zagan ya está en producción desde el deploy `7312baf8`. La **lógica C++** (crimson helmet/wand, fury cape, medusa sword, sword of silence) y fixes asociados están **pendientes de commit/deploy**.

## Sword of Silence (`20139`) — local jul 2026

Renombrado desde `dawnbreak falchion`. Ataque **42** / defensa **30**.

| Pieza | Detalle |
|-------|---------|
| Efecto | 10% al pegar a un jugador: silencio 2–3 s |
| Bloquea | Spells hablados (`creatureSaySpell`) |
| No bloquea | Runas (`playerUseItemEx`) ni potions |
| Cooldown | 12 s por target (por atacante) |
| C++ | `ITEM_SWORD_OF_SILENCE`, `Creature::silenceTicks`, `applySwordOfSilence()` |
| OTB | `python3 scripts/patch-sword-of-silence-otb.py` |
| Loot | Fury (`data/monster/fury.xml`): rare drop `chance="400"` (fury cape sigue en `750`) |

**Solo local por ahora** — no deployar al VPS hasta autorización.

## Windsting Axe (`20130`) — local jul 2026

Renombrado desde `windsting bow` (era DIST 2H). Ahora **axe** 1H: ataque **43** / defensa **22**.

| Pieza | Detalle |
|-------|---------|
| Efecto | 20% al pegar a un jugador: drunk 6 s (`ICON_DRUNK`; el cliente 7.6 tuerce el walk) |
| C++ | `ITEM_WINDSTING_AXE`, `Creature::drunkTicks`, `applyWindstingDrunk()` |
| OTB | `python3 scripts/patch-windsting-axe-otb.py` |
| Loot | Rare `chance="400"`: Enraged Dwarf Guard, Enraged Orc Berserker, Enraged Behemoth, Enraged Black Knight |

**Solo local por ahora** — no deployar al VPS hasta autorización.

Plan completo, restricciones (no tocar DP ni casas) y checklist:

→ [`../_archive/DEPLOY-PENDIENTE-VPS-JUL2026.md`](../_archive/DEPLOY-PENDIENTE-VPS-JUL2026.md)
