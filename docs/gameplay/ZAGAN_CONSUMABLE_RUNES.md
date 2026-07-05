# Runas consumibles Zagan (20131, 20132)

Items custom del pack Zagan con acción **Use** en inventario. Requieren `items-zagan-test.otb` y reinicio del OT (Lua/XML al boot; **experience recovery rune** además necesita rebuild C++ por `doPlayerAddExp` y storage en muerte).

---

## Resumen

| Item ID | Nombre en juego | Efecto al usar | Límite | Se consume |
|---------|-----------------|----------------|--------|------------|
| `20131` | **experience recovery rune** | Recupera **60–80%** de la exp perdida en la **última muerte** | Una runa por muerte (storage se limpia al usar) | Sí |
| `20132` | **training extension rune** | **+12 horas** de tiempo de training **ese día** | Una vez por personaje por día | Sí |

---

## 20131 — experience recovery rune

Recupera experiencia perdida al morir. Nombre anterior de desarrollo: *voidscript rune*.

### Comportamiento

1. Al **morir**, el servidor guarda en storage `9110` la exp que vas a perder (`getLostExperience()`, hoy **7%** del total según `diepercent` en `config.lua`).
2. Al usar la runa:
   - Lee storage `9110`.
   - Si no hay exp guardada → mensaje de error, no consume la rune.
   - Si hay → restaura un **porcentaje aleatorio entre 60% y 80%** (entero, piso).
   - Pone storage `9110` en `0`.
   - Consume 1 runa.

### Mensajes (inglés, en juego)

- Éxito: `You recovered X experience (Y% of your last death).`
- Sin exp: `This rune has no death experience to restore.`
- Exp muy baja: `The lost experience is too small to recover.`

### Archivos

| Archivo | Rol |
|---------|-----|
| `server/YurOTS/ots/data/actions/scripts/experience_recovery_rune.lua` | Lógica de uso |
| `server/YurOTS/ots/data/actions/actions.xml` | `<action itemid="20131" …>` |
| `server/YurOTS/ots/source/player.cpp` | Guarda exp perdida en `die()` y `preSave()` |
| `server/YurOTS/ots/source/actions.cpp` | Lua `doPlayerAddExp` |
| `server/YurOTS/ots/data/items/items-zagan-test.xml` | Nombre del item |

### Storages

| Key | Uso |
|-----|-----|
| `9110` | Exp perdida en la última muerte (0 después de usar la runa) |

### Cómo probar

1. Personaje con exp; morir (PvE o PvP).
2. Verificar en XML del player `<storage><data key="9110" value="…"/>`.
3. Usar experience recovery rune → sube exp, mensaje con % y cantidad, runa desaparece.
4. Volver a usar otra runa sin morir de nuevo → “no death experience”.

### Notas

- Cada **nueva muerte** sobrescribe `9110` con la exp perdida de esa muerte.
- No recupera skills ni magic level; solo **experience**.
- Requiere **recompilar** el binario por cambios en `player.cpp` y `actions.cpp`.

---

## 20132 — training extension rune

Extiende el límite diario de training. Nombre anterior de desarrollo: *deathpeal rune*.

### Comportamiento

1. Al usar la runa (desde inventario, cualquier lugar):
   - Si ya usaste una **training extension rune hoy** → no suma más, no consume otra.
   - Si no → suma **720 minutos** al bonus diario de training y consume la runa.
2. El bonus se suma al límite del día junto con el base (`trainingdailyminutes` / `trainingpremiumminutes`) y con otros bonus del mismo sistema (p. ej. parchment `1953` en mapa).

### Mensajes (inglés, en juego)

- Éxito: `The training extension rune grants you +12 hours of training time for today.`
- Ya usada hoy: `This training extension rune is spent. You already received +12 hours of training today.`

### Archivos

| Archivo | Rol |
|---------|-----|
| `server/YurOTS/ots/data/actions/scripts/training_extension_rune.lua` | Lógica de uso |
| `server/YurOTS/ots/data/actions/actions.xml` | `<action itemid="20132" …>` |
| `server/YurOTS/ots/source/player.cpp` | `getTrainingDailyLimitMs()` suma bonus de storages `9102`/`9103` |
| `server/YurOTS/ots/data/items/items-zagan-test.xml` | Nombre del item |

### Storages (training bonus compartido)

| Key | Uso |
|-----|-----|
| `9100` | Fecha del día de training (uso acumulado) |
| `9101` | Ms usados hoy en training zone |
| `9102` | Fecha del bonus extra activo |
| `9103` | **Minutos extra** sumados al límite diario (parchment + runas, etc.) |
| `9104` | Fecha en que se usó **training extension rune** (anti doble uso del item 20132) |

### Límite diario efectivo

```
límite_hoy = base_minutos + bonus_minutos(9103 si 9102 == hoy)
```

- Base: `120` min (free) / `360` min (premium) — `config.lua` `trainingdailyminutes` / `trainingpremiumminutes`.
- Parchment `1953` en `135 130 9`: +300 min (5 h), 1×/día — ver [`TRAINING_BONUS_PARCHMENT.md`](TRAINING_BONUS_PARCHMENT.md).
- Training extension rune `20132`: +720 min (12 h), 1×/día **por personaje** (independiente del parchment; **se acumulan** si usas ambos el mismo día).

### Cómo probar

1. Usar training extension rune → mensaje +12 h, item consumido.
2. Entrar a training zone → mensaje de entrada con límite = base + 720 (± parchment si aplica).
3. Usar otra training extension rune el mismo día → mensaje “already received”.
4. Al día siguiente → vuelve a funcionar.

### Notas

- Solo Lua + XML; **no** requiere recompilar C++ (el motor de training bonus ya existía).
- Si cambias los minutos, edita `BONUS_MINUTES` en `training_extension_rune.lua`.

---

## Despliegue

1. Cambios solo Lua/XML: reiniciar OT.
2. Si tocaste `player.cpp` / `actions.cpp` (experience recovery rune): `make` en el container y reiniciar `yurots`.
3. Servidor debe cargar `items-zagan-test.otb` / `items-zagan-test.xml` (entorno Zagan / test map).
4. Si regenerás assets Zagan: `python3 scripts/build_zagan_test_assets.py` + `./scripts/install-zagan-test-env.sh` para nombres en OTB/cliente.

---

## Referencias

- Training diario: [`docs/features/01-training-daily-system.md`](../features/01-training-daily-system.md)
- Parchment +5 h: [`TRAINING_BONUS_PARCHMENT.md`](TRAINING_BONUS_PARCHMENT.md)
- Items Zagan: [`docs/items-and-map/ZAGAN_TEST_ITEMS.md`](../items-and-map/ZAGAN_TEST_ITEMS.md)
- `zagan-test/manifest.json` — ids `20131`, `20132`
