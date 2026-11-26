# Claro de los Lobos

Isla de pasto aislada al sureste de la ciudad, en un vacío del mapa que no tenía tiles, casas, spawns ni NPC. Hunt chico de nivel 8–25: lobos en el sendero, War Wolf y Bear en el claro del fondo.

Generador: `scripts/map/generate-wolf-grove.py` (re-ejecutable). Manifiesto: `server/YurOTS/ots/data/world/generated-wolf-grove.json`.

![Vista del claro y el sendero](img/claro-de-los-lobos.png)

## Cómo es

| Qué | Dónde |
|-----|-------|
| Caja | `x 187–261, y 265–339, z7` (agua + tierra). La tierra solo crece en `196–252, 274–330` |
| Entrada | `206,286,7` (esquina noroeste del sendero) |
| Sendero | tierra de 2 de ancho en zigzag: `206,286` → `228,286` → `228,314` → `240,314` |
| Claro | `x 232–244, y 308–318`, fogata en `240,314,7` |
| Orilla | costa de pasto `4644–4655` sobre agua `4608`; lo que no es sendero es bosque que bloquea |
| Cartel | `206,285,7`, bloque `WOLF_GROVE_SIGNS` de `readables.xml` |

**251 casillas caminables**, 1083 de tierra, 4542 de agua. No hay agujeros: no hace falta `style-hole-entrances`. No toca ciudad, templos, portales ni casas.

La isla está rodeada de agua; se llega en bote (o con un GM). No tiene portal en la plaza del templo.

## Monstruos

7 spawns (bloque `WOLF_GROVE_SPAWNS` de `test-spawn.xml`):

| Zona | Monstruos | Spawntime |
|------|-----------|-----------|
| Sendero | 5 Wolf | 90–110 s |
| Claro | 2 War Wolf + 2 Bear | 140 s |

## Cómo regenerar

Desde la raíz del repo:

```bash
python3.11 scripts/map/generate-wolf-grove.py --dry-run --preview /tmp/claro-lobos.png
python3.11 scripts/map/generate-wolf-grove.py
python3 scripts/map/check-map-load.py
python3 scripts/scan-map-depots.py server/YurOTS/ots/data/world/test.otbm
python3 scripts/sync-houses-with-map.py --dry-run
```
