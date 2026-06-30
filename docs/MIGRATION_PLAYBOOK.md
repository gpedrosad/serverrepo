# Retro76 - Playbook de migracion de ideas

## Objetivo

Este documento resume los cambios mas valiosos que se fueron agregando a este server para poder **replicarlos en otro proyecto**, aunque el otro server use otra base, otra estructura de archivos o incluso otra filosofia tecnica.

La idea no es copiar el codigo tal cual.

La idea es conservar:

- el problema que resolvia cada cambio
- el valor real que agrego
- la forma recomendada de adaptarlo
- los riesgos a revisar antes de moverlo

## Como leer esta guia

Cada caso esta escrito en lenguaje de producto y operacion, no como especificacion de motor.

Si queres bajar a detalle tecnico en este repo, al final de cada caso dejo una referencia corta a los archivos o docs donde hoy vive esa logica.

## Resumen ejecutivo

Estas son las ideas que mas valor tienen para portar a otro server:

| Prioridad | Idea | Valor principal | Portabilidad |
|----------|------|-----------------|--------------|
| Alta | Ecosistema de training controlado | retencion, orden, menos abuso | Alta |
| Alta | Bounty / Most Wanted | contenido social y PvP organico | Media |
| Alta | Confirmacion universal en NPCs | menos errores de usuario | Alta |
| Alta | Economia apoyada en banco | menos friccion, menos micro manejo | Media |
| Alta | Rage monsters | sorpresa, replayability, mejor loot loop | Media |
| Media | Gemas + imbuements simples | progresion lateral sin rehacer items | Media |
| Media | Premium/promocion con perks utiles | monetizacion o status con valor claro | Media |
| Media | Spells y ajustes retro de calidad | mejora sensacion de juego | Alta |
| Alta | Disciplina operativa y backups | evita perder personajes al migrar | Alta |

---

## 1. Ecosistema de training controlado

### Idea

No pensar el training como una sala mas, sino como un **sub-sistema con reglas propias**.

En este server ese sub-sistema termino incluyendo:

- zona de training separada
- limite diario por personaje
- bloqueo total de PvP dentro de esa zona
- mobs dedicados de training
- parchment que agrega horas extra por ese dia

### Por que valio la pena

- evita que el training se convierta en zona de abuso o grief
- limita el progreso AFK sin prohibirlo del todo
- da herramientas para hacer eventos o compensaciones sin tocar rates globales
- hace que el training sea facil de explicar al jugador

### Como migrarlo a otro server

Mantene estas reglas, aunque cambie la implementacion:

1. El training debe tener una frontera clara.
2. El consumo de tiempo debe vivir por personaje y por dia.
3. Dentro del training no deberia existir incentivo PvP.
4. Los bonuses temporales deberian sumarse al limite diario, no romperlo.

### Riesgos

- si la zona queda mal definida, bloqueas combate donde no corresponde
- si el limite diario no persiste bien, algunos players lo van a resetear
- si el bonus diario no expira por fecha real, se transforma en exploit

### Referencias en este repo

- `docs/TRAINING_ZONE_NO_PVP.md`
- `docs/TRAINING_BONUS_PARCHMENT.md`
- `OTINFO`

---

## 2. Bounty / Most Wanted como loop social

### Idea

La bounty no se trato como un premio que el sistema imprime, sino como una **carga social transferible** entre jugadores.

Eso cambia mucho el tono del sistema:

- alguien financia una caceria desde el banco
- el target gana visibilidad
- si otro player lo mata, la “marca” se mueve al killer
- la web convierte eso en narrativa publica con ranking visible

### Por que valio la pena

- genera historias solas
- da contenido PvP sin obligar wars formales
- hace que la web tenga una seccion viva y no solo ranking estatico
- convierte el banco en herramienta real del juego, no solo deposito

### Como migrarlo a otro server

Lo importante no es el NPC exacto.

Lo importante es conservar estas invariantes:

