# Auto-actualización del cliente Retro76 (plan pendiente)

> **Estado:** documentado, **no implementado** (julio 2026).  
> **Repo cliente:** `~/clienteretro` (mac/ + windows/).  
> **Repo juego/web:** `yurots-principal` (`web/`, `scripts/sync-clienteretro.sh`).

## Problema

- El cliente publicado corre desde **carpeta descomprimida** (ZIP → carpeta), no desde archive embebido.
- Los items Zagan viven en `data/things/760/Tibia.dat` + `Tibia.spr`. Si el jugador tiene sprites viejos, ve ítems incorrectos en juego.
- El módulo `modules/updater/` **ya existe** en OTClientV8, pero hoy está **desactivado**:
  - `Services.updater = ""` en `init.lua`
  - El updater solo arranca si `g_resources.isLoadedFromArchive()` → falso con carpeta suelta
  - `entergame.lua` solo llama al updater si **faltan** archivos, no si el checksum de `.dat`/`.spr` es viejo

## Recomendación

**Updater parcial de sprites**, no cliente completo en cada parche.

| Qué | Por qué |
|-----|---------|
| Parchear solo `data/things/760/Tibia.dat` + `Tibia.spr` | Es lo que cambia con items Zagan (~16 MB) |
| Check automático **al abrir** el cliente | El jugador no tiene que ir a la web |
| ZIP completo en `web/downloads/` | Solo para instalaciones nuevas |
| Una **última descarga manual** para quien ya tiene cliente | El cliente viejo no trae URL de updater configurada |

No recomendado por ahora: updater del binario en macOS (Gatekeeper), bajar todo el ZIP en cada parche, depender del opcode `LoginServerUpdateNeeded` del login (YurOTS no lo usa para sprites).

---

## Experiencia del jugador (cuando esté hecho)

### Quien ya tiene cliente (después de la migración única)

1. Abre `Iniciar Cliente.bat` / `.command`
2. Ventana **Updater** → “Checking for updates…”
3. Si hay parche: barra de progreso, descarga, aplica, reinicia (o sigue si solo cambiaron sprites)
4. Login normal → items Zagan se ven bien

**Tiempo estimado:** 10–30 s, sin descomprimir ZIP.

### Migración única (jugadores con cliente viejo)

- **Una vez:** descargar ZIP nuevo desde retro76.cl (incluye updater configurado + sprites Zagan)
- **Después:** solo parches automáticos al abrir

### Botón opcional

- “Buscar actualizaciones” en menú → `Updater.check()` manual si falló el check automático

---

## Arquitectura técnica

```
Jugador abre cliente
       │
       ▼
POST https://retro76.cl/api/updater.php
  { version, build, os, platform }
       │
       ▼
JSON manifest (checksums + URL base)
       │
       ▼
Compara con g_resources.filesChecksums() / fileChecksum()
       │
       ▼
Descarga solo archivos distintos desde url + path
       │
       ▼
g_resources.updateData() → reinicio si hace falta
```

### Respuesta JSON esperada (OTCv8)

```json
{
  "url": "https://retro76.cl/updater/files",
  "files": {
    "/data/things/760/Tibia.dat": "checksum_crc32_o_md5",
    "/data/things/760/Tibia.spr": "checksum_crc32_o_md5"
  },
  "keepFiles": true
}
```

Opcional para releases mayores:

```json
"binary": { "file": "/otclient_gl.exe", "checksum": "..." }
```

