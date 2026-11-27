"""Página privada de métricas: https://retro76.cl/stats/<STATS_TOKEN> (HTML), /summary.json y /llms.txt.

Pensada para que un bot (p. ej. el grokbot de Gonzalo) la lea y cuente qué pasa. Sin el token da 404.
Doc: docs/systems/METRICAS.md#url-para-bots.
"""
from __future__ import annotations

import html
import json

LLMS_TXT = """# Retro76 — métricas para bots

Retro76 es un OT server de Tibia 7.6 (juego retro online). Esta URL privada da todas sus métricas.

## URLs (reemplazar TOKEN)
- https://retro76.cl/stats/TOKEN/summary.json   → todo en JSON (parámetro opcional ?days=7..90, por defecto 30)
- https://retro76.cl/stats/TOKEN                → lo mismo en una página legible
- https://retro76.cl/stats/TOKEN/llms.txt       → esta guía

## Qué hay en summary.json
- generated_at, timezone: cuándo se generó (hora de Chile).
- server_now: estado del juego en este momento (online, players_online, players_peak, uptime_s).
- alerts: problemas a avisar ya (servidor caído, uptime < 100 %, reinicios, poca RAM, disco lleno, muchos logins fallidos).
- totals: sumas del período (visitantes web, páginas vistas, descargas, cuentas creadas, jugadores nuevos, logins,
  pico de online, de dónde llegan las visitas y locales de navegador).
- funnel: embudo de jugadores del período, paso por paso (visitó la web → descargó → abrió el cliente → creó cuenta →
  entró al juego → nivel 20/50/100 → promotion → abrió WhatsApp premium → premium activo → casa). `people` = personas
  únicas en ese paso; `from_web_visitors` = cuántas de ellas son IPs que visitaron la web en el período.
- daily: un objeto por día con:
  - game: muestras cada 5 min → uptime_pct, online_avg, online_peak, cpu_pct, ram_free_min_mb, yurots_mem_max_mb,
    net_in_gb/net_out_gb, restarts, disk_used_pct.
  - players: foto del día → accounts, characters, active_1d/7d/30d, premium_active, max_level, by_level,
    by_vocation, houses_owned.
  - access: accounts_created, accounts_played, first_time_players, game_logins, avg_session_min, login_fails, unique_ips.
  - web: visitors, pageviews, downloads_windows/mac, client_opens_unique (gente que abrió el cliente),
    updater_checks, page_langs, referrers (otservlist.org, google...), browser_locales (pt-BR = Brasil, es-CL =
    Chile...), top_pages, premium_funnel (tab_view → checkout_open → plan_select → step3 → submit_click = abrió WhatsApp).
  - funnel: hitos de ese día por paso.
- recent_funnel_events: últimos hitos (step, ts, ip_id, acc, name, level, platform, referrer...).
- recent_logins: últimos logins al juego (event, name, acc, reason, ip_id).

## Reglas de lectura
- Las cuentas del staff (GM) están excluidas de todo.
- ip_id es un hash corto de la IP: el mismo ip_id es la misma persona/conexión; no se publica la IP.
- Premium se cobra en USD y se paga por WhatsApp: submit_click es una intención, no un pago confirmado.
- Comparar contra días anteriores: crecimiento (cuentas nuevas, first_time_players), retención (active_1d vs 7d/30d),
  origen (referrers, browser_locales), conversión (funnel) y salud (alerts, uptime, RAM, reinicios).
"""


def _kv(d: dict) -> str:
    return ", ".join(f"{html.escape(str(k))} {html.escape(str(v))}" for k, v in (d or {}).items()) or "—"


