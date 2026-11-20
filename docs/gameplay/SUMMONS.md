# Summons que siguen al dueño

Desde el 20 nov 2026, los summons de un jugador (`utevo res "nombre`, criaturas de `data/summons.xml`):

| Qué | Cómo |
|-----|------|
| Velocidad | La misma que el dueño. La toman al nacer y se vuelve a copiar en cada paso del dueño: haste, botas o anillos se contagian. |
| Seguir | Cuando el dueño da un paso, el summon que lo sigue ocupa la casilla que el dueño dejó. Se mueve en el mismo momento y a la misma velocidad, así que va siempre un paso detrás. |
| Darse vuelta | Si el dueño camina hacia la casilla de su propio summon, cambian de lugar. Sin esto, el summon pegado detrás taparía la vuelta. No pasa en PZ. |
| Cambio de piso | Escaleras, escaleras de mano, agujeros, teleports, `/c` o cualquier salto lejos: el summon aparece al lado del dueño (con efecto de energía). Primero prueba la casilla de atrás según hacia dónde mira el dueño. |

Mientras pelean, los summons usan su IA de siempre: atacan a su blanco. Solo siguen paso a paso cuando no
tienen blanco (`STATE_IDLESUMMON`). Al cambiar de piso sueltan el blanco y vuelven a seguir.

No se teletransportan a casillas:

- de PZ (el templo, los rellanos marcados como PZ): ahí no puede entrar ningún monstruo;
- sin suelo, con escaleras, agujeros o teleports;
- ocupadas, o bloqueadas por paredes o muebles.

Si no hay lugar, el summon se queda donde estaba. Se acerca solo cuando el dueño vuelve a estar a su
alcance, como antes.

Los summons de monstruos (por ejemplo, los esqueletos de un necromancer) no cambian.

## Código

| Dónde | Qué |
|-------|-----|
| `monster.cpp` `Monster::followMasterStep` | Paso detrás del dueño: la casilla que dejó o, si no puede, una libre a su lado a un paso. |
| `monster.cpp` `Monster::followMasterTeleport` | Aparecer al lado del dueño en el piso nuevo. |
| `monster.cpp` `Monster::syncMasterSpeed` / `setMaster` | Velocidad del dueño. `utevo res` pone al summon en el mapa antes de darle dueño, así que `setMaster` usa `changeSpeed` para que los clientes se enteren. |
| `monster.cpp` `calcMovePosition` | Ya pegado al dueño se queda quieto. Antes elegía otra casilla al azar y "temblaba". |
| `monster.cpp` `onTeleport` | Un summon sin blanco que se teletransporta vuelve a seguir al dueño. Antes quedaba en `STATE_TARGETNOTREACHABLE`. |
| `game.cpp` `thingMoveInternal(Creature*)` | Al final de un paso del jugador en el mismo piso llama a `followMasterStep`. Antes de los chequeos de paso, el cambio de lugar con el propio summon. |
| `game.cpp` `Game::teleport` | Si el jugador cambió de piso o saltó más de una casilla, llama a `followMasterTeleport` de cada summon. |

Errores que ya pasaron (con la prueba de abajo):

- **Monstruo en el mapa antes del dueño.** Asignar `speed` en `setMaster` no alcanza: el cliente sigue con
  la velocidad vieja y la animación no coincide. Por eso se usa `changeSpeed`.
- **Ciclo de pensar cortado.** El teleport de un monstruo le corta el ciclo de pensar, porque recibe su
  propio `onCreatureDisappear`. Después de cualquier teleport del summon hay que llamar a `startThink`
  (`resumeFollowing`).
- **Lo que se ve en el cliente.** `Game::teleport` avisa la llegada de un monstruo con actualizaciones de
  casilla (0x69), una por cada criatura cercana. Es así de antes y no es un error del summon.

## Prueba

Servidor de prueba aparte, sobre una copia de los datos. Se arma como en
[SANITIZER_TESTS.md](../systems/SANITIZER_TESTS.md), con el binario normal, en el puerto 7275 y con los bots
en `116 60 7` (el muelle, fuera de PZ: en PZ no se invoca). Después:

```bash
python3 scripts/ot/test-summon-follow.py --port 7275 --start 116 60 7 --dest 120 46 6
```

El Bot Druid invoca un lobo, camina 13 pasos (5 de vuelta) y el GM lo lleva a otro piso con `/c`. Resultado
del 20 nov:

- 13 de 13 pasos con el lobo en la casilla que dejó el druida, también al darse vuelta;
- velocidad 338 = 338;
- en el piso nuevo, el lobo aparece al lado del druida.

Además, 4 minutos de `exercise-server.py --fuzz` sin caídas.

El servidor espera `utevo res "wolf` sin la comilla de cierre, como lo manda el cliente. Con la comilla dice
"You cannot summon this creature".
