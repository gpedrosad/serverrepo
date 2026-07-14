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
MAX_RECEIPT_BYTES = 5 * 1024 * 1024
ALLOWED_RECEIPT_EXT = frozenset({".jpg", ".jpeg", ".png", ".pdf", ".webp"})
CHAR_RE = re.compile(r"^[a-zA-Z ]{3,20}$")

# Extras opcionales en checkout web (orden de visualización).
PREMIUM_ADDONS: tuple[dict, ...] = (
    {
        "key": "golden_amulet",
        "item_id": 2130,
        "price": 2000,
        "label": "Golden amulet",
        "desc": "El oro del botín va directo a tu cuenta bancaria.",
        "ext": "jpg",
    },
    {
        "key": "golden_ring",
        "item_id": 2179,
        "price": 2000,
        "label": "Golden ring",
        "desc": "+20% de oro de monstruos mientras lo llevas equipado.",
        "ext": "jpg",
    },
    {
        "key": "experience_recovery_rune",
        "item_id": 20131,
        "price": 2500,
        "label": "Experience recovery rune",
        "desc": "Recupera 60-80% de la exp perdida en tu última muerte.",
        "ext": "png",
    },
    {
        "key": "training_extension_rune",
        "item_id": 20132,
        "price": 1500,
        "label": "Training extension rune",
        "desc": "+12 horas de training ese día (una vez por personaje).",
        "ext": "png",
    },
    {
        "key": "private_trainer_dummy",
        "item_id": 20155,
        "price": 15000,
        "label": "Private trainer dummy",
        "desc": "Muñeco de entrenamiento para colocar en tu casa (1 por house, solo el dueño).",
        "ext": "png",
    },
)

GOLDEN_AMULET_ID = 2130
GOLDEN_AMULET_PRICE = 2000


def _addon_by_key(key: str) -> dict | None:
    for addon in PREMIUM_ADDONS:
        if addon["key"] == key:
            return addon
    return None


def _addon_images(item_id: int, ext: str) -> dict:
    base = f"/assets/premium/{item_id}-small"
    return {
        "image": f"{base}.{ext}",
        "image2x": f"{base}@2x.{ext}",
    }


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

    addons = []
    for addon in PREMIUM_ADDONS:
        imgs = _addon_images(addon["item_id"], addon["ext"])
        addons.append(
            {
                "key": addon["key"],
                "itemId": addon["item_id"],
                "price": addon["price"],
                "label": addon["label"],
                "desc": addon["desc"],
                **imgs,
            }
        )

    amulet = _addon_by_key("golden_amulet")
    amulet_imgs = _addon_images(amulet["item_id"], amulet["ext"]) if amulet else {}
    return {
        "plans": [plan_entry("1954"), plan_entry("2345")],
        "addons": addons,
        # Compat con JS/cache viejo
        "goldenAmulet": {
            "price": GOLDEN_AMULET_PRICE,
            "label": "Golden amulet",
            "desc": amulet["desc"] if amulet else "",
            **amulet_imgs,
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


def parse_addon_selections(fields: dict) -> dict[str, bool]:
    truthy = {"1", "true", "on", "yes"}
    return {
        addon["key"]: str(fields.get(addon["key"], "")).lower() in truthy
        for addon in PREMIUM_ADDONS
    }


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
    addon_selections: dict[str, bool],
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

    addon_lines: dict[str, dict] = {}
    addons_total = 0
    for addon in PREMIUM_ADDONS:
        selected = bool(addon_selections.get(addon["key"]))
        price = addon["price"] if selected else 0
        addon_lines[addon["key"]] = {
            "selected": selected,
            "price": price,
            "label": addon["label"],
            "item_id": addon["item_id"],
        }
        addons_total += price

    total = plan["price"] + addons_total
    order_id = time.strftime("%Y%m%d") + "-" + uuid.uuid4().hex[:8]
    uploads_dir.mkdir(parents=True, exist_ok=True)
    receipt_path = uploads_dir / f"{order_id}{ext}"
    receipt_path.write_bytes(receipt_bytes)

    golden_amulet = addon_lines["golden_amulet"]["selected"]
    order = {
        "id": order_id,
        "created_at": int(time.time()),
        "status": "pending",
        "character_name": character_name,
        "plan_id": plan_id,
        "plan_label": plan["label"],
        "plan_price": plan["price"],
        "addons": addon_lines,
        "addons_total": addons_total,
        "golden_amulet": golden_amulet,
        "golden_amulet_price": addon_lines["golden_amulet"]["price"],
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
