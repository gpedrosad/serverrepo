# Retro76 / YurOTS Principal

Repositorio **principal** del servidor YurOTS 7.6 (Tibia clásico) en Docker. Por ahora no hay servidor de producción: el único servidor es el de prueba en la ThinkPad ([docs/systems/THINKPAD_TEST_SERVER.md](docs/systems/THINKPAD_TEST_SERVER.md)).

> **Guía completa del proyecto, hosting y deploy (leer primero):**
> **[docs/PROYECTO.md](docs/PROYECTO.md)** — arquitectura Mac/GitHub/ThinkPad, data de jugadores, cómo aplicar cambios sin borrar saves.
>
> **Deploy (obligatorio antes de tocar el servidor de la ThinkPad):**
> **[docs/systems/THINKPAD_TEST_SERVER.md](docs/systems/THINKPAD_TEST_SERVER.md)**

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

`config.lua` trae **`ip = "127.0.0.1"`** por defecto (Docker local para todos).

## Web (rankings, status)

```bash
./scripts/web.sh
```

Abre **http://localhost:8080/** — Python directo, sin Docker.

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

- **[docs/PROYECTO.md](docs/PROYECTO.md)** — Proyecto, servidor, data de jugadores, flujo de cambios
- [docs/gameplay/BOAT_TRAVEL.md](docs/gameplay/BOAT_TRAVEL.md) — Viajes de Nimral/Fargum: destinos, Hell Quest y reglas de teleport/temple
- [docs/gameplay/GOLDEN_ACCESSORIES.md](docs/gameplay/GOLDEN_ACCESSORIES.md) — Golden amulet y golden ring: auto-bank, bonus de oro y cómo se combinan
- **[docs/systems/THINKPAD_TEST_SERVER.md](docs/systems/THINKPAD_TEST_SERVER.md)** — Servidor de la ThinkPad y deploy seguro (**obligatorio**)

Para el índice completo de documentación, ver [docs/INDEX.md](docs/INDEX.md).

Si sos un agente IA, ver también [AGENTS.md](AGENTS.md).

## Estructura

```
yurots-principal/
├── Dockerfile
├── docker-compose.yml
├── docker-compose.prod.yml
├── run.sh
├── scripts/                 # deploy/, ot/, map/, otb/, client-rme/, web/
├── devtools/                # clientes + RME + zagan (ver devtools/README.md)
│   ├── clients/             # client-local, zagan-test client, etc.
│   └── rme/                 # rme-client-760, extensions, zagan RME root
├── server/YurOTS/           # Servidor YurOTS (bind mount)
│   └── ots/
│       ├── config.lua
│       ├── data/world/      # mapa, spawns, casas
│       ├── data/monster/    # incl. Trainer Monk, Elite Trainer Monk
│       └── source/          # C++ + binario yurots
├── backups/                 # yurots-original.otbm; backups/map/ = locales (gitignored)
└── docs/
```

Los nombres históricos en la raíz (`client-local`, `rme-client-760`, `zagan-test`, …) son **symlinks** a `devtools/`.

## Compilar dentro del container

```bash
./run.sh
cd /app/YurOTS/ots/source && make clean && make
```

## Deploy (ThinkPad)

Por ahora no hay producción. Los deploys van a la ThinkPad (`ssh thinkpad`, `~/apps/serverrepo`) y **solo con
el OK de Gonzalo**. La Mac mini no compila: el C++ se compila en la ThinkPad.

> **Obligatorio leer antes de tocar el servidor:**
> **[docs/systems/THINKPAD_TEST_SERVER.md](docs/systems/THINKPAD_TEST_SERVER.md)**

Un deploy mal hecho puede borrar cuentas y personajes, o pisar cambios sin commitear de otras sesiones.

**Prohibido en la ThinkPad:** `git stash -u`, `git clean`, `git reset --hard`, `git pull` a mano. Se actualiza
con `git merge --ff-only origin/main` después del respaldo, como dice el doc.

## Remoto

```bash
git remote -v
# origin → https://github.com/gpedrosad/serverrepo.git
```
