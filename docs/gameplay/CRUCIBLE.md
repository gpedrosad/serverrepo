# El Crisol — escalera diaria Bronze → Silver → Gold

> Idioma visible: **inglés**. Ver [política y corrección de textos](SERVER_LANGUAGE.md).

Sala con **3 puertas en orden**: Bronze, Silver y Gold. Limpiar una puerta abre la siguiente **ese día** y da su
premio **una vez por día**. La puerta Gold tiene un jefe propio que suelta un **arma Zagan exclusiva** y se puede
matar **una vez por día** por jugador. El guardián **Varkon** corre las 3 arenas: cuenta regresiva, contador en
pantalla, premio, vuelta a la sala y limpieza.

**v4 (24 nov 2026):** la v3 no se entendía y se podía abusar:

| Problema de la v3 | v4 |
|---|---|
| El jefe de Oro se farmeaba sin límite: matarlo, salir, tirar la palanca (5 Ironhide en 1 minuto en el log) | Una vez por día por jugador, marcado cuando muere el jefe a todos los que están adentro |
| Si el jefe quedaba vivo, la palanca invocaba **otro** jefe encima (completaba "hasta el tope" sin mirar quién quedaba) | Cada corrida arranca limpia: Varkon borra los monstruos de una arena vacía a los 3 s |
| Al limpiar no pasaba nada: sin aviso, sin premio; Bronze y Silver no tenían sentido | Contador abajo de la pantalla, aviso al morir el elite, premio diario por puerta y "se abrió la puerta siguiente" |
| Élites incoherentes (Bronze con Giant Spider o Beholder, más difíciles que Silver) | Élites con vida creciente por puerta (Bronze ~400–580, Silver ~900–1400) |
| Rotación con `os.date("%j")` (se cortaba en Año Nuevo) | Día local monótono (`crucibleDay()`) |
| Se podía entrar a una arena con relog adentro sin pasar por la palanca | Varkon manda a la sala a quien aparece en una arena libre sin pase de palanca |
| Carteles y palancas en fila sin decir qué hace cada una | Cartel "step N of 3" con nivel recomendado, estandarte por puerta, plataforma de llegada del mismo piso que la del hub |

Portal en la plaza del templo: `164, 47, 7` (cartel `164, 46, 7`, llegada al volver `164, 48, 7`).

