# Servidor de prueba en la ThinkPad

Por ahora no hay servidor de producción: la ThinkPad corre el único servidor. Los deploys ahí van **solo con
el OK de Gonzalo** (ver `CLAUDE.md` de la carpeta de proyectos). La Mac mini no compila.

| Item | Valor |
|------|-------|
| Acceso | `ssh thinkpad` (usuario `gonzalo`, ya en el grupo `docker`) |
| Repo | `~/apps/serverrepo`, rama `main` |
| Contenedor | `yurots`, creado con **`docker-compose.prod.yml`** (`docker compose -f docker-compose.prod.yml up -d`); monta `server/YurOTS` → `/app/YurOTS` |
| Log | `server/YurOTS/ots/yurots.log` (rota a `yurots.log.1` al arrancar si pasa de 20 MB) y `docker logs yurots` (tope 3 × 10 MB) |
| Dirección | `192.168.1.17:7171` (red local; `ip` en `config.lua`) |
| Binario | `server/YurOTS/ots/source/yurots`, compilado ahí mismo |
| Personaje GM | **GM Retro** (access 3, vocación 0). La cuenta está en `server/YurOTS/ots/data/accounts/` de la ThinkPad (no va a git); pedírsela a Gonzalo |
| Web | contenedor `retro76-web` (`python:3.12-slim`, `--restart unless-stopped`, red del host, usuario `gonzalo`) que corre `web/server.py` del repo en el puerto **8080**: http://192.168.1.17:8080. Tras cambiar `web/*.py`: `docker restart retro76-web`; `web/dist` y los datos se leen en cada pedido. Python 3.12 porque `server.py` usa `cgi` (no existe desde 3.13) |
| Web 2 (8076) | servicio de usuario systemd `retro76-web.service` (`~/.config/systemd/user/`), corre el mismo `web/server.py` del repo en el puerto **8076**: http://192.168.1.17:8076. Tiene que llevar `SERVER_IP=192.168.1.17` (con `127.0.0.1` la web les decía a los jugadores que se conecten a la propia ThinkPad). Tras cambiarlo: `systemctl --user daemon-reload && systemctl --user restart retro76-web` |
| Mapas (8077) | http://192.168.1.17:8077: mapa interactivo de monstruos, pisos y zonas de lo deployado. Servicios `retro76-mapas` y `retro76-mapas-refresh.timer` (regenera solo cada 10 min si cambió el mapa); ver [MAPA_DE_MONSTRUOS.md](../items-and-map/MAPA_DE_MONSTRUOS.md#sitio-de-mapas-en-la-thinkpad-toda-la-red) |
| Cliente | `~/apps/clienteretro` (mac/ + windows/). Se actualiza solo al abrirse desde la web (`/api/updater.php`); tras cambiar sprites o Lua del cliente: `python3 scripts/client-rme/publish_client.py` ([CLIENT_UPDATER_RETRO76.md](../CLIENT_UPDATER_RETRO76.md)). En la Mac de Gonzalo: `~/Desktop/Retro76-Mac` (binario + `data.zip`, el zip de descarga) |

Los datos de jugadores de la ThinkPad son de prueba, pero igual se respaldan antes de reiniciar.

## Ojo: otras sesiones trabajan ahí

El repo de la ThinkPad suele tener **cambios sin commitear de otra sesión** (C++, `config.lua`, `web/dist`,
el `Tibia.dat`/`.spr` de RME). No hay que hacer `stash`, `reset` ni `checkout` de esos archivos. Antes de
actualizar, comprobar que los archivos que trae `main` no son los mismos que ellos tocaron:

```bash
ssh thinkpad 'cd ~/apps/serverrepo && git fetch -q origin main && \
  comm -12 <(git diff --name-only HEAD origin/main | sort) \
           <((git diff --name-only; git ls-files --others --exclude-standard) | sort)'
```

Si esa lista está vacía, `git merge --ff-only origin/main` actualiza sin tocar lo de ellos. Si no está
vacía, parar y preguntar.

## Deploy de cambios de datos (mapa, spawns, NPC, Lua, carteles)

