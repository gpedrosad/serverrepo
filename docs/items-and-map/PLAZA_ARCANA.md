# Plaza arcana de los teleports

Estado: **publicada y desplegada en la ThinkPad el 19 nov 2026**, validada con cliente Mac en instancia aislada.
Rediseño pedido por Gonzalo: nuevas torres, suelo y sprites con basalto azul y cian eléctrico.
No requiere recompilar C++.

![Antes y después, con pisos superiores](img/portal-citadel/before-after.png)

## Diseño y límites

- Dos torres ornamentales nuevas: **155–157,42–44** y **167–169,42–44**, base z7,
  dos cuerpos superiores z6/z5 y remate con cristal en z4.
- Basalto oscuro, sendero cobalto/cian, anillos rúnicos para las llegadas, dos beacons
  en 157,51 y 168,51 y dos obeliscos en 155,50 y 169,50 (z7).
- Pasillo delante de los carteles en y45 y acceso central sur–norte libres.
- Se conservan los ocho portales en y47, carteles y46, llegadas y48 y todos sus destinos.
  La galería, las torres antiguas del templo y los edificios vecinos no se remodelan.
- **210 casillas** afectadas dentro de las huellas declaradas: 156 en planta baja y
  **54 nuevas** arriba. Todo tile fuera de esas huellas queda idéntico, incluidos depots y casas.

Las torres son remates arquitectónicos cerrados: no agregan escaleras, NPCs ni monstruos.
Las paredes norte/oeste de los pisos superiores van sin ground, según PIEZAS_DE_MAPA.md;
el resto tiene soporte en el piso anterior. No hay techos sueltos fuera de las torres.
Se mantienen los flags originales de los tiles de planta baja.

## Sprites nuevos

| Server ID | Client ID reservado | Apariencia | Prototipo |
|---:|---:|---|---:|
| 20214 | 3379 | Basalto | 965 |
| 20215 | 3368 | Sendero cian | 965 |
| 20216 | 3365 | Anillo rúnico de llegada | 965 |
| 20217 | 3363 | Poste | 1027 |
| 20218 | 3342 | Muro horizontal | 1028 |
| 20219 | 3253 | Muro vertical | 1030 |
| 20220 | 3247 | Esquina | 1033 |
| 20221 | 3246 | Ventana horizontal | 1265 |
| 20222 | 3245 | Ventana vertical | 1266 |
| 20223 | 3244 | Beacon de cristal (luz 6/71) | 1445 |
| 20224 | 3243 | Obelisco rúnico (luz 4/71) | 1445 |

Tres pisos 32×32, seis piezas de pared 64×64 y dos adornos 64×64: **35 sprites nuevos**.
Los **14.037 sprites previos** se conservan byte por byte; final 14.072. Tampoco cambian
outfits, efectos, proyectiles ni apariencias anteriores, salvo los once slots reservados.
Las murallas del depot conservan sus propios IDs y dibujos.

Los pisos clonan white marble floor **965**, una variante de un sprite con velocidad **100**,
igual que el mármol 406/407 de la plaza anterior. Gravel 105 tenía velocidad 150 y se descartó
para no hacer más lenta la caminata. Los beacons/obeliscos clonan monument 1445: inmóviles y sólidos.

Los client IDs se eligieron con el buscador canónico de candidatos; además se comprobó en solo
lectura que sus server IDs antiguos no estaban en jugadores ni houseitems de la ThinkPad.
No hay alias de esos client IDs usado por otro item del mapa.

## Fuentes y reproducción

Arte creado con **ImageGen integrado**. Prompts completos y salidas originales en
`devtools/zagan-test/custom-sprites/portal-citadel/prompts.json` y `*-generated.png`.
`walls-template-brick.png` es la referencia del atlas 3×2; `template-1027.png`, etc.,
guardan las seis máscaras exactas. PNG finales: `basalt.png`, `conduit.png`, `dais.png`,
`wall-<prototipo>.png`, `beacon.png` y `obelisk.png`.

Se adapta con nearest-neighbor y alpha 0/255. Las paredes recuperan la silueta original;
los adornos conservan proporciones y apoyan el pie abajo; los pisos son totalmente opacos.
`add_custom_items.with_light` ahora añade el flag 0x15 cuando el prototipo no tenía luz,
además de reemplazarlo cuando existe; antes un monumento ignoraba `light=` en el DAT.

