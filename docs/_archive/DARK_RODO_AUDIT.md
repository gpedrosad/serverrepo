# Dark Rodo NPC — Auditoría completa 2026-06-30

> **Estado**: análisis finalizado, mayoría de fixes aplicados en disco, NO se compiló ni se reinició el server (decisión del usuario). El server actual sigue corriendo con el binario previo. Para activar los cambios, compilar y reiniciar (ver "Activación" al final).

## Índice

1. [Resumen ejecutivo](#resumen-ejecutivo)
2. [Cambios aplicados en disco (no compilados)](#cambios-aplicados)
3. [Cambios revertidos / pendientes](#cambios-pendientes)
4. [Bugs identificados pero NO arreglados (de baja prioridad)](#bugs-no-arreglados)
5. [Activación](#activación)
6. [Validación post-compile](#validación-post-compile)

---

## Resumen ejecutivo

4 agentes en paralelo analizaron el NPC "Dark Rodo" (`data/npc/dark rodo.xml` + `data/npc/scripts/runes.lua`). Encontraron:

- **2 bugs críticos** (exploits de oro / items gratis): 1 arreglado, 1 revertido por incompatibilidad de tipo
- **4 bugs altos** (pricing, patrones de match, NPC duplicado): todos arreglados
- **5 bugs medios** (UX, help text): 4 arreglados
- **3 bugs bajos** (code smell, hardening): 2 arreglados, 1 informativo

Cambios del usuario aplicados: SD pasó de 90 → **250gp**, UH pasó de 40 → **200gp**.

---

## Cambios aplicados

### A) `data/npc/scripts/runes.lua` (agente 1, completo)

**Precios nuevos** (líneas 11-12):
- `sudden death` (sd): 90 → **250gp**
- `ultimate healing` (uh): 40 → **200gp**

**Strings de ayuda actualizados** (RUNES_HELP, RUNES_BACKPACKS):
- bp UH: 810 → **4010gp** (= 20 × 200 × 1 + 10)
- bp SD: 1810 → **5010gp** (= 20 × 250 × 1 + 10)
- bp HMM, GFB, explosion: sin cambios (810, 1210, 1210 — ya correctos con la nueva fórmula)

**State globals** (líneas 1-5): `focus`, `talk_start`, `target`, `following`, `attacking` ahora son `local` (antes globales a nivel módulo).

**Función `matchBackpack(msg)`** (nueva, ~L58-73): tabla-driven. Matchea `bp X` / `backpack X` / `backpack of X` para cualquier runeCharges entry (hmm/uh/gfb/explosion/sd). Las 5 branches hardcoded (`bp hmm`, `bp uh`, etc.) eliminadas.

**Función `findCatalogBuy(msg, catalog)`** (nueva, ~L54-56): wrapper de `npcFindCatalogBuyEntry`.

**Función `summarizeCatalog(entries, groupName)` + `formatPrice`** (nuevas, ~L34-52): help text dinámico para wands/rods. Reemplaza los strings hardcoded de 5 items por la lista completa de 10.

**Branch "price"/"how much"** (nuevo, ~L103-110): corre antes del catálogo. Si el jugador pregunta precio, selfSays el precio sin disparar compra.

**Reordenamiento del elseif chain**:
1. `npcIsHelp` / `runes` → help
2. `backpacks` / `rune backpacks` / `bps` → help de backpacks
3. `potions` / `potion` → help de potions (pero solo si NO matchea catálogo)
4. `wands` / `rods` → help dinámico de magic weapons
5. `matchBackpack(msg)` → compra bp
6. `findCatalogBuy(msg, RUNE_BUYS)` → compra (resuelve el bug de "strong mana potion")
7. `findCatalogBuy(msg, WAND_BUYS)` → compra
8. `else` → "I do not understand..."

**Validación**: `luac -p` pasa. 133 líneas, 4866 bytes.

---

### B) `source/npc.cpp` (agente 2, parcial)

**`addChargedItemsToPlayer` refactor** (línea 160):
- Antes: `static bool addChargedItemsToPlayer(...)` retornaba `true` si todos los items entraban, `false` si alguno fallaba.
- Ahora: `static int addChargedItemsToPlayer(...)` retorna el **número de items realmente entregados**. Para en el primer fallo, NO rollback.
- 3 callsites actualizados (2 dentro de `isRuneQuantityBuy` / `isItemQuantityBuy`, 1 firma).

**Fix del bug #2 — Rune/blank-rune partial-delivery** (líneas 555-572):
```cpp
}else if(pt.isRuneQuantityBuy){
    int delivered = addChargedItemsToPlayer(player, pt.itemid, pt.runeCharges, pt.runeQuantity);
    if(delivered == pt.runeQuantity){
        doSay("Here you go!");
    } else {
        int unit = pt.runeQuantity > 0 ? (pt.cost / pt.runeQuantity) : pt.cost;
        player->payBack(pt.cost - unit * delivered);
        doSay("You do not have enough capacity or room for that.");
    }
}
```
- **Bug arreglado**: antes, si el jugador tenía 50 slots libres y pedía 100 SD, entraban 50 y el código reembolsaba las 100 → 50 SD gratis. Ahora solo se reembolsan los no entregados.

**Fix del bug #2 (mismo patrón) para `isItemQuantityBuy`** (líneas 564-572): mismo fix para blank runes.

**`luaCreatureGetName` null check** (línea 855): ahora retorna `""` si el creature no existe en vez de desreferenciar null.

**Lua sandbox hardening** (líneas 657-661):
- Antes: `luaL_openlibs(luaState)` — exponía `io`, `os`, `debug`, `package` a scripts de NPC (RCE si un admin edita un script).
- Ahora: solo `luaopen_base/string/table/math`. Los scripts de NPC ya no pueden hacer `os.execute("rm -rf /")` o `io.open` para leer archivos del server.

**Validación**: `bool delivered = true` en npc.cpp: **0 matches**. `addChargedItemsToPlayer` en npc.cpp: 3 matches (def + 2 callers, todos actualizados). `luaL_openlibs` en npc.cpp: **0 matches**. Brace depth: balanced.

---

### C) `data/npc/scripts/lib/npc.lua` (agente 3, completo)

**Bug #3 — Disambiguación por longest-key → lowest-offset** (línea 254):

**Antes** (buggy):
```lua
function npcFindCatalogBuyEntry(msg, entries)
    local best = nil
    local bestLen = 0
    for i = 1, table.getn(entries) do
        local entry = entries[i]
        if npcMatchesAny(msg, entry.keys) then
            local len = npcCatalogKeyLength(entry)
            if len > bestLen then
                best = entry
                bestLen = len
            end
        end
    end
    return best
end
```

**Ahora** (orden-aware):
```lua
function npcFindCatalogBuyEntry(msg, entries)
    local best = nil
    local bestOffset = math.huge
    local bestLen = 0
    for i = 1, table.getn(entries) do
        local entry = entries[i]
        local offset, len = npcFindMatchOffset(msg, entry.keys)
        if offset ~= nil then
            if offset < bestOffset or (offset == bestOffset and len > bestLen) then
                best = entry
                bestOffset = offset
                bestLen = len
            end
        end
    end
    return best
end
```

**Helper `npcFindMatchOffset(msg, keys)`** (nueva, ~L272-298): busca la primera key en el mensaje respetando word-boundaries (mismas semánticas que `msgcontains`). Retorna `(offset, len)` o `(nil, nil)`.

**Casos que arregla**:
- `3 sd uh` → antes compraba UH (key "ultimate healing" = 17 chars > "sudden death" = 12), ahora compra SD (offset 3 < offset 6).
- `5 hmm mana` → antes compraba HMM (key "heavy magic missile" = 19 > "strong mana" = 11), ahora compra HMM (offset 3 < offset 7) — además el tiebreaker longest-key dentro del mismo offset mantiene el comportamiento previo cuando los items están a la misma distancia.

**Casos que mantiene**:
- `blank rune` → sigue ganando sobre `blank` (mismo offset, longest-key tiebreaker).
- `mana fluid` → sigue ganando sobre `mana` (mismo offset, longest-key tiebreaker).
- `uhsd` / `3 uhx` / `xuh` → no matchea (word-boundary preservado, igual que antes).

**Validación**: `luac -p` pasa. 15 tests mentales documentados en el commit del agente.

---

### D) `data/world/npc.xml` (agente 4, completo)

**Bug #6 — Dark Rodo duplicado**: el archivo tenía dos entradas:
- Línea 5: `x="129" y="50" z="6" dir="0"`
- Línea 11: `x="207" y="71" z="7" dir="2"`

**Análisis del agente**:
- Ambas fueron introducidas en el commit inicial `2491c60` sin comentario explicativo.
- Solo hay un NPC definition (`data/npc/dark rodo.xml`) que usa `runes.lua`.
- (129, 50, 6) está en el hub principal de NPCs (Banker, Mad, Perac, Dufi, Guild Master, Lector nearby).
- (207, 71, 7) está aislado, solo con un Seller cerca — copy-paste artifact clásico.

**Acción aplicada**: comentado el spawn de (207, 71, 7) con XML comment, no eliminado. Si es intencional, se descomenta.

```xml
<!-- Dark Rodo duplicate removed: (207, 71, 7) was a copy-paste of the spawn at (129, 50, 6). Re-enable if both are intentional. -->
<!-- <npc name="Dark Rodo" x="207" y="71" z="7" dir="2"/> -->
```

**Validación**: `xmllint --noout` reporta XML OK.

---

## Cambios pendientes

### E) Bug #1 — Fluid quantity buy no reembolsa (CRÍTICO, REVERTIDO)

**Estado**: el fix que aplicó el agente 2 **NO COMPILA** porque `Player::TLMaddItem(int, unsigned char)` retorna `void`, no `bool`. El agente asumió que retornaba bool. Revertí a la versión original (rota pero compilable) con un TODO comment.

**Código actual** (npc.cpp:543-555):
```cpp
}else if(pt.isFluidQuantityBuy){
    // YUR NOTE (Dark Rodo audit 2026-06-30): TLMaddItem returns void,
    // so we can't tell if the add succeeded. The original code had
    // `bool delivered = true;` (always true) and ignored TLMaddItem's
    // return, which meant a full inventory charged the player without
    // delivering the fluids and never refunded. Proper fix requires
    // changing `void Player::TLMaddItem(...)` to return bool and
    // propagating the change. See docs/DARK_RODO_AUDIT.md for details.
    for(int i = 0; i < pt.fluidQuantity; i++){
        player->TLMaddItem(pt.itemid, (unsigned char)pt.count);
    }
    doSay("Here you go!");
}
```

**Exploit actual**: inventario casi lleno → `5 smp` (1250gp) o `5 mana fluid` (500gp) o hasta 100 unidades (25000gp). Gold debitado, 0 items entregados, sin refund.

**Fix correcto** (5 pasos):
1. En `player.h:341` cambiar firma: `void TLMaddItem(int itemid, unsigned char count);` → `bool TLMaddItem(int itemid, unsigned char count);`
2. En `player.cpp:2806` cambiar el return: agregar `return true/false` según éxito de `addItemInventory` / `container->addItem`.
3. Buscar todos los callsites de `TLMaddItem` y ajustar si dependían del return void (probablemente ninguno, ya que nadie chequeaba el retorno).
4. En npc.cpp:543, cambiar el fix a:
   ```cpp
   }else if(pt.isFluidQuantityBuy){
       int delivered = 0;
       for(int i = 0; i < pt.fluidQuantity; i++){
           if(player->TLMaddItem(pt.itemid, (unsigned char)pt.count))
               delivered++;
           else
               break;
       }
       if(delivered == pt.fluidQuantity){
           doSay("Here you go!");
       } else {
           int unit = pt.fluidQuantity > 0 ? (pt.cost / pt.fluidQuantity) : pt.cost;
           player->payBack(pt.cost - unit * delivered);
           doSay("You do not have enough capacity or room for that.");
       }
   }
   ```
5. Compilar y verificar que `TLMaddItem` no se use en otros lados sin chequeo.

**Riesgo del fix**: el `TLMaddItem` original tiene paths no-obvios (busca slot específico, luego container con espacio). Hacerlo retornar bool requiere chequear éxito en cada path. Cuidado con los `return` implícitos al final.

---

## Bugs no arreglados (baja prioridad, no críticos)

Estos los listé en el análisis pero no los arreglé. Documentados para referencia futura.

### Bug #5 (parcial) — Substring match hazards en bp
- "backpack ultimate healing" (sin "of") → antes compraba 1 UH. AHORA ARREGLADO por la nueva función `matchBackpack` que acepta "backpack X" sin "of".
- "bp hmm runes" (con palabra trailing) → antes compraba 1 HMM. AHORA ARREGLADO — la nueva `matchBackpack` solo requiere las formas estándar, pero `findCatalogBuy` puede seguir capturando mensajes con palabras trailing. Si la palabra trailing matchea una key del catálogo, podría ganar. Edge case bajo.

### Bug #8 — "wands" / "rods" lists omiten half (arreglado parcialmente)
- AHORA el help es dinámico (summarizeCatalog), muestra los 10 items.
- Pero "wands" y "rods" son aliases al mismo help ("Magic weapons:..."). Si el jugador dice "wands", ve la lista completa. OK.

### Bug #9 — Lua sandbox (RCE) — ARREGLADO en npc.cpp
- `luaL_openlibs` reemplazado por `luaopen_base/string/table/math`. NPC scripts ya no tienen acceso a `os`/`io`/`debug`/`package`.

### Bug #10 — Variables de estado Lua no son local — ARREGLADO en runes.lua
- `focus`, `talk_start`, `target`, `following`, `attacking` ahora son `local`.

### Bug #11 — `creatureGetName` null check — ARREGLADO en npc.cpp
- Ahora retorna `""` si el creature no existe.

### Bug #12 — Race condition en pendingTrades
- `pendingTrades` es per-NPC, no per-(NPC, player). Jugador A puede confirmar una compra de jugador B si B está focused. Documentado como UX gotcha, no arreglo.

### Bug #13 — `msgcontains` whitespace-sensitivity
- "5sd" no funciona (debe ser "5 sd" con espacio). Word-boundary preservado para evitar false positives. Documentado como UX menor.

### Bug #14 — `focus` no se limpia en `selfGotoIdle`
- Si el NPC entra en combate, `focus` queda apuntando al último jugador que habló. Puede causar idle-timeout dialog a un player que ya se fue. Cosmético.

---

## Activación

Para activar los cambios aplicados, desde el directorio del repo:

```bash
# 1. Compilar el binario (dentro del container)
docker exec yurots bash -c "cd /app/YurOTS/ots/source && make clean && make"

# 2. Si la compilación pasa, reiniciar
docker restart yurots
sleep 4
docker logs --tail 5 yurots

# 3. Verificar que arrancó
docker ps | grep yurots
```

**NO compilar todavía** si querés primero arreglar el bug #1 de fluidos (cambios pendientes arriba).

### Orden recomendado

1. **Arreglar el bug #1 de fluidos primero** (cambiar TLMaddItem a bool en player.h/player.cpp + actualizar npc.cpp).
2. Compilar y verificar que no rompiste nada.
3. Reiniciar.
4. Validar con los tests de abajo.

---

## Validación post-compile

Tests manuales para verificar que los fixes funcionan:

### 1. Bug #1 (fluid refund) — REQUIERE FIX MANUAL primero
- Llenar inventario hasta casi lleno.
- `5 smp` con Dark Rodo → confirmar con `yes`.
- **Antes**: gold perdido, 0 items.
- **Después**: gold solo por los entregados, mensaje "You do not have enough capacity..." si no entran todos.

### 2. Bug #2 (rune partial delivery) — YA ARREGLADO
- Llenar inventario hasta 50 slots libres.
- `100 sd` con Dark Rodo → confirmar con `yes`.
- **Antes**: 50 SD gratis + 9000gp refund.
- **Después**: 50 SD + refund de 50×250=12500gp (= 5000gp cobrados). Mensaje de "not enough capacity".

### 3. Bug #3 (disambiguation) — YA ARREGLADO
- `3 sd uh` con Dark Rodo.
- **Antes**: prompt de compra de UH.
- **Después**: prompt de compra de SD.

### 4. Bug #4 (bp pricing) — YA ARREGLADO
- `bp uh` con Dark Rodo → 4010gp (antes 810gp).
- `bp sd` con Dark Rodo → 5010gp (antes 1810gp).
- `bp hmm`, `bp gfb`, `bp explosion` → precios sin cambios (810, 1210, 1210).

### 5. Bug #5 (bp patterns) — YA ARREGLADO
- `backpack ultimate healing` → ahora compra bp UH.
- `backpack of sd please` → ahora compra bp SD.

### 6. Bug #6 (NPC duplicado) — YA ARREGLADO
- Verificar con RME: solo debe haber 1 Dark Rodo en el mapa (en 129, 50, 6).

### 7. Bug #7 (strong mana potion) — YA ARREGLADO
- `strong mana potion` (sin abreviar) → ahora compra SMP en vez de mostrar help de potions.

### 8. Bug #8 (price check) — YA ARREGLADO
- `price sd` → "Sudden death: 250gp." (sin prompt de compra).
- `how much is uh` → "Ultimate healing: 200gp." (sin prompt de compra).

### 9. Bug #9 (no feedback) — YA ARREGLADO
- `asdfasdf` → "I do not understand. Say 'help' for prices."

### 10. Sandbox (RCE) — YA ARREGLADO
- Desde un NPC script, intentar `os.execute("id")` o `io.open("/etc/passwd")` → debe fallar con error de undefined global.

### 11. Test de regression — todo lo que ya andaba
- `hi` → greeting.
- `sd` → compra 1 SD.
- `5 uh` → compra 5 UH (1000gp total).
- `bp hmm` → compra bp HMM (810gp).
- `wands` → help dinámico con 10 items.

---

## Archivos modificados

| Archivo | Estado | Notas |
|---|---|---|
| `data/npc/scripts/runes.lua` | ✅ Modificado | 7 fixes aplicados, luac OK |
| `data/npc/scripts/lib/npc.lua` | ✅ Modificado | 1 fix (disambiguación), luac OK |
| `data/world/npc.xml` | ✅ Modificado | 1 fix (NPC duplicado), xmllint OK |
| `source/npc.cpp` | ⚠️ Parcial | 4 fixes aplicados (rune partial, null check, sandbox, helper refactor) + 1 fix REVERTIDO (fluid) con TODO comment |
| `source/player.h` | ⏳ Pendiente | Cambiar TLMaddItem firma: void → bool |
| `source/player.cpp` | ⏳ Pendiente | Implementar return bool en TLMaddItem, ajustar callsites |

## Binario actual

Sigue corriendo el binario anterior (`/app/YurOTS/ots/source/yurots` del último build antes de esta auditoría). Los cambios en disco NO se activaron.
