"""jev: el modelo de decisión barato para las decisiones chicas de un mapa (solo mapas).

OpenRouter `typesafe/jev-router`: elige solo el modelo y el esfuerzo para cada pedido. Una decisión chica
(elegir de un menú, proponer 3 números, escribir un cartel) cuesta ~US$0,00005. Se usa para lo que es
gusto o criterio, no para lo que se puede medir: la geometría, las piezas y la validación son de código.

Reglas (docs/items-and-map/MAPAS.md#jev):
  - Clave en OPENROUTER_API_KEY (~/.config/retro76/openrouter.env). Nunca imprimirla ni commitearla.
  - SOLO para mapas. Para todo lo demás, opencode (ver memoria del proyecto).
  - Toda respuesta se valida en Python (`check`); si no sirve, se reintenta una vez y después se usa el
    `fallback` del que llama. Sin clave o con --no-jev, siempre el fallback: el mapa sale igual.
  - Las decisiones se guardan en `zones/<zona>.decisions.json`: regenerar no vuelve a preguntar (y da el
    mismo mapa). `--redecide` las borra.
  - Tope de gasto por corrida: MAPKIT_JEV_MAX_USD (0,05 por defecto). Cada llamada queda en
    ~/.cache/retro76/jev-log.jsonl con tokens y costo.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

MODEL = "typesafe/jev-router"
URL = "https://openrouter.ai/api/v1/chat/completions"
LOG = Path.home() / ".cache/retro76/jev-log.jsonl"
ENV_FILE = Path.home() / ".config/retro76/openrouter.env"
SYSTEM = ("You make small design decisions for a Tibia 7.6 map generator (an old 2D tile MMORPG). "
          "Answer ONLY with one JSON object matching the requested shape. Be concrete and brief.")


def _key() -> str | None:
    k = os.environ.get("OPENROUTER_API_KEY")
    if k:
        return k
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip().removeprefix("export ").strip()
            if line.startswith("OPENROUTER_API_KEY="):
                return line.split("=", 1)[1].strip().strip("'\"")
    return None


class Jev:
    def __init__(self, cache: Path | None, enabled=True, redecide=False, verbose=True):
        self.cache = cache
        self.enabled = enabled and _key() is not None
        self.verbose = verbose
        self.spent = 0.0
        self.calls = 0
        self.max_usd = float(os.environ.get("MAPKIT_JEV_MAX_USD", "0.05"))
        self.memory = {}
        if cache and cache.exists() and not redecide:
            self.memory = json.loads(cache.read_text())

    def _save(self):
        if self.cache:
            self.cache.write_text(json.dumps(self.memory, indent=1, ensure_ascii=False) + "\n")

    def _call(self, prompt: str) -> tuple[dict | None, dict]:
        body = {"model": MODEL, "messages": [{"role": "system", "content": SYSTEM},
                                             {"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"}, "usage": {"include": True}, "max_tokens": 4000}
        req = urllib.request.Request(URL, data=json.dumps(body).encode(), headers={
            "Authorization": "Bearer " + _key(), "Content-Type": "application/json",
            "X-Title": "map generator"})
        t0 = time.time()
        try:
            r = json.load(urllib.request.urlopen(req, timeout=120))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            return None, {"error": str(e)[:200]}
        usage = r.get("usage") or {}
        meta = {"model": r.get("model"), "cost": usage.get("cost", 0.0), "tokens": usage.get("total_tokens"),
                "seconds": round(time.time() - t0, 1)}
        try:
            text = r["choices"][0]["message"]["content"]
            if not text:        # el router a veces gasta todo en razonar y no contesta: cuenta como inválida
                return None, meta | {"error": f"sin contenido ({r['choices'][0].get('finish_reason')})"}
            text = text[text.index("{"):text.rindex("}") + 1]
            return json.loads(text), meta
        except (KeyError, IndexError, ValueError, TypeError):
            return None, meta | {"error": "respuesta sin JSON"}

    def decide(self, key: str, prompt: str, check, fallback):
        """Decisión `key` (se guarda). `check(dict)` devuelve el valor limpio o lanza ValueError."""
        if key in self.memory:
            try:
                return check(self.memory[key])
            except ValueError:
                pass
        if not self.enabled or self.spent >= self.max_usd:
            return fallback
        for attempt in range(2):
            ans, meta = self._call(prompt if attempt == 0 else
                                   prompt + "\n\nYour previous answer was invalid. Follow the shape exactly.")
            self.calls += 1
            self.spent += meta.get("cost") or 0.0
            LOG.parent.mkdir(parents=True, exist_ok=True)
            with LOG.open("a") as f:
                f.write(json.dumps({"t": time.strftime("%Y-%m-%d %H:%M:%S"), "key": key, **meta}) + "\n")
            if ans is None:
                continue
            try:
                value = check(ans)
            except (ValueError, KeyError, TypeError) as e:
                if self.verbose:
                    print(f"  jev {key}: respuesta inválida ({e})")
                continue
            self.memory[key] = ans
            self._save()
            if self.verbose:
                print(f"  jev {key}: {json.dumps(ans, ensure_ascii=False)[:160]}  ({meta.get('model')}, "
                      f"US${meta.get('cost', 0):.5f})")
            return value
        return fallback

    def summary(self) -> str:
        return f"jev: {self.calls} llamadas, US${self.spent:.4f}" + ("" if self.enabled else " (apagado: fallback)")
