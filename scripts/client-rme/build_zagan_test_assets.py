#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import shutil
import struct
from dataclasses import dataclass
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = Path("/Users/gonzalo/Downloads/Zagan+Square")
MAP_OTBM = ROOT / "server" / "YurOTS" / "ots" / "data" / "world" / "test.otbm"
BASE_DAT = ROOT / "client-local" / "data" / "things" / "760" / "Tibia.dat"
BASE_SPR = ROOT / "client-local" / "data" / "things" / "760" / "Tibia.spr"
BASE_OTB = ROOT / "server" / "YurOTS" / "ots" / "data" / "items" / "items.otb"
BASE_XML = ROOT / "server" / "YurOTS" / "ots" / "data" / "items" / "items.xml"
OUT_DIR = ROOT / "zagan-test"
CUSTOM_SPRITES_DIR = OUT_DIR / "custom-sprites"

OTBM_TILE_AREA = 4
OTBM_TILE = 5
OTBM_ITEM = 6
OTBM_ATTR_ITEM = 9

# Never sacrifice client ids tied to map decoration (carpets, ship parts, etc.).
PROTECTED_NAME_KEYWORDS: tuple[str, ...] = (
    "carpet",
    "banner",
    "tapestry",
    "curtain",
    "painting",
    "picture",
    "roof",
    "grille",
    "hawser",
    "cleat",
    "ship",
    "butterfly",
    "botanist",
    "stalagmite",
    "rubbish",
    "monk",
    "monkey",
    "ventilation",
    "wooden",
    "flat roof",
    "stone wall",
    "stone monk",
    "stone monkey",
    "ginsen",
    "brooch",
    "pick",
)
NODE_START = 0xFE
NODE_END = 0xFF
ESCAPE_CHAR = 0xFD
THING_LAST_ATTR = 0xFF
CLIENT_VERSION = 760
SPRITE_SIZE = 32
MAGENTA = (255, 0, 255, 255)

ITEM_ATTR_SERVERID = 0x10
ITEM_ATTR_CLIENTID = 0x11
ITEM_ATTR_NAME = 0x12
ITEM_ATTR_DESCR = 0x13


@dataclass(frozen=True)
class ItemSpec:
    source_path: Path
    prototype_server_id: int
    item_name: str
    description: str
    dat_prototype_server_id: int | None = None


@dataclass
class DatItemEntry:
    client_id: int
    prefix: bytes
    sprite_ids: list[int]
    raw: bytes


@dataclass
class Node:
    node_type: int
    props: bytes
    children: list["Node"]


CORE_RESERVED_CLIENT_IDS: tuple[int, ...] = (5080, 5086, 5087, 5088, 5089)

# bmp file -> (display name, prototype server id)
BMP_ITEM_DEFS: dict[str, tuple[str, int]] = {
    "swords.bmp": ("vexon blade", 2409),
    "Shields.bmp": ("quarry ward", 2515),
    "helmet.bmp": ("morlen crest", 2457),
    "armor.bmp": ("ashlar plate", 2476),
    "legs.bmp": ("basalt greaves", 2477),
    "furious sword.bmp": ("irefang sword", 2409),
    "nicesword.bmp": ("gleamsteel saber", 2407),
    "sworden.bmp": ("nightglass dagger", 2383),
    "swordenn.bmp": ("silverwake sword", 2400),
    "swordens.bmp": ("sword of silence", 2407),
    "longie.bmp": ("reachbrand lance", 2414),
    "dishammer.bmp": ("rift hammer", 2391),
    "nicehammer.bmp": ("anvil song hammer", 2391),
    "zsshield1.bmp": ("mosaic shield", 2515),
    "zsshield2.bmp": ("brimstone aegis", 2516),
    "zsshield3.bmp": ("sunforge shield", 2520),
    "shieledero.bmp": ("bulwark disk", 2515),
    "helmeten.bmp": ("crimson helmet", 2498),
    "zsarm.bmp": ("tiled breastplate", 2476),
    "zsarm2.bmp": ("quarryguard armor", 2463),
    "zsarm3.bmp": ("obsidian regalia", 2472),
    "armoren.bmp": ("rubbleguard mail", 2487),
    "leg.bmp": ("marcher leggings", 2477),
    "leggins.bmp": ("cordovan leggings", 2477),
    "zslegs.bmp": ("kilnfire leggings", 2464),
    "shoen.bmp": ("wayfarer boots", 2643),
    "amulet.bmp": ("thornheart amulet", 2197),
    "amuleto.bmp": ("veilglass talisman", 2200),
    "robe.bmp": ("emberweft robe", 2656),
    "littlewizard.bmp": ("starbinder hood", 2457),
    "spell.bmp": ("experience recovery rune", 2260),
    "spell2.bmp": ("training extension rune", 2268),
    "spell3.bmp": ("lifewell rune", 2273),
    "spell4.bmp": ("emberstorm rune", 2304),
    "spell6.bmp": ("shattercall rune", 2313),
    "spellero.bmp": ("arcflash rune", 2311),
    "wot.bmp": ("flamecoil rune", 2302),
    "wot2.bmp": ("mireveil rune", 2285),
    "wot3.bmp": ("stonelock rune", 2293),
    "wot3spspel7.bmp": ("venomthread rune", 2292),
    "bob.bmp": ("storm maul", 2391),
    "ika.bmp": ("fury cape", 2654),
    "keko.bmp": ("granite mace", 2398),
    "sowe.bmp": ("windsting bow", 2456),
    "next.bmp": ("boltworker crossbow", 2455),
    "1.bmp": ("medusa sword", 2446),
    "44.bmp": ("hollow orb", 2168),
    "ohmy.bmp": ("crimson wand", 2187),
    "ohmy2.bmp": ("azure sunstone", 2168),
    "ohmy3.bmp": ("verdant sunstone", 2168),
    "ohmy4.bmp": ("violet sunstone", 2168),
    "wowwow.bmp": ("relic of ulm", 2168),
}

