#!/usr/bin/env bash
# Comprueba si hay procesos RME zombie (UE) que impiden abrir el editor.
set -uo pipefail

count=0
while read -r pid state _; do
  [[ -n "${pid:-}" ]] || continue
  if [[ "$state" == *UE* ]]; then
    count=$((count + 1))
  fi
done < <(ps -ax -o pid= -o state= -o comm= 2>/dev/null | awk '$3 ~ /rme$/ || $3 ~ /\/rme$/ || $3 ~ /rme-yurots$/')

if [[ "$count" -ge 3 ]]; then
  echo "WARN: $count procesos RME colgados (UE). Reiniciá el Mac si el editor no abre." >&2
  if [[ "${FORCE_RME_LAUNCH:-0}" != "1" ]]; then
    osascript -e "display alert \"RME necesita reinicio del Mac\" message \"Hay $count procesos Remere bloqueados. Reiniciá el Mac y después abrí open-rme-zagan-terminal.command.\" as warning buttons {\"Entendido\"} default button \"Entendido\"" 2>/dev/null || true
    exit 1
  fi
fi
exit 0
