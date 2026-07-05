# Rate de Magic Level (manamul)

## Cambio 2026-07-04

| | Antes | Ahora |
|---|-------|-------|
| `manamul` (todas las voc) | **×5** | **×3** |
| ML free efectivo | ×5 | ×3 |
| ML premium efectivo (`premmyskillmul` ×2) | ×10 | ×6 |
| Regen de mana al comer | sin cambio | sin cambio |
| Skills (`weaponmul`, etc.) | ×4 | sin cambio |

**Motivo:** el ML subía demasiado rápido respecto al ritmo del server (spam de curas, conjurar en PZ, hunt). La regen de mana se mantiene igual; solo baja cuánto ML cuenta cada punto de mana gastado.

**Estado:** aplicado en `config.lua` y `OTINFO`. Requiere **restart del OT** (local o VPS) para entrar en vivo.

**Contexto exp:** en jul 2026 también se bajaron los tramos altos de exp (71–100 ×2, 101+ ×1). Ver [`EXP_RATE.md`](EXP_RATE.md).

## Config

```lua
-- server/YurOTS/ots/config.lua
manamul = {"3", "3", "3", "3", "3"}   -- {no-voc, sorcerer, druid, paladin, knight}
premmyskillmul = 2                     -- sin cambio; premium sigue ×2 sobre manamul
```

`manamul` se carga al arrancar el binario desde `config.lua` (`luascript.cpp` → `Player::addManaSpent`). No requiere recompilar.

## Qué cuenta para ML

Cada mana gastada suma `manamul` (× premium si aplica) al progreso:

- Hechizos ofensivos y curas
- Conjurar runas en PZ
- Wands/rods (si están habilitados)

**No** depende de: `manatickmul`, `healthtickmul`, vectores de regen en `player.cpp`.

## Tiempos orientativos (sorcerer, spam `exura` 25 mana, exhaust 1 s)

| Objetivo | ×5 (antes) free | ×3 (ahora) free | ×3 premium |
|----------|-----------------|-----------------|------------|
| 0 → ML 10 | ~1 min | ~2 min | ~1 min |
| 0 → ML 20 | ~3 min | ~5 min | ~2 min |
| 0 → ML 30 | ~9 min | ~15 min | ~7 min |
| 0 → ML 50 | ~1 h | ~1.7 h | ~50 min |

RL Tibia (×1): 0 → ML 30 ≈ 45 min con el mismo método.

## Alternativas consideradas

| manamul | Efecto vs ×5 anterior | Notas |
|---------|-------------------------|--------|
| 4 | ~20% más lento | Alineado con skills ×4; cambio suave |
| **3** | **~40% más lento** | **Elegido — punto intermedio** |
| 2 | ~2.5× más lento | Nerfeo fuerte |
| 1 | ×5 más lento (= RL ML) | Muy lento para server con exp ×2–5 en tramos altos |

## Deploy

Solo datos; no hace falta rebuild del binario:

```bash
# En VPS, tras sync del repo o copiar config.lua
docker compose -f docker-compose.prod.yml restart yurots
```

Actualizar también la web/OTINFO pública si muestra rates (`OTINFO` ya actualizado en repo).

## Archivos

- `server/YurOTS/ots/config.lua` — `manamul`
- `server/YurOTS/ots/source/player.cpp` — `addManaSpent()`, `getReqMana()`
- `OTINFO` — rates públicos in-game / referencia staff
