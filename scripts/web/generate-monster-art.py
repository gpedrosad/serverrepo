#!/usr/bin/env python3
"""Genera arte para la web (retrato, banner) de un monstruo con nano banana (Replicate).

Uso:
  export REPLICATE_API_TOKEN=r8_...        # nunca se guarda en disco ni en el repo
  python3 scripts/web/generate-monster-art.py \
      --reference docs/gameplay/img/black-dragon.png \
      --prompt-file prompt.txt --aspect 1:1 --out /tmp/retrato.png

--reference es una imagen del sprite del juego que se usa como referencia de diseño
(por ejemplo la vista previa de add_black_dragon_look.py). --aspect: 1:1, 16:9, 4:3,
match_input_image, etc. La salida es PNG; para la web conviene pasarla a JPG:
  sips -s format jpeg -s formatOptions 85 /tmp/retrato.png --out web/assets/monsters/NOMBRE-portrait.jpg

Solo para arte fijo: nano banana NO sirve para sprites animados (ver
docs/gameplay/CUSTOM_MONSTER_WORKFLOW.md).
"""
from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import sys
import time
import urllib.request
from pathlib import Path

API = "https://api.replicate.com/v1/models/google/nano-banana/predictions"


def call(token: str, payload: dict) -> dict:
    req = urllib.request.Request(API, data=json.dumps(payload).encode(), headers={
        "Authorization": "Bearer " + token, "Content-Type": "application/json", "Prefer": "wait=60"})
    result = json.load(urllib.request.urlopen(req, timeout=120))
    while result.get("status") in ("starting", "processing"):
        time.sleep(3)
        poll = urllib.request.Request(result["urls"]["get"], headers={"Authorization": "Bearer " + token})
        result = json.load(urllib.request.urlopen(poll, timeout=60))
    return result


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reference", type=Path, help="imagen de referencia (sprite del juego)")
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--prompt")
    group.add_argument("--prompt-file", type=Path)
    ap.add_argument("--aspect", default="1:1")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    token = os.environ.get("REPLICATE_API_TOKEN", "").strip()
    if not token:
        sys.exit("Falta REPLICATE_API_TOKEN en el entorno.")
    prompt = args.prompt if args.prompt else args.prompt_file.read_text(encoding="utf-8")

    payload = {"input": {"prompt": prompt, "aspect_ratio": args.aspect, "output_format": "png"}}
    if args.reference:
        mime = mimetypes.guess_type(args.reference.name)[0] or "image/png"
        data = base64.b64encode(args.reference.read_bytes()).decode()
        payload["input"]["image_input"] = [f"data:{mime};base64,{data}"]

    result = call(token, payload)
    if result.get("status") != "succeeded":
        sys.exit(f"Replicate: {result.get('status')} {result.get('error')}")
    output = result["output"] if isinstance(result["output"], str) else result["output"][0]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(output, args.out)
    print(f"Escrito {args.out}")


if __name__ == "__main__":
    main()
