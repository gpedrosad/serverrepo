# Casas — dueños, items y deploy

Documento de **data runtime de casas** en Retro76 / YurOTS: qué archivos guardan dueños,
qué pisa el deploy y cómo recuperar si algo sale mal.

Relacionado:

- `server/YurOTS/ots/data/houses.xml` — tiles de cada casa (generado desde mapa)
- `server/YurOTS/ots/data/houses/*.xml` — **dueños y permisos por casa**
- `server/YurOTS/ots/data/houseitems.xml` — items dentro de casas
- `scripts/deploy-vps.sh`, `scripts/backup-runtime-data.sh`
- `docs/CAMBIAR-MAPA.md`

## Dos capas distintas (no mezclar)

| Archivo / carpeta | Qué es | ¿En git? | ¿Quién lo cambia? |
|-------------------|--------|----------|-------------------|
| `data/houses.xml` | Tiles de cada casa en el mapa | Sí | `sync-houses-from-rme.py` al exportar mapa |
| `data/houses/<nombre>.xml` | Dueño, subowners, guests, doorowners, frontdoor | Sí (plantillas vacías) + **runtime en VPS** | Jugadores al comprar casa; GM con `/owner` |
| `data/houseitems.xml` | Items colocados en casas | No (runtime VPS) | Motor al guardar |

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

En **producción**, los archivos de `data/houses/` con dueño real **solo deben vivir en el VPS**.
El repo puede tener plantillas vacías o copias viejas; **no son la fuente de verdad de quién es dueño**.

## Incidente jul 2026 — dueños borrados en deploy

**Qué pasó (10 jul 2026):**

1. Varios jugadores tenían dueños en `data/houses/*.xml` **solo en el VPS** (cambios nunca commiteados).
2. El deploy hacía `git pull` pero **no** respaldaba ni restauraba `data/houses/`.
3. Se ejecutó `git checkout -- data/houses/` antes del deploy → los XML volvieron a las plantillas del repo (`owner name=""`).
4. Casas como Great Street quedaron sin dueño; otras (ej. Sand Mansion) seguían en git con dueño y no se perdieron.

**Lección:** tratar `data/houses/` como data sagrada en VPS, igual que `houseitems.xml`.

## Qué hace el deploy hoy (desde fix jul 2026)

`scripts/deploy-vps.sh`:

1. Cuenta casas con dueño **antes** del pull.
2. **Backup** de `data/houses/` → `~/ot-backups/pre-deploy-FECHA/houses/`
3. `git pull`
4. **Restaura** `data/houses/` desde el backup (`cp -a`, sobrescribe lo que git haya pisado)
5. Si baja el número de casas con dueño → **aborta** el deploy

También respalda/restaura: `players/`, `accounts/`, `houseitems.xml`, `private_trainers.xml`, etc.

`scripts/backup-runtime-data.sh` incluye `data/houses/` en backups locales y VPS.

## Comandos prohibidos en el VPS

| Comando | Riesgo |
|---------|--------|
| `git checkout -- data/houses/` | Borra dueños locales no commiteados |
| `git reset --hard` sin backup de `data/houses/` | Igual |
| Copiar `data/houses/` desde Mac al VPS | Pisa dueños reales con plantillas vacías |

## Cómo verificar dueños en el VPS

```bash
cd ~/yurots-principal
# Casas con dueño asignado
grep -h 'owner name=' server/YurOTS/ots/data/houses/*.xml | grep -v 'owner name=""'

# Conteo rápido
grep -h 'owner name=' server/YurOTS/ots/data/houses/*.xml | grep -cv 'owner name=""'
```

In-game: mirar la puerta de la casa → debe decir quién es el dueño.

## Recuperación si faltan dueños

1. Buscar backup reciente:

```bash
ls -lt ~/ot-backups/
grep house_owners ~/ot-backups/pre-deploy-*/BACKUP_INFO.txt 2>/dev/null
```

2. Restaurar solo casas:

```bash
BACKUP=~/ot-backups/pre-deploy-FECHA   # el que tenga house_owners > 0
cp -a "$BACKUP/houses/." server/YurOTS/ots/data/houses/
docker compose -f docker-compose.prod.yml restart yurots
```

3. Si no hay backup con dueños, revisar `git stash list` en el VPS (último recurso) o reasignar con GM `/owner`.

## Cambio de mapa vs dueños

- Cambiar `test.otbm` / regenerar `houses.xml` **no** borra dueños en `data/houses/*.xml` si los nombres de casa se mantienen.
- Si **renombrás o eliminás** una casa en RME, el XML de dueño viejo queda huérfano; la casa nueva empieza vacía.
- `houseitems.xml` es independiente; el deploy ya lo preserva.

Ver checklist de mapa en `docs/CAMBIAR-MAPA.md` y depots en `docs/gameplay/DEPOTS.md`.

## Para agentes IA

- **Nunca** `git checkout` ni `git reset` sobre `data/houses/` en el VPS.
- Deploy **solo** con `DEPLOY_I_READ_README=yes ./scripts/deploy-vps.sh`.
- Si un jugador reporta “perdí mi casa”, verificar primero `data/houses/<nombre>.xml` en el VPS antes de tocar `players/*.xml`.
- Los dueños que el admin asigna manualmente en prod **no deben perderse** en el próximo deploy: el script los restaura del backup pre-pull.
