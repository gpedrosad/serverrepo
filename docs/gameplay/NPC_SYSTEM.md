# Sistema de NPCs (Lua)

Cómo están armados los NPCs del servidor, qué hace cada componente compartido, cómo crear uno nuevo y cómo probar cambios sin levantar el servidor.

Relacionado: [`NPC_CONFIRMATION.md`](NPC_CONFIRMATION.md) (confirmación de compra/venta del lado C++), [`SELLER_FLUIDS.md`](SELLER_FLUIDS.md), [`DAILY_TASK.md`](DAILY_TASK.md), [`SAND_CLOCK.md`](SAND_CLOCK.md).

---

## 1. Cómo los carga el servidor

| Pieza | Dónde | Qué hace |
|-------|-------|----------|
| Definición | `data/npc/<nombre>.xml` | Nombre, outfit y `script="data/npc/scripts/<script>.lua"` |
| Ubicación | `data/world/npc.xml` | Dónde aparece cada NPC (no van dentro del OTBM) |
| Motor | `source/npc.cpp` | Un **estado Lua propio por NPC**. Registra la API (§5), hace `dofile` de `lib/npc.lua` y después del script |
| Biblioteca | `data/npc/scripts/lib/npc.lua` + `lib/npc/*.lua` | Componentes compartidos (§2) |
| Script | `data/npc/scripts/<script>.lua` | Solo lo propio del NPC: textos, catálogos, lógica |

El C++ llama a estos callbacks del script: `onCreatureSay(cid, type, msg)`, `onThink()`, `onCreatureAppear(creature)`, `onCreatureDisappear(cid, pos)`, `onThingMove`, `onCreatureTurn`, `onCreatureChangeOutfit`. **Nadie los escribe a mano**: los arma `npcDefine{...}` (§3).

Como cada NPC tiene su propio estado Lua, las globales (`focus`, `talk_state`, ...) son de ese NPC y no chocan con las de otro. Dos NPCs con el mismo script (Nimral y Fargum, los dos Dark Rodo) tampoco comparten estado.

**Dialecto:** Lua 5.1 (Docker usa `liblua5.1`; el `Makefile` prefiere LuaJIT si está instalado, que es compatible con 5.1). No usar `goto`, `//` ni `math.mod` (en LuaJIT no existe; usar `math.fmod`). `table.getn` y `#` funcionan en los dos.

---

## 2. Componentes compartidos (`data/npc/scripts/lib/`)

`lib/npc.lua` es solo el cargador; cada componente vive en `lib/npc/`. Todas las funciones son globales (los scripts las llaman directo).

| Componente | Funciones | Para qué |
|------------|-----------|----------|
| `npc/core.lua` | `msgcontains(txt, palabra)`, `getDistanceToCreature(cid)`, `moveToPosition`, `moveToCreature`, `selfGotoIdle` | Coincidencia de palabras completas y distancia al jugador |
| `npc/intents.lua` | `npcIsGreeting`, `npcIsFarewell`, `npcIsYes`, `npcIsNo`, `npcIsHelp`, `npcMatchesAny(msg, claves)` | Qué quiso decir el jugador. Acepta inglés y español (`hi/hola/buenas`, `bye/adios/chau`, `yes/si/sí/dale`, `help/ayuda/list/precios`...) |
| `npc/conversation.lua` | `npcHandleMessage`, `npcBeginConversation`, `npcTouchConversation`, `npcEndConversation`, `npcResetState`, `npcOnThink`, `npcOnCreatureDisappear`, `npcHandlePendingYesNo` | Atiende a **un jugador a la vez** (`focus`). Saludo / "estoy ocupado" / despedida, cierre por inactividad o por alejarse, preguntas sí/no |
| `npc/catalog.lua` | `npcTryCatalogBuyQuantity`, `npcTryCatalogSell`, `npcTryCatalogReply`, `npcFindCatalogEntry`, `npcFindCatalogBuyEntry`, `npcParseBuyQuantity` | Tiendas por catálogo con cantidad ("5 ham"), fluidos, runas con cargas, respuestas por tema |
| `npc/text.lua` | `npcTrim`, `npcResolveGoldAmount(cid, texto, origen)`, `npcFormatPrice` | Montos de oro ("10000", "all", "todo"; origen `'money'` = encima, otro = banco) y precios ("2.5k") |
| `npc/define.lua` | `npcDefine{...}`, `npcCatalogHandler{...}` | Arma los callbacks del NPC a partir de una descripción |
| `daily_task.lua` | `dailyTask*` | Sistema de contratos diarios (lo usa el Huntmaster; ver `DAILY_TASK.md`) |

### Ciclo de una conversación

```
jugador: "hi"    -> npcHandleMessage: focus libre y a < 4 sqm  -> saluda, focus = cid   ('greet')
otro: "hola"     -> focus ocupado                              -> "One moment..."      ('busy')
jugador: "5 ham" -> es el focus                                -> onMessage(cid, msg)  ('focused')
jugador: "bye"   -> despedida, cancela trade pendiente, limpia estado                  ('bye')
sin hablar 30 s  -> onThink: "Next please..." y cierra
se aleja > 5 sqm -> onThink: "See you later!" y cierra
```

