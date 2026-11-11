# Hechizos de versiones nuevas adaptados a 7.6 (nov 2026)

Ocho hechizos que existen en Tibia 8.x en adelante, hechos para Retro76 con la misma idea. Junto con
[`exori hur`](SPELL_EXORI_HUR.md) y [`exori con`](SPELL_EXORI_CON.md), que se rehicieron el mismo día.

Leer también: [`SPELL_RUNTIME.md`](SPELL_RUNTIME.md) (carga y bindings), [`SPELL_EXHAUSTION.md`](SPELL_EXHAUSTION.md)
(ofensivos 2 s, curaciones y buffs 1 s).

## Tabla

| Hechizo | Palabras | Vocación | ML / maná | Qué hace | Daño o curación |
|---------|----------|----------|-----------|----------|-----------------|
| Brutal Strike | `exori ico` | Knight | 3 / 30 | Golpe al blanco pegado (8 casillas de alrededor). Necesita espada, hacha o maza | `nivel/5 + (skill + ataque) × 0.5` a `× 1.5` (TFS) |
| Front Sweep | `exori min` | Knight | 5 / 80 | Barrido a las 3 casillas de adelante. Necesita espada, hacha o maza | `nivel/5 + (skill + ataque) × 0.5` a `× 1.1` (TFS) |
| Wound Cleansing | `exura ico` | Knight | 3 / 40 | Se cura a sí mismo | `(nivel×2 + ML×3) × 0.5` a `× 0.9` |
| Divine Missile | `exori san` | Paladin | 6 / 20 | Proyectil al blanco, hasta 4 casillas | `nivel/5 + ML×1.79 + 11` a `nivel/5 + ML×3 + 18` (TFS) |
| Divine Healing | `exura san` | Paladin | 6 / 50 | Se cura a sí mismo | `(nivel×2 + ML×3) × 0.9` a `× 1.4` |
| Sharpshooter | `utito tempo san` | Paladin | 8 / 150 | +30 de skill (distancia y melee) por 10 s | — |
| Ice Strike | `exori frigo` | Druid | 3 / 20 | Bola de hielo al blanco, hasta 3 casillas, espera corta | `(nivel + ML) × 0.8` a `× 1.0` (como `exori flam`) |
| Eternal Winter | `exevo gran mas frigo` | Druid | 30 / 650 | Tormenta de hielo en el rombo de Poison Storm (72 casillas) | `(nivel×2 + ML×3) × 1.3` a `× 2.0` |

Ejemplos a nivel 100 y ML 20: Brutal Strike con espada (ataque 30, skill 90) 80–200; Front Sweep 80–152;
Divine Missile 67–98; Divine Healing 234–364; Ice Strike 96–120; Eternal Winter 338–520.

Los que necesitan blanco (`exori ico`, `exori san`, `exori frigo`) y los que necesitan arma (`exori ico`,
`exori min`) no se lanzan ni gastan maná si falta algo.

## Adaptaciones a 7.6

- **Daño sagrado (paladin):** 7.6 no lo tiene. Divine Missile hace daño de energía con el proyectil de power
  bolt y anillos dorados.
- **Daño de hielo (druid):** 7.6 no lo tiene. Ice Strike y Eternal Winter hacen daño físico con la bola y los
  efectos del pack "ice" ([`CLIENT_EFFECTS.md`](CLIENT_EFFECTS.md)), como los monstruos de hielo. Con un cliente
  viejo el daño llega pero no se ven los efectos.
- **Sharpshooter:** en las versiones nuevas además baja la velocidad. Acá no: `changeSpeed` pisa el haste
  (`utani hur`) y al terminar lo cortaría.
- **Front Sweep:** el área se arma en Lua según hacia dónde mira el knight (`getCreatureDirection`), porque
  en un área con `needDirection` cada casilla tiene una sola dirección y las esquinas del barrido son de dos.
- **Requisitos:** los hechizos piden magic level, no nivel (así funciona el servidor). Se eligieron para que
  cada vocación los tenga a una altura parecida a la de las versiones nuevas.
- **Curaciones:** usan la fórmula del servidor (`exura`, `exura gran`, `exura vita`), no la de TFS, que está
  pensada para la vida de versiones más nuevas.

## `exeta res` (Challenge)

Ya existía y no se cambió: los monstruos de las 8 casillas de alrededor atacan al knight durante 6 s, sin
cambiar de blanco ni huir. Es la misma idea y la misma área (3×3) que en las versiones nuevas. Ver
[`SPELL_EXETA_RES.md`](SPELL_EXETA_RES.md).

## Archivos

| Archivo | Qué |
|---------|-----|
| `server/YurOTS/ots/data/spells/instant/<palabras>.lua` | Un script por hechizo |
| `server/YurOTS/ots/data/spells/spells.xml` | Entradas (bloque "Nov 2026") |
| `server/YurOTS/ots/source/spells.cpp` / `spells.h` | `getPlayerSkill`, `getPlayerWeapon`, `getCreatureDirection` |

**Necesitan el binario compilado con esos bindings.** Compila en la ThinkPad (Docker i386) sin warnings;
la lógica se probó con un banco en Lua que simula los bindings. Falta probarlos en el juego.

## Probar en el juego

1. Knight con espada: `exori ico` a un monstruo pegado; `exori min` mirando a cada lado (3 casillas de
   adelante); `exura ico` herido.
2. Paladin: `exori san` a 4 casillas (a 5 no sale); `exura san`; `utito tempo san` y mirar el skill.
3. Druid: `exori frigo` a 3 casillas; `exevo gran mas frigo` en un grupo. Se ve el hielo con el cliente nuevo.
4. Sin blanco o sin arma: no pasa nada y no gasta maná.
