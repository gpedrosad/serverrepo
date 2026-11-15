# Elvenbane — fortaleza élfica de Tibia clásico (portal `157,47,7`)

> Documentación completa (cajas, las 19 escaleras con llegadas, spawns, cómo regenerar y validar, renders y diferencias vs la referencia): [`ELVENBANE.md`](ELVENBANE.md).


Recrea **Elvenbane**, la fortaleza élfica del oeste de Ab'Dendriel, en la zona vacía al sur del
templo. Sale de las plantas ASCII de TibiaWiki (`docs/items-and-map/img/elvenbane-ref/`): el
castillo sobre una isla al norte, la tierra firme con bosque y montañas al sur, y el túnel del
sótano que une la bajada de la entrada con el sótano bajo el castillo. Siete pisos.

| Piso | Qué hay |
|------|---------|
| z7 | Entrada (tierra firme al sur): bosque, montañas, llegada del portal, portales de vuelta y la bajada. Al norte, la isla con el castillo (muralla, anillo de pasillo, patio de pasto, torre central y explanada de piedra al sur) rodeada de agua con orilla |
| z8 | Túnel largo N-S + sótano -1 bajo el castillo (sube al patio del castillo y baja al -2) |
| z9 | Sótano -2 (sube al -1 y baja a la prisión) |
| z10 | Prisión -3 (celdas al norte y al centro, sala grande al sur) |
| z6 | Adarve: anillo de muralla con 4 esquinas + torre central |
| z5 | 4 torretas de esquina + torre central |
| z4 | 4 torretas + cima de la torre central (el dragón) |

Generador: `scripts/map/generate-elvenbane.py` (lee `elvenbane_ascii.md` como máscara, resuelve las
escaleras automáticamente y valida alcanzabilidad multi-piso). Manifiesto:
`server/YurOTS/ots/data/world/generated-elvenbane.json`.

## Piezas de z7 (de dónde salen los ids)

| Qué | Ids | De dónde |
|---|---|---|
| Pasto | `4756`; costa `4526` | los dos grounds de pasto que usa el mapa (el `4526` es el que llevan las islas generadas en la costa) |
| Agua | `4608` (shallow water ground) | mar del mapa |
| Orilla pasto↔agua | `4644`–`4655` | set `grass->water` de `map-kb/border_sets.json`, el mismo de `generate-natural-island.py`; se elige con `pieces_for()` (lados, esquinas externas `4648`–`4651` e internas `4652`–`4655`) |
| Piedra del castillo | piso `431`, paredes `1049`–`1053` | `PIEZAS_DE_MAPA.md` (pies de la torre del castillo) |
| Montañitas grises | meseta `4566` (rocks ground) + pared de roca `906` al norte y `903` al oeste | medido en `test.otbm`: las mesetas de roca del mapa usan ese ground y esas dos paredes; **no** se usa `919` (ese ground se dibuja con el sprite desplazado y deja huecos negros si no lleva la pared completa) |
| Poison field (torre z6) | `1490` (cid 2121, sólo `block_pathfind`) | `ITEMS_OTB_DUMP.txt`; `destroyfield.lua` ya lo limpia |
| Árboles | `4009` (pino 2x2), `2768` (arbolito) | `generate-beast-valley.py` / `generate-north-pass.py` |
| Arbustos y flores | `2767`, `2786`, `4158`, `4150`, `2740` | idem |
| Escaleras (18 links) | `409` (ladder down) arriba + `1386` (escalera de mano) abajo | `teleport.lua` (`LADDERS_UP` 1386 sube a `x, y+1`) y `actions.xml` (409 → `teleport.lua`) |
| Buraco de la entrada | `469` (hole, `floorChangeDown`) arriba + `1386` abajo, cercado por 4 piedras `1285` | `shovel.lua` (468→469 con pala; acá queda abierto) y `teleport.lua` (`LADDERS_UP` 1386) |

### Vegetación: densa pero respirable

