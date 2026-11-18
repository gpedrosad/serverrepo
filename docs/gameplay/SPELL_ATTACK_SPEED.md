# Frenzy y Rapid Fire: ataques más rápidos unos segundos (nov 2026)

Dos hechizos de buff que bajan la espera entre golpes durante unos segundos. Mientras dura, el jugador
tiene un efecto encima cada segundo (lo ven todos) y un ícono en el panel de condiciones del cliente.

| Hechizo | Palabras | Vocación | ML / maná | Espera entre golpes | Dura | Se relanza a los | Efecto constante |
|---------|----------|----------|-----------|---------------------|------|------------------|------------------|
| Frenzy | `utito hur` | Knight / Elite Knight | 5 / 100 | −40 %: 1333 → **800 ms** | 6 s | 20 s | chispas rojas (`NM_ME_MAGIC_BLOOD`) |
| Rapid Fire | `utito san hur` | Paladin / Royal Paladin | 8 / 120 | −35 %: 1333 → **866 ms** | 6 s | 20 s | chispas azules (`NM_ME_MAGIC_ENERGIE`) |

- Vale para **melee y distancia**: `Game::checkCreatureAttacking` programa el próximo golpe con
  `Player::getAttackDelayMs()`, que es el mismo camino para los dos.
- **Se suma** a las armas y gemas rápidas (Aurora, Crisol, ruby, Nightglass, Crystal Arrow): el porcentaje
  se aplica sobre la espera que ya daban (`getBaseAttackDelayMs()`), con un piso de **500 ms**
  (`ATTACK_SPEED_BUFF_MIN_DELAY_MS` en `const76.h`).
- Si se lo dice antes de los 20 s: "You can use it again in N s.", **no gasta maná** (el Lua devuelve
  `false`, como el Eco).
- El primer golpe después de lanzarlo sale todavía con la espera vieja (ya estaba programado); del segundo
  en adelante, con la nueva.
- Al relogear se pierde (el estado vive en el objeto `Player`).

## Ajustar sin recompilar

En `server/YurOTS/ots/data/spells/instant/utito hur.lua` y `utito san hur.lua`:

```lua
DURACION = 6        -- segundos
PORCENTAJE = 40     -- cuánto baja la espera entre golpes (1-99)
ESPERA = 20         -- segundos desde el cast hasta poder relanzarlo (nunca menos que DURACION)
EFECTO = NM_ME_MAGIC_BLOOD   -- cada segundo sobre el jugador (NM_ME_NONE = ninguno)
```

ML y maná, en `spells.xml` (bloque "ataques mas rapidos"). Se toman al reiniciar el server.

## Cómo está hecho

| Dónde | Qué |
|-------|-----|
| `source/player.h` / `player.cpp` | `attackSpeedUntil`, `attackSpeedPercent`, `attackSpeedReadyAt`, `attackSpeedEffect`; `hasAttackSpeedBuff()`; `getAttackDelayMs()` = `getBaseAttackDelayMs()` con el buff encima |
| `source/spells.cpp` | Bindings Lua `attackSpeedReady(cid)` (segundos que faltan, avisa al jugador) y `startAttackSpeed(cid, duración, %, espera, efecto)` |
| `source/game.cpp` | Tick de 1 s del jugador (`checkCreature`): dibuja el efecto mientras dura y al terminar manda "Your attacks slow down." |
| `data/spells/instant/utito hur.lua`, `utito san hur.lua` | Los números de arriba |
| Cliente `clienteretro` (`mac/` y `windows/`): `modules/game_inventory/inventory.lua` | Ícono `strengthened` en el panel de condiciones con los segundos que quedan escritos encima (desde nov 2026 es una fila de la tabla `TimedIcons`, compartida con los hechizos de [SPELLS_FEEDBACK.md](SPELLS_FEEDBACK.md)); al terminar queda apagado con la espera hasta poder relanzarlo ("Frenzy: ready again in N s.") |
| Cliente: `modules/gamelib/spells.lua`, perfil `Retro76` | Las palabras, para el texto naranja de los hechizos |

**Por qué el ícono lo prende un mensaje y no el byte de estados:** en 7.6 los íconos viajan en un byte
(`0xA2`) y sus 8 bits ya están usados (veneno, fuego, energía, borracho, escudo, parálisis, haste, espadas).
Pasar a 16 bits cambia el protocolo y rompe a cualquier cliente sin actualizar. El cliente escucha el mensaje
"Your attacks speed up for N s." (`onTextMessage`), crea el ícono y lo saca con "Your attacks slow down." o
cuando la cuenta llega a 0. Un cliente sin actualizar ve el mensaje y el efecto, pero no el ícono.
**No cambiar el texto de esos dos mensajes** sin cambiar el cliente.

## Pruebas (2026-11-16)

Binario compilado en la ThinkPad (`~/build/attackspeed-src`, `make clean`, 0 avisos) y levantado aparte en el
puerto 7275 con una copia de los datos y las cuentas de `make-test-bots.py`. Un bot GM invoca un Private
Trainer Dummy y Bot Knight / Bot Pally le pegan; se mide el tiempo entre los efectos de golpe bloqueado:

| | Antes | Con el buff | Después |
|---|---|---|---|
| Knight (`utito hur`) | 1333 ms | 799 ms | 1333 ms |
| Paladin (`utito san hur`) | 1333 ms | 866 ms | 1333 ms |

Efecto constante: 6 por cast (uno por segundo), ninguno antes ni después. Relanzar a los 2 s: "You can use it
again in 8 s." (no gasta maná); a los 20 s vuelve a salir. El ícono del cliente se probó con un banco en Lua
(mensaje → ícono con cuenta regresiva → se saca con el mensaje de fin o al llegar a 0). Falta verlo en el
cliente real.

**Ojo al medir con bots:** en el paquete `0x83` el efecto va como `tipo + 1` (`NM_ME_MAGIC_BLOOD` = 13 llega
como 14).