BMP_ITEM_DAT_PROTOTYPES: dict[str, int] = {
    # wand of inferno is 3 sprites in .dat; use a 1-sprite wand for client layout.
    "ohmy.bmp": 2162,
}

BMP_ITEM_DESCRIPTIONS: dict[str, str] = {
    "helmeten.bmp": "A crimson helm. Knights and paladins: +1 sword, club, axe and distance.",
    "ohmy.bmp": "A crimson wand for sorcerers and druids. Fast heavy magic missiles, 4 ML imbue.",
    "ika.bmp": "A blazing cape. Sorcerers and druids gain +1 magic level while wearing it.",
    "1.bmp": "A cursed blade with a petrifying gaze. Every hit against a player paralyzes them in PvP.",
}

# Gameplay pendiente de implementar en server/YurOTS (C++ / Lua).
ITEM_GAMEPLAY_SPECS: dict[str, dict[str, object]] = {
    "crimson helmet": {
        "vocations": ["knight", "paladin"],
        "skillBonus": {"sword": 1, "club": 1, "axe": 1, "distance": 1},
        "armorPrototype": "royal helmet",
        "armor": 9,
        "weight": 48.0,
        "slot": "head",
    },
    "crimson wand": {
        "vocations": ["sorcerer", "druid"],
        "minLevel": 33,
        "minDamage": 55,
        "maxDamage": 65,
        "mana": 13,
        "range": 5,
        "attackDelayMs": 667,
        "referenceWand": "wand of inferno",
        "referenceInfernoDamage": "60-70",
        "animation": "adori gran (NM_ANI_FIRE, NM_ME_EXPLOSION_DAMAGE / NM_ME_ENERGY_DAMAGE)",
        "attackType": "ATTACK_ENERGY",
        "imbueMlMax": 4,
    },
    "fury cape": {
        "vocations": ["sorcerer", "druid"],
        "magLevelBonus": 1,
        "armorPrototype": "cape",
        "armor": 1,
        "weight": 32.0,
        "slot": "body",
    },
    "medusa sword": {
        "attack": 42,
        "weaponType": "sword",
        "weaponPrototype": "the pharao sword",
        "slot": "hand",
        "pvpParalyzeOnHit": True,
    },
    "sword of silence": {
        "attack": 42,
        "defence": 30,
        "weaponType": "sword",
        "weaponPrototype": "bright sword",
        "slot": "hand",
        "pvpSilenceOnHit": True,
        "silenceChancePercent": 10,
        "silenceDurationMs": "2000-3000",
        "silenceCooldownPerTargetMs": 12000,
        "blocksSpokenSpellsOnly": True,
    },
}

# PNG/BMP extras living in zagan-test/custom-sprites/
CUSTOM_ITEM_DEFS: tuple[tuple[str, str, int, str], ...] = (
    (
        "fox_machina_helmet.png",
        "fox machina helmet",
        2457,
        "A white mecha helm with a green gaze.",
    ),
    (
        "chillan_shield.png",
        "chillan shield",
        2515,
        "Ice-rimmed stone with a molten vein.",
    ),
    (
        "southern_axe.png",
        "southern axe",
        2386,
        "Twin blades of frost and ember on a volcanic haft.",
    ),
)

CORE_BMP_ORDER: tuple[str, ...] = (
    "swords.bmp",
    "Shields.bmp",
    "helmet.bmp",
    "armor.bmp",
    "legs.bmp",
)


