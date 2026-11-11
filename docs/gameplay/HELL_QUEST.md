# Hell Quest — Isla del Infierno

Destino de barco (`hell quest` / `hell`, 20 gp). Reemplaza (nov 2026) a la isla generada de damero
(lava, piedra y madera al azar sobre arena) que tenía 3 demons, 2 dragon lords y Demodras amontonados
y dos cofres de shield of honour (uid 2517, ya no existen).

Generador: `scripts/map/generate-hell-quest.py` (usa las herramientas de `generate-frozen-isle.py` y
`generate-north-pass.py`). Manifiesto: `server/YurOTS/ots/data/world/generated-hell-quest.json`.

## Recorrido y caza

| Zona | Piso | Qué es | Monstruos |
|------|------|--------|-----------|
| Puerto | z7 | llegada `345 211 7`, Nimral `348 210 7` | — |
| Campos de Ceniza | z7 oeste | llanura abierta con charcos de lava | Fire Elemental, Dragon |
| Ríos de Lava | z7 este | dos ríos de lava con vados | Dragon, Dragon Lord |
| Fortaleza del Culto | z7 noroeste | patio de mármol negro, columnas, altar, braseros | Warlock, Necromancer |
| Cráter | z7 noreste | lago de lava con fuentes; bajada `358 146 7` en el santuario (nivel 80) | Dragon Lord |
| Fauces del Infierno | z8 | red de 9 cámaras con lava, unidas en circuito | **Hellhound** (jaurías), Dragon Lord, Demon Skeleton |
| Abismo | z9 | Sala de los Demonios y Nido Negro | Demon, **Black Dragon**, Hellhound |
| Arena del Ashen Lord | z9 | arena con cuatro bocas de lava | **Ashen Lord** (boss, 2 h) |
| Cámara de la Elección | z9 | 4 cofres + portal al templo `130 53 6` | — |

Todo lo no caminable es un mar de lava (en bloques de 2x2, con borde de grava) con un anillo de rocas
alrededor de los caminos y de la costa. 54 spawns, 96 monstruos.

## Restricciones de nivel

| Puerta | Dónde | Nivel |
|--------|-------|------:|
| Santuario de la bajada | z7, `358 148 7`: recinto de ladrillo en el borde del cráter; la escalera está adentro | **80** |
| Puerta del Abismo | z9, `346 170 9`: corta el pasillo del Nido Negro a la arena del Ashen Lord | **100** |

Son puertas `1229` con actionId = nivel + 1000 (`leveldoor.lua`): hay que pararse justo enfrente y
usarla; con nivel, te pasa al otro lado (en las dos direcciones). El generador comprueba que sin cruzar
la puerta no se llega a la escalera ni a la arena. La superficie y sus cazas no tienen restricción.

## La quest: Cámara de la Elección

Detrás del Ashen Lord hay 4 cofres. **Cada personaje se lleva uno solo** (storage `5100` compartido):

| Cofre (uid) | Premio |
|-------------|--------|
| 5100 | Demon Helmet (2493) |
| 5101 | Magic Plate Armor (2472) |
| 5102 | Boots of Haste (2195) |
| 5103 | Demon Shield (2520) |

Script: `data/actions/scripts/hellchest.lua` (registrado en `actions.xml`, uniqueId 5100–5103).
Solo Lua: no hace falta recompilar el server.

## Criaturas nuevas

| Criatura | Look | Vida | Exp | Rol |
|----------|-----:|-----:|----:|-----|
| Hellhound | 238 | 1500 | 1300 | perro infernal rápido (290), en jauría; muerde y escupe una ola corta de fuego (`dragon_firewave`, `soulfire`). Rara: fire sword |
| Ashen Lord | 239 | 32000 | 18000 | boss para grupo: olas y bombas de fuego, great fireball, drena maná, se cura e invoca 2 Hellhounds. Loot: crystal coins, fire axe, demon shield, MPA, demon helmet, demon legs |

- XML: `data/monster/hellhound.xml`, `data/monster/ashen lord.xml`, registrados en `monsters.xml`.
- Sprites: presets `hellhound` (War Wolf 3 en carbón y brasas) y `ashen-lord` (Demon 35 de ceniza
  con magma y cuernos de obsidiana) en `scripts/client-rme/add_recolor_look.py`, aplicados al
  `Tibia.dat`/`Tibia.spr` de `devtools/rme/rme-client-760`.
- Solo usan hechizos que ya existían: no hace falta tocar C++ ni `spells.xml`.
- Igual que el Black Dragon (look 230), **solo se ven con el cliente nuevo**: publicar el
  `Tibia.dat`/`Tibia.spr` antes de abrir el server.

## Regenerar

```bash
python3 scripts/map/generate-hell-quest.py --dry-run --preview /tmp/hell.png   # valida y dibuja
python3 scripts/map/generate-hell-quest.py                                    # escribe
python3 scripts/npc/run_npc_tests.py                                          # el barco tiene golden
```

Caja **x 288–405, y 124–226, z7–z9**. Re-ejecutable y determinista. Escribe `test.otbm` (backup
`test.otbm.bak-hellquest` la primera vez), spawns (bloque `HELL_QUEST_SPAWNS`), carteles
(`HELL_QUEST_SIGNS`), el Nimral del puerto en `npc.xml` y el destino en `boat.lua`.

Valida antes de escribir: costa, bordes de lava (una pieza por casilla: la lava se arma en bloques de
2x2 y se achica hasta que cada casilla tenga pieza), paredes de cueva, que se llegue del puerto a la
bajada, entre pisos, a la arena, a los cofres y al portal, y que nada caminable vea el borde de la caja.
