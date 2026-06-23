# Cliente Tibia 7.6 para YurOTS

Cliente **oficial 7.6** parcheado como `YurOTS.exe` (sin IP changer).

## Generar para compartir (Desktop + ZIP)

```bash
python3 scripts/patch-tibia760-client.py --desktop
```

Crea:

- `~/Desktop/YurOTS-Cliente-7.6/` — carpeta lista para enviar
- `~/Desktop/YurOTS-Cliente-7.6.zip` — comprimido listo para adjuntar

## Solo en el repo (desarrollo)

```bash
python3 scripts/patch-tibia760-client.py
```

Salida en `client-760/` (gitignored).

## Jugar en Mac (Wine)

```bash
./scripts/play-yurots-client.sh
```

## Requisito

Copia de Tibia 7.6 en `~/Downloads/tibia76/` con `Tibia.exe`, `Tibia.dat`, `Tibia.spr`, `Tibia.pic`.

Tras cambiar `ip` en `config.lua`, volvé a ejecutar el script con `--desktop`.
