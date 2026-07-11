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
- Aplica a **42 familias** de monstruos (Demon, Dragon Lord, Behemoth, Warlock, etc.)
- No spawnan en zonas PZ ni PvP Arena
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
