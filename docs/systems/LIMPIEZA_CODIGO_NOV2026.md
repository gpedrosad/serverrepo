# Limpieza y optimización del código (nov 2026)

Qué se simplificó en el servidor, cómo se comprobó que el juego no cambia, qué quedó pendiente y
las reglas para no volver a ensuciarlo. La revisión de NPCs de la misma semana está en
[`../gameplay/NPC_SYSTEM.md`](../gameplay/NPC_SYSTEM.md) §9.

**Resultado:** el C++ pasó de 815 a 121 condicionales `#if` y perdió ~3.800 líneas netas (y 6 archivos)
**sin cambiar el binario de Linux**. Se sacaron 12 MB de binarios del repo. La web dejó de leer
todos los jugadores en cada visita. Nada de esto se compiló en la Mac mini. Después (2026-11-12) se buscaron errores de memoria con
sanitizers y bots: ver [SANITIZER_TESTS.md](SANITIZER_TESTS.md).

---

## 1. Qué se hizo

| Commit (en `main`) | Qué | Cambia el juego |
|---|---|---|
| `a51bc85` | Saca de git el binario `source/yurots` (12 MB, ya estaba en `.gitignore`), `otserv.rar`, los proyectos de Windows (`msvc/`, `devcpp/`, `otserv.ico`) y dos copias viejas del mapa | No |
| `ea10f1a` | Fija en el código las 54 opciones `-DYUR_*`/`-DTLM_*`/... del `Makefile` (todas estaban siempre activas) y borra los bloques que nunca se compilaban (`TR_ANTI_AFK`, `USING_VISUAL_2005`, `TP_TRASH_BINS`, `ENABLESQLMAPSUPPORT`, `CVS_*`, `MAGICLEVEL_TEST`) | No |
| `6bcc70c` | Saca el código de Windows (`WIN32`, `__WINDOWS__`, `_MSC_VER`), MySQL (`__USE_MYSQL__`), el asignador de depuración (`__OTSERV_ALLOCATOR*__`) y el exception tracer de Windows. Borra `mdump.*`, `allocator.*`, `exception.*` (quedaron vacíos o sin uso); el `Makefile` compila todos los `.cpp` | No |
| `28192f3` | Borra 262 bloques de código comentado (`//std::cout...`, `/* case ...: */`), ~730 líneas. Los comentarios que explican se quedan | No |
| `20dc6c2` | Web: `/api/data` guarda el resultado 30 s (`WEB_PAYLOAD_TTL`) en vez de parsear el XML de todos los jugadores en cada visita; si llegan varias visitas juntas lo arma una sola. Se borran los tests del Most Wanted (sistema sacado en julio) | Solo la web: los datos de la portada pueden tener hasta 30 s de atraso |
| `a851f34` (merge de `build-o2`) | Compila con `-O2 -g -fno-strict-aliasing` (antes `-O0`, el modo de depurar). `make OPT=-O0` vuelve al anterior | **Sí** (más rápido). En uso en la ThinkPad desde el 2026-11-11 |
| 2026-11-12 (ver git log) | Pruebas con AddressSanitizer/UBSan y bots ([SANITIZER_TESTS.md](SANITIZER_TESTS.md)): arregla una caída remota sin login, dos corrupciones de memoria y una carrera al leer `config.lua`. El build queda con `-Wall` sin avisos y sin `-fpermissive`. El log deja de llenarse con el healthcheck y rota solo | No (salvo que ya no se cae con esos paquetes) |

### Decisiones

- **Binario fuera de git:** el binario se compila en el servidor (hoy la ThinkPad) en cada deploy de C++,
  así que no hace falta versionarlo. El script de deploy del VPS de entonces hacía `git pull` y después
  `make clean && make`.
- **Mapas:** `test-original.otbm` era idéntico (md5) a `backups/yurots-original.otbm`; se dejó el
  de `backups/`, que es el que citan los docs. `test-edited-backup.otbm` era un backup viejo.
  Ambos siguen en la historia de git.
- **`docs/items-and-map/map-kb/*.json` se quedan** (10 MB): incluyen etiquetas hechas con
  DeepSeek/OpenCode que no se regeneran gratis.
- **Bounty Master:** el NPC se borró en la revisión de NPCs porque su C++ ya se había sacado en
  `35373e0`. Diseño en [`../gameplay/MOST_WANTED_SYSTEM.md`](../gameplay/MOST_WANTED_SYSTEM.md).
- **Lo que queda de `#if`** (121): plataforma Linux (`__GNUC__`, `MSG_NOSIGNAL`), depuración
  (`__DEBUG__`, `__DEBUG_CRITICALSECTION__`, `__DEBUG__EVENTSCHEDULER__`, `__DEBUG_NPC__`) y guardas
  de headers. Las de depuración se dejaron a propósito: sirven para diagnosticar.

---

## 2. Cómo se comprobó (sin compilar)

La Mac mini no compila y la ThinkPad todavía no tiene Docker para el usuario `gonzalo`, así que la
prueba es que **el código que ve el compilador es el mismo**:

