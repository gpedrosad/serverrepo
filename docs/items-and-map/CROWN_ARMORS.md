# Crown Armors de loot (Imperial y Sapphire)

Dos versiones de la Crown Armor agregadas en nov 2026. Son loot raro de monstruos fuertes y cada una tiene una
ventaja propia.

![Crown armor, Imperial y Sapphire](img/crown-armors.png)

| Server id | Nombre | Client id (sacrificado) | Armadura | Ventaja |
|---:|---|---|---:|---|
| 20161 | imperial crown armor | 3570 (ball gown) | 14 | −10% de daño elemental: energía, fuego, veneno, robo de vida y burst |
| 20162 | sapphire crown armor | 3564 (red tunic) | 14 | −10% de daño físico: melee, distancia y hechizos físicos |

- **Prototipo:** 2487 crown armor (arm 13). El peso y el slot salen de ella.
- **Sprite:** la crown armor del cliente, que en este servidor es roja con oro (client 3381), recoloreada con
  `scripts/client-rme/recolor_item.py`. Cambia el tono de las placas y respeta las sombras; el oro queda igual.

  ```bash
  python3.11 scripts/client-rme/recolor_item.py --client-id 3381 --hue 258 --sat 0.85 --val 0.78 --gamma 1.05 \
      --out devtools/zagan-test/custom-sprites/imperial_crown_armor.png
  python3.11 scripts/client-rme/recolor_item.py --client-id 3381 --hue 222 --sat 0.95 --val 0.95 \
      --out devtools/zagan-test/custom-sprites/sapphire_crown_armor.png
  ```

  Ojo: se generan desde el `Tibia.dat`/`.spr` actual. Si la crown armor cambia de dibujo, el resultado también.
- **Alta:** entradas en `NEW_ITEMS` de `scripts/client-rme/add_custom_items.py`, que ahora acepta `armor=` (bloque
  `ITEM_ATTR_ARMOR2` del `.otb`) además de `attack=`/`defence=`. Ver
  [IMPORTAR_ITEM_DE_OTRA_VERSION.md](IMPORTAR_ITEM_DE_OTRA_VERSION.md).

## Ventaja (C++)

- `GameState::applyAmulets()` en `game.cpp`: si la armadura puesta es una de las dos y el tipo de ataque
  coincide, multiplica el daño por `(100 − CROWN_ARMOR_REDUCTION_PERCENT) / 100`. El porcentaje es 10 y está en
  `const76.h`.
- Se aplica después de amuletos y anillos, de forma multiplicativa. No gasta cargas.
- Solo se aplica a daño positivo, así que las curas no se tocan. El manadrain no se reduce.
- Al mirarlas se ve la ventaja (`item.cpp`, descripción completa).
- Ids en `const76.h`: `ITEM_IMPERIAL_CROWN_ARMOR` y `ITEM_SAPPHIRE_CROWN_ARMOR`. Hace falta el binario compilado.

## Loot

`chance` sobre 100000. Desde el 12 nov 2026 `lootmul = 1`. No están en `isRareEquipmentLootItem`, así que no
se dividen a la mitad.

| Monstruo | Imperial | Sapphire |
|---|---:|---:|
| demon | 150 | |
| angry demon | 250 | |
| furious demon | 350 | |
| enraged demon | 500 | |
| furious warlock | 250 | |
| enraged warlock | 400 | |
| orshabaal | 800 | |
| imperial hero ([Castillo Imperial](../gameplay/IMPERIAL_CASTLE.md)) | 800 | |
| the fallen emperor (jefe del castillo) | 6000 | |
| angry behemoth | | 200 |
| furious behemoth | | 300 |
| enraged behemoth | | 450 |
| demodras | | 600 |
| ashen lord | 800 | 800 |

Wiki para jugadores: `web/site/src/wiki/crown-armors.md`.
