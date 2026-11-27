# Servidor en el VPS de Vultr (São Paulo)

Desde el **27 nov 2026** el servidor del juego y la web corren en un VPS de Vultr en São Paulo. La ThinkPad
queda con el juego apagado (`yurots` detenido, sin reinicio automático) y sus datos congelados como respaldo.

| Item | Valor |
|------|-------|
| Acceso | `ssh vps` (alias de `~/.ssh/config` de la Mac: usuario `gonzalo`, clave `~/.ssh/id_ed25519`). `root` entra con la misma clave |
| Máquina | Vultr Cloud Compute Regular Performance `vc2-1c-1gb`: 1 vCPU, 1 GB RAM, 2,4 GB de swap (viene así), 25 GB SSD, 1 TB/mes, US$ 5/mes. Ubuntu 24.04 x64, hora de Chile (`America/Santiago`) |
| IP / dominio | `216.128.175.142` (IPv4; IPv6 `2001:19f0:b800:2957:5400:7ff:fe19:3c1b`). **`retro76.cl`** y `www` apuntan acá (Cloudflare, registros A en **DNS only**: con la nube naranja el cliente no llega al puerto 7171) |
| Repo | `~/apps/serverrepo`, rama `main`; cliente en `~/apps/clienteretro` (solo lectura: en el VPS no hay credenciales de GitHub para pushear) |
| Juego | contenedor `yurots` de `docker-compose.prod.yml`, puerto **7171–7172**. `config.lua` tiene `ip = "216.128.175.142"` como cambio local sin commitear (igual que la ThinkPad tenía su IP) |
| Web | **https://retro76.cl**: Caddy (`/etc/caddy/Caddyfile`, certificado Let's Encrypt automático) → contenedor `retro76-web` en `127.0.0.1:8080` (`python:3.12-slim`, red del host, usuario `gonzalo`) que corre `web/server.py`. `www` y `http://` redirigen a `https://retro76.cl`, **salvo** `/api/updater.php` y `/updater/files/*`, que van por HTTP plano (el updater del cliente). El 8080 sigue abierto para los clientes que todavía apuntan a la IP |
| Firewall | `ufw`: 22, 7171–7172, 8080, 80, 443 |
| Métricas | cron de `gonzalo` cada 5 min: `scripts/ot/collect-metrics.py`; informe `scripts/ot/metrics-report.py` ([METRICAS.md](METRICAS.md)) |
| Respaldo | cron de `gonzalo` al minuto 17: `scripts/deploy/auto-backup-runtime.sh` → `~/backups/auto/`. La Mac lo trae a `~/Retro76-backups/vps-auto/` con `scripts/deploy/pull-auto-backups.sh` (launchd, 13:00 y al prender) |
| No está en el VPS | el mapa interactivo de monstruos (8077) y la web 2 (8076) siguen en la ThinkPad, solo en la red local |

## otservlist

Desde el 27 nov 2026 está en https://otservlist.org/ots/1667197 (cuenta de Gonzalo; editar en
`/servers/edit/1667197`): `retro76.cl:7171`, Brazil, 7.6, PvP, exp 5, descripción en portugués. La lista no tiene campo
de web: la saca del protocolo de estado, o sea de `url` en `config.lua`, igual que `location` ("Brazil") y el dueño
(`ownername`). Ojo con sus reglas: el "online" no puede contar personajes inactivos más de 15 min, x-logs ni más de 4
por IP (YurOTS cuenta a todos los conectados); si se llena de AFKs hay riesgo de ban de 30 a 90 días.

## Uso medido (27 nov 2026)

Con 0–1 jugadores: `yurots` 135–190 MB, `retro76-web` 21–35 MB, total de la máquina ~600 MB contando el
caché. CPU casi nula. El juego usa un solo núcleo y el binario es de 32 bits (no puede pasar de ~3–4 GB), así
que más vCPU o más RAM no lo hacen andar mejor; si algún día falta, el salto es al plan de 2 GB.

El tráfico lo pone la web, no el juego: cada publicación de sprites hace que cada cliente baje el
`Tibia.spr` entero (22 MB), y cada jugador nuevo baja el zip (22 MB Mac, 28 MB Windows).

## Deploy de cambios de datos (mapa, spawns, NPC, Lua, web)

Igual que en la ThinkPad, pero en el VPS no trabajan otras sesiones: el único cambio local es `config.lua` (la IP)
y las casas con dueño (`data/houses/*.xml`, runtime).

```bash
# 1. jugadores conectados (el reinicio los saca un momento)
python3 scripts/ot/ot-probe.py 216.128.175.142 7171

# 2. respaldo, actualizar y reiniciar (SIGTERM guarda a los conectados; -t 45 le da tiempo)
ssh vps 'set -e; cd ~/apps/serverrepo; D=server/YurOTS/ots/data; B=~/backups/pre-deploy-$(date +%Y%m%d-%H%M%S)
  mkdir -p "$B"; for f in players accounts vip online.xml queue.xml houseitems.xml houses guilds.xml private_trainers.xml scrolltexts.xml sponsors.xml; do
  [ -e "$D/$f" ] && cp -a "$D/$f" "$B/"; done; cp -a web/state "$B/web-state"
  git fetch -q origin main && git merge --ff-only origin/main && docker restart -t 45 yurots'

# 3. comprobar
ssh vps 'docker logs --since 3m yurots 2>&1 | grep -i "graceful\|Loaded in\|Running\|error"; docker ps'
python3 scripts/ot/ot-probe.py 216.128.175.142 7171
```

