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

## Sprites redibujados (nov 2026)

Los sprites originales del pack se perdieron: `~/Downloads/Zagan+Square` no está en ninguna máquina,
el `.dat` Zagan solo se repartía por el updater del VPS (ya no existe) y el cliente de
`gpedrosad/clienteretro` nunca los tuvo (su `Tibia.dat` es el base). Se redibujaron de cero **solo
los 17 items con uso real** (lógica en C++, loot, El Crisol o premium):

| Grupo | Server ids |
|-------|-----------|
| Armas raras de El Crisol | 20100, 20110, 20112, 20121, 20122, 20138, 20154 |
| Efecto propio en C++ | 20105 medusa sword, 20139 sword of silence, 20130 windsting axe, 20114 fury cape, 20123 crimson wand, 20137 nightglass dagger |
| Premium | 20131 experience recovery rune, 20132 training extension rune |
| Cofres de quest | 20113 crimson helmet y 20123 crimson wand: cofres de la guarida de la Isla del Hielo Eterno (antes, final del Alice Maze) |
| Sin forma de conseguirlo | 20126 train wand (en el OTB se llama "violet sunstone" y es tipo anillo) |

- Script: `scripts/client-rme/draw_zagan_items.py` (Pillow + numpy; en la Mac mini usar `python3.11`).
  Dibuja cada pieza a 4x con volumen y luz y la reduce a 32x32.
- `--preview hoja.png` para mirarlos; `--apply devtools/rme/rme-client-760` los escribe en el
  `Tibia.dat`/`Tibia.spr` canónico, en el client id que cada item ya tiene en `items-zagan-test.otb`
  (el OTB no cambia), con los flags del `.dat` de un item vanilla del mismo tipo. Re-aplicar
  reemplaza los sprites en el lugar (sprites 11259–11275).
- Los íconos de las runas en la web (`web/assets/wiki/items/2013[12].png`,
  `web/assets/premium/2013[12]-small*.png`) salen del mismo script.
- Los otros 40 items Zagan no tienen uso (ni loot, ni NPC, ni lógica) y siguen mostrando el sprite
  del item vanilla cuyo client id ocupan. Ocho están en la sala de exhibición del mapa
  (x 142–146, y 47–55, z 6). Pendiente: sacarlos del OTB y del mapa.
- Para que lo vean los jugadores falta publicar este `Tibia.dat`/`Tibia.spr` en el cliente de descarga.

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

## Aurora Axe — nueva (nov 2026)

Hacha 1H rápida que completa el set Aurora junto a la Blade y el Shield.

| Dato | Valor |
|------|-------|
| Prototipo | knight axe `2430` (atk 33 / def 21, 1H) |
| Velocidad | **1250 ms** por golpe (default `PLAYER_ATTACK_DELAY_MS` = 1333 ms; ~6 % más rápida) |
| Sprite | `zagan-test/custom-sprites/aurora_axe.png` (32×32, PNG con alpha) |
| Preview | `docs/items-and-map/img/aurora-axe.png` |
| Builder | entrada `aurora_axe.png` en `CUSTOM_ITEM_DEFS` |
| C++ | `AURORA_AXE_ATTACK_DELAY_MS 1250` en `const76.h`; `Player::getAttackDelayMs()` la detecta por nombre. Las gemas ruby siguen reduciendo el delay. |
| Set | Aurora Blade + Aurora Axe + Aurora Shield |

**Pendiente:** mismo build que la Aurora Blade: correr `./scripts/install-zagan-test-env.sh` en la máquina con el pack Zagan y probar in-game. El 32×32 está en `devtools/zagan-test/custom-sprites/` (gitignoreado; agregado con `git add -f`).

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

## Producción (histórico)

El OTB/XML Zagan estuvo en producción (el VPS, que ya no existe) desde el deploy `7312baf8`. Hoy no hay producción; el servidor es el de la ThinkPad.

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

**Solo local por ahora** — pendiente: probar en la ThinkPad (deploy solo con OK de Gonzalo).

## Windsting Axe (`20130`) — local jul 2026

Renombrado desde `windsting bow` (era DIST 2H). Ahora **axe** 1H: ataque **43** / defensa **22**.

| Pieza | Detalle |
|-------|---------|
| Efecto | 20% al pegar a un jugador: drunk 6 s (`ICON_DRUNK`; el cliente 7.6 tuerce el walk) |
| C++ | `ITEM_WINDSTING_AXE`, `Creature::drunkTicks`, `applyWindstingDrunk()` |
| OTB | `python3 scripts/patch-windsting-axe-otb.py` |
| Loot | Rare `chance="400"`: Enraged Dwarf Guard, Enraged Orc Berserker, Enraged Behemoth, Enraged Black Knight |

**Solo local por ahora** — pendiente: probar en la ThinkPad (deploy solo con OK de Gonzalo).

Plan completo, restricciones (no tocar DP ni casas) y checklist:

→ [`../_archive/DEPLOY-PENDIENTE-VPS-JUL2026.md`](../_archive/DEPLOY-PENDIENTE-VPS-JUL2026.md)
