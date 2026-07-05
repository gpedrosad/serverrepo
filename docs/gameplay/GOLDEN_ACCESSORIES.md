# Golden Accessories

Documentación del comportamiento actual de:

- `golden amulet` (`2130`)
- `golden ring` (`2179`)

Los dos afectan el **oro de monstruos**, pero cumplen roles distintos.

## Resumen rápido

- `golden amulet (2130)`:
  deposita en el banco el oro del loot del monstruo al matarlo, sin abrir el cuerpo.
- `golden ring (2179)`:
  aumenta en `20%` el oro que genera el monstruo, mientras esté equipado en el slot de ring.
- Si usás ambos:
  el ring aumenta primero el oro del corpse y luego el amulet deposita ese total en el banco.

## Golden Amulet (2130)

### Qué hace

Si está equipado en el slot de amuleto/necklace, el oro del monstruo se mueve directo al banco del killer cuando el loot se genera.

Aplica solo a monedas:

- gold coins
- platinum coins
- crystal coins

No mueve otros ítems del loot.

### Qué no hace

- no aumenta la cantidad de oro;
- no auto-lootea armas, armaduras, gemas ni otros drops;
- no requiere abrir el corpse.

### Seguridad del flujo

El depósito ocurre solo si el guardado del balance de banco sale bien.
Si el depósito falla, el oro no se borra del corpse.

## Golden Ring (2179)

### Qué hace

Si está equipado en el slot de ring, da `+20%` de oro de monstruos al killer.

Ese bonus se calcula sobre el valor total de monedas del corpse:

- gold
- platinum
- crystal

También cuenta monedas dentro de contenedores del loot del monstruo.

### Qué no hace

- no afecta ítems no monetarios;
- no da bonus a gemas, equipos ni consumibles;
- no deposita al banco por sí solo;
- no necesita activación visual ni estado “in use”: alcanza con tenerlo equipado.

### Ejemplo

Si el loot monetario total de un monstruo es `150 gp`, el ring agrega `30 gp`.

Resultado final:

- sin ring: `150 gp`
- con ring: `180 gp`

## Interacción entre ambos

Si el jugador mata con ambos equipados:

1. el monstruo genera su loot normal;
2. el `golden ring` agrega `20%` extra de monedas;
3. el `golden amulet` deposita al banco todo el oro del corpse;
4. las monedas se eliminan del corpse, pero el resto del loot queda normal.

Ejemplo:

- loot monetario base: `500 gp`
- bonus del ring: `100 gp`
- total depositado por el amulet: `600 gp`

## Restricción especial del Golden Ring

El `golden ring (2179)` está bloqueado globalmente como loot de monstruos.

Eso significa que:

- ningún monstruo lo puede dropear;
- aunque algún XML viejo todavía liste `2179`, el servidor lo ignora al generar loot.

## Alcance real del sistema

Esto corre del lado servidor al momento de crear el loot del monstruo.

Por eso:

- funciona igual con loot manual o con golden amulet;
- no depende del cliente;
- no depende de abrir el corpse;
- aplica sobre el oro realmente generado por el server.

## Referencias técnicas

- `server/YurOTS/ots/source/player.cpp`
- `server/YurOTS/ots/source/game.cpp`
- `server/YurOTS/ots/source/monsters.cpp`
- `server/YurOTS/ots/source/item.cpp`
- `server/YurOTS/ots/source/const76.h`
