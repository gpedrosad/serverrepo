# Regen de HP/Mana al comer — 4 tiers (free, promoted, premium, promoted+premium)

## Resumen

La regeneración pasiva (comiendo, fuera de PZ) usa **cuatro escalones** según cuenta y promotion de Orlan:

| Tier | Requisitos | Qué mejora |
|------|------------|------------|
| 1 — Free | Sin premium ni promotion | Base |
| 2 — Promoted | Promotion de Orlan (lvl 20, 20k gp) | Ticks más rápidos |
| 3 — Premium | Cuenta premium activa | Cantidad por pulso mayor |
| 4 — Advanced | Premium **y** promotion | Cantidad máxima (tope moderado) |

**Promotion es para free y premium.** Premium sigue valiendo por regen más fuerte, exp, training, outfits, etc.

## Lógica en código

`Player::gainManaTick()` y `Player::gainHealthTick()` (`server/YurOTS/ots/source/player.cpp`):

```cpp
if (promoted) {
    if (isPremium())     // tier 4 — advancedGain*
    else                 // tier 2 — promotedGain*
} else if (isPremium())   // tier 3 — premiumGain*
else                      // tier 1 — gain*
```

- `isPromoted()` = flag `promoted` (permanente tras pagar a Orlan).
- `promote()` siempre activa el flag (sin requerir premium).

## Formato de vectores

`{thinkTicks, amount}` — ticks del game loop entre pulsos de regen; `amount` es HP/mana **antes** de `healthtickmul` / `manatickmul` (default **5** en `config.lua`).

Think ≈ 1 s → tiempo entre pulsos ≈ `thinkTicks` segundos.  
Mana/s efectiva ≈ `(amount × manatickmul) / thinkTicks`.

## Tablas por vocación

### Mana

| Vocación | Free | Promoted (free) | Premium | Promoted+premium |
|----------|------|-----------------|---------|------------------|
| Sorcerer (1) | `{3,1}` | `{2,1}` | `{2,2}` | `{2,3}` |
| Druid (2) | `{3,1}` | `{2,1}` | `{2,2}` | `{2,3}` |
| Paladin (3) | `{4,1}` | `{3,1}` | `{2,2}` | `{2,3}` |
| Knight (4) | `{6,1}` | `{5,1}` | `{5,2}` | `{4,2}` |

### Health

| Vocación | Free | Promoted (free) | Premium | Promoted+premium |
|----------|------|-----------------|---------|------------------|
| Sorcerer (1) | `{6,1}` | `{5,1}` | `{5,2}` | `{4,2}` |
| Druid (2) | `{6,1}` | `{5,1}` | `{5,2}` | `{4,2}` |
| Paladin (3) | `{4,1}` | `{3,1}` | `{3,2}` | `{2,2}` |
| Knight (4) | `{3,1}` | `{2,1}` | `{2,2}` | `{2,3}` |

## Ejemplo: Sorcerer comiendo (`manatickmul = 5`)

| Estado | Vector | Pulso | +Mana en pantalla | ~Mana/s |
|--------|--------|-------|-------------------|---------|
| Free | `{3,1}` | ~3 s | +5 | ~1.7 |
| Free + promotion | `{2,1}` | ~2 s | +5 | ~2.5 |
| Premium | `{2,2}` | ~2 s | +10 | ~5.0 |
| Premium + promotion | `{2,3}` | ~2 s | +15 | ~7.5 |

**Qué ve el jugador:** promotion = regenera más seguido; premium = números más grandes; ambos = mejor tope sin el salto extremo del sistema anterior (`{1,2}` → ~10 mana/s).

## Orlan (`data/npc/scripts/promote.lua`)

- **Level 20** + **20,000 gp** — cualquier cuenta.
- Sin requisito de premium.
- Diálogo en inglés; `help` menciona que premium mejora el regen en https://retro76.cl

## Cambio 2026-07-01 (4 tiers)

Antes: solo 3 tiers; `isPromoted()` exigía premium → free con promotion no ganaba regen.  
Ahora: 4 tiers escalonados; premium sin promotion gana más que antes; promoted+premium un poco menos extremo que `{1,2}`.

## Archivos

- `server/YurOTS/ots/source/player.cpp` — vectores y `gain*Tick()`
- `server/YurOTS/ots/source/player.h` — `isPromoted()`, `promote()`
- `server/YurOTS/ots/source/commands.cpp` — `/promote` sin check premium
- `server/YurOTS/ots/data/npc/scripts/promote.lua` — Orlan
- `OTINFO` — reglas públicas

## Tuning

Los multiplicadores globales en `config.lua` afectan todos los tiers por igual:

```lua
healthtickmul = 5
manatickmul = 5
```

Para cambiar la diferencia entre tiers hay que editar los vectores en `player.cpp` y recompilar.
