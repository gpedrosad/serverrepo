# Pozos del Infierno — zona de caza del portal `159,47,7`

La propuesta **Pits of Inferno** de [`gameplay/QUESTS.md`](../gameplay/QUESTS.md) hecha mapa (nov 2026):
la cueva de fuego de nivel 90–130 para grupos, y la **fuente de las armas traídas de 8.x** —Emerald
Sword, Avenger, Arcane Staff y Arbalest— que hasta ahora solo se conseguían por GM. Convive con la
[Isla del Infierno](../gameplay/HELL_QUEST.md) (barco, puertas 80/100, cofres de Demon Helmet/MPA/BoH/Demon
Shield): la isla queda como la antesala; los Pozos son la progresión más dura de fuego del server.

Generador: `scripts/map/generate-inferno-pits.py` (cuevas con la maquinaria del Valle
[`generate-beast-valley.py`](../../scripts/map/generate-beast-valley.py); ceniza, lava y santuario con
la de la Isla del Infierno `generate-hell-quest.py`). Manifiesto:
`server/YurOTS/ots/data/world/generated-inferno-pits.json`.

## Recorrido

| Piso | Zona | Monstruos | Nivel |
|------|------|-----------|-------|
| z7 | Yerma de Ceniza: cañón de ceniza con charcos de lava, del arrival a la Boca | Campo de Brasas (Fire Devil / Fire Elemental) y La Jauría (Hellhound) en los claros | 85–95 |
| z8 | Pozos de Ceniza (~1.000 casillas): zigzag al sur desde la Boca | Fire Elemental sueltos → Hellhound sueltos → de a 2 | 90–105 |
| z9 | Garganta de Magma (~1.000): vuelve al norte | Hellhound sueltos → de a 2 → Demon sueltos → Demon + Hellhound de a 2 | 100–115 |
| z10 | Corazón del Infierno (~1.300 + arena): cruza al sur hasta el final | Demon sueltos → de a 2 → Demon + Fury → Fury de a 2 | 115–130+ |
| z10 | Arena de las Furias (tras la puerta de nivel 100): anillo de lava | **1 Fury** (600 s) + **2 Demon** (300 s) | grupo |
| z10 | Cámara de las Armas: 4 cofres + portal al templo | — | 100 |

Cada piso de cueva arranca donde termina el de arriba (la bajada la elige `stair_down` dentro de la
caja del piso de abajo): z8 baja al sur, z9 vuelve al norte y z10 cruza al sur hasta el arena. La
superficie es un cañón (no un campo abierto): todo lo que no es yerma bloquea, como el bosque del valle.

## Puertas de nivel

| Puerta | Dónde | Nivel |
|--------|-------|------:|
| Santuario de la Boca | `540,287,7` (ladrillo, única entrada a la bajada) | **90** |
| Puerta del Corazón | `539,356,10` (corta el corredor al arena) | **100** |

Puertas `1229` con actionId = nivel + 1000 (`leveldoor.lua`). El generador comprueba que sin
cruzarlas no se llega ni a la Boca ni a los cofres.

## La quest: Cámara de las Armas

Detrás del Arena de las Furias hay 4 cofres. **Cada personaje se lleva uno solo** (storage
compartido `5104`):

| Cofre (uid) | Premio |
|-------------|--------|
| 5104 | Emerald Sword (20157) |
| 5105 | Avenger (20158) |
| 5106 | Arcane Staff (20159) |
| 5107 | Arbalest (20160) |

Script: `data/actions/scripts/pitschest.lua` (registrado en `actions.xml`, uniqueId 5104–5107).
Solo Lua: no hace falta recompilar el server. Mismo patrón que `hellchest.lua`.

## Coordenadas

| Qué | Pos |
|-----|-----|
| Portal (plaza del templo) | `159, 47, 7` → llegada `540, 440, 7` |
| Portales de vuelta en la llegada | `540, 445, 7` y `541, 445, 7` → `159, 48, 7` |
| La Boca (santuario + puerta 90 + bajada `432`) | `540, 285, 7` |
| Bajada z8 → z9 | `542, 325, 8` (escalera `1385` en `542, 325, 9`) |
| Bajada z9 → z10 | `570, 292, 9` (escalera en `570, 292, 10`) |
| Puerta del Corazón (nivel 100) | `539, 356, 10` |
| Arena de las Furias (centro) | `540, 369, 10` |
| Cámara de las Armas (cofres) | `536–543, 380, 10` |
| Portal final (Cámara) | `540, 384, 10` → `159, 48, 7` |
| Caja | x `490–589`, y `240–460`, z7–z10 (vacía: el hub de eventos vive en x 595+) |