El bosque cubre **toda** la tierra firme y la franja este/sur de la isla. No hay prados: el único
claro es un corredor de 1–2 casillas que une la bajada `39,340`, la llegada `39,346` y los portales
`41–42,347`, más el anillo de piedra de los portales; el resto es bosque. El **patio del castillo**
(las 21×18 casillas dentro de la muralla, incluido el anillo de pasto) va limpio: sólo pasto y
piedra, sin árboles, arbustos ni flores — el bosque va afuera de la muralla. La densidad se hace con
las copas de los pinos 2x2, no apilando árboles:

- pino grande `4009` sólo si no hay otro a menos de 2 casillas (Chebyshev) y si su bloque 2x2 es
  todo pasto; ocupa 1 casilla para caminar pero se ve en 4;
- en el resto se alterna arbolito `2768` (14 %), arbusto `2767`/`2786` (14 %) y flores (25 %), y
  queda pasto a la vista entre medio;
- ~52 % de las casillas de bosque quedan con algo encima; el resto es transitable, así el bosque se
  ve lleno pero se puede cruzar. `open_pockets()` sólo tala el árbol/arbusto que deje una casilla
  de pasto encerrada (en la última pasada: 42, sobre ~860 de pasto con bosque).

## Recorrido

| Etapa | Piso | Paisaje | Monstruos |
|-------|------|---------|-----------|
| Llegada | z7 sur | claro de pasto con cartel y 2 portales de vuelta | — |
| Entrada (bosque) | z7 sur | bosque cerrado con montañitas, junto a la bajada | Wasp, Orc, Orc Spearman, Elf, Elf Scout, Orc Warrior |
| Túnel | z8 | pasillo largo de tierra | Troll, Orc, Orc Spearman, Dwarf, Minotaur, Orc Warrior |
| Sótano -1 | z8 | rectángulo de salas bajo el castillo | (el mismo grupo) |
| Sótano -2 | z9 | salas grandes | Orc, Minotaur, Orc Warrior |
| Prisión -3 | z10 | celdas 2×3 + sala grande al sur | Minotaur, Orc Warrior, Minotaur Guard |
| Castillo (isla) | z7 norte | muralla, anillo de pasillo, patio y torre central | Minotaur, Orc Warrior, Minotaur Guard, Orc Berserker |
| Adarve | z6 | anillo de muralla | Minotaur, Orc Warrior |
| Torretas + torre | z5 | 4 torretas + torre central | Elf, Elf Scout, Orc Warrior; en la torre Orc Shaman, Elf Arcanist |
| Cima | z4 | 4 torretas + cima de la torre | Orc Berserker, Hunter, Minotaur Archer; en la torre Minotaur Mage, Demon Skeleton y **1 Dragon** |

La dificultad sube de sur a norte (entrada → castillo) y de abajo hacia la torre: el Dragon es el
"jefe" en la cima (z4). Total: **50 spawns y 81 monstruos**. Detalle por monstruo en el manifiesto
(`monsters`).

## Coordenadas

| Qué | Pos |
|-----|-----|
| Portal (plaza del templo) | `157, 47, 7` → llegada `39, 346, 7` |
| Portales de vuelta en la llegada | `41, 347, 7` y `42, 347, 7` → `157, 48, 7` |
| Bajada de la entrada al túnel | `39, 340, 7` → `39, 340, 8` |
| Sótano -1 → patio del castillo | `57, 303, 8` → `57, 303, 7` |
| Sótano -1 → sótano -2 | `58, 313, 8` → `58, 313, 9` |
| Sótano -2 → prisión -3 | `42, 312, 9` → `42, 312, 10` |
| Castillo (muralla) | `40, 298` a `60, 315` (21×18) |
| Caja z7 | x `12–82`, y `282–362` |
| Caja z8 | x `30–67`, y `288–349` |
| Caja z9 / z10 | x `33–67`, y `291–322` |
| Caja z4–z6 | x `38–62`, y `296–317` |
| Poison fields (`1490`) | z6, interior de la torre: x `48–53`, y `303–307` (27 casillas, sin las 2 escaleras) |

### Escaleras

Todas son del estilo de la entrada: **escalera de mano**. Dos pares, siempre en la misma casilla
(arriba / abajo):

