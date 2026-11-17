# El Foso Olvidado — cuevas progresivas en la antigua Arena PvP

La Arena PvP de z9 (`119–130, 33–40`) se retiró en nov 2026. En su lugar hay una sala de
entrada natural y tres pisos de laberinto de caza, de nivel 20 a 100+. La arena no tenía portal
en la plaza: se entra por las cloacas de la ciudad, como antes.

Generador: `scripts/map/generate-forgotten-pit.py` (re-ejecutable, determinista con la misma
semilla). Manifiesto: `server/YurOTS/ots/data/world/generated-forgotten-pit.json`.

## Qué se sacó

- Tiles de la arena: piso de mármol `991`, alfombras `1546/1547`, muros `1034/1032`,
  decoración `1900–1905`, pads, palanca `7001` y teleport `1387` de `121,33,9`.
- `data/pvparenas.xml` quedó vacío (`<pvparenas/>`): ningún tile se carga como arena PvP.
- La acción `uniqueid 7001` de `actions.xml` se sacó. El script `arenalever.lua` y el C++
  `pvparena.cpp` quedan en el repo por si algún día se declara otra arena, pero hoy no hay
  ninguna zona marcada.

La sala nueva **conserva la escalera de mano `1386` de `125,30,9`**, que es la salida real a las
cloacas. Si se regenera la zona, esa escalera y la trampilla de arriba no se tocan.

## Cómo se llega

| Paso | Posición |
|------|----------|
| Cartel en la ciudad | `128,33,7` (junto a la trampilla) |
| Trampilla en la ciudad | `127,32,7` (baja a la salita de z8) |
| Salita de z8 | `125–127, 30–33` (piso `431`) |
| Trampilla a la arena | `125,30,8` |
| Sala de entrada (El Foso) | `125,30,9`, escalera de mano de vuelta a z8 |
| Bajada al primer piso | `140,28,9` (escalera `432`) |

No hay portal en la plaza del templo. La entrada es la misma que usaba la arena.

## Recorrido

| Piso | Nombre | Nivel | Entrada | Salida | Casillas de piso |
|---|---|---|---:|---|---:|
| z10 | Galerías Húmedas | 20–45 | corredor `140,28` → túnel `200,11` → `214,12` | `238,76` | 2.386 + 196 de corredor |
| z11 | Cavernas Profundas | 45–80 | `238,76` | `214,12` | 2.404 |
| z12 | El Corazón | 70–110+ | `214,12` | `262,76` | 2.448 |

El corredor de z10 es un camino de 2 de ancho que serpentea desde la escalera de la sala de
entrada hasta el laberinto. Los tres laberintos ocupan la caja `x 200–275, y 0–90` (z10–z12), que
estaba vacía. La caja del corredor es `x 130–199, y 0–32`: no toca la cueva del Minotauro, que
empieza en `y 33`.

Cada piso es un laberinto perfecto sobre una grilla de celdas de **2×2 casillas**, con pasillos de
2 de ancho, paredes de 2, loops suaves (7%) y salas de 3×3 celdas en la entrada, la salida y los
jefes. El recorrido más corto entrada→salida es de **326 / 284 / 234 pasos** (semilla 1976).

## Monstruos

Todos los nombres ya existen en `monsters.xml` y **no tenían spawn** en el mapa antes de esta
zona. La dificultad sube con la distancia a la entrada del piso.

| Piso | Etapas |
|------|--------|
| z10 | Poison Spider, Centipede, Tiger → Tortoise, Thornback Tortoise, Dworc Voodoomaster → Blood Crab, Cyclops Drone, Quara Constrictor → Cyclops Smith, Quara Mantassin, Blue Djinn |
| z11 | Earth Elemental, Nightstalker, Blue Djinn → Quara Constrictor, Quara Mantassin, Cyclops Smith → Quara Pincher, Worker Golem, Nightstalker → Quara Predator, Worker Golem, Quara Pincher |
| z12 | Worker Golem, Quara Predator, Nightstalker → Quara Pincher, Quara Predator, Worker Golem → Nightstalker, Quara Predator, Worker Golem |

Jefes (respawn largo, salas laterales o final):

