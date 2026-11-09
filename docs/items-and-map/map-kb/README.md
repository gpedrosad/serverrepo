# Map KB: qué es cada pieza del mapa y dónde va

Base de conocimiento estructurada de las piezas de `test.otbm`, pensada para que una IA (o un script)
genere y revise mapas sin adivinar. Todo es JSON con esquema fijo; nada de texto suelto salvo los
campos `description_es` y `usage_rule_es` dentro de cada etiqueta.

## Cómo se regenera

```bash
cd scripts/map/kb
python3 extract_facts.py                      # hechos deterministas (1 s)
OPENROUTER_KEY_FILE=~/.openrouter_key \
  python3 label_deepseek.py --only-used       # etiquetas DeepSeek de piezas usadas (reanudable)
OPENROUTER_KEY_FILE=~/.openrouter_key \
  python3 label_deepseek.py --only-unused --effort low
python3 build_kb.py                           # une, corrige, agrupa y revisa el mapa (1 s)
```

`label_deepseek.py` guarda una etiqueta por pieza en `.cache/labels/<id>.json` y salta las que ya
existen; `--force` las rehace, `--ids 406,407` limita a piezas concretas. La key nunca va en el repo.

## Archivos

| Archivo | Origen | Para qué |
|---|---|---|
| `facts.json` | código | Flags OTB/.dat, capa, usos, pisos, posiciones de ejemplo y vecinos medidos en el mapa |
| `adjacency.json` | código | Pares `(a, dir, b, count)`: suelo/borde `b` aparece al lado `dir` de `a` |
| `zones.json` | código | Zonas `generated-*.json`: cajas, puntos clave y si existen en el mapa |
| `pieces.json` | código + DeepSeek | Pieza final: hechos clave + `label` + `label_fixes` (correcciones por reglas duras) |
| `review.json` | código | Piezas cuya etiqueta contradijo los hechos, con baja confianza o sprite raro |
| `border_sets.json` | código | Bordes agrupados por `suelo_debajo->terreno_borde` y lado; `missing_edges` |
| `wall_sets.json` | código | Paredes por material y parte (horizontal, vertical, esquina, poste) |
| `map_lint.json` | código | Problemas del mapa con coordenada y zona |
| `overview_z*.png` + `overview.json` | código | Mapa por piso, 2 px por casilla, colores de minimapa |

## Esquemas

### `facts.json` → `items[id]`
- `layer`: `ground` | `border` | `bottom` | `common` | `top` (orden de dibujo del cliente).
- `dat_flags`: flags del `.dat` 7.6 (`ground`, `ground_border`, `on_bottom`, `unpassable`, `block_missile`, ...).
- `map_uses`, `floors {z: n}`, `sample_positions [[x,y,z]]`.
- `ground_under`, `same_tile_items`: top 5 `{id, name, share}`.
- `same_item_neighbor_share {dir: 0..1}`: cuánto se repite la misma pieza en cada dirección (paredes: dice si corre N-S o E-O).
- `different_ground_neighbor_share {dir: 0..1}`: cuánto cambia el suelo en cada dirección (bordes: dice el lado).
- `neighbor_ground {dir: [{id, share}]}`: suelos vecinos; `-1` = casilla vacía, `0` = casilla sin suelo.

### `pieces.json` → `items[id].label`
| Campo | Valores |
|---|---|
| `category` | ground, ground_border, wall, wall_decoration, door, window, floor_change, nature_tree, nature_bush_plant, nature_rock, water_feature, furniture, container, light_source, decoration, structure, teleport_magic, item, other |
| `terrain` | grass, dirt, sand, stone, cobblestone, marble, wood, water, swamp, snow, ice, lava, cave, mud, gravel, metal, carpet, void, mixed, none |
| `border` | `{is_border, under_terrain, over_terrain, edge}`; `edge` = lado donde está el otro terreno: n, s, e, w, `*_outer`, `*_inner`, full, none, unknown |
| `wall` | `{is_wall, part, material}`; `part` = horizontal, vertical, corner_nw, corner_se, pole, end, none, unknown |
| `settings` | temple, city, house, forest, jungle, desert, snow, swamp, cave, dungeon, beach, volcanic, underwater, arena, any |
| `walkable_expected` | bool (forzado por el flag `unpassable`) |
| `pairs_with_ids` / `avoid_with_ids` | ids que salen de los vecinos medidos, máx 6 |
| `description_es` / `usage_rule_es` | texto corto en español |
| `sprite_matches_name` | false = el dibujo no corresponde al nombre (posible id Zagan reutilizado) |
| `confidence` | 0..1 |

Reglas duras que pisan a DeepSeek (`label_fixes` registra cada una): capa `ground` ⇒ `category=ground`;
sin flag `ground_border` ⇒ no es borde; `walkable_expected` = no `unpassable`; categoría `wall` ⇔ `wall.is_wall`.

### `map_lint.json` → `issues[]`
`{rule, x, y, z, zone, ids, detail}`:
- `R1_sin_suelo`: casilla pisable sin suelo ni nada que bloquee.
- `R2_dos_suelos`: más de un suelo en la misma casilla.
- `R3_borde_huerfano`: borde en una casilla cuyos 8 vecinos tienen el mismo suelo.
- `R4_transicion_sin_borde`: dos terrenos naturales distintos (pasto/tierra/arena/...) se tocan sin ningún borde.

## Límites conocidos
- Sprites del cliente 7.6 base: los ids reutilizados por Zagan se ven con el dibujo vanilla
  (`sprite_matches_name=false` suele marcarlos).
- Las etiquetas son de un modelo con visión (DeepSeek v4 flash vision): úsalas como guía y
  revisa `review.json`; los hechos de `facts.json` son exactos.
