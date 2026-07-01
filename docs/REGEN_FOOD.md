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

`{thinkTicks, amount}` — ticks del game loop entre pulsos de regen.

- **Mana** (`manatickmul = 1`): `amount` = +mana que ve el jugador por pulso.
- **HP** (`healthtickmul = 5`): `amount × healthtickmul` = +vida en pantalla.

Think ≈ 1 s → tiempo entre pulsos ≈ `thinkTicks` segundos.

## Tablas por vocación

### Mana (manatickmul = 1 — el número del vector es lo que sube en pantalla)

Referencia **sorcerer**: free **+5**, premium **+8**, promoted+premium **+10**.  
Promotion sin premium: **+5** con ticks más rápidos (no más cantidad). Knight tope: **+7** (7/10 del sorc).

| Vocación | Free | Promoted (free) | Premium | Promoted+premium |
|----------|------|-----------------|---------|------------------|
| Sorcerer (1) | `{3,5}` | `{2,5}` | `{3,8}` | `{3,10}` |
| Druid (2) | `{3,5}` | `{2,5}` | `{3,8}` | `{3,10}` |
| Paladin (3) | `{4,5}` | `{3,5}` | `{3,8}` | `{3,10}` |
| Knight (4) | `{6,5}` | `{5,5}` | `{5,8}` | `{5,7}` |

### Health (sin cambio — healthtickmul = 5)

| Vocación | Free | Promoted (free) | Premium | Promoted+premium |
|----------|------|-----------------|---------|------------------|
| Sorcerer (1) | `{6,1}` | `{5,1}` | `{5,2}` | `{4,2}` |
| Druid (2) | `{6,1}` | `{5,1}` | `{5,2}` | `{4,2}` |
| Paladin (3) | `{4,1}` | `{3,1}` | `{3,2}` | `{2,2}` |
| Knight (4) | `{3,1}` | `{2,1}` | `{2,2}` | `{2,3}` |

## Ejemplo: Sorcerer comiendo (`manatickmul = 1`)

| Estado | Vector | Pulso | +Mana en pantalla | ~Mana/s |
|--------|--------|-------|-------------------|---------|
| Free | `{3,5}` | ~3 s | +5 | ~1.7 |
| Free + promotion | `{2,5}` | ~2 s | +5 | ~2.5 |
| Premium | `{3,8}` | ~3 s | +8 | ~2.7 |
| Premium + promotion | `{3,10}` | ~3 s | +10 | ~3.3 |

**Qué ve el jugador:** free +5 por pulso; premium +8; promotion+premium +10. Promotion sin premium regenera más seguido (+5 igual que free).

## Tuning mana 2026-07 (sorcerer 5 / 8 / 10)

Bajó la mana pasiva de magos (antes ~+15/pulso en premium+promo con `manatickmul=5`).  
`manatickmul` pasó a **1** solo para mana; HP sigue con `healthtickmul=5`.

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
manatickmul = 1   -- mana: el amount del vector es el +mana en pantalla
```

Para cambiar +5/+8/+10 del sorcerer hay que editar los vectores de **mana** en `player.cpp` y recompilar. HP no se toca.
