# Respawn de monstruos en Retro76 / YurOTS

Documento de comportamiento actual del sistema de respawn de monstruos.
Describe como funciona hoy el motor, no como "deberia" funcionar.

Actualizado con el fix aplicado el `2026-07-06` para evitar duplicacion de
monstruos cuando eran lureados fuera del area del spawn, y el cambio del
`2026-07-10` que elimina el bloqueo por visibilidad de pantalla.

Relacionado:

- `server/YurOTS/ots/source/spawn.cpp`
- `server/YurOTS/ots/source/spawn.h`
- `server/YurOTS/ots/source/otserv.cpp`
- `server/YurOTS/ots/data/world/test-spawn.xml`
- `docs/CAMBIAR-MAPA.md`
- `docs/gameplay/RAGE_MONSTERS.md`

## Resumen corto

Hoy el respawn funciona asi:

1. **Aparece aunque haya gente mirando**: cuando vence el `spawntime` y el slot
   esta libre, el monstruo respawnea en el siguiente tick (hasta `20s`), sin
   esperar a que nadie vea el tile.
2. **No duplica si ya esta vivo**: el slot sigue ocupado mientras el monstruo
   exista, aunque se haya lureado fuera del area del spawn (fix `2026-07-06`).

El bug de duplicacion real por kiteo fuera del area fue corregido el
`2026-07-06`: ahora un monstruo vivo sigue ocupando su slot original aunque se
aleje del radio del spawn.

## Archivos que participan

### 1. Archivo de spawns del mapa

El mapa activo usa:

- `server/YurOTS/ots/data/world/test.otbm`
- `server/YurOTS/ots/data/world/test-spawn.xml`

El `.otbm` no guarda los monstruos activos del mundo. Solo referencia el archivo
externo de spawns. En OTBM, la referencia se lee por `OTBM_ATTR_EXT_SPAWN_FILE`.

### 2. Loader del mapa

Durante el arranque:

- `Map::loadMap(...)` devuelve `SPAWN_XML` para mapas `OTBM` y `XML`
- `otserv.cpp` inicializa `SpawnManager`
- `SpawnManager::loadSpawnsXML(...)` lee `test-spawn.xml`
- `SpawnManager::startup()` hace el spawn inicial

## Formato real de `test-spawn.xml`

Cada bloque:

```xml
<spawn centerx="153" centery="46" centerz="4" radius="5">
  <monster name="dragon" x="0" y="-1" z="4" spawntime="90" direction="2" />
</spawn>
```

Se interpreta asi:

- `centerx`, `centery`, `centerz`: centro del spawn area
- `radius`: radio cuadrado del area de spawn
- `monster x`, `monster y`: **offsets relativos** al centro, no coordenadas
  absolutas
- `monster z`: hoy el loader **no lo usa**; la Z efectiva sale de `centerz`
- `spawntime`: segundos en XML, milisegundos internamente
- `direction`: orientacion inicial

La posicion real del monstruo queda:

- `real_x = centerx + x`
- `real_y = centery + y`
- `real_z = centerz`

## Estado actual del mapa activo

Analizando `server/YurOTS/ots/data/world/test-spawn.xml` hoy:

- `373` bloques `<spawn>`
- `1201` slots `<monster>`
- `18` bloques `<spawn />` vacios
- no hay posiciones absolutas duplicadas
- no hay centros de spawn duplicados

Distribucion actual de `spawntime` (balance jul 2026, opcion C: +30% sobre opcion B):

- `175s`: `1049` slots (antes 135s en opcion B; 90s opcion A; 60s RL)
- `235s`: `152` slots (antes 180s; 120s; 90s RL)
- `290s`: `55` slots (antes 225s; 150s; 120s RL)
- otros valores: marginales (`50`–`90`, `585` bosses)

Promedio configurado: ~187 s (opcion B ~144 s; opcion A ~96 s; RL ~66 s).

Historial de tiers:

| Etapa | Tier comun | Promedio |
|-------|------------|----------|
| RL clasico | 60 / 90 / 120 s | ~66 s |
| Opcion A (jul 2026) | 90 / 120 / 150 s | ~96 s |
| Opcion B (jul 2026) | 135 / 180 / 225 s | ~144 s |
| **Opcion C (jul 2026)** | **175 / 235 / 290 s** | **~187 s** |

## Ciclo de vida actual de un spawn

### 1. Carga

`SpawnManager::loadSpawnsXML(...)` crea un `Spawn` por cada bloque `<spawn>` y
un slot interno por cada `<monster>`.

Cada slot guarda:

- nombre del monstruo
- posicion absoluta
- direccion
- `spawntime`
- `lastspawn`

### 2. Spawn inicial al boot

`Spawn::startup()` recorre todos los slots y llama `respawn(...)` de inmediato.

Consecuencia:

- al reiniciar el server, el mundo queda repoblado enseguida
- el `spawntime` no se espera al arrancar

### 3. Loop de chequeo

Si existe al menos un spawn, el server agenda `Game::checkSpawns(20000)`.

Eso significa:

- el respawn se revisa cada `20s`
- no es continuo ni por evento fino
- cualquier cosa "lista" sale en el siguiente tick de `20s`

### 4. Cuando un monstruo muere

En `Spawn::idle(...)`, si un monstruo asociado al slot aparece como
`isRemoved == true`:

- se actualiza `lastspawn = OTSYS_TIME()`
- se elimina del tracking activo del spawn

Consecuencia:

