# Retro76 — Guía del proyecto

Documento de referencia para entender **qué es este repo**, **cómo está hosteado** y **cómo aplicar cambios sin perder cuentas ni personajes**.

Para el checklist detallado de deploy en producción, ver también **[scripts/README-DEPLOY-VPS.md](../scripts/README-DEPLOY-VPS.md)** (lectura obligatoria antes de tocar el VPS).

Para cambios delicados del core que hoy estan aplicados pero pueden necesitar
rollback, ver tambien:

- [docs/STAIRS_DEFAULT_ROLLBACK.md](STAIRS_DEFAULT_ROLLBACK.md)

---

## Qué es este proyecto

| Concepto | Valor |
|----------|--------|
| Nombre público | **Retro76** |
| Motor | YurOTS 7.6 (Tibia clásico 7.6) |
| Repo local | `~/Desktop/yurots-principal/` |
| Repo remoto | `https://github.com/gpedrosad/serverrepo.git` |
| Reglas y rates | [OTINFO](../OTINFO) |

El repo incluye servidor (C++), mapa, NPCs, monstruos, spells, web de registro/rankings, Docker y scripts de deploy.

---

## Arquitectura: tres lugares distintos

```
┌─────────────┐     git push      ┌──────────────┐     git pull      ┌─────────────────────┐
│  Mac (dev)  │ ────────────────► │   GitHub     │ ────────────────► │  VPS (producción)   │
│  127.0.0.1  │                   │   main       │                   │  64.176.20.238      │
└─────────────┘                   └──────────────┘                   │  retro76.cl         │
       │                                                              └─────────────────────┘
       │  Docker local                                                         │
       │  Pruebas, RME, compilar                                               │
       │                                                                         │
       └─ NO es la fuente de verdad de jugadores ────────────────────────────────┘
                    La data real vive SOLO en el VPS
```

### Mac (desarrollo)

- Docker con `docker-compose.prod.yml`
- `config.lua` → `ip = "127.0.0.1"` (o LAN con `./scripts/share-ot.sh lan`)
- Web local: `./scripts/web.sh` → `http://localhost:8080`
- Sirve para probar código, editar mapa (RME), compilar

### GitHub (código versionado)

- Rama principal: `main`
- Aquí va **código**, mapas, NPCs, config de plantilla, scripts
- **No** debe haber cuentas ni personajes reales de jugadores

### VPS (producción — fuente de verdad de jugadores)

| Dato | Valor |
|------|--------|
| IP | `64.176.20.238` |
| Dominio | `retro76.cl` (HTTPS en web) |
| SSH | `ssh root@64.176.20.238` |
| Ruta del repo | `~/yurots-principal` |
| Juego | `retro76.cl:7171` o `64.176.20.238:7171` |
| Web | `https://retro76.cl` (registro de cuentas, rankings) |

**Servicios en el VPS:**

| Servicio | Qué hace |
|----------|----------|
| Contenedor `yurots` (Docker) | Servidor OT, puertos 7171/7172 |
| `yurots-web` (systemd) | Web Python (registro, status, rankings) |
| nginx | HTTPS y proxy a la web |

El servidor OT monta `server/YurOTS` como volumen Docker: los XML de cuentas/personajes en disco del VPS son los que usa el juego en vivo.

---

## Data sagrada (runtime) — no tocar sin backup

Estos archivos son el **progreso real de los jugadores**. Viven en el VPS y están **excluidos de git** (ver `.gitignore`):

| Ruta | Contenido |
|------|-----------|
| `server/YurOTS/ots/data/accounts/*.xml` | Cuenta + contraseña + lista de personajes |
| `server/YurOTS/ots/data/players/*.xml` | Personaje (exp, skills, inventario, depot, etc.) |
| `server/YurOTS/ots/data/vip/*.xml` | Listas VIP |
| `server/YurOTS/ots/data/online.xml` | Sesiones conectadas |
| `server/YurOTS/ots/data/queue.xml` | Cola de login |
| `server/YurOTS/ots/data/houseitems.xml` | Items en casas |
| `web/state/daily.json` | Baseline de rankings |
| `web/state/register.json` | Estado anti-bot del registro |
| `web/downloads/*.zip` | Clientes OTClient (**no en git**, solo en VPS) |

