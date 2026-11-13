# Monstruo custom paso a paso (caso real: Black Dragon)

Guía detallada para crear un monstruo nuevo de punta a punta: diseño, XML, hechizos propios, sprite propio en el cliente, arte para la web, pruebas, spawn y deploy. Usa como ejemplo el **Black Dragon** (rama `black-dragon`, noviembre 2026).

- Para el flujo corto (XML + `monsters.xml` + RME + spawn), ver [`MONSTER_CREATION.md`](MONSTER_CREATION.md).
- Para traer el dibujo de una criatura de otra versión de Tibia (8.60), ver [`IMPORTAR_CRIATURA_DE_OTRA_VERSION.md`](IMPORTAR_CRIATURA_DE_OTRA_VERSION.md).
- Para la ficha del Black Dragon, ver [`BLACK_DRAGON.md`](BLACK_DRAGON.md).

---

## 0. Las piezas

| # | Pieza | Archivo(s) | ¿Obligatoria? |
|---|-------|------------|---------------|
| 1 | Diseño (tier, stats, rol) | — | Sí |
| 2 | Definición del monstruo | `server/YurOTS/ots/data/monster/NOMBRE.xml` | Sí |
| 3 | Hechizos propios | `data/spells/instant/*.lua`, `data/spells/runes/*.lua` + `data/spells/spells.xml` | Solo si los existentes no alcanzan |
| 4 | Registro | `data/monster/monsters.xml` | Sí |
| 5 | Paleta RME | `rme-extensions/yurots-creatures.xml` | Recomendado |
| 6 | Sprite propio (looktype nuevo) | `Tibia.dat` + `Tibia.spr` (cliente y RME) | Solo si ningún look existente sirve |
| 7 | Arte para la web | `web/assets/monsters/` | Opcional |
| 8 | Spawn | `data/world/test-spawn.xml` (o RME) | Sí, para que aparezca |
| 9 | Pruebas y deploy | Docker local / ThinkPad, `ot-probe.py`, `THINKPAD_TEST_SERVER.md` | Sí |

**El orden importa cuando hay sprite propio:** el cliente de los jugadores se actualiza **antes** de poner el spawn en producción (ver sección 6.6).

---

## 1. Diseñar el monstruo

### 1.1 Elegir el tier

Stats reales de monstruos existentes, para ubicar el nuevo:

| Monstruo | Vida | Exp | Speed | Armor | Def | Melee | Look |
|----------|-----:|----:|------:|------:|----:|------:|-----:|
| Rotworm | 65 | 40 | 116 | 2 | 9 | — | 26 |
| Cyclops | 260 | 150 | 190 | 21 | 22 | 25–80 | 22 |
| Dragon | 1000 | 700 | 170 | 30 | 31 | 37–110 | 34 |
| Black Knight | 1800 | 1600 | 390 | 43 | 45 | 82–275 | 131 |
| Dragon Lord | 1900 | 2100 | 200 | 32 | 34 | 62–205 | 39 |
| **Black Dragon** | **2600** | **2900** | **210** | **34** | **36** | **80–240** | **230** |
| Hydra | 2250 | 2100 | 200 | 38 | 35 | 60–150 | 121 |
| Behemoth | 4000 | 2500 | 270 | 44 | 42 | 160–400 | 55 |
| Warlock | 3200 | 4000 | 240 | 29 | 31 | 27–85 | 130 |
| Demon | 8200 | 6000 | 245 | 49 | 51 | 192–510 | 35 |
| Fury | 9200 | 7800 | 400 | 50 | 52 | 240–640 | 137 |

Criterio que se usó con el Black Dragon: "un escalón por encima del Dragon Lord". Tiene unos +35 % de vida y experiencia, algo más de armadura y melee, y el mismo rol (melee con aliento en abanico). La experiencia no es una fórmula fija: compárala con monstruos de riesgo parecido. Los que tiran mucho daño mágico (Warlock) dan más experiencia por punto de vida.

### 1.2 Definir el rol

