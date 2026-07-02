# Cambiar el mapa (RME → local → VPS)

Guía paso a paso para reemplazar `test.otbm` sin romper casas, spawns ni el arranque del servidor.

Relacionado:

- [docs/RME_SETUP.md](RME_SETUP.md) — abrir RME y assets 7.6
- [scripts/README-DEPLOY-VPS.md](../scripts/README-DEPLOY-VPS.md) — deploy seguro en producción
- [docs/PROYECTO.md](PROYECTO.md) — qué data es sagrada y qué va en git

---

## Archivos que forman el mapa

| Archivo en repo | Origen (RME) | Qué define |
|-----------------|--------------|------------|
| `server/YurOTS/ots/data/world/test.otbm` | Guardar mapa OTBM | Tiles, items, casas (HOUSETILE), depots en mapa |
| `server/YurOTS/ots/data/world/test-house.xml` | Export casas / metadata RME | Lista de casas (`houseid`, entrada, town) |
| `server/YurOTS/ots/data/world/test-spawn.xml` | Export spawns RME | Respawns de monstruos |
| `server/YurOTS/ots/data/houses.xml` | **Generado por script** | Tiles de cada casa (lo lee el servidor) |
| `server/YurOTS/ots/data/world/npc.xml` | Manual / editor | Posiciones de NPCs (no van dentro del OTBM) |

El servidor carga `test.otbm` desde `config.lua` (`map = "data/world/test.otbm"`).

---

## 1. Editar en Remere's Map Editor

```bash
./scripts/open-rme.sh
```

Antes de guardar:

- **Casas:** definilas en RME (HOUSETILE). Si borrás una casa del mapa, también hay que quitar su entrada en `data/houses/*.xml` (ver paso 4).
- **Spawns:** usá el spawn editor de RME; al exportar genera `test-spawn.xml`.
- **Depots:** colocalos en RME con el depot ID correcto. No hace falta parchear el OTBM a mano si RME ya los exporta bien.
- **Puertas de nivel:** puerta cerrada + **actionId = nivel + 1000** (ej. nivel 20 → `1020`). Script: `data/actions/scripts/leveldoor.lua`.
- **NPCs:** las posiciones van en `npc.xml`, no solo en el mapa.

Guardá / exportá desde RME (o copiá desde `~/Downloads` si guardaste ahí):

- `test.otbm` (o tu nombre, ej. `MAPA ACTUALIZADO CUATRO.otbm`)
- `test-house.xml`
- `test-spawn.xml`

---

## 2. Copiar al repo (Mac / local)

Desde la raíz del proyecto:

```bash
cp "/Users/gonzalo/Downloads/TU_MAPA.otbm" \
  server/YurOTS/ots/data/world/test.otbm

cp ~/Downloads/test-house.xml server/YurOTS/ots/data/world/test-house.xml
cp ~/Downloads/test-spawn.xml server/YurOTS/ots/data/world/test-spawn.xml
```

Ajustá la ruta del `.otbm` al nombre que hayas usado al guardar.

---

## 3. Sincronizar casas (obligatorio)

RME guarda casas como **HOUSETILE** dentro del OTBM. El servidor YurOTS necesita:

1. OTBM sin HOUSETILE (tiles normales)
2. `houses.xml` con los tiles de cada casa

```bash
python3 scripts/sync-houses-from-rme.py
```

El script:

- Lee `test-rme.otbm` o `test.otbm`
- Regenera `data/houses.xml` desde `test-house.xml` + tiles del mapa
- Convierte HOUSETILE → TILE en `test.otbm`
- Valida que no queden tiles inválidos

Si falla con `Tile (x/y/z) is not valid`, hay casas en `houses.xml` que no existen en el mapa — volvé a exportar desde RME o corré el script de nuevo.

**Validación extra (solo lectura):**

```bash
python3 scripts/sync-houses-with-map.py --dry-run
```

Debe decir: `houses.xml ya coincide con el mapa.`

---

## 4. Casas eliminadas del mapa

Si borraste casas en RME (ej. River Street I y II):

1. No deben aparecer en `test-house.xml` tras exportar.
2. Borrá el XML del dueño si existe:

   ```bash
   rm -f "server/YurOTS/ots/data/houses/River Street I.xml"
   rm -f "server/YurOTS/ots/data/houses/River Street II.xml"
   ```

3. `sync-houses-from-rme.py` ya no las incluirá en `houses.xml`.

**No edites `houses.xml` a mano** salvo emergencia; usá el script.

---

## 5. NPCs y otros datos

| Cambio | Archivo |
|--------|---------|
| Mover NPC (Dufi, Guild Master, etc.) | `server/YurOTS/ots/data/world/npc.xml` |
| Nuevo monstruo en spawn | `test-spawn.xml` + definición en `data/monster/` |
| Items en casas de jugadores | `houseitems.xml` (runtime VPS, no git) |

