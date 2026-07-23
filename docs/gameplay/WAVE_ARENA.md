# Wave Arena — oleadas desde el templo viejo

Arena PvE de oleadas: matás el pack, usás la palanca, viene la siguiente. Ranking semanal por personaje.

| Sistema | Portal templo viejo |
|---------|---------------------|
| El Crisol (bosses diarios) | `157, 54, 7` |
| **Wave Arena** | `159, 54, 7` |
| Hunt maze plano | `160, 54, 7` |
| Floor hunt (campus) | `162, 54, 7` |

---

## Flujo

1. Pisar TP `159, 54, 7` → landing `177, 394, 7`.
2. Palanca **izquierda** (uid `7100`): inicia / siguiente oleada.
3. Matar todos los monstruos en la sala 7×7.
4. Volver a usar la palanca → oleada N+1.
5. Palanca **derecha** (uid `7101`): ranking semanal (top 5) + tu mejor.
6. Retorno: tile `178, 395, 7` → `158, 54, 7`.

Si quedan criaturas, la palanca dice cuántas faltan. Si otro jugador tiene una corrida activa y sigue en la zona, no podés hijackearla.

---

## Oleadas (20)

Rat → Cave Rat → Hyaena → Poison Spider → Centipede → Larva → Scorpion → Orc Spearman → Bandit → War Wolf → Amazon → Valkyrie → Stalker → Assassin → Hunter → Mummy → Terror Bird → Gazer → Blue Djinn (×2) → Blue Djinn (×3).

---

## Archivos

| Archivo | Rol |
|---------|-----|
| `scripts/generate-wave-arena.py` | OTBM: arena + TPs + palancas |
| `data/actions/scripts/wave_arena.lua` | Lógica oleadas + ranking |
| `data/actions/actions.xml` | `uniqueid` 7100 / 7101 |
| `data/logs/wave_arena_rank.json` | Ranking semanal (runtime) |
| `data/world/generated-wave-arena.json` | Manifiesto |

Storage jugador: `9300` semana, `9301` mejor semana, `9302` mejor histórico.

---

## Regenerar mapa

```bash
python3 scripts/generate-wave-arena.py --replace
docker compose -f docker-compose.prod.yml restart yurots
```

Tras cambiar solo el `.lua` / `actions.xml`, basta restart (sin regenerar OTBM).

---

## Probar

```
/pos 159 54 7
# palanca izq → oleada 1
# matar → palanca → oleada 2
# palanca der → ranking
```

Relacionado: [`../items-and-map/MAPEAR_HUNT_MAZE.md`](../items-and-map/MAPEAR_HUNT_MAZE.md), [`../items-and-map/MAPEAR_FLOOR_HUNT.md`](../items-and-map/MAPEAR_FLOOR_HUNT.md).
