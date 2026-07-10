# Anchor Rune (2296)

Root momentáneo de **1 segundo**. No es paralyze: no usa `ATTACK_PARALYZE`, no pone el icono de paralyze y no baja la speed del target.

## Efecto

- Al usar la rune sobre un creature: el target no puede caminar ni ser pusheado por **1000 ms**.
- Puede seguir atacando, casteando y usando items.
- Visual: hit `NM_ME_MAGIC_ENERGIE` (sin icono de paralyze).
- Mensaje al target: `You are rooted.`

## Uso en war

- Cortar un escape corto sin el lock injusto de paralyze.
- Setup de combos coordinados (SD / explosion / melee).

## Reglas

| Caso | Resultado |
|------|-----------|
| Sin creature en el tile | Puff en caster, **no** consume carga |
| Otro piso / sin línea de tiro | Cancel, no consume |
| Caster o target en PZ | Cancel (mismo criterio ofensivo) |
| Target GM (`ACCESS_PROTECT`) | No aplica |
| Self-target | No aplica |
| Hit PvP válido | Consume 1 carga, marca fight/pzLocked |

## Balance actual

| Campo | Valor |
|-------|-------|
| Item id | `2296` |
| Charges (store) | `3` (crafted: +3 → 6) |
| Magic level | `8` |
| Duración root | `1000` ms |

## Archivos

| Archivo | Rol |
|---------|-----|
| `server/YurOTS/ots/data/spells/runes/anchor.lua` | Script de la rune |
| `server/YurOTS/ots/data/spells/spells.xml` | Registro `Anchor` id 2296 |
| `server/YurOTS/ots/source/spells.cpp` | `doAnchorRoot` / `luaActionDoAnchorRoot` |
| `server/YurOTS/ots/source/creature.h` | `rootTicks` |
| `server/YurOTS/ots/source/game.cpp` | Bloqueo en `onPrepareMoveCreature` + tick decay |

## Cómo probar

1. Rebuild C++ (`make clean && make` — se tocó `creature.h`).
2. Reiniciar `yurots` + `python3 scripts/ot-probe.py 127.0.0.1 7171`.
3. Dar rune: `/i 2296` (o crear item con charges).
4. Usar sobre otro player: no puede moverse ~1 s; no aparece icono de paralyze.
5. Tras 1 s vuelve a caminar normal.

## Notas

- Distinto de Paralyze rune (`2278`) / Medusa sword: esos usan condition `ATTACK_PARALYZE` + speed baja.
- Requiere **recompilar** el binario.
