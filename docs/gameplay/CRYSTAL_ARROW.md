# Crystal Arrow (2352) — throwable tipo spear + Blue Gem + hit chance

Documentación completa del trabajo de julio 2026 para fomentar paladines: convertir la crystal arrow en arma DIST reutilizable (como spear), imbuible con Blue Gem (20× Small Diamond), con mejor precisión que spear, y subir también el hit chance de spears.

> **TL;DR:** Crystal arrow = spear mejorada (atk 35, **85% hit**, no se gasta) + Blue Gem hasta **5 stacks** de attack speed. Spears pasan de 50% → **70% hit**. Flechas/bolts siguen en 90%.

---

## 0. Motivación

- Meta de distancia en 7.6 favorece **bow/crossbow + ammo** (90% hit).
- Spears thrown tenían **50% miss** → frustrante y poco atractivo para pallys.
- La crystal arrow (`2352`) existía en OTB como ammo rota (atk 0); se reutilizó como identidad de progresión pally.

---

## 1. Crystal Arrow — arma

| Campo | Valor |
|-------|--------|
| Server ID | `2352` (`ITEM_CRYSTAL_ARROW`) |
| Nombre | crystal arrow |
| Peso | 0.7 oz |
| Tipo OTB | `ITEM_GROUP_WEAPON` + `WEAPON2` |
| Weapon | `DIST`, `amuType=NONE` (no necesita arco) |
| Shoot | `OTB_DIST_ARROW` |
| Attack | **35** (spear = 30) |
| Defence | 0 |
| Stackable | **No** (imbue limpio en un solo ítem) |
| Consumo | **No** (`removeDistItem` solo gasta `AMO`) |
| Hit chance | **85%** (`CRYSTAL_ARROW_HIT_CHANCE`) |

### Antes / después OTB

| | Antes | Después |
|---|--------|---------|
| Group | `AMMUNITION` (4) | `WEAPON` (3) |
| Attr | `AMU2` arrow, atk 0 | `WEAPON2` DIST, atk 35 |
| Uso | No útil (ammo rota) | Throwable en mano, como spear |

Parche: `scripts/patch-crystal-arrow-otb.py` → `items.otb` y `items-zagan-test.otb`.

---

## 2. Blue Gem — imbue de velocidad (×5)

La gema de **20× Small Diamond** en 7.6 se llama **Blue Gem** (`2158`). Antes solo se vendía a Parived; ahora imbuye crystal arrow.

| Campo | Valor |
|-------|--------|
| Gema | Blue Gem `2158` |
| Origen | Tonka: `exchange diamond` (20× `2145`) |
| Target | Crystal arrow equipada (mano) |
| Stacks | 5 (`AID` 9070–9074) |
| Efecto | +5% attack speed por stack (máx. +25%) |
| Fail | 50% (igual yellow/violet/ruby/emerald) |
| Big Ruby | **No** aplica a crystal arrow |

```
Small Diamond ×20 ──Tonka──► Blue Gem ──Use──► Crystal Arrow AID 9070…9074
                                                      │
                                                      ▼
                                            getAttackDelayMs()
```

| Stacks | AID | Speed | Delay (ms) |
|--------|-----|-------|------------|
| 0 | 0 | +0% | 1333 |
| 1/5 | 9070 | +5% | 1266 |
| 2/5 | 9071 | +10% | 1200 |
| 3/5 | 9072 | +15% | 1133 |
| 4/5 | 9073 | +20% | 1066 |
| 5/5 | 9074 | +25% | 1000 |

`PLAYER_ATTACK_DELAY_MS` = 1333. Prioridad en `getAttackDelayMs()`: Crimson Wand → Nightglass → **Crystal Arrow** → Big Ruby → default.

---

## 3. Hit chance (misses)

Lógica en `Player::getWeaponDamage()` (`player.cpp`):

| Arma | Antes | Ahora | Constante |
|------|-------|-------|-----------|
| Ammo (arrow/bolt/burst…) | 90% | 90% | hardcode |
| **Spear** (`2389`) | 50% | **70%** | `SPEAR_HIT_CHANCE` |
| **Crystal arrow** (`2352`) | 50% (thrown genérico) | **85%** | `CRYSTAL_ARROW_HIT_CHANCE` |
| Otras thrown (star, knife, stone…) | 50% | 50% | hardcode |

Orden de precisión: ammo 90% ≥ crystal 85% > spear 70% > otras thrown 50%.

