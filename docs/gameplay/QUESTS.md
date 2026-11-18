# Quests — registro y propuestas

Registro público: **`/quests`** (`web/site/src/pages/quests.astro`). La fuente de datos es
`web/site/src/data/quests.json`; la página se compila en la ThinkPad con `scripts/web/build-site.sh`.

## Qué hay

- **30 entradas existentes**: 26 con cofre o grupo y 4 sistemas repetibles (Daily Task, Wave Arena,
  Reloj de Arena y El Crisol). La Arena PvP se retiró en nov 2026 (su zona es ahora El Foso Olvidado).
- **44 cofres de quest** en el mapa: 29 con `quest.lua` (uid 1001–4999 y 20100–20199), 4 del
  Annihilator (`5006`–`5009`), 3 del Pharaoh (`5003`, `5004`, `5017`), 4 de Hell Quest (`5100`–`5103`)
  y 4 de los Pozos del Infierno (`5104`–`5107`).
- **8 propuestas** para crear, con nivel recomendado.

## Quests principales

| Quest | Nivel | Jugadores | Dónde | Recompensa |
|---|---:|---|---|---|
| Annihilator | 100–130 | 4 | Sala del Annihilator `194,118,9` | Demon Armor, Sword of Valor, Stonecutter's Axe o Thunder Hammer |
| Pharaoh Quest | 80–100 | 2–4 | Tumbas del desierto `205-209,166,9` | Dragon Lance, War Hammer o Giant Sword |
| Castillo Imperial | 60–80 | 1–4 | Tesorería z3 `97/103,28,3` | Crown Legs y Royal Helmet |
| Hell Quest | 100–130 | 1–7 | Cámara de la Elección z9 | Demon Helmet, MPA, Boots of Haste o Demon Shield |
| Pozos del Infierno | 100–130 | 4–6 | Cámara de las Armas z10 `540,380,10` (tras la puerta 100 y el Arena de las Furias) | Elegir una: Emerald Sword, Avenger, Arcane Staff o Arbalest |
| TP Gauntlet | 80–100 | 1–4 | Sala final `450,77/79,7` | Demon Armor y Fury Cape |
| Isla del Hielo: leñador | 25–45 | 1 | `373,95,7` | Crystal Coin |
| Isla del Hielo: Yeti | 40–60 | 1 | `369,63,7` | Frozen Starlight |
| Isla del Hielo: guarida | 70–90 | 1–4 | `393/397,17,9` | Crimson Wand y Crimson Helmet |
| Desierto: Templo de los lagartos | 40–70 | 1–2 | `242,78,7` | Knight Armor |
| Desierto: Campo de huesos | 45–80 | 1–2 | `257,114,7` | Vampire Shield |

Las **quests clásicas** (Fire Sword, Boots of Haste, Guardian Halberd, Crusader Helmet, Lady Helmet,
Steel Boots, Knight Legs, Helmet of the Ancients, Shield of Honour, Dark Shield, Giant Sword, Bright
Sword, Golden Armor, Amazon Shield) están en la tabla completa del JSON, con coordenadas, recompensa,
nivel estimado y monstruos de la zona.

> **Ojo:** los niveles de la tabla son recomendados. Desde nov 2026 el cofre valida el nivel con
> `CHEST_LEVEL` en `quest.lua` y varias puertas existentes se subieron para que el acceso coincida
> con ese nivel. Ver "Puertas de level" abajo.

## Puertas de level

El nivel de los cofres se protege en dos capas:

1. **Cofre** — `server/YurOTS/ots/data/actions/scripts/quest.lua` tiene `CHEST_LEVEL` con los 40
   cofres y su nivel. Si el jugador no llega, el cofre responde *"You need level X to open this
   chest."* Esto no se puede esquivar por otro camino.
2. **Puertas** — se subieron 8 puertas de level que ya existían en los caminos (cubren Pharaoh,
   Ancients A/B, Shield of Honour, Fire Cave, Knight Legs, Lady Helmet, Steel Boots, Bright Sword,
   Amazon Shield y Boots of Haste). No se agregaron puertas nuevas.

**Intento descartado (nov 2026):** se probó agregar 9 puertas automáticas con
`scripts/map/add-quest-gates.py` en las quests que no tenían puerta (Castillo Imperial, Isla del
Hielo, Desierto, Crusader Helmet, Guardian Halberd, Dark Shield). El resultado quedó mal
ambientado: puertas y paredes sueltas, marcos que no seguían la arquitectura del lugar. Se
quitaron todas del mapa y `generated-quest-gates.json` quedó vacío. El script ahora exige
`--force` y está marcado como descartado; no usarlo para agregar puertas sin revisar el lugar en
RME e in-game.

