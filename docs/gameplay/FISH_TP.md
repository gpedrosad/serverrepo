# Fish TP — pescar el teleporte

Pozo de agua en el templo: usás la **fishing rod** (`2580`) y te “pesca” hacia una lagoon con mobs. Animaciones de splash / energy al entrar y al spawnear criaturas.

| Sistema | Portal templo |
|---------|----------------|
| El Crisol | `157, 54, 7` |
| Wave Arena | `159, 54, 7` |
| Hunt maze | `160, 54, 7` |
| Arena de Fosos | `161, 54, 7` |
| Floor campus | `162, 54, 7` |
| **Fish TP** | agua `164, 54, 7` (no se pisa: se pesca) |
| Reloj de Arena | `166, 54, 7` |

Retorno: TP en la lagoon → `165, 54, 7`. Cartel `164, 53, 7`.

---

## Flujo

1. Parate junto al agua `164, 54, 7` (path alrededor).
2. Usá **fishing rod** sobre el agua.
3. Splash en el pozo + anillos/energy en el player.
4. Mensaje *Something huge bites…* → TP a `309, 392, 6`.
5. Spawn pack en la orilla con cloud → rings → pop/energy por mob.
6. Salida: TP sur de la shore → templo `165, 54, 7`.

Si la lagoon ya tiene criaturas (mas de 2), no re-spawnea pack (evita flood).

---

## Layout

| Z | Rol |
|---|-----|
| **z6** | Lagoon (shore `406` + agua `490`) |
| **z5** | Fondo neutro `405` |
| **z7** | Pozo templo + pad + cartel |

---

## Pack

| Mob | Cantidad |
|-----|----------|
| Crab | 3 |
| Crocodile | 2 |
| Snake | 2 |
| Tarantula | 1 |

Efectos (`spells.lua` / cliente 7.6): splash `1`, puff `2`, yellow rings `7`, energy area `10`, energy pop `11`, poison cloud `20`.

---

## Archivos

| Archivo | Rol |
|---------|-----|
| [`scripts/map/generate-fish-tp.py`](../../scripts/map/generate-fish-tp.py) | OTBM + cartel |
| `data/actions/scripts/fish_tp.lua` | Lógica + animaciones |
| `data/actions/scripts/fishing.lua` | `dofile` + hook al inicio de `onUse` |
| `data/world/generated-fish-tp.json` | Manifiesto |
| `data/readables.xml` | Bloque `FISH_TP_SIGNS` |

No usa uniqueid nuevo: el pozo se detecta por **coordenadas**.

---

## Regenerar

```bash
python3 scripts/map/generate-fish-tp.py --dry-run
python3 scripts/map/generate-fish-tp.py --replace
```

Solo Lua: restart OT.

---

## Probar

```
/i 2580 1
/pos 164 55 7
# usar rod en el agua 164,54,7
# matar pack → TP sur
```

Relacionado: [`SVAR_ARENA.md`](SVAR_ARENA.md), [`WAVE_ARENA.md`](WAVE_ARENA.md), [`../CAMBIAR-MAPA.md`](../CAMBIAR-MAPA.md).
