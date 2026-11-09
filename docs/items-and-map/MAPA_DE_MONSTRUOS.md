# Mapa interactivo de monstruos

Página HTML con todos los pisos de `test.otbm` y cada spawn, NPC y zona encima. Sirve para ver qué hay en cada lugar del mundo, buscar un monstruo y saltar entre sus spawns.

```bash
python3 scripts/map/build-monster-map.py SALIDA/
```

Escribe `SALIDA/monstruos.html` y `SALIDA/monstruos/`, que tiene una imagen por piso (`z*.png`, 1 píxel por casilla, colores del minimapa del `Tibia.dat`) y un `data.json`. Si `SALIDA` es el sitio local de Retro76 (con `site.css` y `menu.js`), la página aparece con el menú común; sin ellos funciona igual. Tarda unos 5 segundos y solo lee el repo.

## Qué muestra

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