- **¿Melee o distancia?** `targetdistance="1"` persigue y pega cuerpo a cuerpo; con valores mayores se queda a distancia (ver el ajuste de Fury en `MONSTER_CREATION.md`).
- **¿Huye?** `runonhealth="N"` hace que huya con N de vida o menos. El Black Dragon huye con 260 (10 % de su vida, como el Dragon Lord).
- **Identidad:** un rasgo que lo distinga de su vecino de tier. En el Black Dragon es el aliento que **drena vida** en vez de quemar.

---

## 2. El XML del monstruo

Archivo real: `server/YurOTS/ots/data/monster/black dragon.xml`. El nombre del archivo puede tener espacios; el nombre visible sale de `name=`.

```xml
<monster name="Black Dragon" level="60" maglevel="70" experience="2900" pushable="0"
         armor="34" defense="36" canpushitems="1" staticattack="50" changetarget="200" speed="210">
	<health now="2600" max="2600"/>
	<look type="230" head="0" body="0" legs="0" feet="0" corpse="3104"/>
	<combat targetdistance="1" runonhealth="260"/>
	<attacks>...</attacks>
	<defenses>...</defenses>
	<voices>...</voices>
	<loot>...</loot>
</monster>
```

| Campo | Qué hace | Notas |
|-------|----------|-------|
| `level`, `maglevel` | Nivel y nivel mágico del monstruo | Influyen en el daño de hechizos genéricos |
| `experience` | Experiencia al morir | Ver tabla 1.1 |
| `armor`, `defense` | Reducción de daño | |
| `pushable="0"`, `canpushitems="1"` | No se puede empujar; empuja ítems | Igual que los dragones |
| `staticattack`, `changetarget` | Agresividad y cada cuánto cambia de objetivo | Se copiaron del Dragon Lord |
| `speed` | Velocidad | Black Knight ~390 es muy rápido; los dragones rondan 170–210 |
| `<look type>` | Looktype (apariencia) | `head/body/legs/feet` solo colorean outfits humanos; en criaturas no tienen efecto |
| `corpse` | ID del ítem cadáver | Se usó el del Dragon (3104), porque el sprite sale de él |

### 2.1 Inmunidades: solo estas palabras

`source/monsters.cpp` solo reconoce: **energy, burst, fire, physical, poison, paralyze, drunk, invisible**. Cualquier otra se ignora sin aviso. Se probó `immunity="lifedrain"` (un XML viejo lo usa) y **no hace nada**, así que se quitó.

### 2.2 Loot

Hay dos sintaxis:

```xml
<item id="2148" countmax="100" chance1="100000" chancemax="0"/>   <!-- apilables: oro, gemas -->
<item id="2498" chance="1100"/>                                    <!-- equipo: probabilidad sobre 100000 -->
<item id="1987" chance="50000"><inside> ... </inside></item>       <!-- bolsa con contenido -->
```

- `chance="1100"` es 1,1 %. Escala: 100000 = 100 %.
- Si al arrancar aparece `missing chance for loot id = X`, ese ítem quedó con la sintaxis equivocada.
- Para nombres de ítems, buscar el ID en `data/items/items.xml`.

### 2.3 Voces

`<voice sentence="DARKNESS FALLS!"/>`: frases que grita al azar. En mayúsculas, como el resto de los dragones.

---

## 3. Ataques y hechizos propios

### 3.1 Tipos de ataque en el XML

```xml
<attack type="melee" mindamage="80" maxdamage="240" probability="100"/>
<attack type="instant" name="blackdragon_darkwave" exhaustion="500" cycleticks="6000" probability="80"/>
<attack type="rune" name="dragonlord_firebomb" exhaustion="500" cycleticks="8000" probability="25"/>
<attack type="instant" name="exura" exhaustion="500" cycleticks="6000" probability="60"/>
```

- `cycleticks`: cada cuánto lo intenta, en milisegundos.
- `probability`: probabilidad sobre 100 en cada intento.
- `exhaustion`: pausa después de lanzarlo.
- `name`: en ataques `instant` tiene que coincidir con **`words`** de un spell habilitado en `data/spells/spells.xml` (ej. `exura vita`, no su nombre visible `Ultimate Healing`); el Lua se carga desde `instant/<words>.lua`. En ataques `rune` se busca por el nombre de la runa. Los hechizos exclusivos de monstruos usan `maglv="4000"` para que ningún jugador los aprenda.

