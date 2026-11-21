# Feedback de curación y recuperación de maná

Al usar pociones/fluids de maná o vida, runas de curación o hechizos de curación/maná, el servidor ahora muestra el **valor real recuperado** (limitado por `healthmax` / `manamax`, no el valor teórico del hechizo o poción):

- **Texto animado sobre el personaje** (`sendAnimatedText`):
  - **Maná:** `+<N>` en azul (`23`, `#0099FF`).
  - **Vida:** `+<N>` en verde (`30`, `#00FF00`).
- **Mensaje en el chat / log de eventos** (`MSG_EVENT = 20`, mismo canal que `"You lose X hitpoints."` y `"You lose X mana."`), en inglés según [`SERVER_LANGUAGE.md`](SERVER_LANGUAGE.md):
  - Maná: `"You recovered <N> mana."`
  - Curación propia: `"You healed yourself for <N> hitpoint(s)."`
  - Curación sobre otro jugador o summon:
    - Quien recibe la cura (si es jugador): `"You were healed by <Caster> for <N> hitpoint(s)."`
    - Quien castea: `"You healed <Target> for <N> hitpoint(s)."`
- **Sin spam en 0:** si el personaje ya está al máximo de vida o maná (`valor real == 0`), el efecto visual del hechizo/poción se ejecuta igual (incluyendo quitar parálisis con curas o el `"Aaaaah..."` de mana fluid), pero no se muestra `"+0"` ni mensaje en el chat.

---

## Qué cubre

| Categoría | Elementos | Dónde se aplica |
|-----------|-----------|-----------------|
| **Pociones / Fluids** | Mana Fluid (`type 7`, hasta +100 MP), Strong Mana Potion (`type 14`, hasta +250 MP), Life Fluid (`type 10`, hasta +100 HP) | `server/YurOTS/ots/data/actions/scripts/fluids.lua` (solo Lua) |
| **Runas de curación** | Ultimate Healing Rune (`2273` / UH), Intense Healing Rune (`2265` / IH) | `server/YurOTS/ots/source/game.cpp` |
| **Spells de curación clásicos** | `exura`, `exura gran`, `exura vita`, `exura ico`, `exura san`, `exura sio`, `exura gran mas res` | `server/YurOTS/ots/source/game.cpp` |
| **Spells custom con C++ propio** | Seed of Life (`exura tera`, cura inmediata + floración diferida a los 3 s), Blood Ritual (`utamo mort`, cada tick de maná) | `server/YurOTS/ots/source/spells.cpp` |

> **Nota sobre monstruos:** las autocuraciones de monstruos (`exura`, `bograider_heal`, `k_heal_*`) siguen sin mostrar números flotantes verdes sobre el monstruo; el texto animado verde se muestra cuando el blanco o el lanzador es un jugador (incluye curar a tu propio summon con UH/IH/`exura gran mas res`).

---

## Por qué fue necesario tocar C++

1. **Bug histórico en `Game::creatureApplyDamage` (`game.cpp`):** todas las runas y hechizos de curación (`doTargetMagic` / `doAreaMagic` con `offensive = false`) pasan por `creatureApplyDamage` con `damage < 0`. El código original hacía:
   ```cpp
   creature->health = newhealth;
   ...
   outDamage = creature->health - newhealth; // siempre daba 0
   ```
   Por eso `creatureState.damage` quedaba en `0` y nunca salía texto animado ni mensaje de curación. Además, los scripts Lua de spells no tienen bindings para consultar HP ni enviar texto animado/mensajes.
2. **Hechizos con lógica directa en C++ (`spells.cpp`):** `exura tera` (`luaActionDoDelayedHeal` / `runDelayedHeal`) y `utamo mort` (`runBloodRitualTick`) modifican `health`/`mana` directamente en C++ sin pasar por `creatureApplyDamage`. Se respetaron intactos todos los mensajes que el cliente usa para prender/apagar íconos de estado ([`SPELLS_FEEDBACK.md`](SPELLS_FEEDBACK.md)).

> **Importante:** los cambios en `fluids.lua` entran al recargar/reiniciar el servidor; los cambios en `game.cpp` y `spells.cpp` **requieren recompilar el binario `yurots`** (en la ThinkPad o en el contenedor Docker correspondiente) para tener efecto en runas y spells.

---

## Archivos modificados

- `server/YurOTS/ots/data/actions/scripts/fluids.lua`
  - Mide `getPlayerMana(cid)` / `getPlayerHealth(cid)` antes y después de `doPlayerAddMana` / `doPlayerAddHealth` en Mana Fluid (`type 7`), Strong Mana Potion (`type 14`) y Life Fluid (`type 10`).
  - Envía `doSendAnimatedText` (`+N` azul `23` para maná, verde `30` para vida) y `doPlayerSendTextMessage(..., 20, ...)` solo cuando el valor real recuperado es `> 0`.
