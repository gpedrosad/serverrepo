# Depots — mapa, XML y motor

Documento de referencia para **no romper depots** al cambiar mapa o deployar.
Incidente real: **jul 2026** — tras deploy de `test.otbm`, jugadores abrieron lockers del temple y vieron contenedor vacío. Los items **no se borraron**; seguían en `players/*.xml`.

Relacionado:

- [`../../AGENTS.md`](../../AGENTS.md) — reglas para agentes (sección 8, depots)
- [`../CAMBIAR-MAPA.md`](../CAMBIAR-MAPA.md) — workflow de cambio de mapa
- [`../../scripts/README-DEPLOY-VPS.md`](../../scripts/README-DEPLOY-VPS.md) — deploy seguro
- `server/YurOTS/ots/source/actions.cpp` — `resolveMapDepotId()`, `openContainer()`
- `server/YurOTS/ots/source/iomapotbm.cpp` — carga `OTBM_ATTR_DEPOT_ID`
- `scripts/scan-map-depots.py` — auditoría de lockers en OTBM
- `scripts/patch-map-depot-ids.py` — parche parcial (ver limitaciones)

---

## Cómo funciona (dos lugares distintos)

| Dónde | Qué guarda | Archivo / tile |
|-------|------------|----------------|
| **Mapa** | Locker visual (`2589`) que el jugador clickea | `data/world/test.otbm` |
| **Jugador** | Items reales del depot | `data/players/Nombre.xml` → `<depots><depot depotid="N">…` |

Al abrir un locker, el motor debe enlazar el tile del mapa con un **`depotid`** del XML del jugador. Si el locker no tiene depot id, YurOTS abre el contenedor **vacío del mapa** y el jugador cree que perdió todo.

### IDs en Retro76 (prod, jul 2026)

| `depotid` en XML | Uso típico | Players en VPS |
|------------------|------------|----------------|
| `1` | Temple / ciudad principal (lockers ~127–133) | 83 |
| `405` | Depots de casa (sistema house) | 30 |
| `2`–`5` | Otros (pocos) | 2 c/u |

Lockers del temple en el mapa actual (11 tiles):

```text
(127–133, 58, z=5–6) y (127, 53/55/57, z=7) — item 2589
```

---

## Síntomas y diagnóstico

| Síntoma | Causa probable | Los items ¿se borraron? |
|---------|----------------|-------------------------|
| Depot vacío al abrir locker | Locker sin `depotid` en OTBM / fallback C++ roto | **No** — siguen en XML |
| `You can not use this object` | Item no es contenedor usable | Revisar id del tile |
| Depot de otra ciudad vacío | Locker debería usar `depotid` distinto de `1` | Revisar id en RME |

### Comprobar que el XML del jugador tiene items

En VPS (solo lectura):

```bash
grep -o '<depot depotid="[0-9]*"' server/YurOTS/ots/data/players/TuChar.xml
grep -A5 'depot depotid="1"' server/YurOTS/ots/data/players/TuChar.xml | head
```

Si hay `<item` dentro del depot, los datos están bien; el problema es el enlace mapa → depotid.

### Auditar lockers en el OTBM

```bash
python3 scripts/scan-map-depots.py server/YurOTS/ots/data/world/test.otbm
```

Salida esperada en prod (con fallback C++ activo): puede mostrar `depotid=None` en todos los lockers — el servidor igual resuelve a `1` vía `resolveMapDepotId()`.

Si se quita el fallback C++, **todos** los lockers deben tener `depotid=1` (o el id correcto) antes de deployar.

---

## Por qué RME exporta lockers sin depot id

Los lockers colocados en RME suelen guardarse como **`OTBM_ATTR_ITEM` inline en el tile** (item `2589` embebido en propiedades del tile), **sin** atributo `OTBM_ATTR_DEPOT_ID` (10).

El loader (`iomapotbm.cpp`) solo asigna `container->depot` cuando el OTBM trae ese atributo en un nodo `OTBM_ITEM` hijo. Resultado: `container->depot == 0` → contenedor normal del mapa.

### Fix en código (commit `8acdba0`, jul 2026)

`actions.cpp` → `resolveMapDepotId()`:

- Si `container->depot != 0` → usa ese id (RME exportó bien).
- Si el item es `2589`, `2590`, `2591` o `2592` y `depot == 0` → **default `depotid = 1`** (temple).
- `openContainer()` usa ese id para abrir `player->getDepot(depotId)`.

**No mueve tiles** — funciona en las ubicaciones actuales del mapa.

---

## Checklist obligatorio antes de deploy de mapa

```text
[ ] python3 scripts/scan-map-depots.py server/YurOTS/ots/data/world/test.otbm
[ ] python3 scripts/sync-houses-with-map.py --dry-run
[ ] Levantar local: docker compose -f docker-compose.prod.yml up -d yurots
[ ] In-game: abrir locker temple con char que TENGA items en depotid=1
[ ] Confirmar que se ven los items guardados (no contenedor vacío)
[ ] bash scripts/test-local-smoke.sh
[ ] python3 scripts/ot-probe.py 127.0.0.1 7171
[ ] Backup VPS: BACKUP_LABEL=pre-map ./scripts/backup-runtime-data.sh --vps
[ ] Deploy: DEPLOY_I_READ_README=yes ./scripts/deploy-vps.sh
[ ] Post-deploy: probar locker in-game en prod
```

---

## Herramientas

### `scan-map-depots.py`

Lista cada locker `2589–2592` con coordenadas y `depotid` leído del OTBM.

```bash
python3 scripts/scan-map-depots.py mapa-viejo.otbm mapa-nuevo.otbm
```

Muestra diff de posiciones y depot ids.

### `patch-map-depot-ids.py` — limitación importante

Solo parchea lockers en nodos **`OTBM_ITEM` hijos**. **No** modifica lockers inline (`OTBM_ATTR_ITEM` en tile), que es el formato habitual de RME.

No confiar en este script como única solución. El fallback C++ en `actions.cpp` cubre el caso real de Retro76.

---

## Reglas para deploy (data sagrada)

1. **`players/*.xml`** contiene los depots reales — nunca commitear, nunca borrar en VPS.
2. **`deploy-vps.sh`** hace backup y restaura `players/` con `cp -an` — no pisa depots existentes.
3. Cambiar `test.otbm` **no borra** items del XML; solo puede desconectar lockers si se rompe el `depotid`.
4. **Nunca** `git stash -u` en VPS (incidente cuentas jun 2026).

---

## Si vuelve a pasar en producción

1. **No entrar en pánico** — verificar XML del jugador (items suelen estar).
2. Confirmar que el binario tiene `resolveMapDepotId` (rebuild tras `actions.cpp`).
3. Probar locker temple in-game.
4. Si un locker nuevo necesita otro id: colocar en RME con depot id explícito **o** extender `resolveMapDepotId()` en C++.
5. Rollback de mapa solo si moviste lockers a coordenadas incorrectas — backup en `~/ot-backups/`.

---

## Errores frecuentes (agentes)

| Error del agente | Consecuencia |
|------------------|--------------|
| Deployar mapa sin probar depot in-game | Jugadores ven depot vacío |
| Asumir que items “desaparecieron” y tocar `players/*.xml` | Riesgo de pérdida real de data |
| Confiar solo en `patch-map-depot-ids.py` | No parchea formato RME inline |
| Mover lockers sin mantener `depotid=1` en temple | Misma ciudad, distinto enlace |
| No rebuild C++ tras tocar `actions.cpp` | Fix no activo en prod |