**Reutilizar antes que crear.** Hay 64 hechizos registrados. Para buscar: `grep -ho 'name="[^"]*"' data/monster/*.xml | sort | uniq -c`. El Black Dragon reutiliza `necro_lifedrain`, `dragonlord_firebomb` y `exura`, y agrega uno solo propio.

### 3.2 Crear un hechizo instantáneo (ej. `blackdragon_darkwave`)

1. **Lua** en `data/spells/instant/blackdragon_darkwave.lua`. Se copió `dragonlord_firewave.lua`: misma matriz de área (abanico), con cambios en el tipo de daño, los efectos y el daño.
2. **Registro** en `data/spells/spells.xml`:
   ```xml
   <spell name="blackdragon_darkwave" words="blackdragon_darkwave" maglv="4000" mana="800" enabled="1"></spell>
   ```

Estructura del Lua:

```lua
area = { ... }               -- matriz; ver 3.4
attackType = ATTACK_LIFEDRAIN
needDirection = true         -- true = el área gira hacia donde mira (olas); false = centrado (alrededor)
areaEffect = NM_ME_MORT_AREA -- efecto en cada casilla
animationEffect = NM_ANI_NONE
hitEffect = NM_ME_MAGIC_BLOOD
damageEffect = NM_ME_MAGIC_BLOOD
animationColor = BLACK       -- color del número de daño
offensive = true
drawblood = false

DarkWaveObject = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, 0, 0)

function onCast(cid, creaturePos, level, maglv, var)
centerpos = {x=creaturePos.x, y=creaturePos.y, z=creaturePos.z}
DarkWaveObject.minDmg = 170
DarkWaveObject.maxDmg = 290
return doAreaMagic(cid, centerpos, needDirection, areaEffect, area, DarkWaveObject:ordered())
end
```

### 3.3 Constantes disponibles (`data/spells/lib/spells.lua`)

| Grupo | Valores |
|-------|---------|
| `ATTACK_*` (tipo de daño) | `ENERGY`, `BURST`, `FIRE`, `PHYSICAL`, `POISON`, `PARALYZE`, `DRUNKNESS`, `LIFEDRAIN`, `MANADRAIN` |
| `NM_ME_*` (efectos en casilla) | `DRAW_BLOOD`, `LOOSE_ENERGY`, `PUFF`, `BLOCKHIT`, `EXPLOSION_AREA`, `EXPLOSION_DAMAGE`, `FIRE_AREA`, `YELLOW_RINGS`, `POISEN_RINGS`, `HIT_AREA`, `ENERGY_AREA`, `ENERGY_DAMAGE`, `MAGIC_ENERGIE`, `MAGIC_BLOOD`, `MAGIC_POISEN`, `HITBY_FIRE`, `POISEN`, `MORT_AREA`, `SOUND_*`, `POISONCLOUD`, `NONE` |
| `NM_ANI_*` (proyectil) | `BOLT`, `ARROW`, `FIRE`, `ENERGY`, `POISONARROW`, `BURSTARROW`, `THROWINGSTAR`, `THROWINGKNIFE`, `SMALLSTONE`, `SUDDENDEATH`, `LARGEROCK`, `SNOWBALL`, `POWERBOLT`, `NONE` |
| Colores del número | `GREEN`, `RED`, `DARK_BLUE`, `LIGHT_BLUE`, `ORANGE`, `ENERGY`, `FIRE`, `GREY`, `BLUE`, `PURPLE`, `YELLOW`, `BLACK` |

El cliente 7.6 base trae 25 efectos (0–24) y 15 proyectiles (0–14), sin hielo, sagrado ni tierra. **Se pueden agregar
efectos nuevos recoloreando los existentes**: ver [`CLIENT_EFFECTS.md`](CLIENT_EFFECTS.md) (pack "ice": `NM_ME_ICE_*` 25–28 y
`NM_ANI_FROSTBALL` 15).

### 3.4 Matrices de área