def render_html(s: dict, token: str) -> str:
    now = s.get("server_now", {})
    t = s.get("totals", {})
    rows = []
    for d in reversed(s.get("daily", [])):
        g, a, w, p = d.get("game") or {}, d.get("access") or {}, d.get("web") or {}, d.get("players") or {}
        if not (g or w or any(a.values()) or p):
            continue
        rows.append(
            "<tr>" + "".join(f"<td>{html.escape(str(x))}</td>" for x in (
                d["date"], g.get("uptime_pct", "—"), g.get("online_avg", "—"), g.get("online_peak", "—"),
                p.get("active_1d", "—"), p.get("accounts", "—"), a.get("accounts_created", 0), a.get("first_time_players", 0),
                a.get("game_logins", 0), w.get("visitors", "—"), w.get("pageviews", "—"),
                (w.get("downloads_windows", 0) + w.get("downloads_mac", 0)) if w else "—", w.get("client_opens_unique", "—"),
                g.get("ram_free_min_mb", "—"), g.get("restarts", "—"))) + "</tr>")
    funnel = "".join(f"<tr><td>{html.escape(f['label'])}</td><td>{f['people']}</td><td>{f['from_web_visitors']}</td></tr>"
                     for f in s.get("funnel", []))
    events = "".join(
        f"<tr><td>{html.escape(str(e.get('ts', '')))}</td><td>{html.escape(str(e.get('step', '')))}</td>"
        f"<td>{html.escape(str(e.get('name', '') or ''))}</td><td>{html.escape(str(e.get('ip_id', '')))}</td>"
        f"<td>{html.escape(_kv({k: v for k, v in e.items() if k in ('platform', 'referrer', 'locale', 'landing', 'plan', 'total', 'level')}))}</td></tr>"
        for e in s.get("recent_funnel_events", [])[:60])
    alerts = "".join(f"<li>{html.escape(a)}</li>" for a in s.get("alerts", [])) or "<li>Sin alertas.</li>"
    base = f"/stats/{html.escape(token)}"
    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow"><meta http-equiv="refresh" content="60"><title>Retro76 · métricas</title>
<style>body{{font:14px/1.45 system-ui,sans-serif;margin:16px;background:#0f1115;color:#e6e6e6}}h1,h2{{font-weight:600}}
table{{border-collapse:collapse;margin:.5rem 0 1.5rem;font-variant-numeric:tabular-nums}}td,th{{border-bottom:1px solid #2a2e36;padding:4px 8px;text-align:left}}
th{{color:#9aa3b2;font-weight:500}}.k{{color:#9aa3b2}}a{{color:#e0b85a}}.wrap{{overflow-x:auto}}</style></head><body>
<h1>Retro76 · métricas</h1>
<p class="k">Generado {html.escape(s.get('generated_at', ''))} ({html.escape(s.get('timezone', ''))}) · se renueva cada minuto ·
<a href="{base}/summary.json">summary.json</a> · <a href="{base}/llms.txt">llms.txt</a></p>
<h2>Ahora</h2><p>Servidor {'en línea' if now.get('online') else '<b>CAÍDO</b>'} · online {now.get('players_online', 0)} ·
récord {now.get('players_peak', 0)} · uptime {round((now.get('uptime_s') or 0) / 3600, 1)} h</p>
<h2>Alertas</h2><ul>{alerts}</ul>
<h2>Últimos {s.get('period_days')} días</h2>
<p>Visitantes {t.get('web_visitors')} · páginas vistas {t.get('web_pageviews')} · descargas {t.get('downloads')} ·
cuentas nuevas {t.get('accounts_created')} · jugadores nuevos {t.get('first_time_players')} · logins {t.get('game_logins')} ·
pico online {t.get('online_peak')}</p>
<p><span class="k">De dónde llegan:</span> {_kv(t.get('referrers'))}<br><span class="k">Navegadores:</span> {_kv(t.get('browser_locales'))}</p>
<h2>Embudo</h2><div class="wrap"><table><tr><th>paso</th><th>personas</th><th>de visitantes web</th></tr>{funnel}</table></div>
<h2>Por día</h2><div class="wrap"><table><tr><th>día</th><th>uptime %</th><th>online prom</th><th>online pico</th><th>activos 1d</th>
<th>cuentas</th><th>cuentas nuevas</th><th>1ª vez</th><th>logins</th><th>visitantes</th><th>páginas</th><th>descargas</th>
<th>abrieron cliente</th><th>RAM libre mín</th><th>reinicios</th></tr>{''.join(rows)}</table></div>
<h2>Últimos hitos</h2><div class="wrap"><table><tr><th>hora (UTC)</th><th>paso</th><th>personaje</th><th>ip_id</th><th>detalle</th></tr>{events}</table></div>
</body></html>"""


def summary_json(s: dict) -> bytes:
    return json.dumps(s, ensure_ascii=False, indent=1).encode("utf-8")