Sin compilar. Es lo que se hizo con el Valle de las Bestias, el Reloj de Arena y el barco (nov 2026):

```bash
# 1. jugadores conectados (el reinicio los saca un momento)
python3 scripts/ot/ot-probe.py 192.168.1.17 7171

# 2. respaldo, actualizar y reiniciar (el servidor guarda a los conectados al recibir SIGTERM; -t 45 le da tiempo)
ssh thinkpad 'set -e; cd ~/apps/serverrepo; D=server/YurOTS/ots/data; B=~/backups/pre-deploy-$(date +%Y%m%d-%H%M%S)
  mkdir -p "$B"; for f in players accounts vip online.xml queue.xml houseitems.xml houses private_trainers.xml; do
  [ -e "$D/$f" ] && cp -a "$D/$f" "$B/"; done
  git merge --ff-only origin/main || { echo "main no avanza solo: ver abajo"; exit 1; }; docker restart -t 45 yurots'

# 3. comprobar: guardó, cargó el mapa y está "healthy"
ssh thinkpad 'docker logs --since 3m yurots 2>&1 | grep -i "graceful\|Loaded in\|Running\|error"; docker ps | grep yurots'
python3 scripts/ot/ot-probe.py 192.168.1.17 7171
```

En el log tiene que aparecer `graceful shutdown complete`, `Loaded in …` (el mapa) y
`Retro76 Server Running...`. Antes de reiniciar, conviene correr en la Mac `scripts/map/check-map-load.py` y
`scripts/npc/run_npc_tests.py`.

## Cambios de C++

Se compila en la ThinkPad con la imagen del servidor (`serverrepo-yurots:latest`, sin `--platform`), en
una **copia aparte** del código, así no se mezcla con lo que esté a medio hacer:

```bash
ssh thinkpad 'rm -rf ~/build/deploy-src && mkdir -p ~/build/deploy-src && \
  rsync -a --exclude "*.o" --exclude yurots ~/apps/serverrepo/server/YurOTS/ots/source/ ~/build/deploy-src/ && \
  cd ~/build/deploy-src && docker run --rm --entrypoint "" -v "$PWD":/src -w /src serverrepo-yurots:latest make -j4 yurots \
  > build.log 2>&1; tail -1 build.log; grep -c "warning:" build.log'
```

Tiene que terminar con la línea del link (`g++ -o yurots ...`) y **0 avisos**: el `Makefile` compila con `-Wall`
y un aviso nuevo suele ser un error de verdad ([SANITIZER_TESTS.md](SANITIZER_TESTS.md)). Después de cambios
grandes de C++ conviene repetir ahí las pruebas con sanitizers y bots.

Para cambiar el binario: respaldarlo, `docker stop -t 45 yurots` (guarda a los conectados), copiarlo **con
un contenedor** (el archivo es de `root`: un `cp` común da "Permiso denegado" y el servidor queda apagado) y
`docker start yurots` (o `docker compose -f docker-compose.prod.yml up -d` si cambió el compose: lo recrea):

```bash
docker run --rm --entrypoint "" -v ~/apps/serverrepo/server/YurOTS:/app/YurOTS -v ~/build/deploy-src:/new \
  serverrepo-yurots:latest cp /new/yurots /app/YurOTS/ots/source/yurots
```

Si al compilar con `rsync` no cambia nada, `make` no recompila: los archivos copiados conservan la fecha. Hacer
`touch` de los `.cpp` cambiados o compilar en una carpeta nueva.

## Si la ThinkPad tiene commits propios sin pushear

Pasó el 2026-11-13: otra sesión commiteó "El Crisol v3" directo en `~/apps/serverrepo` y no lo pusheó, así que
`git merge --ff-only origin/main` falla ("Diverging branches"). Ojo: con `set -e`, un `merge ... && docker restart`
no corta al fallar el merge y reinicia igual con el código viejo; por eso el comando de arriba sale con `exit 1`.

Sin `reset` ni `rebase` (es trabajo de otra sesión):

