# Comandos de GM para probar contenido (19 nov 2026)

> Idioma visible: **inglés**. Ver [política y corrección de textos](SERVER_LANGUAGE.md).
> Comandos principales: `/go`, `/level`, `/killmonsters`, `/help`; los antiguos siguen como alias. Los lugares se listan en inglés con `/go`.

Todos son `access="3"` en `data/commands.xml` y están en `source/commands.cpp` (al final, `gm*`). Los mensajes
salen en azul en la consola. Para el GM invisible ver [GM_INVISIBLE.md](GM_INVISIBLE.md).

**Resumen al entrar:** un GM (`access >= accessprotect`) recibe en la consola, al conectarse, la lista de todos
los comandos de GM (viejos y nuevos) en 5 mensajes: moverse, probar contenido, jugadores y servidor.
`/comandos` la vuelve a mostrar. El texto está en `GM_HELP_SECTIONS` (`commands.cpp`): **si se agrega un
comando, sumarlo ahí**. Se manda desde `Protocol76` al terminar el login (`sendGmCommandsHelp`).

| Comando | Qué hace |
|---------|----------|
| `/god` | Prende/apaga la protección del GM. **Apagada**: los monstruos lo atacan, recibe daño real (la vida no baja de 1, nunca muere), pega sin el `+1337` y camina a la velocidad de su nivel. **Prendida** (lo normal): vuelve con vida y maná llenos. No se guarda: al relogear vuelve a estar protegido. |
| `/ir` | `/ir` solo lista los lugares; `/ir glaciar` (o el principio: `/ir gla`) teletransporta. Los lugares están en `data/gmplaces.xml`. Si la casilla está ocupada cae en la libre más cercana (hasta 3). |
| `/i` | Como antes (`/i 2160 5`) y además por nombre: `/i black fire sword`, `/i platinum coin 50`. Sin cantidad: 1 si se apila, 10 cargas si es runa. Primero busca el nombre exacto (sin mayúsculas); si no, el id más bajo cuyo nombre contiene el texto. |
| `/nivel` | `/nivel 100` o `/nivel 100 Nombre` (jugador online). Sube con `addExp` (vida, maná y cap como al subir jugando) o baja restando lo mismo por nivel. 1–1000. |
| `/skill` | `/skill sword 90 [Nombre]`. Skills: `fist club sword axe distance shielding fishing` (también `puno maza espada hacha distancia escudo pesca`). 10–300. |
| `/ml` | `/ml 60 [Nombre]`. 0–200. |
| `/loot` | `/loot frost dragon 500`: simula 500 muertes con la misma función del juego (`MonsterType::createLoot`, con `lootmul`, rares a la mitad y oro→platino) y lista cuántas veces cayó cada ítem, el % y el oro por muerte. Sin bonus premium ni Golden Ring. 100 por defecto, hasta 10000. No crea nada en el mapa. |
| `/matar` | Saca todos los monstruos a la vista (mismo piso), sin cuerpo ni loot. Los invocados se van con su dueño; los spawns los vuelven a poner. |
| `/comandos` | Muestra otra vez el resumen de comandos de GM. |
| `/speed` | `/speed 300` fija la velocidad del GM (50–1500); `/speed` solo vuelve a la normal (1000 con la protección prendida). |

**Look de GM** (`accesslook`): al mirar un ítem muestra el id de servidor (antes salía el del cliente), action id
y unique id si tiene, la posición y todos los ítems de la casilla (`Tile: suelo encima... abajo...`, `(PZ)`,
`(house)`). Al mirar una criatura: vida, velocidad y posición.

## Cómo está hecho `/god`

Ya antes el GM (`access >= accessprotect`) no recibía daño, los monstruos no lo elegían de blanco y sus golpes
sumaban 1337. `Creature::isGmProtected()` = `access >= accessprotect && !gmMortal` reemplaza esa comprobación en
el daño cuerpo a cuerpo (`game.cpp`), el daño mágico (`magic.cpp`, los 6 `getDamage`), la elección de blanco de
los monstruos (`monster.cpp`) y el ataque de jugadores al GM. Lo demás del GM (sin exhaust, sin cap, sin
mana) sigue igual. `Creature::drainHealth` deja en 1 la vida de cualquier GM en vez de matarlo.

## Lugares de `/ir`

Sacados de los manifiestos `data/world/generated-*.json` (entrada o llegada de cada zona) y comprobados contra
`test.otbm`: 7 caían sobre pared, escalera, agujero o teleport y se corrieron a la casilla libre de al lado
(Kongra, Mage Tower, Fargum, Bamboo, Dungeon, Cripta, Gauntlet). Para agregar uno: una línea `<place>` en
`gmplaces.xml`; se lee en cada `/ir`, no hace falta reiniciar.

## Pruebas

- Compila sin avisos (`make clean`, imagen `serverrepo-yurots:latest`).
- Falta probarlo in-game (lo prueba Gonzalo).
