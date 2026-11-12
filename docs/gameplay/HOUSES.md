# Casas — dueños, items y deploy

Documento de **data runtime de casas** en Retro76 / YurOTS: qué archivos guardan dueños,
qué pisa el deploy y cómo recuperar si algo sale mal.

Relacionado:

- `server/YurOTS/ots/data/houses.xml` — tiles de cada casa (generado desde mapa)
- `server/YurOTS/ots/data/houses/*.xml` — **dueños y permisos por casa**
- `server/YurOTS/ots/data/houseitems.xml` — items dentro de casas
- `docs/systems/THINKPAD_TEST_SERVER.md` (deploy), `scripts/backup-runtime-data.sh`
- `docs/CAMBIAR-MAPA.md`

## Dos capas distintas (no mezclar)

| Archivo / carpeta | Qué es | ¿En git? | ¿Quién lo cambia? |
|-------------------|--------|----------|-------------------|
| `data/houses.xml` | Tiles de cada casa en el mapa | Sí | `sync-houses-from-rme.py` al exportar mapa |
| `data/houses/<nombre>.xml` | Dueño, subowners, guests, doorowners, frontdoor | Sí (plantillas vacías) + **runtime en el servidor** | Jugadores al comprar casa; GM con `/owner` |
| `data/houseitems.xml` | Items colocados en casas | No (runtime del servidor) | Motor al guardar |

Ejemplo de dueño en runtime:

```xml
<?xml version="1.0"?>
<house>
  <frontdoor x="215" y="105" z="7"/>
  <owner name="Santry"/>
</house>
```

Plantilla sin dueño (normal en repo Mac):

```xml
<owner name=""/>
```

En el **servidor** (hoy la ThinkPad; no hay producción), los archivos de `data/houses/` con dueño real **solo viven ahí**.
El repo puede tener plantillas vacías o copias viejas; **no son la fuente de verdad de quién es dueño**.

## Incidente jul 2026 — dueños borrados en deploy

**Qué pasó (10 jul 2026):**

1. Varios jugadores tenían dueños en `data/houses/*.xml` **solo en el VPS** de entonces (cambios nunca commiteados).
2. El deploy hacía `git pull` pero **no** respaldaba ni restauraba `data/houses/`.
3. Se ejecutó `git checkout -- data/houses/` antes del deploy → los XML volvieron a las plantillas del repo (`owner name=""`).
4. Casas como Great Street quedaron sin dueño; otras (ej. Sand Mansion) seguían en git con dueño y no se perdieron.

**Lección:** tratar `data/houses/` como data sagrada en el servidor, igual que `houseitems.xml`.

## Qué protege el deploy hoy (ThinkPad)

El deploy de la ThinkPad ([`../systems/THINKPAD_TEST_SERVER.md`](../systems/THINKPAD_TEST_SERVER.md)):

1. Compara los archivos que trae `main` con los cambiados en la ThinkPad (incluye `data/houses/*.xml` con dueño). Si se cruzan, se para y se pregunta.
2. **Backup** de `houses`, `houseitems.xml`, `players`, `accounts`, `private_trainers.xml`, etc. → `~/backups/pre-deploy-FECHA/`
3. `git merge --ff-only origin/main`

El script de deploy del VPS de entonces (desde el fix de jul 2026) respaldaba `data/houses/` antes del `git pull`, lo restauraba después y abortaba si bajaba el número de casas con dueño.

`scripts/backup-runtime-data.sh` incluye `data/houses/` en sus backups.

## Comandos prohibidos en el servidor (ThinkPad)

| Comando | Riesgo |
|---------|--------|
| `git checkout -- data/houses/` | Borra dueños locales no commiteados |
| `git reset --hard` sin backup de `data/houses/` | Igual |
| Copiar `data/houses/` desde la Mac a la ThinkPad | Pisa dueños reales con plantillas vacías |

## Cómo verificar dueños en la ThinkPad

```bash
cd ~/apps/serverrepo
# Casas con dueño asignado
grep -h 'owner name=' server/YurOTS/ots/data/houses/*.xml | grep -v 'owner name=""'

# Conteo rápido
grep -h 'owner name=' server/YurOTS/ots/data/houses/*.xml | grep -cv 'owner name=""'
```

In-game: mirar la puerta de la casa → debe decir quién es el dueño.

## Recuperación si faltan dueños

1. Buscar backup reciente:

```bash
ls -lt ~/backups/ ~/ot-backups/ 2>/dev/null
grep house_owners ~/ot-backups/*/BACKUP_INFO.txt 2>/dev/null   # backups de backup-runtime-data.sh
```

2. Restaurar solo casas:

```bash
BACKUP=~/backups/pre-deploy-FECHA   # el que tenga los dueños
cp -a "$BACKUP/houses/." server/YurOTS/ots/data/houses/
docker restart -t 45 yurots
```

3. Si no hay backup con dueños, revisar `git stash list` en la ThinkPad (último recurso) o reasignar con GM `/owner`.

## Cambio de mapa vs dueños

- Cambiar `test.otbm` / regenerar `houses.xml` **no** borra dueños en `data/houses/*.xml` si los nombres de casa se mantienen.
- Si **renombrás o eliminás** una casa en RME, el XML de dueño viejo queda huérfano; la casa nueva empieza vacía.
- `houseitems.xml` es independiente; el deploy ya lo preserva.

