# Dark Cathedral — referencia de layout (datos, no texto de la wiki)

Fuente: TibiaWiki (tibia.fandom.com/wiki/Dark_Cathedral), mapas de la wiki. Tibia real: oeste de Plains of Havoc, sur de Outlaw Camp, sur del pantano de Venore. Implementada 7.5.

## Imágenes en esta carpeta
- `Dark_Cathedral_0.png` (260x226): superficie z7. Ruina grande gris (piso de piedra) ~ cuadrada en el centro, bordeada por paredes rojas/naranja; jungla/bosque verde alrededor, ríos azules en arco por el norte y el este, casitas sueltas (rectángulos con borde rojo) al oeste/noroeste. Escala aprox 1 px = 1 sqm.
- `Dark_Cathedral_1.png` (515x406, aprox 1 px ≈ 0.5 sqm... medir): piso -1 (z8). Pasillos grises con muros rojos/naranja dentro de roca marrón. Salas etiquetadas A–T. Cueva natural marrón al noreste (G–J: rotworms, tarántulas/poison spiders, undead, slimes+bonelord).
- `Resp-2DC.png` (827x878): piso -2 (z9). Planta simétrica: sala grande al norte (laberinto de columnas), cruz central con "stairs up" en sala octogonal, brazos oeste con 4 salas en H, brazo este con 2 salas romboidales + sala oval grande; anillo de pasillos al sur con 4 salas (2 a cada lado), sala central sur grande (la de la escalera/teleport al -3) y sala final al extremo sur.

## Mapa de referencia de Gonzalo (minimapa, superficie) — descripción
- Catedral central: nave NEGRA larga (norte-sur) — el edificio principal. Entrada abajo (sur) marcada en celeste "Entrada".
- Alrededor: estructuras de paredes naranjas con piso marrón (ruinas):
  - edificio grande con varias salas a la IZQUIERDA (oeste);
  - sala rectangular ABAJO con muchos puntos grises (bancos/escombros);
  - salas pequeñas a la DERECHA (este).
- Franja verde de jungla en ARCO por arriba (norte).
- Dos círculos violeta "Acesso ao -2": uno ARRIBA en la jungla (norte), otro a la IZQUIERDA junto a una sala gris. Es decir, dos bajadas que llevan (vía -1) al -2.

## Respawns piso -1 (de la wiki)
A 2 bandit+2 smuggler | B 2 bandit+2 wild warrior | C 3 bandit+2 smuggler+3 wild warrior | D 3 slime | E 3 poison spider | F 2 bat+1 wild warrior | G rotworm cave | H poison spiders+1 scorpion (cueva) | I undead (skeleton/ghoul) | J slime + bonelord | K 3 wild warrior | L 2 bandit | M 2 centipede | N 6 bandit+2 wild warrior | O 2 bandit+3 wild warrior | P 3 bandit+3 smuggler | Q 3 bandit | R 3 bandit | S 1 assassin+3 bandit | T 2 assassin+4 bandit+1 dark monk

## Respawns piso -2 (de la imagen)
Mayoría monks (marrón) y dark monks (negro), con ghosts, hunters, witches; sala central sur mixta (monk, dark monk, mummy, witch, hunter, stone golem). Sala oeste-sur con 5 ghosts. Sala norte grande: dark monks + monks + ghost.

## Piso -3
Se accede por teleport en la sala grande del sur del -2 tras 6 palancas en 5 salas alrededor (tiempo límite). Opcional para nosotros: dark monks / demon skeletons / boss Rukor Zad (no existe en 7.6; no inventar).

## Monstruos disponibles en el server (data/monster)
bandit, smuggler, wild warrior, assassin, slime, poison spider, bat, rotworm, scorpion, centipede, skeleton, ghoul, ghost, mummy, monk, dark monk, witch, hunter, stone golem, demon skeleton. (No usar dark magician/apprentice/bonelord si no existen.)