1. `git log --oneline origin/main..HEAD` para ver qué commits son solo de la ThinkPad.
2. `git merge --no-edit origin/main` con el autor del último commit (`git -c user.name=... -c user.email=...`).
3. Si choca solo el historial de este archivo, quedarse con las dos filas.
4. Reiniciar y comprobar. El merge queda en la ThinkPad; cuando esa sesión pushee, sube con su commit.

## Si `main` trae archivos que otra sesión tiene sin commitear

Pasó el 2026-11-11 (`config.lua`, `game.cpp` y páginas de `web/dist`). Sin `stash` ni `reset --hard`:

1. Respaldar en `~/backups/deploy-FECHA/`: `git diff --binary` de todo, el parche de los archivos en
   conflicto, una copia (`tar`) de esos archivos y los datos de jugadores.
2. `git checkout -- <solo esos archivos>`, `git merge --ff-only origin/main`.
3. Volver a aplicar sus cambios de código con `git apply --3way <parche>` y `git reset -q` (solo saca del
   índice; no toca archivos). Los generados (`web/dist`) se restauran tal cual desde la copia.
4. Comprobar que no hay marcas de conflicto, que la lista de archivos con cambios es la misma de antes y
   que su diff quedó idéntico. Si algo falla, restaurar desde la copia.
5. Compilar como arriba: el binario lleva su C++ sin commitear y el de `main`.

## Historial

