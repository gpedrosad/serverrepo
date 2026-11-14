# Epstein Island — isla de caza larga (4 pisos)

Epstein Island es una isla de caza de nivel medio/alto con **cuatro pisos**: superficie z7, cuevas
z8, un piso z9 y un piso profundo z10. Las zonas son recorridos largos (pasillos + salas) para
poder cazar bastante. El barco ya no restringe el destino por vocación: cualquier jugador puede
viajar a `85,209,7`.

## Superficie (z7)

| Zona | Dónde | Monstruos |
|---|---|---|
| **Mutant Camp** | pasto oeste/sur, `x64-71, y207-216` | Mutated Human ×3, Blue Elf Arcanist ×2 |
| **Terror Bird Nest** | pasto norte, `x75-85, y187-198` | Terror Bird ×3, Dragon Hatchling ×1 |
| **Dragon Roost** | arena oeste, `x63-75, y191-204` | Dragon Hatchling ×2, Wyvern ×1 |

## Cuevas z8

| Cueva | Entrada | Monstruos |
|---|---|---|
| **Mutant Burrow** | agujero `82,190,7` | Mutated Rat ×2, Mutated Bat ×1 |
| **Drowned Grotto** | agujero `66,200,7` | Drowned Sailor ×4, Blue Elf Arcanist ×2 |
| **Wyvern Roost** | agujero `80,201,7` | Wyvern ×4, Dragon Hatchling ×2 |
| **Murius Den** | agujero `97,204,7` | Murius ×2, Mutated Bat ×4 |

## Piso z9

Cada cueva z8 baja a una zona z9 larga:

| Zona z9 | Bajo | Monstruos |
|---|---|---|
| **Mutated Tiger Den** | Drowned Grotto | Mutated Tiger ×3, Mutated Rat ×2 |
| **Tide Priest Sanctum** | Wyvern Roost | Tide Priest ×2, Drowned Sailor ×3 |
| **Bog Raider Bog** | Murius Den | Bog Raider ×3, Mutated Bat ×2 |

## Piso profundo z10

Cada zona z9 baja a una zona z10 más larga:

| Zona z10 | Bajo | Monstruos |
|---|---|---|
| **Deep Mutant Lab** | Mutated Tiger Den | Mutated Rat ×3, Mutated Bat ×3, Mutated Human ×3 |
| **Abyssal Grotto** | Tide Priest Sanctum | Tide Priest ×3, Drowned Sailor ×3 |
| **Bog Raider Queen** | Bog Raider Bog | Bog Raider ×3, Mutated Tiger ×2 |

> **Dificultad:** Bog Raider (1.300 HP, 800 exp, 110 de daño), Mutated Tiger (1.100 HP, 750 exp)
> y Murius (650 HP, 300 exp) son para personajes altos. El piso z10 está pensado para grupos.

## NPCs, tienda y Oracle

- Se sacaron **Nimral** (85,210,7), **The Oracle** y **Sally** (74,220,7).
- La tienda de Sally (x71-79, y217-223) se borró del mapa; quedó pasto.
- **The Oracle ya no existe en el juego.** Ojo: sin Oracle, un jugador con vocación 0 no puede
  elegir vocación (`promote.lua` también lo pide). Si querés conservar esa progresión, hay que
  volver a ponerlo en el templo o agregar otro método.
- En la llegada del barco, `85,210,7`, hay un **portal** al templo `130,53,6`.

## Generadores

```bash
# 1) limpieza de NPCs, tienda, Oracle y portal
python3 scripts/map/generate-epstein-cleanup.py --dry-run
python3 scripts/map/generate-epstein-cleanup.py

# 2) cuevas largas z8 + z9 + z10 (escribe generated-epstein-caves.json)
python3 scripts/map/generate-epstein-caves.py --dry-run --preview-dir /tmp/epstein
python3 scripts/map/generate-epstein-caves.py

# 3) spawns de todas las zonas (lee el manifiesto)
python3 scripts/map/generate-epstein-hunts.py --dry-run
python3 scripts/map/generate-epstein-hunts.py
```

Orden: cleanup → caves → hunts. El generador de hunts borra todos los spawns de la caja de
Epstein (z6-z10) y vuelve a colocar las zonas.

## Verificación

```bash
python3 scripts/map/check-map-load.py
python3 scripts/map/validate-tele-dest.py server/YurOTS/ots/data/world/test.otbm
python3 scripts/sync-houses-with-map.py --dry-run
```

Pendiente: prueba in-game del portal, de las escaleras/agujeros y del balance de z8/z9/z10.
