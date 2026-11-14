# Quests — registro y propuestas

Registro público: **`/quests`** (`web/site/src/pages/quests.astro`). La fuente de datos es
`web/site/src/data/quests.json`; la página se compila en la ThinkPad con `scripts/web/build-site.sh`.

## Qué hay

- **30 entradas existentes**: 25 con cofre o grupo y 5 sistemas repetibles (Daily Task, Wave Arena,
  Reloj de Arena, El Crisol y Arena PvP).
- **40 cofres de quest** en el mapa: 29 con `quest.lua` (uid 1001–4999 y 20100–20199), 4 del
  Annihilator (`5006`–`5009`), 3 del Pharaoh (`5003`, `5004`, `5017`) y 4 de Hell Quest (`5100`–`5103`).
- **8 propuestas** para crear, con nivel recomendado.

## Quests principales

| Quest | Nivel | Jugadores | Dónde | Recompensa |
|---|---:|---|---|---|
| Annihilator | 100–130 | 4 | Sala del Annihilator `194,118,9` | Demon Armor, Sword of Valor, Stonecutter's Axe o Thunder Hammer |
| Pharaoh Quest | 80–100 | 2–4 | Tumbas del desierto `205-209,166,9` | Dragon Lance, War Hammer o Giant Sword |
| Castillo Imperial | 60–80 | 1–4 | Tesorería z3 `97/103,28,3` | Crown Legs y Royal Helmet |
| Hell Quest | 100–130 | 1–7 | Cámara de la Elección z9 | Demon Helmet, MPA, Boots of Haste o Demon Shield |
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

> **Ojo:** los niveles son recomendados, no requisitos. Las únicas puertas de nivel reales son Hell
> Quest (80 y 100) y Arena PvP (25). Los niveles de las quests clásicas se estimaron según los
> monstruos cercanos y el valor de la recompensa.

## Sistemas repetibles

| Sistema | Nivel | Cómo funciona |
|---|---|---|
| Daily Task | 8–100+ | Huntmaster en el templo; 1 contrato por personaje/día, oro o exp, racha hasta +50 %. |
| Wave Arena | 40–100 | 20 oleadas, grupo hasta 7; premios semanales al limpiar 5/10/15/20. |
| Reloj de Arena | 40–100 | 6 oleadas cada 6:30; entra en el descanso. |
| El Crisol | 50–100 | 3 puertas (Bronce/Plata/Oro); rare de Oro, arma Zagan del día. |
| Arena PvP | 25+ | Duelo de 2 jugadores con palanca `7001`. |

## Propuestas para crear

| Quest | Nivel | Jugadores | Recompensa | Por qué |
|---|---:|---|---|---|
| Pits of Inferno | 100–130 | 4–6 | Elegir Avenger, Arcane Staff o Arbalest + loot de demons | Es la fuente que falta para las armas 8.x, hoy solo por GM |
| El Faro de los Contrabandistas | 20–35 | 1 | Serpent Sword + 1.000 gp | Cubre el hueco de nivel 20–35 y reusa piratas |
| Las Minas de los Enanos | 45–65 | 1–2 | Dwarven Axe o War Axe + 5.000 gp | Contenido de enanos y recompensa media |
| La Cripta de los Reyes | 55–70 | 1 | Crown Armor + Crown Legs | Puente entre Knight Legs y armaduras altas |
| El Templo Sumergido | 70–90 | 2–4 | MPA o Sapphire Crown Armor | Aprovecha quaras/elementales 8.6 y da grupo |
| La Forja de los Titanes | 90–110 | 2–4 | Demon Shield + 20.000 gp | Contenido de fuego de alto nivel |
| Expedición semanal: Cazadores del Desierto | 60–100 | 1–4 | Gemas + exp; ranking semanal | Contenido repetible en las 9 zonas del desierto |
| Arena de Jefes | 100–130 | 2–4 | Rare loot + ranking semanal | Objetivo de fin de semana con jefes existentes |

## Mantenimiento

1. Agregar o cambiar una quest en `web/site/src/data/quests.json` (tipo, nivel, ubicación, recompensa,
   notas y `chests` si tiene cofres).
2. Actualizar los contadores de la página (se calculan solos desde el JSON).
3. Compilar y deployar la web: `scripts/web/build-site.sh` y merge en la ThinkPad.
4. Si la quest nueva tiene cofres, verificar los `uniqueId` contra `data/actions/actions.xml` y
   `data/actions/scripts/quest.lua` (el uid del cofre es el id del premio, salvo Annihilator/Pharaoh/Hell).