def infer_prototype(bmp_name: str) -> int:
    name = bmp_name.lower()
    if "shield" in name or "shiel" in name:
        return 2515
    if "helm" in name:
        return 2457
    if "armor" in name or "arm" in name or "cape" in name:
        return 2476
    if "leg" in name:
        return 2477
    if "shoe" in name or "boot" in name:
        return 2643
    if "amul" in name:
        return 2197
    if "robe" in name or "wizard" in name:
        return 2656
    if "hammer" in name:
        return 2391
    if "sword" in name or "longie" in name:
        return 2409
    if "wand" in name or "rod" in name:
        return 2187
    if "spell" in name or "wot" in name or "rune" in name:
        return 2260
    if "bow" in name or "sowe" in name:
        return 2456
    if "cross" in name or "next" in name:
        return 2455
    if "axe" in name or "ika" in name:
        return 2386
    if "mace" in name or "keko" in name:
        return 2398
    if "club" in name or "bob" in name:
        return 2421
    return 2168


def default_item_name(bmp_name: str) -> str:
    stem = Path(bmp_name).stem.strip().lower().replace("_", " ")
    return f"curio of {stem}"


def item_description(item_name: str) -> str:
    return f"A strange relic known as the {item_name}."


def build_item_specs(source_dir: Path, custom_dir: Path) -> tuple[ItemSpec, ...]:
    bmp_files = sorted(source_dir.glob("*.bmp"), key=lambda path: path.name.lower())
    if not bmp_files:
        raise SystemExit(f"No .bmp files found in {source_dir}")

    ordered_names: list[str] = []
    seen: set[str] = set()
    for bmp_name in CORE_BMP_ORDER:
        if (source_dir / bmp_name).is_file():
            ordered_names.append(bmp_name)
            seen.add(bmp_name.lower())
    for path in bmp_files:
        if path.name.lower() not in seen:
            ordered_names.append(path.name)
            seen.add(path.name.lower())

    specs: list[ItemSpec] = []
    for bmp_name in ordered_names:
        item_name, prototype_id = BMP_ITEM_DEFS.get(bmp_name, (default_item_name(bmp_name), infer_prototype(bmp_name)))
        description = BMP_ITEM_DESCRIPTIONS.get(bmp_name, item_description(item_name))
        specs.append(
            ItemSpec(
                source_path=source_dir / bmp_name,
                prototype_server_id=prototype_id,
                item_name=item_name,
                description=description,
                dat_prototype_server_id=BMP_ITEM_DAT_PROTOTYPES.get(bmp_name),
            )
        )
    return tuple(specs) + build_custom_item_specs(custom_dir)


def build_custom_item_specs(custom_dir: Path) -> tuple[ItemSpec, ...]:
    specs: list[ItemSpec] = []
    for filename, item_name, prototype_id, description in CUSTOM_ITEM_DEFS:
        source_path = custom_dir / filename
        if not source_path.is_file():
            raise SystemExit(f"Missing custom sprite: {source_path}")
        specs.append(
            ItemSpec(
                source_path=source_path,
                prototype_server_id=prototype_id,
                item_name=item_name,
                description=description,
            )
        )
    return tuple(specs)


ITEM_SPECS: tuple[ItemSpec, ...] = ()


class DatReader:
    def __init__(self, data: bytes, client_version: int = CLIENT_VERSION) -> None:
        self.data = data
        self.pos = 0
        self.client_version = client_version
        self.signature = self._u32()
        counts = struct.unpack_from("<HHHH", self.data, self.pos)
        self.pos += 8
        self.item_count, self.outfit_count, self.effect_count, self.missile_count = counts

    def _u8(self) -> int:
        value = self.data[self.pos]
        self.pos += 1
        return value

    def _u16(self) -> int:
        value = struct.unpack_from("<H", self.data, self.pos)[0]
        self.pos += 2
        return value

    def _u32(self) -> int:
        value = struct.unpack_from("<I", self.data, self.pos)[0]
        self.pos += 4
        return value

    def _skip_attr_payload(self, attr: int) -> None:
        if attr in (0, 8, 9, 25, 28, 29, 32, 34):
            self.pos += 2
        elif attr == 21:
            self.pos += 4
        elif attr == 24 and self.client_version >= 755:
            self.pos += 4
        elif attr == 33:
            self.pos += 6
            name_len = struct.unpack_from("<H", self.data, self.pos)[0]
            self.pos += name_len + 4

    def read_item_entries(self) -> tuple[list[DatItemEntry], bytes]:
        entries: list[DatItemEntry] = []
        for client_id in range(100, 100 + self.item_count):
            start = self.pos
            done = False
            while not done:
                attr = self._u8()
                if attr == THING_LAST_ATTR:
                    done = True
                    break
                if self.client_version >= 755 and attr == 23:
                    attr = 252
                self._skip_attr_payload(attr)

            width = self._u8()
            height = self._u8()
            if width > 1 or height > 1:
                self._u8()
            layers = self._u8()
            pattern_x = self._u8()
            pattern_y = self._u8()
            pattern_z = self._u8() if self.client_version >= 755 else 1
            anim_phases = self._u8()

            total = width * height * layers * pattern_x * pattern_y * pattern_z * anim_phases
            sprite_pos = self.pos
            sprite_ids = [self._u16() for _ in range(total)]
            end = self.pos

            entries.append(
                DatItemEntry(
                    client_id=client_id,
                    prefix=self.data[start:sprite_pos],
                    sprite_ids=sprite_ids,
                    raw=self.data[start:end],
                )
            )

        tail = self.data[self.pos :]
        return entries, tail


