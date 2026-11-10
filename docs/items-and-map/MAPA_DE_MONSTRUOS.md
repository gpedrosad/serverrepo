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
- **Enlaces:** la URL guarda el piso, la vista y el monstruo elegido (`#z=8&x=420&y=320&k=4&m=Dragon`), así que se puede compartir.

## Fuentes

| Dato | Archivo |
|------|---------|
| Terreno | `server/YurOTS/ots/data/world/test.otbm` + `devtools/rme/rme-client-760/Tibia.dat` (colores) |
| Spawns | `server/YurOTS/ots/data/world/test-spawn.xml` |
| NPC | `server/YurOTS/ots/data/world/npc.xml` (ignora los comentados) |
| Vida, experiencia, look | `server/YurOTS/ots/data/monster/monsters.xml` y cada XML |
| Zonas | `server/YurOTS/ots/data/world/generated-*.json` |

Volver a correrlo después de cambiar el mapa o los spawns.
