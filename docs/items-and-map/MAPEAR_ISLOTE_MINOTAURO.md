# Islote del Minotauro — caza para subir de nivel junto al muelle

Zona de caza de fácil acceso en plena ciudad (nov 2026): un islote en el canal entre el Castillo
Imperial y la isla de los elfos, unido al muelle por un puente de madera. Arriba hay minotauros
comunes; abajo, tres pisos de cueva con minotauros cada vez más fuertes.

Generador: `scripts/map/generate-minotaur-isle.py` (usa las cuevas, bordes y validaciones de
`generate-north-pass.py` y la escritura de `roomkit.py`). Manifiesto:
`server/YurOTS/ots/data/world/generated-minotaur-isle.json`.

## Recorrido

| Piso | Zona | Monstruos (local) | Nivel orientativo |
|------|------|-------------------|-------------------|
| z7 | Islote: pasto con costa, campamento con fogata, barril y cajón | 8 Minotaur, 2 Minotaur Archer | 8–20 |
| z10 | Cueva del Minotauro | Minotaur y Archer cerca de la entrada → Guard al fondo (52) | 20–30 |
| z11 | Galerías | Guard y Archer → Guard y Mage (48) | 30–45 |
| z12 | Cámara del Rey | Guard y Mage, 2 y después 3 por spawn (71) | 45+ |

En cada cueva la dificultad sube con la distancia a la entrada; cada piso arranca más fuerte que el
anterior. Los spawns de cueva respawnean entre 60 y 90 s.

## Coordenadas

| Qué | Pos |
|-----|-----|
| Puente (piso de madera 405) | `113–114, 56–58, 7`, sale del muelle (fila 59) |
| Entrada de la cueva (portal) | `100, 53, 7` → `108, 53, 10` |
| Vuelta (al lado de la llegada en z10) | `109, 53, 10` → `102, 53, 7` |
| Escalera z10 → z11 | `128, 41` |
| Escalera z11 → z12 | `99, 38` |
| Portal final (fondo de z12) | `125, 64, 12` → `102, 53, 7` |
| Caja | z7 `97–120, 49–58`; z10–z12 `80–140, 24–80` |

Cartel en `readables.xml` (bloque `MINOTAUR_ISLE_SIGNS`); spawns en `test-spawn.xml` (bloque
`MINOTAUR_ISLE_SPAWNS`).

## Por qué así

- **Lava:** al oeste del canal hay un campo de lava. El islote empieza en x 100 y el validador exige
  que desde ninguna casilla caminable del islote ni del puente entre lava en pantalla (±9, ±7).
- **Portal y no escalera:** bajo el canal, z8 y z9 ya tienen las cuevas de rotworms y otras zonas.
  Se baja por portal a z10 (vacío) y de ahí por escaleras reales a z11 y z12.
- **Costa:** las piezas de orilla (`4644–4655`, pasto con borde sobre agua) son las medidas en la costa
  del canal y **bloquean el paso**: el islote se achica hasta que cada casilla de costa tenga una sola
  pieza. El puente entra una casilla al islote para que su punta no sea costa.
- **Muelle:** el borde norte del muelle (`434/442/443` sobre agua) bloquea; bajo el puente se
  reemplaza por piso `405`. Las otras casillas del muelle quedan igual.

## Reglas que valida el script (si algo falla no escribe nada)

- El rectángulo del islote es agua (o lo generó este script antes: existe el manifiesto).
- Costa con una sola pieza por casilla.
- Del puente se llega a la plaza del templo (`164,48,7`), a la entrada de la cueva y a todo el islote.
- Sin lava a la vista desde el islote y el puente.
- Cuevas: escaleras y portales alcanzables, paredes con pieza única, sin ver el borde negro; la caja
  de z10–z12 estaba vacía.
- Todos los monstruos existen en `monsters.xml`.

## Regenerar

```bash
python3 scripts/map/generate-minotaur-isle.py --dry-run --png /tmp/islote.png   # valida y dibuja (y _z10/_z11/_z12)
python3 scripts/map/generate-minotaur-isle.py --replace                          # escribe
python3 scripts/map/check-map-load.py                                            # que el server cargue el mapa
```

Determinista (`--seed`, por defecto 7) y re-ejecutable: reemplaza el rectángulo del islote, la caja de
las cuevas y los bloques de spawns y carteles.

Antes de deployar un `test.otbm` nuevo, probar depots in-game ([`../gameplay/DEPOTS.md`](../gameplay/DEPOTS.md)).
