# El Crisol — bosses diarios + armas exclusivas

Hub con **3 puertas** (Bronce / Plata / Oro). Cada día rota elite/boss. La puerta Oro dropea un **arma Zagan exclusiva** con efecto C++.

**v3 (nov 2026):** salas compactas y decoradas (antes: 4 cajas de hasta 19x17 casi vacías, 1376 casillas;
ahora 559). Las 3 arenas tienen la misma forma 11x9, así comparten llegada, spawns y salida.

Portal en la plaza del templo: `164, 47, 7` (cartel `164, 46, 7`, llegada al volver `164, 48, 7`).

Portales del templo: plaza `155,43–169,52` (z7), tabla completa en [`CAMBIAR-MAPA.md`](../CAMBIAR-MAPA.md#portales-del-templo-plaza-z7--nov-2026). Los maneja `scripts/map/temple-portals.py`.

---

## Mapa (z0, todo generado)

| Sala | Caja interior | Estilo | Entrada / salida |
|------|---------------|--------|------------------|
| Hub "Sala del Crisol" (**PZ**), 11x8 | `78,80 – 88,87` | mármol con marco negro, alfombra, 2 columnas, ángel, braseros | llegada `83,85`; TP al templo `83,87` |
| Bronce "Foso de Arena", 11x9 | `93,80 – 103,88` | arena, arenisca, 2 columnas, calaveras y sangre, guerreros en la salida | `98,86` / TP `98,88` |
| Plata "Coliseo de Piedra", 11x9 | `108,80 – 118,88` | piedra gris, círculo central, 2 columnas, tapices azules, perros en la salida | `113,86` / TP `113,88` |
| Oro "Trono de Fuego", 11x9 | `123,80 – 133,88` | mármol negro, estrado del boss, alfombra, ríos de lava a los costados, obeliscos, tapices de fuego | `128,86` / TP `128,88` |

En el hub, contra la pared norte: por puerta una **plataforma 3x2** (bronce `78-80`, plata `82-84`, oro `86-88`,
filas `y=81-82`) con cartel y palanca en la fila `y=80` (palancas `79/83/87, 80`). Info: cartel `78,84`, palanca `78,85`.

Arenas (coordenadas locales, iguales en las 3): spawns en las filas 1-3 (boss en `5,1`), llegada del grupo en las
filas 5-6 alrededor de `5,6`, TP de salida en `5,8`.

### Cómo está hecho el generador

- Todo se escribe en coordenadas **locales** de cada sala (`Room.at(dx, dy)`): mover una sala es cambiar su origen.
- Una sola función `build_arena()` con el tema en `ARENAS` (suelo, paredes, columna, guardián, brasero, tapiz);
  solo el estrado/lava de Oro, el círculo de Plata y las calaveras de Bronce son propios de cada una.
- La validación lee los flags del `.otb` (`block_solid`, `stackable`): nada de listas de ids bloqueantes a mano.
  Revisa: ids que existen, sin dos piezas sólidas en una casilla, salas sin pisarse y dentro de `CLEAR_BOX`,
  todo el piso conectado, plataformas/palancas/TP alcanzables, spawns y llegadas pisables y sin repetir.
- Los ítems apilables (calaveras `2320`, etc.) llevan el byte de cantidad solos (flag `stackable`).
- `ARRIVALS` y `SPAWNS` se escriben en el bloque `LAYOUT` de `crucible.lua`; el tope del grupo es `#arrivals` (7).

### Patrones de piezas (medidos en `test.otbm`, reusables en otros generadores)

Paredes de un cuarto (las piezas van en el anillo de casillas que rodea el interior):

| Material | Poste (esquina NO) | Horizontal (filas N y S, esquina NE) | Vertical (columnas O y E, esquina SO) | L (esquina SE) |
|----------|-------------------|--------------------------------------|----------------------------------------|----------------|
| Piedra | `1051` | `1050` | `1049` | `1053` |
| Arenisca | `1062` | `1063` | `1060` | `1066` |
| Ladrillo | `1027` | `1028` | `1030` | `1033` |

Colgables: antorcha `2061` sobre pared vertical (oeste), farol `2040` sobre pared horizontal (norte).

Alfombra roja (rectángulo de 3 de ancho; **el borde oeste es `4397`, el este `4399`**, no al revés):

```
4394 4395 4396   arriba: esquina NO, fleco, esquina NE
4397 4398 4399   medio:  borde O, centro, borde E
4400 4401 4402   abajo:  esquina SO, fleco, esquina SE
```

## Flujo

1. TP `164, 47, 7` (plaza del templo) → hub `83, 85, 0`.
2. Palanca INFO `7203`: bosses y rare del día + **estado de cada arena** (libre / ocupada por quién / monstruos sueltos).
3. Bronce `7200` / Plata `7201` / Oro `7202`: entran **todos los jugadores parados en la plataforma** de esa puerta
   más el que tira (máx 7 = puntos de llegada; los que sobran reciben "Grupo lleno"). Llegan al sur de la arena.
4. Monstruos en la **mitad norte**: elite/boss arriba al centro (en Oro, sobre el estrado), el pack repartido.
   Rotación en `DAILY` con campos por puerta (`bronze`, `silver`, `gold`, `rare`).
5. Salida: TP sur de la arena → hub → TP sur del hub → templo `164, 48, 7`.

## Reglas (`data/actions/scripts/crucible.lua`)

- **Cada puerta es independiente**: pueden correr 3 grupos a la vez. Una arena está ocupada mientras haya
  un jugador adentro (se escanea la caja; no hay dueño guardado que pueda quedar colgado).
- Hay que tirar la palanca desde el hub.
- Si quedaron monstruos de una corrida abandonada, se invoca el elite y se completa el pack **hasta el tope**
  (`PACK_COUNT + 1`); nunca se acumulan más.
- El bloque `LAYOUT` de `crucible.lua` (hub, plataformas, arenas, entradas, spawns) **lo escribe el generador**;
  no editarlo a mano.
- Mapa, `crucible.lua`, `readables.xml` y el portal del templo van **en el mismo commit**. Nunca dejar el Lua
  nuevo con el mapa viejo en el árbol de la ThinkPad: el próximo reinicio (de cualquier sesión) los carga
  desincronizados y las palancas mandan a casillas vacías. Para probar sin tocar el árbol en vivo: worktree aparte
  + contenedor descartable en otro puerto (necesita `queue.xml`, `online.xml` y `houseitems.xml` vacíos).

---

## Rotación diaria + armas

| Día | Oro (boss) | Arma | Id | Delay | Efecto |
|-----|------------|------|----|-------|--------|
| 1 | Ashlord | ashlord emberblade | `20112` | 1100ms | Trail fuego; 20% burn DoT |
| 2 | Frostwarden | frostwarden chillblade | `20138` | 1200ms | 18% chill (slow) 4s PvP |
| 3 | Bonepriest | bonepriest reaver | `20154` | default | 15% mana drain |
| 4 | Ironhide | ironhide crusher | `20121` | 1700ms | 22% root 2.5s PvP |
| 5 | Venomqueen | venomqueen fang | `20100` | 950ms | 25% poison DoT |
| 6 | Stormcaller | stormcaller maul | `20110` | 1000ms | Trail energy; 20% burst |
| 7 | Bloodreaver | bloodreaver saber | `20122` | 1200ms | 30% life leech 25% dmg |

Loot exclusive: `chance="4500"` (~4.5%) solo en ese boss.

```bash
python3 scripts/otb/patch-crucible-rares-otb.py
# symlink: scripts/patch-crucible-rares-otb.py
```

Tras tocar C++: `make clean && make` (se agregó `chillTicks` en `creature.h`).

---

## Archivos

| Archivo | Rol |
|---------|-----|
| `scripts/map/generate-crucible.py` (symlink `scripts/generate-crucible.py`) | OTBM (hub + 3 arenas, PZ del hub), carteles en readables, bloque `LAYOUT` de `crucible.lua`, `generated-crucible.json`. `--dry-run --png x.png` para previsualizar; `--replace` escribe. Después correr `scripts/map/temple-portals.py` |
| `scripts/otb/patch-crucible-rares-otb.py` (symlink `scripts/patch-crucible-rares-otb.py`) | Stats/nombres OTB de las 7 armas |
| `data/actions/scripts/crucible.lua` | Palancas, grupos, arenas independientes, rotación |
| `data/monster/crucible *.xml` | Bosses + loot |
| `source/const76.h`, `game.cpp`, `player.cpp`, `item.cpp`, `creature.h` | Gameplay |