Carteles en `readables.xml`, bloque `INFERNO_PITS_SIGNS`. Spawns en `test-spawn.xml`, bloque
`INFERNO_PITS_SPAWNS` (105 monstruos: Hellhound 38, Demon 28, Fire Elemental 23, Fury 10,
Fire Devil 6; 1 cada 42–47 casillas en cuevas, dentro de la receta de
[`ZONAS_DE_CAZA.md`](ZONAS_DE_CAZA.md)).

## Regenerar

```bash
python3 scripts/map/generate-inferno-pits.py --dry-run --preview /tmp/pozos.png   # valida y dibuja
python3 scripts/map/generate-inferno-pits.py          # mapa, spawns, carteles y manifiesto
python3 scripts/map/temple-portals.py                 # el portal de la plaza (159,47,7)
python3 scripts/map/check-map-load.py                 # 0 errores
python3 scripts/map/check-upper-view.py --box 490 240 589 460 --z 8 9 10
```

Re-ejecutable y determinista (`--seed`, por defecto 23): borra su caja z7–z10 y reemplaza sus
bloques de spawns y carteles. Las bajadas internas las elige `stair_down` según la semilla.

## Reglas que valida (si algo falla no escribe nada)

- Piezas únicas: bordes de tierra y de lava en la superficie, paredes de cueva (`356–367`) y lava
  con borde de grava en los tres pisos.
- Con las puertas abiertas se llega de la llegada a los claros, la Boca, las bajadas, el arena, los
  cofres y el portal; **cerradas no**: la puerta 90 encierra la Boca, la 100 encierra cofres y portal.
- Escaleras: bajada `432` arriba, escalera de mano `1385` justo debajo, salidas caminables (sur
  abajo, norte arriba).
- Desde ninguna casilla caminable se ve el borde de la caja (media pantalla 7×5).
- Todos los monstruos existen en `monsters.xml`.

## Errores que ya pasaron (y cómo se evitan)

| Qué pasó | Cómo se evita |
|---|---|
| La superficie quedó con 7.300 casillas caminables (un campo abierto, no un cañón) | El relleno de la yerma tiene ramas sin bloqueo (pebbles). **Toda** casilla fuera de `play` lleva pieza que bloquea, como el bosque del valle |
| Los portales de vuelta "sin acceso" | El arrival estaba a 8 del borde sur del `inner` y los portales caían en la banda de montaña. Llegada y portales tienen que quedar bien adentro (`ARRIVAL` y 210 → el `inner` llega a 211) |
| Los cofres y el arena "sin acceso" | El BFS de distancia excluía la celda de la puerta (bloquea) y todo lo que seguía quedaba inalcanzable. La distancia se mide **con las puertas abiertas**; que no se salteen cerradas es un chequeo aparte |

## Pendiente

- Prueba in-game: bajar por la Boca (puerta 90), las dos bajadas internas, la puerta 100, matar la
  Furia, abrir UN cofre y verificar que el segundo no da nada, y volver por el portal final.
- Antes de deployar `test.otbm`: prueba de depot in-game ([`gameplay/DEPOTS.md`](../gameplay/DEPOTS.md)).
- Con el deploy: actualizar `web/site/src/data/quests.json` (la propuesta Pits of Inferno pasa a
  existente) y compilar la web (`scripts/web/build-site.sh`).

## Sin borde de pasto en el sendero (24 nov 2026)

El sendero de tierra de la superficie llevaba a los costados las piezas `DIRT_SIDE/CORNER/INNER` (`110–121`), que
son **pasto** con borde de tierra: en la grava volcánica se veía una franja verde. No hay familia grava/tierra, así
que la grava queda lisa junto al sendero. Se cambiaron 472 suelos `110–121 → 105` en la caja z7 (conservando lo que
tenían encima) y el generador ya no los pone (la validación ahora rechaza pasto en la grava).
