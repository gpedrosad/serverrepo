# Tres zonas de caza nuevas cerca de la city (nov 2026)

Tres dungeons generados por código alrededor y debajo de la ciudad para cubrir huecos de progresión y de Daily Tasks (`Rat`, `Giant Spider`, familia `Mutated`, `Beholder`/`Vampire Bride`/`Banshee`). Todos siguen las reglas de [ZONAS_DE_CAZA.md](ZONAS_DE_CAZA.md) y [PIEZAS_DE_MAPA.md](PIEZAS_DE_MAPA.md#cuevas) (bloques 2×2, pasillos largos en zigzag, separación 10–12, techo de roca sin vista al piso de arriba, decoración fija).

## Resumen

| Zona | Entrada | `/ir` (GM) | Pisos | Nivel | Casillas | Monstruos | Generador |
|---|---|---|---|---|---:|---|---|
| **Alcantarilla Profunda y Mutada** | `168,53,8` (dentro de las cloacas de `152,54,7`) | `/ir cloacas` | z9 (antesala), z10, z11 | 8–20 / 25–45 | 558 / 931 | Rat ×7, Cave Rat ×10, Slime ×3 (z10) · Mutated Human ×5, Mutated Rat ×5, Mutated Bat ×7, Mutated Tiger ×6, Bog Raider ×3 (z11) | `scripts/map/generate-mutated-sewers.py` |
| **Nido de Seda Negra** | `105,80,7` (camino suroeste, cartel `103,79,7`) | `/ir seda` | z8–z10 (pozo), z11 | 40–65 | 1.012 | Tarantula ×5, Poison Spider ×3, Giant Spider ×11, Wyvern ×3 | `scripts/map/generate-spider-nest.py` |
| **Cripta de los Ojos y Vampiros** | `78,34,7` (oeste del Castillo Imperial, cartel `77,34,7`) | `/ir ojos` | z8–z9 (acceso), z10 | 30–65 | 1.358 | Ghoul ×2, Gazer ×2, Beholder ×6, Crypt Shambler ×2, Vampire ×8, Elder Beholder ×4, Vampire Bride ×4, Banshee ×4 | `scripts/map/generate-beholder-crypt.py` |

## Conexiones (agujero `469` + escalera de mano `1386`)

En todos los enlaces se baja por agujero `469` y se sube con escalera de mano `1386` (aterriza en `x, y+1` del piso de arriba, siempre libre):

- **Alcantarilla Profunda:** `168,53` (z8→z9) · `166,51` (z9→z10) · `168,74` (z10→z11).
- **Nido de Seda Negra:** `105,80` (z7→z8) · `104,80` (z8→z9) · `105,80` (z9→z10) · `104,80` (z10→z11).
- **Cripta de los Ojos:** `78,34` (z7→z8) · corredor norte z8 hasta `78,24` (esquiva el Santuario Petrificado de z9 `y ≥ 28`) · `78,24` (z8→z9) · `77,23` (z9→z10).

## Regenerar y validar

```bash
python3 scripts/map/generate-mutated-sewers.py
python3 scripts/map/generate-spider-nest.py
python3 scripts/map/generate-beholder-crypt.py

python3 scripts/map/check-map-load.py
python3 scripts/map/check-upper-view.py --box 140 24 196 96 --z 9 10 11
python3 scripts/map/check-upper-view.py --box 70 74 142 140 --z 8 9 10 11
python3 scripts/map/check-upper-view.py --box 14 16 84 88 --z 8 9 10
python3 scripts/map/scan-map-depots.py server/YurOTS/ots/data/world/test.otbm
python3 scripts/map/sync-houses-with-map.py --dry-run
```

Manifiestos: `generated-mutated-sewers.json`, `generated-spider-nest.json` y `generated-beholder-crypt.json` en `server/YurOTS/ots/data/world/`. Bloques administrados en `test-spawn.xml` y `readables.xml`: `MUTATED_SEWERS_*`, `SPIDER_NEST_*` y `BEHOLDER_CRYPT_*`.
