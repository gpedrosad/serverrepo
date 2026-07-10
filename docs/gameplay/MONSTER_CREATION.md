# Creacion de monstruos en Retro76 / YurOTS

Guia del flujo real para agregar un monstruo nuevo al server y hacer que tambien
aparezca en Remere's Map Editor (RME).

Caso real tomado como ejemplo: `Fury` (`2026-07-06`).

---

## Resumen corto

Para que un monstruo exista de punta a punta en este repo hacen falta **cuatro
piezas distintas**:

| Pieza | Archivo | Para que sirve |
|-------|---------|----------------|
| Definicion del monstruo | `server/YurOTS/ots/data/monster/NOMBRE.xml` | Stats, look, ataques, loot, voces, inmunidades |
| Registro en el server | `server/YurOTS/ots/data/monster/monsters.xml` | Hace que YurOTS pueda cargarlo por nombre |
| Visibilidad en RME | `rme-extensions/yurots-creatures.xml` | Lo mete en una categoria visible de la paleta |
| Spawn real en juego | `server/YurOTS/ots/data/world/test-spawn.xml` | Hace que aparezca en el mapa al correr el server |

Ademas, RME genera un `creatures.xml` propio a partir de los XML del repo con:

```bash
./scripts/setup-rme-creatures.sh
```

Eso exporta los monstruos a la data local de RME.

---

## Punto importante: RME y el server no usan exactamente la misma fuente

- **El server** necesita `NOMBRE.xml` + alta en `monsters.xml`.
- **RME** lee los XML de `data/monster/` y exporta criaturas si tienen
  `<look .../>`, incluso si todavia faltara el alta en `monsters.xml`.
- **El mapa `.otbm` no guarda el respawn real del server**. Los monstruos que
  respawnean salen de `test-spawn.xml`.

Consecuencia practica:

- si el XML existe pero no esta en `monsters.xml`, puede verse en RME pero el
  server no lo va a crear;
- si el monstruo existe en el server pero no esta en `test-spawn.xml`, no va a
  aparecer in-game;
- si existe en el server pero no esta en `yurots-creatures.xml`, puede seguir
  apareciendo en RME, pero probablemente quede mezclado en `Others` o solo
  importable manualmente.

---

## Flujo recomendado

### 1. Crear el XML del monstruo

Archivo:

```text
server/YurOTS/ots/data/monster/fury.xml
```

Base recomendada: copiar un monstruo parecido y ajustar numeros, en vez de
inventar todo desde cero.

Campos que importan mas:

| Campo | Para que sirve |
|-------|----------------|
| `<monster name="...">` | Nombre real del monstruo. Debe coincidir exacto con `monsters.xml` y con `test-spawn.xml`. |
| `speed` | Velocidad base de movimiento. |
| `staticattack` | Ritmo/agresividad de ataque del legacy YurOTS. |
| `changetarget` | Cada cuanto intenta cambiar de target. |
| `<health now="..." max="..."/>` | Vida total. |
| `<look .../>` | Apariencia. Tambien es clave para que RME pueda exportarlo. |
| `<combat targetdistance="..." />` | Si pelea melee o a distancia. |
| `<attacks>` | Daños, hechizos, runas, curas. |
| `<defenses>` | Inmunidades/resistencias legacy. |
| `<loot>` | Tabla de drop. |

### Regla practica para el look

Si queres que aparezca bien en RME:

- usa un `look type` que exista en los assets 7.6;
- si no tiene `<look .../>`, `setup-rme-creatures.sh` lo saltea;
- el nombre visual en RME sale del atributo `name`, no del nombre del archivo.

### Regla practica para el loot

Este repo mezcla sintaxis legacy. En la practica:

- oro, stacks y consumibles suelen usar `countmax`, `chance1`, `chancemax`;
- varios equipos usan `chance="..."` simple;
- si al boot ves `missing chance for loot id = ...`, ese item quedo mal definido.

Ejemplo real: en `Fury`, el item `2385` tuvo que quedar con `chance="22000"`
porque el parser estaba reclamando `missing chance`.

---

### 2. Darlo de alta en `monsters.xml`

Archivo:

```text
server/YurOTS/ots/data/monster/monsters.xml
```

Entrada minima:

```xml
<monster name="Fury" file="fury.xml" />
```

Sin este paso:

- el server no puede resolver el nombre al cargar spawns;
- `test-spawn.xml` puede referenciar `Fury`, pero YurOTS no la va a crear.

---

### 3. Validar que el server arranque limpio

Como toca data de monstruos, validar siempre el boot local:

```bash
docker compose -f docker-compose.prod.yml restart yurots
docker logs yurots --tail 50
python3 scripts/ot-probe.py 127.0.0.1 7171
```

Que deberias mirar:

- que llegue a `Retro76 Server Running...`;
- que no haya errores de parseo XML;
- que no haya warnings de loot mal formado;
- que el `ot-probe` responda `OK`.

Si el cambio fue delicado, tambien conviene correr:

```bash
bash scripts/test-local-smoke.sh
```

---

### 4. Hacer que aparezca en RME

Hay dos capas:

### 4.1 Export de criaturas a RME

Script:

```bash
./scripts/setup-rme-creatures.sh
```

Que hace hoy:

