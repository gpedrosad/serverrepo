# Monstruos Furiosos

Al matar un monstruo elegible, **5.3% de chance** de que reviva al instante convertido en versión furiosa:

| Variante | Probabilidad | Grito |
|----------|-------------|-------|
| **Angry** | 4% | "GRAAAH! VOLVI MAS ENOJADO!" |
| **Furious** | 1% | "RAAAH! AHORA SI ESTOY FURIOSO!" |
| **Enraged** | 0.3% | "MI FURIA NO TIENE LIMITE!" |

> **Histórico:** hasta 2026-07-04 era 13% total (10% / 2% / 1%). Ajuste en `game.cpp` → `chooseRageVariantName`.

### ¿Qué cambia?
- **Stats**: nivel, HP, daño, armadura, defensa, velocidad suben progresivamente
- **Experiencia**: 2x-4x más que el original
- **Loot**: mejorado (más gemas, platinum, items raros)
- **Nunca huyen** (`runonhealth=0`)
- **Mismo look**, ataques e inmunidades que el original

### Detalles
- Aplica a **99 familias** de monstruos: las **42 históricas** (Demon, Dragon Lord, Behemoth, Warlock, etc., jun 2026) más las **57 nuevas** de jul–nov 2026 (ver abajo)
- No spawnan en zonas PZ
- Las variantes que aparecen **al matar** un monstruo normal son criaturas adicionales — no afectan el respawn del spawnpoint base
- Las variantes **colocadas en el mapa** (`test-spawn.xml`, nombres `Angry`/`Furious`/`Enraged`) sí respawnean por `spawn.cpp` y demoran **4×** el `spawntime` del XML (ver `docs/gameplay/RESPAWN_SYSTEM.md`)
- El sistema es puro C++ (sin Lua), se gatilla automáticamente al morir cualquier monstruo

### Inmunidad a magic fields (jul 2026)

Las variantes `Angry` / `Furious` / `Enraged` son **inmunes a magic fields** (energy, fire, poison, etc.). Esto cubre:

- Fields que ya estaban en el tile cuando el monstruo entra o cae sobre él.
- Fields que un player tira encima mientras el monstruo está quieto.
- Fields que aparecen bajo el monstruo por spells o AoE.

**Implementación:** `server/YurOTS/ots/source/game.cpp` → `Game::thingMoveInternal(...)`, bloque "Magic Field in destiny field". Antes de llamar a `fieldItem->getDamage(creatureMoving)`, se chequea si `creatureMoving` es un `Monster` cuyo nombre matchea el helper `isRageMonsterName()` (prefijo `Angry ` / `Furious ` / `Enraged `). Si matchea, no se aplica el daño.

**Nota:** el pathfinding de monsters ya evita tiles con fields (`Monster::tileHasMagicField` en `monster.cpp:119`), por lo que en condiciones normales los rage variants no caminan hacia fields. El fix en `game.cpp` cubre los casos residuales (spawn sobre field, teletransporte, push por spell).

**Sin recompilar** este cambio no toma efecto — requiere rebuild del binario `yurots`.

### Familias nuevas (nov 2026)

Los monstruos agregados después de las 42 familias originales no tenían variantes: al morir no
podían revivir furiosos porque `trySpawnRageMonster` no encontraba `Angry <Nombre>` en
`monsters.xml`. Se generaron las **57 familias nuevas** (171 XML) con las mismas fórmulas por
tramo de experiencia que las históricas:

- Custom / zonas: Black Dragon, Frost Dragon, Blue Elf Arcanist, Drowned Sailor, Ice Monk,
  Ice Spider, Tide Priest, Hellhound, Court Mage, Dark Hydra, Emerald Scarab, Root Colossus,
  Imperial Squire, Imperial Archer, Imperial Hero, Serpent Spawn, Orc Berserker Pot Thrower.
- Cyborgs (19 nov 2026): Metal Dragon, Metal Hydra y Metal Demon ([METAL_MONSTERS.md](METAL_MONSTERS.md)).
- Tibia 8.60: piratas ×4, bárbaros ×4, chakoyas ×3, Frost Giant/Giantess, Ice Golem,
  Crystal Spider, Bog Raider, Tortoise, Thornback Tortoise, Mammoth, Blood Crab, quara ×5,
  Cyclops Drone/Smith, Wyrm, elementales de tierra/agua, Zombie, Vampire Bride, Worker Golem,
  Undead Gladiator, Nightstalker, mutados ×4, Wyvern.

Quedan afuera a propósito: jefes (Ashen Lord, The Fallen Emperor, los 7 del Crisol, Wrath),
trainers/dummy, mascotas (Husky), crías (hatchlings) y los élites custom (Fury).

**Generador:** `python3 scripts/monsters/rage-variants.py` audita qué familias base no tienen
las tres variantes (y falla si falta alguna de las nuevas); `--write` escribe los XML y los
registra en `monsters.xml`; `--write --only "Wyrm" "Zombie"` limita a algunos. Es idempotente.

Tramos (mismos que las históricas; nivel/maglevel, armor/defense, speed, HP, exp, daño):

| Exp base | Nivel/mag | Armor/def | Speed | HP | Exp | Daño |
|---|---|---|---|---|---|---|
| < 50 | +4/+8/+12 | +2/+4/+6 | +10/16/22 | ×1.45/1.8/2.2 | ×1.75/2.2/2.8 | ×1.3/1.6/1.9 |
| 50–149 | +5/+10/+15 | +3/+5/+7 | +12/18/24 | ×1.55/1.95/2.35 | ×1.9/2.4/3.05 | ×1.4/1.75/2.1 |
| 150–699 | +7/+13/+19 | +4/+6/+8 | +14/20/26 | ×1.7/2.1/2.55 | ×2.1/2.7/3.4 | ×1.5/1.9/2.3 |
| 700–1999 | +9/+16/+24 | +5/+7/10 | +16/22/30 | ×1.85/2.3/2.8 | ×2.3/3.0/3.8 | ×1.6/2.05/2.5 |
| ≥ 2000 | +12/+20/+30 | +6/+8/12 | +18/24/34 | ×2.0/2.5/3.05 | ×2.5/3.3/4.2 | ×1.7/2.2/2.7 |

Los tres valores de cada celda son Angry / Furious / Enraged. El daño escala todos los
`mindamage`/`maxdamage` de `<attacks>` (melee, distance, runas y curas), igual que en las
variantes históricas. Los hechizos con `kit="1"` (monstruos 8.60) mantienen el escalón del
monstruo base: el daño del kit lo define el Lua, no el `<attack>`. Las gemas van por tramo con
las chances base, igual que en las variantes históricas.

> **Bug conocido (nov 2026):** `monsters.cpp` → `getRageGemChancePercent()` compara contra
> `"angry "` / `"furious "` / `"enraged "` en minúsculas, pero `MonsterType::name` se carga tal
> cual del XML (`"Angry Dragon"`, Title Case). Por eso el ×2.4 (furious) y ×3.2 (enraged) de
> gemas que describía `docs/gameplay/GEMS.md` **no se aplica**, y el fallback de gem para los
> rage trolls tampoco. Las chances efectivas son las del XML. Arreglarlo requiere tocar C++ y
> recompilar (decisión de balance pendiente).
