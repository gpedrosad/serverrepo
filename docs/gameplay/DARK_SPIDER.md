# Dark Spider

Araña de caparazón negro carbón, ojos rojo brasa y patas largas articuladas.
El dibujo sigue las proporciones generales de Giant Spider, con perspectiva
oblicua y reflejos gris cálido para que se lea sobre la tierra. Tiene formato
2×2, cuatro direcciones y tres cuadros de movimiento. El looktype `190` y el
cadáver `20663` usan sus mismos IDs de sprite. El cadáver conserva el
contenedor y el decay de `2857`.

![Dark Spider en cuatro direcciones y tres cuadros](img/dark-spider.png)

| Monstruo | Vida | Exp | Velocidad | Melee |
|---|---:|---:|---:|---:|
| Giant Spider | 1.300 | 900 | 270 | 120–300 |
| Dragon Lord | 1.900 | 2.100 | 200 | 62–205 |
| Dark Spider | 3.400 | 3.200 | 355 | 180–410 |

Persigue hasta quedar adyacente y usa los campos venenosos de Giant Spider y
`necro_lifedrain` a los blancos que la rodean. Inmune a poison, invisible y drunk.

Aparece en dos cámaras de [Duskweb Hollow](../items-and-map/DUSKWEB_HOLLOW.md)
(`29,132,8` y `31,143,8`), con acceso desde el sendero de la costa oeste en
`17,136,7`. Se recomienda nivel 65 o más para el tramo final.

```bash
python3.11 scripts/client-rme/add_dark_spider.py --apply \
  --preview docs/gameplay/img/dark-spider.png \
  --corpse devtools/zagan-test/custom-sprites/dead_dark_spider.png
```

Para instalar el cadáver en un cliente sin el ítem 20663:

```bash
python3.11 scripts/client-rme/add_custom_items.py \
  --things devtools/rme/rme-client-760 \
  --otb server/YurOTS/ots/data/items/items-zagan-test.otb \
  --otb server/YurOTS/ots/data/items/items.otb --only 20663
```