- el timer de respawn empieza a contar desde la remocion real

### 5. Cuando el monstruo sale del area del spawn

Este punto cambio el `2026-07-06`.

Comportamiento actual:

- si el monstruo sigue vivo pero sale del cuadrado del spawn
- **sigue ocupando su `spawnid` original**
- ese slot no vuelve a considerarse libre hasta que el monstruo muera o sea
  removido

Consecuencia directa:

- un monstruo lureado lejos **no** habilita un respawn duplicado del mismo slot
- si alguien deja un monstruo vivo muy lejos, ese spawn queda bloqueado hasta
  que ese monstruo desaparezca de verdad

Este tradeoff es intencional: es preferible un spawn bloqueado por un lure a
duplicar monstruos vivos en el mundo.

## Como decide reaparecer

Para cada slot:

1. Si no hay monstruo activo asociado a ese `spawnid`
2. y `OTSYS_TIME() - lastspawn >= spawntime`
3. entonces respawnea en el siguiente tick de chequeo (cada `20s`)

No hay bloqueo por visibilidad de pantalla desde el `2026-07-10`. La unica
proteccion contra duplicados es que el slot siga marcado como ocupado mientras
el monstruo original siga vivo.

## Cambio aplicado el 2026-07-10

Se elimino el bloqueo por `Player::CanSee(...)` que retenia el respawn mientras
un jugador normal veia el tile.

Comportamiento anterior (`2026-07-03` a `2026-07-09`):

- si el tile estaba visible, el monstruo no reaparecia todavia
- el timer no se reiniciaba
- al dejar de ver el tile, varios slots podian salir en rafaga

Comportamiento actual:

- el monstruo reaparece al vencer `spawntime` + proximo tick, aunque haya
  espectadores mirando
- no reaparece si el slot sigue ocupado (monstruo vivo, incluido lureado fuera
  del area)

## Cambio historico: visibilidad (2026-07-03, revertido 2026-07-10)

Entre el `2026-07-03` y el `2026-07-09` existia un bloqueo por visibilidad de
pantalla documentado en `docs/_archive/CAMBIOS_SESION_2026-07-03.md`. Ese
comportamiento ya no aplica.

## Cambio aplicado el 2026-07-06

En `Spawn::idle(...)` se elimino la logica que liberaba el slot cuando un
monstruo salia del area del spawn sin morir.

Antes:

- el monstruo se movia internamente a la clave `0`
- el `spawnid` original quedaba libre
- pasado el `spawntime`, el spawn podia crear otro monstruo
- si el original seguia vivo, se producia duplicacion real

Ahora:

- el monstruo conserva su `spawnid`
- el slot sigue ocupado mientras ese monstruo exista
- no deberian aparecer duplicados por lure fuera del radio

## Por que hoy puede parecer lento un spawn

### Monstruo lureado fuera del area

Si alguien deja un monstruo vivo lejos del spawn original, ese slot no genera
otro hasta que el primero muera o sea removido. Esto es intencional para evitar
duplicados.

## Bug historico corregido

### Duplicacion por kiteo fuera del radio

Antes del fix del `2026-07-06`, el siguiente escenario podia duplicar monstruos:

1. Un monstruo salia vivo del area cuadrada de su spawn.
2. El spawn dejaba de contarlo como ocupante del slot.
3. Cuando se cumplia el `spawntime`, el slot podia crear otro monstruo.
4. El monstruo original podia seguir vivo fuera del area.

Resultado historico:

- habia dos criaturas relacionadas al mismo slot de spawn
- si esto se repetia, el mapa podia verse "acumulado"

Ese ya no deberia ser el comportamiento del binario actualizado.

## Cosas que NO afectan este respawn

El sistema de `rage monsters` es aparte:

- puede crear una variante especial al morir un monstruo
- no usa el loop normal de `spawn.cpp`
- no reemplaza ni bloquea el slot base del spawnpoint

Ver `docs/gameplay/RAGE_MONSTERS.md`.

## Quirks utiles para mantenimiento

- El area del spawn se evalua como cuadrado alrededor del centro, no como
  circulo.
- El check corre cada `20s`, asi que siempre hay granularidad gruesa.
- `monster z` en XML no gobierna el spawn real; manda `centerz`.
- Un restart del server repuebla inmediatamente todos los slots.
- Los bloques `<spawn />` vacios no hacen nada.

## Como probarlo

### Prueba de respawn con espectadores

1. Mata monstruos de un mismo sector.
2. Quedate mirando el tile donde deberian reaparecer.
3. Espera su `spawntime` mas el siguiente tick de hasta `20s`.

Esperado hoy:

- el monstruo reaparece aunque sigas mirando el tile

### Prueba del fix de no-duplicacion

1. Lurea un monstruo fuera del cuadrado de su spawn.
2. Mantenelo vivo.
3. Espera su `spawntime` mas el siguiente tick de hasta `20s`.
4. Volve al spawn original.

Esperado hoy:

- el spawn original **no** deberia generar otro monstruo mientras el primero
  siga vivo

## Diagnostico actual

Con el codigo actual:

- **si no reaparece pese a haber pasado el `spawntime`**: el slot sigue ocupado
  (monstruo vivo, a menudo lureado fuera del area) o el tile no admite
  `placeCreature`
- **si aparecen monstruos extra vivos al mismo tiempo**: el binario corriendo no
  incluye el fix del `2026-07-06`, o existe otro camino distinto al tracking
  normal del spawn
