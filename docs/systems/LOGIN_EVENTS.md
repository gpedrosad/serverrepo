# Registro de accesos (logins, cuentas nuevas)

Guarda cada intento de acceso con su resultado, para medir cuántos jugadores nuevos llegan a jugar, cuántos vuelven, por qué fallan los logins y si hay fuerza bruta. También sirve de señal de cuelgues: si siguen llegando `charlist_ok` pero dejan de aparecer `game_login`, el juego no está respondiendo aunque el contenedor esté `Up`.

## Dónde se guarda

Una línea JSON por evento, un archivo por mes, en `server/YurOTS/ots/data/logs/`:

| Archivo | Lo escribe | Eventos |
|---------|-----------|---------|
| `logins-AAAA-MM.jsonl` | Servidor C++ (`source/loginlog.cpp`, llamado desde `ConnectionHandler` en `otserv.cpp`) | `charlist_*`, `game_*` |
| `web-AAAA-MM.jsonl` | Web (`web/access_log.py`, en `_create_account` de `web/server.py`) | `account_created`, `account_create_fail` |

Son **data runtime** (incluyen IPs): están en `.gitignore`, viven en el servidor (hoy la ThinkPad) y no se commitean. Para borrar lo viejo basta con eliminar los archivos de meses anteriores. Se propone conservar 6 meses.

**Nunca se registra la contraseña**, ni la correcta ni la intentada.

## Campos

`t` (epoch UTC), `ts` (ISO UTC), `event`, `acc` (número de cuenta), `name` (personaje; vacío en la lista de personajes), `ip`, `reason` (solo en fallos) y `value` (dato numérico opcional, ver tabla).

## Eventos

| Evento | Cuándo | `reason` / `value` |
|--------|--------|--------------------|
| `account_created` | La web creó cuenta y personaje | `voc`, `sex` |
| `account_create_fail` | La web rechazó el registro | `reason` = mensaje mostrado (captcha, nombre en uso, cuenta existente…) |
| `charlist_ok` | Login correcto a la lista de personajes (protocolo 0x0201) | `value` = cantidad de personajes |
| `charlist_fail` | Login a la lista rechazado | `ip_banished`, `no_account`, `wrong_password` |
| `game_login` | El personaje entró al juego (0x020A) | — |
| `game_logout` | Terminó la sesión (logout, desconexión o kick) | `value` = duración en segundos |
| `game_reattach` | Se reengancha a un personaje que seguía en el mapa sin conexión | — |
| `game_replace` | Reemplaza una sesión abierta del mismo personaje (`replaceconnectedcharacter`) | — |
| `game_fail` | Entrada al juego rechazada | `bad_version` (`value` = versión del cliente), `ip_banished`, `wrong_password`, `no_account_or_char`, `already_logged_in`, `char_banished`, `shutdown`, `server_closed`, `queue` (`value` = puesto), `wrong_temple`, `server_full` |

`game_login` se escribe después de soltar `gameLock`, para que escribir en disco no frene el juego. Si no se puede escribir el archivo (disco lleno, permisos), el login sigue igual y el evento se pierde.

## Informe

```bash
python3 scripts/ot/login-report.py              # últimos 14 días
python3 scripts/ot/login-report.py --days 30
```

En la ThinkPad se ejecuta desde `~/apps/serverrepo`. Muestra:

- Cuentas nuevas, logins y personajes por día.
- Embudo de cuentas nuevas: cuántas llegaron a entrar al juego, y cuántas en las primeras 24 h.
- Retención al día 1, 7 y 30.
- Fallos por motivo, e IPs con 10 o más fallos de credenciales.
- Duración de las sesiones y pico aproximado de jugadores por hora (UTC).

Es de solo lectura.
