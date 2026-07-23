"""Catálogo privado de items custom Zagan para /items."""
from __future__ import annotations

import json
import re
import shutil
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ZAGAN_MANIFEST = ROOT / "zagan-test" / "manifest.json"
ZAGAN_OTB = ROOT / "zagan-test" / "server-items" / "items.otb"
ZAGAN_PREVIEWS = ROOT / "zagan-test" / "previews"
PRIVATE_IMG_DIR = Path(__file__).resolve().parent / "private" / "zagan-items"
# Runtime override (gitignored). Canonical curated catalog for /items:
CURATED_CATALOG = Path(__file__).resolve().parent / "data" / "items_catalog.json"
CATALOG_FILE = Path(__file__).resolve().parent / "state" / "zagan_items_catalog.json"

IMAGE_EXT = re.compile(r"\.(png|jpe?g)$", re.I)

NODE_START = 0xFE
NODE_END = 0xFF
ESCAPE_CHAR = 0xFD

ITEM_ATTR_SERVERID = 0x10
ITEM_ATTR_CLIENTID = 0x11
ITEM_ATTR_NAME = 0x12
ITEM_ATTR_SLOT = 0x15
ITEM_ATTR_WEIGHT = 0x17
ITEM_ATTR_MAGLEVEL = 0x1B
ITEM_ATTR_WEAPON2 = 0x26
ITEM_ATTR_ARMOR2 = 0x28

GROUP_LABELS = {
    0: "none",
    1: "ground",
    2: "container",
    3: "weapon",
    4: "ammo",
    5: "armor",
    6: "rune",
    7: "teleport",
    8: "magicfield",
    9: "writeable",
    10: "key",
    11: "splash",
    12: "fluid",
}

WEAPON_LABELS = {
    0: "—",
    1: "sword",
    2: "club",
    3: "axe",
    4: "shield",
    5: "dist",
    6: "wand",
    7: "ammo",
}

SLOT_LABELS = {
    0: "default",
    1: "head",
    2: "body",
    3: "legs",
    4: "backpack",
    5: "weapon",
    6: "2h",
    7: "feet",
    8: "amulet",
    9: "ring",
    10: "hand",
}


def _safe_image_name(name: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+\.(png|jpe?g)", name, re.I):
        raise ValueError(f"invalid image name: {name}")
    return name


def _category(name: str) -> str:
    n = name.lower()
    if any(k in n for k in ("sword", "blade", "hammer", "axe", "bow", "wand", "rod", "maul", "lance", "crossbow", "dagger", "falchion", "saber", "fang", "crusher", "reaver", "emberblade", "chillblade")):
        return "Armas"
    if "shield" in n or "ward" in n or "disk" in n or "aegis" in n:
        return "Escudos"
    if "helm" in n or "crest" in n or "hood" in n or "visor" in n:
        return "Cascos"
    if "armor" in n or "plate" in n or "robe" in n or "mail" in n or "regalia" in n or "cape" in n:
        return "Armaduras"
    if "leg" in n or "greave" in n:
        return "Piernas"
    if "boot" in n:
        return "Botas"
    if "ring" in n or "amulet" in n or "talisman" in n or "sunstone" in n or "prism" in n or "orb" in n or "relic" in n:
        return "Accesorios"
    if "rune" in n:
        return "Runas"
    return "Otros"


def _read_escaped_byte(data: bytes, pos: int) -> tuple[int, int]:
    byte = data[pos]
    pos += 1
    if byte == ESCAPE_CHAR:
        byte = data[pos]
        pos += 1
    return byte, pos


def _parse_node(data: bytes, pos: int) -> tuple[tuple[int, bytes, list], int]:
    if data[pos] != NODE_START:
        raise ValueError("expected NODE_START")
    pos += 1
    node_type, pos = _read_escaped_byte(data, pos)
    props = bytearray()
    children: list = []
    while True:
        byte = data[pos]
        if byte == ESCAPE_CHAR:
            props.append(data[pos + 1])
            pos += 2
            continue
        if byte == NODE_START:
            child, pos = _parse_node(data, pos)
            children.append(child)
            continue
        if byte == NODE_END:
            pos += 1
            break
        props.append(byte)
        pos += 1
    return (node_type, bytes(props), children), pos


def _parse_item_props(props: bytes) -> tuple[bytes, list[tuple[int, bytes]]]:
    flags = props[:4]
    pos = 4
    blocks: list[tuple[int, bytes]] = []
    while pos < len(props):
        attr = props[pos]
        size = struct.unpack_from("<H", props, pos + 1)[0]
        start = pos + 3
        end = start + size
        blocks.append((attr, props[start:end]))
        pos = end
    return flags, blocks


def _block_payload(blocks: list[tuple[int, bytes]], attr_id: int) -> bytes | None:
    for attr, payload in blocks:
        if attr == attr_id:
            return payload
    return None


def _decode_otb_item(node_type: int, props: bytes) -> dict | None:
    _, blocks = _parse_item_props(props)
    server_payload = _block_payload(blocks, ITEM_ATTR_SERVERID)
    if not server_payload:
        return None

    server_id = struct.unpack("<H", server_payload)[0]
    if 20000 < server_id < 20100:
        server_id -= 20000

    client_payload = _block_payload(blocks, ITEM_ATTR_CLIENTID)
    name_payload = _block_payload(blocks, ITEM_ATTR_NAME)
    slot_payload = _block_payload(blocks, ITEM_ATTR_SLOT)
    weight_payload = _block_payload(blocks, ITEM_ATTR_WEIGHT)
    weapon_payload = _block_payload(blocks, ITEM_ATTR_WEAPON2)
    armor_payload = _block_payload(blocks, ITEM_ATTR_ARMOR2)
    mag_payload = _block_payload(blocks, ITEM_ATTR_MAGLEVEL)

    info: dict = {
        "serverId": server_id,
        "clientId": struct.unpack("<H", client_payload)[0] if client_payload else 0,
        "name": name_payload.decode("latin-1", errors="replace") if name_payload else "",
        "group": GROUP_LABELS.get(node_type, str(node_type)),
        "attack": None,
        "defence": None,
        "armor": None,
        "weight": None,
        "weaponType": None,
        "slot": None,
        "magLevel": None,
    }

    if slot_payload:
        info["slot"] = SLOT_LABELS.get(struct.unpack("<H", slot_payload)[0], "?")

    if weight_payload:
        info["weight"] = round(struct.unpack("<d", weight_payload)[0], 2)

    if weapon_payload and len(weapon_payload) >= 5:
        info["weaponType"] = WEAPON_LABELS.get(weapon_payload[0], str(weapon_payload[0]))
        info["attack"] = int(weapon_payload[3])
        info["defence"] = int(weapon_payload[4])

    if armor_payload and len(armor_payload) >= 10:
        info["armor"] = int(struct.unpack("<H", armor_payload[:2])[0])
        if info["weight"] is None:
            info["weight"] = round(struct.unpack("<d", armor_payload[2:10])[0], 2)

    if mag_payload:
        info["magLevel"] = int(struct.unpack("<H", mag_payload)[0])

    return info


def _load_otb_index() -> dict[int, dict]:
    if not ZAGAN_OTB.is_file():
        return {}
    data = ZAGAN_OTB.read_bytes()
    root, _ = _parse_node(data, 4)
    out: dict[int, dict] = {}
    for node_type, props, _ in root[2]:
        item = _decode_otb_item(node_type, props)
        if item:
            out[int(item["serverId"])] = item
    return out


def _stat(value: int | float | None) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)


