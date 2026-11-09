# El Crisol — bosses diarios + armas exclusivas

Hub con **3 puertas** (Bronce / Plata / Oro). Cada día rota elite/boss. La puerta Oro dropea un **arma Zagan exclusiva** con efecto C++.

**v2 (nov 2026):** rediseño completo del mapa y la lógica (antes eran 4 cajas de piso de madera sin paredes).

Portal en la plaza del templo: `164, 47, 7` (cartel `164, 46, 7`, llegada al volver `164, 48, 7`).

Portales del templo: plaza `155,43–169,52` (z7), tabla completa en [`CAMBIAR-MAPA.md`](../CAMBIAR-MAPA.md#portales-del-templo-plaza-z7--nov-2026). Los maneja `scripts/map/temple-portals.py`.

---

## Mapa (z0, todo generado)

| Sala | Caja interior | Estilo | Entrada / salida |
|------|---------------|--------|------------------|
| Hub "Sala del Crisol" (**PZ**) | `76,79 – 94,95` | mármol, marco negro, alfombra roja, 4 columnas, ángel, braseros | llegada `85,92`; TP al templo `85,95` |
| Bronce "Foso de Arena" | `104,80 – 118,92` | arena, paredes de arenisca, 4 columnas, escombros, calaveras, guerreros en la salida | `111,90` / TP `111,92` |
| Plata "Coliseo de Piedra" | `128,79 – 144,93` | baldosa gris, círculo central, 4 columnas, perros guardianes | `136,91` / TP `136,93` |
| Oro "Trono de Fuego" | `154,78 – 172,94` | mármol negro, 4 pozos de lava (no pisables), alfombra al estrado dorado del boss, obeliscos, banderas | `163,92` / TP `163,94` |

En el hub, pared norte: por puerta una **plataforma 3x2** (bronce `78-80`, plata `84-86`, oro `90-92`, filas `y=80-81`)
con la palanca al norte del centro (`79/85/91, 79`) y el cartel a su izquierda. Palanca INFO `77,88` (cartel `77,87`).
Antorchas en la pared oeste, faroles en la norte, braseros en las esquinas.

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

1. TP `164, 47, 7` (plaza del templo) → hub `85, 92, 0`.
2. Palanca INFO `7203`: bosses y rare del día + **estado de cada arena** (libre / ocupada por quién / monstruos sueltos).
3. Bronce `7200` / Plata `7201` / Oro `7202`: entran **todos los jugadores parados en la plataforma** de esa puerta
   más el que tira (máx 7). Llegan al sur de la arena, repartidos alrededor de la entrada.
4. Monstruos en la **mitad norte**: elite/boss arriba al centro (en Oro, sobre el estrado), el pack repartido.
5. Salida: TP sur de la arena → hub → TP sur del hub → templo `164, 48, 7`.

## Reglas (`data/actions/scripts/crucible.lua`)

- **Cada puerta es independiente**: pueden correr 3 grupos a la vez. Una arena está ocupada mientras haya
  un jugador adentro (se escanea la caja; no hay dueño guardado que pueda quedar colgado).
- Hay que tirar la palanca desde el hub.
- Si quedaron monstruos de una corrida abandonada, se invoca el elite y se completa el pack **hasta el tope**
  (`PACK_COUNT + 1`); nunca se acumulan más.
- El bloque `LAYOUT` de `crucible.lua` (hub, plataformas, arenas, entradas, spawns) **lo escribe el generador**;
  no editarlo a mano.

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