- `0` = nada. `1`, `2`, `3`, `4` = casillas afectadas según la dirección (norte, oeste, este, sur) cuando `needDirection = true`. El centro de la matriz es el monstruo.
- Para un área alrededor sin dirección, usar `1` en todo el contorno (ver `necro_lifedrain.lua`) y `needDirection = false`.
- Para una runa con proyectil y área en el objetivo, copiar un archivo de `data/spells/runes/` (ej. `dragonlord_firebomb.lua`, que usa `doAreaGroundMagic` y deja campos) y registrarlo como `<rune name="..." id="5xxx" ...>` en `spells.xml`. Los IDs 5000+ ya se usan para runas de monstruos; tomar el siguiente libre.

---

## 4. Registro y paleta de RME

1. `data/monster/monsters.xml`: `<monster name="Black Dragon" file="black dragon.xml" />`. Se puso junto a los Dragon Lord.
2. `rme-extensions/yurots-creatures.xml`: `<creature name="Black Dragon"/>` dentro del tileset `YurOTS Custom`.
3. `./scripts/setup-rme-creatures.sh` y `./scripts/setup-rme-extensions.sh` (o `./scripts/open-rme.sh`, que corre todo).

Detalle en [`MONSTER_CREATION.md`](MONSTER_CREATION.md), secciones 2 y 4.

Opcional: `data/spells/lib/spells.lua` tiene una tabla `outfits` (nombre → looktype) que usan los hechizos de transformación en monstruo. Si se agrega el nuevo monstruo ahí, los jugadores podrían transformarse en él. Con el Black Dragon **no** se hizo.

---

## 5. Decidir el aspecto: look existente o sprite propio

| Opción | Ventaja | Costo |
|--------|---------|-------|
| **Reusar un looktype existente** (ej. Fury usa 137, un outfit humano coloreado) | Cero cambios en el cliente; se despliega ya | Se ve igual que otro monstruo (las criaturas no se pueden recolorear con `head/body/...`) |
| **Sprite propio** (Black Dragon, looktype 230) | Aspecto único | Hay que actualizar `Tibia.dat`/`Tibia.spr` de **todos** los jugadores antes de ponerlo en el mapa |

---

## 6. Sprite propio: looktype nuevo

### 6.1 Límites del protocolo 7.6

- El looktype viaja en **un byte** (`protocol76.cpp`, `msg.AddByte(creature->looktype)`): **máximo 255**.
- El `Tibia.dat` base define 254 looktypes, pero muchos están **vacíos**: 11, 12, 20, 46, 47, 72, 77, 93, 96–98, 135, 143, 145–159, 161–200, 222–224, 226, 229–254.
- Los custom del servidor ya usan 211–221 y 225. El Black Dragon tomó el **230**.
- Antes de elegir, comprobar que ningún XML lo use: `grep -rhoE 'type="[0-9]+"' data/monster data/npc | sort -u`.

### 6.2 Cómo se guarda una criatura en el cliente

Un looktype en `Tibia.dat` es un "thing" con atributos y una lista de IDs de sprites (32×32) de `Tibia.spr`. El Dragon (34) tiene:

| Dato | Valor |
|------|-------|
| Tamaño | 2×2 tiles (64×64 píxeles) |
| Patrón X | 4 = direcciones (norte, este, sur, oeste) |
| Animación | 3 cuadros (quieto + 2 de caminar) |
| Total | 2×2×4×3 = **48 sprites** |

Orden de los IDs: por cuadro de animación, luego por dirección, luego los 4 tiles empezando por **abajo a la derecha**. `add_black_dragon_look.py` lo usa para armar la vista previa.

Formato de `Tibia.spr` (7.6): firma `u32`, cantidad `u16` (máximo 65535), tabla de offsets `u32` y cada sprite comprimido en RLE: color clave de 3 bytes, tamaño `u16` y pares (transparentes, coloreados) seguidos de RGB. El base tiene 10962 sprites; con el Black Dragon quedaron 11010.

**Ojo con `build_zagan_test_assets.py`:** lee `item_count` entradas de ítems empezando en el 100, pero en el `.dat` hay `item_count - 99` ítems. Las 99 entradas que lee "de más" son en realidad los looktypes 1–99. Como reescribe esos bytes sin cambios no rompe nada hoy, pero si alguna vez elige como "sacrificio" un client id mayor que 5088, estaría pisando un looktype. Los scripts nuevos usan `item_count - 99`.

