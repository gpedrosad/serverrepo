# Puente principal — Ironbound (23 nov 2026)

Puente elevado de la ciudad: **141,65,6**, tablero x140–142, y57–75. Es el puente
principal documentado en [PIEZAS_DE_MAPA.md](PIEZAS_DE_MAPA.md#puente-de-madera-elevado-z6).

La estética cambia de madera a **basalto oscuro, hierro, remates de piedra clara y
bronce**, con balizas ámbar. Los dos segmentos angostos llevan inlays de bronce y
bandas de umbral: se distinguen las plataformas y los lugares de trap sin poner
obstáculos ni decoración encima del paso. Los ocho apoyos de madera pasan a pilares
de basalto con abrazaderas de bronce. Todo el arte se construye con el modelo 3D
nativo del puente, sin cambiar sprites de otros muelles ni puentes.

![Antes y después con sprites nativos](img/main-bridge/comparison.png)

Es una vista previa fuera del juego, con mapa y assets reales de cada versión.

## PvP conservado

- **41 casillas transitables**, idénticas a la versión anterior.
- Dos pasos de **1 sqm**, x141 en **y62–65** y **y68–71**; las plataformas siguen
  teniendo 3 casillas de ancho. Cada una de las ocho casillas angostas sigue
  cortando la conexión norte-sur al ocuparla un jugador, incluso con diagonales.
- Mismas **50 anclas de baranda**, sin suelo, y mismos flags de bloqueo y proyectiles.
- **Cuatro trampillas 429** y sus llegadas conservadas. No se cubren con decoración:
  así mantienen su dibujo reconocible y el click derecho sobre la trampilla nativa.
- Mismas posiciones y colisión de los **ocho pilares en z7**.
- El suelo base 405 se conserva bajo un pavimento decorativo no bloqueante:
  velocidad, niveles, rutas, colocación de fields y el combate conservan sus bases.

## Scripts y recursos

| Archivo | Función |
|---|---|
| `scripts/client-rme/city_bridge_z6_art.py` | Contorno 3D, anclas originales fijas y reparto de piezas de 64×64; caché de piezas para el instalador. |
| `scripts/client-rme/ironbound_bridge_material.py` | Basalto, mampostería, hierro/bronce y balizas. Carga una copia privada del renderizador de madera: no modifica su paleta global. |
| `scripts/client-rme/ironbound_bridge_deck.py` | 16 pavimentos de 32×32 con bordes y marcas; pilar de 64×64. |
| `scripts/client-rme/add_custom_items.py` | Instala solo los IDs de esta familia sobre los assets actuales. |
| `scripts/map/bridge-trap-steps.py` | Aplica el acabado con guardas de colisión, suelos, casas y atributos protegidos. |
| `scripts/map/render-main-bridge.py` | Render real y comparación con un backup completo. |

Barandas: server **20490–20507**, client **5210–5227** (misma familia exclusiva,
nuevo dibujo). Pavimentos: server **20540–20555**, client **5260–5275**. Pilar:
server **20579**, client **5299**. Los slots nuevos estaban vacíos al integrarlos.
35 apariencias en total; 92 sprites añadidos, **15334–15425**. Outfits, efectos y
proyectiles anteriores permanecen idénticos. Ambos OTB actualizados.

PNG reproducibles en `devtools/zagan-test/custom-sprites/`: `cbz6_00.png` a
`cbz6_17.png`, `ironbound_floor_00.png` a `ironbound_floor_15.png` e
`ironbound_pier.png`. No se sustituyen los suelos/barandas/pilares nativos globales.

```bash
python3.11 scripts/client-rme/city_bridge_z6_art.py
python3.11 scripts/client-rme/add_custom_items.py \
  --things devtools/rme/rme-client-760 \
  --otb server/YurOTS/ots/data/items/items-zagan-test.otb \
  --otb server/YurOTS/ots/data/items/items.otb \
  --only 20490 20491 20492 20493 20494 20495 20496 20497 20498 20499 20500 20501 20502 20503 20504 20505 20506 20507 20540 20541 20542 20543 20544 20545 20546 20547 20548 20549 20550 20551 20552 20553 20554 20555 20579
python3.11 scripts/map/bridge-trap-steps.py --dry-run
python3.11 scripts/map/bridge-trap-steps.py
python3.11 scripts/map/render-main-bridge.py --before-dir backups/map/ironbound-bridge
```

## Validaciones y detalles importantes

Auditoría contra `backups/map/ironbound-bridge/`: **45 casillas cambiadas** (37 de
pavimento y ocho pilares), ninguna fuera del puente. Misma huella del mapa, suelos,
flags de movimiento/proyectiles/cambio de piso, casas y 11 lockers completos.
Conectividad de las 41 casillas y ocho cortes de 1 sqm comprobados estáticamente.
Las cuatro trampillas y las casillas de sus escaleras siguen iguales.

DAT: solo 18 apariencias exclusivas actualizadas y 17 slots antes vacíos ocupados;
todo el resto y su cola son idénticos. SPR: los 15.333 registros anteriores son
idénticos; se añaden 92. En OTB solo cambian nombres/descripciones de las 18 piezas
anteriores, además de los nuevos ítems; su comportamiento no cambia.
`bridge-trap-steps.py --dry-run` repetido: **0 cambios**; `check-map-load.py`:
**0 errores**; `sync-houses-with-map.py --dry-run`: coincide.

No ampliar la base de los pretiles por fuera de su huella: los píxeles a nivel del
suelo pueden necesitar anclas nuevas y cambiar la colisión del puente. El modelo
actual fija las 50 anclas existentes y falla si una pieza no cabe en su 2×2.
El material se carga de forma privada para no recolorear los demás puentes al
importar el instalador general. Las apariencias se generan antes de instalarlas.

Implementado en el repositorio, pendiente de publicar el cliente y deploy. No se recompiló C++, no se modificaron jugadores ni se
hicieron suites, bots o pruebas in-game, respetando la preferencia del usuario.
Antes del deploy: publicar el cliente, respaldo runtime y reinicio ordenado según
[ThinkPad](../systems/THINKPAD_TEST_SERVER.md), con autorización del usuario.