Si cambió `web/*.py`: `ssh vps 'docker restart retro76-web'`. `web/dist` se lee en cada pedido.

El contenedor de la web se creó así (si hay que recrearlo):

```bash
ssh vps 'cd ~/apps/serverrepo && docker rm -f retro76-web; docker run -d --name retro76-web --restart unless-stopped \
  --network host --user $(id -u):$(id -g) -e PORT=8080 -e SITE_URL=https://retro76.cl -e SERVER_IP=retro76.cl \
  -e UPDATER_FILES_URL=http://retro76.cl/updater/files -v ~/apps/serverrepo:/repo -w /repo/web python:3.12-slim python server.py'
```

`UPDATER_FILES_URL` va fijo: detrás de Caddy, armada con el `Host`, la URL salía con `:8080`. `SERVER_IP` es solo
lo que la web muestra para conectarse; `config.lua` sigue con la IP numérica (`ip`) y `url = "https://retro76.cl"`.

Las reglas de siempre siguen: data de jugadores fuera de git, probar el locker del templo tras un mapa nuevo
([DEPOTS.md](../gameplay/DEPOTS.md)), nada de `git stash -u` / `git clean -fd` / `git reset --hard`.

## Cambios de C++

Se compila en el VPS con la imagen del servidor, en una copia aparte. Con 1 vCPU tarda ~5 minutos (`-j2`
alcanza; la RAM aguanta gracias al swap):

```bash
ssh vps 'rm -rf ~/build/deploy-src && mkdir -p ~/build/deploy-src && \
  rsync -a --exclude "*.o" --exclude yurots ~/apps/serverrepo/server/YurOTS/ots/source/ ~/build/deploy-src/ && \
  cd ~/build/deploy-src && docker run --rm --entrypoint "" -v "$PWD":/src -w /src serverrepo-yurots:latest make -j2 yurots \
  > build.log 2>&1; tail -1 build.log; grep -c "warning:" build.log'
```

Tiene que terminar con la línea del link y **0 avisos**. Para cambiar el binario: respaldar, `docker stop -t 45
yurots`, copiarlo con un contenedor (el archivo es de `root`) y `docker start yurots`:

```bash
ssh vps 'docker run --rm --entrypoint "" -v ~/apps/serverrepo/server/YurOTS:/app/YurOTS -v ~/build/deploy-src:/new \
  serverrepo-yurots:latest cp /new/yurots /app/YurOTS/ots/source/yurots'
```

Si cambia el `Dockerfile`: `ssh vps 'cd ~/apps/serverrepo && docker compose -f docker-compose.prod.yml build && docker compose -f docker-compose.prod.yml up -d'`.

## Cliente

El cliente apunta al dominio desde `clienteretro` `93f4663`: `init.lua` tiene
`updater = "http://retro76.cl/api/updater.php"` y `Servers = { ["Retro76"] = "retro76.cl:7171:760" }`. Si se cambia de
servidor, alcanza con cambiar el DNS. El updater va por HTTP plano a propósito: no está probado que el OTClientV8 3.2 siga
la redirección a HTTPS en un POST.

`publish_client.py` se sigue corriendo **en la ThinkPad** (ahí está el clone con credenciales de GitHub y el
entorno que arma el minimapa). Después de publicar, copiar lo publicado al VPS y traer el commit del cliente:

```bash
ssh thinkpad 'cd ~/apps/serverrepo && tar czf - web/updater/files web/downloads' | \
  ssh vps 'cd ~/apps/serverrepo && rm -rf web/updater/files && tar xzf - && git -C ~/apps/clienteretro pull -q'
```

La web de la ThinkPad (8080) sigue prendida a propósito: un cliente viejo que todavía apunta a
`192.168.1.17` recibe de ahí el `init.lua` nuevo y queda apuntando al VPS. Se puede apagar cuando todos los
clientes hayan abierto al menos una vez.

## Pendiente

- **Cerrar el 8080** cuando todos los clientes hayan abierto una vez (ya apuntan a `retro76.cl`). Ojo: `web/server.py`
  confía en `X-Forwarded-For`, así que con el 8080 abierto alguien puede mandar una IP falsa al registro.
- **DDoS.** Sin protección. Vultr la vende aparte.
- Las rutas de la wiki apuntan al mapa interactivo de la ThinkPad (`192.168.1.17:8077`, "red local").

## Mudanza (27 nov 2026)

1. VPS: Docker, `ufw`, usuario `gonzalo`, clones de `serverrepo` y `clienteretro`, imagen construida y binario
   compilado desde `main` `65e8c08d` (0 avisos; mismo C++ que el binario de la ThinkPad, que ya incluía
   "usar de lejos").
2. ThinkPad: respaldo en `~/backups/pre-vps-20261127-164702`, `docker stop -t 45 yurots` (graceful shutdown
   complete) y `docker update --restart=no yurots`.
3. Copia a `~/apps/serverrepo` del VPS: `players`, `accounts`, `vip`, `houses`, `houseitems.xml`, `online.xml`,
   `queue.xml`, `guilds.xml`, `data/logs`, `web/state`, `web/.items-admin-token`, `web/downloads`,
   `web/updater/files` (1 cuenta, 8 personajes, 1 casa con dueño).
4. Juego y web arriba en el VPS (probe OK, 67 ms desde la Mac); cliente publicado con la IP nueva.
5. Dominio: en Cloudflare `retro76.cl` y `www` pasaron de `64.176.20.238` (el VPS viejo) a `216.128.175.142` en DNS only;
   Caddy sacó los certificados; cliente publicado con `retro76.cl` (`93f4663`).
