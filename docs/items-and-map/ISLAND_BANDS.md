# Bandas de terreno en islas — guía de coherencia agua/pasto

> **Problema:** las islas generadas por `scripts/generate-island.py` (y por extensión la mayoría de OTs Tibia 7.6) tienen un **corte visual duro** entre el agua y el pasto porque YurOTS no tiene autotile. Esta guía documenta cómo se debe componer una isla para que la transición se vea coherente.

**Audiencia:** quien modifique `scripts/generate-island.py` o genere terreno a mano en RME.

**No es un cambio de código todavía:** es la especificación del comportamiento correcto. Cuando se implemente, este doc pasa a ser el contrato que debe cumplir el script.

---

## 1. Por qué se "rompe" la separación agua/pasto

YurOTS 7.6 — como el cliente original de Tibia 7.6 — **no tiene autotile**. Cada ground es un sprite fijo:

- El sprite de agua `4608` es un cuadrado plano con borde rectangular recto.
- El sprite de pasto `101` es un cuadrado plano con borde rectangular recto.
- Cuando los pones adyacentes, ves una **línea recta entre dos texturas planas** — sin interpolación, sin borde, sin shading.

A partir de Tibia 10 el cliente agregó autotile (edges con border masks), pero el protocolo y la paleta 7.6 no lo soportan. Por eso **toda** isla 7.6 tiene este problema latente, sin importar el mapper.

La única mitigación real es **componer bandas de transición** con tiles que ya tengan bordes aceptables.

---

## 2. Bandas correctas, de afuera hacia adentro

Una isla estética en 7.6 se compone de **5 bandas concéntricas**, cada una con sus propios tiles y reglas:

```
            ┌─────────────────────────────────────┐
            │            VOID (sin tile)          │  dist > 1.18
            ├─────────────────────────────────────┤
            │  ░░░ DEEP WATER ░░░░░░░░░░░░░░░░░░  │  dist 1.05–1.18
            │  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  │
            ├─────────────────────────────────────┤  dist ~1.05
            │  ▒▒ SHALLOW WATER ▒▒▒▒▒▒▒▒▒▒▒▒▒▒  │  dist 0.95–1.05
            ├─────────────────────────────────────┤
            │  ▓▓▓ SHORE / SAND ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓  │  dist 0.85–0.95
            ├─────────────────────────────────────┤
            │  ███ DIRT BAND ████████████████████  │  dist 0.72–0.85
            ├─────────────────────────────────────┤
            │  ▓▓▓▓▓▓▓▓ GRASS INTERIOR ▓▓▓▓▓▓▓▓▓  │  dist ≤ 0.72
            └─────────────────────────────────────┘
```

### 2.1 Deep water (anillo más externo)

- **Tiles:** `4608` (~95%) + `4691` (~5%, mezclado al azar).
- **Función visual:** el cuerpo de agua "real". `4691` aparece en manchones para que no se vea 100% uniforme.
- **Server id confirmado en mapa:** `4608` (912 tiles), `4691` (255 tiles), `4609` (28), `4610` (21), `4632-4642` (variants profundas poco usadas).

### 2.2 Shallow water (anillo intermedio, 0.95–1.05)

- **Tiles:** `4691` mezclado con `4608` en proporción que se va invirtiendo hacia la costa.
- **Función visual:** "el agua se va poniendo menos profunda". El ojo lo lee como transición aunque el sprite no cambie.
- **Truco:** la **proporción** entre `4608` y `4691` no es 50/50 fija. En el extremo profundo (dist ≈ 1.05) pesa más `4608`; en el extremo costero (dist ≈ 0.95) pesa más `4691`. La transición se ve como un degradado.

### 2.3 Shore / arena (costa)

- **Tiles:** `4526` (~70%, arena clara) + `4566` (~30%, arena más oscura/húmeda).
- **Función visual:** la línea de costa. Este anillo es **crítico**: si falta, el agua choca directo contra grass y se ve mal.
- **Server id confirmado:** `4526` (101 tiles), `4566` (56 tiles).
- **Regla:** el shore debe tener **al menos 2 tiles de ancho** para que se lea como playa. Con 1 solo tile se ve como un parche raro.

### 2.4 Dirt band (anillo de tierra)

