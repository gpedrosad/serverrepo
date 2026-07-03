#!/bin/bash
# consolidate-memory.sh
# Hook de auto-aprendizaje — registra el fin de sesión en MEMORY.md
# Invocado por el Stop hook de Claude Code al cerrar cada sesión
# Proyecto: Servidor YurOTS 7.6 (Retro76) — motor C++ + data Lua/XML + infra Docker/VPS

MEMORY_FILE="$(cd "$(dirname "$0")/../.." && pwd)/Contexto/MEMORY.md"
DATE=$(date '+%Y-%m-%d %H:%M')

# Crear sección de aprendizajes si no existe
if ! grep -q "## Aprendizajes del Equipo" "$MEMORY_FILE" 2>/dev/null; then
  printf "\n## Aprendizajes del Equipo\n\n" >> "$MEMORY_FILE"
fi

printf "\n--- Sesión cerrada: %s ---\n" "$DATE" >> "$MEMORY_FILE"
echo "✓ Hook consolidate-memory ejecutado. Revisar si hay aprendizajes pendientes en MEMORY.md"
