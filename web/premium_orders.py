"""Pedidos premium: persistencia JSON + comprobantes en disco."""
from __future__ import annotations

import cgi
import json
import re
import time
import uuid
from pathlib import Path

from data import player_name_taken

PREMIUM_PLANS = {
    "1954": {"days": 7, "label": "1 semana", "price": 4000, "item_id": 1954},
    "2345": {"days": 14, "label": "2 semanas", "price": 6000, "item_id": 2345},
}
GOLDEN_AMULET_ID = 2130
GOLDEN_AMULET_PRICE = 2000
MAX_RECEIPT_BYTES = 5 * 1024 * 1024
ALLOWED_RECEIPT_EXT = frozenset({".jpg", ".jpeg", ".png", ".pdf", ".webp"})
CHAR_RE = re.compile(r"^[a-zA-Z ]{3,20}$")


def default_payment_info() -> dict:
    import os

    return {
        "holder": os.environ.get("PREMIUM_PAY_HOLDER", "Javier Pedrosa"),
        "rut": os.environ.get("PREMIUM_PAY_RUT", "19.295.136-4"),
        "account": os.environ.get("PREMIUM_PAY_ACCOUNT", "19295136"),
        "note": "Donación por transferencia. Adjunta el comprobante en el formulario.",
    }


def premium_config_payload() -> dict:
    def plan_entry(plan_id: str) -> dict:
        plan = PREMIUM_PLANS[plan_id]
        base = f"/assets/premium/{plan['item_id']}-small"
        return {
            "id": plan_id,
            "days": plan["days"],
            "label": plan["label"],
            "price": plan["price"],
            "image": f"{base}.jpg",
            "image2x": f"{base}@2x.jpg",
        }

    amulet_base = f"/assets/premium/{GOLDEN_AMULET_ID}-small"
    return {
        "plans": [plan_entry("1954"), plan_entry("2345")],
        "goldenAmulet": {
            "price": GOLDEN_AMULET_PRICE,
            "label": "Golden amulet",
            "desc": "El oro del botín va directo a tu cuenta bancaria.",
            "image": f"{amulet_base}.jpg",
            "image2x": f"{amulet_base}@2x.jpg",
        },
        "payment": default_payment_info(),
    }


def parse_multipart_form(handler) -> dict:
    content_type = handler.headers.get("Content-Type", "")
    if not content_type.startswith("multipart/form-data"):
        raise ValueError("Formato inválido.")
    length = int(handler.headers.get("Content-Length", "0"))
    if length <= 0 or length > MAX_RECEIPT_BYTES + 65536:
        raise ValueError("Petición inválida.")
    environ = {
        "REQUEST_METHOD": "POST",
        "CONTENT_TYPE": content_type,
        "CONTENT_LENGTH": str(length),
    }
    fs = cgi.FieldStorage(
        fp=handler.rfile,
        headers=handler.headers,
        environ=environ,
        keep_blank_values=True,
    )
    fields: dict = {"_receipt_bytes": b"", "_receipt_name": ""}
    items = fs.list if isinstance(fs.list, list) else []
    for field in items:
        name = field.name
        if not name:
            continue
        if name == "receipt" and getattr(field, "filename", None):
            fields["_receipt_bytes"] = field.file.read() if field.file else b""
            fields["_receipt_name"] = field.filename or ""
        else:
            fields[name] = field.value or ""
    return fields


def _load_orders(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _save_orders(path: Path, orders: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(orders, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def create_premium_order(
    *,
    orders_file: Path,
    uploads_dir: Path,
    players_dir: Path,
    character_name: str,
    plan_id: str,
    golden_amulet: bool,
    receipt_name: str,
    receipt_bytes: bytes,
    client_ip: str,
) -> dict:
    character_name = character_name.strip()
    plan = PREMIUM_PLANS.get(plan_id)
    if not plan:
        return {"ok": False, "message": "Plan premium inválido."}
    if not CHAR_RE.match(character_name):
        return {"ok": False, "message": "Nombre de personaje inválido (3-20 letras y espacios)."}
    if not player_name_taken(players_dir, character_name):
        return {"ok": False, "message": "No encontramos ese personaje. Revisa el nombre exacto."}
    if not receipt_bytes:
        return {"ok": False, "message": "Debes adjuntar el comprobante de pago."}
    if len(receipt_bytes) > MAX_RECEIPT_BYTES:
        return {"ok": False, "message": "El comprobante es muy grande (máx. 5 MB)."}

    ext = Path(receipt_name or "comprobante.jpg").suffix.lower()
    if ext not in ALLOWED_RECEIPT_EXT:
        return {"ok": False, "message": "Formato no permitido. Usa JPG, PNG o PDF."}

    total = plan["price"] + (GOLDEN_AMULET_PRICE if golden_amulet else 0)
    order_id = time.strftime("%Y%m%d") + "-" + uuid.uuid4().hex[:8]
    uploads_dir.mkdir(parents=True, exist_ok=True)
    receipt_path = uploads_dir / f"{order_id}{ext}"
    receipt_path.write_bytes(receipt_bytes)

    order = {
        "id": order_id,
        "created_at": int(time.time()),
        "status": "pending",
        "character_name": character_name,
        "plan_id": plan_id,
        "plan_label": plan["label"],
        "plan_price": plan["price"],
        "golden_amulet": golden_amulet,
        "golden_amulet_price": GOLDEN_AMULET_PRICE if golden_amulet else 0,
        "total_price": total,
        "receipt_file": receipt_path.name,
        "client_ip": client_ip,
    }

    orders = _load_orders(orders_file)
    orders.append(order)
    _save_orders(orders_file, orders[-200:])

    return {
        "ok": True,
        "message": f"Gracias por tu donación ({order_id}). Activaremos premium en «{character_name}» al confirmar el pago.",
        "order_id": order_id,
        "total": total,
    }