- **Tiles:** `103` (~40%) + `231` (~40%) + manchones de `351-360` (~20%).
- **Función visual:** el "borde interno" de la isla, donde la tierra está más expuesta y menos cubierta de pasto. Es el equivalente natural del "lodo/playa interior".
- **Server id confirmado:** `103` (188 tiles), `231` (132 tiles), `351` (64), `352` (58), `353-360` (variants).
- **Regla importante:** la dirt band **no debe ser un anillo perfecto**. Si la hacés circular perfecta se ve artificial. Mejor: manchones irregulares con wobble fuerte. Idealmente también algunos manchones de dirt **dentro** del pasto (parches dispersos), como suele verse en islas reales.

### 2.5 Grass interior (centro de la isla)

- **Tiles:** `101` (35%) + `598` (35%) + `407` (10%) + `405` (5%) + `919` (10%) + `920` (5%).
- **Función visual:** el cuerpo de la isla. La variación entre 6 sprites rompe la uniformidad.
- **Server id confirmado:** `101` (1420), `598` (1149), `919` (172), `405` (171), `407` (143), `920` (37).
- **Regla:** el grass debe "armar" manchones, no estrías. Si los 6 tiles se mezclan tile-por-tile, queda ruido. Mejor: elegir 2-3 "manchones dominantes" según un noise (perlin/value noise) y usar los demás como点缀 (detalles).

---

## 3. Reglas críticas de coherencia

Estas reglas **deben** cumplirse. Si falta alguna, la isla se ve rota:

### R1. Nunca agua directa contra grass

```
[agua] [grass]  ← MAL: corte visible, línea dura
[agua] [shore] [grass]  ← BIEN
[agua] [shallow] [shore] [dirt] [grass]  ← IDEAL
```

Si el script genera `dist > 0.92 = shore` y `dist > 0.78 = dirt`, el ring resultante es agua-shore-dirt-grass. Hoy cumple esto, pero **si alguien baja `dist > 0.92` a `0.85` sin agregar otro anillo, se rompe**.

### R2. Nunca un solo id por banda

Cada banda debe tener **al menos 2 ids mezclados**, salvo que la banda tenga < 5 tiles. Un anillo de shore 100% `4526` se ve pintado con stencil.

### R3. Wobble en cada banda, no solo en la externa

El script actual aplica wobble solo a la condición de corte (`> 1.05`, `> 0.92`, etc.). Esto significa que los anillos de shore/dirt/grass son **anillos concéntricos perfectos** salvo en el borde externo. Hay que aplicar un **ruido de wobble local** dentro de cada banda, sino se ven los radios marcados.

Patrón sugerido: en vez de `if dist > 0.92`, usar `if dist + wobble_local(x, y, seed) > 0.92` con `wobble_local ∈ [-0.06, +0.06]`.

### R4. Shore con grosor mínimo

El shore debe ocupar **al menos 2-3 tiles de ancho radial**. Si el script usa `dist > 0.92` y `dist > 0.85`, el shore es de 7% del radio. Para una isla radio 14, eso es 1 sola tile de ancho. **Demasiado fino** — se ve como línea.

Recomendación: shore de 2-3 tiles = `0.85-0.95` del radio, no `0.92-0.95`.

### R5. Manchones de dirt, no anillo

La dirt band no debe ser un anillo perfecto. Mezclar:
- Anillo principal de dirt en `0.72-0.85`.
- Manchones de dirt **adentro** del grass (parches aleatorios al 15% en el pasto).
- Manchones de grass **adentro** del dirt (lo opuesto, al 10%).

Esto le da a la isla textura en vez de un "anillo pintado".

### R6. Grass con seed de manchas, no tile-a-tile random

Si elegís el grass con `random.choice(GRASS)`, queda ruido de píxeles (cada tile puede ser un grass distinto del vecino). En cambio, generá un **noise field** con la misma `seed` de la isla y mapeá rangos del noise a "manchones dominantes". Así te queda:

```
[grass A] [grass A] [grass A] [grass A] [grass B] [grass B] [grass A]
[grass A] [grass A] [grass A] [grass B] [grass B] [grass B] [grass A]
```

en vez de:

```
[A] [B] [A] [C] [B] [A] [D] [B] [A] [C]
[B] [A] [C] [B] [D] [A] [B] [C] [A] [B]
```

