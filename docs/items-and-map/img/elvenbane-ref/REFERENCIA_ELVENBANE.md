# Referencia Elvenbane (Tibia clásico) — datos de layout

Fuente: TibiaWiki (tibia.fandom.com/wiki/Elvenbane), minimapas por piso. Implementado en Tibia 5.0.
Ubicación original: isla al oeste de Ab'Dendriel, rodeada de río/lago; SOLO se entra por una
cueva subterránea cuya entrada está en tierra firme al sur (bajada en la superficie → túnel largo
en el -1 que llega por debajo del castillo).
Pasillos del castillo MUY angostos (1 sqm), característica clave.

Escala de las imágenes: 3 px = 1 sqm. `elvenbane_ascii.md` tiene la conversión 1 char = 1 sqm.
Leyenda ASCII: `~` agua, `.` pasto, `T` árboles/arbustos, `_` piso de piedra/castillo,
`#` pared, `=` piso de tierra/cueva, `^` roca/montaña (o piedra en cueva), `S` escalera/hueco/escalera de mano (punto de cambio de piso), ` ` vacío.

Pisos (Tibia: ground = z7):
- Entrada (z7, tierra firme al sur): bosque con montañitas grises, bajada `S` a la cueva.
  Monstruos: Wasp, Orc, Orc Spearman, Elf, Orc Warrior.
- Piso -1 (z8): túnel largo N-S desde la entrada (sur) hasta el sótano del castillo (norte):
  sótano rectangular ~21x18 con salas, escaleras a la superficie (patio del castillo) y al -2.
  Monstruos: Troll, Orc, Orc Spearman, Dwarf, Minotaur, Orc Warrior.
- Piso -2 (z9): sótano ~21x18, salas grandes, sala NE, sala SE con pilares de roca.
  Monstruos: Orc, Minotaur, Orc Warrior.
- Piso -3 (z10): celdas de prisión (fila de celdas 2x3 al norte y al centro), sala grande al sur.
  Monstruos: Minotaur, Orc Warrior, Minotaur Guard.
- Ground (z7): isla con el castillo ~21x18: muralla exterior con pasillo de 1-3 sqm por dentro
  (anillo), patio de pasto entre muralla y torre central, torre central ~8x8 con escalera,
  4 escaleras en las esquinas del anillo hacia el piso 1. Salida al sur del castillo a una
  explanada de piedra y la orilla. Monstruos: Minotaur, Orc Warrior, Minotaur Guard, Orc Berserker.
- Piso 1 (z6): adarve (anillo de muralla) de 1-3 sqm + torre central; escaleras en las 4 esquinas.
  Monstruos: Minotaur, Orc Warrior.
- Piso 2 (z5): 4 torretas de esquina (3x3 interior) + torre central (~6x6).
  Monstruos: Elf, Orc Warrior.
- Piso 3 (z4): 4 torretas de esquina + torre central (cima).
  Monstruos: Orc Berserker, Hunter, Minotaur Archer.
- Torre central (pisos altos): Orc Shaman, Minotaur Mage, Elf Arcanist, Demon Skeleton, Dragon (1, el "jefe").
Para darle identidad élfica en este server se pueden sumar Elf Scout y Elf Arcanist en las torres.