### 6.3 Crear el sprite: recoloreado por algoritmo

`scripts/client-rme/add_black_dragon_look.py`:

1. Lee el Dragon (34) del `.dat` y decodifica sus 48 sprites del `.spr`.
2. Recolorea cada píxel. Los ojos y la lengua (rojo/naranja intenso) pasan a rojo brillante; el resto pasa a negro con brillo violeta azulado según la luminosidad original, con contraste ajustado para que no se pierda en suelos oscuros.
3. Agrega los 48 sprites nuevos al final del `.spr`.
4. Reemplaza la entrada vacía del looktype 230 por la cabecera del Dragon con los IDs nuevos.
5. Comprueba que el `.dat` resultante se lea completo y que el 230 apunte a los sprites nuevos.
6. Deja copias `.bak-blackdragon`. Si el 230 ya tiene sprites, no hace nada (idempotente).

```bash
python3 scripts/client-rme/add_black_dragon_look.py devtools/rme/rme-client-760 --preview docs/gameplay/img/black-dragon.png
```

Se verificó leyendo los archivos resultantes con un parser independiente:

- El 230 se ve igual que la vista previa.
- 300 sprites viejos al azar siguen idénticos.
- Los looktypes 34 y 39 no cambiaron.
- Los ítems no cambiaron.

### 6.4 Adaptarlo a otro monstruo

> **Receta paso a paso para crear o editar un sprite:** [`SPRITE_RECOLOR_GUIDE.md`](SPRITE_RECOLOR_GUIDE.md).
> Tiene los comandos en orden, una plantilla de preset, los trucos que ya funcionaron y los umbrales de
> color de cada base. Leerla antes de escribir un preset.

**Cómo está armado:** cada criatura es un preset, un archivo en `scripts/client-rme/presets/`
(`tide_priest.py` = preset `tide-priest`) con `PRESET = dict(name, source, target, parts, palettes, detail)`.
`sprite_tool.py new NOMBRE --base LOOK` lo crea listo para editar; `add_recolor_look.py --preset NOMBRE
DIR_THINGS` lo aplica (con `--replace` rehace un look que ya existe). Sirve para criaturas 2×2 (48 sprites)
y 1×1 (12 sprites) con 4 direcciones y 3 cuadros; la estructura del base se copia tal cual.

Presets y looktypes usados: `python3 scripts/client-rme/sprite_tool.py looks` (lista cada preset, su base,
su archivo y si está aplicado). Bases posibles: [`SPRITE_BASES.md`](SPRITE_BASES.md).

`scripts/client-rme/sprite_tool.py` ahorra los scripts sueltos: `bases` (catálogo de bases), `new` (crear
preset), `inspect` (el sprite en texto), `check` (hoja + escena), `sheet`, `scene` y `verify` (integridad
del `.dat`/`.spr` contra git).

### 6.5 ¿Y la IA para sprites? (probado: no)

Se probó nano banana (Replicate) para repintar la grilla de 12 cuadros sobre fondo magenta, con instrucciones estrictas de no mover nada. Resultado:

- Devolvió 1184×864 en vez de 2048×1536, con escala distinta en horizontal y vertical.
- Una vez alineado, cada cuadro coincide con la silueta original solo entre un 93 y un 96 %.
- Cambia detalles entre cuadros (ojos, cuernos): la animación parpadearía.
- Deja bordes magenta y motas blancas.

**Conclusión:** para sprites animados, el recoloreado por algoritmo (o el dibujo a mano). La IA, para arte fijo (sección 7).

### 6.6 Repartir el sprite (orden obligatorio)

1. **RME (en git):** aplicar el script a `devtools/rme/rme-client-760/` y commitear `Tibia.dat`/`Tibia.spr`. Hecho para el Black Dragon.
2. **Cliente de jugadores (Mac de desarrollo):** aplicar el script a la base `client-local/data/things/760/` y regenerar el pack con `python3 scripts/client-rme/build_zagan_test_assets.py`. El builder copia los looktypes de la base sin tocarlos.
3. **Publicar** `zagan-test/client-things/760/Tibia.{dat,spr}` en el updater ([`../CLIENT_UPDATER_RETRO76.md`](../CLIENT_UPDATER_RETRO76.md)) y confirmar con un cliente actualizado que el monstruo se ve.
4. **Recién entonces** agregar el spawn y desplegar el servidor. Un cliente viejo encuentra el looktype vacío: el monstruo sale invisible, o el cliente puede fallar.

