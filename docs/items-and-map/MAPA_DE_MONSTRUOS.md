# Mapa interactivo de monstruos

Página HTML con todos los pisos de `test.otbm` **como se ven en el juego** (sprites reales) y cada monstruo y NPC dibujado en su lugar. Sirve para ver qué hay en cada lugar del mundo, buscar un monstruo y saltar entre sus spawns.

```bash
python3 -m pip install pillow                                   # una vez (la vista del juego lo necesita)
python3 scripts/map/build-monster-map.py SALIDA/                # vista del juego + minimapa (~90 s, ~55 MB)
python3 scripts/map/build-monster-map.py SALIDA/ --minimap      # solo minimapa, sin Pillow (~5 s)
```

Escribe `SALIDA/monstruos.html` y `SALIDA/monstruos/`:

| Carpeta | Contenido |
|---------|-----------|
| `t/{piso}/{nivel}/{i}_{j}.webp` | Mosaicos de 512 px con los sprites del juego (`scripts/map/game_render.py`). Nivel 0 = tamaño real (32 px por casilla, 16×16 casillas por mosaico); cada nivel siguiente es la mitad, hasta 1 px por casilla. El visor carga el nivel que corresponde al zoom, como Google Maps. |
| `look/*.png` | Cada monstruo y NPC mirando al sur, con los colores de su outfit (head/body/legs/feet) aplicados con la misma fórmula que el cliente. |
| `z*.png` | Minimapa por piso (1 px por casilla), de fondo mientras cargan los mosaicos. |
| `data.json` | Spawns, NPC, zonas y datos de cada monstruo. |

Si `SALIDA` es el sitio local de Retro76 (con `site.css` y `menu.js`), la página aparece con el menú común; sin ellos funciona igual. Solo lee el repo. Los sprites salen del `Tibia.dat`/`.spr` de RME (`devtools/rme/rme-client-760`): los ítems Zagan que reutilizan ids se ven con el sprite vanilla, igual que en map-kb.

## Qué muestra

- **Vista del juego:** de cerca, cada casilla con sus sprites (suelo, bordes, paredes, ítems, elevación). Desactivándola se ve el minimapa de colores.
- **Monstruos y NPC dibujados:** desde un zoom de 10 px por casilla se dibuja cada monstruo en su posición con su sprite, y desde 22 px también su nombre. Más lejos, cada spawn es un círculo.
- **Pisos:** botones por piso, con la cantidad de monstruos de cada uno.
- **Spawns:** un círculo por spawn, de tamaño según la cantidad de monstruos y de color según la experiencia del más fuerte (verde < 50, amarillo < 300, naranja < 1000, rojo < 3000, violeta 3000+). La ★ marca un respawn de 30 minutos o más (jefes y raros).
- **NPC:** cuadrados blancos.
- **Zonas:** rectángulos opcionales. Salen de los `generated-*.json` con `box`, más una lista fija en el script (ciudad, plaza de portales, sala de entrenamiento, campo del Paso del Norte).
- **Panel lateral:** lista de monstruos con vida, experiencia y cantidad en el piso y en total, más un buscador de monstruos y NPC. Al elegir un monstruo se resaltan sus spawns, se indica en qué pisos están y el botón "Ir al siguiente" salta de uno a otro.
- **Navegación:** rueda para zoom, arrastrar para moverse, doble clic para acercar. Al pasar el mouse se ven la coordenada y el detalle del spawn (monstruos, vida, experiencia, respawn, centro y radio).
- **Rutas:** capa con los caminos desde el templo a los destinos principales (portales, barcos y caminatas). Se elige una ruta en el panel, se dibuja el camino con flechas y paradas (templo, portal, llegada, escaleras, puertas) y se muestran los pasos. El botón "Ir al inicio" lleva al comienzo y "Ver llegada"/"Ver destino" al otro extremo. La URL guarda la ruta (`#r=isla-natural`) para compartirla; la wiki enlaza con ese hash.
- **Enlaces:** la URL guarda el piso, la vista, el monstruo elegido y la ruta (`#z=8&x=420&y=320&k=4&m=Dragon&r=isla-natural`), así que se puede compartir.

## Fuentes

| Dato | Archivo |
|------|---------|
| Terreno | `server/YurOTS/ots/data/world/test.otbm` + `devtools/rme/rme-client-760/Tibia.dat` (colores) |
| Spawns | `server/YurOTS/ots/data/world/test-spawn.xml` |
| NPC | `server/YurOTS/ots/data/world/npc.xml` (ignora los comentados) |
| Vida, experiencia, look | `server/YurOTS/ots/data/monster/monsters.xml` y cada XML |
| Zonas | `server/YurOTS/ots/data/world/generated-*.json` |
| Rutas | `scripts/map/routes.json`, generado por `scripts/map/build-routes.py` |

## Rutas

`scripts/map/build-routes.py` calcula los caminos sobre el mapa (casillas caminables, escaleras, rampas,
agujeros, puertas y teleports) y escribe `scripts/map/routes.json`. `build-monster-map.py` lo lee y lo
mete en `data.json`; si el JSON no existe, el visor funciona igual sin la capa de rutas.