---

## 3. `npcDefine{...}`

Cada script termina con un `npcDefine`. Campos:

| Campo | Tipo | Uso |
|-------|------|-----|
| `greet` | string o `function(cid)` | Saludo. Obligatorio salvo que uses `onSay` |
| `busy` | string o `function(cid)` | Si ya atiende a otro (default `"One moment, <name>! I am helping someone else."`) |
| `bye` | string o `function(cid)` | Despedida (default `"Bye, <name>! Come back anytime."`) |
| `onMessage` | `function(cid, msg)` | Mensaje del jugador que está atendiendo. `msg` ya viene en minúsculas |
| `onGreet` | `function(cid)` | Al empezar la charla (p. ej. limpiar pendientes, Banker) |
| `onLeave` | `function(cid)` | El jugador atendido desaparece (antes del cierre estándar) |
| `idleTimeout`, `idleMessage` | número, string | Timeout de la charla (default 30 s y "Next please...") |
| `state` | tabla | Globales propias con valor inicial (opcional; también se pueden declarar arriba del script) |
| `onSay` | `function(cid, msg)` | **Reemplaza** todo el manejo de mensajes (Fargum/Nimral: saludo con lista de destinos) |
| `onThink` | `function()` | **Reemplaza** el think estándar (Chronos: fases de la sala) |
| `onAppear`, `onDisappear` | funciones | Reemplazan los callbacks de aparecer/desaparecer (Chronos) |

`npcCatalogHandler{help, helpKeys, buys, sells, topics, maxQty}` devuelve un `onMessage` de tienda estándar, en este orden: ayuda → compra con cantidad → venta → respuesta por tema.

### Formato de catálogo

```lua
{keys = {'brown bread', 'bread'}, itemid = 2691, unitPrice = 8}          -- compra, precio por unidad
{keys = {'sudden death', 'sd'}, itemid = 2268, unitPrice = 250, runeCharges = 1}
{keys = {'mana fluid', 'mana'}, itemid = 2006, fluidSubtype = 7, unitPrice = 100}
{keys = {'blank rune'}, itemid = 2260, unitPrice = 10, itemQuantity = true}
{keys = {'royal helmet'}, itemid = 2498, price = 30000}                  -- venta (el NPC paga)
{keys = {'helmets'}, reply = 'I buy royal (30k), ...'}                   -- tema: solo responde
```

Si dos claves coinciden gana la que aparece primero en el mensaje y, a igual posición, la más larga ("strong mana" antes que "mana"). Antes de mostrar una compra se revisa que haya lugar en la mochila.

---

## 4. Recetas

**Tienda nueva** (`data/npc/scripts/flores.lua`):

```lua
-- Flora (flores). Tienda simple con cantidad ("3 rose").
FLORES_HELP = 'Rose 20gp, tulip 15gp. Say any amount, e.g. "3 rose".'
FLORES_BUYS = {
	{keys = {'rose', 'roses'}, itemid = 2744, unitPrice = 20},
	{keys = {'tulip', 'tulips'}, itemid = 2745, unitPrice = 15},
}

npcDefine{
	greet = function(cid) return 'Hi ' .. creatureGetName(cid) .. '! ' .. FLORES_HELP end,
	onMessage = npcCatalogHandler{help = FLORES_HELP, buys = FLORES_BUYS},
}
```

Después: `data/npc/flora.xml` con `script="data/npc/scripts/flores.lua"`, ubicarla en `data/world/npc.xml` y reiniciar el servidor.

**NPC con pregunta sí/no** (patrón de Orlan, Tonka, Fargum):

```lua
talk_state = 0

local function onMessage(cid, msg)
	if talk_state == 1 then
		if npcHandlePendingYesNo(cid, msg, function() --[[ hacer la acción ]] end) then
			talk_state = 0
		end
		return
	end
	if msgcontains(msg, 'promotion') then
		selfSay('It costs 20,000 gp. Do you want it? (yes or si)')
		talk_state = 1
	end
end

npcDefine{greet = 'Hello! Say "promotion".', onMessage = onMessage}
```

`npcResetState` (despedida, timeout, alejarse) vuelve `talk_state` a 0 y borra `pending_exchange` / `pending_travel` si el script los usa.

---

## 5. API del C++ disponible en los scripts

Registrada en `source/npc.cpp` (`NpcScript`). Ojo con el tipo de argumento y de retorno:

| Recibe **nombre** del jugador (no cid) | `getPlayerLevel`, `getPlayerGuildStatus`, `getPlayerGuildName`, `setPlayerGuild*`, `clearPlayerGuild` |
|---|---|
| Devuelven **booleano** | `pay`, `isPremium`, `isPromoted`, `isMonster`, `cancelPendingTrade` |
| Devuelven número | `getPlayerMoney`, `getPlayerBankBalance`, `getPlayerStorageValue` (-1 si no existe), `getPlayerItemCount`, `getPlayerFreeSlots`, `doSummonCreature` (0 si falla), `getTopCreature` (0 si no hay) |