---

## 7. Arte para la web (nano banana)

`scripts/web/generate-monster-art.py` llama a `google/nano-banana` en Replicate con el sprite del juego como referencia de diseño, para que el arte se parezca al monstruo real. El token va en `REPLICATE_API_TOKEN`; el script no lo guarda.

```bash
export REPLICATE_API_TOKEN=r8_...
python3 scripts/web/generate-monster-art.py --reference REF.png --prompt-file retrato.txt --aspect 1:1 --out /tmp/retrato.png
python3 scripts/web/generate-monster-art.py --reference REF.png --prompt-file banner.txt --aspect 16:9 --out /tmp/banner.png
sips -s format jpeg -s formatOptions 85 /tmp/retrato.png --out web/assets/monsters/NOMBRE-portrait.jpg
sips -s format jpeg -s formatOptions 85 /tmp/banner.png  --out web/assets/monsters/NOMBRE-banner.jpg
```

La referencia del Black Dragon fue un cuadro del sprite (mirando al sur) ampliado 8× sobre fondo oscuro. También sirve la vista previa en grilla del script del sprite.

Prompt usado para el **retrato** (1:1):

> Use the reference image only as the character design: a black dragon from a classic 2D MMORPG (Tibia 7.6 era). Create a detailed retro pixel-art illustration of this Black Dragon for the game's website: the dragon rearing up with wings spread inside a dark volcanic cave, obsidian-black scales with subtle deep purple and dark blue highlights, bone-white horn and claw tips, glowing red eyes, wisps of dark purple-black life-draining breath curling from its jaws. Square composition, dragon centered and fully visible, dramatic rim lighting, limited retro palette, crisp visible pixels, no anti-aliasing blur. No text, no letters, no watermark, no logo, no UI, no frame.

Prompt usado para el **banner** (16:9):

> Use the reference image only as the character design: a black dragon from a classic 2D MMORPG (Tibia 7.6 era). Create a wide retro pixel-art announcement banner: the Black Dragon flies on the left third of the image over a dark misty fantasy landscape with ancient stone ruins and a blood-red moon, obsidian-black scales with deep purple and dark blue highlights, glowing red eyes, a stream of dark purple-black life-draining breath. Keep the right half calm and dark (night sky and mist) as empty space for overlay text. Limited retro palette, crisp visible pixels. No text, no letters, no watermark, no logo, no UI, no frame.

Consejos:

- **Sin texto en la imagen.** Los modelos deforman letras, y el texto en HTML se puede editar y traducir.
- **Describir los rasgos del sprite:** colores, ojos, detalles. Así el arte no contradice lo que se ve en el juego.
- **Pedir espacio vacío** donde irá el texto del anuncio.
- **Pasar a JPG 85** antes de commitear: de ~1 MB en PNG a 120–260 KB.

---

## 8. Probar

Con el servidor local (Docker en la Mac de desarrollo o en la ThinkPad):

```bash
docker compose -f docker-compose.prod.yml restart yurots
docker logs yurots --tail 80          # sin errores de black dragon.xml ni de blackdragon_darkwave
python3 scripts/ot-probe.py 127.0.0.1 7171
```

En el juego, con un GM (`access` 2 o más):

- `/m Black Dragon`: lo crea al lado (`/summon` crea un summon, con access 3).
- Comprobar:
  - Que se ve en las 4 direcciones y camina (cliente actualizado).
  - Que lanza el aliento y la ola sale hacia donde mira.
  - El daño contra un personaje de nivel parecido al del tier.
  - El loot al morir.
  - Que huye con poca vida.
- Con un **cliente viejo**, confirmar el riesgo: así se ve qué le pasaría a quien no actualice.

---

## 9. Spawn y deploy

