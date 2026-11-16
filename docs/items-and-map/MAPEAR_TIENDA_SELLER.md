# Tienda del Seller — recorte del fondo sur

La tienda del NPC **Seller** (`145,50,7`) está a la derecha del depot del templo. Se achicó
recortando las **2 filas del fondo sur** en todos los pisos: pasa de `y46–56` a `y46–54`.
El ancho (`x141–147`) no cambia.

Script: `scripts/map/shrink-seller-shop.py` (dry-run por defecto, `--replace` para escribir).

![Antes y después: z7, z6, z5 y z4 (izquierda antes, derecha después)](img/tienda-seller/antes-despues.png)

## Qué se recortó

| Piso | Antes | Después |
|------|-------|---------|
| z7 | salón de piedra `x142–146, y47–55`, abierto al sur | salón `y47–53`; `y54–55` pasa a pasto `4756` |
| z6 | hall de displays `y47–55` + muro sur `y56` | hall `y47–53` + muro sur en `y54`; `y55–56` queda vacío |
| z5 | cuarto de armas `y53–55` + muro sur `y56` | cuarto `y53` + muro sur en `y54`; `y55–56` queda vacío |
| z4 | techo plano `y53–56` | techo `y53–54`; `y55–56` se saca |

El muro sur que estaba en `y56` se movió a `y54` con las mismas piezas:
`1043` (SO), `1045/1263` (paños y ventanas) y `1042` (SE). Las esquinas llevan el ground
del piso (piedra `431` en z6, madera `405` en z5), igual que el muro original.

## Displays reubicados

Los 11 raros y 10 small sapphires que estaban en `z6, y54–55` se movieron a la franja oeste
`x142–143, y48–53`, dejando libre `x142,y51` para leer el blackboard de `141,51,6`:

| Posición | Item |
|----------|------|
| `142,48,6` | crown armor + sapphire |
| `142,49,6` | blue robe + sapphire |
| `142,50,6` | stormcaller maul + sapphire |
| `142,52,6` | bonepriest reaver (sin sapphire: lo compartía con stormcaller) |
| `142,53,6` | dragon shield + sapphire (sobre mesa 1626) |
| `143,48,6` | basalt greaves + sapphire |
| `143,49,6` | venomqueen fang + sapphire |
| `143,50,6` | ironhide crusher + sapphire |
| `143,51,6` | sword of silence + sapphire |
| `143,52,6` | wayfarer boots + sapphire |
| `143,53,6` | morlen crest + sapphire (sobre mesa 1623) |

Las 5 armas del cuarto de z5 se pusieron sobre las mesas de `y53`:

| Posición | Mesa | Arma |
|----------|------|------|
| `142,53,5` | 1626 | spear |
| `143,53,5` | 1623 | arrow |
| `144,53,5` | 1623 | bolt |
| `145,53,5` | 1623 | crossbow |
| `146,53,5` | 1627 | bow |

## Perac (NPC)

Perac estaba en **`144,54,5`**, justo en la fila que se recorta. Se movió a **`144,52,5`**
(terraza, detrás de las mesas de `y53`, mirando al sur). Sin este cambio el servidor no
podría colocarlo al arrancar (`Could not place Perac!`), igual que pasó con el Huntmaster
al borrar la torre del depot.

## Tienda de Mad (z6), ordenada (15 nov 2026)

El piso de displays de z6 es la tienda de **Mad** (`145,51,6`). Tenía un small sapphire debajo de cada
raro y 9 ítems sueltos en el piso, varios en la columna de Mad. Script: `scripts/map/arrange-mad-shop.py`
(dry-run por defecto, `--replace` para escribir; idempotente).

![Antes y después de la tienda de Mad (z6)](img/tienda-seller/mad-antes-despues.png)

- Fuera los **24 small sapphires** (2146); no queda ninguno en el edificio.
- Los **25 ítems** quedan sobre mesas o mostradores, ninguno en el piso ni fuera del salón
  (`x142–146, y47–53`). Se agregaron 9 mesitas `1619` en `x142` (49, 50, 52) y `x145` (todo menos 51).
- Agrupados: armadura en la mesa larga `x144` (de la cabeza a los pies), mazas/reaver/runa/reliquia en
  las mesitas `x145`, espadas y hachas en el mostrador `x146`, escudos y morlen crest al oeste.
- Libres a propósito: `142,48` (llega la escalera de mano de `142,47,7`), el pasillo `x143, y48–52` y
  `142,51` (para leer el pizarrón). Mad queda rodeado de mesas en `145,51` y se lo atiende desde el
  pasillo (`x143`, a 2 casillas; los NPC atienden a menos de 4).

## Qué NO se tocó

- Las casas **Small Street** de `x143–144` y `x146`, `y43–45` (z7, z6 y z5).
- El NPC Seller en `145,50,7` y su tile PZ.
- Las escaleras/trampillas de acceso: `141,44,7`, `141,44,6`, `142,47,6` y `143,47,5`.
- El mostrador este `x146`, las mesas centrales `x144` y el blackboard `141,51,6`.
- El depot y el resto del mapa.

## Verificar / regenerar

```bash
python3 scripts/map/shrink-seller-shop.py            # dry-run
python3 scripts/map/shrink-seller-shop.py --replace  # escribe
python3 scripts/map/check-map-load.py
python3 scripts/map/sync-houses-with-map.py --dry-run
python3 scripts/map/validate-tele-dest.py server/YurOTS/ots/data/world/test.otbm
```

El script hace backup de `test.otbm` y `npc.xml` en
`/private/var/folders/.../opencode/shrink-seller-<fecha>/` y es idempotente: si la tienda
ya está achicada y Perac ya está movido, no vuelve a tocar nada. Si encuentra el estado a
medias, aborta.