| Fecha | Qué | Commit |
|-------|-----|--------|
| 2026-11-11 | Valle de las Bestias (reemplaza al Hunt Maze), barco (GM viajan a todo), Reloj de Arena chico con oleadas, Paso del Norte e Isla del Hielo compactados | `9d2ca0d` |
| 2026-11-11 | Binario nuevo: `exori hur` / `exori con` de cero, 8 hechizos de versiones nuevas, Eco (`utevo vis`); sin VPS en el repo. Se combinó con el power hit sin commitear de otra sesión (respaldo en `~/backups/deploy-20261111-202201`) | `2d1d2b5` |
| 2026-11-11 | `main` completo: power hit (C++ y config), footer y wiki nuevos, catálogos `/items` y `/items-all` con los sprites actuales. Binario compilado desde `main` en `~/build/deploy-src`; web pasada a contenedor (`retro76-web`). Respaldo en `~/backups/deploy-20261111-223517` | `ddecc7b` |
| 2026-11-11 | Armas de 8.x (Emerald Sword, Avenger, Arcane Staff, Arbalest): binario nuevo (ataque de la ballesta), otb y cliente. Respaldo en `~/backups/deploy-20261111-225503` | `c0811e1` |
| 2026-11-11 | Auto-actualización del cliente: `publish_client.py`, `web/updater/files/`, zips de descarga con `data.zip`; `clienteretro` apunta a `192.168.1.17` | ver git log |
| 2026-11-12 | `exori gran` más chico (12 casillas) con efecto nuevo `NM_ME_WHIRL_SLASH` (35, pack "gran" de `add_drawn_effects.py`): solo Lua + cliente publicado con `publish_client.py` | ver git log |
| 2026-11-12 | Binario nuevo con los arreglos de las pruebas con sanitizers ([SANITIZER_TESTS.md](SANITIZER_TESTS.md)): caída remota sin login, auto-walk vacío, carrera en la config. Build con `-Wall` y 0 avisos. Contenedor recreado con `docker-compose.prod.yml` (tope de log de Docker); el healthcheck ya no llena el log. Respaldo en `~/backups/pre-deploy-20261112-sanitizers` | ver git log |
| 2026-11-12 | Binario con las tres cuentas de azar corregidas como opción de `config.lua` (`fixlootchance`, `fixchangetarget`, `fixshielddefense`), apagadas: el juego no cambia. Respaldo en `~/backups/pre-deploy-20261112-fixflags` | ver git log |
| 2026-11-12 | `config.lua`: `fixlootchance = 1` y `fixchangetarget = 1` (loot con la chance configurada, monstruos que no cambian de blanco en cada turno); `fixshielddefense` queda en 0. Solo config + reinicio. Respaldo en `~/backups/pre-deploy-20261112-fixon` | ver git log |
| 2026-11-12 | Castillo Imperial (6 pisos, The Fallen Emperor, Imperial Hero/Archer/Squire, Court Mage), Crown Armors de loot (binario nuevo: −10% de daño en `applyAmulets`), `lootmul = 1`, y Dark Hydra, Emerald Scarab y Root Colossus del Valle de las Bestias. Binario compilado desde `main` (`git archive origin/main` en `~/build/deploy-src`); el `ip` local de `config.lua` se respaldó y se volvió a aplicar. Cliente publicado (looks 240–244, ítems 20161–20164). Respaldo en `~/backups/pre-deploy-20261112-121306-castillo` | `52fbaef` |
| 2026-11-12 | Revisión de los ítems Zagan: 38 dibujos nuevos (`recolor_zagan_items.py`), `20126` pasa a "train wand", `20148` a las piernas, Aurora Shield (`20165`) y el Ice Monk la suelta. Solo datos (otb, monstruo) + cliente publicado | ver git log |
| 2026-11-12 | Isla natural rehecha: herradura chica con sendero, 3 campamentos Cyclops y cueva de 4 salas hasta el Grorlam ([MAPEAR_ISLA_NATURAL.md](../items-and-map/MAPEAR_ISLA_NATURAL.md)). Solo datos (mapa, spawns, carteles) | `06d5726` |
| 2026-11-12 | Sin ramas sueltas (4224) en la Isla natural, el Valle de las Bestias y el Paso del Norte: 42 sacadas del mapa y de los generadores. Solo mapa | ver git log |
| 2026-11-12 | **Desierto de las Ruinas** (la ciudad del desierto pasa a zona de caza: 9 lugares, 2 jefes, 2 cofres; sin Desert Street, Sand Mansion ni su Seller) y **mesones de vuelta bajo los 11 lockers** del templo. Solo datos (mapa, spawns, casas, NPC, cartel) + reinicio. Falta la prueba de depot dentro del juego | ver git log |
| 2026-11-12 | Lockers del templo girados: la cerradura mira al jugador (estaban al revés, se habían tomado las bisagras por el frente). Solo mapa + reinicio | ver git log |
| 2026-11-13 | **25 criaturas del cliente 8.60** (`import_client_look.py`): piratas en la cubierta del barco del desierto; chakoyas, husky, bárbaros, Frost Giant/Giantess, Ice Golem, Crystal Spider y Frost Dragon Hatchling en la Isla del Hielo Eterno; Bog Raider en una ciénaga nueva del desierto; Wyvern, hatchlings de dragón y mutated sin spawn. Datos (monstruos, hechizos, spawns, mapa del desierto) + cliente publicado | ver git log |
| 2026-11-13 | **El Crisol v3**: hub 11x8 y 3 arenas 11x9 decoradas (de 1376 a 559 casillas), generador con validación por flags del `.otb`, llegadas del grupo en el bloque `LAYOUT` de `crucible.lua` (tope 7), portal del templo a `83,85,0`. Solo datos (mapa, Lua, carteles) + reinicio | ver git log |
| 2026-11-13 | Kits de ataque para 15 monstruos nuevos (Castillo Imperial y criaturas de 8.60) con ataques de su tema y daño escalado (`apply-monster-kits.py`, 4 hechizos y 7 runas `k_*`); los 2 "dworc voodoomaster" del spawn de `169, 118, 5` pasan a Dworc Fleshhunter. Solo datos + reinicio | ver git log |
| 2026-11-13 | **Wave Arena v2 "Claro de la Selva"**: campamento PZ + claro 13x11 de bambú, grupo hasta 7, 20 oleadas con jefe cada 5 que escalan con el grupo, marca por oleada limpia, palanca de retirarse (7103) y premio semanal. `roomkit.py` común con el Crisol. Solo datos (mapa, Lua, actions, carteles, web) + reinicio | ver git log |
| 2026-11-13 | **Frozen Isle corregida**: bote completo, llegada a z9 libre, spawns únicos, paso de hielo/costa nevada y decoración menos densa. Preflight con copia aislada (7173): depot con objetos guardados y ambas escaleras recorridas mediante cliente de protocolo. Solo datos + reinicio ordenado; probe posterior OK / healthy. 1 cuenta, 6 personajes y 31 casas preservados; config local intacta. Respaldo `~/backups/pre-deploy-20261113-165043-frozen`. Falta recorrido visual completo con cliente gráfico. | `a526166`, informe `e80fddb` |
| 2026-11-13 | **Islote del Minotauro**: islote en el canal junto al muelle (puente de madera, 8 Minotaur y 2 Archer) y cuevas z10–z12 con Archer, Guard y Mage cada vez más fuertes ([MAPEAR_ISLOTE_MINOTAURO.md](../items-and-map/MAPEAR_ISLOTE_MINOTAURO.md)). Solo datos (mapa, spawns, cartel, web) + reinicio. Respaldo en `~/backups/pre-deploy-20261113-171321-minotaur-isle` | `0c0eab8` |
| 2026-11-13 | **Resto del catálogo 8.60**: 19 looks con sprites originales, 18 corpses (`20173`–`20190`), 19 XML de monstruo con stats de 8.60, loot adaptado, kits de ataque y 21 spawns (isla natural, cueva, Isla del Hielo y Valle de las Bestias). Se corrigió la sintaxis de loot apilable (`chance1`/`chancemax`) en los nuevos y en las bolsas de Drowned Sailor, Tide Priest y Frost Dragon. Cliente publicado con `publish_client.py`; último reinicio sin warnings de loot ni errores de spawn, probe OK / healthy. Respaldo `~/backups/pre-deploy-20261113-171*` | `83de3e5`, `11273f6`, `e92932f`, `d921fc1` |
| 2026-11-13 | **Bamboo Camp fuera + Cuevas de Bambú + Epstein 4 pisos**: 6 casas menos y 128 tiles de casa; dungeon bajo el claro (pozo z8 + cueva z9); Epstein sin Nimral/Sally/Oracle, tienda borrada, barco abierto a todos, portal al templo y zonas largas z7–z10 con Bog Raiders. Solo datos (mapa, spawns, NPC, Lua, monstruos) + reinicio. Respaldo `~/backups/pre-deploy-20261113-215005`. Probe OK / healthy; 1 cuenta, 6 personajes y 31 casas preservados. | `9de5b59` |
| 2026-11-14 | **Isla natural z8–z10 + dungeon de la city + piratas del barco**: cueva de 3 pisos (wyverns, hatchlings, mutantes, Emerald Scarab) hasta la Old Widow; Smuggler's Den / Deeper Den / Flooded Vault bajo el distrito este; barco del este con tripulación pirata y Dragon Lord Hatchling escondido. Solo datos (mapa, spawns, carteles, docs) + reinicio. Respaldo `~/backups/pre-deploy-20261114-120132`. Probe OK / healthy; 1 cuenta, 6 personajes y 31 casas preservados. Lockers del templo sin cambios (11 con `depotid=1`, 6 personajes con depot 1); falta prueba visual de depot in-game. | `62a74b8` |
| 2026-11-14 | **River Street III–V**: casas de 3x3 por dentro con pasillos de tierra de 1 casilla entre ellas, patios en III y V, puente de sogas de 1 casilla bajo IV y camino hasta el arco de las ruinas de los trolls; orilla conservada bajo la pared oeste de III ([HOUSES.md](../gameplay/HOUSES.md)). Las tres casas sin dueño ni ítems; puertas sin mover. Solo datos (mapa, `houses.xml`) + reinicio. Respaldo `~/backups/pre-deploy-20261114-130047-river-street`. Probe OK / healthy; 1 cuenta y 7 personajes preservados. Falta prueba in-game (puente, patios y depot del templo). | `c92e16f` |
| 2026-11-14 | **River Street: camino bajo el arco**: el camino de tierra al sur del puente pasa a 2 de ancho, alineado con el arco de las ruinas de los trolls (152–153, 78) y empalmado con la tierra de adentro; 13 casillas. Solo mapa + reinicio. Respaldo `~/backups/pre-deploy-20261114-154024-river-path`. Probe OK / healthy; 1 cuenta y 7 personajes preservados. Falta prueba in-game (puente, patios y depot del templo). | `f737b58` |