### R7. El shore toca agua, no termina en vacío

En los bordes cardinales de la isla (N/S/E/O), el tile más externo de la dirt band debe **siempre** estar adyacente a un shore, que a su vez está adyacente al agua. Si por wobble queda un grass tocando agua directo, es un bug visual.

Mitigación: **post-procesado de costa**. Después de generar el terreno, recorrer los tiles con `getFieldItem()` y reemplazar cualquier grass adyacente a agua por shore/dirt.

---

## 4. Limitaciones hard de YurOTS 7.6

Aunque cumplas todas las reglas de arriba, hay límites que **no** podés pasar con el protocolo 7.6:

1. **Sin autotile real.** Los bordes entre bandas siempre serán líneas visibles. La única forma de disimular es **bandas anchas** (3+ tiles).
2. **Sin bordes con mask.** Tibia 10+ usa sprites con bordes que se interpolan. 7.6 no.
3. **Sin z-stacking para overlay.** No podés poner un "borde de agua" como item encima del grass (sería un item walkable raro que rompe pathing).
4. **Walls en la costa = bug visible.** Cualquier `TILE` con `count > 0` (un item encima) en la línea de costa se ve como un error. Mantener la línea de costa limpia (solo ground).

---

## 5. Tabla de referencia de IDs

| Familia | ID | Server name (aprox) | Uso | Tiles en mapa actual |
|---------|---:|--------------------|-----|---------------------:|
| Deep water | `4608` | water | Anillo externo | 912 |
| Shallow | `4691` | shallow water | Mezcla con deep | 255 |
| Deep variant | `4609` | water dark | Acento | 28 |
| Deep variant | `4610` | water darker | Acento | 21 |
| Deep variant | `4619` | water edge? | Borde | 6 |
| Shore | `4526` | sand light | Costa principal | 101 |
| Shore | `4566` | sand dark | Costa húmeda/sombra | 56 |
| Dirt | `103` | earth brown | Dirt principal | 188 |
| Dirt | `231` | dirt | Dirt alternativo | 132 |
| Dirt | `351` | mud | Manchón | 64 |
| Dirt | `352` | mud dark | Manchón | 58 |
| Dirt | `353-360` | mud variants | Detalles | 7-13 c/u |
| Grass | `101` | grass | Pasto principal | 1420 |
| Grass | `598` | grass dark | Pasto oscuro | 1149 |
| Grass | `919` | grass forest | Pasto bosque | 172 |
| Grass | `405` | grass jungle | Pasto selva | 171 |
| Grass | `407` | grass jungle dark | Pasto selva oscuro | 143 |
| Grass | `920` | grass variant | Detalle | 37 |
| Wood floor | `493` | wood floor | NO es tierra natural, no usar como dirt | 201 |
| Stone | `966` | cobblestone | Senderos internos | 49 |
| Cobble | `3263` | cobblestone gray | Senderos | 66 |
| Forest floor | `777` | forest floor | Anillo alrededor de árboles | 78 |

**Nota sobre `493`:** aparece en el mapa 201 veces pero es **wood floor** (un floor de casa), no tierra natural. No usar en islas.

**Nota sobre `966` / `3263` / `777`:** son útiles para **acento** — un sendero de cobble cruzando la isla, un anillo de forest floor alrededor de donde iría un árbol. No como banda principal.

---

## 6. Lo que el script actual hace mal

`scripts/generate-island.py` rev. jul 2026:

| Issue | Línea aprox | Detalle |
|-------|-------------|---------|
| Una sola variant de shore | `GROUND_SHORE = 4526` | Debería ser mezcla con `4566` |
| Una sola variant de dirt | `GROUND_DIRT = 231` | Debería ser mezcla con `103`, `351-360` |
| Solo 3 variants de grass | `GROUND_GRASS = (405, 598, 407)` | Faltan `101` (principal), `919`, `920` |
| Anillos perfectos | comparación `>` sobre `dist` | Sin wobble local por banda |
| Shore de 1 tile | `dist > 0.92` y `dist > 0.85` | Banda fina, debería ser `0.85-0.95` |
| Sin manchones de dirt en grass | no implementado | Debería haber ruido de dirt al 15% dentro del pasto |
| Sin post-procesado de costa | no implementado | grass adyacente a agua no se repara |
| Noise = random tile-a-tile | `rng.choice(GROUND_GRASS)` | Debería ser noise field con seed |

