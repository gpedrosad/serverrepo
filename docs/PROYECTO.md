# Retro76 — Guía del proyecto

Documento de referencia para entender **qué es este repo**, **cómo está hosteado** y **cómo aplicar cambios sin perder cuentas ni personajes**.

> **Agentes IA (Codex, etc.):** empezar por **[LEERCODEX.md](../LEERCODEX.md)** — acceso SSH a la ThinkPad, logs, cuelgues, scripts de diagnóstico.

Por ahora **no hay servidor de producción**: el VPS que había ya no existe. El único servidor es el de prueba en la ThinkPad. Antes de tocarlo, leer **[systems/THINKPAD_TEST_SERVER.md](systems/THINKPAD_TEST_SERVER.md)** (deploy, respaldo, otras sesiones).

Para cambios delicados del core que hoy estan aplicados pero pueden necesitar
rollback, ver tambien:

- [docs/_archive/STAIRS_DEFAULT_ROLLBACK.md](_archive/STAIRS_DEFAULT_ROLLBACK.md)

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
┌─────────────┐     git push      ┌──────────────┐   git merge --ff-only   ┌──────────────────────┐
│  Mac (dev)  │ ────────────────► │   GitHub     │ ──────────────────────► │  ThinkPad (prueba)   │
│  127.0.0.1  │                   │   main       │                         │  192.168.1.17:7171   │
└─────────────┘                   └──────────────┘                         └──────────────────────┘
       │
       │  Docker local: pruebas, RME
       │
       └─ NO es la fuente de verdad de jugadores: la data vive en la ThinkPad
```

### Mac (desarrollo)

- Docker con `docker-compose.prod.yml`
- `config.lua` → `ip = "127.0.0.1"` (o LAN con `./scripts/share-ot.sh lan`)
- Web local: `./scripts/web.sh` → `http://localhost:8080`
- Sirve para probar código y editar mapa (RME). La Mac mini no compila: el C++ se compila en la ThinkPad.

### GitHub (código versionado)

- Rama principal: `main`
- Aquí va **código**, mapas, NPCs, config de plantilla, scripts
- **No** debe haber cuentas ni personajes reales de jugadores

### ThinkPad (servidor de prueba — el único por ahora)

| Dato | Valor |
|------|--------|
| Acceso | `ssh thinkpad` |
| Ruta del repo | `~/apps/serverrepo` (rama `main`) |
| Contenedor | `yurots` (`docker-compose.yml`) |
| Juego | `192.168.1.17:7171` (red local) |

Cuenta GM, otras sesiones y deploy: [systems/THINKPAD_TEST_SERVER.md](systems/THINKPAD_TEST_SERVER.md).
Los deploys van solo con el OK de Gonzalo.

El servidor OT monta `server/YurOTS` como volumen Docker: los XML de cuentas/personajes en disco de la ThinkPad son los que usa el juego.

---

## Data sagrada (runtime) — no tocar sin backup

Estos archivos son el **progreso real de los jugadores**. Viven en la ThinkPad y están **excluidos de git** (ver `.gitignore`):

| Ruta | Contenido |
|------|-----------|
| `server/YurOTS/ots/data/accounts/*.xml` | Cuenta + contraseña + lista de personajes |
| `server/YurOTS/ots/data/players/*.xml` | Personaje (exp, skills, inventario, depot, etc.) |
| `server/YurOTS/ots/data/vip/*.xml` | Listas VIP |
| `server/YurOTS/ots/data/online.xml` | Sesiones conectadas |
| `server/YurOTS/ots/data/queue.xml` | Cola de login |
| `server/YurOTS/ots/data/houseitems.xml` | Items en casas |
| `server/YurOTS/ots/data/private_trainers.xml` | Trainers privados colocados en casas |
| `web/state/daily.json` | Baseline de rankings |
| `web/state/register.json` | Estado anti-bot del registro |
| `web/downloads/*.zip` | Clientes OTClient (**no en git**) |

