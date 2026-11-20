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
| z7 | Islote: pasto con costa, campamento con fogata, barril y cajón | 5 Minotaur: 1 junto al puente, después de a 2 | 8–20 |
| z10 | Cueva del Minotauro | Minotaur → Minotaur y Archer → Archer y Guard al fondo (38) | 20–30 |
| z11 | Galerías | Guard y Archer → Guard, Archer y Mage → Guard y Mage (34) | 30–45 |
| z12 | Cámara del Rey | Guard y Mage de a 2 (42) | 45+ |

En cada cueva la dificultad sube con la distancia a la entrada; cada piso arranca más fuerte que el
anterior. Los spawns de cueva respawnean entre 60 y 90 s.

**Nov 2026, más espaciado y gradual:** antes el islote tenía 10 minotauros en 5 spawns a 4 casillas uno
de otro, al lado de los Mini Trainer Monk (`122–125, 55–57`), y z12 llegaba a 3 por spawn (194 en total).
Ahora son 119: máximo 2 por spawn, centros cada 5 casillas en el islote y 8–9 en las cuevas (`GAP`), nada
a menos de 3 casillas del puente, y cada tipo nuevo entra mezclado con el anterior (`STAGES`).

## Coordenadas

| Qué | Pos |
|-----|-----|
| Puente (piso de madera 405) | `113–114, 56–58, 7`, sale del muelle (fila 59) |
| Puente al Castillo (nov 2026) | `103–104, 48–50, 7`, a la isla del Castillo Imperial; lo arma `generate-bridge-tower.py` ([MAPEAR_TORRE_PUENTE.md](MAPEAR_TORRE_PUENTE.md)) |
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

## Techo (16 nov 2026)

La Cueva del Minotauro (z10) queda debajo de la vieja Arena PvP y z9 estaba vacío en parte: desde ~220
casillas se veían encima las cuevas de z8. Se puso roca en z9 donde no había nada con
`scripts/map/check-upper-view.py --fix` (este generador no escribe z9, así que el techo no se pierde al
regenerar). Ver [PIEZAS_DE_MAPA.md#techo](PIEZAS_DE_MAPA.md#techo).

## Regenerar

```bash
python3 scripts/map/generate-minotaur-isle.py --dry-run --png /tmp/islote.png   # valida y dibuja (y _z10/_z11/_z12)
python3 scripts/map/generate-minotaur-isle.py --spawns-only                      # solo spawns (no toca el mapa)
python3 scripts/map/generate-minotaur-isle.py --replace                          # escribe todo
python3 scripts/map/check-map-load.py                                            # que el server cargue el mapa
```

Determinista (`--seed`, por defecto 7) y re-ejecutable: reemplaza el rectángulo del islote, la caja de
las cuevas y los bloques de spawns y carteles.

**Ojo con `--replace` (nov 2026):** otra zona tiene paredes y una escalera de mano (`1385` en `140,28,10`)
en el borde este de la caja de las cuevas (x 139–140, y 25–30, z10); `--replace` las convierte en roca.
Para cambiar monstruos usar `--spawns-only`. Antes de un `--replace`, comparar el mapa antes y después.

Remates visuales del 20 nov: el muelle y el brazo al islote llevan barandas, faroles y rampa de madera propios, sin mover
el puente ni sus dos carriles ([TRANSICIONES_DEPOT.md](TRANSICIONES_DEPOT.md)). Si se regenera
el islote, reaplicar `python3 scripts/map/city-bridge-transitions.py` después.

Antes de deployar un `test.otbm` nuevo, probar depots in-game ([`../gameplay/DEPOTS.md`](../gameplay/DEPOTS.md)).