```bash
# toda la limpieza contra el main de antes (823d2ce): resuelve cada #if con la configuración real
# del build de Linux y compara el código sin comentarios
python3 scripts/code/check-cpp-equivalence.py --flags scripts/code/linux-build-flags.h 823d2ce
# -> 110 iguales, 0 distintos

# solo comentarios (paso 28192f3)
python3 scripts/code/check-cpp-equivalence.py --comments 6bcc70c
```

- `scripts/code/linux-build-flags.h`: las 54 opciones que el `Makefile` tenía activas
  (`#define`), las que nunca se activaban y las de Windows/MySQL (`#undef`), y `__GNUC__`.
  Es el formato de `unifdef -f`; no lleva comentarios.
- `check-cpp-equivalence.py` pasa los dos lados por `unifdef` con esa configuración (cualquier
  otra macro, sin definir), saca comentarios y espacios, y compara archivo por archivo. Necesita
  `unifdef` (viene con las Xcode Command Line Tools; en Linux `apt install unifdef`).
- Los 6 archivos borrados no entran en la comparación: se comprobó con `grep` que nada los incluye
  ni usa sus símbolos (`ExceptionHandler`, `MiniDumper`, `functionMap`...). Si algo los usara, el
  link fallaría al compilar, no el juego.
- Web: prueba con 10 pedidos simultáneos (1 sola lectura, se renueva al vencer) y
  `python3.11 -m unittest test_data test_bug_reports` en `web/`.

### Repetir la limpieza de comentarios

```bash
cd server/YurOTS/ots/source
python3 ../../../../scripts/code/strip-dead-comments.py --dry *.cpp *.h   # cuenta
python3 ../../../../scripts/code/strip-dead-comments.py *.cpp *.h         # aplica
cd - && python3 scripts/code/check-cpp-equivalence.py --comments HEAD
```

Cuenta como código desactivado lo que termina en `;` `{` `}` (con paréntesis, `=`, `->`, `::`...)
o empieza con `if(`/`for(`/`return`. No toca licencias ni comentarios con TODO/FIXME/NOTE/YUR CHANGE.
Hoy da 0: ya está aplicado.

---

## 3. Reglas para adelante

1. **No agregar `#ifdef` para activar funciones nuevas.** Si algo se puede apagar, que sea por
   `config.lua`. Las opciones de compilación terminaban siempre activas y solo ensuciaban.
2. **Solo Linux.** No volver a agregar código de Windows ni proyectos de IDE.
3. **Código que no se usa se borra, no se comenta.** Queda en git.
4. **Nada compilado en git** (ya estaba en `AGENTS.md` regla 3; ahora se cumple).
5. Para limpiezas mecánicas del C++: hacerlas con herramienta (`unifdef`, scripts) y comprobar con
   `check-cpp-equivalence.py` antes del commit.

---

## 4. Pendiente

| Qué | Estado / por qué |
|---|---|
| **Tres cuentas de azar mal hechas** | Loot a la mitad de lo configurado, monstruos que cambian de blanco siempre y escudos que bloquean ~5 veces menos de lo pensado. Se corrigen desde `config.lua`: loot y cambio de blanco prendidas el 2026-11-12; **falta probar y decidir la de los escudos** (`fixshielddefense`) ([SANITIZER_TESTS.md](SANITIZER_TESTS.md) § 5) |
| **Guardado automático congela el juego** | `Game::serverSave()` guarda el XML de cada jugador con `gameLock` tomado (cada ~10 min). Primero medir en el log del servidor de la ThinkPad (`server save... ok (Xs)`, solo lectura, con OK). Si vale la pena: guardar solo los que cambiaron o escribir fuera del lock |
| **`bind2nd`/`mem_fun` → lambdas** | 19 usos (sobre todo `game.cpp`); ya no existen en C++17 y atan el build a `gnu++14`. Solo hace falta para subir de estándar: hoy compilan sin avisos (`-Wno-deprecated`) |
| **Hechizos repetidos** | 28 archivos de crear runas casi idénticos y 7 copias del haste de monstruos; se pueden pasar a una tabla en `spells/lib` (confirmar que `spells.xml` acepta un script compartido) |
| **Web con Python 3.13+** | `web/premium_orders.py` usa el módulo `cgi`, que Python 3.13 eliminó. Si el servidor actualiza Python, se cae la página de pedidos premium |
| **Test `test_spells`** | Espera que el paladín promovido tenga `utani slow`; o falta el hechizo o el test quedó viejo |
| **Orden del repo** | `scripts/` (172 archivos, muchos generadores de mapa de un solo uso) y `docs/` (12 MB, notas de sesiones viejas) → `_archive/` |
| **Repetir las pruebas con bots** | Después de cambios grandes de C++ (protocolo, movimiento, combate): [SANITIZER_TESTS.md](SANITIZER_TESTS.md). Los bots todavía no comercian con NPC, no usan casas ni el depot |
| No se toca | La red de un hilo por jugador y partir `game.cpp` (8.000 líneas): mucho riesgo para lo que gana el jugador |