```bash
python3 scripts/map/build-routes.py                     # usa test.otbm del repo
python3 scripts/map/build-routes.py --map OTRO.otbm     # otro mapa
```

Cada ruta tiene `slug`, `name`, `kind` (`portal`, `boat` o `walk`), `steps`, `segments` (puntos por
piso), `jumps` (portal/barco) y `markers` (depot, portal, llegada, escaleras, puertas, destino). Para
agregar una ruta nueva, sumarla a la lista de `build-routes.py` y volver a generarla. La wiki enlaza
cada artículo con `http://192.168.1.17:8077/monstruos.html#r=<slug>`.

### Fotos de ruta para la wiki

`scripts/map/build-route-images.py` dibuja los mismos caminos sobre el **mapa real** (sprites del
cliente), con flechas rojas y paradas, y parte cada ruta en pasos. Las imágenes van a
`web/assets/wiki/routes/<slug>/` y el índice a `web/assets/wiki/routes/manifest.json`.
`scripts/web/apply-wiki-routes.py` inserta las fotos en los artículos entre los marcadores
`RUTA_IMAGENES`.

```bash
python3 scripts/map/build-routes.py
python3 scripts/map/build-route-images.py          # necesita Pillow
python3 scripts/web/apply-wiki-routes.py
scripts/web/build-site.sh
```

Las fotos son del mapa real a 16 px por casilla; el depot es el punto de partida (`127, 57, 6`).

## Actualización automática (sitio local de docs)

En la Mac mini, el sitio local de docs vive en `~/apps/retro76-docs` y se sirve en
`http://127.0.0.1:8765`. El mapa de monstruos y el mapa por pisos (`mapa.html`, generado por
`scripts/map/build-floor-map.py`) se mantienen solos al día con `main`:

| LaunchAgent | Qué hace |
|-------------|----------|
| `com.gonzalo.retro76-docs` | Sirve el sitio (`python3 -m http.server 8765 --bind 127.0.0.1`), siempre arriba. |
| `com.gonzalo.retro76-docs-maps` | Cada 10 minutos (y al iniciar sesión) corre `scripts/docs-site/refresh-maps.sh`. |

`refresh-maps.sh` trae `origin/main` a un worktree propio (`~/proyectos/serverrepo-docs-map`, en
detached HEAD, separado del checkout principal). Si cambió algo de lo que dibujan los mapas (mapa,
spawns, NPC, monstruos, cliente de RME o los scripts de `scripts/map`), regenera los dos mapas
(~2 min). Si no cambió nada, termina sin hacer nada. Registro en `~/apps/retro76-docs/.maps.log`.

```bash
scripts/docs-site/install-agents.sh                     # instala los dos agentes (--remove los quita)
scripts/docs-site/refresh-maps.sh                       # a mano (solo si cambió algo)
FORCE=1 scripts/docs-site/refresh-maps.sh               # regenerar igual
launchctl kickstart gui/$(id -u)/com.gonzalo.retro76-docs-maps   # que lo corra el agente ya
```

Para otro mapa o una rama, correr los scripts a mano a otra carpeta: el sitio muestra siempre `main`.

## Sitio de mapas en la ThinkPad (toda la red)

El sitio de la Mac escucha solo en `127.0.0.1`. En la ThinkPad hay uno que se abre desde cualquier
equipo de la red: **http://192.168.1.17:8077**. Tiene portada (`scripts/docs-site/thinkpad-index.py`),
el mapa interactivo, un cuadro por piso y las vistas de zona de `build-floor-map.py`.

Dibuja lo **deployado**: el commit de `main` de `~/apps/serverrepo`, en un worktree propio
(`~/apps/serverrepo-mapas`), sin los cambios sin commitear de otras sesiones. Así el mapa cambia
cuando cambia el server, no antes.

| Servicio de usuario (systemd) | Qué hace |
|---|---|
| `retro76-mapas.service` | `python3 -m http.server 8077 --bind 0.0.0.0` sobre `~/apps/retro76-mapas` |
| `retro76-mapas-refresh.timer` | Cada 10 min corre `thinkpad-maps.sh`: si cambió el mapa, spawns, NPC, monstruos, el cliente de RME o `scripts/map`, regenera (~2–3 min) |

`thinkpad-maps.sh` arma todo en `~/apps/retro76-mapas.next` y recién al final lo cambia por el sitio:
la web nunca queda a medio generar. El instalador copia los scripts a `~/.local/share/retro76-mapas/`
(el `main` deployado puede no tenerlos todavía).

```bash
scripts/docs-site/install-thinkpad.sh               # instala o reinstala (copia los scripts y arranca)
FORCE=1 ~/.local/share/retro76-mapas/thinkpad-maps.sh   # regenerar ya
journalctl --user -u retro76-mapas-refresh -n 20    # registro
scripts/docs-site/install-thinkpad.sh --remove      # quitar
```

