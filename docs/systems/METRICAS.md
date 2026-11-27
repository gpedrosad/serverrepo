# Métricas de Retro76

Desde el 27 nov 2026 todo lo que sirve para medir el servidor se registra solo en el VPS, y la Mac guarda una copia.
Para verlo, un comando:

```bash
ssh vps 'python3 ~/apps/serverrepo/scripts/ot/metrics-report.py'            # últimos 7 días
ssh vps 'python3 ~/apps/serverrepo/scripts/ot/metrics-report.py --days 30'
```

Las cuentas que tienen algún GM (access > 0) no cuentan como jugadores en ningún número.

## Qué se registra y dónde

| Qué | Archivo (en el VPS) | Lo escribe | Cada cuánto |
|-----|---------------------|-----------|-------------|
| Online, máximo y récord, uptime del juego, reinicios del contenedor | `server/YurOTS/ots/data/logs/metrics-AAAA-MM.jsonl` (`kind: sample`) | `scripts/ot/collect-metrics.py` (cron de `gonzalo`) | 5 min |
| Máquina: carga, CPU, RAM libre, swap, disco, bytes de red; CPU/RAM de `yurots` y `retro76-web` | mismo archivo (`kind: sample`) | mismo | 5 min |
| Foto de jugadores: cuentas, personajes, por vocación y nivel, nivel máximo, premium activos, activos en 1/7/30 días, casas con dueño | mismo archivo (`kind: snapshot`) | mismo | 1 vez por día |
| Logins al juego, sesiones (duración), fallos de login | `data/logs/logins-AAAA-MM.jsonl` | servidor C++ ([LOGIN_EVENTS.md](LOGIN_EVENTS.md)) | cada evento |
| Cuentas creadas en la web y fallos | `data/logs/web-AAAA-MM.jsonl` | `web/access_log.py` | cada evento |
| Web: visitantes únicos, páginas vistas, de dónde llegan (otservlist, Google…), idioma de la página, locale del navegador (`pt-BR`, `es-CL`…), descargas Mac/Windows | `web/state/analytics.json` (por día) | `web/analytics.py` (`record_pageview`, `record_download`) | cada página |
| Clientes activos: chequeos del updater e IPs únicas que abrieron el cliente | `web/state/analytics.json` (`updater_checks`, `updater_ips`) | `record_updater` | cada vez que se abre el cliente |
| Embudo premium (vio la página → eligió plan → abrió WhatsApp) | `web/state/analytics.json` (`premium.counts`) | `/api/premium-event` | cada paso |

Los bots (User-Agent con bot, spider, crawl…) no cuentan como páginas vistas. El sitio de origen solo guarda el host
externo, nunca la URL completa.

El cron:

```
*/5 * * * * /usr/bin/python3 /home/gonzalo/apps/serverrepo/scripts/ot/collect-metrics.py >> /home/gonzalo/backups/metrics.log 2>&1 # retro76-metrics
```

## Embudo

Cada hito importante del camino de un jugador queda como una línea en `data/logs/funnel-AAAA-MM.jsonl`, con hora,
**IP** y, desde que hay cuenta, número de cuenta y personaje. La IP permite seguir a la misma persona de un paso al
siguiente (la que visitó desde otservlist, ¿descargó? ¿abrió el cliente? ¿creó cuenta?) y distinguir personas
distintas; la cuenta sigue al jugador una vez que existe.