Referencia OTCv8: [OTCv8/otcv8-tools](https://github.com/OTCv8/otcv8-tools) (plantilla `updater.php`).

---

## Fase 1 — Cliente (clienteretro)

### 1.1 `init.lua` (mac + windows)

```lua
Services = {
  updater = "https://retro76.cl/api/updater.php",
  -- resto igual
}

-- Quitar isLoadedFromArchive(): cargar updater también en carpeta descomprimida
if type(Services.updater) == 'string' and Services.updater:len() > 4
  and g_modules.getModule("updater") then
  g_modules.ensureModuleLoaded("updater")
  return Updater.init(loadModules)
end
loadModules()
```

### 1.2 `modules/client_entergame/entergame.lua`

En `validateThings()`: comparar checksum de `760/Tibia.dat` y `760/Tibia.spr` **siempre** (no solo con `isLoadedFromArchive()`). Si difiere del esperado y existe `Updater`, llamar `Updater.check({ version = G.clientVersion, host = G.host })`.

Hoy el check de checksum se ignora en carpeta suelta (línea ~98); hay que invertir esa lógica para things o leer checksums desde el manifest del servidor.

### 1.3 Opcional: botón en topmenu

```lua
-- modules/client_topmenu/topmenu.lua
if Updater then
  -- ítem "Buscar actualizaciones" → Updater.check()
end
```

### 1.4 Publicar ZIP con todo lo anterior

```bash
cd ~/Desktop/yurots-principal
./scripts/sync-clienteretro.sh    # sprites Zagan → clienteretro
cd ~/clienteretro && ./build-zips.sh
# Subir web/downloads/Retro76-*.zip
```

Aviso en web/Discord: *última descarga manual; después se actualiza solo*.

---

## Fase 2 — Backend (retro76.cl / yurots-principal/web)

### 2.1 Estructura en el VPS

```
/var/www/retro76/
  api/updater.php          # POST → JSON manifest
  updater/files/
    data/things/760/
      Tibia.dat
      Tibia.spr
  downloads/               # ZIPs completos (ya existe)
    Retro76-Mac.zip
    Retro76-Windows.zip
```

### 2.2 `updater.php`

- Recibe POST JSON del cliente (`version`, `build`, `os`, `platform`)
- Devuelve `url` + `files` con checksums (CRC32b o MD5 — **mismo algoritmo** que use `HTTP.download` en el cliente)
- Cachear checksums en disco (regenerar cada N segundos o en deploy)
- Plantilla base: OTCv8 otcv8-tools

### 2.3 Script de publicación (crear)

Propuesta: `scripts/publish-client-patcher.sh`

```bash
# 1. Asegurar assets Zagan actuales
./scripts/install-zagan-test-env.sh

# 2. Copiar a staging del updater
cp zagan-test/client-things/760/* → web/updater-files/data/things/760/

# 3. Regenerar manifest / checksums para updater.php

# 4. (Opcional) sync clienteretro + build zips completos
./scripts/sync-clienteretro.sh
```

Integrar con `scripts/upload-client-downloads.sh` si aplica.

---

## Pipeline de release (items Zagan nuevos)

```bash
# Desarrollo
python3 scripts/build_zagan_test_assets.py
./scripts/install-zagan-test-env.sh

# Cliente público
./scripts/sync-clienteretro.sh
cd ~/clienteretro && ./build-zips.sh

# Producción (cuando exista publish-client-patcher.sh)
./scripts/publish-client-patcher.sh
./scripts/upload-client-downloads.sh   # zips + parche updater
```

Servidor de juego: debe cargar `items-zagan-test.otb` (o equivalente) para que server ids coincidan con el `.dat` del cliente.

---

## Archivos clave

| Archivo | Rol |
|---------|-----|
| `~/clienteretro/mac\|windows/init.lua` | `Services.updater`, arranque del módulo |
| `~/clienteretro/.../modules/updater/updater.lua` | Lógica de descarga (no tocar salvo bugfix) |
| `~/clienteretro/.../modules/client_entergame/entergame.lua` | Check al conectar |
| `~/clienteretro/sync-from-yurots.sh` | Copia Tibia.dat/spr desde yurots-principal |
| `yurots-principal/scripts/sync-clienteretro.sh` | Rebuild Zagan + sync clienteretro |
| `yurots-principal/zagan-test/client-things/760/` | Fuente de sprites parcheados |
| `yurots-principal/web/downloads/` | ZIPs para jugadores nuevos |

---

## Checklist de implementación

- [ ] Fase 1: cambios `init.lua` + `entergame.lua` en mac y windows (paridad)
- [ ] Fase 1: publicar ZIP “migración” + aviso en web
- [ ] Fase 2: `updater.php` en retro76.cl
- [ ] Fase 2: carpeta `updater/files/data/things/760/`
- [ ] Fase 2: `scripts/publish-client-patcher.sh`
- [ ] Probar: cliente viejo (sin parche) → migración manual una vez
- [ ] Probar: cliente con updater → cambiar `.spr` en servidor → abrir → parche automático
- [ ] Probar: Windows + macOS
- [ ] Documentar en `clienteretro/README.md` sección “Actualizaciones automáticas”

---

## Relacionado

- [CLIENT.md](./CLIENT.md) — cliente local de desarrollo
- [ZAGAN_TEST_ITEMS.md](./items-and-map/ZAGAN_TEST_ITEMS.md) — pipeline items custom
- [IMPORTAR_ITEM_DESDE_IMAGEN.md](./items-and-map/IMPORTAR_ITEM_DESDE_IMAGEN.md) — llevar items a producción
- `~/clienteretro/Contexto/MEMORY.md` — nota de pack Zagan en cliente publicado
- `~/clienteretro/README.md` — sync manual actual (`sync-from-yurots.sh`)