**Excepción en git:** solo las plantillas de vocación `players/0.xml` … `players/4.xml` (personajes de prueba para crear chars, no jugadores reales).

### Descargas del cliente (web)

| Archivo en VPS | Plataforma |
|----------------|------------|
| `web/downloads/Retro76-Windows.zip` | Windows (~25 MB) |
| `web/downloads/Retro76-Mac.zip` | macOS (~19 MB) |

No van a GitHub (`.gitignore`). Tras un rollback o VPS nuevo, subirlos con:

```bash
./scripts/upload-client-downloads.sh
```

Si faltan, la pestaña **Cliente** en retro76.cl muestra los botones pero las URLs dan **404**.

### Cómo se crean cuentas nuevas

1. El jugador entra en **https://retro76.cl**
2. La web (`web/data.py`) escribe `accounts/NUMERO.xml` y `players/nombre.xml` en el VPS
3. Esos archivos **nunca** pasan por GitHub

### Incidente que no debe repetirse (27/06/2026)

Se usó `git stash -u` en el VPS antes de un deploy. Eso **movió del disco al stash** las cuentas creadas por la web. El backup no las incluyó y varios personajes desaparecieron temporalmente (`Cachero`, `Cachomisto`, `Pichulon`, etc.). Se recuperaron desde `stash@{0}^3`.

**Lección:** en el VPS, nunca `git stash -u`, `git clean`, ni `git reset --hard` sin backup previo de `accounts/` y `players/`.

---

## Qué sí va en git (y qué no)

### Sí commitear

- Código C++ (`server/YurOTS/ots/source/`)
- `config.lua` (con IP local; en VPS se ajusta la IP a mano)
- Mapa, spawns, NPCs, monstruos, items, spells
- Web (`web/*.py`, `web/index.html`, etc.)
- Scripts (`scripts/`)
- Documentación

### No commitear

- Cuentas y personajes reales (`accounts/`, `players/*` excepto 0–4)
- `online.xml`, `queue.xml`, `houseitems.xml`
- `web/state/*.json` (runtime)
- Binario compilado `source/yurots`, objetos `.o`
- `server.log`

---

## Cómo aplicamos cambios

Hay **tres tipos** de cambio, con procedimientos distintos:

### 1. Solo datos (XML/Lua) — sin recompilar

Ejemplos: pesos de runas en `items.xml`, script de un NPC, `runes.lua` de Dark Rodo.

**En Mac:** editar → `git add` → `git push`

**En VPS:**

```bash
cd ~/yurots-principal
git pull origin main   # solo si ya está en GitHub
# O copiar el archivo con scp si es un hotfix urgente
docker compose -f docker-compose.prod.yml restart yurots
```

No hace falta `make`. Reiniciar el contenedor basta para recargar items/NPCs.

### 2. Cambios de código C++ — recompilar

Ejemplos: mecánicas nuevas, fixes en `player.cpp`, spells en el motor.

**En Mac:** editar → commit → push

**En VPS (deploy completo y seguro):**

```bash
cd ~/yurots-principal
DEPLOY_I_READ_README=yes ./scripts/deploy-vps.sh
```

El script: backup de players/accounts → `git pull` → restaura backup → `make` en Docker → reinicia.

### 3. Cambios solo en VPS (no commiteados aún)

A veces se aplica un hotfix directo en producción (ej. rollback a un commit viejo, parche puntual).

**Siempre:**

