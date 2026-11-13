# Kits de ataque de los monstruos nuevos

Los monstruos agregados en nov 2026 que solo pegaban cuerpo a cuerpo o con un proyectil común (Castillo Imperial y
criaturas de 8.60) tienen 1 o 2 ataques de su tema, con efectos y con el daño escalado a cada uno. Los arma
`scripts/monsters/apply-monster-kits.py`. **Los monstruos de siempre no se tocan**: el script solo cambia los que
están en su tabla `KITS`.

```bash
python3 scripts/monsters/apply-monster-kits.py --dry-run   # qué le toca a cada uno
python3 scripts/monsters/apply-monster-kits.py             # escribe (se puede repetir)
```

## Qué le tocó a cada uno

| Monstruo | Golpe máx. | Kit |
|---|---:|---|
| Barbarian Bloodwalker | 110 | roar burst 4 |
| Barbarian Headsplitter | 50 | roar burst 2, prisa |
| Barbarian Skullhunter | 55 | roar burst 2, prisa |
| Chakoya Toolshaper | 30 | ice strike 1 |
| Chakoya Tribewarden | 35 | ice strike 1 |
| Frost Giant | 90 | ice burst 3 |
| Frost Giantess | 90 | ice burst 3 |
| Husky | 50 | ice touch 1, prisa |
| Imperial Archer | 130 | burst ball 5 |
| Imperial Squire | 28 | earth touch 1 |
| Mutated Tiger | 260 | roar burst 7, prisa |
| Pirate Buccaneer | 150 | cannon ball 5 |
| Pirate Corsair | 170 | cannon ball 5, prisa |
| Pirate Cutthroat | 110 | blade strike 4 |
| Pirate Marauder | 80 | burst ball 2 |
| Tortoise | 40 | earth touch 1 |
| Thornback Tortoise | 55 | earth touch 2, earth burst 1 |
| Mammoth | 100 | earth touch 4, prisa |
| Blood Crab | 70 | earth touch 4 |
| Quara Constrictor | 100 | ice strike 4, drain burst 3 |
| Quara Hydromancer | 80 | ice wave 3, drain strike 3, cura |
| Quara Mantassin | 120 | ice strike 4, prisa |
| Quara Pincher | 230 | earth touch 8, ice strike 6 |
| Quara Predator | 320 | ice strike 8, prisa |
| Cyclops Drone | 60 | roca 18–48 |
| Cyclops Smith | 90 | roca 27–72, earth touch 3 |
| Wyrm | 130 | energy wave 5, energy strike 5, cura |
| Earth Elemental | 80 | earth burst 3, poison strike 3, cura |
| Water Elemental | 100 | ice wave 4, drain strike 4, cura |
| Zombie | 90 | death touch 3, drain strike 2 |
| Vampire Bride | 120 | drain strike 4, death strike 4, cura |
| Worker Golem | 160 | cannon ball 5, cura |
| Undead Gladiator | 150 | blade strike 5, throwing star 45–120 |
| Nightstalker | 110 | drain strike 4, death touch 4, prisa |

Los nombres del kit son `elemento forma escalón`.

## Cómo se arma

- **Elemento** (efecto y tipo de daño): fuego, flecha incendiaria, energía, veneno, flecha y cuchillo envenenados,
  hielo (físico con efectos de hielo, como el del Frost Dragon), muerte, robo de vida, roca, bala de cañón y rugido.
- **Forma**: `strike` (proyectil al blanco), `touch` (mordida o golpe, sin proyectil), `ball` (estalla en 3x3),
  `wave` (cono hacia adelante) y `burst` (anillo alrededor suyo). `ball` y `burst` pegan un 20 % menos.
- **Escalón de daño** (`TIERS`, de 5–20 a 250–450): el que más se acerca al 75 % del golpe máximo del monstruo.
  Los débiles tiran cada 4 s con 25 % de chance; los fuertes, cada 2,5 s con 40 %.
- Extras: `+haste` (se acelera, `orcb_haste`), `+heal` (se cura un escalón por debajo de su daño) y `dist:` (un
  proyectil común con daño del 30 al 80 % de su golpe).

Cada combinación usada es un archivo `k_<elemento>_<forma>_<escalón>.lua` en `data/spells/instant/` o
`data/spells/runes/`, registrado en el bloque `MONSTER_KITS` de `spells.xml` (runas con id 6000+, libres en el
`items.otb`). En el XML del monstruo las líneas agregadas llevan `kit="1"`, que el servidor ignora y que el script
usa para reemplazarlas al volver a correrlo. Los ataques que ya tenía no se tocan.

## Sumar un monstruo

Agregarlo a `KITS` (`"elemento:forma"`, con `-1`/`+1` para bajar o subir el escalón) y volver a correr el script.
Los archivos `k_*.lua` que ya no use nadie se borran solos.

## Otros arreglos de esta tanda

- El spawn de dworcs de `169, 118, 5` tenía dos "dworc voodoomaster", un monstruo que no existe en el servidor:
  ahora son Dworc Fleshhunter.

No está probado en el juego.
