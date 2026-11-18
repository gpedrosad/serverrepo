# Cripta Imperial (túnel de caza bajo el pantano)

Zona de caza chica y directa en el pantano del suroeste, con la guarnición imperial del
[Castillo Imperial](../gameplay/IMPERIAL_CASTLE.md) — **sin variantes rage** (a pedido, nov 2026).
La boca original pedida (`94,86,7`) la tomó el Spot del Dragon Negro (plataforma del cazador
`93-95,85-87` + túnel z8 `94-103,84-87`); la cripta va **6 casillas al sur, en la orilla**:
plataforma de piedra `94,92,7` con la bajada y un cartel, cripta z8 debajo.

Generador: `python3 scripts/map/generate-imperial-crypt.py` (idempotente; `--dry-run --preview`
para mirar la forma antes de escribir). Manifiesto: `world/generated-imperial-crypt.json`.

## Boca y plataforma

- z7 `93–95, 91–93`: plataforma de piedra (`415`) en la orilla sur del pantano, con la bajada `432`
  en `94,92` y el cartel `1429` en `95,91` ("CRIPTA IMPERIAL").
- z8 `94,92`: piso de cueva + escalera de mano `1385`; se sale al sur (`94,93`), como todas las
  cuevas del valle (ver [ZONAS_DE_CAZA.md](ZONAS_DE_CAZA.md)).

## Recorrido y monstruos

Caja z8 `90–113 × 91–112`, zona cavable `92–109 × 92–108` (sin la lava del lago del sur). Recorrido
en U: fila norte `y93` (la boca cuelga de su borde oeste), bajada por `x92` y fila sur `y107` con la
sala final (`rooms_along`) — filas a 14 de eje. **228 casillas caminables**. Etapas por distancia
caminando desde la boca (`place_stages` + `slices_by`):

| Etapa | Monstruos | Por spawn | Spawntime |
|-------|-----------|-----------|-----------|
| 1 (entrada) | Imperial Squire / Imperial Archer | 1 | 100 s |
| 2 | Imperial Archer / Court Mage | 1 | 120 s |
| 3 | Court Mage / Imperial Hero | 2 | 170 s |
| 4 (fondo) | Imperial Hero | 2 | 235 s |

Da 4 spawns / 6 monstruos: **1 cada 38 casillas** (banda 33–50 de la receta). Nada a 6 casillas de
la escalera (`STAIR_CLEAR`).

## Convivencia con el dragon spot y qué pisa la caja

- Margen con su túnel: su piso más al sur es `y87`; el piso más al norte de la cripta, `y91` —
  3 filas de roca (la regla `CAVE_SEPARATION`) + su propia pared. El generador comparó el mapa
  tile por tile contra el deploy del dragon spot: **0 tiles suyos tocados** fuera de la caja.
- La caja solo pisa terreno sin uso (roca `101`, huecos vacíos y el borde de la lava del lago que
  nadie ve). El generador **excluye la lava del área cavable** y llena de roca los huecos vacíos a
  la vista del piso (156, mismo criterio que la Dark Cathedral: solo casillas sin tile).

## Validaciones del generador (falla → no escribe)

BFS desde la boca cubre el piso, escaleras pareja (432 arriba / 1385 abajo con salidas pisables),
piezas de pared exactas, nada de piezas cortadas del dragón (`CUT_DRAGON_PIECES`), sin huecos a la
vista (`grow(walk, 9)` con relleno de roca) y densidad mínima (1 cada 22 o peor → error).

Checks de siempre (corridos antes del deploy): `check-map-load` 0 errores, `check-upper-view` OK,
`scan-map-depots` 11 lockers `depotid=1`, `sync-houses --dry-run` OK, `validate-tele-dest` OK.

## Errores que ya pasaron

| Qué pasó | Cómo se evita |
|---|---|
| El relleno de roca pavimentó tiles existentes (el túnel del dragon spot, lava y corridor): `existing` se armó en `(x,y,z)` y se comparaba contra casillas 2D → nunca matcheaba y todo entraba como "hueco" | El relleno compara **en 2D del mismo piso** (`{(x,y)}` de z8); si el conteo de huecos se dispara, algo se está pisando — verificar contra el mapa anterior tile por tile |