Tras mover NPCs, reiniciá el servidor (no hace falta recompilar).

---

## 6. Probar en local (Docker)

```bash
docker compose restart yurots
docker logs yurots --tail 30
```

Debe aparecer:

- `Loaded in X s`
- `Loading houses.xml... [done]`
- `Retro76 Server Running...`

Si falla en casas, revisá el paso 3.

Cliente local:

```bash
./scripts/play-yurots-client.sh
```

Conectar a `127.0.0.1:7171`.

---

## 7. Qué commitear a GitHub (cuando el mapa esté listo)

**Sí incluir:**

- `server/YurOTS/ots/data/world/test.otbm`
- `server/YurOTS/ots/data/world/test-house.xml`
- `server/YurOTS/ots/data/world/test-spawn.xml`
- `server/YurOTS/ots/data/houses.xml`
- `server/YurOTS/ots/data/world/npc.xml` (si cambió)
- `scripts/sync-houses-from-rme.py` (si aún no está en main)

**No incluir:**

- `test-rme.otbm`, `*.bak`, `test.otbm.bak` (copias locales)
- `config.lua` con `ip = "127.0.0.1"` — en el repo debe quedar `ip = "retro76.cl"`; en Mac podés tener `127.0.0.1` solo local sin commitear
- `data/accounts/`, `data/players/` reales, logs, binario `source/yurots`
- `client-local/`

---

## 8. Subir al VPS (producción)

Solo cuando el mapa esté probado en local:

1. `git push origin main` desde tu Mac
2. En el VPS (ver [README-DEPLOY-VPS.md](../scripts/README-DEPLOY-VPS.md)):

   ```bash
   ssh root@64.176.20.238
   cd ~/yurots-principal
   DEPLOY_I_READ_README=yes ./scripts/deploy-vps.sh
   ```

El deploy:

- Hace backup de cuentas/personajes
- `git pull`
- Restaura data runtime
- Compila el servidor
- Valida mapa ↔ casas (`sync-houses-with-map.py --dry-run`)
- Reinicia Docker y healthcheck en 7171

**En el VPS:** `config.lua` debe tener `ip = "64.176.20.238"` (no commitear esa IP si preferís manejarla solo en el servidor).

---

## Checklist rápido

```
[ ] Guardar/exportar OTBM + test-house.xml + test-spawn.xml desde RME
[ ] Copiar los 3 archivos a server/YurOTS/ots/data/world/
[ ] python3 scripts/sync-houses-from-rme.py
[ ] python3 scripts/sync-houses-with-map.py --dry-run
[ ] Borrar data/houses/*.xml de casas eliminadas (si aplica)
[ ] Actualizar npc.xml (si moviste NPCs)
[ ] docker compose restart yurots + revisar logs
[ ] Probar in-game: casas, depots, spawns nuevos, puertas de nivel
[ ] git commit + push (solo cuando estés conforme)
[ ] DEPLOY_I_READ_README=yes ./scripts/deploy-vps.sh en el VPS
```

---

## Errores frecuentes

| Síntoma | Causa | Solución |
|---------|--------|----------|
| `Tile (x/y/z) is not valid!` al cargar casas | `houses.xml` con tiles que ya no están en el mapa | `sync-houses-from-rme.py` |
| `Could not load houses!` | Casa en `houses.xml` sin archivo en `data/houses/Nombre.xml` | Crear XML o quitar casa del mapa |
| `You can not use this object` (depot) | Jugador sin ese `depotid` en su XML | Abrir depot en RME con ID estándar (ej. 1) o fix en `actions.cpp` (auto-crear depot) |
| Puerta no pide nivel | Falta actionId o itemid sin `leveldoor.lua` | actionId = nivel + 1000 |
| Spawns no aparecen | `test-spawn.xml` viejo o monstruo sin definición | Reexportar spawns; revisar `data/monster/monsters.xml` |
| Deploy VPS falla validación | Mismo desajuste mapa/casas | Arreglar en Mac, push, volver a deploy |

---

## Notas de esta iteración (mapa 2026-07)

- Mapa de referencia probado en local: **MAPA ACTUALIZADO CUATRO** (export RME).
- Casas: 35 (sin River Street I / II).
- Hub NPCs: Dufi `128,51,5`; Guild Master `129,51,5`.
- Spawns nuevos incluyen Enraged Hydra/Vampire, Angry Giant Spider, Mini Trainer Monk (zona ~129–134, 63).
- Depots y puertas: configurar en RME; evitar parches manuales al OTBM salvo casos puntuales.
