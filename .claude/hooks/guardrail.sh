#!/bin/bash
# guardrail.sh — PreToolUse hook (REFORZADO para servidor de producción)
# Intercepta operaciones peligrosas antes de que se ejecuten.
# Recibe JSON en stdin con { "tool_name": "...", "tool_input": { "command": "..." } }
# Exit 0 = permitir | Exit 2 = bloqueo duro (Claude no puede continuar la acción)
#
# Proyecto: Servidor YurOTS 7.6 (Retro76). Producción en VPS retro76.cl.
# La data runtime de jugadores (accounts/, players/, houseitems.xml) es SAGRADA:
# solo vive en el VPS y nunca se commitea ni se pisa en deploy.
#
# Nota: NO depende de python3/jq (en esta máquina python3 es el stub de MS Store).
# Extrae los campos con grep/sed puro.

INPUT=$(cat)

# Extraer tool_name (primer par "tool_name":"...")
TOOL=$(printf '%s' "$INPUT" | grep -oE '"tool_name"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed -E 's/.*"([^"]*)"[[:space:]]*$/\1/')

if [ "$TOOL" != "Bash" ]; then
  exit 0
fi

# Extraer command. Como puede contener comillas escapadas, para la DETECCIÓN
# usamos el INPUT crudo (el comando es la única fuente de estos patrones cuando
# la tool es Bash). Para el MENSAJE mostramos un best-effort del campo command.
COMMAND=$(printf '%s' "$INPUT" | grep -oE '"command"[[:space:]]*:[[:space:]]*"([^"\\]|\\.)*"' | head -1 | sed -E 's/^"command"[[:space:]]*:[[:space:]]*"//; s/"$//')
[ -z "$COMMAND" ] && COMMAND="$INPUT"

# Superficie de detección: todo el INPUT en minúsculas.
SCAN=$(printf '%s' "$INPUT" | tr '[:upper:]' '[:lower:]')

block() {
  echo "🚫 GUARDRAIL BLOQUEADO: $1"
  echo "   Comando interceptado: $COMMAND"
  exit 2
}

# --- BLOQUEO: git commit ---
if printf '%s' "$SCAN" | grep -qE '(^|&&|\||;|")\s*git\s+commit\b'; then
  block "Se detectó git commit. Los commits NO los ejecuta el agente — se sugieren al usuario al final."
fi

# --- BLOQUEO: git push ---
if printf '%s' "$SCAN" | grep -qE '(^|&&|\||;|")\s*git\s+push\b'; then
  block "Se detectó git push. Los push NO los ejecuta el agente — se sugieren al usuario al final."
fi

# --- BLOQUEO: comandos git PROHIBIDOS en el VPS (destruyen data de jugadores) ---
if printf '%s' "$SCAN" | grep -qE 'git\s+stash\s+[^"]*-[a-z]*u'; then
  block "'git stash -u' está PROHIBIDO (borra data untracked, incluida la de jugadores)."
fi
if printf '%s' "$SCAN" | grep -qE 'git\s+clean\b'; then
  block "'git clean' está PROHIBIDO (borra accounts/ y players/ reales)."
fi
if printf '%s' "$SCAN" | grep -qE 'git\s+reset\s+[^"]*--hard'; then
  block "'git reset --hard' está PROHIBIDO sin backup previo (puede pisar prod)."
fi

# --- BLOQUEO: intentar versionar data SAGRADA de jugadores ---
if printf '%s' "$SCAN" | grep -qE 'git\s+add\b[^"]*(data/accounts|data/players/|data/vip|houseitems\.xml|online\.xml|queue\.xml)'; then
  block "'git add' sobre data runtime de jugadores. accounts/, players/ reales, vip/, houseitems.xml NUNCA se commitean."
fi

# --- BLOQUEO: modificación/borrado a mano del binario compilado del motor ---
if printf '%s' "$SCAN" | grep -qE '\b(rm|mv|cp|sed\s+-i|tee|truncate)\b[^"]*source/yurots\b'; then
  block "Intento de modificar/borrar el binario compilado 'source/yurots'. Se regenera con make, no se parchea a mano."
fi

# --- ADVERTENCIA (no bloquea): borrado recursivo sobre data/, source/ o world/ ---
if printf '%s' "$SCAN" | grep -qE '\brm\s+-[rf]+\b[^"]*(data/|source/|world/)'; then
  echo "⚠️  GUARDRAIL ADVERTENCIA: Borrado recursivo sobre data/, source/ o world/."
  echo "   Confirmá que fue autorizado y que NO toca accounts/players/mapa en producción."
fi

# --- ADVERTENCIA (no bloquea): comando que toca el VPS de producción ---
if printf '%s' "$SCAN" | grep -qE 'deploy-vps\.sh|64\.176\.20\.238|ssh\s+root@'; then
  echo "⚠️  GUARDRAIL ADVERTENCIA: Comando que toca el VPS de producción (retro76.cl)."
  echo "   Verificá que el usuario pidió acción en producción (no solo debug local)."
fi

exit 0