1. **Spawn:** en `data/world/test-spawn.xml` (a mano o desde RME). Elegir zona y `spawntime` según la dificultad. Ver [`../CAMBIAR-MAPA.md`](../CAMBIAR-MAPA.md) y [`RESPAWN_SYSTEM.md`](RESPAWN_SYSTEM.md).
2. **Commit y push**, en commits chicos (regla del repo: ~300 líneas máximo).
3. **Deploy a la ThinkPad**, solo con el OK de Gonzalo: seguir [`../systems/THINKPAD_TEST_SERVER.md`](../systems/THINKPAD_TEST_SERVER.md), y `ot-probe.py 192.168.1.17 7171` después.

---

## 10. Checklist

```text
Diseño
[ ] Tier y rol definidos contra la tabla 1.1
XML y hechizos
[ ] data/monster/NOMBRE.xml (look, corpse, inmunidades válidas, loot con la sintaxis correcta)
[ ] Hechizos nuevos: Lua en spells/instant o spells/runes + entrada en spells.xml (maglv="4000")
[ ] Alta en monsters.xml
[ ] Tileset en rme-extensions/yurots-creatures.xml + setup-rme-creatures.sh
Sprite propio (si aplica)
[ ] Looktype vacío elegido (sprite_tool.py looks) — receta en SPRITE_RECOLOR_GUIDE.md
[ ] Preset aplicado al RME (git) con hoja y escena revisadas (sprite_tool.py sheet / scene)
[ ] sprite_tool.py verify --expect LOOK en "TODO BIEN" y sin .bak-*
[ ] Script aplicado a client-local + build_zagan_test_assets.py
[ ] Tibia.dat/.spr publicados en el updater y verificados con un cliente actualizado
Web (opcional)
[ ] Retrato y banner con generate-monster-art.py → web/assets/monsters/*.jpg
Pruebas y salida
[ ] Boot local limpio + ot-probe OK + /m NOMBRE en el juego
[ ] Spawn en test-spawn.xml
[ ] Deploy a la ThinkPad con OK de Gonzalo
```

---

## 11. Caso Black Dragon: qué se hizo

Rama `black-dragon`, desde `main` (`bcec923`):

| Commit | Contenido |
|--------|-----------|
| `dda15ab` | `black dragon.xml`, `blackdragon_darkwave.lua`, entradas en `spells.xml` y `monsters.xml`, tileset de RME |
| `a3a7534` | `add_black_dragon_look.py`, looktype 230 en el `Tibia.dat`/`.spr` de RME, vista previa, `BLACK_DRAGON.md` |
| `ce5756e` | Retrato y banner para la web |

Decisiones:

- **Aliento que drena vida.** Le da identidad propia frente al Dragon Lord, que quema.
- **Sin `immunity="lifedrain"`.** El motor la ignora.
- **Cadáver del Dragon (3104).** El sprite sale de ese dragón.
- **Looktype 230.** Estaba vacío y ningún XML lo usaba.
- **Recoloreado por algoritmo y no por IA.** Mantiene la animación consistente.

Pendiente al escribir esto:

- Cliente de jugadores y updater.
- Spawn: falta elegir la zona.
- Prueba en el juego.
- Deploy.

---

## 12. Problemas típicos

| Síntoma | Causa probable | Dónde mirar |
|---------|----------------|-------------|
| El monstruo sale invisible | Looktype que el cliente no tiene (cliente viejo) | 6.6 |
| Una inmunidad no funciona | Palabra no reconocida (ej. `lifedrain`) | 2.1 |
| `missing chance for loot id` al arrancar | Sintaxis de loot equivocada | 2.2 |
| El hechizo no se lanza nunca | `name` no está en `spells.xml`, o el archivo Lua no se llama igual | 3.2 |
| La ola sale para el lado equivocado | Números 1–4 de la matriz o `needDirection` | 3.4 |
| El sprite se ve cortado o desordenado | Orden de tiles/direcciones distinto al del base | 6.2 |
| `Tibia.spr se pasaría del máximo` | Más de 65535 sprites | 6.2 |
| Aparece en RME pero no en el juego | Falta el alta en `monsters.xml` o el spawn | [`MONSTER_CREATION.md`](MONSTER_CREATION.md) |