def zagan_manifest_rows() -> list[dict]:
    if not ZAGAN_MANIFEST.is_file():
        return []

    manifest = json.loads(ZAGAN_MANIFEST.read_text(encoding="utf-8"))
    otb_index = _load_otb_index()
    rows: list[dict] = []

    for entry in manifest:
        server_id = int(entry["serverId"])
        client_id = int(entry["clientId"])
        name = str(entry["itemName"])
        prototype_id = int(entry["prototypeServerId"])
        prototype = otb_index.get(prototype_id) or {}
        stats = otb_index.get(server_id) or {}

        preview = Path(str(entry.get("preview", "")))
        image = preview.name if preview.name else f"{name.replace(' ', '_')}.png"

        rows.append(
            {
                "name": name,
                "category": _category(name),
                "serverId": server_id,
                "clientId": client_id,
                "spriteId": int(entry.get("spriteId", 0)),
                "prototypeServerId": prototype_id,
                "prototypeName": prototype.get("name") or "",
                "group": stats.get("group") or "—",
                "attack": stats.get("attack"),
                "defence": stats.get("defence"),
                "armor": stats.get("armor"),
                "weight": stats.get("weight"),
                "weaponType": stats.get("weaponType"),
                "slot": stats.get("slot"),
                "magLevel": stats.get("magLevel"),
                "image": image,
                "spawn": f"/i {server_id} 1",
            }
        )

    rows.sort(key=lambda row: row["serverId"])
    return rows


def sync_previews() -> int:
    PRIVATE_IMG_DIR.mkdir(parents=True, exist_ok=True)
    copied = 0
    for row in zagan_manifest_rows():
        src = ZAGAN_PREVIEWS / row["image"]
        if not src.is_file():
            continue
        dest_name = _safe_image_name(row["image"])
        shutil.copy2(src, PRIVATE_IMG_DIR / dest_name)
        copied += 1
    return copied


def build_catalog() -> list[dict]:
    return zagan_manifest_rows()


def write_catalog() -> list[dict]:
    CATALOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    catalog = build_catalog()
    CATALOG_FILE.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    return catalog


def sync_all() -> dict:
    copied = sync_previews()
    catalog = write_catalog()
    return {"images": copied, "items": len(catalog)}


def _read_catalog_file(path: Path) -> list[dict] | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if isinstance(data, list) and data:
        return data
    return None


def load_catalog() -> list[dict]:
    """Prefer curated /items catalog (VPS), then state override, then full Zagan pack."""
    for path in (CURATED_CATALOG, CATALOG_FILE):
        rows = _read_catalog_file(path)
        if rows is not None:
            return rows
    return build_catalog()


def image_path(name: str) -> Path | None:
    safe = _safe_image_name(name)
    path = (PRIVATE_IMG_DIR / safe).resolve()
    if not str(path).startswith(str(PRIVATE_IMG_DIR.resolve())):
        return None
    return path if path.is_file() else None
