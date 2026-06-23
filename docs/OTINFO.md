# OTINFO — YurOTS

Servidor **Tibia 7.6** basado en YurOTS, hosteado en Docker. Cliente compatible: **7.6**.

---

## Rates y progresión

| Sistema | Multiplicador | Config |
|---------|---------------|--------|
| **Experiencia (monstruos)** | **×3** | `expmul = 3` |
| **Skills** (arma, dist, shield) | **×5** | `weaponmul`, `distmul`, `shieldmul` |
| **Magic level** | **×5** | `manamul` |
| Regeneración comida (hp/mana) | ×5 | `healthtickmul`, `manatickmul` |

Todos los multiplicadores de skill y ML aplican a **todas las vocaciones** por igual.

### Pérdida al morir

Al morir pierdes **7%** de: experiencia, mana gastada (ML), skills, equipo en slots y **100%** del contenido del backpack (`diepercent`).

---

## PvP

| Parámetro | Valor |
|-----------|-------|
| Tipo de mundo | **PvP** (`worldtype = "pvp"`) |
| Skulls activos | Sí (solo en mundos PvP) |
| PZ lock tras combatir | **10 segundos** (`pzlocked`) |

### Skulls y frags

| Evento | Efecto |
|--------|--------|
| Atacas a un jugador sin skull | **White skull** durante **1 minuto** |
| Matar jugador injustificado | +1 frag; white skull **15 minutos** |
| **3 frags** acumulados | **Red skull** |
| Duración red skull | **6 horas** |
| **6 frags** | Ban automático |
| Cada frag se absuelve | **1 frag cada 5 horas** (`fragtime = 5*60` min) |

Comando in-game: **`!frags`** — muestra frags injustificados y tiempo hasta perder el siguiente.

### Exp por matar jugador de nivel superior (underdog)

Si matas a alguien **de nivel mayor** que tú:

- Recibes **50%** de la experiencia que **él perdió** al morir.
- Repartido según **daño infligido** (si hubo ayuda).
- Mínimo **1 nivel** de diferencia (`pvpunderdogexp_mindiff = 1`).

*Ejemplo:* víctima lvl 80 pierde 7% de su exp → el killer recibe la mitad de ese monto (proporcional al daño).

---

## Combate y exhaust

| Acción | Cooldown |
|--------|----------|
| Hechizos / runas / acciones | **2 seg** (`exhausted = 2000 ms`) |
| Hechizos de cura | **1 seg** (`exhaustedheal = 1000 ms`) |
| Spam mientras exhaust | +300 ms extra (`exhaustedadd`) |

La velocidad de golpes físicos sigue la mecánica clásica 7.6 (sin exhaust artificial extra en melee).

---

## Capacidad y runas

- **Sistema de cap activo** (`capsystem = "yes"`).
- Peso de runas **por carga** (más cargas = más peso):
  - **IH / antidote:** 1.5 oz/carga (livianas)
  - **HMM, fields, etc.:** 2–5 oz/carga
  - **SD:** 6 oz/carga
  - **UH:** 10 oz/carga (pesadas)
  - **Blank rune:** 1 oz

---

## Mundo y mapa

| Elemento | Detalle |
|----------|---------|
| Mapa | `test.otbm` |
| Autosave | Cada **10 minutos** |
| Max jugadores | **28** |
| Casas | Sistema de houses activo |
| Depot | Hasta **1000** ítems |

---

## Contenido custom

### Monstruos

| Criatura | Descripción |
|----------|-------------|
| **Trainer Monk** | Dummy de entrenamiento: se cura, no deambula sobre fields, voces en español/chileno |
| **Elite Trainer Monk** | Igual que Trainer pero con `skillmul ×2` |
| **Angry Troll** | Aparece al matar un **Troll** normal (100%): mucha exp y loot generoso |

### Spells custom

| Spell | Vocación | Notas |
|-------|----------|-------|
| **`exori gran`** (Berzeker Gran) | Knight | AoE diamante, más daño y efectos visuales que `exori` |

Ver detalle técnico en [SPELL_EXORI_GRAN.md](SPELL_EXORI_GRAN.md).

---

## NPCs destacados

| NPC | Venta |
|-----|-------|
| **Dark Rodo** | Runas (HMM, UH, GFB, Explosion, SD, blank), varas y rods |
| **Perac** | Arcos, ballestas, flechas, **bolts**, **power bolts**, lanzas |

Precios runas (ej.): HMM 40 gp, UH 40 gp, GFB 60 gp, SD 90 gp, blank 5 gp.  
Power bolts: **50 por 400 gp** (decir `power bolt`; no confundir con `bolts` normales).

---

## Otros sistemas

| Sistema | Estado |
|---------|--------|
| Spells sin aprender previo | Sí (`learnspells = "no"`) |
| Summons | Máx. **2** (solo vocaciones con summon) |
| Spears | **50%** chance de perder al disparar |
| Burst arrows | Daño configurable (`burstarrowdmg`) |
| Death list | Últimas **10** muertes guardadas |
| Anti-AFK kick | **15 min** idle |
| Party | Sistema de party con iconos |
| Guilds | Sistema de guilds YurOTS |
| Rookgaard | Soporte activo en código |

---

## Conexión

| Parámetro | Valor |
|-----------|-------|
| Puerto | **7171** |
| Protocolo | **7.6** |
| IP pública (config) | Ver `config.lua` → `ip` |

---

## Archivos de configuración

Todo lo anterior se controla desde:

```
server/YurOTS/ots/config.lua
```

Tras cambiar `config.lua`, reinicia el servidor:

```bash
docker compose -f docker-compose.prod.yml restart yurots
```

Cambios en C++ (`source/`) requieren recompilar dentro del container:

```bash
docker exec yurots bash -c "cd /app/YurOTS/ots/source && make -j4"
```
