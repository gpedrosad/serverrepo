# Catalogo de features para traspasar

## Objetivo

Este catalogo divide las features importantes del server en fichas individuales, una por archivo, para que sea facil decidir cuales queremos portar a otro proyecto.

Cada ficha intenta responder lo mismo:

- que hace la feature
- por que valio la pena
- que conviene conservar al migrarla
- que riesgos hay
- donde esta implementada hoy

## Como usarlo

1. Leer esta tabla.
2. Abrir solo las fichas que tengan mas valor o mejor portabilidad.
3. Marcar que se porta completo, que se adapta y que se descarta.

## Fichas disponibles

| ID | Feature | Categoria | Valor | Portabilidad | Ficha |
|----|---------|-----------|-------|--------------|-------|
| 01 | Training diario controlado | Training | Alta | Alta | [01-training-daily-system](features/01-training-daily-system.md) |
| 02 | No PvP dentro de training | Training / PvP | Alta | Alta | [02-training-no-pvp](features/02-training-no-pvp.md) |
| 03 | Parchment de bonus de training | Training / Eventos | Media | Alta | [03-training-bonus-parchment](features/03-training-bonus-parchment.md) |
| 04 | Bounty / Most Wanted | PvP / Social | Alta | Media | [04-bounty-most-wanted](features/04-bounty-most-wanted.md) |
| 05 | Confirmacion universal en NPCs | UX / NPCs | Alta | Alta | [05-npc-transaction-confirmation](features/05-npc-transaction-confirmation.md) |
| 06 | Economia apoyada en banco | Economia | Alta | Media | [06-bank-backed-economy](features/06-bank-backed-economy.md) |
| 07 | Seller: packs de fluids y venta de vials | NPCs / Economia | Alta | Alta | [07-seller-fluid-packs-and-vials](features/07-seller-fluid-packs-and-vials.md) |
| 08 | Dark Rodo: backpacks de runas | NPCs / Economia | Media | Alta | [08-rune-backpacks-dark-rodo](features/08-rune-backpacks-dark-rodo.md) |
| 09 | Rage monsters | PvE / Loot | Alta | Media | [09-rage-monsters](features/09-rage-monsters.md) |
| 10 | Gemas e imbuements | Progresion | Alta | Media | [10-gems-and-imbuements](features/10-gems-and-imbuements.md) |
| 11 | Premium y promotion con perks reales | Monetizacion / Progresion | Media | Media | [11-premium-and-promotion](features/11-premium-and-promotion.md) |
| 12 | Soft Boots con regen y desgaste real | Items / QoL | Media | Alta | [12-soft-boots](features/12-soft-boots.md) |
| 13 | Peso de runas tipo RL | Retro QoL | Media | Alta | [13-rune-weight-rl](features/13-rune-weight-rl.md) |
| 14 | Visibilidad correcta del casteo | Combate / UX | Media | Alta | [14-spell-cast-visibility](features/14-spell-cast-visibility.md) |
| 15 | Spell custom exori gran | Combate / Vocaciones | Media | Alta | [15-exori-gran](features/15-exori-gran.md) |
| 16 | Apertura de utility spells clave | Retro QoL / Vocaciones | Media | Alta | [16-utility-spell-access](features/16-utility-spell-access.md) |

## Orden sugerido para evaluar portado

Si hubiera que elegir rapido, empezaria por este orden:

1. `05` Confirmacion universal en NPCs
2. `01` Training diario controlado
3. `02` No PvP dentro de training
4. `06` Economia apoyada en banco
5. `09` Rage monsters
6. `10` Gemas e imbuements
7. `04` Bounty / Most Wanted
8. `07` Seller: packs de fluids y venta de vials
9. `12` Soft Boots
10. `13` Peso de runas tipo RL
11. `14` Visibilidad correcta del casteo
12. `15` Spell custom exori gran
13. `16` Apertura de utility spells clave
14. `03` Parchment de bonus de training
15. `08` Backpacks de runas
16. `11` Premium y promotion con perks reales

## Documento puente

Para una version mas narrativa y menos dividida, ver tambien:

- [docs/MIGRATION_PLAYBOOK.md](MIGRATION_PLAYBOOK.md)