Cada issue por separado se ve "ok". Juntos producen la isla actual, que se ve **pintada con stencil** — visible sobre todo en el anillo de shore y en el corte circular grass→agua.

---

## 7. Cómo se ve una isla correcta (especificación)

Para una isla de radio 14 (default actual), el output ideal debería tener:

| Banda | Ancho radial | Tiles totales | Variants |
|-------|-------------:|--------------:|----------|
| Deep water | 1-2 tiles | ~120-180 | `4608` (95%) + `4691` (5%) |
| Shallow water | 1-2 tiles | ~100-140 | `4608`→`4691` invert |
| Shore | 2-3 tiles | ~140-200 | `4526` (70%) + `4566` (30%) |
| Dirt band | 1-2 tiles | ~80-120 | `103`/`231`/`351-360` + manchones |
| Grass interior | resto (~7-8 tiles) | ~250-350 | 6 variants, manchas con noise |
| **Total tiles** | radio 14 | ~700-900 | |

**Contraste con la isla actual generada** (centro 350,180,7, seed 42):
- 861 tiles totales
- 178 water + 683 land (sin distinción deep/shallow)
- Sin dirt band identificable
- Sin manchones

→ Está en el rango correcto de tamaño, pero la **composición** es la que falla.

---

## 8. Roadmap de fix (cuando se implemente)

Si en el futuro alguien toca `scripts/generate-island.py`, el orden sugerido es:

1. **Separar deep y shallow water** con un anillo intermedio y proporción invertida.
2. **Expandir shore a 2 variants** (`4526` + `4566`) con peso 70/30.
3. **Expandir dirt a 4-5 variants** (`103`, `231`, `351-360`).
4. **Aplicar wobble local por banda** (no solo en el borde externo).
5. **Implementar noise field** para los manchones de grass (reemplazar `random.choice`).
6. **Agregar manchones de dirt en grass** (15% del área de grass).
7. **Post-procesar costa** (reparar grass adyacente a agua → shore).
8. **Validar visualmente** con un test de humo: regenerar isla, abrir RME, ver si la transición agua/pasto se ve coherente.

Cada paso se puede hacer y commitear por separado. El estado actual del script (1 sola banda por familia, anillos perfectos) es el "piso" — todo lo de arriba son mejoras incrementales.

---

## 9. Validación manual recomendada

Después de regenerar una isla, abrir RME (`./scripts/open-rme.sh`) y revisar **a ojo**:

- [ ] ¿El anillo de shore tiene al menos 2 tiles de ancho en todas las direcciones?
- [ ] ¿Hay algún grass tocando agua directo? (Si sí, post-procesado falla)
- [ ] ¿El dirt se ve como anillo marcado o como manchones irregulares?
- [ ] ¿El grass interior tiene variación de tono o es plano?
- [ ] ¿Los bordes N/S/E/O de la isla se ven simétricos? (Si sí, falta wobble)
- [ ] ¿Hay zonas donde el agua se ve 100% uniforme? (Si sí, faltan variants de deep/shallow)

Si todos dan verde, la isla está bien compuesta.

---

## 10. Referencias cruzadas

- [MAPEAR_CON_CODIGO.md](MAPEAR_CON_CODIGO.md) — generador de islas actual, formato OTBM
- [IMPORTAR_ITEM_DESDE_IMAGEN.md](IMPORTAR_ITEM_DESDE_IMAGEN.md) — pipeline de items, contexto del `.dat`/`.spr`
- [SESION_EDITOR_MAPA_JUL2026.md](SESION_EDITOR_MAPA_JUL2026.md) — bitácora del editor, cambios de la última sesión
- `scripts/generate-island.py` — el script a modificar
- `server/YurOTS/ots/data/items/items.otb` — catálogo completo de grounds
- `server/YurOTS/ots/data/world/test.otbm` — mapa actual, fuente de los IDs validados visualmente

---

*Doc de especificación — no es un cambio de código todavía. Mientras nadie modifique el script, este archivo queda como referencia del comportamiento correcto esperado.*