1. Lee `server/YurOTS/ots/data/monster/*.xml`
2. Lee `server/YurOTS/ots/data/npc/*.xml`
3. Toma los atributos de `<look .../>`
4. Excluye criaturas que ya existen en la lista base de Tibia 7.6
5. Escribe `creatures.xml` en la data local de RME

Destinos actuales:

- `~/dev/rme/build/data/user/data/760/creatures.xml`
- `~/Library/Application Support/.rme/data/760/creatures.xml`

### 4.2 Categoria visible en la paleta

Archivo:

```text
rme-extensions/yurots-creatures.xml
```

Si queres que no quede perdido en `Others`, agregalo a un tileset:

```xml
<tileset name="YurOTS Custom">
	<creatures>
		<creature name="Fury"/>
	</creatures>
</tileset>
```

Luego instalar la extension:

```bash
./scripts/setup-rme-extensions.sh
```

### 4.3 Abrir RME con todo sincronizado

La forma recomendada es:

```bash
./scripts/open-rme.sh
```

Ese script ya corre:

1. `setup-rme-config.sh`
2. `setup-rme-creatures.sh`
3. `setup-rme-extensions.sh`

Si RME ya estaba abierto, cerrarlo y volverlo a abrir.

Referencia operativa: [docs/RME_SETUP.md](../RME_SETUP.md)

---

### 5. Hacer que aparezca in-game

Que un monstruo exista en RME **no** significa que vaya a aparecer en el
servidor.

Para que exista en juego tiene que estar en:

```text
server/YurOTS/ots/data/world/test-spawn.xml
```

Opciones:

1. Pintar/exportar spawns desde RME.
2. Editar `test-spawn.xml` a mano.

Ejemplo minimo:

```xml
<spawn centerx="140" centery="50" centerz="7" radius="3">
	<monster name="Fury" x="0" y="0" z="7" spawntime="120" />
</spawn>
```

El nombre `Fury` tiene que coincidir exactamente con:

- `name="Fury"` dentro de `fury.xml`
- `<monster name="Fury" file="fury.xml" />` en `monsters.xml`

Si despues editas el mapa, el flujo completo de mapa/spawns esta documentado en
[docs/CAMBIAR-MAPA.md](../CAMBIAR-MAPA.md).

---

### 6. Checklist final

```text
[ ] Crear server/YurOTS/ots/data/monster/NOMBRE.xml
[ ] Verificar que tenga <look .../> valido
[ ] Darlo de alta en data/monster/monsters.xml
[ ] Reiniciar local + revisar docker logs
[ ] Ejecutar python3 scripts/ot-probe.py 127.0.0.1 7171
[ ] Agregarlo a rme-extensions/yurots-creatures.xml si queres categoria visible
[ ] Correr ./scripts/setup-rme-creatures.sh
[ ] Correr ./scripts/setup-rme-extensions.sh
[ ] Reabrir RME
[ ] Agregar spawn en test-spawn.xml o exportarlo desde RME
```

---

## Caso Fury

Archivos reales del alta de `Fury`:

| Archivo | Rol |
|---------|-----|
| `server/YurOTS/ots/data/monster/fury.xml` | Definicion del monstruo |
| `server/YurOTS/ots/data/monster/monsters.xml` | Registro para el server |
| `rme-extensions/yurots-creatures.xml` | Categoria visible `YurOTS Custom` en RME |

Caracteristicas cargadas:

- look femenino rojo (`look type 137`);
- mas rapida y mas fuerte que `Demon` (`speed="400"`, tier `Black Knight`);
- combate **cuerpo a cuerpo** (`targetdistance="1"`), sin ataque a distancia;
- melee fuerte mas hechizos de area (`firefield`, `demon fireball`,
  `demon_manadrain`) y autocura (`exura vita`);
- loot corregido para evitar warning de `missing chance`.

### Ajuste melee (jul 2026)

`Fury` arranco con `targetdistance="3"` y `throwingknife`, lo que la hacia
perseguir a distancia y tirar cuchillos. Para que pelee como un elite melee
(similar a `Demon`):

| Campo | Antes | Despues |
|-------|-------|---------|
| `<combat targetdistance>` | `3` | `1` |
| Ataque `throwingknife` | presente | eliminado |

Los hechizos instant/rune se mantienen: son parte del kit magico del monstruo
pero no obligan a mantener distancia de tiro.

### Velocidad (jul 2026)

`speed` subio de `260` a `400` para que persigan mucho mas rapido en melee
(referencia: `Black Knight` ~390, `Enraged Black Knight` ~420).

---

## Problemas tipicos

| Sintoma | Causa probable | Donde mirar |
|---------|----------------|-------------|
| No aparece en RME | Falta `<look .../>` o no se reexporto `creatures.xml` | `scripts/setup-rme-creatures.sh` |
| Aparece en RME pero no en juego | Falta alta en `monsters.xml` o falta spawn | `data/monster/monsters.xml`, `test-spawn.xml` |
| El server bootea con warning de loot | Item con sintaxis de chance incorrecta | `docker logs yurots --tail 50` |
| El spawn no sale nunca | Nombre distinto entre XML/registro/spawn | `fury.xml`, `monsters.xml`, `test-spawn.xml` |
| Queda en `Others` | No esta listado en `rme-extensions/yurots-creatures.xml` | extension RME |
