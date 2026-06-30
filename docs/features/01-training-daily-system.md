# 01. Training diario controlado

## Que es

Sistema de training con limite diario por personaje, mensajes claros de uso/restante y salida automatica al templo cuando se acaba el tiempo.

En esta base el limite actual es de `120` minutos por dia, con Trainer Monks dedicados y una zona de training definida aparte.

## Por que valio la pena

- permite training AFK sin dejarlo infinito
- ordena la progresion de skills
- reduce abuso de macros pasivos
- es facil de explicar al jugador

## Que conviene conservar al portarlo

- contador por personaje y por dia real
- mensaje al entrar con usado/restante
- aviso de ultimos 5 minutos
- teletransporte automatico al terminar
- definicion explicita de la zona de training

## Riesgos

- si el reset diario usa mala fecha/huso, aparecen reinicios raros
- si el uso no persiste bien, algunos players podrian resetearlo
- si la salida del training esta mal definida, el player puede quedar atrapado

## Portabilidad

Alta. La idea no depende demasiado del motor; lo importante es persistencia diaria y control de zona.

## Referencias actuales

- `server/YurOTS/ots/source/player.cpp`
- `server/YurOTS/ots/data/trainingareas.xml`
- `server/YurOTS/ots/data/monster/trainer monk.xml`
- `OTINFO`
