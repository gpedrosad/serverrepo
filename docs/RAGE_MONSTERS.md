# Monstruos Furiosos

Al matar un monstruo, **13% de chance** de que reviva al instante convertido en versión furiosa:

| Variante | Probabilidad | Grito |
|----------|-------------|-------|
| **Angry** | 10% | "GRAAAH! VOLVI MAS ENOJADO!" |
| **Furious** | 2% | "RAAAH! AHORA SI ESTOY FURIOSO!" |
| **Enraged** | 1% | "MI FURIA NO TIENE LIMITE!" |

### ¿Qué cambia?
- **Stats**: nivel, HP, daño, armadura, defensa, velocidad suben progresivamente
- **Experiencia**: 2x-4x más que el original
- **Loot**: mejorado (más gemas, platinum, items raros)
- **Nunca huyen** (`runonhealth=0`)
- **Mismo look**, ataques e inmunidades que el original

### Detalles
- Aplica a **42 familias** de monstruos (Demon, Dragon Lord, Behemoth, Warlock, etc.)
- No spawnan en zonas PZ ni PvP Arena
- Son criaturas adicionales — no afectan el respawn normal del spawnpoint
- El sistema es puro C++ (sin Lua), se gatilla automáticamente al morir cualquier monstruo
