# Hechizos nuevos de nov 2026: efectos, avisos y duración en el cliente

Los 8 hechizos de `3a4e69e` (`exori con gran`, `exeta sio`, `exana res`, `exori vis con`, `exura tera`,
`exevo vis tera`, `utito tera`, `utamo mort`) tienen cada uno su efecto dibujado (36–43,
[CLIENT_EFFECTS.md](CLIENT_EFFECTS.md)). Al lanzarlos, el jugador recibe un aviso de lo que pasó. Los que
duran unos segundos muestran un ícono en el panel de condiciones con los segundos que quedan, igual que
Frenzy / Rapid Fire ([SPELL_ATTACK_SPEED.md](SPELL_ATTACK_SPEED.md)).

| Hechizo | Palabras | Voc. | ML / maná | Qué hace | Aviso (verde = `MSG_INFO`, abajo = `MSG_SMALLINFO`) | Ícono con cuenta |
|---------|----------|------|-----------|----------|------------------------------------------------------|------------------|
| Piercing Volley | `exori con gran` | Paladin | 10 / 110 | Línea de 5 casillas, daño físico | (los números de daño) | — |
| Rescue | `exeta sio "Nombre` | Knight | 8 / 80 | Los monstruos que atacan al aliado (radio 4) pasan a atacar al Knight 4 s | Knight: "You draw N monsters away from X for 4 s." · aliado: "K draws the monsters away from you." · fin: "Your rescue ends." · sin monstruos: "No monsters are attacking X." | `rescue` (Knight) |
| Cleanse | `exana res "Nombre` | Druid | 12 / 70 | Saca veneno y parálisis | "You cleanse X: poison and paralysis removed." · al otro: "D cleanses you: …" · sin nada: "The target has no ailments to cleanse." | — |
| Chain Lightning | `exori vis con` | Sorcerer | 14 / 90 | Al monstruo atacado y salta a 2 más (55 % cada salto) | "Your lightning strikes 1 monster." / "Your lightning chains through N monsters." · inmunes: "The lightning has no effect." | — |
| Seed of Life | `exura tera "Nombre` | Druid | 10 / 60 | Cura ya y otra más grande a los 3 s si sigue a 6 casillas | Quien la recibe: "A seed of life will bloom on you in 3 s." → "The seed of life blooms." o "The seed of life withers." · druid: "You plant a seed of life on X." | `seed_of_life` (quien la recibe) |
| Field Detonation | `exevo vis tera` | Sorcerer | 22 / 220 | Detona hasta 3 campos de fuego/energía/veneno en 3×3 | "You detonate N fields." · sin campos: "There are no fire, energy or poison fields around you." | — |
| Counter Stance | `utito tera` | Knight | 10 / 80 | 5 s: los 2 próximos golpes hacen 25 % menos y el daño absorbido vuelve al monstruo | "You take a counter stance for 5 s: the next 2 hits deal 25% less damage." · cada golpe: "Your counter stance absorbs N damage." (+ escudo) · fin: "Your counter stance ends." | `counter_stance` |
| Blood Ritual | `utamo mort` | Sorcerer | 18 / 120 | 4 veces cada 2 s: −30 vida, +60 maná (nunca baja del 25 % de vida, no en PZ) | "Your blood turns into mana for 8 s: 30 health into 60 mana every 2 s." · fin (o al cortarse): "Your blood ritual ends." | `blood_ritual` |

Si se lo dice antes de tiempo: "You can use it again in N s." (sale de `spellCooldownReady`, igual que Frenzy).

## Cómo está hecho

| Dónde | Qué |
|-------|-----|
| `source/spells.cpp` | Los avisos, en cada `luaActionDo*` (helpers `sendSpellText`, `sendSpellTextLater`, `endCounterStance` arriba del archivo). Los avisos de fin van con `addEvent(makeTask(…))` |
| `source/playerstates.h` / `game.cpp` (`applyCounterStance`) | Counter Stance ahora vence a los `DURATION_S` (antes el Lua lo pasaba pero nadie lo usaba: duraba hasta recibir los 2 golpes) |
| `source/magic.cpp` (`getMagicEffect`) | Arreglo del efecto, ver abajo |
| Cliente `clienteretro`: `modules/game_inventory/inventory.lua` | Tabla `TimedIcons`: patrón del mensaje de inicio (con los segundos), mensajes de fin, imagen y tooltip. Los segundos se ven sobre el ícono |
| Cliente: `data/images/game/states/` | `counter_stance.png`, `blood_ritual.png`, `seed_of_life.png`, `rescue.png` (18×18, hechos con un cuadro de cada efecto) |

**No cambiar los textos que prenden o apagan un ícono sin cambiar `TimedIcons` en el cliente.** Un cliente sin
actualizar ve los avisos y los efectos, pero no los íconos.

## El efecto que salía como sangre (arreglado nov 2026)

`exeta sio`, `exori vis con`, `exevo vis tera` y `exeta res` son `offensive = true` con `ATTACK_NONE`. En
`MagicEffectClass::getMagicEffect`, un hechizo ofensivo muestra la sangre del blanco si el blanco es inmune al
tipo de ataque: `(inmunidades & attackType) == attackType`, que con `ATTACK_NONE` (0) **siempre** da verdadero.
Como `doTargetMagic` apunta al propio jugador, en vez de `RALLY_RING`, `CHAIN_ARC`, `DETONATION_RING` (o el
`SOUND_BLUE` de `exeta res`) salía un chorro de sangre, y `DETONATION_RING` no se veía nunca. Ahora la condición
pide además `attackType != ATTACK_NONE`. No cambia nada para los hechizos con daño.

No se arregló pasando esos Lua a `offensive = false`: `offensive` también decide el exhausted (2 s contra 1 s,
[SPELL_EXHAUSTION.md](SPELL_EXHAUSTION.md)).

## Pruebas (2026-11-18)

Binario compilado en la ThinkPad (`~/build/spellfb-src`, 0 avisos) y levantado aparte en el puerto 7276 con una
copia de los datos y los bots de `make-test-bots.py` (al Bot Knight hubo que subirle el ML a 12 para
`utito tera`). Bots en el Valle (312, 357, 7) con un Orc:

- Los 8 efectos llegan con su número (36–43); ninguno sale como sangre.
- `exeta sio` con el orco pegándole al druid: avisos a los dos, y "Your rescue ends." a los 4 s.
- `utito tera` con un Orc Warrior: absorbe un golpe (escudo + aviso), "You can use it again in 29 s." al
  repetirlo, y "Your counter stance ends." a los 5 s aunque quedaba un golpe.
- `exura tera` en el knight: aviso, y "The seed of life blooms." a los 3 s.
- `utamo mort`: aviso, 4 ticks, "Your blood ritual ends." a los 8 s.
- `exevo vis tera` sin campos y `exana res` sin nada que sacar: el aviso de que no hizo nada.
- `exori vis con` sobre el orco: "Your lightning strikes 1 monster."

Los íconos del cliente se probaron con un banco en Lua (widgets y `scheduleEvent` falsos) pasándole esos
mensajes: cada uno aparece con sus segundos, baja de a 1 y se va con su mensaje de fin o al llegar a 0. Falta
verlos en el cliente real.