class SprReader:
    def __init__(self, data: bytes) -> None:
        self.data = data
        self.signature = struct.unpack_from("<I", data, 0)[0]
        self.sprite_count = struct.unpack_from("<H", data, 4)[0]
        self.offset_table_pos = 6
        self.offsets = [
            struct.unpack_from("<I", self.data, self.offset_table_pos + i * 4)[0]
            for i in range(self.sprite_count)
        ]

    def sprite_raw(self, sprite_id: int) -> bytes | None:
        offset = self.offsets[sprite_id - 1]
        if offset == 0:
            return None
        pixel_data_size = struct.unpack_from("<H", self.data, offset + 3)[0]
        end = offset + 5 + pixel_data_size
        return self.data[offset:end]


def read_escaped_byte(data: bytes, pos: int) -> tuple[int, int]:
    byte = data[pos]
    pos += 1
    if byte == ESCAPE_CHAR:
        byte = data[pos]
        pos += 1
    return byte, pos


def parse_node(data: bytes, pos: int) -> tuple[Node, int]:
    if data[pos] != NODE_START:
        raise ValueError(f"Expected NODE_START at {pos}, got {data[pos]:#x}")
    pos += 1
    node_type, pos = read_escaped_byte(data, pos)

    props = bytearray()
    children: list[Node] = []
    while True:
        byte = data[pos]
        if byte == ESCAPE_CHAR:
            props.append(data[pos + 1])
            pos += 2
            continue
        if byte == NODE_START:
            child, pos = parse_node(data, pos)
            children.append(child)
            continue
        if byte == NODE_END:
            pos += 1
            break
        props.append(byte)
        pos += 1

    return Node(node_type=node_type, props=bytes(props), children=children), pos


def escape_bytes(data: bytes) -> bytes:
    out = bytearray()
    for byte in data:
        if byte in (NODE_START, NODE_END, ESCAPE_CHAR):
            out.append(ESCAPE_CHAR)
        out.append(byte)
    return bytes(out)


def write_node(node: Node) -> bytes:
    out = bytearray([NODE_START])
    out.extend(escape_bytes(bytes([node.node_type])))
    out.extend(escape_bytes(node.props))
    for child in node.children:
        out.extend(write_node(child))
    out.append(NODE_END)
    return bytes(out)


def parse_item_props(props: bytes) -> tuple[bytes, list[tuple[int, bytes]]]:
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


def build_item_props(flags: bytes, blocks: list[tuple[int, bytes]]) -> bytes:
    out = bytearray(flags)
    for attr, payload in blocks:
        out.append(attr)
        out.extend(struct.pack("<H", len(payload)))
        out.extend(payload)
    return bytes(out)


def get_block_payload(blocks: list[tuple[int, bytes]], attr_id: int) -> bytes | None:
    for attr, payload in blocks:
        if attr == attr_id:
            return payload
    return None


def upsert_block(blocks: list[tuple[int, bytes]], attr_id: int, payload: bytes) -> list[tuple[int, bytes]]:
    out: list[tuple[int, bytes]] = []
    replaced = False
    for attr, existing in blocks:
        if attr == attr_id:
            out.append((attr_id, payload))
            replaced = True
        else:
            out.append((attr, existing))
    if not replaced:
        out.append((attr_id, payload))
    return out


def load_sprite(path: Path) -> Image.Image:
    image = Image.open(path).convert("RGBA")
    pixels = []
    for pixel in image.getdata():
        red, green, blue, alpha = pixel
        if pixel == MAGENTA or (red, green, blue) == (0, 0, 0):
            pixels.append((0, 0, 0, 0))
        elif alpha == 0:
            pixels.append((0, 0, 0, 0))
        else:
            pixels.append(pixel)
    image.putdata(pixels)
    if image.size != (SPRITE_SIZE, SPRITE_SIZE):
        image = image.resize((SPRITE_SIZE, SPRITE_SIZE), Image.Resampling.LANCZOS)
    return image


