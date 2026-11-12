# Bases para sprites de criaturas

Catálogo de las criaturas del cliente 7.6 que sirven de base para un preset (1x1 o 2x2, 4 direcciones,
3 cuadros), para elegir una **sin abrir imágenes ni correr `inspect` en muchas**. Buscar por nombre o por
color con grep. Generado con `python3 scripts/client-rme/sprite_tool.py bases --write`: no editar a mano,
volver a generarlo después de crear un look o un monstruo nuevo.

- **Colores:** familias con al menos 5 % de los píxeles, en %. `dark` es el contorno y las sombras casi
  negras; `gray` los grises sin color; `orange` incluye la piel y los marrones.
- **Estudiada:** ya tiene clasificador de partes probado (`BASE_PARTS[n]` en `sprite_kit.py`) o algún
  preset que la usa. Conviene empezar por estas.

Receta: [`SPRITE_RECOLOR_GUIDE.md`](SPRITE_RECOLOR_GUIDE.md).

| Look | Forma | Monstruos y NPC que la usan | Colores (%) | Estudiada |
|-----:|-------|-----------------------------|-------------|-----------|
| 2 | 1x1 | Angry Orc Warlord, Enraged Orc Warlord, Furious Orc Warlord, Orc Warlord | dark 48, gray 34, green 8, yellow 5 |  |
| 3 | 2x2 | War Wolf | gray 80, dark 19 | `hellhound` |
| 4 | 2x2 | Orc Rider | gray 51, dark 36, green 10 |  |
| 5 | 1x1 | Angry Orc, Enraged Orc, Furious Orc, Orc | dark 43, green 31, orange 16, gray 10 |  |
| 6 | 1x1 | Angry Orc Shaman, Enraged Orc Shaman, Furious Orc Shaman, Orc Shaman | dark 44, violet 24, green 12, orange 9, gray 8 |  |
| 7 | 1x1 | Angry Orc Warrior, Enraged Orc Warrior, Furious Orc Warrior, Orc Warrior | dark 44, gray 26, orange 16, green 9 |  |
| 8 | 1x1 | Angry Orc Berserker, Enraged Orc Berserker, Furious Orc Berserker, Orc Berserker Pot Thrower, Orc Berserker | dark 40, green 21, gray 19, red 13 |  |
| 9 | 1x1 | Angry Necromancer, Crucible Bonepriest, Enraged Necromancer, Furious Necromancer, Necromancer | dark 64, gray 22, orange 6, magenta 5 | `BASE_PARTS[9]`; `tide-priest` |
| 13 | 1x1 | Black Sheep | gray 64, dark 28, orange 6 |  |
| 14 | 1x1 | Sheep | gray 66, dark 27, orange 5 |  |
| 15 | 1x1 | Angry Troll, Enraged Troll, Furious Troll, Troll | orange 72, dark 22, red 6 |  |
| 16 | 2x2 | Bear | orange 84, dark 16 |  |
| 17 | 2x2 | Beholder | yellow 73, dark 21 |  |
| 18 | 1x1 | Angry Ghoul, Enraged Ghoul, Furious Ghoul, Ghoul | orange 47, dark 27, yellow 17, red 6 | `BASE_PARTS[18]` |
| 21 | 1x1 | Rat | orange 65, red 21, dark 13 |  |
| 22 | 2x2 | Angry Cyclops, Cyclops, Enraged Cyclops, Furious Cyclops | orange 86, dark 12 |  |
| 23 | 1x1 | Angry Minotaur Mage, Enraged Minotaur Mage, Furious Minotaur Mage, Minotaur Mage | dark 32, gray 22, violet 17, red 11, blue 9, orange 8 |  |
| 24 | 1x1 | Angry Minotaur Archer, Enraged Minotaur Archer, Furious Minotaur Archer, Minotaur Archer | orange 52, dark 38, gray 8 |  |
| 25 | 1x1 | Angry Minotaur, Enraged Minotaur, Furious Minotaur, Minotaur | orange 44, dark 30, red 19, gray 6 |  |
| 27 | 1x1 | Wolf | gray 70, dark 30 |  |
| 28 | 1x1 | Snake | green 56, dark 43 |  |
| 29 | 1x1 | Angry Minotaur Guard, Enraged Minotaur Guard, Furious Minotaur Guard, Minotaur Guard, Murius | dark 39, orange 26, red 13, blue 13, gray 9 |  |
| 30 | 1x1 | Spider | dark 50, red 21, green 19 |  |
| 31 | 1x1 | Deer | orange 41, dark 40, red 15 |  |
| 32 | 1x1 | Dog | orange 66, red 27, dark 7 |  |
| 33 | 1x1 | Angry Skeleton, Enraged Skeleton, Furious Skeleton, Skeleton | dark 37, yellow 27, gray 19, orange 15 |  |
| 34 | 2x2 | Angry Dragon, Dragon, Enraged Dragon, Furious Dragon | green 71, dark 24 | `black-dragon`, `frost-dragon` |
| 35 | 2x2 | Angry Demon, Crucible Bloodreaver, Demon, Enraged Demon, Furious Demon, Orshabaal | red 67, dark 15, orange 13 | `ashen-lord` |
| 36 | 1x1 | Poison Spider | dark 41, orange 26, red 21, yellow 5 |  |
| 37 | 1x1 | Demon Skeleton | red 63, dark 34 |  |
| 38 | 2x2 | Angry Giant Spider, Crucible Venomqueen, Enraged Giant Spider, Furious Giant Spider, Giant Spider, Old Widow | dark 37, orange 27, red 26, yellow 8 | `ice-spider` |
| 39 | 2x2 | Angry Dragon Lord, Crucible Ashlord, Demodras, Dragon Lord, Enraged Dragon Lord, Furious Dragon Lord | red 73, dark 23 |  |
| 40 | 1x1 | Fire Devil | red 72, dark 21, orange 7 |  |
| 41 | 2x2 | Lion | orange 88, dark 12 |  |
| 42 | 2x2 | Polar Bear | gray 76, dark 13, orange 8 |  |
| 43 | 1x1 | Scorpion | orange 49, dark 45 |  |
| 45 | 1x1 | Bug | dark 51, orange 21, gray 13, red 9 |  |
| 48 | 1x1 | Ghost | blue 67, gray 18, dark 15 |  |
| 50 | 1x1 | Orc Spearman | dark 43, green 23, blue 18, gray 12 |  |
| 51 | 2x2 | Green Djinn | green 41, orange 27, cyan 9, red 8, gray 7, dark 6 |  |
| 52 | 1x1 | Winter Wolf | gray 65, dark 35 |  |
| 53 | 1x1 | Frost Troll | cyan 80, dark 20 |  |
| 54 | 2x2 | Witch | dark 60, gray 30, orange 8 |  |
| 55 | 2x2 | Angry Behemoth, Behemoth, Crucible Ironhide, Enraged Behemoth, Furious Behemoth | orange 83, dark 14 | `BASE_PARTS[55]`; `root-colossus` |
| 56 | 1x1 | Cave Rat | gray 68, dark 30 |  |
| 57 | 2x2 | Elite Trainer Monk, Monk, Private Trainer Dummy, Guild Master (NPC) | orange 79, dark 19 | `BASE_PARTS[57]`; `ice-monk`, `novice-monk`, `sparring-monk` |
| 58 | 1x1 | Priestess | dark 56, orange 25, red 19 |  |
| 59 | 1x1 | Angry Orc Leader, Enraged Orc Leader, Furious Orc Leader, Orc Leader | dark 47, gray 32, green 18 |  |
| 60 | 1x1 | Pig | orange 75, dark 24 |  |
| 61 | 1x1 | Goblin | orange 37, green 31, dark 28 |  |
| 62 | 1x1 | Elf | dark 42, orange 25, green 25 |  |
| 63 | 1x1 | Blue Elf Arcanist, Elf Arcanist | dark 41, red 28, gray 15, yellow 8, orange 6 |  |
| 64 | 1x1 | Elf Scout | dark 47, orange 38, yellow 6, red 5 |  |
| 65 | 1x1 | Angry Mummy, Enraged Mummy, Furious Mummy, Mummy | orange 50, yellow 27, dark 22 |  |
| 66 | 1x1 | Angry Dwarf Geomancer, Dwarf Geomancer, Enraged Dwarf Geomancer, Furious Dwarf Geomancer | dark 42, red 37, orange 10, gray 6 |  |
| 67 | 2x2 | Angry Stone Golem, Crucible Frostwarden, Enraged Stone Golem, Furious Stone Golem, Grorlam, Stone Golem | gray 81, dark 16 |  |
| 68 | 1x1 | Angry Vampire, Enraged Vampire, Furious Vampire, Vampire | dark 71, gray 17, orange 6 |  |
| 69 | 1x1 | Angry Dwarf, Dwarf, Enraged Dwarf, Furious Dwarf | dark 42, orange 37, yellow 14 |  |
| 70 | 1x1 | Angry Dwarf Guard, Dwarf Guard, Enraged Dwarf Guard, Furious Dwarf Guard | dark 46, orange 36, gray 14 |  |
| 71 | 1x1 | Angry Dwarf Soldier, Dwarf Soldier, Enraged Dwarf Soldier, Furious Dwarf Soldier | dark 43, orange 22, red 13, blue 11, yellow 6 |  |
| 73 | 1x1 | Angry Hero, Enraged Hero, Furious Hero, Hero | orange 47, red 27, dark 16 | `imperial-hero` |
| 74 | 1x1 | Rabbit | orange 58, red 37 |  |
| 75 | 1x1 | — | blue 53, orange 21, gray 11, dark 10 |  |
| 76 | 1x1 | Swamp Troll | green 78, dark 22 |  |
| 78 | 1x1 | Banshee | dark 47, blue 36, gray 7, orange 6 |  |
| 79 | 2x2 | Ancient Scarab, Angry Ancient Scarab, Enraged Ancient Scarab, Furious Ancient Scarab | dark 45, green 24, violet 15, gray 8, blue 7 | `BASE_PARTS[79]`; `emerald-scarab` |
| 80 | 2x2 | Blue Djinn, Crucible Stormcaller | gray 50, orange 22, blue 19, dark 7 |  |
| 81 | 1x1 | Cobra | magenta 37, dark 31, gray 20, green 9 |  |
| 82 | 1x1 | Larva | green 39, dark 36, yellow 7, violet 6 |  |
| 83 | 1x1 | Angry Scarab, Enraged Scarab, Furious Scarab, Scarab | dark 42, gray 26, green 16, violet 12 |  |
| 84 | 2x2 | Omruc | dark 34, red 24, yellow 21, orange 14, magenta 6 |  |
| 85 | 2x2 | Morguthis | dark 34, red 24, yellow 21, orange 14, magenta 6 |  |
| 86 | 2x2 | Thalas | dark 34, red 24, yellow 21, orange 14, magenta 6 |  |
| 87 | 2x2 | Dipthrah | dark 42, blue 15, red 13, orange 12, cyan 9, yellow 6 |  |
| 88 | 2x2 | Ashmunrah | dark 42, blue 15, red 13, orange 12, cyan 9, yellow 6 |  |
| 89 | 2x2 | Mahrdis | dark 34, red 24, yellow 21, orange 14, magenta 6 |  |
| 90 | 2x2 | Vashresamun | dark 34, red 24, yellow 21, orange 14, magenta 6 |  |
| 91 | 2x2 | Rahemos | dark 42, blue 15, red 13, orange 12, cyan 9, yellow 6 |  |
| 92 | 1x1 | — | orange 80, dark 13, gray 6 |  |
| 94 | 2x2 | Hyaena | orange 73, dark 22 |  |
| 95 | 2x2 | Angry Gargoyle, Enraged Gargoyle, Furious Gargoyle, Gargoyle | gray 71, dark 27 |  |
| 99 | 2x2 | Angry Lich, Enraged Lich, Furious Lich, Lich | dark 51, gray 23, orange 12, green 8 |  |
| 100 | 1x1 | Angry Crypt Shambler, Crypt Shambler, Enraged Crypt Shambler, Furious Crypt Shambler | dark 38, orange 32, red 16, green 5 | `BASE_PARTS[100]`; `drowned-sailor` |
| 101 | 2x2 | Bone Beast | dark 49, gray 38, orange 11 |  |
| 102 | 1x1 | Deathslicer | dark 29, red 24, gray 20, orange 19, yellow 8 |  |
| 103 | 2x2 | Efreet | green 34, dark 19, gray 12, orange 8, violet 8, cyan 6, magenta 5 |  |
| 104 | 2x2 | Marid | blue 35, dark 18, orange 13, red 9, cyan 7, gray 6 |  |
| 105 | 1x1 | Badger | gray 66, dark 33 |  |
| 106 | 1x1 | Skunk | gray 57, dark 42 |  |
| 107 | 2x2 | — | red 67, dark 15, orange 13 |  |
| 108 | 2x2 | Elder Beholder | orange 64, dark 23, yellow 5 |  |
| 109 | 1x1 | Gazer | green 68, dark 28 |  |
| 110 | 2x2 | Yeti | gray 68, dark 13, orange 12 |  |
| 111 | 1x1 | Chicken | gray 53, dark 37, red 6 |  |
| 112 | 1x1 | Crab | orange 48, dark 29, red 22 |  |
| 113 | 2x2 | Angry Lizard Templar, Enraged Lizard Templar, Furious Lizard Templar, Lizard Templar | green 36, dark 34, orange 17, gray 7 |  |
| 114 | 2x2 | Lizard Sentinel | green 39, dark 33, orange 17, yellow 6 |  |
| 115 | 2x2 | Lizard Snakecharmer | dark 37, green 26, violet 13, blue 7, yellow 7 |  |
| 116 | 2x2 | Kongra | orange 60, dark 38 |  |
| 117 | 2x2 | Merlkin | dark 45, orange 42, yellow 5 |  |
| 118 | 2x2 | Sibang | orange 51, dark 38 |  |
| 119 | 2x2 | Crocodile | green 70, dark 26 |  |
| 120 | 2x2 | Carniphila | green 46, dark 44, orange 5 |  |
| 121 | 2x2 | Angry Hydra, Enraged Hydra, Furious Hydra, Hydra | green 76, dark 24 | `BASE_PARTS[121]`; `dark-hydra` |
| 123 | 2x2 | Panda | gray 60, dark 39 |  |
| 124 | 2x2 | Centipede | dark 55, orange 23, yellow 9, red 6 |  |
| 125 | 2x2 | Tiger | orange 61, red 20, dark 17 |  |
| 201 | 2x2 | — | red 67, dark 15, orange 13 |  |
| 202 | 1x1 | — | dark 39, orange 26, red 13, blue 13, gray 9 |  |
| 203 | 1x1 | — | dark 41, red 28, gray 15, yellow 8, orange 6 |  |
| 204 | 2x2 | — | red 73, dark 23 |  |
| 205 | 2x2 | — | gray 81, dark 16 |  |
| 206 | 2x2 | — | orange 79, dark 19 |  |
| 207 | 1x1 | — | dark 39, orange 26, red 13, blue 13, gray 9 |  |
| 208 | 2x2 | — | dark 37, orange 27, red 26, yellow 8 |  |
| 209 | 1x1 | — | dark 64, gray 22, orange 6, magenta 5 |  |
| 210 | 2x2 | — | orange 64, dark 23, yellow 5 |  |
| 211 | 2x2 | Elephant | gray 76, dark 22 |  |
| 212 | 1x1 | Flamingo | dark 38, gray 28, red 18, orange 11, magenta 6 |  |
| 214 | 2x2 | Dworc Voodoomaster | dark 50, green 22, orange 18, gray 6 |  |
| 215 | 2x2 | Dworc Fleshhunter | dark 45, green 37, gray 14 |  |
| 216 | 1x1 | Dworc Venomsniper | dark 48, green 36, orange 10 |  |
| 218 | 2x2 | Terror Bird | dark 36, orange 34, red 17, yellow 12 |  |
| 219 | 2x2 | Tarantula | dark 54, orange 38 |  |
| 220 | 2x2 | Serpent Spawn | dark 38, orange 23, green 18, yellow 15, red 7 |  |
| 225 | 2x2 | Angry Dark Monk, Dark Monk, Enraged Dark Monk, Furious Dark Monk | orange 79, dark 19 |  |