**Excepción en git:** solo las plantillas de vocación `players/0.xml` … `players/4.xml` (personajes de prueba para crear chars, no jugadores reales).

### Descargas del cliente (web)

| Archivo | Plataforma |
|---------|------------|
| `web/downloads/Retro76-Windows.zip` | Windows (~25 MB) |
| `web/downloads/Retro76-Mac.zip` | macOS (~19 MB) |

No van a GitHub (`.gitignore`). Si faltan, la pestaña **Cliente** de la web muestra los botones pero las URLs dan **404**.

### Cómo se crean cuentas nuevas

1. El jugador entra a la web de registro
2. La web (`web/data.py`) escribe `accounts/NUMERO.xml` y `players/nombre.xml` en el servidor
3. Esos archivos **nunca** pasan por GitHub

### Incidente que no debe repetirse (27/06/2026)

Se usó `git stash -u` en el VPS de entonces antes de un deploy. Eso **movió del disco al stash** las cuentas creadas por la web. El backup no las incluyó y varios personajes desaparecieron temporalmente (`Cachero`, `Cachomisto`, `Pichulon`, etc.). Se recuperaron desde `stash@{0}^3`.

**Lección:** en el servidor (hoy la ThinkPad), nunca `git stash -u`, `git clean`, ni `git reset --hard` sin backup previo de `accounts/` y `players/`.

---

## Qué sí va en git (y qué no)

### Sí commitear

- Código C++ (`server/YurOTS/ots/source/`)
- `config.lua` (con IP local; en la ThinkPad se ajusta la IP a mano)
- Mapa, spawns, NPCs, monstruos, items, spells
- Web (`web/*.py`, el sitio Astro `web/site/` y su compilado `web/dist/`, etc.)
- Scripts (`scripts/`)
- Documentación

### No commitear

- Cuentas y personajes reales (`accounts/`, `players/*` excepto 0–4)
- `online.xml`, `queue.xml`, `houseitems.xml`, `private_trainers.xml`
- `web/state/*.json` (runtime)
- Binario compilado `source/yurots`, objetos `.o`
- `server.log`

---

## Cómo aplicamos cambios

Hay **tres tipos** de cambio, con procedimientos distintos:

### 1. Solo datos (XML/Lua) — sin recompilar

Ejemplos: pesos de runas en `items.xml`, script de un NPC, `runes.lua` de Dark Rodo.

**En Mac:** editar → `git add` → `git push`

**En la ThinkPad** (solo con el OK de Gonzalo): seguir "Deploy de cambios de datos" en
[systems/THINKPAD_TEST_SERVER.md](systems/THINKPAD_TEST_SERVER.md) — revisar archivos de otras sesiones,
respaldar datos de jugadores, `git merge --ff-only origin/main`, `docker restart -t 45 yurots`, revisar el log.

No hace falta `make`. Reiniciar el contenedor basta para recargar items/NPCs.

### 2. Cambios de código C++ — recompilar

Ejemplos: mecánicas nuevas, fixes en `player.cpp`, spells en el motor.

**En Mac:** editar → commit → push (la Mac mini no compila)

**En la ThinkPad** (solo con el OK de Gonzalo): actualizar igual que en el caso 1, compilar ahí (Docker i386) y
reiniciar. Coordinar con la sesión que tenga cambios de C++ sin commitear: el binario que corre puede ser de ellos.

### 3. Cambios solo en el servidor (no commiteados aún)

A veces se aplica un hotfix directo en el servidor (ej. rollback a un commit viejo, parche puntual).

**Siempre:**

1. Backup antes: `cp -a server/YurOTS/ots/data/players ~/backups/manual-FECHA/`
2. Anotar qué commit/binario está corriendo
3. Si el cambio es bueno, llevarlo después a Mac → commit → push para no perderlo

---

## Flujo recomendado (Mac → ThinkPad)

