# Cartas, scrolls y libros (leer y escribir)

> Portado en nov 2026 de la rama `feat/readables-writeables-build-fix` (basrodriguezr, jul 2026), que nunca
> se había mergeado. Antes de eso, escribir respondía "Write not working yet.".

## Qué hace

- **Usar** un ítem legible abre la ventana de texto. Lo decide el `items.otb`, no una lista de ids:
  - grupo `writeable` → ventana editable (hasta 100 caracteres en el cliente);
  - solo flag `readable` → ventana de solo lectura.
- **Escribir** guarda el texto en el ítem (`Protocol76::parseTextWindow`). Se rechaza si el ítem no es
  escribible en el OTB (un cliente modificado podría intentarlo con un libro), si la ventana no es la última
  abierta o si el ítem ya no existe. Se corta a 255 caracteres y se quitan los caracteres de control salvo
  el salto de línea (el texto termina en XML).
- **Persistencia:**
  - en inventario, containers o depot: con el personaje (`Item::serialize` guarda `text`);
  - en el piso: `data/scrolltexts.xml`, por posición (el mapa se carga siempre del `.otbm`). Al arrancar,
    `Readables::LoadScrollTexts` se lo pone al ítem de arriba de esa casilla **solo si es escribible**.
    Es data runtime: no va a git (`.gitignore`) y se respalda en el deploy.

Hoy el mapa no tiene ningún ítem escribible (`test.otbm`, nov 2026), así que `scrolltexts.xml` solo guarda
lo escrito en scrolls tirados al piso, que desaparecen al reiniciar salvo los de las casas.

## Ids (items.otb / items-zagan-test.otb, iguales)

- Escribibles (14): 1811, 1818, 1947 (blank paper), 1948, 1949 (scroll), 1951, 1952, 2597, 2599, 4842,
  4853, 4854, 4855, 4857.
- Solo lectura (37): 1810, 1815, 1950, 1953, 1954 (premium scroll), 1955–1986.

## Con script propio (`data/actions/actions.xml`)

Lo que tiene action propio se atiende antes del default de `Actions::UseItem`:

| Id | Script | Qué hace |
|----|--------|----------|
| 1953 | `rwitems.lua` | En `135,130,9`: pergamino de +5 h de training por día. En otro lado, se lee. |
| 2598 | `rwitems.lua` | Stamped letter: el OTB no la marca legible; el script la abre solo lectura. |
| 1954, 2345 | `premium_scroll.lua` | Premium scroll. |

## Errores que ya pasaron

- `rwitems.lua` hacía `if rw and 1` / `if rw and 2`: en Lua eso es siempre verdadero, así que abría **todo**
  como editable, también los libros de solo lectura. No se notaba porque escribir no funcionaba. Ahora mira
  los bits (`rw % 2`, `math.floor(rw / 2) % 2`) y solo atiende 1953 y 2598.
- El paquete de uso (`0x82`) lleva el **id de cliente**, no el del server (1949 → 2815, 1955 → 2821,
  2598 → 3506). Un bot de prueba que mande el id del server recibe "You can not use this object".

## Cómo se probó

Server de prueba aparte (puerto 7275, cuentas de `scripts/ot/make-test-bots.py`, ver
[`SANITIZER_TESTS.md`](../systems/SANITIZER_TESTS.md)) y un bot que, con el Bot GM: crea un 1949 con `/i`,
lo usa, escribe dos líneas, lo reabre y compara; abre un 1955 y comprueba que un write forzado no cambia
nada; abre un 2598. Después, reinicio con `scrolltexts.xml` presente.