1. Backup antes: `cp -a server/YurOTS/ots/data/players ~/ot-backups/manual-FECHA/`
2. Anotar qué commit/binario está corriendo
3. Si el cambio es bueno, llevarlo después a Mac → commit → push para no perderlo

---

## Flujo recomendado (Mac → producción)

```
1. Desarrollar y probar en Mac (Docker local)
2. git add (solo archivos de código/datos de juego, NUNCA accounts/players reales)
3. git commit && git push origin main
4. En VPS: DEPLOY_I_READ_README=yes ./scripts/deploy-vps.sh
5. Verificar conteo de cuentas/personajes y logs
6. Probar login en el cliente
```

Deploy remoto desde Mac (opcional):

```bash
ssh root@64.176.20.238 'cd ~/yurots-principal && DEPLOY_I_READ_README=yes ./scripts/deploy-vps.sh'
```

---

## Config que difiere entre Mac y VPS

| Setting | Mac | VPS |
|---------|-----|-----|
| `config.lua` → `ip` | `127.0.0.1` | `64.176.20.238` |
| Jugadores reales | No (o copia de prueba) | Sí — fuente de verdad |
| HTTPS web | No | `retro76.cl` vía nginx |

**No commitear** `ip = "64.176.20.238"` al repo; se setea solo en el VPS.

---

## Backups en el VPS

| Ubicación | Cuándo se crea |
|-----------|----------------|
| `~/ot-backups/pre-deploy-*` | Automático con `deploy-vps.sh` |
| `~/ot-backups/rollback-*` | Rollbacks manuales |
| `~/ot-backups/recovered-from-stash-*` | Recuperaciones de emergencia |

Para listar y restaurar:

```bash
ls -lt ~/ot-backups/
cp -an ~/ot-backups/pre-deploy-FECHA/players/. server/YurOTS/ots/data/players/
cp -an ~/ot-backups/pre-deploy-FECHA/accounts/. server/YurOTS/ots/data/accounts/
docker compose -f docker-compose.prod.yml restart yurots
```

---

## Estado de producción (referencia)

A junio 2026, en el VPS:

- **Binario estable:** basado en commit `3b7f99c` (antes de life/healing rings y cambio de rates x4/x5 que causaban crashes)
- **Aplicado encima (solo datos):** pesos de runas Tibia 7.6 + Dark Rodo vende mana fluid a 100 gp
- **Pendiente / revertido:** implementación C++ de life ring y ring of healing; rates skills x4 / ML x5 del deploy `3786f92`

Antes de volver a desplegar features de C++ nuevas, probar en Mac y hacer deploy con el script seguro.

---

## Comandos útiles

### VPS — estado rápido

```bash
docker ps
docker logs yurots --tail 30
ls -1 server/YurOTS/ots/data/accounts/*.xml | wc -l
ls -1 server/YurOTS/ots/data/players/*.xml | wc -l
systemctl status yurots-web
```

### VPS — reinicio suave (sin deploy)

```bash
docker compose -f docker-compose.prod.yml restart yurots
systemctl restart yurots-web
```

### Mac — arranque local

```bash
cd ~/Desktop/yurots-principal
docker compose -f docker-compose.prod.yml up -d --build
./scripts/web.sh
```

---

## Documentación relacionada

| Documento | Contenido |
|-----------|-----------|
| [scripts/README-DEPLOY-VPS.md](../scripts/README-DEPLOY-VPS.md) | Deploy seguro, prohibiciones, recuperación |
| [OTINFO](../OTINFO) | Reglas del juego, rates, custom |
| [docs/SETUP.md](SETUP.md) | Docker, compilación i386 |
| [docs/RME_SETUP.md](RME_SETUP.md) | Editor de mapa |
| [README.md](../README.md) | Arranque rápido local |

---

## Resumen en una frase

**GitHub tiene el código; el VPS tiene a los jugadores. Siempre backup antes de deploy; nunca `git stash -u` ni `git clean` en producción.**