def load_custom_sprite(path: Path) -> Image.Image:
    """PNG imports from custom-sprites: tighter black-key and crop for JPEG/halos."""
    image = Image.open(path).convert("RGBA")
    pixels = []
    for pixel in image.getdata():
        red, green, blue, alpha = pixel
        if pixel == MAGENTA or (red, green, blue) == (0, 0, 0):
            pixels.append((0, 0, 0, 0))
        elif max(red, green, blue) <= 30:
            pixels.append((0, 0, 0, 0))
        elif alpha == 0:
            pixels.append((0, 0, 0, 0))
        else:
            pixels.append(pixel)
    image.putdata(pixels)
    bbox = image.getbbox()
    if bbox:
        image = image.crop(bbox)
    if image.size != (SPRITE_SIZE, SPRITE_SIZE):
        resample = Image.Resampling.NEAREST if max(image.size) > SPRITE_SIZE * 2 else Image.Resampling.LANCZOS
        image = image.resize((SPRITE_SIZE, SPRITE_SIZE), resample)
    return image


def encode_sprite_record(image: Image.Image) -> bytes:
    if image.size != (32, 32):
        raise ValueError(f"Expected 32x32 sprite, got {image.size}")

    pixels = list(image.getdata())
    payload = bytearray()
    idx = 0
    total = len(pixels)

    while idx < total:
        transparent = 0
        while idx < total and pixels[idx][3] == 0:
            transparent += 1
            idx += 1

        colored = bytearray()
        while idx < total and pixels[idx][3] != 0:
            colored.extend(pixels[idx][:3])
            idx += 1

        if transparent == 0 and not colored and idx >= total:
            break
        if transparent == total:
            break

        payload.extend(struct.pack("<HH", transparent, len(colored) // 3))
        payload.extend(colored)

        if idx >= total and transparent > 0 and not colored:
            break

    record = bytearray(b"\xff\x00\xff")
    record.extend(struct.pack("<H", len(payload)))
    record.extend(payload)
    return bytes(record)


def write_spr(signature: int, sprite_records: list[bytes | None]) -> bytes:
    out = bytearray()
    out.extend(struct.pack("<I", signature))
    out.extend(struct.pack("<H", len(sprite_records) - 1))

    offsets: list[int] = []
    payloads = bytearray()
    header_size = 6 + (len(sprite_records) - 1) * 4

    for record in sprite_records[1:]:
        if record is None:
            offsets.append(0)
        else:
            offsets.append(header_size + len(payloads))
            payloads.extend(record)

    for offset in offsets:
        out.extend(struct.pack("<I", offset))
    out.extend(payloads)
    return bytes(out)


def write_dat(
    signature: int,
    item_count: int,
    outfit_count: int,
    effect_count: int,
    missile_count: int,
    item_entries: list[bytes],
    tail: bytes,
) -> bytes:
    out = bytearray()
    out.extend(struct.pack("<I", signature))
    out.extend(struct.pack("<HHHH", item_count, outfit_count, effect_count, missile_count))
    for entry in item_entries:
        out.extend(entry)
    out.extend(tail)
    return bytes(out)


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def read_props(data: bytes, pos: int) -> tuple[bytes, int]:
    out = bytearray()
    while pos < len(data):
        byte = data[pos]
        pos += 1
        if byte in (NODE_START, NODE_END):
            pos -= 1
            break
        if byte == ESCAPE_CHAR:
            if pos >= len(data):
                raise ValueError("OTBM truncado")
            out.append(data[pos])
            pos += 1
        else:
            out.append(byte)
    return bytes(out), pos


def load_map_server_ids(otbm_path: Path) -> set[int]:
    """Server item ids placed on test.otbm — their client ids must not be sacrificed."""
    if not otbm_path.is_file():
        return set()

    raw = otbm_path.read_bytes()
    pos = 4
    if pos >= len(raw) or raw[pos] != NODE_START:
        return set()
    pos += 2
    _, pos = read_props(raw, pos)
    body = raw[pos:]

    server_ids: set[int] = set()

    def walk(pos: int, area_base: tuple[int, int, int]) -> int:
        if pos >= len(body) or body[pos] != NODE_START:
            return pos
        pos += 1
        ntype = body[pos]
        pos += 1
        props, pos = read_props(body, pos)
        local = area_base
        if ntype == OTBM_TILE_AREA and len(props) >= 5:
            bx, by, bz = struct.unpack_from("<HHB", props, 0)
            local = (bx, by, bz)
        elif ntype == OTBM_TILE and len(props) >= 2:
            p = 2
            while p < len(props):
                attr = props[p]
                p += 1
                if attr == OTBM_ATTR_ITEM and p + 2 <= len(props):
                    server_ids.add(struct.unpack_from("<H", props, p)[0])
                    p += 2
                    continue
                p += 1
        elif ntype == OTBM_ITEM and len(props) >= 2:
            server_ids.add(struct.unpack_from("<H", props, 0)[0])

        depth = 1
        while pos < len(body) and depth > 0:
            if body[pos] == NODE_START:
                pos = walk(pos, local)
            elif body[pos] == NODE_END:
                pos += 1
                depth -= 1
            else:
                pos += 1
        return pos

    walk(0, (0, 0, 0))
    return server_ids


def build_protected_client_ids(
    map_server_ids: set[int],
    otb_server_to_client: dict[int, int],
    otb_client_to_name: dict[int, str],
) -> set[int]:
    protected: set[int] = set()
    for server_id in map_server_ids:
        client_id = otb_server_to_client.get(server_id)
        if client_id is not None:
            protected.add(client_id)
    # Carpet ranges used heavily in RME brushes even when not yet painted on test.otbm.
    for server_id in range(1794, 1803):
        client_id = otb_server_to_client.get(server_id)
        if client_id is not None:
            protected.add(client_id)
    for server_id in range(4394, 4403):
        client_id = otb_server_to_client.get(server_id)
        if client_id is not None:
            protected.add(client_id)
    for client_id, name in otb_client_to_name.items():
        lower = name.lower()
        if any(keyword in lower for keyword in PROTECTED_NAME_KEYWORDS):
            protected.add(client_id)
    return protected


# OTClient 7.6 loads ids 100..item_count from the dat header. Extending item_count
# without reshaping the whole item section misaligns outfits and breaks loadDat().
# Reuse obscure 1-sprite ids already inside that range. Never sacrifice client ids
# used by tiles on test.otbm or common map-decoration names (carpets, ship parts, etc.).


def discover_sacrifice_client_ids(
    item_entries: list[DatItemEntry],
    otb_client_to_server: dict[int, int],
    action_item_ids: set[int],
    protected_client_ids: set[int],
    reserved: set[int],
    needed: int,
    max_client_id: int,
) -> list[int]:
    slots: list[int] = []
    for entry in item_entries:
        client_id = entry.client_id
        if client_id in reserved or client_id in protected_client_ids or client_id > max_client_id:
            continue
        if len(entry.sprite_ids) != 1:
            continue
        server_id = otb_client_to_server.get(client_id)
        if server_id is not None and server_id in action_item_ids:
            continue
        slots.append(client_id)
    slots = sorted(set(slots), reverse=True)
    if len(slots) < needed:
        raise SystemExit(
            f"Need {needed} reusable 1-sprite client ids (max {max_client_id}), found {len(slots)}. "
            f"Protected {len(protected_client_ids)} map/decor client ids."
        )
    return slots[:needed]


def patch_item_sprite(entry: DatItemEntry, prototype_prefix: bytes, sprite_id: int) -> bytes:
    return prototype_prefix + struct.pack("<H", sprite_id)


def remove_otb_nodes_for_client_ids(root: Node, client_ids: set[int]) -> None:
    kept: list[Node] = []
    for child in root.children:
        _, blocks = parse_item_props(child.props)
        client_payload = get_block_payload(blocks, ITEM_ATTR_CLIENTID)
        if client_payload is not None and len(client_payload) == 2:
            client_id = struct.unpack("<H", client_payload)[0]
            if client_id in client_ids:
                continue
        kept.append(child)
    root.children = kept


def main() -> None:
    if not SOURCE_DIR.is_dir():
        raise SystemExit(f"Missing source directory: {SOURCE_DIR}")

    item_specs = build_item_specs(SOURCE_DIR, CUSTOM_SPRITES_DIR)

    ensure_dir(OUT_DIR)
    ensure_dir(CUSTOM_SPRITES_DIR)
    ensure_dir(OUT_DIR / "previews")
    ensure_dir(OUT_DIR / "server-items")
    ensure_dir(OUT_DIR / "rme-client-760-zagan-test")
    ensure_dir(OUT_DIR / "client-things" / "760")

    dat_reader = DatReader(BASE_DAT.read_bytes())
    item_entries, dat_tail = dat_reader.read_item_entries()
    spr_reader = SprReader(BASE_SPR.read_bytes())

    otb_data = BASE_OTB.read_bytes()
    root, end_pos = parse_node(otb_data, 4)
    if end_pos != len(otb_data):
        raise SystemExit(f"Unexpected trailing bytes in items.otb: parsed {end_pos} of {len(otb_data)}")

    server_id_to_node: dict[int, Node] = {}
    max_server_id = 0
    for child in root.children:
        flags, blocks = parse_item_props(child.props)
        server_payload = get_block_payload(blocks, ITEM_ATTR_SERVERID)
        if server_payload is None or len(server_payload) != 2:
            continue
        server_id = struct.unpack("<H", server_payload)[0]
        server_id_to_node[server_id] = child
        max_server_id = max(max_server_id, server_id)

    if len(CORE_RESERVED_CLIENT_IDS) > len(item_specs):
        raise SystemExit("CORE_RESERVED_CLIENT_IDS is longer than the item spec list")

    otb_client_to_server: dict[int, int] = {}
    otb_server_to_client: dict[int, int] = {}
    otb_client_to_name: dict[int, str] = {}
    for child in root.children:
        _, blocks = parse_item_props(child.props)
        server_payload = get_block_payload(blocks, ITEM_ATTR_SERVERID)
        client_payload = get_block_payload(blocks, ITEM_ATTR_CLIENTID)
        name_payload = get_block_payload(blocks, ITEM_ATTR_NAME)
        if server_payload is None or client_payload is None:
            continue
        if len(server_payload) != 2 or len(client_payload) != 2:
            continue
        server_id = struct.unpack("<H", server_payload)[0]
        client_id = struct.unpack("<H", client_payload)[0]
        otb_client_to_server[client_id] = server_id
        otb_server_to_client[server_id] = client_id
        if name_payload:
            otb_client_to_name[client_id] = name_payload.decode("latin-1")

    map_server_ids = load_map_server_ids(MAP_OTBM)
    protected_client_ids = build_protected_client_ids(
        map_server_ids, otb_server_to_client, otb_client_to_name
    )
    print(
        f"Protecting {len(protected_client_ids)} client ids "
        f"({len(map_server_ids)} item server ids on {MAP_OTBM.name})"
    )

    action_item_ids = {
        int(match)
        for match in re.findall(r'itemid="(\d+)"', BASE_XML.read_text(encoding="utf-8"))
    }
    actions_path = ROOT / "server" / "YurOTS" / "ots" / "data" / "actions" / "actions.xml"
    if actions_path.is_file():
        action_item_ids.update(
            int(match) for match in re.findall(r'itemid="(\d+)"', actions_path.read_text(encoding="utf-8"))
        )

    original_item_count = dat_reader.item_count
    max_client_id = original_item_count
    reserved_client_ids = set(CORE_RESERVED_CLIENT_IDS[: len(item_specs)])
    zagan_client_ids = list(CORE_RESERVED_CLIENT_IDS[: min(len(item_specs), len(CORE_RESERVED_CLIENT_IDS))])
    extra_needed = len(item_specs) - len(zagan_client_ids)
    if extra_needed > 0:
        zagan_client_ids.extend(
            discover_sacrifice_client_ids(
                item_entries,
                otb_client_to_server,
                action_item_ids,
                protected_client_ids,
                reserved_client_ids,
                extra_needed,
                max_client_id,
            )
        )
    next_sprite_id = spr_reader.sprite_count + 1
    next_server_id = max(max_server_id + 1, 20100)

    entry_index_by_client_id = {entry.client_id: index for index, entry in enumerate(item_entries)}

    missing_client_ids = [client_id for client_id in zagan_client_ids if client_id not in entry_index_by_client_id]
    if missing_client_ids:
        raise SystemExit(
            "Dat file is missing entries for Zagan client ids: "
            + ", ".join(str(client_id) for client_id in missing_client_ids)
        )

    # Keep sacrificed OTB rows so existing map tiles still resolve their server ids.
    # Dat sprites for reused client ids are patched in the client pack.
    new_item_entries: list[bytes] = [entry.raw for entry in item_entries]
    sprite_records: list[bytes | None] = [None]
    sprite_records.extend(spr_reader.sprite_raw(sprite_id) for sprite_id in range(1, spr_reader.sprite_count + 1))

    manifest: list[dict[str, object]] = []

    for spec, zagan_client_id in zip(item_specs, zagan_client_ids):
        source_path = spec.source_path
        if not source_path.is_file():
            raise SystemExit(f"Missing source sprite: {source_path}")

        prototype_node = server_id_to_node.get(spec.prototype_server_id)
        if prototype_node is None:
            raise SystemExit(f"Prototype server id {spec.prototype_server_id} not found in items.otb")

        dat_prototype_server_id = spec.dat_prototype_server_id or spec.prototype_server_id
        dat_prototype_node = server_id_to_node.get(dat_prototype_server_id)
        if dat_prototype_node is None:
            raise SystemExit(f"Dat prototype server id {dat_prototype_server_id} not found in items.otb")

        prototype_client_id = None
        prototype_entry = None
        flags, blocks = parse_item_props(prototype_node.props)
        _, dat_blocks = parse_item_props(dat_prototype_node.props)
        dat_client_payload = get_block_payload(dat_blocks, ITEM_ATTR_CLIENTID)
        if dat_client_payload is None or len(dat_client_payload) != 2:
            raise SystemExit(f"Dat prototype server id {dat_prototype_server_id} has no client id payload")
        dat_prototype_client_id = struct.unpack("<H", dat_client_payload)[0]

        client_payload = get_block_payload(blocks, ITEM_ATTR_CLIENTID)
        if client_payload is None or len(client_payload) != 2:
            raise SystemExit(f"Prototype server id {spec.prototype_server_id} has no client id payload")
        prototype_client_id = struct.unpack("<H", client_payload)[0]

        for entry in item_entries:
            if entry.client_id == dat_prototype_client_id:
                prototype_entry = entry
                break
        if prototype_entry is None:
            raise SystemExit(f"Dat prototype client id {dat_prototype_client_id} not found in Tibia.dat")
        if len(prototype_entry.sprite_ids) != 1:
            raise SystemExit(
                f"Dat prototype client id {dat_prototype_client_id} is not a simple 1-sprite item (has {len(prototype_entry.sprite_ids)})"
            )

        if source_path.parent.resolve() == CUSTOM_SPRITES_DIR.resolve():
            image = load_custom_sprite(source_path)
        else:
            image = load_sprite(source_path)
        preview_path = OUT_DIR / "previews" / f"{spec.item_name.replace(' ', '_')}.png"
        image.save(preview_path, "PNG")

        sprite_record = encode_sprite_record(image)
        sprite_records.append(sprite_record)
        new_sprite_id = next_sprite_id
        next_sprite_id += 1

        new_client_id = zagan_client_id
        slot_index = entry_index_by_client_id[new_client_id]
        new_item_entries[slot_index] = patch_item_sprite(
            item_entries[slot_index],
            prototype_entry.prefix,
            new_sprite_id,
        )

        new_server_id = next_server_id
        next_server_id += 1

        descr_bytes = spec.description.encode("latin-1")
        if len(descr_bytes) >= 128:
            raise SystemExit(
                f"Description too long for OTB ({len(descr_bytes)} bytes, max 127): {spec.item_name!r}"
            )
        new_blocks = upsert_block(blocks, ITEM_ATTR_SERVERID, struct.pack("<H", new_server_id))
        new_blocks = upsert_block(new_blocks, ITEM_ATTR_CLIENTID, struct.pack("<H", new_client_id))
        new_blocks = upsert_block(new_blocks, ITEM_ATTR_NAME, spec.item_name.encode("latin-1"))
        new_blocks = upsert_block(new_blocks, ITEM_ATTR_DESCR, descr_bytes)
        root.children.append(Node(node_type=prototype_node.node_type, props=build_item_props(flags, new_blocks), children=[]))

        manifest_entry: dict[str, object] = {
            "itemName": spec.item_name,
            "sourceBmp": str(source_path),
            "prototypeServerId": spec.prototype_server_id,
            "prototypeClientId": prototype_client_id,
            "datPrototypeServerId": dat_prototype_server_id,
            "serverId": new_server_id,
            "clientId": new_client_id,
            "spriteId": new_sprite_id,
            "preview": str(preview_path.relative_to(ROOT)),
        }
        gameplay = ITEM_GAMEPLAY_SPECS.get(spec.item_name)
        if gameplay:
            manifest_entry["gameplaySpec"] = gameplay
        manifest.append(manifest_entry)

    dat_out = write_dat(
        signature=dat_reader.signature,
        item_count=original_item_count,
        outfit_count=dat_reader.outfit_count,
        effect_count=dat_reader.effect_count,
        missile_count=dat_reader.missile_count,
        item_entries=new_item_entries,
        tail=dat_tail,
    )
    spr_out = write_spr(signature=spr_reader.signature, sprite_records=sprite_records)
    otb_out = b"\x00\x00\x00\x00" + write_node(root)

    client_things_dir = OUT_DIR / "client-things" / "760"
    rme_client_dir = OUT_DIR / "rme-client-760-zagan-test"
    server_items_dir = OUT_DIR / "server-items"

    (client_things_dir / "Tibia.dat").write_bytes(dat_out)
    (client_things_dir / "Tibia.spr").write_bytes(spr_out)
    (rme_client_dir / "Tibia.dat").write_bytes(dat_out)
    (rme_client_dir / "Tibia.spr").write_bytes(spr_out)
    (server_items_dir / "items.otb").write_bytes(otb_out)
    shutil.copy2(BASE_XML, server_items_dir / "items.xml")

    manifest_path = OUT_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"Wrote {len(item_specs)} Zagan items (server ids {next_server_id - len(item_specs)}..{next_server_id - 1})")
    print(f"Wrote {client_things_dir / 'Tibia.dat'}")
    print(f"Wrote {client_things_dir / 'Tibia.spr'}")
    print(f"Wrote {server_items_dir / 'items.otb'}")
    print(f"Wrote {server_items_dir / 'items.xml'}")
    print(f"Wrote {manifest_path}")


if __name__ == "__main__":
    main()
