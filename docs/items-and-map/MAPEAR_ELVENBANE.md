# Elvenbane — fortaleza élfica de Tibia clásico (portal `157,47,7`)

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
| Sótano -1 → patio del castillo | `57, 301, 8` → `57, 301, 7` |
| Sótano -1 → sótano -2 | `58, 313, 8` → `58, 313, 9` |
| Sótano -2 → prisión -3 | `42, 312, 9` → `42, 312, 10` |
| Castillo (muralla) | `40, 298` a `60, 315` (21×18) |
| Caja z7 | x `18–72`, y `286–360` |
| Caja z8 | x `30–67`, y `288–349` |
| Caja z9 / z10 | x `33–67`, y `291–322` |
| Caja z4–z6 | x `38–62`, y `296–317` |

### Escaleras (el hueco 432 va arriba, la escalera 1385 abajo, en la misma casilla)

| Etiqueta | Hueco (arriba) | Subida (abajo) |
|----------|----------------|----------------|
| entrada | `39,340,7` | `39,340,8` |
| sótano→patio | `57,301,7` | `57,301,8` |
| sótano→-2 | `58,313,8` | `58,313,9` |
| -2→-3 | `42,312,9` | `42,312,10` |
| patio→adarve (4 esquinas) | `42,300 / 58,300 / 43,313 / 57,313` (z6) | mismas casillas en z7 |
| torre→adarve | `53,304,6` | `53,304,7` |
| adarve→torretas (4) | `43,300 / 57,300 / 42,313 / 58,313` (z5) | mismas casillas en z6 |
| torre adarve→2 | `48,304,5` | `48,304,6` |
| torretas→3 (4) | `42,300 / 58,300 / 41,313 / 57,313` (z4) | mismas casillas en z5 |
| torre 2→3 | `53,304,4` | `53,304,5` |

Carteles en `readables.xml`, bloque `ELVENBANE_SIGNS`. Spawns en `test-spawn.xml`, bloque
`ELVENBANE_SPAWNS`.

### Escaleras reubicadas

La planta ASCII marca las escaleras con `S`, pero varias no tienen contraparte lógica válida (las
llegadas caían en pared o vacío). `resolve_stair()` las reubica a la casilla caminable más cercana
con llegadas libres; el manifiesto guarda cada reubicación en `relocated`. Las 13 reubicadas están a
≤ 1 casilla del `S` original (p. ej. `patio→adarve NO` de `42,299` a `42,300`). Las celdas de la
prisión del -3 que el minimapa dibuja cerradas se abren como piso (`PRISON_DOORS`).

## Vecinos

| Zona | Dónde | Relación |
|------|-------|----------|
| Valle de las Bestias | x 262–361, y 232–378 | Lejos al este; Elvenbane termina en x 72 |
| Reloj de Arena | x 328–348, y 383–401 | Lejos al sureste |
| Templo / plaza de portales | x 146–178, y 36–62 | Al noroeste (el portal `157,47,7` está en la plaza) |

Elvenbane queda en una zona que estaba vacía en z4–z10. Todo lo que no es agua, castillo o bosque
se rellena con roca (z8–z10) o agua (z7); desde ninguna casilla caminable se ve el borde de la caja.

## Reglas que valida el script (si algo falla no escribe nada)

- Caja vacía: se niega a escribir si la caja pisa casillas existentes (verificada vacía en z4–z10).
- Cada escalera con hueco 432 arriba y 1385 abajo en la misma casilla; las dos llegadas caminables y
  sin otra escalera.
- Alcanzabilidad multi-piso desde la llegada (BFS que sigue escaleras y huecos): todo lo caminable
  se alcanza. En z7 el script deja el piso cerrado: abre un paso de pasto en la montaña (9 pasos) o
  tapa el bolsón con roca / le saca el árbol que cortaba el paso (13 bolsones), y se niega a escribir
  si queda alguna casilla caminable inalcanzable.
- Spawns solo sobre casillas caminables, lejos de llegadas y escaleras.
- Paredes de cueva con pieza única (`356–367`) y paredes de castillo (`1049–1053`) por vecinas.

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
`validate-tele-dest.py`: OK, 81 monstruos sobre casillas caminables, alcanzabilidad multi-piso OK).
Falta deploy y recorrido in-game. Antes de deployar un `test.otbm` nuevo, probar depots in-game
([`../gameplay/DEPOTS.md`](../gameplay/DEPOTS.md)).
