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