- `server/YurOTS/ots/source/game.cpp` *(sin tocar los cambios paralelos en `applyAmulets`)*
  - `Game::creatureApplyDamage`: guarda `oldhealth` (`int64_t`) antes de asignar `creature->health = newhealth` y devuelve `outDamage = -healed` (valor real limitado por `healthmax`).
  - `Game::creatureMakeMagic`: cuando `creatureState.damage < 0` y el lanzador o el blanco es jugador, envía `"+<healed>"` con `me->animationColor` (`GREEN = 30`); tras el loop de espectadores, notifica al lanzador `"You healed <Target> for <N> hitpoint(s)."` si curó a otro objetivo (incluso a distancia con `exura sio`).
  - `Game::CreateDamageUpdate`: agrega la rama `damage < 0` para enviar `"You healed yourself for <N> hitpoint(s)."` o `"You were healed by <Name> for <N> hitpoint(s)."` en `MSG_EVENT`.
- `server/YurOTS/ots/source/spells.cpp`
  - Helpers locales `sendSpellAnimatedText` y `sendSpellHealFeedback` en el namespace anónimo.
  - `luaActionDoDelayedHeal` y `runDelayedHeal` (`exura tera`): calcula el HP real curado, muestra `+<N>` verde, actualiza barra de vida a espectadores y manda los mensajes `MSG_EVENT` sin alterar los textos de íconos del cliente.
  - `runBloodRitualTick` (`utamo mort`): calcula el maná real recuperado por tick, muestra `+<N>` azul y manda `"You recovered <N> mana."` en `MSG_EVENT`.
- `docs/gameplay/HEAL_FEEDBACK.md` *(este documento)*.

---

## Cómo probarlo

> Primero compilar el binario C++ (`game.cpp` y `spells.cpp`) y reiniciar el servidor. Verificar con `python3 scripts/ot-probe.py <IP> 7171`.

1. **Mana Fluid (`type 7`) y Strong Mana Potion (`type 14`):**
   - Gastar algo de maná (por ejemplo lanzando `utevo lux` o `exura` hasta tener ~50 MP menos del máximo).
   - Usar un **Mana Fluid** (teórico 100): debe mostrar `+<real>` (ej. `+50`) en **azul** sobre el personaje y `"You recovered 50 mana."` en el chat, **no** `+100`.
   - Con >250 MP faltantes en un Sorcerer/Druid nivel 50+, usar una **Strong Mana Potion**: debe mostrar `+250` en azul y `"You recovered 250 mana."`.
   - Con maná al 100 %, beber un Mana Fluid: sale `"Aaaaah..."` y el efecto, **sin** `+0` ni mensaje.
2. **Life Fluid (`type 10`):**
   - Recibir daño (ej. >100 HP o solo 30 HP) y beber Life Fluid: debe mostrar `+100` (o `+30`) en **verde** y `"You healed yourself for <N> hitpoints."`.
3. **Runas de curación (UH `2273` e IH `2265`):**
   - Recibir daño (ej. 150 HP faltantes cuando la UH cura ~400+): usar UH sobre uno mismo → debe mostrar `+150` en **verde** y `"You healed yourself for 150 hitpoints."`.
   - Repetir con más daño (ej. 500 HP faltantes): debe mostrar el valor real curado (ej. `+380` en verde).
   - Usar UH/IH sobre otro jugador o summon herido: sale `+<N>` verde sobre el blanco; el lanzador lee `"You healed <Target> for <N> hitpoints."` y el aliado (si es jugador) lee `"You were healed by <Caster> for <N> hitpoints."`.
   - Usar UH/IH estando con vida llena: solo efecto mágico, sin `+0`.
4. **Spells de curación instantáneos:**
   - Probar `exura`, `exura gran`, `exura vita`, `exura ico` (Knight), `exura san` (Paladin) con vida incompleta: debe mostrar `+<real>` en verde y `"You healed yourself for <N> hitpoints."`.
   - Probar `exura sio "Aliado"` (Druid) y `exura gran mas res` (Druid) con un aliado herido: `+<real>` verde sobre cada curado y mensajes en ambos chats.
5. **Spells custom (`exura tera` y `utamo mort`):**
   - `exura tera "Aliado"` (Druid) sobre aliado herido: debe mostrar `+<real>` verde tanto en la cura inmediata como a los 3 s al florecer, y el ícono del cliente debe prenderse y apagarse normalmente.
   - `utamo mort` (Sorcerer) fuera de PZ con maná incompleto: cada tick de 2 s debe mostrar `+<real>` en azul (hasta `+60`) y `"You recovered <N> mana."`, y el ícono debe apagarse con `"Your blood ritual ends."`.
