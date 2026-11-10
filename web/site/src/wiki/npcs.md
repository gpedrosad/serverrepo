---
titulo: Comprar y vender con NPCs
categoria: NPCs y economía
resumen: Cómo comprar y vender con NPCs, pagar con el banco y dónde está cada NPC importante.
orden: 10
icono: 2148
estado: publicado
---

## Lo esencial

- Saluda con `hi`, pide el ítem y confirma con `yes` o `si`. Toda compra y venta pide confirmación.
- Si no llevas suficiente oro, el resto se cobra **solo del banco**.
- Puedes pedir cantidades: `50 arrows`, `5 ham`, `sell 3 swords`, `sell all maces`.
- Los NPCs **no compran** ítems con imbuement.
- Casi todos los NPCs están en el edificio del templo, repartidos en cuatro pisos.

## Cómo se compra

1. Acércate a menos de 4 casillas y di `hi`.
2. Di lo que quieres, con cantidad si quieres más de uno: `3 rope`.
3. El NPC pregunta, por ejemplo: *Buy 3x rope for 150 gp? (yes or si)*.
4. Responde `yes` o `si` para comprar, o `no` para cancelar.
5. Di `bye` al terminar.

Para vender es igual: `sell plate armor`, y el NPC pregunta *Sell 1x plate armor for 500 gp?*. Si no sabes qué decir, prueba `help`.

## Pagar con el banco

- El NPC usa primero el oro que llevas encima y saca el resto de tu cuenta.
- Verás un aviso como *Paid 3000 gp from your bank account*.
- Funciona en tiendas, barcos y la promoción.
- Cuando vendes, el oro llega a tu mochila. Si no hay espacio, cae a tus pies.
- Si compras algo y no te cabe, no te lo entrega y te devuelve el oro.

El **Banker** guarda tu oro: `balance`, `deposit 10000`, `deposit all`, `withdraw 5k`, `transfer 10000 Nombre`. Siempre pide `yes` antes de mover oro.

## Ítems con imbuement

Los NPCs no compran ítems mejorados con gemas. Si tienes uno limpio y uno mejorado, venden solo el limpio. Al vender, el NPC toma primero lo que está en tus mochilas y al final lo que llevas puesto. Ver [[gemas]].

## Dónde está cada NPC

El templo está en el piso 6 (`130, 53`).

| NPC | Qué hace | Dónde |
|---|---|---|
| Dark Rodo | Runas, backpacks de runas, mana fluid, wands y rods | Piso del templo (`129, 50, 6`) |
| Banker | Banco | Piso del templo (`128, 55, 6`) |
| Huntmaster | Contratos diarios | Piso del templo (`138, 53, 6`) |
| Mad | Compra armas y armaduras | Piso del templo (`145, 51, 6`) |
| Seller | Fluids, rope, shovel, backpack, armas y equipo de knight; compra vials | Un piso abajo (`145, 50, 7`). Hay otro en `208, 80, 7` |
| Parived | Compra gemas | Un piso abajo (`133, 58, 7`) |
| Tonka | Cambia 20 gemas pequeñas por 1 grande | Un piso abajo (`140, 50, 7`) |
| Lector | Comida a 8 gp | Un piso abajo (`127, 49, 7`) |
| Perac | Bows, crossbows, flechas, bolts y spears | Un piso arriba (`144, 54, 5`) |
| Dufi | Anillos, scarf y Amulet of Loss | Un piso arriba (`128, 51, 5`) |
| Guild Master | Crear y manejar guilds | Un piso arriba (`129, 51, 5`) |
| Orlan | Promoción: nivel 20 y 20.000 gp | Dos pisos arriba (`127, 49, 4`) |
| Obi | Muebles para tu casa a 500 gp | `173, 46, 7` |
| Fargum | Barcos | Puerto de la ciudad (`172, 66, 7`) |

## Comercio entre jugadores

Usa *Trade with* sobre un ítem. Los dos tienen que estar en el mismo piso y a **2 casillas** o menos. Si alguien se aleja o mueve el ítem ofrecido, el trade se cancela. Una mochila puede llevar hasta 100 ítems por oferta.

> **Ojo:** si cambias de idea, di `no`. Si hablas de otra cosa, la pregunta sigue abierta y un `yes` más tarde concreta esa compra.

## Relacionado

- [[fluids]]
- [[backpacks-de-runas]]
- [[gemas]]
- [[tarea-diaria]]
- [[barcos]]
- [[accesorios-dorados]]