- la bounty sale de riqueza existente
- no se duplica oro al pagarla
- no se pierde el estado al reiniciar
- solo cambia de manos en PvP valido

### Riesgos

- exploits si permitis bounty entre chars de la misma cuenta
- inconsistencias si guardas sponsor y target en momentos separados sin rollback
- ruido social si la UI publica muestra staff o personajes ocultos

### Referencias en este repo

- `docs/MOST_WANTED_SYSTEM.md`

---

## 3. Confirmacion universal de transacciones de NPC

### Idea

Mover la confirmacion al core del sistema de NPCs, en vez de resolverla NPC por NPC.

En la practica significa que comprar y vender deja de ser “instantaneo y facil de errarle” y pasa a ser:

- pedido
- confirmacion
- ejecucion

### Por que valio la pena

- reduce compras accidentales
- evita errores caros al vender loot o consumibles
- mejora todos los NPCs de una sola vez
- hace que scripts simples sigan sirviendo

### Como migrarlo a otro server

Si tu motor lo permite, hacelo como capa comun.

Si no lo permite, igual vale la pena imponer la regla de UX:

- ninguna transaccion sensible deberia ejecutarse sin confirmacion humana

### Riesgos

- algunos NPCs raros pueden disparar mas de una operacion en el mismo dialogo
- si el estado pendiente queda mal manejado, el NPC puede “recordar” una compra vieja
- en engines legacy puede ser mejor una estructura externa antes que tocar layouts delicados

### Referencias en este repo

- `docs/NPC_CONFIRMATION.md`

---

## 4. Economia apoyada en banco, no solo en mochila

### Idea

Hacer que el banco sea infraestructura del juego y no una feature aislada.

En este server eso quedo reflejado en varias ideas compatibles entre si:

- compras NPC pagando desde inventario y banco
- bounty financiada desde bank balance
- golden amulet que manda el oro del loot directo al banco

### Por que valio la pena

- menos friccion administrativa
- menos viajes aburridos a ordenar gold
- mas sentido para tener cuenta bancaria
- mas espacio libre para jugar, no para cargar moneda

### Como migrarlo a otro server

Porta primero la idea de “saldo utilizable desde varios sistemas”.

Despues elegi si queres:

- pago mixto mano + banco
- auto bank de gold loot
- transferencias entre jugadores
- sistemas premium o bounty apoyados en banco

### Riesgos

- si el banco y el inventario no guardan con seguridad, aparecen duplicaciones o perdidas
- auto-bankear demasiado puede quitar sensacion de loot si no se comunica bien
- conviene limitarlo al oro, no a todo el botin

### Referencias en este repo

- `docs/MOST_WANTED_SYSTEM.md`
- `server/YurOTS/ots/source/player.cpp`
- `server/YurOTS/ots/source/game.cpp`

---

## 5. NPCs de conveniencia: vender soluciones, no solo items

### Idea

Los NPCs utiles no solo venden unidades sueltas.
Tambien pueden vender **paquetes listos para usar** y reconocer acciones frecuentes del jugador.

Casos ya aplicados aca:

- backpack de mana fluid
- backpack de life fluid
- backpack de runas
- venta masiva de vials vacios

### Por que valio la pena

- reduce clicks y spam de chat
- hace que la economia del early/mid game sea mas amable
- baja mucho el costo mental de reabastecerse

### Como migrarlo a otro server

Pensalo como patron:

- detectar compras repetitivas
- empaquetarlas
- cobrar exactamente la suma de contenido + container
- confirmar antes de ejecutar

Tambien es buena idea diferenciar mejor items parecidos, por ejemplo:

- “vial vacio” no deberia confundirse con “container con liquido”

### Riesgos

- si no distinguis subtype o charges, el NPC puede comprar o vender lo incorrecto
- si no validas capacidad y espacio, el jugador paga y no recibe bien el pack

### Referencias en este repo

- `docs/SELLER_FLUIDS.md`
- `docs/DARK_RODO_RUNE_BACKPACKS.md`

