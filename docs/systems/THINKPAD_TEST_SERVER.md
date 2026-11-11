# Servidor de prueba en la ThinkPad

Por ahora no hay servidor de producción: la ThinkPad corre el único servidor. Los deploys ahí van **solo con
el OK de Gonzalo** (ver `CLAUDE.md` de la carpeta de proyectos). La Mac mini no compila.

| Item | Valor |
|------|-------|
| Acceso | `ssh thinkpad` (usuario `gonzalo`, ya en el grupo `docker`) |
| Repo | `~/apps/serverrepo`, rama `main` |
| Contenedor | `yurots` (`docker-compose.yml`), monta `server/YurOTS` → `/app/YurOTS` |
| Dirección | `192.168.1.17:7171` (red local; `ip` en `config.lua`) |
| Binario | `server/YurOTS/ots/source/yurots`, compilado ahí mismo |
| Personaje GM | **GM Retro** (access 3, vocación 0). La cuenta está en `server/YurOTS/ots/data/accounts/` de la ThinkPad (no va a git); pedírsela a Gonzalo |
| Cliente Mac | `~/Desktop/Retro76-Mac` (copia de `~/apps/clienteretro/mac` de la ThinkPad) con el servidor "ThinkPad (prueba)" agregado |

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
  git merge --ff-only origin/main && docker restart -t 45 yurots'

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
  cd ~/build/deploy-src && docker run --rm --entrypoint "" -v "$PWD":/src -w /src serverrepo-yurots:latest make -j4 yurots'
```

Para cambiar el binario: respaldarlo, `docker stop -t 45 yurots` (guarda a los conectados), copiarlo **con
un contenedor** (el archivo es de `root`: un `cp` común da "Permiso denegado" y el servidor queda apagado) y
`docker start yurots`:

```bash
docker run --rm --entrypoint "" -v ~/apps/serverrepo/server/YurOTS:/app/YurOTS -v ~/build/deploy-src:/new \
  serverrepo-yurots:latest cp /new/yurots /app/YurOTS/ots/source/yurots
```

Si al compilar con `rsync` no cambia nada, `make` no recompila: los archivos copiados conservan la fecha. Hacer
`touch` de los `.cpp` cambiados o compilar en una carpeta nueva.

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
