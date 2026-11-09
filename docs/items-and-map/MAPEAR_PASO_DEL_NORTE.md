# Paso del Norte

Salida por la muralla norte de la ciudad hacia una región nueva: bosque de pinos, Tundra Helada, Cuevas del Dragón (z8) y Nido Negro (z9). Lo genera `scripts/map/generate-north-pass.py` (rama `north-pass`, nov 2026).

Relacionado:

- [docs/CAMBIAR-MAPA.md](../CAMBIAR-MAPA.md): flujo general del mapa y deploy.
- [MAPEAR_CON_CODIGO.md](MAPEAR_CON_CODIGO.md): cómo se escribe OTBM por código.
- [MAPA_DE_MONSTRUOS.md](MAPA_DE_MONSTRUOS.md): mapa interactivo con todos los spawns.
- [../gameplay/BLACK_DRAGON.md](../gameplay/BLACK_DRAGON.md): el monstruo del Nido Negro.

![Puerta norte, camino y portal](img/paso-del-norte/ciudad_puerta.png)

---

## Por qué un portal y no un camino largo

La muralla norte está en y=23–25 y el mapa empieza en y≈2. Al norte solo hay unas 20 casillas de pasto, y a la izquierda está la sala de entrenamiento (Trainer Monks, x 134–154). El camino sale por una puerta nueva, cruza el campo y termina en un portal entre rocas. La región sigue en la zona vacía del mapa (x 370–469, y 236–467): se llega por su lado sur y se avanza hacia el norte, así que se siente continuo.

Correr el mapa entero hacia el sur se descartó: habría cambiado las coordenadas de casas, spawns, NPC, portales, scripts y personajes guardados en el VPS.

## Coordenadas clave

| Qué | Posición |
|-----|----------|
| Puerta en la muralla | `184-185, 23-25, 7` (muro 1050 / montaña 919 / muro 1050 → piedra 431) |
| Pasillo interior | `x 185, y 26-33` y `y 33, x 182-185` (piedra 431), empalma con el camino de tierra al templo |
| Camino del campo | `184-185, 4-22, 7`, tierra 103 con bordes de pasto 110–121 |
| Portal de la ciudad | `184-185, 3, 7` → llegada `420, 452, 7` |
| Vuelta (portales de la región y del Nido) | → `184, 6, 7` |
| Portales de la región | `420-421, 456, 7` |
| Escalera a las cuevas | `420, 258, 7` (432) / `420, 258, 8` (1385, sube al norte) |
| Bajada al Nido | `437, 376, 8` (432) / `437, 376, 9` (1385) |
| Portal del Nido | `416, 397, 9` |
| Manifiesto | `server/YurOTS/ots/data/world/generated-north-pass.json` |

## Zonas y spawns (seed 31)

| Zona | Ambientación | Spawns |
|------|--------------|--------|
| Bosque de pinos | Camino serpenteante, arboledas (pino 4009, firetree 2700, beech 2707, sycamore 2701, poplar 2708), arbustos, flores, hongos y troncos; campamento con fogata 1423 y cartel | Wolf ×21, Bear ×5, War Wolf ×8, Deer ×8, Rabbit ×8 |
| Línea de nieve | Bordes de nieve 4737–4748 sobre el pasto | — |
| Tundra Helada | Nieve 670, pino nevado 2698, árbol muerto 2697/2709/2717/2720, lago de hielo 671 con estalagmitas 4995, faroles 3744 | Winter Wolf ×27, Polar Bear ×5, Frost Troll ×18, Yeti ×1 (1800 s) |
| Pie de la montaña | Piedras agrupadas 1309/1285, huesos y calaveras de dragón | (Winter Wolf) |
| Cuevas del Dragón (z8) | ~7100 casillas, paredes 356–367 sobre roca 101, piedras y huesos | Dragon ×50, Dragon Lord ×8 (en la mitad lejana) |
| Nido Negro (z9) | ~1100 casillas, más barro (355), muchos huesos | Dragon Lord ×6, Demodras ×1 (7200 s); Black Dragon ×3 solo con `--with-black-dragon` |

