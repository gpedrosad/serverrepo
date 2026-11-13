# Wave Arena — Claro de la Selva

Arena PvE de 20 oleadas para grupos (v2, nov 2026). Campamento seguro + claro de selva cerrado con bambú.
Un jefe cada 5 oleadas, las oleadas escalan con el grupo, ranking semanal por oleadas **limpias** y premio
la primera vez en la semana que se limpia la 5 / 10 / 15 / 20.

Portal en la plaza del templo: `166, 47, 7` (cartel `166, 46, 7`, llegada al volver `166, 48, 7`).
Portales del templo: tabla en [`CAMBIAR-MAPA.md`](../CAMBIAR-MAPA.md#portales-del-templo-plaza-z7--nov-2026),
los maneja `scripts/map/temple-portals.py`.

**v1 → v2:** la v1 era una sala de 7x7 con un vestíbulo abierto, para un jugador, con una sola especie por oleada.
Tenía dos fallas: el ranking anotaba la oleada **al empezarla** (con abrir la 20 quedabas primero) y el conteo de
monstruos no miraba el vestíbulo, donde estaban las palancas.

---

## Mapa (z7, todo generado)

| Sala | Caja interior | Estilo |
|------|---------------|--------|
| Campamento (**PZ**), 9x5 | `172,400 – 180,404` | bambú, piso de barro, plataforma de madera 3x2, fogatas, arbustos |
| Claro, 13x11 | `170,385 – 182,395` | bambú, pasto con textura, barro al centro, selva cerrando las 4 esquinas, tocones y arbustos de cobertura |

| Qué | Dónde |
|-----|-------|
| Llegada desde el templo | `176,403` (campamento) |
| TP al templo | `176,404` |
| Plataforma de grupo | `175–177, 401–402` |
| Palanca inicio `7100` / ranking `7101` | `176,400` / `179,400` (carteles a su izquierda) |
| Llegada del grupo al claro | filas `393–394` alrededor de `176,394` |
| Palanca siguiente `7102` / retirarse `7103` | `175,395` / `177,395` (cartel `176,395`) |
| Spawns | borde norte y costados del claro (16 puntos; el 1º, `176,386`, es el del jefe) |

Bambú (medido en el mapa): poste `3425`, horizontal `3426`, vertical `3423`, esquina SE `3429`.

## Flujo

1. Portal del templo → campamento.
2. El grupo se para en la plataforma de madera; uno tira la palanca de inicio. Entran todos (máx 7) y sale la oleada 1.
3. Con el claro limpio, la palanca **siguiente** anota la oleada limpia a todos los del claro y suelta la próxima.
4. La palanca **retirarse** lleva al campamento y anota la última oleada limpia (la actual si ya está limpia).
   No hay TP de salida en el claro: así nadie se va sin que la marca quede guardada. Morir no anota nada.
5. Al limpiar la 20 el grupo vuelve al campamento.

## Reglas (`data/actions/scripts/wave_arena.lua`)

- Una corrida a la vez. El claro está ocupado mientras haya un jugador adentro (se escanea la caja; no hay dueño
  guardado que pueda quedar colgado). Si el grupo muere o se retira entero, otro grupo puede entrar.
- Monstruos sobrantes de una corrida anterior cuentan para la oleada 1 del grupo nuevo.
- Escala: cada entrada del pack es `base + floor(base * (jugadores - 1) / 2)`; el jefe no escala.
- La oleada en curso vive en `WaveRun.wave` y se copia en el storage `9303` de cada jugador del claro: si se
  recarga el script a mitad de corrida, se recupera de ahí.
- Premios en `REWARDS` (5 / 15 / 30 platinum, 1 crystal), una vez por semana por jugador y por escalón.
- El bloque `LAYOUT` de `wave_arena.lua` (cajas, plataforma, llegadas, spawns) **lo escribe el generador**.

| Storage | Qué |
|---------|-----|
| `9300` | semana de las marcas |
| `9301` | mejor oleada limpia de la semana |
| `9302` | mejor oleada limpia histórica |
| `9303` | oleada en curso (respaldo) |
| `9310–9313` | semana en que cobró el premio de la 5 / 10 / 15 / 20 |

Ranking: `data/logs/wave_arena_rank.json` (runtime, top 10 de la semana).

## Oleadas

| # | Monstruos (base, 1 jugador) | # | Monstruos |
|---|---|---|---|
| 1 | 3 Rat, 2 Cave Rat | 11 | 2 Lion, 2 Tiger |
| 2 | 3 Wolf, 2 Snake | 12 | 2 Dworc Fleshhunter, 2 Dworc Venomsniper, 1 Dworf Voodoomaster |
| 3 | 2 Hyaena, 2 Poison Spider | 13 | 2 Stalker, 2 Hunter |
| 4 | 2 Centipede, 2 Larva, 1 Scorpion | 14 | 2 Terror Bird, 2 Crocodile |
| 5 | **Jefe Tarantula**, 3 Poison Spider | 15 | **Jefe Lizard Templar**, 2 Kongra, 1 Sibang |
| 6 | 2 Orc Spearman, 2 Orc Warrior | 16 | 2 Mummy, 2 Ghoul |
| 7 | 2 Bandit, 2 Smuggler | 17 | 2 Carniphila, 2 Lizard Sentinel |
| 8 | 3 War Wolf, 1 Bear | 18 | 2 Gazer, 1 Lizard Snakecharmer, 2 Assassin |
| 9 | 2 Amazon, 2 Valkyrie | 19 | 2 Blue Djinn, 1 Lizard Templar |
| 10 | **Jefe Orc Leader**, 1 Orc Berserker, 2 Orc Shaman | 20 | **Jefe Giant Spider**, 2 Tarantula |

## Archivos

| Archivo | Rol |
|---------|-----|
| `scripts/map/generate-wave-arena.py` | Mapa (campamento + claro), carteles, bloque `LAYOUT` de `wave_arena.lua`, `generated-wave-arena.json`. `--dry-run --png x.png` para ver; `--replace` escribe. Después, `scripts/map/temple-portals.py` |
| `scripts/map/roomkit.py` | Piezas comunes con El Crisol: salas, paredes, validación con flags del `.otb`, escritura del OTBM |
| `data/actions/scripts/wave_arena.lua` | Palancas, oleadas, marcas, premios, ranking |
| `data/actions/actions.xml` | `uniqueid` 7100–7103 |

Mapa, Lua, carteles y portal van en el **mismo commit** (ver la regla en [`CRUCIBLE.md`](CRUCIBLE.md)).

## Probar sin server

La lógica se probó con Lua 5.1 (la librería del server, `liblua5.1` en la imagen `serverrepo-yurots`) y un
simulador del motor: grupo, sala ocupada, siguiente con vivos, retirarse, recarga del script, las 20 oleadas y
premios que no se repiten en la semana. Nombres de monstruos chequeados contra `monster/monsters.xml`.
