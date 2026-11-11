# Spell: `utevo vis` (Eco)

Hechizo de sorcerer que rompe el esquema de "más daño": no pega, hace que **el próximo golpe se repita
solo**, más débil. Nov 2026.

## Cómo funciona

1. Lanzas `utevo vis`: el Eco queda activo **6 s**.
2. El primer golpe a un blanco que salga bien en ese tiempo se **repite 1 s después**, contra el mismo
   blanco, al **50 %** del daño (**25 %** si el blanco es un jugador). La repetición no cobra maná ni
   agrega espera.
3. Si cambiaste de blanco o quedó fuera de alcance o detrás de una pared, el eco se pierde
   ("The echo fades").
4. El Eco se puede volver a lanzar a los **25 s**. Antes avisa "Echo is ready in N s" y no cobra.

| | |
|---|---|
| Palabras / nombre | `utevo vis` / Echo |
| Vocación | Sorcerer (para sumar Druid: `<vocation id="2" />` en `spells.xml`) |
| ML / maná | 20 / 120 |
| Espera al lanzarlo | la de los buffs (1 s): no cuesta un turno de ataque |
| Repite | solo los hechizos con `echo="1"` en `spells.xml`: `exori flam`, `exori vis`, `exori mort`, `exori vis hur`, `exori frigo`, `exori san` |
| Nunca repite | áreas, runas, curaciones, buffs ni otro Eco |
| Visual | sonido violeta en el jugador al cargar el eco y al salir la repetición |

Por qué así (cómo se limitó para que no combee): solo golpes a un blanco (nada de UE ni Eternal Winter
dobles), a la mitad, una vez cada 25 s y sin costar un turno. Es más o menos medio golpe extra cada 25 s:
un pico de daño, no un multiplicador. Para ajustar: subir el 50 % o bajar la espera, sin abrir combos.

## Ajustar sin compilar

Los números están arriba de `data/spells/instant/utevo vis.lua`: `VENTANA` (6), `ESPERA` (25), `ESCALA`
(0.5), `ESCALA_PVP` (0.25). Para que otro golpe se pueda repetir, agregarle `echo="1"` en `spells.xml`
(solo golpes a un blanco). El retraso de 1 s está en `ECHO_DELAY_MS` (`spells.cpp`).

## Cómo está hecho (C++)

| Pieza | Dónde | Qué hace |
|-------|-------|----------|
| `echo="1"` | `spells.xml` → `Spell::isEchoable()` | Marca los golpes que se pueden repetir |
| `echoReady(cid)` | `spells.cpp` | Segundos que faltan para poder lanzar el Eco; si falta, avisa |
| `startEcho(cid, ventana, espera, escala, escala_pvp)` | `spells.cpp` | Deja el Eco activo (estado por jugador en `echoStates`) |
| `SpellScript::onPlayerSpellCast` | llamado desde `Game::creatureSaySpell` cuando un hechizo de jugador sale bien | Si el hechizo admite eco y el Eco está activo, lo consume y programa la repetición con `addEvent` |
| `SpellScript::castEcho` | tarea programada (toma `gameLock`) | Vuelve a lanzar el script con `echoCast = true` |
| `SpellScript::echoCast` / `echoScale` | `doTargetMagic` / `doAreaMagic`, `creatureOnPrepareMagicAttack`, la espera en `game.cpp`, `reduceExhaustion` | Mientras dura la repetición: maná 0, daño × escala, sin chequear ni aplicar espera |

Los GM (access alto) usan otro camino en `creatureSaySpell` y no disparan el eco.

## Probado

En la ThinkPad, con un servidor aparte (puerto 7181) y un sorcerer de prueba:

- `utevo vis` cobró 120 y `exori flam` 20; la repetición salió a los 1001 ms, con éxito y al 50 %, sin
  cobrar maná (log del servidor y maná del paquete de estado).
- El siguiente `exori flam` cobró 20 y no se repitió (el Eco ya se había gastado).
- `utevo vis` en espera no cobró.

Falta probarlo con el cliente: que se vea bien y que se sienta bien de daño.
