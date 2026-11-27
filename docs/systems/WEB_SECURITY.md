# Seguridad de la web (`web/server.py`)

Revisión de nov 2026, antes de exponer la web a internet en un VPS. La web crea cuentas y personajes (escribe
XML en `data/accounts` y `data/players` del OT), recibe comprobantes de pago y guarda estado en `web/state/`.

## Arreglado (nov 2026)

| Riesgo | Antes | Ahora |
|--------|-------|-------|
| **Leer cualquier archivo de `web/`** | `GET /data/../state/premium_orders.json` (o `/assets/..`, `/components/..`) devolvía pedidos premium con IPs, comprobantes bancarios (`uploads/`), `state/*.json`, el token y el código | `_static` solo sirve dentro de `assets/`, `components/` o `data/` (`is_relative_to` de esa carpeta) y rechaza `..`, `%` y `\`. Probado con `curl --path-as-is`: 404 |
| **IP falsificable** | `client_ip` tomaba el primer valor de `X-Forwarded-For`: con una IP inventada por pedido no había límite de cuentas, reportes ni pedidos premium | Los headers del proxy solo se creen si la conexión viene de `127.0.0.1` (nginx); vale `X-Real-IP` o el último valor de `X-Forwarded-For`. `WEB_BIND=127.0.0.1` en el VPS para que nadie le hable directo |
| **Token del catálogo de ítems** | fijo en el código: `"2424"`, comparado con `==`, sin límite de intentos | `ITEMS_ADMIN_TOKEN` o `web/.items-admin-token` (fuera de git), 12+ caracteres, `hmac.compare_digest`, 10 intentos malos por hora y por IP. Sin token, `/items` da 404 |
| **Crear cuenta a la vez** | comprobar y escribir sin lock: dos pedidos iguales podían pisar la contraseña de una cuenta | lock global + `open(..., "x")` (nunca pisa una cuenta existente) |
| **Nombres de staff** | solo se bloqueaba el prefijo `gm` | también `cm`, "admin", "gamemaster", "moderator"... y palabras sueltas "god", "staff", "tutor", "dev"... (`_reserved_name` en `data.py`) |
| **Captcha / límites** | `register.json` escrito sin lock (una escritura cruzada lo corrompía y **reseteaba los límites**), captchas sin tope, `form_ts=0` saltaba el control de tiempo | lock + escritura atómica (`.tmp` + `replace`), máximo 2.000 captchas vivos, `form_ts` vacío = bot |
| **Cuerpos sin límite / conexiones lentas** | `rfile.read(Content-Length)` sin tope; sin timeout | `create-account` hasta 8 KB, updater hasta 64 KB, `Handler.timeout = 20` |
| **Comprobante** | solo se miraba la extensión (un HTML renombrado a `.pdf` pasaba) | además los primeros bytes: JPG, PNG, PDF o WEBP |
| **Analytics** | cada IP (falsificable) se guardaba sin tope; `/api/premium-event` guardaba cualquier dict | tope de 20.000 visitantes por día; `detail` limitado a 6 valores simples y cortos |
| **Cabeceras** | sin cabeceras de seguridad; `Server` mostraba la versión de Python | `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy` en todas las respuestas; `Server: Retro76Web` |

No se encontró: inyección XML al crear cuentas (nombre `[a-zA-Z ]`, contraseña alfanumérica, `type`/`access` fijos),
forma de darse GM o premium desde la web, ni XSS en el navegador (todo pasa por `esc()` / `charLink()`).

## Pendiente para el VPS

- **nginx** (`deploy/nginx/yurots.conf`, ya actualizado): `client_max_body_size 6m` (si no, los comprobantes de más
  de 1 MB dan 413), `server_tokens off`, HSTS cuando Certbot ponga HTTPS, `X-Real-IP $remote_addr`.
- **Servicio** (`scripts/web/yurots-web.service`): `WEB_BIND=127.0.0.1` (ya puesto); correr con un usuario propio en
  vez de `root`, con escritura solo en `web/state/`, `web/uploads/` y los datos del OT.
- **Updater del cliente:** hoy arma `http://<Host>/updater/files` y el manifiesto solo tiene CRC32. En una red
  insegura alguien podría cambiar `init.lua` en el camino. En el VPS: `UPDATER_FILES_URL=https://.../updater/files`
  (verificar que OTClientV8 acepte https).
- **`import cgi`** (`premium_orders.py`): no existe desde Python 3.13. Usar Python 3.12 en el VPS (como el
  contenedor de la ThinkPad) o reemplazar el parser.
- `/api/premium-analytics` compara su token con `!=`: pasar a `hmac.compare_digest`.
- "Ese número de cuenta ya existe" deja averiguar qué números existen (con captcha de por medio).
