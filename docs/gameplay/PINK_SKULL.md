# Pink Skull — skull punitiva para bots

> **Estado:** implementada (18 nov 2026). Servidor: `/pink` y `/unpink`, drop total al morir, la amarilla no la
> tapa y una muerte injusta no la cambia. Cliente Retro76: `SkullPink = 7` con su calavera rosa. Ver
> [Cómo quedó](#cómo-quedó-nov-2026) al final.
>
> Esta ficha describe la Pink Skull: qué hace, cómo se asigna, cómo se ve y qué hay que tocar en el servidor y en el cliente. Fue solicitada como castigo para bots: un GM la asigna a un personaje y, mientras dure, **al morir deja caer todo el equipo**.

---

## 1. Qué hace

| Aspecto | Comportamiento |
|---------|----------------|
| **Visual** | Cráneo rosa sobre la cabeza del personaje y en el battle list. |
| **Castigo** | Si el personaje muere (PvP o PvE), todos los slots equipados caen al cadáver: cabeza, collar, mochila, armadura, manos, piernas, pies, anillo y munición. **También cae el contenido de la mochila y el AOL**. |
| **Duración** | Temporal: el GM elige cuántas horas dura. La marca persiste tras logout/relog. |
| **Asignación** | Comando GM `/pink "Nombre", horas` (mínimo 1 h). Solo jugadores online. |
| **Remoción** | Comando GM `/unpink "Nombre"`. También expira sola cuando pasa el tiempo. |
| **Frag** | Matar a un personaje con Pink Skull **no suma frag** (el servidor ya exime a víctimas que no tengan `SKULL_NONE`). |

### Diferencias clave con Red Skull

- Red Skull se gana por frags injustificados; Pink Skull se impone manualmente por un GM.
- Ambas comparten la misma mecánica de drop total (`dropLoot` con `SKULL_RED || SKULL_PINK`).
- Pink Skull **no** afecta depots, banco ni casas.

---

## 2. Comandos GM propuestos

```text
/pink "Nombre", 24     -- asigna Pink Skull por 24 horas
/pink "Nombre", 1      -- asigna Pink Skull por 1 hora
/unpink "Nombre"       -- quita la Pink Skull
```

Reglas de los comandos:

- Requiere `access = 3` (nivel de admin/God).
- No se puede aplicar a otro GM de igual o mayor `access`.
- El GM recibe un mensaje de confirmación; el objetivo recibe un mensaje visible.
- Se guarda el personaje inmediatamente (`IOPlayer::savePlayer`) para que la marca sobreviva a un reinicio.

---

## 3. Implementación técnica (servidor)

### Archivos a tocar

| Archivo | Cambio |
|---------|--------|
| `server/YurOTS/ots/source/const76.h` | Agregar `SKULL_PINK = 7` al enum de skulls. |
| `server/YurOTS/ots/source/commands.cpp` | Handlers `/pink` y `/unpink`: búsqueda case-insensitive, validación de jerarquía, seteo de `skullType`/`skullTicks`, broadcast del cambio y save. |
| `server/YurOTS/ots/source/commands.h` | Declarar los handlers. |
| `server/YurOTS/ots/data/commands.xml` | Registrar `/pink` y `/unpink` con `access="3"`. |
| `server/YurOTS/ots/source/player.cpp` | En `Player::dropLoot`, ampliar la rama red a `SKULL_RED \|\| SKULL_PINK`. |
| `server/YurOTS/ots/source/protocol76.cpp` | Asegurar que Pink no sea ocultado por la yellow skull de retaliación. |
| `server/YurOTS/ots/source/game.cpp` | Evitar que una muerte injusta posterior reemplace Pink por white/red mientras dure. |

### Flujo de asignación

1. GM ejecuta `/pink "Nombre", horas`.
2. Se busca al jugador online por nombre (case-insensitive, como `/kick`).
3. Se valida que el GM tenga mayor `access` que el objetivo.
4. Se setean:
   - `player->skullType = SKULL_PINK`
   - `player->skullTicks = horas * 3600 * 1000`
5. Se llama a `Game::Skull(player)` para refrescar a los espectadores.
6. Se guarda el personaje con `IOPlayer::savePlayer`.

### Flujo de muerte con Pink

1. `Player::dropLoot` detecta `skullType == SKULL_PINK`.
2. Transfiere todos los items de los slots `0..10` al cadáver, incluyendo AOL.
3. Limpia los slots a `NULL`.
4. `preSave()` respawnea al personaje en el templo **sin** los items perdidos.

### Consideraciones de seguridad

- **No tocar `players/*.xml` a mano**. El castigo ocurre por mecánica de muerte, no editando archivos.
- **Respaldar datos de jugadores** antes de cualquier prueba en la ThinkPad (`docs/systems/THINKPAD_TEST_SERVER.md`).
- Probar primero con un personaje de prueba, nunca con un jugador real.

---

## 4. Implementación técnica (cliente)

La Pink Skull requiere un cambio en el cliente **Retro76/OTClientV8** (Mac y Windows). El cliente oficial 7.6 queda fuera del alcance inicial porque no hay pipeline para parchear `Tibia.exe`/`Tibia.dat` en este repo.

### Cambios en `clienteretro`

1. **Constantes** (`modules/gamelib/const.lua`):
   ```lua
   SkullPink = 7
   ```
2. **Mapeo de imagen** (`modules/gamelib/creature.lua`):
   ```lua
   elseif skullId == SkullPink then
       path = '/images/game/skulls/skull_pink'
   ```
3. **Asset** (`data/images/game/skulls/skull_pink.png`):
   - Tamaño: **11×11 px**, RGBA.
   - Recolorear `skull_red.png` a rosa manteniendo la forma, el contorno oscuro y el alpha.
   - Color sugerido: `#FF69B4` (rosa fuerte) con sombra `#8B3A62`.

### Publicación

- Actualizar primero el cliente y publicar con `scripts/client-rme/publish_client.py`.
- Luego activar el estado server-side.
- Jugadores con cliente desactualizado **siguen siendo castigados** (el drop es server-side), pero no verán el icono rosa.

---

## 5. Cómo se vería

### Vista previa descriptiva

- **En el juego:** sobre la cabeza del personaje aparece un cráneo pequeño de color rosa brillante, igual de tamaño que el red skull.
- **Battle list:** el mismo icono aparece junto al nombre.
- **Al morir:** el cadáver contiene todos los items equipados y la mochila completa; el personaje revive en el templo sin equipo.

### Mockup textual

```text
[icono 11×11 rosa]  NombreDelBot
                     ^ cráneo rosa sobre la cabeza

Battle list:
[rosa] NombreDelBot  HP/MP
```

### Preview del icono

![Pink Skull 11×11 ampliado](pink-skull-preview.png)

El PNG de 11×11 (`pink-skull-11x11.png`) es el tamaño real que usaría el cliente.

### Nota sobre el asset

El PNG real se puede generar recoloreando `skull_red.png` del repo `clienteretro`. La herramienta sugerida es un script de Python con Pillow que mapee los tonos rojos a rosas conservando el alpha:

```python
from PIL import Image
img = Image.open("skull_red.png").convert("RGBA")
# mapeo por luminosidad: rojo -> rosa, oscuro -> violeta oscuro
...
img.save("skull_pink.png")
```

---

## 6. Tests mínimos antes de activar

1. `/pink "TestBot", 1` → el objetivo aparece con skull rosa (en cliente actualizado).
2. Logout/relog → la skull sigue rosa.
3. Matar al bot (GM o monstruo) → el cadáver tiene todos los slots + mochila + AOL.
4. Relog del bot → el personaje respawnea sin equipo; no hay duplicados.
5. `/unpink "TestBot"` → la skull desaparece y persiste tras relog.
6. Matar a un Pink no suma frag al killer.
7. Red Skull y muerte normal con AOL siguen funcionando igual.
8. `python3 scripts/ot-probe.py 127.0.0.1 7171` responde OK tras reinicio.

---

## 7. Preguntas abiertas para definir antes de codear

- ¿El comando acepta duración en horas o en minutos?
- ¿Pink Skull puede aplicarse a personajes offline o solo online?
- ¿Matar a un Pink debe dar derecho de saqueo inmediato o sigue las reglas normales de cuerpo?
- ¿Se quiere un log de auditoría (`GM X puso/quito Pink a Y`) en un archivo aparte?

---

## 8. Relación con la Yellow Skull

La **Yellow Skull** existe hoy como derecho de retaliación PvP ([docs/PVP_SYSTEM.md](PVP_SYSTEM.md)). La Pink Skull es una marca separada:

- Yellow es efímera y automática (1 minuto tras ser agredido).
- Pink es manual, dura horas y es un castigo administrativo.
- En el protocolo usan IDs distintos (`1` vs `7`), por lo que no se confunden.

---

## Cómo quedó (nov 2026)

Respuestas a las preguntas abiertas y lo que cambió respecto del diseño:

| Tema | Cómo quedó |
|------|-----------|
| Comando | `/pink Nombre` = rosa **hasta `/unpink`**; `/pink "Nombre", horas` = por esas horas (1–500: `skullTicks` es `int` en ms, 500 h ≈ 21 días). Las comillas son opcionales. `/unpink Nombre`. `access="3"` en `commands.xml` |
| A quién | Solo jugadores **conectados**. No se le puede poner a un GM de igual o mayor `access`, **salvo a uno mismo** (para probarla) |
| Persistencia | Se guarda el personaje al momento (`IOPlayer::savePlayer`); `skullType=7` y `skullTicks` van en `<skull>` del XML. Con `ticks="0"` no vence (`Player::checkSkull` solo descuenta si es > 0) |
| Muerte | `Player::dropLoot`: `SKULL_RED \|\| SKULL_PINK` → caen los 11 slots al cadáver, mochila y AOL incluidos |
| Si el marcado mata injusto | Suma el frag (`skullKills`) pero **no** le cambia la rosa por white/red (`Game::onPvP`) |
| Si matan al marcado | No suma frag (la víctima no es `SKULL_NONE`) y el atacante no gana white |
| Vista | `Protocol76::getDisplayedSkull`: la amarilla de retaliación no tapa ni a la roja ni a la rosa |
| Cliente | `modules/gamelib/const.lua` y `creature.lua`: `SkullPink = 7` → `/images/game/skulls/skull_pink.png` (11×11, la roja recoloreada a rosa con el mismo brillo). La usan la cabeza del personaje y la battle list (`getSkullImagePath`). Un cliente sin actualizar no dibuja nada, pero el castigo es del servidor |

Auditoría: no hay archivo de log aparte; el GM recibe la confirmación y el marcado un aviso en rojo.

### Pruebas (18 nov 2026, server aparte en 7276 con bots)

- `/pink "Bot Knight", 2`: el Bot Sorc recibe la calavera `7` del knight; el knight, el aviso.
- `/pink Bot GM` (a sí mismo) y `/unpink Bot GM`: la calavera pasa a `7` y vuelve a `0`.
- Dos Demon matan al knight: "You are dead"; su XML queda con **0 ítems** (tenía 28) y `<skull type="7" ticks="7193000">`.
- Falta verla dibujada en el cliente real.