| Jefe | Piso | Posición | Respawn |
|------|------|----------|--------:|
| Dipthrah | z11 | `254,20` | 3.600 s |
| Mahrdis | z12 | `250,24` | 7.200 s |
| Morguthis | z12 | `226,68` | 7.200 s |
| Vashresamun | z12 | `254,52` | 7.200 s |
| Ashmunrah | z12 | `246,72` | 7.200 s |
| Orshabaal | z12 | `262,76` | 14.400 s |

Orshabaal está en la sala final, con un cartel de aviso. El portal de vuelta
(`265,79,12`) lleva a `128,31,9`, al lado de la escalera de mano de la entrada.

Total: **236 monstruos** en 112 centros de spawn (`FORGOTTEN_PIT_SPAWNS` en
`test-spawn.xml`).

## Carteles

Bloque `FORGOTTEN_PIT_SIGNS` de `readables.xml`:

| Posición | Texto |
|----------|-------|
| `128,33,7` | Cartel de la ciudad, junto a la trampilla |
| `122,39,9` | Entrada, niveles, salida a la ciudad |
| `143,26,10` | Galerías Húmedas |
| `240,79,11` | Cavernas Profundas |
| `216,15,12` | El Corazón |
| `258,79,12` | Aviso de Orshabaal |

## Techo (16 nov 2026)

z9 estaba vacío encima del corredor y del primer piso del laberinto (z10). El cliente dibujaba encima las
cuevas de z8 (x 195–280): desde 675 casillas de z10 "se veía lo de arriba". Ahora el generador pone roca
en z9 sobre `CORRIDOR_BOX` y `MAIN_BOX` (con 2 de margen) solo donde no hay tile (`ceiling_tiles`, 8.155
casillas). z11 y z12 ya tenían techo: el piso de arriba del laberinto está entero. Ver
[PIEZAS_DE_MAPA.md#techo](PIEZAS_DE_MAPA.md#techo).

## Regenerar

```bash
python3 scripts/map/generate-forgotten-pit.py --dry-run --preview-dir /tmp/foso
python3 scripts/map/generate-forgotten-pit.py --replace
python3 scripts/map/check-map-load.py
python3 scripts/map/sync-houses-with-map.py --dry-run
python3 scripts/map/scan-map-depots.py server/YurOTS/ots/data/world/test.otbm
python3 scripts/map/check-upper-view.py                 # que desde ninguna cueva se vea el piso de arriba
```

`--replace` vuelve a escribir el bloque `FORGOTTEN_PIT_SPAWNS` al final de `test-spawn.xml`: si los spawns no
cambiaron, conviene dejar el archivo como estaba (`git checkout`) para no ensuciar el diff.

`--replace` escribe:

- `server/YurOTS/ots/data/world/test.otbm` (solo las cajas de la zona; no toca el resto del mapa)
- `server/YurOTS/ots/data/world/test-spawn.xml` (bloque `FORGOTTEN_PIT_SPAWNS`)
- `server/YurOTS/ots/data/readables.xml` (bloque `FORGOTTEN_PIT_SIGNS`)
- `server/YurOTS/ots/data/pvparenas.xml` (vacío)
- `server/YurOTS/ots/data/world/generated-forgotten-pit.json`

El generador valida antes de escribir:

- en la primera ejecución, que las cajas del laberinto (z10–z12) y del corredor no pisen nada
  caminable existente (si ya está el manifiesto, se reescriben como zona propia);
- que la sala de entrada no conserve palanca, teleport ni pads de la arena;
- que la escalera de mano `125,30,9` siga existiendo y se llegue a la bajada `140,28,9`;
- que desde el corredor se alcance la salida de z10 y, en cada piso, la salida y las salas
  laterales;
- que ningún tile caminable vea el borde negro de la caja;
- que todos los spawns caigan en piso caminable y que los nombres existan en `monsters.xml`.

Si algo falla, no escribe nada.

## Pendiente

- **Cliente:** las criaturas importadas de 8.60 (`Tortoise`, `Thornback Tortoise`, `Blood Crab`,
  quaras, `Cyclops Drone/Smith`, `Earth Elemental`, `Worker Golem`, `Nightstalker`) necesitan el
  cliente publicado con `publish_client.py`. Los faraones y Orshabaal son looks de 7.6.
- **Prueba in-game:** recorrer la entrada desde la ciudad, las tres escaleras y el portal final;
  probar que los spawns no se apilan y que Orshabaal no se sale de su sala. No se deployó a la
  ThinkPad.
- La zona no tiene cofre de quest: es caza y jefes, no una quest nueva.