| Paso (`step`) | Cuándo | Lo escribe | Una vez por IP |
|---------------|--------|-----------|----------------|
| `visit` | primera visita de esa IP a cualquier página (con `landing`, `referrer`, `locale`) | web | sí |
| `download` | cada descarga del cliente (`platform` mac/windows; `first` = primera de esa IP) | web | no |
| `client_open` | la primera vez que un cliente desde esa IP pregunta al updater (= instaló y abrió) | web | sí |
| `account_created` | cuenta y personaje creados en la web (`acc`, `name`, `voc`) | web | no |
| `first_login` | primer ingreso al juego de esa cuenta (sale de `logins-*.jsonl`) | `collect-metrics.py` | por cuenta |
| `level` | el personaje pasó nivel 20, 30, 50, 80, 100, 150 o 200 (`level`; los nuevos nacen en nivel 10) | `collect-metrics.py` | por personaje |
| `promoted` | hizo la promotion | `collect-metrics.py` | por personaje |
| `premium_click` | tocó "Pedir por WhatsApp" (`plan`, `total` en USD) | web | no |
| `premium_active` | el personaje pasó a tener premium | `collect-metrics.py` | por personaje |
| `house` | el personaje pasó a ser dueño de una casa | `collect-metrics.py` | por personaje |

- Las IPs ya vistas por paso están en `web/state/funnel_seen.json`; el estado del juego (niveles, cuentas que ya
  entraron) en `data/logs/.funnel-state.json`. La primera corrida solo guarda la base: no inventa hitos de lo que ya
  existía.
- Los hitos del juego toman la IP del último `game_login` de ese personaje.
- Las cuentas con GM no generan hitos.
- El informe (`metrics-report.py`) muestra cuántas personas llegaron a cada paso en el período y cuántas de ellas
  venían de una IP que visitó la web. El detalle fino (quién, cuándo, desde qué IP) se saca del `.jsonl`.

## URL para bots

Todo lo de arriba, ya resumido, en una URL privada de la web: `https://retro76.cl/stats/<STATS_TOKEN>` (página
legible, se renueva cada minuto), `/summary.json` (JSON completo, `?days=7..90`, 30 por defecto) y `/llms.txt`
(guía de cada campo para un bot, p. ej. el grokbot). La arman `web/metrics_data.py` y `web/stats_page.py`.

- **Token:** en el VPS, `~/.config/retro76/stats.env` (`STATS_TOKEN` y `STATS_IP_SALT`, permisos 600, fuera de git);
  el contenedor `retro76-web` lo carga con `--env-file`. Sin token válido la ruta da 404. Para cambiarlo: editar
  ese archivo y recrear el contenedor ([VPS_VULTR.md](VPS_VULTR.md)).
- **Privacidad:** no publica IPs; cada IP va como `ip_id` (hash corto con sal), que distingue personas sin mostrar
  la dirección. No muestra contraseñas ni datos de pago. Las cuentas de GM no cuentan.
- `noindex` y `Cache-Control: no-store`: no la indexan los buscadores ni queda en cachés.

## Copia en la Mac

`scripts/deploy/pull-auto-backups.sh` (launchd, todos los días a las 13:00 y al prender) trae los `*.jsonl` de
`data/logs` y `analytics.json` a `~/Retro76-backups/vps-logs/` (copia de seguridad; el informe se corre en el VPS).

## Privacidad

Los registros tienen IPs: son runtime, están en `.gitignore` y no se commitean ni se publican. Tamaño: unos 2 MB
por mes de muestras; borrar los meses viejos cuando haga falta (se propone guardar 12 meses).

## Qué mirar

- **Crecimiento:** cuentas nuevas, "primera vez" (cuentas que entraron al juego por primera vez) y activos 7d/30d.
- **Retención:** activos 1d contra 7d y 30d; sesión promedio en minutos.
- **De dónde vienen:** referrers (otservlist.org, Google, Discord…) y locale del navegador (de qué países).
- **Conversión:** visitantes → descargas → clientes del updater → cuentas nuevas → primera vez en el juego.
- **Premium:** el embudo hasta `submit_click` (abrió WhatsApp); los pagos se confirman a mano por WhatsApp.
- **Capacidad:** online pico, CPU, RAM libre mínima y tráfico. Con RAM libre < 150 MB o CPU sostenida > 70 %,
  pasar al plan de 2 GB ([VPS_VULTR.md](VPS_VULTR.md)).
- **Estabilidad:** uptime < 100 % o reinicios > 0 en un día → mirar `docker logs yurots` y
  [CRASH_DIAGNOSTICS.md](CRASH_DIAGNOSTICS.md).
