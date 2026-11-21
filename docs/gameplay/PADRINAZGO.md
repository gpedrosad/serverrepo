# Padrinazgo

> Idioma visible: **inglés**. Ver [política y corrección de textos](SERVER_LANGUAGE.md).
> Comando principal: `!sponsor Name` / `!sponsor accept Name`; `!padrino` sigue como alias.

Desde el 20 nov 2026: un jugador nuevo elige padrino a un jugador con más nivel. Cuando el nuevo (el ahijado)
llega a ciertos niveles, **los dos** reciben oro y una caja de regalo, y se avisa a todo el server. La idea:
que los veteranos traigan gente y la acompañen, y que el nuevo tenga metas cercanas.

## Cómo se usa

| Quién | Escribe | Qué pasa |
|-------|---------|----------|
| Ahijado (nivel 15 o menos) | `!padrino Nombre` | Le llega el pedido al padrino, que tiene que estar conectado. |
| Padrino (nivel 30 o más) | `!padrino aceptar Nombre` | Dentro de los 5 minutos. Quedan vinculados y el ahijado recibe una novice gift de bienvenida. |
| Cualquiera | `!padrino` | Muestra el estado: tu padrino y el próximo premio, o tus ahijados con su nivel. Sin vínculo, explica cómo usarlo. También entrega premios pendientes. |

Al entrar, un jugador de nivel 15 o menos sin padrino ve el aviso: "Si un amigo te invito, escribe !padrino
Nombre…".

## Premios

| El ahijado llega a | Ahijado | Padrino |
|-------------------:|---------|---------|
| 20 | 2 000 gp + caja | 5 000 gp + caja |
| 35 | 4 000 gp + caja | 10 000 gp + caja |
| 50 | 8 000 gp + caja | 20 000 gp + caja |
| 80 | 15 000 gp + caja | 40 000 gp + caja |
| 100 | 25 000 gp + caja | 80 000 gp + caja |

- La caja es la de [regalos de nivel](LEVEL_UP_REWARDS.md) que corresponde al nivel de **cada uno**: el padrino
  de nivel 90 recibe una heroic gift. Se suma a las cajas normales de cada nivel.
- Cada hito se cobra una sola vez: morir y volver a subir no lo repite.
- Si el padrino no está conectado, su premio queda pendiente y le llega al entrar o al escribir `!padrino`.
- A todos: "Bot Novato, ahijado de Bot Knight, llego a nivel 20: premio para los dos!".
- El oro sale en monedas; si no hay lugar, cae al piso.

## Reglas contra el abuso

- El ahijado tiene que ser **nivel 15 o menos** al pedirlo; el padrino, **nivel 30 o más**.
- No puede ser de la **misma cuenta**. No se compara la IP: los jugadores juegan en la misma red local.
- **Un padrino por ahijado**, para siempre. **Hasta 10 ahijados** por padrino.
- Los GMs no participan, ni de un lado ni del otro.
- Los premios dependen de que el ahijado suba de verdad: con un segundo personaje propio, hay que jugarlo.

## Datos

`data/sponsors.xml` (runtime: está en `.gitignore`; se respalda en el deploy junto con `players`). Una línea
por vínculo:

```xml
<link child="Bot Novato" sponsor="Bot Knight" level="37" done="3" pending="0" since="1795222453"/>
```

- `level`: último nivel conocido del ahijado (para `!padrino` del padrino).
- `done`: un bit por hito ya alcanzado (1 = 20, 2 = 35, 4 = 50, 8 = 80, 16 = 100).
- `pending`: premios del padrino todavía sin entregar.

Se escribe en un `.tmp` y se renombra, así un corte no deja el archivo a medias. Si no existe, se arranca sin
padrinos. Los pedidos sin aceptar viven solo en memoria y vencen a los 5 minutos.

## Código

| Dónde | Qué |
|-------|-----|
| `source/sponsor.cpp` / `sponsor.h` | Todo el sistema: pedidos, vínculos, hitos, premios, archivo. Las constantes (hitos, oro, niveles, tope) están arriba. |
| `commands.cpp` `Commands::sponsor` + `data/commands.xml` | `!padrino` (access 0). |
| `player.cpp` `Player::addExp` | Después de `onLevelAdvance`, `Sponsors::onLevel`. `levelGiftItemId` dejó de ser `static` para usarla acá. |
| `protocol76.cpp` (login) | `Sponsors::onLogin`: premios pendientes y aviso a los nuevos. |
| `otserv.cpp` | Carga `sponsors.xml` al arrancar. |

Los mensajes van **sin tildes**: el cliente 7.6 recibe latin-1 y el resto de los mensajes del server tampoco
las usa.

## Prueba

Servidor de prueba aparte, sobre una copia de los datos y con el binario nuevo, en el puerto 7275. Los bots
van en `116 60 7`. `make-test-bots.py` crea también la cuenta **111113** con **Bot Novato** (nivel 8): los
demás bots comparten cuenta y el padrinazgo no lo permite.

```bash
python3 scripts/ot/test-sponsor.py --port 7275
```

Resultado del 20 nov 2026: todo OK.

| Qué se probó | Resultado |
|--------------|-----------|
| Reglas | Rechaza al padrino desconectado, al de nivel 20 y al de la misma cuenta |
| Pedido y aceptación | Caja de bienvenida; no se puede pedir un segundo padrino |
| Hito 20, padrino conectado | Premios a los dos y aviso a todos |
| Hito 35, padrino afuera | El padrino lo cobró al entrar |
| Bajar y volver a subir | Sin premios repetidos |
| `!padrino` | Estado correcto de los dos lados |
| Reinicio | El vínculo sigue |

Además, 2 minutos de `exercise-server.py --fuzz` sin caídas.

Error que ya pasó en la prueba: en el muelle el bot queda "en pelea" y el logout (`0x14`) no lo deja salir.
Sigue conectado, cobra en esa conexión y al volver es un *reattach*. El test usa `/kick` del GM.