---

## 6. Rage monsters como generador de sorpresa

### Idea

Cuando un monstruo muere, puede volver en una variante mas fuerte.

No es solo “mas stats”.
Es una forma barata de crear:

- sorpresa
- tension
- mejores drops
- historias memorables

### Por que valio la pena

- hace menos repetitivo el PvE
- permite subir el techo de recompensa sin rehacer spawns enteros
- funciona bien con gemas, loot especial o economia de riesgo

### Como migrarlo a otro server

Hay tres reglas que conviene conservar:

1. La reaparicion debe ser rara.
2. La recompensa debe justificar el susto.
3. No debe romper zonas seguras ni sistemas especiales.

### Riesgos

- si aparece en training, PZ o arena, arruina sistemas paralelos
- si la mejora es solo HP y no loot/exp, se siente como castigo
- si la chance es alta, deja de ser sorpresa y pasa a ser ruido

### Referencias en este repo

- `docs/RAGE_MONSTERS.md`

---

## 7. Progresion lateral con gemas e imbuements simples

### Idea

Agregar una capa de progresion que no dependa solo de level, skill o item “mejor”.

En este server se resolvio con:

- gemas chicas que caen de monstruos fuertes
- fusion 20 a 1 grande
- venta a NPC como salida economica
- uso de gemas grandes para imbuir items equipados

### Por que valio la pena

- agrega objetivos de farmeo sin romper el retro
- da valor a matar monstruos “buenos para farm”
- crea decisiones: vender la gema o usarla
- permite perks tangibles sin introducir equipos totalmente nuevos

### Como migrarlo a otro server

Funciona mejor si las mejoras son:

- faciles de entender
- limitadas en cantidad de stacks
- asociadas a slots claros
- visibles para el jugador

### Riesgos

- si el fail chance es muy cruel, la gente lo vive como castigo
- si los buffs no tienen tope, se te va el balance
- si varias imbuements se pisan mal, aparecen combinaciones absurdas

### Referencias en este repo

- `docs/GEMS.md`
- `server/YurOTS/ots/data/actions/scripts/gem_imbue.lua`

---

## 8. Premium y promocion con valor jugable real

### Idea

Premium y promotion solo valen la pena si cambian la experiencia de juego de forma clara.

En esta base, la parte mas interesante no es “cobrar premium”, sino que premium/promocion afectan:

- regeneracion
- experiencia extra contra monstruos
- acceso a promotion
- posibilidad de conectar prioridad de cola si se desea

### Por que valio la pena

- hace que premium sea mas que cosmetica
- deja una escalera simple: free -> premium -> promoted
- sirve tanto para monetizacion como para recompensas del staff

### Como migrarlo a otro server

La clave es mantener los perks entendibles y no demasiados.

Buen criterio:

- premium = comodidad y mejora moderada
- promotion = mejora de identidad de vocacion

### Riesgos

- si premium resuelve demasiado poder bruto, se siente pay to win
- si promotion solo cambia el nombre, casi no se percibe
- ojo con documentar cola preferente si en config actual no esta activa

### Nota de esta copia

La base soporta premium/promotion y bonus de exp/regen.
La prioridad de cola existe como patron, pero hoy en `config.lua` la opcion `queuepremmy` esta en `"yes"`, o sea que en esta copia no esta configurada como bypass preferencial.

### Referencias en este repo

- `server/YurOTS/ots/data/npc/scripts/promote.lua`
- `server/YurOTS/ots/source/player.cpp`
- `server/YurOTS/ots/source/creature.cpp`
- `server/YurOTS/ots/config.lua`

---

## 9. Ajustes retro que mejoran mucho sin rehacer el server

### Idea

Hay cambios chicos que no parecen “feature grande”, pero mejoran muchisimo la sensacion general del server.

Los que mas valor dejaron aca fueron:

