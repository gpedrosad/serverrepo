# Wave Arena — Claro de la Selva

Arena PvE de 20 oleadas progresivas (lvl 25 → 100+) para solo o grupos (v3, nov 2026). Campamento seguro + claro de selva cerrado con bambú.
Un jefe cada 5 oleadas, las oleadas escalan con el grupo sin saturar los spawns, ranking semanal por oleadas **limpias** (desempata por menor tiempo de corrida), premio semanal (oro + gemas pequeñas) al limpiar la 5 / 10 / 15 / 20, y NPC vigía **Kaelen** en el campamento que limpia monstruos huérfanos y muestra el HUD en vivo.

Portal en la plaza del templo: `166, 47, 7` (cartel `166, 46, 7`, llegada al volver `166, 48, 7`).
Portales del templo: tabla en [`CAMBIAR-MAPA.md`](../CAMBIAR-MAPA.md#portales-del-templo-plaza-z7--nov-2026), los maneja `scripts/map/temple-portals.py`.

**v2 → v3 (nov 2026):**
- Se rehízo la curva de 20 oleadas para que escale de forma estrictamente monótona (lvl 25 → 100+): salieron los Rats/Snakes iniciales, las caídas de dificultad (Lions/Tigers tras Orc Leader, Mummies tras Lizard Templar) y `Carniphila` (tenía `HP=022`).
- Se sumó **Kaelen** (`603, 220, 7`) para limpiar automáticamente monstruos huérfanos (~2 s tras quedar vacío el claro) y mostrar el HUD de monstruos restantes / aviso en rojo de oleada limpia, sin recompilar C++.
- Ranking semanal ahora guarda `{wave, time}` y desempata por menor tiempo (antes desempataba alfabéticamente); semana monótona desde lunes UTC (no se corta en Año Nuevo).
- Escalado de grupo ajustado (`+30%` por jugador extra, tope `14` en pack) para no saturar los 15 spawns.
- Premios semanales mejorados con oro + gemas pequeñas.

---

## Mapa (z7, todo generado)

Campamento y claro viven en el **distrito de eventos** (x≥560, lejos del mapa principal).

| Sala | Caja interior | Estilo |
|------|---------------|--------|
| Campamento (**PZ**), 9x5 | `602,220 – 610,224` | bambú, piso de barro, plataforma de madera 3x2, fogatas, arbustos |
| Claro, 13x11 | `600,205 – 612,215` | bambú, pasto con textura, barro al centro, selva cerrando las 4 esquinas, tocones y arbustos de cobertura |

| Qué | Dónde |
|-----|-------|
| Llegada desde el templo | `606,223` (campamento) |
| TP al templo | `606,224` |
| NPC vigía **Kaelen** | `603,220` (campamento PZ) |
| Plataforma de grupo | `605–607, 221–222` |
| Palanca inicio `7100` / ranking `7101` | `606,220` / `609,220` (carteles a su izquierda) |
| Llegada del grupo al claro | filas `213–214` alrededor de `606,214` |
| Palanca siguiente `7102` / retirarse `7103` | `605,215` / `607,215` (cartel `606,215`) |
| Spawns | borde norte y costados del claro (16 puntos; el 1º, `606,206`, es el del jefe) |

Bambú (medido en el mapa): poste `3425`, horizontal `3426`, vertical `3423`, esquina SE `3429`.

**Selva alrededor (24 nov 2026):** las salas flotaban en vacío negro (se veía desde 165 casillas). Ahora todo
`590,197 – 622,232` que no es sala ni pared es selva tupida que bloquea: pasto con árboles (`TREES`), arbustos
`2767` y matas `2781` (`build_jungle`, `JUNGLE_BOX`). `CLEAR_BOX` pasó a `589,196 – 623,233`.

## Flujo

1. Portal del templo → campamento.
2. El grupo se para en la plataforma de madera; uno tira la palanca de inicio. Entran todos (máx 7) y sale la oleada 1.
3. Mientras pelean, **Kaelen** muestra abajo `Wave Arena | Oleada X/20 | quedan N monstruo(s)` y avisa en rojo en cuanto la oleada queda limpia.
4. Con el claro limpio, la palanca **siguiente** anota la oleada limpia + tiempo a todos los del claro (y entrega premio si corresponde) y suelta la próxima.
5. La palanca **retirarse** lleva al campamento y guarda la última oleada limpia (la actual si ya está limpia). Cada oleada previa ya quedó guardada al pasarla, incluso si después morís en una oleada más alta.
6. Al limpiar la 20 el grupo vuelve al campamento. Si el claro queda vacío con monstruos vivos (muerte o retiro), Kaelen los retira en ~2 s y `start()` bloquea el ingreso hasta que quede limpio.

## Reglas (`data/actions/scripts/wave_arena.lua` + `data/npc/scripts/kaelen.lua`)

- Una corrida a la vez. El claro está ocupado mientras haya un jugador adentro; si quedaron monstruos huérfanos, Kaelen los limpia en ~2 s y la palanca de inicio pide esperar 2 segundos.
- Escala: cada entrada del pack es `round(base * (1 + 0.30 * (jugadores - 1)))`, con tope `MAX_PACK_MOBS = 14`; el jefe no escala.
- La oleada en curso (`9303`) y el timestamp de inicio (`9305`) se copian en cada jugador del claro: si se recarga el script a mitad de corrida, se recuperan ambos.
- Premios semanales (`REWARDS`), una vez por semana por jugador y por escalón:
  - Oleada 5: `10 platinum coins` + `1 Small Emerald` (`2149`)
  - Oleada 10: `30 platinum coins` + `2 Small Sapphire` (`2146`)
  - Oleada 15: `1 crystal coin` + `3 Small Ruby` (`2147`)
  - Oleada 20: `3 crystal coins` + `5 Small Diamond` (`2145`)
- El bloque `LAYOUT` de `wave_arena.lua` (cajas, plataforma, llegadas, spawns) **lo escribe el generador**.

| Storage | Qué |
|---------|-----|
| `9300` | semana monótona (lunes UTC) de las marcas |
| `9301` | mejor oleada limpia de la semana |
| `9302` | mejor oleada limpia histórica |
| `9303` | oleada en curso (respaldo + leído por Kaelen para el HUD) |
| `9304` | mejor tiempo (segundos) de `9301` |
| `9305` | `os.time()` de inicio de corrida (respaldo) |
| `9310–9313` | semana en que cobró el premio de la 5 / 10 / 15 / 20 |

Ranking: `data/logs/wave_arena_rank.json` (runtime, top 10 de la semana, formato `{"wave": N, "time": S}`, retrocompatible con el formato entero v2).

## Oleadas (base, 1 jugador, sin variantes rage)

| # | Monstruos | # | Monstruos |
|---|---|---|---|
| 1 | 2 Orc Warrior, 2 Orc Spearman, 1 Minotaur | 11 | 1 Hero, 1 Black Knight, 1 Undead Gladiator |
| 2 | 2 Minotaur Guard, 2 Minotaur Archer, 1 Minotaur Mage | 12 | 2 Bog Raider, 2 Mutated Tiger |
| 3 | 3 Tarantula, 2 Terror Bird | 13 | 2 Dragon Lord, 1 Dragon |
| 4 | 2 Cyclops, 2 Dwarf Guard, 1 Cyclops Drone | 14 | 2 Hydra, 1 Emerald Scarab |
| 5 | **Jefe Red Kongra**, 2 Kongra, 2 Sibang | 15 | **Jefe Behemoth**, 2 Dragon Lord |
| 6 | 2 Lizard Templar, 2 Lizard Sentinel, 1 Lizard Snakecharmer | 16 | 2 Frost Dragon, 1 Ice Spider, 1 Ice Monk |
| 7 | 2 Vampire, 2 Demon Skeleton, 1 Necromancer | 17 | 2 Black Dragon, 2 Hellhound |
| 8 | 2 Ancient Scarab, 2 Scarab | 18 | 2 Warlock, 1 Lich, 1 Banshee |
| 9 | 2 Dragon, 1 Wyvern | 19 | 2 Dark Hydra, 1 Behemoth |
| 10 | **Jefe Giant Spider**, 1 Crystal Spider, 2 Tarantula | 20 | **Jefe Old Widow**, 1 Dark Hydra, 1 Hydra |

## Archivos

| Archivo | Rol |
|---------|-----|
| `scripts/map/generate-wave-arena.py` | Mapa (campamento + claro), carteles, bloque `LAYOUT` de `wave_arena.lua`, `generated-wave-arena.json` |
| `scripts/map/roomkit.py` | Piezas comunes con El Crisol: salas, paredes, validación `.otb`, escritura OTBM |
| `data/actions/scripts/wave_arena.lua` | Palancas, 20 oleadas, escalado, ranking por tiempo, premios semanales |
| `data/npc/kaelen.xml` + `data/npc/scripts/kaelen.lua` | NPC vigía del campamento: limpieza automática de huérfanos, HUD en vivo, diálogo |
| `data/world/npc.xml` | Spawn de Kaelen en `603, 220, 7` |
| `data/actions/actions.xml` | `uniqueid` 7100–7103 |
| `scripts/npc/scenarios/kaelen.txt` | Prueba automatizada de Kaelen (`python3 scripts/npc/run_npc_tests.py kaelen`) |

## Probar sin server

- Kaelen: `python3 scripts/npc/run_npc_tests.py kaelen` (limpieza de huérfanos, HUD, aviso de oleada limpia y diálogo).
- `wave_arena.lua`: probado con LuaJIT simulando el motor (bloqueo por huérfanos, 20 oleadas, desempate por tiempo en ranking, premios semanales no repetidos, escalado hasta 7 jugadores sin saturar spawns y recuperación tras recarga del script). Todas las especies validadas contra `monster/monsters.xml`.