Constantes en `const76.h`. Look in-game muestra el % en spear y crystal arrow.

---

## 4. Archivos tocados (sesión completa)

| Archivo | Cambio |
|---------|--------|
| `scripts/patch-crystal-arrow-otb.py` | Parche OTB ammo→weapon DIST |
| `data/items/items.otb` | Crystal arrow weapon atk 35 |
| `data/items/items-zagan-test.otb` | Idem |
| `source/const76.h` | `ITEM_CRYSTAL_ARROW`, AID 9070–9074, hit chances |
| `source/creature.h` / `creature.cpp` | `imbueCrystalArrowSpeed` |
| `source/player.cpp` | Imbue speed + hitchance spear/crystal |
| `source/item.cpp` | Descripciones Blue Gem, crystal, spear |
| `data/actions/scripts/gem_imbue.lua` | Blue Gem → crystal arrow ×5 |
| `data/actions/actions.xml` | Action `itemid="2158"` |
| `data/npc/scripts/tonka.lua` | Help: blue on crystal arrows |
| `data/monster/enraged hero.xml` | Loot raro `2352` chance 450 |
| `data/monster/furious amazon.xml` | Loot raro `2352` chance 300 |
| `source/game.cpp` | `isRareEquipmentLootItem` incluye crystal arrow |
| `docs/gameplay/GEMS.md` | Blue Gem ya no es “solo vender” |
| `docs/INDEX.md` / `AGENTS.md` | Índice + tabla de items |

---

## 5. Cómo usarlo in-game

1. Equipar **crystal arrow** en la mano (no en ammo).
2. Atacar a distancia → animación flecha, **no se gasta**, ~85% hit.
3. Tonka: 20 small diamonds → Blue Gem.
4. Usar Blue Gem con la flecha equipada → stack de speed (50% fail).
5. Spears normales: ~70% hit (antes 50%).

Mensajes de imbue:

- *"Equip a crystal arrow to imbue it."*
- *"Crystal arrow already has 5/5 speed imbuements."*
- *"Crystal arrow imbued with speed (3/5): +15% (1133ms per hit)."*

Look ejemplo (3/5):

```
You see a crystal arrow (Atk:35 Def:0, +15% speed).
It weighs 0.7 oz.
A throwable crystal missile (spear-like, 85% hit). Imbue with a blue gem for up to 5 attack speed stacks.
Imbued: +15% attack speed (1133ms per hit, 3/5).
```

---

## 6. Rebuild / prueba

Tras tocar `creature.h` → **`make clean && make`** (build parcial puede segfaultear):

```bash
docker compose -f docker-compose.prod.yml run --rm yurots bash -c 'cd /app/YuroTS/ots/source && make clean && make -j2 yurots'
docker compose -f docker-compose.prod.yml up -d yurots
python3 scripts/ot-probe.py 127.0.0.1 7171
```

Checklist:

1. Crystal arrow: DIST, no melee, no se consume.
2. Hit rate percibido mejor que spear; spear mejor que stars/knives.
3. Blue Gem sin flecha → cancel; con flecha → stack / fail 50%.
4. 5/5 bloquea más gemas; desequipar vuelve delay a 1333 ms.
5. Spear look muestra 70% hit.

---

## 7. Loot raro

| Monstruo | Archivo | Chance | Notas |
|----------|---------|--------|-------|
| **Enraged Hero** | `enraged hero.xml` | `450` (~0.45%) | Dentro del backpack `1987`; farm distance endgame |
| **Furious Amazon** | `furious amazon.xml` | `300` (~0.30%) | Dentro del backpack; % más bajo porque se farmea mucho |

Ambos usan el mismo formato que Nightglass en Serpent Spawn (`chance="…"` en loot raro). Crystal arrow está en `isRareEquipmentLootItem()` → highlight en mensaje de loot.

---

## 8. Pendiente / no hecho

- Quest chest / NPC vendor: no definido.
- Deploy VPS: **preguntar** antes; requiere rebuild C++ + OTB + monstruos.
- No se renombró Blue Gem a “White Gem” (no existe ese ítem en OTB 7.6).

---

## 9. Referencias cruzadas

- Sistema de gemas: [`GEMS.md`](GEMS.md)
- Patrón similar de speed ×5: Nightglass dagger (Big Ruby, AID 9060–9064) en `SESION_EDITOR_MAPA_JUL2026.md`
- Spears reutilizables: `Player::removeDistItem()` + `spearlosechance = 100000` en `config.lua`