- peso de runas mas cercano a RL
- soul points con tope y regeneracion clasica
- cap base clara y configurable
- `exevo pan` abierto a todas las vocaciones
- `Magic Wall` conjurable por todas las vocaciones definidas
- fix para que las palabras magicas no aparezcan si el cast realmente fallo
- spell custom `exori gran` como mejora concreta del knight

### Por que valio la pena

- baja friccion
- mejora coherencia con expectativas retro
- da personalidad sin rehacer el combate entero

### Como migrarlo a otro server

No migres “todo o nada”.
Porta primero los que cambian sensacion con poco riesgo:

- visibilidad correcta del cast
- pesos realistas
- utility spells compartidos
- uno o dos spells custom muy claros por vocacion

### Riesgos

- pequeños cambios mal explicados pueden generar confusion si chocan con memoria de RL
- abrir utility spells a mas vocaciones puede alterar rutas de progreso
- un spell custom bueno tiene que sentirse upgrade, no reemplazo obligatorio de todo

### Referencias en este repo

- `docs/RUNE_WEIGHT_RL.md`
- `docs/SPELL_CAST_VISIBILITY.md`
- `docs/SPELL_EXORI_GRAN.md`
- `server/YurOTS/ots/data/spells/spells.xml`
- `server/YurOTS/ots/config.lua`

---

## 10. Soft boots y beneficios equipables con identidad

### Idea

Tomar items iconic retro y darles un uso claro y medible, en vez de dejarlos como decoracion o drop muerto.

En esta base, soft boots quedaron como item con:

- duracion real
- regeneracion periodica
- transformacion a worn al agotarse

### Por que valio la pena

- le da valor a un item clasico
- agrega economia secundaria
- el jugador siente el beneficio mientras lo usa

### Como migrarlo a otro server

Si portas este patron, intenta que el item tenga:

- un beneficio facil de notar
- duracion visible o intuible
- una version agotada o desgaste claro

### Riesgos

- si la regen es demasiado fuerte, compite con spells y vocation identity
- si no se comunica el desgaste, parece bug cuando “se rompe”

### Referencias en este repo

- `OTINFO`
- `server/YurOTS/ots/source/player.cpp`
- `server/YurOTS/ots/data/items/items.xml`

---

## 11. Operacion segura: esta idea tambien vale migrarla

### Idea

No todo lo valioso es gameplay.
Una de las lecciones mas importantes de este proyecto es separar bien:

- codigo versionado
- datos vivos de jugadores
- deploy
- rollback

### Por que valio la pena

- evita perder cuentas o personajes
- hace posible iterar sin miedo
- ordena mejor que cosas viven en Git y cuales no

### Como migrarlo a otro server

Aunque cambie tu stack, intenta preservar estas practicas:

1. El runtime de players no debe depender de Git.
2. Todo deploy debe tener backup previo.
3. Nunca mezclar “limpieza de repo” con datos vivos del server.
4. Documentar el flujo de rollback antes del proximo problema, no despues.

### Riesgos

- el error clasico es tratar `accounts/players` como si fueran codigo
- el segundo error clasico es hacer stash, clean o reset en produccion

### Referencias en este repo

- `docs/PROYECTO.md`
- `scripts/README-DEPLOY-VPS.md`

---

## Recomendacion de migracion por etapas

Si hubiera que portar estas ideas a otro server desde cero, el orden sugerido seria:

1. Seguridad operativa y separacion de datos vivos.
2. Confirmacion universal de NPCs.
3. Training con limite diario y no PvP.
4. NPCs de conveniencia y economia apoyada en banco.
5. Rage monsters.
6. Gemas e imbuements.
7. Bounty / Most Wanted.
8. Ajustes retro finos y spells custom.
9. Premium/promocion y perks mas delicados de balance.

## Cierre

Si hubiera que resumir la filosofia de este server en una frase, seria esta:

**mantener alma retro, pero sacar fricciones tontas y agregar sistemas que generen historias, economia y decision real sin destruir la identidad 7.6.**