Portales del templo: plaza `155,43–169,52` (z7), tabla completa en [`CAMBIAR-MAPA.md`](../CAMBIAR-MAPA.md#portales-del-templo-plaza-z7--nov-2026). Los maneja `scripts/map/temple-portals.py`.

---

## Mapa (z0, todo generado)

Las salas viven en el **distrito de eventos** (x≥560, lejos del mapa principal): así no se ven
superpuestas en RME ni como fantasmas desde la ciudad. Se movieron ahí en nov 2026 (antes flotaban
en z0 sobre la ciudad); las casillas viejas se borraron con `scripts/map/remove-old-event-areas.py`.

| Sala | Caja interior | Estilo | Entrada / salida |
|------|---------------|--------|------------------|
| Hub "Sala del Crisol" (**PZ**), 11x8 | `600,100 – 610,107` | mármol con marco negro, alfombra, 2 columnas, ángel, braseros, **Varkon** en `605,103` | llegada `605,105`; TP al templo `605,107` |
| Bronce "Foso de Arena", 11x9 | `615,100 – 625,108` | arena, arenisca, 2 columnas, calaveras y sangre, guerreros en la salida | `620,106` / TP `620,108` |
| Plata "Coliseo de Piedra", 11x9 | `630,100 – 640,108` | piedra gris, estrado del elite, 2 columnas, tapices azules, perros en la salida | `635,106` / TP `635,108` |
| Oro "Trono de Fuego", 11x9 | `645,100 – 655,108` | mármol negro, estrado del boss, alfombra, ríos de lava a los costados, obeliscos, tapices de fuego | `650,106` / TP `650,108` |

En el hub, contra la pared norte: por puerta una **plataforma 3x2** (bronce `600-602`, plata `604-606`, oro `608-610`,
filas `y=101-102`) con cartel y palanca en la fila `y=100` (palancas `601/605/609, 100`) y arriba un farol (Bronze),
estandarte azul (Silver) o rojo y dorado (Gold). Info: cartel `600,104`, palanca `600,105`.

Arenas (coordenadas locales, iguales en las 3): estrado del elite/jefe arriba al centro (`4-6, 0-1` en Silver y Gold),
spawns en las filas 1-3 (elite en `5,1`), **plataforma de llegada 3x3** (`4-6, 5-7`) con el mismo piso que la
plataforma de esa puerta en el hub, TP de salida en `5,8` justo debajo. En Gold la alfombra une la plataforma con el estrado.

**Roca alrededor (24 nov 2026):** todo `590,92 – 666,117` (z0) que no es sala ni pared es tierra maciza `101`
(bloquea), como el Reloj de Arena: desde el hub y las arenas ya no se ve el vacío negro. `CLEAR_BOX` pasó a
`588,90 – 717,125`.

### Cómo está hecho el generador

- Todo se escribe en coordenadas **locales** de cada sala (`Room.at(dx, dy)`): mover una sala es cambiar su origen.
- Las piezas comunes (`Room`, `build_room`, `Checker`, escritura del OTBM) están en `scripts/map/roomkit.py`,
  compartido con la Wave Arena.
- Una sola función `build_arena()` con el tema en `ARENAS` (suelo, paredes, columna, guardián, brasero, tapiz);
  solo el estrado/lava de Oro, el círculo de Plata y las calaveras de Bronce son propios de cada una.
- La validación lee los flags del `.otb` (`block_solid`, `stackable`): nada de listas de ids bloqueantes a mano.
  Revisa: ids que existen, sin dos piezas sólidas en una casilla, salas sin pisarse y dentro de `CLEAR_BOX`,
  todo el piso conectado, plataformas/palancas/TP alcanzables, spawns y llegadas pisables y sin repetir.
- Los ítems apilables (calaveras `2320`, etc.) llevan el byte de cantidad solos (flag `stackable`).
- `ARRIVALS` y `SPAWNS` se escriben en el bloque `LAYOUT` de `data/actions/lib/crucible.lua`; el tope del grupo es `#arrivals` (7).
- La posición de Varkon (`WARDEN`) se escribe en el bloque `CRUCIBLE_NPC` de `data/world/npc.xml`; la validación
  revisa que no pise la llegada, el TP ni una plataforma.
- Los carteles se escapan para XML (`&` crudo rompe `readables.xml`: pasó con `temple-portals.py`, arreglado en v4).
- `--dry-run --png x.png` para ver las salas antes de escribir.

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

1. TP `164, 47, 7` (plaza del templo) → hub `605, 105, 0`. Varkon (`hi`) explica y dice el progreso del día:
   `rules`, `today`, `progress`, `rewards`, `status`.
2. Palanca INFO `7203`: monstruos del día, **tu progreso** (Bronze: cleared / Silver: open / Gold: locked) y estado de
   cada arena.
3. Bronze `7200` / Silver `7201` / Gold `7202`: entra el que tira y **los de la plataforma de esa puerta que cumplan**
   (máx 7 = puntos de llegada). Al que no cumple se le dice por qué ("You stay behind: ..."). La palanca da a cada
   uno un **pase** (storage, 60 s) y cambia de lado.
4. Varkon ve jugadores con pase en la arena libre: **5 s** de cuenta regresiva y aparece el elite/jefe del día en el
   estrado con su escolta.
5. Abajo de la pantalla (`MSG_SMALLINFO`): `Crucible Gold | boss Crucible Ironhide: alive | 5 enemies left`.
   Al morir el elite/jefe hay aviso en rojo; si es el de Gold, todos los de adentro quedan marcados por hoy.
6. Sin enemigos: premio (si es la primera vez hoy en esa puerta), aviso de la puerta siguiente y 60 s para lootear.
   Después Varkon manda a todos a la sala (o se van antes por el TP sur).

## Reglas

- **Escalera diaria:** Silver pide Bronze limpio hoy; Gold pide Silver limpio hoy **y** no haber matado al jefe hoy.
  Repetir una puerta ya limpia está permitido (para ayudar a otros), pero no da premio de nuevo.
- **Jefe de Oro una vez por día:** se marca al **morir el jefe** (aunque queden monstruos o el grupo se vaya), a
  todos los jugadores que están en la arena en ese momento. Si el grupo muere antes, puede volver a intentar.
- **Cada puerta es independiente:** pueden correr 3 grupos a la vez. Una arena está libre si no hay jugadores ni
  monstruos; si el grupo muere o se va, Varkon la vacía a los 3 s.
- **Sin pase no se pelea:** quien aparece en una arena libre sin haber usado la palanca (relog adentro, GM) vuelve a la sala.
- Hay que tirar la palanca desde el hub. Las arenas no son PZ: morir ahí cuesta como en cualquier hunt.
- Si el script de Varkon se recarga en plena pelea, adopta los monstruos que ya están (no invoca otra tanda).
- Mapa, `lib/crucible.lua`, `npc.xml`, `readables.xml` y el portal del templo van **en el mismo commit**. Nunca dejar
  el Lua nuevo con el mapa viejo en el árbol de la ThinkPad: el próximo reinicio (de cualquier sesión) los carga
  desincronizados y las palancas mandan a casillas vacías. Para probar sin tocar el árbol en vivo: copia aparte
  + contenedor descartable en otro puerto (necesita `queue.xml`, `online.xml` y `houseitems.xml`) y
  `scripts/ot/test-crucible.py` (abajo).

### Premios (una vez por día por puerta, `lib/crucible.lua` → `tiers`)

| Puerta | Nivel recomendado | Escolta | Premio |
|---|---|---|---|
| Bronze | 30+ | 3: Minotaur, Minotaur Archer, Minotaur Guard | 2.000 gp, 5.000 exp, 1 gema chica |
| Silver | 50+ | 4: Demon Skeleton, Ghoul, Beholder, Stalker | 5.000 gp, 15.000 exp, 2 gemas chicas |
| Gold | 80+ | 5: Dragon, Giant Spider, Hero, Necromancer, Dragon | 10.000 gp, 40.000 exp, 3 gemas chicas |

La gema es al azar entre diamond, sapphire, ruby, emerald y amethyst (todas del mismo tipo).

### Storage (9500–9504)

| Storage | Uso |
|---|---|
| `9500` | día (`crucibleDay()`) al que corresponde `9501` |
| `9501` | última puerta limpiada ese día: 0 ninguna, 1 Bronze, 2 Silver, 3 Gold |
| `9502` | día en que mató al jefe de Oro |
| `9503` / `9504` | pase de la palanca: puerta (1–3) y `os.time()`; Varkon lo consume al empezar |

### Probar

```bash
python3 scripts/npc/run_npc_tests.py crucible_warden     # Varkon sin servidor (guion scripts/npc/scenarios/crucible_warden.txt)
# en un server de PRUEBA con bots (make-test-bots.py ... 605 104 0), nunca en el que se juega:
python3 scripts/ot/test-crucible.py --port 7275          # escalera, grupo, jefe 1/día, relog adentro, arena abandonada
```

---

## Rotación diaria + armas

El día del ciclo es `crucibleDay() mod 7 + 1` (día local monótono; no sigue los días de la semana).

| Día | Bronze (elite) | Silver (elite) | Gold (jefe) | Arma | Id | Delay | Efecto |
|-----|----------------|----------------|-------------|------|----|-------|--------|
| 1 | Orc Leader | Giant Spider | Ashlord | ashlord emberblade | `20112` | 1100ms | Trail fuego; 20% burn DoT |
| 2 | Cyclops Smith | Dragon | Frostwarden | frostwarden chillblade | `20138` | 1200ms | 18% chill (slow) 4s PvP |
| 3 | Dwarf Geomancer | Lich | Bonepriest | bonepriest reaver | `20154` | default | 15% mana drain |
| 4 | Vampire | Hero | Ironhide | ironhide crusher | `20121` | 1700ms | 22% root 2.5s PvP |
| 5 | Lizard Templar | Vampire Bride | Venomqueen | venomqueen fang | `20100` | 950ms | 25% poison DoT |
| 6 | Bone Beast | Undead Gladiator | Stormcaller | stormcaller maul | `20110` | 1000ms | Trail energy; 20% burst |
| 7 | Necromancer | Orc Warlord | Bloodreaver | bloodreaver saber | `20122` | 1200ms | 30% life leech 25% dmg |

Loot exclusive: `chance="4500"` (**4,5%**, +10% relativo si el que mata es premium) solo en ese jefe. Con el jefe
limitado a una vez por día, es ~1 arma cada 22 días por jugador: si se siente muy raro, subir la chance en los
7 `data/monster/crucible *.xml`.

```bash
python3 scripts/otb/patch-crucible-rares-otb.py
# symlink: scripts/patch-crucible-rares-otb.py
```

Tras tocar C++: `make clean && make` (se agregó `chillTicks` en `creature.h`).

---

## Archivos

| Archivo | Rol |
|---------|-----|
| `scripts/map/generate-crucible.py` (symlink `scripts/generate-crucible.py`) | OTBM (hub + 3 arenas, PZ del hub), carteles en readables, bloque `LAYOUT` de `lib/crucible.lua`, Varkon en `npc.xml`, `generated-crucible.json`. `--dry-run --png x.png` para previsualizar; `--replace` escribe. Después correr `scripts/map/temple-portals.py` |
| `data/actions/lib/crucible.lua` | Config compartida: layout, puertas (`tiers`), rotación (`daily`), storage, escalera y pase |
| `data/actions/scripts/crucible.lua` | Palancas: valida, arma el grupo, da el pase y manda a la arena |
| `data/npc/scripts/crucible_warden.lua` + `data/npc/varkon.xml` | Varkon: corre las arenas (cuenta, spawn, HUD, jefe, premio, vuelta, limpieza) y responde |
| `scripts/otb/patch-crucible-rares-otb.py` (symlink `scripts/patch-crucible-rares-otb.py`) | Stats/nombres OTB de las 7 armas |
| `data/monster/crucible *.xml` | Jefes + loot |
| `scripts/ot/test-crucible.py`, `scripts/npc/scenarios/crucible_warden.txt` | Pruebas |
| `source/const76.h`, `game.cpp`, `player.cpp`, `item.cpp`, `creature.h` | Gameplay de las armas |
