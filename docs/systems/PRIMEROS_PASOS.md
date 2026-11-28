# Primeros pasos y retención

Para saber **en qué paso se va la gente**, **qué hace en sus primeras horas** y **qué tan probable es que se
quede**. Desde el 27 nov 2026. Se suma a las [métricas](METRICAS.md) (embudo de la web, logins, online).

```bash
ssh vps 'python3 ~/apps/serverrepo/scripts/ot/first-steps-report.py'              # personajes nuevos de 30 días
ssh vps 'python3 ~/apps/serverrepo/scripts/ot/first-steps-report.py --days 90'
ssh vps 'python3 ~/apps/serverrepo/scripts/ot/first-steps-report.py --json'       # para bots u otros informes
```

Es de solo lectura (salvo que guarda el modelo en `data/logs/.retention-model.json` cuando lo puede entrenar).
Las cuentas con algún GM no cuentan.

## Qué registra el servidor

El servidor C++ (`source/playlog.cpp`) escribe una línea JSON por evento en `data/logs/play-AAAA-MM.jsonl`, junto a
`logins-*.jsonl`. Runtime: fuera de git, la Mac lo copia con el resto de `*.jsonl` y la limpieza semanal borra lo de
más de 12 meses. Si no se puede escribir, el juego sigue igual.

| Evento | Cuándo | Campos |
|--------|--------|--------|
| `session` | Al salir (o al volver a entrar si la sesión había quedado abierta: `reason` = `relogin`) | `start`, `dur`, `online_s` (segundos realmente en el juego), `lvl0`/`lvl1`, `exp0`/`exp1`, `kills`, `mons` (monstruos matados por nombre), `deaths`, `pvp_deaths`, `died_last` (murió en los últimos 3 min), `last_killer`, `zones` (casillas de 32×32 por piso recorridas), `train_s`, `pz_s`, `party_s`, `says` (hablar en pantalla, incluye NPC), `pms`, `chan`, última posición `x`/`y`/`z` y `hp` (%) |
| `pos` | Cada 2 min de juego, solo hasta nivel 40 | `lvl`, `x`, `y`, `z`, `hp`, `train`, `pz`, `party` |
| `level` | Al subir de nivel | `from`, `to`, `session_s`, posición |
| `death` | Al morir (antes de aplicar la pérdida) | `lvl`, `killer`, `pvp`, `lost_exp`, `kept` (protección de novato), posición |

Todas llevan `t` (epoch), `ts` (ISO UTC), `event`, `name` y `acc`. Los monstruos matados, el chat, el training y las
zonas se suman en memoria y salen en `session`, para no escribir una línea por golpe. Un monstruo cuenta para cada
jugador que recibe exp por él (también los de la party).

Ganchos: `playlogLogin`/`playlogLogout` en `otserv.cpp` (junto a `game_login`/`game_logout`; el id de sesión evita
que un reemplazo de sesión cierre la nueva), `playlogTick` en `Game::checkCreature`, `playlogKill` en
`GameState::recordExpAward`, `playlogDeath` antes de `Player::die()`, `playlogLevel` en `Player::addExp` y
`playlogChat` en `creatureSay`, `creatureSpeakTo` y `creatureTalkToChannel`.

## Qué muestra el informe

1. **Embudo**: visitó la web → descargó → abrió el cliente (por IP) → creó cuenta → entró al juego → jugó 10 min
   el primer día → nivel 10 → 15 → 20 (anidado: cada paso cuenta a los que pasaron todos los anteriores) y cuántos
   volvieron otro día.
2. **Primeros pasos de cada personaje nuevo**: primera sesión, sesiones y días jugados, minutos hasta nivel 10/15/20/30,
   qué hizo el primer día (niveles, monstruos, muertes, zonas, training, chat, party), sus muertes con zona y la última
   sesión (si murió al final, vida, dónde quedó).
3. **Dónde se va la gente**: de los que no volvieron, en qué nivel estaban, cuántos murieron al final de su última
   sesión y en qué zona quedaron. Además, minutos por zona (de las muestras `pos`) y dónde y de qué mueren.
   Las zonas se nombran por los monstruos que aparecen cerca (spawns de `test-spawn.xml`), "depot / templo",
   "ciudad" o "sala de training", con la distancia al depot.
4. **Qué se relaciona con quedarse**: para cada dato del primer día, la correlación `r` (−1 a +1) y el % que se quedó
   por encima y por debajo de la mediana.
5. **Modelo**: regresión logística con los datos del primer día, estandarizados:

   `P(quedarse) = 1 / (1 + e^-(b0 + b1·z1 + b2·z2 + …))`, con `zi = (xi − media) / desvío`

   Los minutos, monstruos, zonas, training y chat entran como `log(1 + x)`. Muestra cada coeficiente y cuántas veces
   cambian las chances de quedarse por cada desvío más (`e^bi`), y el **AUC dejando uno afuera** (0,5 = azar,
   1 = perfecto): con pocos datos es el número honesto. Se entrena solo con 12 o más personajes con resultado y al
   menos 4 en cada grupo; antes de eso muestra **señales de riesgo** (primera sesión de menos de 15 min, murió en la
   primera sesión, no subió de nivel, no habló con nadie, no vuelve hace días), que son hipótesis a confirmar.
6. **Nuevos sin resultado todavía**: su P(quedarse) (con modelo) o sus señales de riesgo, del más en riesgo al menos.

**Se quedó** = volvió a jugar otro día (hora de Chile) dentro de los 7 días de su primer ingreso. Se sabe a los
7 días o apenas vuelve; antes queda "pendiente".

## Qué mirar

- El paso del embudo con la caída más grande es donde conviene trabajar primero.
- Si muchos de los que se fueron **murieron al final de su última sesión**, revisar esa zona y ese monstruo.
- Las zonas donde pasan más tiempo los niveles bajos son las que más vale la pena cuidar (spawns, caminos, carteles).
- Cuando haya modelo: los datos con coeficiente positivo grande son lo que hay que empujar en la primera hora
  (por ejemplo, si hablar con alguien pesa mucho, un NPC o un canal de ayuda que invite a escribir).

Ver también [NIVELES_BAJOS.md](../gameplay/NIVELES_BAJOS.md) (ayudas para los primeros niveles) y
[LOGIN_EVENTS.md](LOGIN_EVENTS.md).

## Pendiente

- Compras y ventas a NPC (qué compran primero) y misiones: no se registran todavía.
- Sumar un resumen de esto a la URL privada de métricas (`/stats/<token>`) para el grokbot.
