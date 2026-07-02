# Deploy en VPS — LECTURA OBLIGATORIA

> Contexto general del proyecto (Mac, GitHub, VPS, data de jugadores):
> **[docs/PROYECTO.md](../docs/PROYECTO.md)**

> **No ejecutes deploy en el VPS sin leer este documento completo.**
> Un deploy mal hecho **borra cuentas y personajes** de jugadores reales.

Incidente real (27/06/2026): se perdieron 7 cuentas y 7 personajes (`Cachero`, `Cachomisto`, `Pichulon`, `Xardax`, `Gehor`, `Kitooh`, `VIxen`) porque se usó `git stash -u` antes del pull. Los archivos quedaron en el stash y el backup no los incluyó. Se recuperaron desde `stash@{0}^3`.

---

## Regla de oro

**En el VPS solo se despliega así:**

```bash
cd ~/yurots-principal
DEPLOY_I_READ_README=yes ./scripts/deploy-vps.sh
```

Nada más. Sin atajos, sin “solo un git pull rápido”.

---

## Qué es “data runtime” (sagrada)

Estos archivos **viven solo en el VPS**. No están en git (o no deben estarlo):

| Ruta | Contenido |
|------|-----------|
| `server/YurOTS/ots/data/accounts/*.xml` | Cuentas (número + contraseña + lista de chars) |
| `server/YurOTS/ots/data/players/*.xml` | Personajes (exp, items, depot, skills) — excepto plantillas `0–4.xml` |
| `server/YurOTS/ots/data/vip/*.xml` | Listas VIP por cuenta |
| `server/YurOTS/ots/data/online.xml` | Quién está conectado |
| `server/YurOTS/ots/data/queue.xml` | Cola de login |
| `server/YurOTS/ots/data/houseitems.xml` | Items en casas |
| `web/state/daily.json` | Baseline rankings web |
| `web/state/register.json` | Estado anti-bot registro |

Las cuentas nuevas se crean en **https://retro76.cl** (web) → archivos XML en disco. **Nunca** van a GitHub.

---

## Qué hace `deploy-vps.sh` (y por qué es seguro)

1. **Backup** con `cp -a` de `players/`, `accounts/`, `vip/`, `online.xml`, `queue.xml`, `houseitems.xml` → `~/ot-backups/pre-deploy-FECHA/`
2. **`git pull origin main`** — actualiza código y plantillas
3. **Restaura** el backup con `cp -an` (no pisa archivos que ya existan; repone los que git haya tocado)
4. **Compila** dentro del container Docker
5. **Reinicia** `yurots` (stop con 45 s de gracia) y `yurots-web`
6. **Valida** mapa/casas, arranque del binario y healthcheck en puerto 7171
7. **Verifica** conteo de cuentas y personajes

**Watchdog en producción** (auto-recuperación si el puerto deja de responder):

```bash
./scripts/install-ot-observability.sh   # en el VPS, una vez (watchdog + logs)
tail -f /var/log/retro76/diagnostics.log
tail -f /var/log/retro76/web.log
tail -f /var/log/retro76/watchdog.log
```

La web **no abre el puerto 7171**: lee `online.xml` + estado del container Docker (`OT_STATUS_SOURCE=docker`).

Diagnóstico manual inmediato:

```bash
./scripts/ot-diagnostics.sh
./scripts/ot-probe.py 127.0.0.1 7171
```

---

## Comandos PROHIBIDOS en el VPS

| Comando | Por qué es peligroso |
|---------|----------------------|
| `git stash` / `git stash -u` | `-u` **saca del disco** archivos no rastreados (cuentas/personajes nuevos) y los mete al stash |
| `git reset --hard` sin backup previo | Puede borrar archivos que git aún rastrea o dejar el repo inconsistente |
| `git clean -fd` / `git clean -fdx` | **Borra** todos los XML de cuentas/personajes no rastreados |
| `git pull` a mano sin backup | El commit que sacó data del repo (`2d94838`) eliminó del disco archivos que git seguía trackeando |
| Copiar `players/` desde tu Mac al VPS | Pisás progreso real de jugadores |
| `git add` / commit de `accounts/` o `players/` reales | No deben ir al repo |