Bordes de la región: una franja de 8 casillas de bosque o pinos nevados, donde cada casilla lleva un bloqueo 1×1 y, cada dos, un árbol grande encima. Tapa el vacío del borde de la caja.

![Minimapa: z7, z8 y z9](img/paso-del-norte/minimapa.png)

| | |
|---|---|
| ![Llegada](img/paso-del-norte/llegada2.png) | ![Campamento](img/paso-del-norte/campamento.png) |
| ![Línea de nieve](img/paso-del-norte/linea_nieve.png) | ![Lago congelado](img/paso-del-norte/lago.png) |
| ![Escalera a las cuevas](img/paso-del-norte/escalera.png) | ![Nido Negro](img/paso-del-norte/nido.png) |

## Uso

```bash
python3 scripts/map/generate-north-pass.py --dry-run --preview /tmp/paso.png   # valida y dibuja, sin escribir
python3 scripts/map/generate-north-pass.py                                      # escribe mapa, spawns, carteles, manifiesto
python3 scripts/map/generate-north-pass.py --with-black-dragon                  # + Black Dragon (cliente actualizado)
python3 scripts/map/generate-north-pass.py --seed 7                             # otra variante del terreno
```

Qué escribe:

- `server/YurOTS/ots/data/world/test.otbm`. Backup la primera vez: `test.otbm.bak-northpass`.
- `server/YurOTS/ots/data/world/test-spawn.xml`, bloque `NORTH_PASS_SPAWNS`.
- `server/YurOTS/ots/data/readables.xml`, bloque `NORTH_PASS_SIGNS`, con 5 carteles.
- `server/YurOTS/ots/data/world/generated-north-pass.json`.

**Re-ejecutable:** borra lo que haya en la caja de la región (z7–z9), rehace las casillas de la ciudad que toca y reemplaza los dos bloques. **Si `test.otbm` cambió en `main`, no hay que mergear el binario:** basta con correr el script sobre el mapa nuevo.

## Validaciones (antes de escribir)

- Cada casilla junto a la nieve tiene la pieza de borde exacta. Cada casilla junto al camino de tierra tiene su pasto con borde.
- Cada roca de cueva que toca piso tiene una única pieza de pared válida.
- Desde la llegada se alcanza caminando la escalera, con libre la casilla al norte, que es donde deja 1385 al subir.
- En z8 se alcanza la bajada al Nido, y en z9 el portal.
- Las casillas de la ciudad existen, no son casas y el campo es pasto común (no de costa).

## Cómo funciona

- **Terreno:** ruido con semilla (misma clase `Noise` que `generate-natural-island.py`). Usa `pieces_for` / `fix_until_valid` para los bordes, pero revisando solo el contorno de cada zona, porque recorrer toda la caja en cada vuelta era lento.
- **Cuevas:** autómata celular sobre una **grilla de bloques 2×2** que después se amplía. Todo pasillo y pared mide 2 casillas o más y no hay contactos solo en diagonal, así que cada pared tiene una única pieza válida. El ajuste casilla a casilla de la isla oscilaba sin converger en cuevas de este tamaño.
- **Decoración que bloquea** (piedras, huesos grandes): se prueba una por una que no corte el paso.
- **Spawns:** centros separados al menos 7–9 casillas, fuera del camino, la llegada, el campamento y las escaleras. Grupos de hasta 3 monstruos en radio 3.

## Pendiente

- Probarlo en un servidor. En la ThinkPad falta acceso a Docker: `sudo usermod -aG docker gonzalo`.
- En el juego, mirar la esquina de la muralla junto a la puerta (deja una sombra en diagonal) y la densidad de las Cuevas del Dragón (58 monstruos).
- Cuando el updater reparta el cliente con el look 230: `--with-black-dragon`.
- Deploy al VPS solo con el OK de Gonzalo.