```
1. Desarrollar y probar en Mac (Docker local)
2. git add (solo archivos de código/datos de juego, NUNCA accounts/players reales)
3. git commit && git push origin main
4. Con OK de Gonzalo: deploy a la ThinkPad según docs/systems/THINKPAD_TEST_SERVER.md
5. Verificar log, ot-probe.py 192.168.1.17 7171 y conteo de cuentas/personajes
6. Probar login en el cliente
```

---

## Config que difiere entre Mac y ThinkPad

| Setting | Mac | ThinkPad |
|---------|-----|-----|
| `config.lua` → `ip` | `127.0.0.1` | `192.168.1.17` |
| Jugadores | No (o copia de prueba) | Sí — de prueba, pero se respaldan |

**No commitear** la IP de la ThinkPad al repo; se setea solo ahí.

---

## Backups en la ThinkPad

| Ubicación | Cuándo se crea |
|-----------|----------------|
| `~/backups/pre-deploy-*` | Antes de cada deploy (procedimiento de `THINKPAD_TEST_SERVER.md`) |

Para listar y restaurar:

```bash
ls -lt ~/backups/
cp -an ~/backups/pre-deploy-FECHA/players/. server/YurOTS/ots/data/players/
cp -an ~/backups/pre-deploy-FECHA/accounts/. server/YurOTS/ots/data/accounts/
docker restart -t 45 yurots
```

---

## Estado de producción en junio 2026 (histórico)

A junio 2026, en el VPS de entonces (ya no existe):

- **Binario estable:** basado en commit `3b7f99c` (antes de life/healing rings y cambio de rates x4/x5 que causaban crashes)
- **Aplicado encima (solo datos):** pesos de runas Tibia 7.6 + Dark Rodo vende mana fluid a 100 gp
- **Pendiente / revertido:** implementación C++ de life ring y ring of healing; rates skills x4 del deploy `3786f92`
- **Pendiente restart (solo config):** rates en repo — ML ×3 (`manamul`, ver `docs/gameplay/ML_RATE.md`); exp 71–100 ×2 y 101+ ×1 (ver `docs/gameplay/EXP_RATE.md`)

## Estado local del workspace (2026-07-03)

- Hay cambios **solo locales** en `player.cpp` para rings:
  `life ring` ahora suma **HP y mana** como pulso adicional y la activación se
  fuerza también cuando el ring entra directo al `SLOT_RING` por código.
- Estos cambios **no implican deploy** ni validación runtime; en esta pasada
  no se levantó servidor ni cliente.
- Detalle técnico y caveats: `docs/RINGS_ANALYSIS.md`

Antes de volver a desplegar features de C++ nuevas, probar en local y deployar a la ThinkPad siguiendo su doc.

---

## Comandos útiles

### ThinkPad — estado rápido

```bash
ssh thinkpad
cd ~/apps/serverrepo
docker ps
docker logs yurots --tail 30
ls -1 server/YurOTS/ots/data/accounts/*.xml | wc -l
ls -1 server/YurOTS/ots/data/players/*.xml | wc -l
```

### ThinkPad — reinicio suave (sin deploy)

```bash
docker restart -t 45 yurots
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
| [systems/THINKPAD_TEST_SERVER.md](systems/THINKPAD_TEST_SERVER.md) | Servidor de la ThinkPad: deploy seguro, otras sesiones, respaldo |
| [OTINFO](../OTINFO) | Reglas del juego, rates, custom |
| [docs/SETUP.md](SETUP.md) | Docker, compilación i386 |
| [docs/RME_SETUP.md](RME_SETUP.md) | Editor de mapa |
| [docs/CAMBIAR-MAPA.md](CAMBIAR-MAPA.md) | Reemplazar OTBM, casas, spawns y deploy |
| [README.md](../README.md) | Arranque rápido local |

---

## Resumen en una frase

**GitHub tiene el código; la ThinkPad tiene a los jugadores (no hay producción por ahora). Siempre backup antes de deploy; nunca `git stash -u` ni `git clean` en la ThinkPad.**