---

## Checklist antes de deploy

- [ ] Leíste este README completo
- [ ] Los cambios ya están en `main` en GitHub (`git push` desde tu Mac)
- [ ] Nadie está en medio de un boss crítico (opcional pero amable)
- [ ] Tenés acceso SSH al VPS

## Checklist después de deploy

```bash
# En el VPS
ls -1 server/YurOTS/ots/data/accounts/*.xml | wc -l   # anotar número ANTES si querés comparar
ls -1 server/YurOTS/ots/data/players/*.xml | wc -l
docker logs yurots --tail 30                            # debe decir "Retro76 Server Running..."
```

Si el número de cuentas o personajes **bajó**, **no reinicies de nuevo**. Ir a [Recuperación](#recuperación-si-faltan-personajes).

---

## Recuperación si faltan personajes

### 1. Backups automáticos del script

```bash
ls -lt ~/ot-backups/
# El más reciente pre-deploy-* tiene players/, accounts/, vip/
cp -an ~/ot-backups/pre-deploy-FECHA/players/. server/YurOTS/ots/data/players/
cp -an ~/ot-backups/pre-deploy-FECHA/accounts/. server/YurOTS/ots/data/accounts/
```

### 2. Stash de git (si alguien hizo `git stash -u`)

Los archivos no rastreados quedan en el **tercer padre** del stash:

```bash
cd ~/yurots-principal
git stash list
git ls-tree -r --name-only 'stash@{0}^3' | grep -E 'accounts|players'

# Restaurar un archivo:
git show 'stash@{0}^3:server/YurOTS/ots/data/players/cachero.xml' \
  > server/YurOTS/ots/data/players/cachero.xml
```

Para restaurar **todos** los del stash:

```bash
STASH='stash@{0}^3'
git ls-tree -r --name-only "$STASH" | grep 'data/accounts/\|data/players/\|data/vip/' | while IFS= read -r f; do
  base=$(basename "$f")
  case "$base" in [0-4].xml) continue ;; esac
  mkdir -p "$(dirname "$f")"
  git show "$STASH:$f" > "$f" && echo "ok $f"
done
```

### 3. Reiniciar servidor

```bash
docker compose -f docker-compose.prod.yml restart yurots
```

---

## Cambiar el mapa antes del deploy

Si el commit incluye un `.otbm` nuevo, seguí la guía completa en [docs/CAMBIAR-MAPA.md](../docs/CAMBIAR-MAPA.md): exportar desde RME, `sync-houses-from-rme.py`, probar en Docker local y solo entonces push + deploy.

---

## Deploy desde tu Mac (opcional)

Si preferís disparar el deploy remoto sin entrar al VPS:

```bash
ssh root@64.176.20.238 'cd ~/yurots-principal && git fetch origin main && DEPLOY_I_READ_README=yes ./scripts/deploy-vps.sh'
```

---

## Config del VPS que no va al repo

En el VPS, `config.lua` debe tener la IP pública:

```lua
ip = "64.176.20.238"
```

En tu Mac/local: `ip = "127.0.0.1"`. No commitees la IP del VPS al repo.

---

## Si el OT se cuelga (7171 no responde)

Síntoma: jugadores no entran, pero `docker ps` muestra el container **Up**. No es lo mismo que un crash.

| Guía | Contenido |
|------|-----------|
| [docs/PREVENT_OT_HANGS.md](../docs/PREVENT_OT_HANGS.md) | Incidente jul 2026, recuperación, watchdog |
| [docs/SOCKET_DEBUG_LOGGING.md](../docs/SOCKET_DEBUG_LOGGING.md) | `YUROTS_SOCKET_DEBUG=1` (activo en prod), lectura de logs |

Recuperación rápida en el VPS:

```bash
docker compose -f docker-compose.prod.yml restart -t 45 yurots
python3 scripts/ot-probe.py 127.0.0.1 7171
```

---

## Resumen en una línea

**Backup → pull → restaurar backup → compilar → reiniciar.** Nunca stash, nunca clean, nunca reset sin backup.