**Pendiente:** esas quests quedan protegidas solo por el nivel del cofre. Si se quieren puertas
físicas, colocarlas a mano en RME en un paso natural (puerta existente, arco, entrada de
cueva/templo), probar in-game y recién ahí deployar el mapa. El Gauntlet queda sin puerta nueva
a propósito: solo tiene el nivel 80 del cofre.

## Sistemas repetibles

| Sistema | Nivel | Cómo funciona |
|---|---|---|
| Daily Task | 8–100+ | Huntmaster en el templo; 1 contrato por personaje/día, oro o exp, racha hasta +50 %. |
| Wave Arena | 40–100 | 20 oleadas, grupo hasta 7; premios semanales al limpiar 5/10/15/20. |
| Reloj de Arena | 40–100 | 6 oleadas cada 6:30; entra en el descanso. |
| El Crisol | 50–100 | 3 puertas (Bronce/Plata/Oro); rare de Oro, arma Zagan del día. |

## Propuestas para crear

| Quest | Nivel | Jugadores | Recompensa | Por qué |
|---|---:|---|---|---|
| El Faro de los Contrabandistas | 20–35 | 1 | Serpent Sword + 1.000 gp | Cubre el hueco de nivel 20–35 y reusa piratas |
| Las Minas de los Enanos | 45–65 | 1–2 | Dwarven Axe o War Axe + 5.000 gp | Contenido de enanos y recompensa media |
| La Cripta de los Reyes | 55–70 | 1 | Crown Armor + Crown Legs | Puente entre Knight Legs y armaduras altas |
| La Biblioteca Perdida | 35–55 | 1 | Train Wand + runas | El train wand no tiene ninguna fuente; una quest de magos le da un lugar |
| El Templo Sumergido | 70–90 | 2–4 | MPA o Sapphire Crown Armor | Aprovecha quaras/elementales 8.6 y da grupo |
| La Forja de los Titanes | 90–110 | 2–4 | Demon Shield + 20.000 gp | Contenido de fuego de alto nivel |
| Expedición semanal: Cazadores del Desierto | 60–100 | 1–4 | Gemas + exp; ranking semanal | Contenido repetible en las 9 zonas del desierto |
| Arena de Jefes | 100–130 | 2–4 | Rare loot + ranking semanal | Objetivo de fin de semana con jefes existentes |

## Todos los cofres del mapa

La página `/quests` lista los **40 cofres uno por uno**, con coordenada exacta (`x, y, z`), UID, premio y quest. Están ordenados por nivel recomendado de menor a mayor. Se pueden buscar por quest, premio o coordenada.

## Items sin drop de monstruo

Estos items no salen de ningún monstruo y todavía no tienen una fuente clara:

| Item | Fuente actual | Quest propuesta | Nivel |
|---|---|---|---:|
| enchanted spear | Solo GM | El Templo Sumergido | 70–90 |
| train wand | Sin forma de conseguirlo | La Biblioteca Perdida | 35–55 |

La Emerald Sword, la Avenger, la Arcane Staff y la Arbalest ya tienen fuente desde nov 2026: la
Cámara de las Armas de los Pozos del Infierno (uid 5104–5107).

No se listan los objetos de sistema que se entregan por tienda o premium (runas consumibles, trainer dummy, scrolls, accesorios dorados) ni los que ya tienen cofre/quest.

La página `/quests` muestra el ícono de cada recompensa (desde `web/assets/wiki/items/<id>.png`) y
esta lista de pendientes. Para regenerar los íconos: `python3 scripts/web/build-wiki-icons.py`
(también lee `reward_ids` y `pending_items` de `quests.json`).

## Mantenimiento

1. Agregar o cambiar una quest en `web/site/src/data/quests.json` (tipo, nivel, ubicación, recompensa,
   notas y `chests` si tiene cofres).
2. Actualizar los contadores de la página (se calculan solos desde el JSON).
3. Compilar y deployar la web: `scripts/web/build-site.sh` y merge en la ThinkPad.
4. Si la quest nueva tiene cofres, verificar los `uniqueId` contra `data/actions/actions.xml` y
   `data/actions/scripts/quest.lua` (el uid del cofre es el id del premio, salvo Annihilator/Pharaoh/Hell).
