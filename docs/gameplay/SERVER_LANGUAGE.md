# Idioma visible del servidor: inglés

Desde el 21 nov 2026, todo texto nuevo que vea un jugador debe escribirse en **inglés**:
NPCs, confirmaciones, mensajes de combate/sistemas, nombres de criaturas, carteles y ayuda de GM.
Comentarios, documentación y nombres internos de archivos pueden seguir en español.
Los nombres que escriben los jugadores y los datos runtime no se traducen.

## Corrección aplicada

- **77 carteles** de `data/readables.xml` traducidos; las 81 posiciones del archivo se conservan.
  Portales y zonas mantienen sus destinos, niveles requeridos e instrucciones de acceso.
- Generadores sincronizados con los carteles en inglés, incluso literales partidos en varias líneas.
  No ejecutar un generador antiguo para restaurar texto: tomar siempre su versión actual.
- Crucible, Wave Arena y Chronos/Sand Clock: reglas, estados, ranking, premios y avisos en inglés.
- Confirmaciones de NPCs: `(yes/no)`. Las respuestas antiguas en español siguen aceptándose.
- Padrinazgo: **Sponsorship**, con `!sponsor Name`, `!sponsor accept Name` y `!sponsor` para estado.
  `!padrino` y `aceptar` se conservan como alias; reglas, premios y `sponsors.xml` no cambian.
- Casas, entrenamiento diario, premium vencido, PZ lock, descripciones de los anillos de oro,
  conflicto de Amulet of Loss y server save: mensajes en inglés.
- Ayuda GM en inglés y comandos `/go`, `/level`, `/killmonsters`, `/help`.
  Los cuatro comandos españoles continúan disponibles con los mismos permisos.
  Los nombres de lugares de `gmplaces.xml` pasan a inglés (`temple`, `glacier`, `sewers`, etc.).
- **Lake Custodian** e **Iron Foreman**: nombres y gritos en inglés, registros, spawns,
  extensión de RME, presets y generadores sincronizados. Los nombres de sus archivos XML
  históricos se conservan; no cambiar las referencias `file=` a traducciones inexistentes.
- Trainer Monk y Elite Trainer Monk: frases de entrenamiento en inglés.

## Verificación y límites

Se revisaron literales de los archivos C++/Lua/XML versionados, nombres/descripciones del OTB y
los 101.916 nodos de ítems del mapa. Los cuatro textos incrustados en OTBM ya estaban en inglés.
Las coincidencias restantes con español en el código de juego son entradas de compatibilidad,
no mensajes enviados al jugador. No se modifican traducciones ni contenido de la web.

Validación realizada: sintaxis Lua (`luac -p`), parseo XML/Python, mismos permisos en alias,
resolución de los dos jefes en registro/spawns y comparación de tokens C++: solo cambian
literales y las cinco entradas nuevas de comandos. No se ejecutaron pruebas in-game ni bots.
La traducción no modifica `test.otbm`, stats, loot, cuentas, personajes ni dueños de casas.

## Despliegue — 21 nov 2026

Aplicado en la ThinkPad con autorización de Gonzalo. Código `f9ec655`; compilación limpia
en carpeta nueva `~/build/deploy-english-holes-20261121-120538`: **97,1 s, 0 errores, 0 avisos**.
Binario instalado con contenedor tras save inmediato y `docker stop -t 45`; arranque normal
con `docker start`. SHA-256: `40d85b7656d3662c7440870b6e739e28a914cd3d5200e5c161ddc0a9a8e6d3bd`.

Se aplicaron también las [entradas de cuevas](../items-and-map/HOLE_ENTRANCES.md).
Cliente publicado primero: `clienteretro` **`4121503`**; updater y ZIPs de Mac/Windows
con los mismos 774 archivos. CRC: DAT `48dcdfc7`, SPR `306d68e5`, minimapa `bef2f1ef`.
Verificados los manifests y los tres archivos servidos por HTTP en 8080 y 8076.

Respaldo: `~/backups/pre-deploy-20261121-120538-english-holes`, con copias inicial,
antes del reinicio y tras el guardado de cierre. Cierre ordenado confirmado; carga del mapa
**0,887 s**, probe OK y contenedor healthy, 0 reinicios automáticos, sin errores en el arranque.
Preservados: 1 cuenta, 8 archivos de personajes, 35 archivos de casas, depots, dueños/permisos,
`houseitems.xml`, `sponsors.xml` y config local. Sin suites, bots ni recorrido in-game,
según la indicación del usuario. Procedimiento: [THINKPAD_TEST_SERVER.md](../systems/THINKPAD_TEST_SERVER.md).