Compra/venta (`buy`, `buyFluidQty`, `buyRuneQty`, `buyItemQty`, `buyItemBackpack`, `buyFluidBackpack`, `sell`, `sellFluid`, `sellBundle`) dejan la operación pendiente y el C++ pide la confirmación (ver `NPC_CONFIRMATION.md`). Otras: `selfSay`, `creatureGetName`, `creatureGetPosition`, `travelPlayerTo`, `setPlayerMasterPos`, `setPlayerVocation`, `doPlayerAddItem`, `doPlayerRemoveItem`, `doPlayerDeposit/Withdraw/TransferMoney`, `doSendMagicEffect`, `doRemoveCreature`, `doPlayerAddMana`, `learnSpell`, `foundNewGuild`.

---

## 6. NPCs actuales

| NPC | Script | Dónde (`npc.xml`) | Qué hace | Tipo |
|-----|--------|-------------------|----------|------|
| Lector | `food.lua` | `127,49,7` | Comida a 8gp | Tienda (catálogo) |
| Perac | `bows.lua` | `144,54,5` | Arcos, munición, lanzas | Tienda (catálogo) |
| Sally | `rookeq.lua` | `74,220,7` | Equipo inicial | Tienda (catálogo) |
| Mad | `loot.lua` | `145,51,6` | Compra armas y armaduras | Tienda de venta (catálogo) |
| Obi | `furniture.lua` | `173,46,7` | Muebles a 500gp | Tienda con temas |
| Dufi | `aol.lua` | `128,51,5` | Anillos, scarf, AOL | Tienda |
| Dark Rodo ×2 | `runes.lua` | `129,50,6`, `207,71,7` | Runas, bp de runas, fluidos, wands/rods | Tienda |
| Seller ×2 | `seller.lua` | `145,50,7`, `208,80,7` | Suministros, bp de fluidos, armas, equipo knight; compra vials | Tienda |
| Parived | `parived.lua` | `133,58,7` | Compra gemas y diamantes | Tienda de venta |
| Tonka | `tonka.lua` | `140,50,7` | Canje 20 gemas chicas → 1 grande | Sí/no |
| Orlan | `promote.lua` | `127,49,4` | Promoción (nivel 20, 20k) | Sí/no |
| The Oracle | `oracle.lua` | `96,207,6` | Vocación y salida de Rookgaard | Diálogo por etapas |
| Banker | `banker.lua` | `128,55,6` | Balance, depósito, retiro, transferencia | Sí/no |
| Guild Master | `guild.lua` | `129,51,5` | Guilds: fundar, invitar, rangos, nicks | Diálogo por etapas |
| Huntmaster | `huntmaster.lua` | `138,53,6` | Contratos diarios (`lib/daily_task.lua`) | Sí/no |
| Fargum, Nimral ×6 | `boat.lua` | `171,66,7` y 6 muelles | Viajes en barco | `onSay` propio |
| Chronos | `chronos.lua` | `338,387,6` | Reloj de Arena: fases y spawns de la sala | `onThink` propio |
| Bounty Master | `bounty_master.lua` | — | Contratos de caza con el banco | **Inactivo** |

**Bounty Master está inactivo:** no está en `npc.xml` y llama a `getPlayerBountyByName` y `doPlayerPlaceBounty`, que `npc.cpp` no registra. Para activarlo hay que agregar esas funciones en C++ (recompilar) y ubicarlo en el mapa.

---

## 7. Probar cambios sin levantar el servidor

```bash
python3 scripts/npc/run_npc_tests.py          # compara todos los NPCs contra lo grabado
python3 scripts/npc/run_npc_tests.py banker   # solo uno
python3 scripts/npc/run_npc_tests.py --record # graba de nuevo (solo si el cambio de diálogo es a propósito)
```

- `scripts/npc/harness.lua` simula el servidor: la API de §5 con los mismos tipos de retorno, jugadores, reloj y azar deterministas. Corre con **LuaJIT** (`brew install luajit`), el mismo dialecto que el server.
- Cada NPC recibe un guion fijo (`scripts/npc/golden/<script>.scenario.txt`): saludo, todas las palabras de su script con cantidades, sí/no, ocupado, timeout y alejarse. Lo que responde queda en `golden/<script>.txt` (`SAY`, `CALL` a la API, `ERROR`).
- Guiones extra a mano: `scripts/npc/scenarios/<script>.txt` (hay para Chronos y Huntmaster).
- Si un cambio modifica un diálogo a propósito, revisar la diferencia que muestra el test y después grabar con `--record`.

Las pruebas no reemplazan probar en el juego: no cubren el C++ (confirmación de trades, travel) ni la carga real de items.

---

## 8. Historial

- **Nov 2026:** `lib/npc.lua` partida en componentes (`lib/npc/`); todos los scripts pasan a `npcDefine` (menos relleno repetido, ~500 líneas menos). `math.mod` → `math.fmod` (Chronos, daily task) para que anden también con LuaJIT. Se sacaron `leech.lua` (Bleed Room) y `guard.lua` (no lo usaba ningún NPC). Comportamiento verificado igual con el banco de pruebas.