- **Escalera de mano (18 links):** `409` (ladder down: hueco con marco de madera y la escalera hacia
  abajo) arriba y `1386` (ladder) abajo. Al usar la `1386` se sube a `(x, y+1)`; al bajar por el `409` se
  cae en la misma casilla (la `1386` no mueve: offset 0, no está en `STAIRS_LANDING`).
- **Buraco de la entrada (`entrada`):** `469` (hole, abrible con pala en el Tibia original) arriba y
  `1386` abajo, rodeado por 4 piedras `1285` (oeste, este, noroeste, noreste) con el sur libre: es el
  aterrizaje de la escalera de mano. En este OT el `469` no tiene decay configurado, así que queda
  abierto de entrada.

No se usan `432`/`1396` (stair down / wooden stairs), ni `1385`, `3685` ni `3687`: en la zona no queda
ninguna casilla con esos ids.

| Etiqueta | Tipo | Arriba (bajada) | Abajo (escalera de mano) |
|---|---|---|---|
| entrada | buraco 469 + 1386 | `39,340,7` | `39,340,8` |
| sotano->patio | 409 + 1386 | `57,303,7` | `57,303,8` |
| sotano->-2 | 409 + 1386 | `58,313,8` | `58,313,9` |
| -2->-3 | 409 + 1386 | `42,312,9` | `42,312,10` |
| patio->adarve NO | 409 + 1386 | `42,299,6` | `42,299,7` |
| patio->adarve NE | 409 + 1386 | `57,299,6` | `57,299,7` |
| patio->adarve SO | 409 + 1386 | `43,312,6` | `43,312,7` |
| patio->adarve SE | 409 + 1386 | `57,312,6` | `57,312,7` |
| torre->adarve | 409 + 1386 | `53,304,6` | `53,304,7` |
| adarve->torreta NO | 409 + 1386 | `43,299,5` | `43,299,6` |
| adarve->torreta NE | 409 + 1386 | `58,299,5` | `58,299,6` |
| adarve->torreta SO | 409 + 1386 | `42,313,5` | `42,313,6` |
| adarve->torreta SE | 409 + 1386 | `58,313,5` | `58,313,6` |
| torre adarve->2 | 409 + 1386 | `48,304,5` | `48,304,6` |
| torreta NO->3 | 409 + 1386 | `42,299,4` | `42,299,5` |
| torreta NE->3 | 409 + 1386 | `57,299,4` | `57,299,5` |
| torreta SO->3 | 409 + 1386 | `42,312,4` | `42,312,5` |
| torreta SE->3 | 409 + 1386 | `58,312,4` | `58,312,5` |
| torre 2->3 | 409 + 1386 | `52,303,4` | `52,303,5` |
Carteles en `readables.xml`, bloque `ELVENBANE_SIGNS`. Spawns en `test-spawn.xml`, bloque
`ELVENBANE_SPAWNS`.

### Escaleras reubicadas

La planta ASCII marca las escaleras con `S`, pero varias no tienen contraparte lógica válida (las
llegadas caían en pared o vacío). `resolve_stair()` las reubica a la casilla caminable más cercana
con llegadas libres; el manifiesto guarda cada reubicación en `relocated`. Con el par de escalera de
mano quedaron 4 reubicadas, todas a 1 casilla del `S`: `sotano->patio` `57,302→57,303`,
`sotano->-2` `57,313→58,313`, `torreta NE->3` `58,299→57,299` y `torre 2->3` `53,303→52,303`
(las demás ya caían donde la llegada al subir, `x, y+1`, es piso). Las celdas de la prisión del -3
que el minimapa dibuja cerradas se abren como piso (`PRISON_DOORS`).

## Vecinos

| Zona | Dónde | Relación |
|------|-------|----------|
| Valle de las Bestias | x 262–361, y 232–378 | Lejos al este; Elvenbane termina en x 74 |
| Reloj de Arena | x 328–348, y 383–401 | Lejos al sureste |
| Templo / plaza de portales | x 146–178, y 36–62 | Al noroeste (el portal `157,47,7` está en la plaza) |

