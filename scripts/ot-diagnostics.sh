#!/usr/bin/env bash
# Snapshot completo de salud: OT, web, red, recursos.
# Uso:
#   ./scripts/ot-diagnostics.sh           # imprime a stdout
#   ./scripts/ot-diagnostics.sh --append    # añade a /var/log/retro76/diagnostics.log
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

LOG_DIR="${RETRO76_LOG_DIR:-/var/log/retro76}"
APPEND="${1:-}"
STAMP="$(date -u '+%Y-%m-%d %H:%M:%S UTC')"
SEP="────────────────────────────────────────────────────────"

section() {
  echo ""
  echo "=== $1 ==="
}

run_block() {
  {
    echo "$SEP"
    echo "[$STAMP] retro76-diagnostics"
    section "host"
    echo "hostname: $(hostname -f 2>/dev/null || hostname)"
    echo "uptime: $(uptime -p 2>/dev/null || uptime)"
    section "resources"
    free -h 2>/dev/null || true
    df -h / /root 2>/dev/null | tail -n +1 || true
    section "docker yurots"
    if command -v docker >/dev/null; then
      docker ps -a --filter name=yurots --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' 2>/dev/null || true
      docker inspect yurots --format 'started={{.State.StartedAt}} restarts={{.RestartCount}} health={{if .State.Health}}{{.State.Health.Status}}{{else}}n/a{{end}}' 2>/dev/null || echo "container yurots no encontrado"
      echo "--- docker logs (últimas 40 líneas) ---"
      docker logs yurots --tail 40 2>&1 || true
      echo "--- patrones de crash en logs ---"
      docker logs yurots 2>&1 | grep -E "Could not load|Segmentation|Error:|Shutdown|GAME_STATE" | tail -15 || echo "(ninguno reciente)"
      echo "--- socket / listen (últimas 20) ---"
      docker logs yurots 2>&1 | grep -E "Player recv disconnect|Listen select failed|\[socket\]" | tail -20 || echo "(ninguno reciente)"
    else
      echo "docker no disponible"
    fi
    section "puerto 7171"
    ss -tan 2>/dev/null | grep 7171 || echo "(sin sockets 7171)"
    close_wait=$(ss -tan state close-wait 2>/dev/null | grep -c 7171 || echo 0)
    syn_sent=$(ss -tan state syn-sent 2>/dev/null | grep 7171 | wc -l || echo 0)
    echo "CLOSE-WAIT en 7171: $close_wait"
    echo "SYN-SENT hacia 7171: $syn_sent"
    section "probe OT (info)"
    if [[ -x "$ROOT/scripts/ot-probe.py" ]]; then
      python3 "$ROOT/scripts/ot-probe.py" 127.0.0.1 7171 --timeout 8 || true
    elif [[ -x "$ROOT/scripts/healthcheck-ot.sh" ]]; then
      "$ROOT/scripts/healthcheck-ot.sh" 127.0.0.1 7171 && echo "healthcheck OK" || echo "healthcheck FAIL"
    fi
    section "web (yurots-web)"
    if systemctl is-active --quiet yurots-web 2>/dev/null; then
      systemctl status yurots-web --no-pager -l 2>/dev/null | head -12 || true
      echo "--- web log (últimas 25 líneas) ---"
      tail -25 "${WEB_LOG_FILE:-$ROOT/web/logs/retro76-web.log}" 2>/dev/null || \
        tail -25 "$LOG_DIR/web.log" 2>/dev/null || echo "(sin log web)"
    else
      echo "yurots-web no activo (systemd)"
    fi
    section "watchdog"
    if [[ -f "$LOG_DIR/watchdog.log" ]]; then
      tail -15 "$LOG_DIR/watchdog.log"
    elif [[ -f /var/log/ot-watchdog.log ]]; then
      echo "(log legado /var/log/ot-watchdog.log — ejecutá install-ot-observability.sh)"
      tail -15 /var/log/ot-watchdog.log
    else
      echo "(sin log watchdog)"
    fi
    section "yurots.log (host)"
    ylog="$ROOT/server/YurOTS/ots/yurots.log"
    if [[ -f "$ylog" ]]; then
      echo "archivo: $ylog ($(wc -l < "$ylog" | tr -d ' ') líneas)"
      grep -E "Player recv disconnect|Listen select failed|Server Running" "$ylog" 2>/dev/null | tail -12 || echo "(sin patrones recientes)"
    else
      echo "(no existe $ylog — ¿docker-entrypoint activo?)"
    fi
    section "mapa / casas"
    otbm="$ROOT/server/YurOTS/ots/data/world/test.otbm"
    if [[ -f "$otbm" ]]; then
      echo "test.otbm: $(ls -lh "$otbm" | awk '{print $5, $6, $7, $8}')"
      python3 "$ROOT/scripts/sync-houses-with-map.py" --dry-run 2>&1 | tail -5 || true
    fi
    echo "$SEP"
  } 2>&1
}

output="$(run_block)"
echo "$output"

if [[ "$APPEND" == "--append" ]]; then
  mkdir -p "$LOG_DIR"
  echo "$output" >> "$LOG_DIR/diagnostics.log"
  # rotación simple: truncar si > 2MB
  if [[ -f "$LOG_DIR/diagnostics.log" ]]; then
    size=$(wc -c < "$LOG_DIR/diagnostics.log" | tr -d ' ')
    if [[ "$size" -gt 2097152 ]]; then
      tail -c 1572864 "$LOG_DIR/diagnostics.log" > "$LOG_DIR/diagnostics.log.tmp"
      mv "$LOG_DIR/diagnostics.log.tmp" "$LOG_DIR/diagnostics.log"
    fi
  fi
fi
