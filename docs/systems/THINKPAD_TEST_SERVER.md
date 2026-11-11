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

Hay que compilar en la ThinkPad (Docker i386) y reiniciar. Coordinar con la sesión que tenga cambios de
C++ sin commitear: el binario que corre puede ser de ellos.

## Historial

| Fecha | Qué | Commit |
|-------|-----|--------|
| 2026-11-11 | Valle de las Bestias (reemplaza al Hunt Maze), barco (GM viajan a todo), Reloj de Arena chico con oleadas, Paso del Norte e Isla del Hielo compactados | `9d2ca0d` |
