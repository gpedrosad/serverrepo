# Arena de Fosos — estilo Svargrond (8.x), lógica Retro76

Cadena de **10 pits** con 1 boss cada uno, 3 dificultades con fee, timer 6 min/pit, y sala de premios con **3 cofres (elegís uno)**.

Inspirado en la [Svargrond Arena / Barbarian Arena Quest](https://tibia.fandom.com/wiki/Svargrond_Arena) (Tibia 8.0+), **no** en el Arena Quarter de Yalahar (ese es hunt).

| Sistema | Portal templo |
|---------|----------------|
| El Crisol | `157, 54, 7` |
| Wave Arena | `159, 54, 7` |
| Hunt maze | `160, 54, 7` |
| **Arena de Fosos** | `161, 54, 7` |
| Reloj de Arena | `166, 54, 7` |
| Floor campus | `162, 54, 7` |

Retorno al templo: `163, 54, 7`. Cartel `1433` en `161, 53, 7`.

---

## Layout (simple, 2 z)

| Z | Rol |
|---|-----|
| **z6** | Todo el gameplay: lobby + 10 pits + reward |
| **z5** | Fondo neutro (`GROUND_BG` 405) bajo el footprint — sin mecánicas |

No se mezclan floors de pits (no hay torre). Un solo piso jugable.

```
Templo 161,54,7
    → Lobby z6 (palancas dificultad)
         → Pit1 → Pit2 → … → Pit10  (fila este)
         → Reward (sur del lobby): muro + showcases / cofres
    → TP salida → 163,54,7
```

---

## Flujo

1. TP `161, 54, 7` → lobby `205, 396, 6`.
2. Palanca **Info** `7303`: reglas + si está ocupada.
3. Elegí dificultad (cobra gold):
   - **Greenhorn** `7300` — 1.000 gp  
   - **Scrapper** `7301` — 5.000 gp  
   - **Warlord** `7302` — 10.000 gp  
4. Entrás a **Pit 1** con 1 boss. Matálo.
5. Palanca **Next** `7304` (en cada pit): si limpio y dentro de 6 min → siguiente pit.
6. Palanca **Forfeit** `7305`: te manda al templo; hay que pagar de nuevo.
7. Tras Pit 10 + Next → sala de premios. **Abrí un solo cofre**.
8. TP sur de la sala → templo `163, 54, 7`.

Una corrida a la vez (owner lock, como Wave/Crisol).

---

## Timer

- **360 s (6 min)** por pit, desde que entrás.
- Se chequea al usar **Next** (`os.time()`; no hay `addEvent` Lua en YurOTS).
- Si se vence: kick al templo y se resetea la corrida.

---

## Bosses (existentes en `monsters.xml`)

| Pit | Greenhorn | Scrapper | Warlord |
|-----|-----------|----------|---------|
| 1 | Rat | Amazon | Black Knight |
| 2 | Wolf | Valkyrie | Dragon |
| 3 | Bear | Cyclops | Hero |
| 4 | Orc | Dwarf Guard | Necromancer |
| 5 | Amazon | Minotaur Guard | Priestess |
| 6 | Valkyrie | Black Knight | Dragon Lord |
| 7 | Cyclops | Giant Spider | Warlock |
| 8 | Dwarf Guard | Dragon | Hydra |
| 9 | Minotaur Guard | Hero | Behemoth |
| 10 | Giant Spider | Necromancer | Demon |

---

## Reward (3 cofres, 1 elección)

Cofres uid `7310` / `7311` / `7312` en `y=407`.  
**Solo uno** por dificultad, **una vez** (storage). Si ya reclamaste esa dificultad: “Ya elegiste premio…”.

| Cofre | Greenhorn | Scrapper | Warlord |
|-------|-----------|----------|---------|
| A `7310` | crystal coin `2160` | magic sword `2400` | demon helmet `2493` |
| B `7311` | fire sword `2392` | magic plate armor `2472` | demon shield `2520` |
| C `7312` | knight armor `2476` | boots of haste `2195` | great axe `2415` |

### Showcase (sin acceso)

- Items de **referencia Greenhorn** en `y=404` (1 sqm al norte de los cofres).
- Fila de muro `1036` en `y=405` → el jugador en la sala (`y≥406`) **no puede pisar** el showcase.
- Los premios reales Scrapper/Warlord están en la tabla de arriba / palanca Info (el mapa no cambia sprites por dificultad).

---

## Storages

| Key | Uso |
|-----|-----|
| `9410` | Claim Greenhorn (1 = ya cobró) |
| `9411` | Claim Scrapper |
| `9412` | Claim Warlord |
| `9413` | Dificultad de la corrida actual |
| `9414` | `1` = puede abrir cofre (llegó al reward) |

---

## Archivos

| Archivo | Rol |
|---------|-----|
| [`scripts/map/generate-svar-arena.py`](../../scripts/map/generate-svar-arena.py) | OTBM + cartel + manifiesto |
| Symlink `scripts/generate-svar-arena.py` | Compat |
| `data/actions/scripts/svar_arena.lua` | Lógica |
| `data/actions/actions.xml` | uids `7300–7305`, `7310–7312` |
| `data/world/generated-svar-arena.json` | Manifiesto |
| `data/readables.xml` | Bloque `SVAR_ARENA_SIGNS` |

---

## Regenerar mapa

```bash
python3 scripts/map/generate-svar-arena.py --dry-run
python3 scripts/map/generate-svar-arena.py --replace
```

Tras solo cambios Lua/XML: restart del OT (sin regenerar OTBM).

**Deploy mapa:** probar depot temple in-game antes (`docs/gameplay/DEPOTS.md`).

---

## Probar

```
/pos 161 54 7
# Info → reglas
# Greenhorn (tener 1000 gp) → Pit 1
# matar → Next → … → Pit 10 → Next → reward
# abrir UN cofre → TP sur
```

Relacionado: [`WAVE_ARENA.md`](WAVE_ARENA.md), [`CRUCIBLE.md`](CRUCIBLE.md), [`../CAMBIAR-MAPA.md`](../CAMBIAR-MAPA.md).
