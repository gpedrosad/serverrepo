# devtools/ — clientes, RME y assets de desarrollo

Herramientas locales de cliente/mapa. **No son runtime del server** en el VPS.

En la raíz del repo quedan **symlinks** con los nombres históricos (`client-local`, `rme-client-760`, `zagan-test`, …) para que scripts y docs sigan funcionando sin cambios.

## Layout

| Ruta canónica | Symlink en raíz | Uso |
|---------------|-----------------|-----|
| `devtools/clients/client-local/` | `client-local` | OTClient local (juego diario) |
| `devtools/clients/client-local-zagan-test/` | `client-local-zagan-test` | Cliente con items Zagan test |
| `devtools/clients/cliente-oficial-retro/` | `cliente-oficial-retro` | Builds oficiales Retro76 (mac/win) |
| `devtools/clients/client-760/` | `client-760` | Cliente Tibia 7.60 clásico parcheado |
| `devtools/rme/rme-client-760/` | `rme-client-760` | `Tibia.dat` / `Tibia.spr` para RME |
| `devtools/rme/rme-client-760-zagan-test/` | `rme-client-760-zagan-test` | Assets RME + items Zagan |
| `devtools/rme/rme-zagan-test-root/` | `rme-zagan-test-root` | Árbol RME de trabajo Zagan |
| `devtools/rme/rme-extensions/` | `rme-extensions` | Extensiones RME (creatures, zagan items) |
| `devtools/zagan-test/` | `zagan-test` | Manifest + assets generados Zagan |

## Comandos habituales

```bash
./scripts/play-yurots-client.sh          # usa client-local
./scripts/play-zagan-test-client.sh      # usa client-local-zagan-test
./scripts/open-rme.sh                    # usa rme-client-760
./scripts/open-rme-zagan-test.sh         # usa árbol Zagan
```

## Canónicos

- **Jugar local:** `client-local`
- **RME mapa prod/test.otbm:** `rme-client-760` + `./scripts/open-rme.sh`
- **Items Zagan:** `zagan-test` + `install-zagan-test-env.sh`