Ver checklist de mapa en `docs/CAMBIAR-MAPA.md` y depots en `docs/gameplay/DEPOTS.md`.

## Items fantasma en casa (look vs `houseitems.xml`)

Síntoma típico: en un SQM se ve un item “fantasma” encima de otro (ej. algo flotando sobre una fire sword), pero al mirar el save no hay un tercer id.

### Diagnóstico rápido (ThinkPad, solo lectura)

```bash
ssh thinkpad
cd ~/apps/serverrepo
# Reemplazar X Y Z
python3 - <<'PY'
from pathlib import Path
import re
x, y, z = 166, 39, 7
t = Path("server/YurOTS/ots/data/houseitems.xml").read_text(encoding="utf-8", errors="replace")
m = re.search(rf'<tile x="{x}" y="{y}" z="{z}">(.*?)</tile>', t, re.S)
print(m.group(0) if m else "tile no está en houseitems.xml")
PY
```

Caso documentado **Great Street IV / Maximus** (`166, 39, 7`, jul 2026):

| Capa | Contenido |
|------|-----------|
| OTBM | solo piso `405` |
| `houseitems.xml` | `<item id="2528"/>` (tower shield) + `<item id="2392"/>` (fire sword) |

No había tercer item en disco. El “fantasma” era el **tower shield debajo** mal dibujado sobre la fire sword (orden de stack / sprite grande).

### Arreglo recomendado: in-game (sin tocar XML)

1. Entrar con dueño/subowner o GM.
2. En `166, 39, 7`: sacar la fire sword y el tower shield (o limpiar el tile con GM).
3. Volver a poner solo lo deseado (si quieren solo la espada, no dejen el `2528`).
4. Esperar un save de casas / logout de quien tenga la casa abierta, o reiniciar luego para persistir.

Preferible cuando el server está online y no querés downtime.

### Arreglo por XML en la ThinkPad (cuando haga falta)

`houseitems.xml` se carga al **boot**. Si editás el XML con el OT corriendo y reiniciás, el **stop suele guardar** la memoria otra vez y **pisa** tu edición. Orden obligatorio:

```bash
ssh thinkpad
cd ~/apps/serverrepo
DATA=server/YurOTS/ots/data
BACKUP=~/backups/house-ghost-$(date -u +%Y%m%d-%H%M%S)
mkdir -p "$BACKUP"
cp -a "$DATA/houseitems.xml" "$BACKUP/"
echo "Backup: $BACKUP"

# 1) Parar OT (puede reescribir houseitems al bajar — por eso el backup previo)
docker stop -t 45 yurots

# 2) Editar DESPUÉS del stop (en el archivo ya guardado por el shutdown)
python3 - <<'PY'
from pathlib import Path
import re
p = Path("server/YurOTS/ots/data/houseitems.xml")
t = p.read_text(encoding="utf-8", errors="replace")
old = '<tile x="166" y="39" z="7"><item id="2528"/><item id="2392"/></tile>'
new = '<tile x="166" y="39" z="7"><item id="2392"/></tile>'
if old not in t:
    raise SystemExit("bloque esperado no encontrado — revisar XML a mano antes de seguir")
p.write_text(t.replace(old, new, 1), encoding="utf-8")
print("OK: quitado 2528 en 166,39,7; queda solo fire sword 2392")
PY

# 3) Subir y verificar protocolo
docker start yurots
# esperar unos segundos
python3 scripts/ot-probe.py 127.0.0.1 7171
```

Verificación in-game: en `166, 39, 7` solo debe verse la fire sword (sin fantasma/escudo).

### Rollback

```bash
BACKUP=~/backups/house-ghost-FECHA   # el del paso anterior
docker stop -t 45 yurots
cp -a "$BACKUP/houseitems.xml" ~/apps/serverrepo/server/YurOTS/ots/data/houseitems.xml
docker start yurots
python3 scripts/ot-probe.py 127.0.0.1 7171
```

Nota: el 2026-07-18 este fix XML **no** se llegó a aplicar en el VPS de entonces (solo quedó el backup previo).

### Para agentes

- **Nunca** editar `houseitems.xml` en caliente y reiniciar sin asumir que el stop re-guarda.
- Backup **antes** del stop y, si hace falta, re-chequear el bloque del tile **después** del stop.
- No tocar otros tiles ni el chest de `167,39,7` (tiene mucho contenido anidado).

---

## Para agentes IA

- **Nunca** `git checkout` ni `git reset` sobre `data/houses/` en la ThinkPad.
- Deploy **solo** con el OK de Gonzalo, siguiendo `docs/systems/THINKPAD_TEST_SERVER.md`.
- Si un jugador reporta “perdí mi casa”, verificar primero `data/houses/<nombre>.xml` en la ThinkPad antes de tocar `players/*.xml`.
- Los dueños que el admin asigna a mano **no deben perderse** en el próximo deploy: si `main` trae ese mismo archivo, parar y preguntar; el backup pre-deploy los guarda.
- Items fantasma / stack raro en casa: sección **Items fantasma en casa** arriba (no asumir pérdida de data).
