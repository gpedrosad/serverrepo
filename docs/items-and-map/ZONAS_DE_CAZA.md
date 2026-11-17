# Zonas de caza: cómo se arma el lugar y cuántos monstruos salen (nov 2026)

Receta que se usa en el [Valle de las Bestias](MAPEAR_VALLE_DE_LAS_BESTIAS.md) desde la v4 (nov 2026), y que
sirve para cualquier zona generada nueva. Nació de una queja: "salen todos muy juntos". Las cuevas eran
manchas redondas con grupos de 3–4 monstruos cada 6 casillas (una cueva de 340 casillas tenía 17 grupos
alrededor de la escalera). Ahora:

1. **El lugar es un pasillo largo y angosto**, no una mancha.
2. **Los monstruos salen sueltos al entrar y de a 2 al fondo**, con 10–13 casillas entre grupo y grupo.
3. **La cantidad la decide el espacio**: no se fija un número de spawns. Cada etapa pone todos los que
   entran respetando su separación.

Código de referencia: `scripts/map/generate-beast-valley.py` (constantes `*_PATH*`, `CAVE_STAGES`,
`DEEP_STAGES`, `ABYSS_STAGES`, `SURFACE_STAGES`; funciones `ribbon`, `rooms_along`, `carve_named`,
`place_stages`, `slices_by`). Las cuevas se cavan con `carve_cave` de `generate-north-pass.py` (bloques de
2x2, ver [PIEZAS_DE_MAPA.md#cuevas](PIEZAS_DE_MAPA.md#cuevas)).

## 1. El lugar: un recorrido en zigzag

Una cueva se describe con un **recorrido**: una lista de puntos unidos por tramos rectos, horizontales o
verticales.

```python
CAT_PATH8 = [(50, 34), (84, 34), (84, 20), (16, 20), (16, 48), (40, 48)]
```

- `ribbon()` cava alrededor del recorrido un pasillo de **4 a 6 de ancho** (varía con ruido) que zigzaguea
  ±1 casilla lejos de las esquinas. `carve_cave` solo puede cavar dentro de una franja de 5 casillas a
  cada lado (`RIBBON_BAND`), así que el autómata de cuevas le da bordes naturales sin ensancharlo.
- **Salas**: ensanches de radio 3. `rooms_along(path)` pone una a mitad de cada tramo de 20 casillas o
  más y otra al final. Las salas son donde mejor entran los grupos de a 2.
- **El final del recorrido es donde va la bajada** al piso de abajo: tiene que haber 3x5 de piso (la sala
  del final) y tiene que caer dentro de la caja del piso de abajo (`mouth_zone`). El piso de abajo empieza
  justo debajo (su `mouth` lo pone `build_caves()`), así que su recorrido arranca cerca de ese punto.

### Reglas de medidas

| Regla | Valor | Qué pasa si no |
|-------|-------|----------------|
| Tramos paralelos de **la misma** cueva | **14 casillas** o más entre ejes | Las franjas se tocan, la cueva hace un atajo y se saltea la progresión |
| Dos cuevas del mismo piso | **3 casillas** de roca como mínimo (`CAVE_SEPARATION`) | Se cavan con esa distancia; si sus recorridos están más cerca, el script falla |
| Recorrido lejos del borde de la caja | 4 casillas dentro de la zona permitida (caja menos 6) | El borde de la cueva queda fuera de la caja o se ve el vacío |
| Tamaño de un piso | ~1.000–1.250 casillas caminables (~170–200 casillas de recorrido) | — |
| Abismo / último piso | ~1.700 casillas | — |

Para dibujar un recorrido, lo más fácil es pensar **filas** (o columnas) separadas por 14 y unirlas por
los extremos: `y 20 / 34 / 48`, `x 60 / 85`. Mirar el preview antes de escribir:

```bash
python3 scripts/map/generate-beast-valley.py --dry-run --preview /tmp/valle.png
```

## 2. Los monstruos: etapas por distancia

Cada zona tiene una lista de **etapas**, de la más fácil a la más difícil:

```python
# (nombres, monstruos por spawn, spawntime en s, separación mínima entre centros)
"dragon": [(("Dragon Hatchling",), 1, 140, 13),
           (("Dragon Hatchling", "Dragon"), 1, 160, 11),
           (("Dragon", "Wyrm"), 2, 190, 12),
           (("Wyrm", "Dragon Lord", "Black Dragon"), 2, 230, 11)],
```

Cómo se reparten (`slices_by` + `place_stages`):

1. Se mide la distancia **caminando** desde la entrada (escalera o llegada) hasta cada casilla.
2. La zona se parte en tantas **franjas** como etapas, de igual tamaño, por esa distancia: la etapa 1
   ocupa el primer tramo del pasillo, la última el fondo.
3. En su franja, cada etapa pone un spawn en cada lugar que quede a la separación pedida (distancia
   Manhattan entre centros) de **todos** los centros ya puestos, también los de etapas anteriores.
   El lugar necesita `por spawn + 3` casillas libres a 2 de distancia.
4. Los nombres se reparten en ronda: con `("Dragon", "Wyrm")` y 2 por spawn sale un Dragon y un Wyrm.
5. Nada a menos de **6 casillas** de escaleras, portales y llegada (`STAIR_CLEAR`).

### Números que se usan (valle, nov 2026)

| Dónde | Por spawn | Separación | Resultado |
|-------|-----------|------------|-----------|
| Cuevas, primera mitad de las etapas | 1 | 11–13 | Monstruos sueltos |
| Cuevas, segunda mitad | 2 | 10–12 | De a 2 |
| Pisos de fondo (z9, z10) | 1 → 2 (5–6 etapas) | 10–13 | Igual, con más etapas y monstruos más fuertes |
| Superficie (claros de ~150–300 casillas) | 1, 1, 2 | 6 | Un claro abierto se ve entero: con más separación quedaban 2–3 monstruos |

**Densidad que da**: en las cuevas, **un monstruo cada 33–50 casillas**; en la superficie, uno cada 9–15
(claros chicos). Antes eran uno cada 6–13. El script imprime la tabla al correr y la guarda en el
manifiesto (`density`):

```
  z8 catacumbs   1067 casillas   16 spawns   25 monstruos  1 cada 43 casillas
  z9 quara       1252 casillas   24 spawns   36 monstruos  1 cada 35 casillas
```

### Para ajustar

| Quiero | Cambiar |
|--------|---------|
| Menos monstruos en una zona | Subir la separación (4.º campo) de sus etapas |
| Más monstruos | Bajarla (no menos de 10 en cuevas: vuelven a verse juntos) |
| Que el fondo sea más duro | Pasar la última etapa a 2 por spawn o poner monstruos más fuertes |
| Que respawneen más lento | Subir el spawntime (3.er campo) |
| Más tramo fácil al principio | Agregar una etapa de 1 por spawn al comienzo (las franjas se achican) |

`spawntime` va de ~100 s (lo fácil) a ~300 s (Demon/Fury). Los jefes (Root Colossus) van aparte, con su
propia función y su sala de 3x3.

## 3. Cada zona con su propio sorteo

Cada cueva y piso sortea sus spawns con su propio generador (`cave_rng(nombre, piso)`). Cambiar una zona
no mueve los spawns de las demás. Lo mismo al cavar: si la franja de una cueva no toca a las otras del
piso, su forma no cambia aunque se agregue otra cueva.

## Cómo hacer una cueva nueva, paso a paso

Ejemplo: agregar una cueva de un piso en z8 del valle. Para un generador nuevo, copiar las funciones
`ribbon`, `rooms_along`, `carve_named`, `mouth_zone`, `stair_down`, `place_stages` y `slices_by` de
`generate-beast-valley.py` (y `carve_cave`, `cave_tiles`, `decorate_cave` de `generate-north-pass.py`).

1. **Elegir el lugar en papel.** Coordenadas locales de la caja (x 0–99, y 0–146 en el valle). Marcar lo que
   ya ocupa ese piso (las otras cuevas y su franja de 5) y dejar 4 casillas de margen dentro de la caja. Lo
   caminable no puede quedar a menos de media pantalla (7×5) del borde de la caja.
2. **La boca.** Es la casilla de la escalera: en el piso de arriba va la bajada `432` y en la cueva, en la
   misma x, y, la escalera de mano `1385` (`STAIRS_UP`). Se llega al sur de la `1385`, así que el recorrido
   arranca hacia el sur o de costado, nunca hacia el norte pegado a la boca.
3. **El recorrido.** Filas (o columnas) a 14 casillas unidas por los extremos. Con 170–200 casillas de
   recorrido sale un piso de ~1.000 casillas. Si tiene piso de abajo, el último punto tiene que caer dentro de
   `mouth_zone` de la caja de abajo, y el recorrido de abajo arranca ahí.
4. **El spec.** Un diccionario como los de `CAVES`:

   ```python
   {"name": "nueva", "box": (x, y, ancho, alto), "mouth": (bx, by), "mud": 0.3, "alt": 0.3,
    "bones": 0.08, "min": 700, "path": NUEVA_PATH, "rooms": rooms_along(NUEVA_PATH),
    "sign": "NOMBRE\nQué hay adentro."}
   ```

   `box` es la caja donde se puede cavar (se le restan 6 de cada lado). `min` es el piso mínimo: poner ~70 %
   de lo que da el preview. `mud`/`alt` son la paleta de piso (barro, piso alterno) y `bones` cuánta
   decoración pone `decorate_cave`.
5. **Las etapas.** En `CAVE_STAGES` (o la tabla del piso): de 3 a 6 etapas, empezando con 1 por spawn y
   pasando a 2 a la mitad, separación 10–13 y spawntime de 100 s (fácil) a 300 s (lo más duro).
6. **Decoración.** `place_props` pone props del tema en los bordes sin cortar el paso (`CAVE_PROPS`). Solo
   piezas de una casilla que se vean enteras (ver [PIEZAS_DE_MAPA.md#cuevas](PIEZAS_DE_MAPA.md#cuevas)):
   nada de cabezas ni garras del esqueleto grande de dragón.
7. **Mirar y medir.** `--dry-run --preview /tmp/x.png`: la forma tiene que verse como un pasillo sin atajos
   entre filas, y la tabla de densidad tiene que dar 33–50 casillas por monstruo. Si falla algo, el script
   dice qué y no escribe.
8. **Techo.** Si el piso de arriba está vacío encima de la cueva, poner roca ahí (si no, desde la cueva se
   ven los pisos de arriba). Comprobar con `scripts/map/check-upper-view.py`
   ([PIEZAS_DE_MAPA.md#techo](PIEZAS_DE_MAPA.md#techo)).
9. **Escribir y probar.** Correr sin `--dry-run`, `check-map-load.py` (0 errores) y, antes de deployar, bajar
   y subir por cada escalera y abrir el depot del templo in-game.

### Errores que ya pasaron

| Qué pasó | Por qué | Cómo se evita |
|---|---|---|
| Cueva de quaras como un pasillo recto de 4 de ancho con la bajada en una esquina | Sin variar el ancho y sin sala al final | `ribbon()` varía ancho y zigzag; sala al final del recorrido (3x5 de piso) |
| Cambiar una cueva cambiaba los spawns de todas | Un solo sorteo para todo el valle | `cave_rng(nombre, piso)` por cueva |
| Todos los monstruos juntos al lado de la escalera | Grupos de 3–4 cada 6 casillas en una mancha redonda | Pasillo + etapas con separación 10–13 |
| Bajada sobre roca, no se podía bajar al fondo | Cada piso tenía una boca fija | La bajada se elige en `mouth_zone` y el piso de abajo empieza ahí |
| Cabezas y garras de dragón cortadas en el suelo | Piezas sueltas del esqueleto grande | Huesos enteros (`CUT_DRAGON_PIECES` en el valle) |

## Checklist para una zona nueva

1. Recorrido con filas a 14, dentro de la caja, terminando en una sala dentro de la caja del piso de abajo.
2. Etapas: empezar con 1 por spawn, pasar a 2 a la mitad, separación 10–13.
3. `--dry-run --preview`: mirar la forma y la tabla de densidad (33–50 casillas por monstruo en cueva).
4. Escribir, `temple-portals.py` si hace falta, `check-map-load.py` y probar escaleras y depot in-game antes
   de deployar (`docs/gameplay/DEPOTS.md`).
