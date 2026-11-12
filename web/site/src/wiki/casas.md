---
titulo: Casas
categoria: Lugares y actividades
resumen: Las casas las entrega el staff. El dueño decide quién entra con los hechizos aleta y no paga arriendo.
orden: 60
icono: 2091
estado: borrador
---

## Lo esencial

- Hay **28 casas** en el mapa, en calles como Small Street, Great Street, River Street y Bamboo Camp.
- **No se compran con un comando ni con un NPC**: las asigna el staff. Pregúntale a un GM en el juego.
- **No hay arriendo**: la casa no se pierde por falta de pago.
- El dueño decide quién entra y quién abre cada puerta con los hechizos *aleta*.
- Lo que dejas en la casa se queda ahí aunque mueras.

## Saber de quién es

Mira la puerta. Dice algo como *It belongs to house 'Great Street I'. Nobody owns this house.* o el nombre del dueño.

## Permisos

Hay cuatro niveles: dueño, subdueño, dueño de puerta e invitado. Los hechizos se dicen **parado dentro de la casa** y abren una ventana con la lista de nombres, uno por línea.

| Hechizo | Qué hace | Quién puede |
|---|---|---|
| `aleta sio` | Editar invitados: pueden entrar si la puerta está abierta | Dueño y subdueños |
| `aleta som` | Editar subdueños: abren puertas e invitan gente | Dueño |
| `aleta grav` | Editar quién abre esa puerta (dilo al lado de la puerta) | Dueño |
| `aleta gom` | Pasarle la casa a otro jugador | Dueño |
| `alana sio` | Salir de la casa al instante | Cualquiera dentro |
| `alana sio "Nombre"` | Echar a alguien de la casa | Dueño y subdueños |

- Los invitados pueden entrar, pero **no abren puertas**.
- Si te acaban de dar permiso y no puedes entrar, escribe `!house` para recargar tus permisos.
- Los personajes sin vocación no pueden usar estos hechizos.

> **Ojo:** `aleta gom` le pasa la casa completa a otro jugador, con todo lo que hay adentro. Solo el nuevo dueño puede devolvértela.

## Límites

- Cada sqm de la casa aguanta **10 objetos**, contando lo que hay dentro de mochilas y cofres.
- Las casas no tienen depot propio: usa los [[depots]] del templo.

## Trainer privado

El *Private Trainer Dummy* es un muñeco de entrenamiento para tu casa. Se consigue como extra al donar por [[premium]] en la web.

1. Entra a la casa y deja el ítem en un sqm libre del piso.
2. Úsalo (clic derecho → *Use*). Se convierte en un trainer.

Solo cabe **1 por casa** y no se puede retirar. Ver [[training]].

## Relacionado

- [[depots]]
- [[training]]
- [[comandos]]
