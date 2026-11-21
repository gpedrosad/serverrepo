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

**Activación pendiente:** los mensajes C++ requieren recompilar e instalar el binario;
la publicación de código por sí sola no los activa. Consultar al usuario según `AGENTS.md §5`.
El despliegue debe seguir [THINKPAD_TEST_SERVER.md](../systems/THINKPAD_TEST_SERVER.md).