```sh
python3.11 scripts/client-rme/portal_citadel_assets.py --prepare --apply
python3 scripts/map/temple-portals.py
python3.11 scripts/map/validate-portal-citadel.py --before backups/map/portal-citadel-before
```

`temple-portals.py` sigue siendo el **único dueño** de la plaza: incorpora el layout de
`portal_citadel_layout.py`. Regenerar una hunt y correrlo de nuevo conserva el diseño.
Ambos instaladores son idempotentes. `--things`/`--otb` permiten probar assets en copias;
`temple-portals.py --dry-run` revisa sin escribir. Backup local: `backups/map/portal-citadel-before/`.

## Validación

- `check-map-load.py`: 0 errores.
- `validate-portal-citadel.py`: resto del mapa idéntico, **226 teleports intactos**,
  ocho llegadas y carteles accesibles sin atravesar otro teleport, sin espacios libres
  aislados fuera de las torres; sprites, nodos OTB y cola DAT anteriores intactos.
- `scan-map-depots.py` antes/después: **11 lockers**, mismos tiles y depotid=1.
- `sync-houses-with-map.py --dry-run`: casas coinciden, sin cambios.
- El mapa anterior ya tenía tres posiciones duplicadas fuera de la plaza: se comparan todas
  sus entradas, que permanecen iguales; no se agregan duplicados ni se corrigen zonas ajenas.
- La velocidad del piso y la luz se leen de vuelta del DAT generado.

### Cliente real en servidor aislado

Instancia en `~/build/portal-citadel-qa-20261119`, puerto **7280**, con datos sintéticos y el
binario ya existente. Ningún cambio del servidor de juego. Script:
`scripts/ot/test-portal-citadel-client.lua`.

El cliente Mac distribuido carga las once apariencias nuevas, recorre el pasillo sur–norte
y entra caminando en los ocho portales; comprueba cada destino recibido del servidor.
Capturas del mapa y de los pisos individuales en `img/portal-citadel/`.
El mismo cliente abrió después el locker 129,58,6 con Bot Knight: mostró las **7 crystal coins**
guardadas en depotid=1. Probe del fixture OK; instaladores repetidos dejan mapa, readables,
OTB, DAT y SPR idénticos byte por byte. Paridad de los 774 archivos comunes Mac/Windows OK.

Nota para repetir QA: este binario usa `Application Support/otclientv8` como writeDir;
**APP_NAME por sí solo no lo aísla**. En el init de la copia QA cargar un settings exclusivo
(`/portal_citadel_qa_config.otml`) y en su minimapa usar otro nombre de archivo de guardado.
El updater debe quedar vacío en ese init de QA para que no reemplace los assets de prueba.

### Publicación y deploy

Autorizado por Gonzalo. Fuente del servidor `b6b86a4`, assets del cliente `55d5342`.
ff-merges sin solapamientos con otras sesiones; cliente publicado primero mediante
`publish_client.py`: **3 archivos cambiados** (DAT, SPR y minimapa), 0 borrados.
Los 774 archivos comunes coinciden en Mac, Windows, updater y ambos ZIPs; manifest CRC,
contenido de los tres assets y descargas HTTP 200 verificados en 8080 y 8076.
CRC DAT `dc61b99b`, SPR `8da89f7a`.

Respaldo `~/backups/pre-deploy-20261119-211809-portal-citadel`, refrescado antes del reinicio
y después del guardado. Mapa y OTB aplicados juntos, `docker restart -t 45 yurots` sin rebuild:
graceful shutdown completo, mapa cargado en **0,801 s**, sin errores ni warnings.
Probe `192.168.1.17:7171` OK, contenedor healthy y 0 reinicios automáticos.
**1 cuenta, 8 personajes y 31 casas** preservados; contenido de depots, dueños, config y
binario idénticos al snapshot previo. La comparación normaliza tuplas/listas al serializar JSON.
La instancia QA quedó detenida. Los smoke tests siguen desactivados.
Pendiente revisión visual manual del jugador en Windows; abrir el cliente toma la actualización.