Elvenbane queda en una zona que estaba vacía en z4–z10. Todo lo que no es agua, castillo o bosque
se rellena con roca (z8–z10) o agua (z7); desde ninguna casilla caminable se ve el borde de la caja.

Forma de z7: la **isla** sale de la **máscara de tierra del ASCII `ground`** (la del minimapa),
alineada a la muralla: castillo + lóbulo de bosque al noreste/este + franja sur + restos de la costa
oeste, y después se comen unas casillas de costa con ruido para que no quede un borde prolijo. La **tierra firme** sale del recorte del ASCII `entrance` con un cierre morfológico suave
(tapa agujeros de una casilla) y conserva la costa irregular; se le suma el **brazo de agua del
oeste** (`WEST_ARM`: sale del agua de la caja en x 26 y entra hacia el noreste hasta x 35, con punta
redondeada), que es el `~~~~` del ASCII y corta la costa noroeste. Los charcos interiores chicos se
rellenan y los pedazos de pasto rodeados de orilla pasan a agua. Entre isla y tierra firme hay agua
en todo el ancho: el único acceso es el túnel (z8).

## Reglas que valida el script (si algo falla no escribe nada)

- Caja vacía: se niega a escribir si la caja pisa casillas existentes (verificada vacía en z4–z10).
- Cada escalera con su par correcto (409+1386, o 469+1386 en la entrada) en la misma casilla; las dos llegadas caminables y
  sin otra escalera.
- Alcanzabilidad multi-piso desde la llegada (BFS que sigue escaleras y huecos): todo lo caminable
  se alcanza. El bosque se ajusta (`open_pockets()`) y los pedazos de pasto que quedan rodeados de
  orilla (que bloquea) pasan a agua antes de escribir.
- Spawns solo sobre casillas caminables, lejos de llegadas y escaleras.
- Paredes de cueva con pieza única (`356–367`) y paredes de castillo (`1049–1053`) por vecinas.
- **Orilla exacta**: cada casilla de pasto vecina al agua tiene exactamente las piezas que pide
  `pieces_for()` (nada de cortes rectos ni bordes sueltos); las casillas de piedra y las paredes van
  sin borde.
- **Nada de `919`**: el script falla si quedó una casilla con ese ground (se ve como vacío negro).
- **Poison fields**: el interior de la torre central en z6 (menos las escaleras) lleva `1490`; el
  adarve y las torretas no.

## Regenerar

```bash
python3 scripts/map/generate-elvenbane.py --dry-run                    # valida y no escribe
python3 scripts/map/generate-elvenbane.py --preview docs/items-and-map/img/elvenbane   # escribe + dibuja z4..z10.png
python3 scripts/map/temple-portals.py                                 # portal de la plaza (157) y cartel
python3 scripts/map/check-map-load.py                                 # que el server cargue el mapa
python3 scripts/map/validate-tele-dest.py server/YurOTS/ots/data/world/test.otbm
```

Re-ejecutable y determinista (misma semilla `--seed 76` = mismo mapa). Escribe `test.otbm` (backup
`test.otbm.bak-elvenbane` la primera vez, no va a git), spawns, carteles y manifiesto. Si `test.otbm`
cambió en `main`, no mergear el binario: volver a correr el script sobre el mapa nuevo y después
`temple-portals.py`.

**Estado (2026-11-15):** generada y validada localmente (`check-map-load.py`: 0 errores,
`validate-tele-dest.py`: OK, 81 monstruos sobre casillas caminables, alcanzabilidad multi-piso OK,
0 casillas con ground `919`, orilla exacta en toda la costa, patio del castillo sin vegetación). La
superficie se rehizo para que se parezca a la referencia: isla más grande con bosque al este y al
sur, tierra firme sin agujeros, orilla completa y montañitas de roca (`4566` + `906`/`903`) en vez de
los bloques negros. Las 19 escaleras usan el estilo de la entrada: escalera de mano 409 + 1386 (la
entrada con buraco 469 + 1386 y sus 4 piedras). Falta
deploy y recorrido in-game. Antes de deployar un `test.otbm` nuevo, probar depots in-game
([`../gameplay/DEPOTS.md`](../gameplay/DEPOTS.md)).
