# Zagan Test Items

Pack del directorio `Zagan+Square` más sprites custom en `zagan-test/custom-sprites/`: **54 items** (`20100`–`20153`).

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

Plan completo, restricciones (no tocar DP ni casas) y checklist:

→ [`../DEPLOY-PENDIENTE-VPS-JUL2026.md`](../DEPLOY-PENDIENTE-VPS-JUL2026.md)
