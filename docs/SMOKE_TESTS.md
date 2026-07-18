# Smoke Tests Locales

> **Estado (jul 2026): desactivados temporalmente.** Existe el sentinel
> `scripts/.smoke-tests-disabled`; mientras esté presente, `test-local-smoke.sh`
> sale en 0 sin correr casos. Para reactivar: `rm scripts/.smoke-tests-disabled`
> y actualizar `AGENTS.md`. Corrida puntual sin borrar el sentinel:
> `bash scripts/test-local-smoke.sh --force`.

Esta base de pruebas existe para tocar el server viejo con un poco mas de red.
La idea no es reemplazar QA completo, sino darnos una verificacion corta y
repetible antes de meter mano en cosas delicadas.

## Que cubre hoy

- Login de cuenta.
- Login al mundo con personaje real.
- Carga del player desde XML.
- Guardado del player al logout.
- Cast de un spell utilitario.
- Cast de un spell ofensivo.
- Cast de un spell de curacion con vida baja.
- Uso de rune real desde inventario con consumo de charge.
- Muerte, relog y respawn con helper GM local.
- Movimiento simple con guardado de posicion.

Todo eso corre con el personaje de prueba `Test Knight` y, al terminar cada
caso, el script restaura su XML para no ir gastando mana ni deformando el
estado base del server.

## Como correrlo

Si el server local ya esta arriba:

```bash
bash scripts/test-local-smoke.sh
```

Si quieres que primero levante Docker:

```bash
bash scripts/test-local-smoke.sh --start
```

Si cambiaste credenciales o personaje de prueba:

```bash
bash scripts/test-local-smoke.sh --account 275783 --password 123456qa --char "Test Knight"
```

## Que valida en cada caso

### 1. Login de cuenta

Confirma que el server responde al primer handshake y que la cuenta todavia
puede listar personajes.

### 2. Login al mundo y save

Entra al mundo con el personaje de prueba, sale, y revisa que el XML del
player haya sido actualizado. Esto nos cubre lo mas sensible del flujo clasico:
`cargar -> jugar -> guardar`.

### 3. Spell utilitario

Lanza un spell inocuo (`utevo lux` por defecto) y luego revisa el XML para
confirmar que el gasto de mana y el progreso de `manaspent` se guardaron bien.
El delta exacto de `manaspent` puede variar segun `manamul` y otras rates del
server, asi que la suite valida que haya avance real sin acoplarse a una sola
configuracion.

### 4. Spell ofensivo

Intenta lanzar un spell ofensivo (`exori` por defecto; Knight) para tocar tambien
el camino de combate/magia, y vuelve a validar el guardado.

Si el personaje de prueba esta parado en una zona segura y el cast no puede
ejecutarse desde ahi, la suite no rompe por eso: lo marca como pendiente manual.
Eso evita falsos rojos cuando el entorno local esta sano pero el spawn de prueba
no sirve para combate real.

### 5. Spell de curacion

La suite baja la vida del personaje de prueba en el XML base, entra al mundo,
lanza `exura` y luego valida tres cosas al salir: que suba la vida, que baje
la mana correcta y que `manaspent` avance.

Este caso vale mucho porque cubre un camino distinto al spell utilitario y al
ofensivo: formulas de curacion sobre el propio player con persistencia real del
resultado.

### 6. Rune desde inventario

La suite inyecta una `Ultimate Healing` temporal en un slot libre del
inventario del personaje de prueba, baja la vida del player en el XML base para
que la cura tenga efecto real, usa la rune sobre el propio player y luego
restaura el XML original.

Se hace asi porque, en este server, abrir el backpack del `Test Knight` por
packet no es un flujo suficientemente estable para usarlo como smoke
automatizada. La validacion importante sigue siendo la misma: que el `count`
del item baje en el XML al salir, o sea, que el charge realmente se consuma.

En este caso ademas espera ver curacion real sobre el player.

### 7. Muerte, relog y respawn

La suite usa un helper local (`GM Kaiser` por defecto), lo teleporta cerca del
personaje de prueba y lanza `exevo gran mas vis` para forzar una muerte real
del player por el camino normal del server.

Despues valida lo importante de verdad:

- que aparezca una entrada nueva en `deaths` con el killer correcto
- que el player reaparezca en el templo
- que se guarden las penalidades reales de muerte

Este caso es local a proposito. No depende de monstruos del mapa ni de abrir un
cliente manual, asi que nos da una senal mucho mas corta y repetible sobre una
de las rutas mas fragiles del server viejo.

Si cambias el spawn base del personaje de prueba o el helper GM, ajusta
`--death-gm-pos` y `--gm-char`.

### 8. Movimiento y save de posicion

La suite prueba movimientos simples en varias direcciones hasta encontrar uno
que realmente desplace al player, y luego valida que la nueva posicion haya
quedado guardada en el XML al salir.

Esto nos da una senal muy util sobre el camino completo de movimiento:
protocolo, `thingMove` y persistencia del player.

## Que sigue siendo manual

Estas pruebas todavia conviene hacerlas con cliente cuando el cambio toca esa
zona:

- Consumo real de runas contra objetivo visible.
- Ataque melee o distancia contra monstruo.
- Interaccion con NPCs, trade, depot y casas.
- Movimiento sobre mapa editado recientemente.
- Combate con rune sobre monstruo real o battle window.

## Cuando correrlo

- Antes de tocar ownership, memoria o logout/login.
- Antes de cambiar spells, runas o formulas.
- Despues de cambios en `game.cpp`, `player.cpp`, `protocol76.cpp`,
  `ioplayerxml.cpp` o scripts de spells.

## Requisito practico para el personaje de prueba

Para que los casos ofensivos, de runas y de muerte no den falsos bloqueos, el
personaje de prueba debe quedar fuera de PZ al momento de guardar su XML base.

## Lectura rapida del resultado

Si todo sale bien, el script termina con:

```text
OK: smoke suite local completada
```

Si falla, corta en el primer caso roto y muestra el motivo para ir directo a la
zona comprometida.
