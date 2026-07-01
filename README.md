# Retro76 / YurOTS Principal

Repositorio **principal** del servidor YurOTS 7.6 (Tibia clásico) en Docker — producción en **retro76.cl**.

> **Guía completa del proyecto, hosting y deploy (leer primero):**
> **[docs/PROYECTO.md](docs/PROYECTO.md)** — arquitectura Mac/GitHub/VPS, data de jugadores, cómo aplicar cambios sin borrar saves.
>
> **Deploy en producción (obligatorio antes de tocar el VPS):**
> **[scripts/README-DEPLOY-VPS.md](scripts/README-DEPLOY-VPS.md)**

Incluye mapa, spawns, NPCs, monstruos custom, spells y assets de RME para evitar confusiones con copias locales.

## Ubicación local

```
~/Desktop/yurots-principal/
```

Symlink de compatibilidad: `~/tibia-yurots-docker` → este directorio.

## Arranque rápido

```bash
cd ~/Desktop/yurots-principal
docker compose -f docker-compose.prod.yml up -d --build
./scripts/share-ot.sh local   # default del repo: 127.0.0.1
```

Puertos: **7171** (login/game), **7172** (expuesto por compatibilidad).

Cliente Tibia 7.6 → **127.0.0.1:7171** (o `./scripts/play-yurots-client.sh`).

### Jugar con otros (misma red WiFi)

```bash
./scripts/share-ot.sh lan
```

Usa la IP de tu Mac/PC en `config.lua` y reinicia Docker. Tus amigos conectan a `TU_IP:7171`
(pueden parchear el cliente con `python3 scripts/patch-tibia760-client.py --ip TU_IP`).

Volver a solo local: `./scripts/share-ot.sh local`

`config.lua` trae **`ip = "127.0.0.1"`** por defecto (Docker local para todos; sin VPS).

## Web (rankings, status)

```bash
./scripts/web.sh
```

Abre **http://localhost:8080/** — Python directo, sin Docker ni VPS.

Para que **otros la vean** (link público temporal):

```bash
./scripts/web-public.sh
```

Te da una URL `https://….trycloudflare.com` para compartir. Requiere `cloudflared` (`brew install cloudflared`).

## Mapa y mundo

| Archivo | Descripción |
|---------|-------------|
| `server/YurOTS/ots/data/world/test.otbm` | Mapa activo |
| `server/YurOTS/ots/data/world/test-spawn.xml` | Spawns |
| `server/YurOTS/ots/data/world/test-house.xml` | Casas |
| `server/YurOTS/ots/data/world/npc.xml` | NPCs en mapa |
| `backups/yurots-original.otbm` | Backup del mapa original |

## Editar mapa (RME)

```bash
~/Desktop/yurots-principal/scripts/open-rme.sh
```

Ver [docs/RME_SETUP.md](docs/RME_SETUP.md).

## Info del servidor

Ver [OTINFO](OTINFO) — rates, PvP, frags y reglas.

## Documentación técnica
- **[docs/PROYECTO.md](docs/PROYECTO.md)** — Proyecto, VPS, data de jugadores, flujo de cambios
- **[scripts/README-DEPLOY-VPS.md](scripts/README-DEPLOY-VPS.md)** — Deploy seguro en producción (**obligatorio**)
- [docs/SETUP.md](docs/SETUP.md) — Docker, compilación i386, errores resueltos
- [docs/SMOKE_TESTS.md](docs/SMOKE_TESTS.md) — Smoke tests locales para login, save, spells, runas, muerte y movimiento
- [docs/RME_SETUP.md](docs/RME_SETUP.md) — Remere's Map Editor 7.6
- [docs/SPELL_EXORI_GRAN.md](docs/SPELL_EXORI_GRAN.md) — Spells custom Knight

## Estructura

```
yurots-principal/
├── Dockerfile
├── docker-compose.yml
├── docker-compose.prod.yml
├── run.sh
├── rme-client-760/          # Tibia.dat + Tibia.spr para RME
├── scripts/                 # open-rme, setup, rebuild, etc.
├── server/YurOTS/           # Servidor YurOTS (bind mount)
│   └── ots/
│       ├── config.lua
│       ├── data/world/      # mapa, spawns, casas
│       ├── data/monster/    # incl. Trainer Monk, Elite Trainer Monk
│       └── source/          # C++ + binario yurots
├── backups/
└── docs/
```

## Compilar dentro del container

```bash
./run.sh
cd /app/YurOTS/ots/source && make clean && make
```

## Deploy en VPS (producción)

> **Obligatorio leer antes de tocar el servidor:**
> **[scripts/README-DEPLOY-VPS.md](scripts/README-DEPLOY-VPS.md)**

Un deploy mal hecho puede borrar cuentas y personajes de jugadores. Solo usar:

```bash
# En el VPS (64.176.20.238)
cd ~/yurots-principal
DEPLOY_I_READ_README=yes ./scripts/deploy-vps.sh
```

**Prohibido en el VPS:** `git stash -u`, `git clean`, `git reset --hard` sin backup, `git pull` a mano.

## Remoto

```bash
git remote -v
# origin → https://github.com/gpedrosad/serverrepo.git
```
