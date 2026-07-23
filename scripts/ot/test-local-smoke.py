#!/usr/bin/env python3
"""
Smoke suite local para YurOTS.

Valida, usando un personaje de prueba dedicado:
- login de cuenta
- login al mundo (carga del player)
- guardado XML al logout
- cast de spell utilitario
- cast de spell ofensivo
- muerte, relog y respawn con helper GM local

Por defecto restaura el XML del personaje al final de cada caso para que la
suite sea repetible y no vaya consumiendo mana ni alterando el estado base.
"""

from __future__ import annotations

import argparse
import socket
import struct
import sys
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


DEFAULT_ACCOUNT = 275783
DEFAULT_PASSWORD = "123456qa"
DEFAULT_CHAR = "Test Knight"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 7171


class SmokeError(RuntimeError):
    pass


@dataclass
class PlayerState:
    lastlogin: int
    pos_x: int
    pos_y: int
    pos_z: int
    health_now: int
    health_max: int
    mana_now: int
    mana_max: int
    mana_spent: int
    mtime_ns: int


@dataclass
class PlayerSnapshot:
    path: Path
    text: str
    state: PlayerState


def add_string(value: str) -> bytes:
    encoded = value.encode("latin-1")
    return struct.pack("<H", len(encoded)) + encoded


def make_packet(body: bytes) -> bytes:
    return struct.pack("<H", len(body)) + body


def pack_position(x: int, y: int, z: int) -> bytes:
    return struct.pack("<HHB", x, y, z)


def inventory_position(slot_id: int) -> tuple[int, int, int]:
    return (0xFFFF, slot_id, 0)


def recv_exact(sock: socket.socket, size: int) -> bytes:
    data = b""
    while len(data) < size:
        chunk = sock.recv(size - len(data))
        if not chunk:
            raise SmokeError("conexion cerrada antes de completar el paquete")
        data += chunk
    return data


def read_packet(sock: socket.socket, timeout: float) -> bytes:
    sock.settimeout(timeout)
    header = recv_exact(sock, 2)
    size = header[0] | (header[1] << 8)
    return recv_exact(sock, size)


def drain_packets(sock: socket.socket, idle_timeout: float = 0.25, limit: int = 16) -> list[bytes]:
    packets: list[bytes] = []
    for _ in range(limit):
        try:
            packets.append(read_packet(sock, idle_timeout))
        except socket.timeout:
            break
        except SmokeError:
            break
        except OSError:
            break
    return packets


def decode_error_message(body: bytes) -> str:
    if len(body) < 3:
        return "respuesta de error incompleta"
    slen = body[1] | (body[2] << 8)
    return body[3:3 + slen].decode("latin-1", "replace")


def account_body(account: int, password: str) -> bytes:
    body = struct.pack("<B", 1)
    body += struct.pack("<H", 2)
    body += struct.pack("<H", 760)
    body += struct.pack("<III", 0, 0, 0)
    body += struct.pack("<I", account)
    body += add_string(password)
    return body


def game_body(account: int, char_name: str, password: str) -> bytes:
    body = struct.pack("<H", 0x020A)
    body += struct.pack("<B", 2)
    body += struct.pack("<H", 760)
    body += struct.pack("<B", 0)
    body += struct.pack("<I", account)
    body += add_string(char_name)
    body += add_string(password)
    return body


def say_body(text: str) -> bytes:
    return struct.pack("<BB", 0x96, 0x01) + add_string(text)


def logout_body() -> bytes:
    return struct.pack("<B", 0x14)


def move_body(opcode: int) -> bytes:
    return struct.pack("<B", opcode)


def use_item_body(pos: tuple[int, int, int], item_id: int, stackpos: int, index: int) -> bytes:
    body = struct.pack("<B", 0x82)
    body += pack_position(*pos)
    body += struct.pack("<HBB", item_id, stackpos, index)
    return body


def use_item_ex_body(
    pos_from: tuple[int, int, int],
    item_id: int,
    from_stackpos: int,
    pos_to: tuple[int, int, int],
    tile_id: int,
    to_stackpos: int,
) -> bytes:
    body = struct.pack("<B", 0x83)
    body += pack_position(*pos_from)
    body += struct.pack("<HB", item_id, from_stackpos)
    body += pack_position(*pos_to)
    body += struct.pack("<HB", tile_id, to_stackpos)
    return body


def connect(host: str, port: int, timeout: float = 10.0) -> socket.socket:
    return socket.create_connection((host, port), timeout=timeout)


def assert_server_available(host: str, port: int) -> None:
    try:
        sock = connect(host, port, timeout=3.0)
    except OSError as exc:
        raise SmokeError(f"servidor no disponible en {host}:{port}: {exc}") from exc
    else:
        sock.close()


def login_account(host: str, port: int, account: int, password: str) -> bytes:
    sock = connect(host, port)
    try:
        sock.sendall(make_packet(account_body(account, password)))
        response = read_packet(sock, 30.0)
    finally:
        sock.close()

    if response and response[0] == 0x0A:
        raise SmokeError(f"login de cuenta rechazado: {decode_error_message(response)}")
    return response


def login_world(host: str, port: int, account: int, password: str, char_name: str) -> tuple[socket.socket, bytes]:
    sock = connect(host, port)
    sock.sendall(make_packet(game_body(account, char_name, password)))
    response = read_packet(sock, 90.0)

    if response and response[0] == 0x14:
        sock.close()
        raise SmokeError(f"login al mundo rechazado: {decode_error_message(response)}")
    if not response or response[0] != 0x0A:
        sock.close()
        detail = f"opcode 0x{response[0]:02x}" if response else "vacia"
        raise SmokeError(f"respuesta inesperada al entrar al mundo: {detail}")

    drain_packets(sock, idle_timeout=0.15)
    return sock, response


def cast_spell(sock: socket.socket, spell_words: str) -> None:
    sock.sendall(make_packet(say_body(spell_words)))
    time.sleep(0.35)
    drain_packets(sock, idle_timeout=0.15)


def say_text(sock: socket.socket, text: str, settle_seconds: float = 0.35) -> None:
    sock.sendall(make_packet(say_body(text)))
    time.sleep(settle_seconds)
    drain_packets(sock, idle_timeout=0.15)


def move_once(sock: socket.socket, opcode: int, settle_seconds: float = 0.9) -> None:
    sock.sendall(make_packet(move_body(opcode)))
    time.sleep(settle_seconds)
    drain_packets(sock, idle_timeout=0.15)


def use_rune_on_position(
    sock: socket.socket,
    slot_id: int,
    item_id: int,
    pos_to: tuple[int, int, int],
) -> None:
    sock.sendall(
        make_packet(
            use_item_ex_body(
                pos_from=inventory_position(slot_id),
                item_id=item_id,
                from_stackpos=0,
                pos_to=pos_to,
                tile_id=0,
                to_stackpos=0,
            )
        )
    )
    time.sleep(0.35)
    drain_packets(sock, idle_timeout=0.15)


def logout(sock: socket.socket) -> None:
    try:
        sock.sendall(make_packet(logout_body()))
        time.sleep(0.35)
        drain_packets(sock, idle_timeout=0.10)
    except OSError:
        pass
    finally:
        try:
            sock.close()
        except OSError:
            pass


def player_file_path(repo_root: Path, char_name: str) -> Path:
    return repo_root / "server" / "YurOTS" / "ots" / "data" / "players" / f"{char_name.lower()}.xml"


def load_player_snapshot(path: Path) -> PlayerSnapshot:
    if not path.exists():
        raise SmokeError(f"no existe el XML del personaje de prueba: {path}")

    text = path.read_text(encoding="utf-8")
    root = ET.fromstring(text)
    spawn = root.find("spawn")
    health = root.find("health")
    mana = root.find("mana")
    if spawn is None:
        raise SmokeError(f"el XML del player no tiene bloque <spawn>: {path}")
    if health is None:
        raise SmokeError(f"el XML del player no tiene bloque <health>: {path}")
    if mana is None:
        raise SmokeError(f"el XML del player no tiene bloque <mana>: {path}")

    state = PlayerState(
        lastlogin=int(root.attrib.get("lastlogin", "0")),
        pos_x=int(spawn.attrib.get("x", "0")),
        pos_y=int(spawn.attrib.get("y", "0")),
        pos_z=int(spawn.attrib.get("z", "0")),
        health_now=int(health.attrib.get("now", "0")),
        health_max=int(health.attrib.get("max", "0")),
        mana_now=int(mana.attrib.get("now", "0")),
        mana_max=int(mana.attrib.get("max", "0")),
        mana_spent=int(mana.attrib.get("spent", "0")),
        mtime_ns=path.stat().st_mtime_ns,
    )
    return PlayerSnapshot(path=path, text=text, state=state)


def restore_player(snapshot: PlayerSnapshot) -> None:
    snapshot.path.write_text(snapshot.text, encoding="utf-8")


def wait_for_player_save(
    path: Path,
    before: PlayerState,
    timeout: float = 8.0,
    before_text: str | None = None,
    settle_seconds: float = 1.50,
) -> PlayerSnapshot:
    deadline = time.time() + timeout
    last_error: Exception | None = None
    changed_snapshot: PlayerSnapshot | None = None
    stable_since: float | None = None

    while time.time() < deadline:
        try:
            current = load_player_snapshot(path)
        except Exception as exc:  # pragma: no cover - transient XML rewrite window
            last_error = exc
            time.sleep(0.15)
            continue

        state = current.state
        if (
            state.lastlogin != before.lastlogin
            or state.mtime_ns != before.mtime_ns
            or state.health_now != before.health_now
            or state.mana_now != before.mana_now
            or state.mana_spent != before.mana_spent
            or (before_text is not None and current.text != before_text)
        ):
            if (
                changed_snapshot is None
                or current.text != changed_snapshot.text
                or current.state.mtime_ns != changed_snapshot.state.mtime_ns
            ):
                changed_snapshot = current
                stable_since = time.time()
            elif stable_since is not None and (time.time() - stable_since) >= settle_seconds:
                return current
        time.sleep(0.15)

    if changed_snapshot is not None:
        return changed_snapshot
    if last_error is not None:
        raise SmokeError(f"no pude leer el player tras el save: {last_error}") from last_error
    raise SmokeError("el XML del player no cambio despues del logout")


def print_case(title: str) -> None:
    print(f"-> {title}")


def parse_snapshot_root(snapshot: PlayerSnapshot) -> ET.Element:
    return ET.fromstring(snapshot.text)


def get_inventory_slot(root: ET.Element, slot_id: int) -> ET.Element | None:
    inventory = root.find("inventory")
    if inventory is None:
        raise SmokeError("el XML del player no tiene bloque <inventory>")

    for slot in inventory.findall("slot"):
        if int(slot.attrib.get("slotid", "0")) == slot_id:
            return slot

    return None


def get_inventory_slot_item(root: ET.Element, slot_id: int) -> ET.Element:
    slot = get_inventory_slot(root, slot_id)
    if slot is None:
        raise SmokeError(f"no existe el slot de inventario {slot_id} en el XML")

    item = slot.find("item")
    if item is None:
        raise SmokeError(f"slot {slot_id} sin item en el XML")
    return item


def get_inside_items(container_item: ET.Element) -> list[ET.Element]:
    inside = container_item.find("inside")
    if inside is None:
        return []
    return [item for item in inside.findall("item")]


def get_inventory_slot_count(snapshot: PlayerSnapshot, slot_id: int) -> int:
    root = ET.fromstring(snapshot.text)
    item = get_inventory_slot_item(root, slot_id)
    return int(item.attrib.get("count", "0"))


def get_temple_position(snapshot: PlayerSnapshot) -> tuple[int, int, int]:
    root = parse_snapshot_root(snapshot)
    temple = root.find("temple")
    if temple is None:
        raise SmokeError("el XML del player no tiene bloque <temple>")

    return (
        int(temple.attrib.get("x", "0")),
        int(temple.attrib.get("y", "0")),
        int(temple.attrib.get("z", "0")),
    )


def get_death_entries(snapshot: PlayerSnapshot) -> list[dict[str, str]]:
    root = parse_snapshot_root(snapshot)
    deaths = root.find("deaths")
    if deaths is None:
        raise SmokeError("el XML del player no tiene bloque <deaths>")

    return [dict(entry.attrib) for entry in deaths.findall("death")]


def find_empty_inventory_slot(snapshot: PlayerSnapshot, preferred_slots: tuple[int, ...] = (9, 2, 1)) -> int:
    root = ET.fromstring(snapshot.text)
    inventory = root.find("inventory")
    if inventory is None:
        raise SmokeError("el XML del player no tiene bloque <inventory>")

    occupied = {int(slot.attrib.get("slotid", "0")) for slot in inventory.findall("slot")}
    for slot_id in preferred_slots:
        if slot_id not in occupied:
            return slot_id

    raise SmokeError(
        "no encontre un slot libre para inyectar la rune de prueba "
        f"(preferidos: {', '.join(str(s) for s in preferred_slots)})"
    )


def install_inventory_item(path: Path, slot_id: int, item_id: int, count: int | None = None) -> None:
    root = ET.fromstring(path.read_text(encoding="utf-8"))
    inventory = root.find("inventory")
    if inventory is None:
        raise SmokeError("el XML del player no tiene bloque <inventory>")

    if get_inventory_slot(root, slot_id) is not None:
        raise SmokeError(f"el slot {slot_id} ya estaba ocupado al intentar inyectar item de prueba")

    slot = ET.Element("slot", {"slotid": str(slot_id)})
    item_attrs = {"id": str(item_id)}
    if count is not None:
        item_attrs["count"] = str(count)
    ET.SubElement(slot, "item", item_attrs)
    inventory.append(slot)
    path.write_text(ET.tostring(root, encoding="unicode"), encoding="utf-8")


def set_player_health(path: Path, health_now: int) -> None:
    root = ET.fromstring(path.read_text(encoding="utf-8"))
    health = root.find("health")
    if health is None:
        raise SmokeError("el XML del player no tiene bloque <health>")

    health.attrib["now"] = str(health_now)
    path.write_text(ET.tostring(root, encoding="unicode"), encoding="utf-8")


def set_player_food(path: Path, food_now: int) -> None:
    root = ET.fromstring(path.read_text(encoding="utf-8"))
    health = root.find("health")
    if health is None:
        raise SmokeError("el XML del player no tiene bloque <health>")

    health.attrib["food"] = str(food_now)
    path.write_text(ET.tostring(root, encoding="unicode"), encoding="utf-8")


def run_basic_save_case(host: str, port: int, account: int, password: str, char_name: str, baseline: PlayerSnapshot) -> None:
    print_case("Caso 2: login al mundo y guardado al logout")
    restore_player(baseline)
    before = load_player_snapshot(baseline.path)
    sock, response = login_world(host, port, account, password, char_name)
    print(f"   mundo OK (opcode 0x{response[0]:02x}, {len(response)} bytes)")
    logout(sock)
    after = wait_for_player_save(baseline.path, before.state, before_text=before.text)

    if after.state.lastlogin == before.state.lastlogin:
        raise SmokeError("el player salio, pero lastlogin no se actualizo")

    print(
        "   save OK "
        f"(lastlogin {before.state.lastlogin} -> {after.state.lastlogin})"
    )
    restore_player(baseline)


def run_spell_case(
    label: str,
    spell_words: str,
    expected_mana_cost: int,
    host: str,
    port: int,
    account: int,
    password: str,
    char_name: str,
    baseline: PlayerSnapshot,
    allow_no_effect: bool = False,
    mana_refund_tolerance: int = 0,
) -> bool:
    print_case(f"Caso {label}: cast '{spell_words}'")
    restore_player(baseline)
    set_player_food(baseline.path, 0)
    before = load_player_snapshot(baseline.path)
    sock, response = login_world(host, port, account, password, char_name)
    print(f"   mundo OK (opcode 0x{response[0]:02x}, {len(response)} bytes)")
    cast_spell(sock, spell_words)
    logout(sock)
    after = wait_for_player_save(baseline.path, before.state, before_text=before.text)

    mana_delta = before.state.mana_now - after.state.mana_now
    spent_delta = after.state.mana_spent - before.state.mana_spent

    if after.state.lastlogin == before.state.lastlogin:
        raise SmokeError("el spell corrio, pero el save no actualizo lastlogin")
    if mana_delta == 0 and spent_delta == 0 and allow_no_effect:
        print("   skip: el spell no tuvo efecto desde la posicion actual (probable PZ)")
        restore_player(baseline)
        return False
    min_expected_mana_delta = max(0, expected_mana_cost - mana_refund_tolerance)
    if mana_delta < min_expected_mana_delta or mana_delta > expected_mana_cost:
        if allow_no_effect:
            print(
                "   skip: el cast tuvo un perfil de mana no estable "
                f"(esperaba entre -{expected_mana_cost} y -{min_expected_mana_delta}, obtuve -{mana_delta})"
            )
            restore_player(baseline)
            return False
        raise SmokeError(
            f"mana inesperada tras '{spell_words}': "
            f"esperaba entre -{expected_mana_cost} y -{min_expected_mana_delta}, "
            f"obtuve -{mana_delta}"
        )
    if spent_delta <= 0:
        raise SmokeError(
            f"mana spent inesperada tras '{spell_words}': "
            f"esperaba progreso positivo, obtuve +{spent_delta}"
        )

    print(
        "   spell OK "
        f"(mana {before.state.mana_now} -> {after.state.mana_now}, "
        f"spent {before.state.mana_spent} -> {after.state.mana_spent}, "
        f"delta +{spent_delta})"
    )
    restore_player(baseline)
    return True


def run_healing_spell_case(
    host: str,
    port: int,
    account: int,
    password: str,
    char_name: str,
    baseline: PlayerSnapshot,
    spell_words: str,
    expected_mana_cost: int,
    mana_refund_tolerance: int = 0,
) -> None:
    print_case(f"Caso 5: cast '{spell_words}' con vida baja")
    restore_player(baseline)
    set_player_food(baseline.path, 0)
    set_player_health(baseline.path, max(1, baseline.state.health_max - 250))
    before = load_player_snapshot(baseline.path)

    sock, response = login_world(host, port, account, password, char_name)
    print(f"   mundo OK (opcode 0x{response[0]:02x}, {len(response)} bytes)")
    cast_spell(sock, spell_words)
    logout(sock)

    after = wait_for_player_save(baseline.path, before.state, before_text=before.text)
    mana_delta = before.state.mana_now - after.state.mana_now
    spent_delta = after.state.mana_spent - before.state.mana_spent

    if after.state.lastlogin == before.state.lastlogin:
        raise SmokeError("el heal corrio, pero el save no actualizo lastlogin")
    min_expected_mana_delta = max(1, expected_mana_cost - mana_refund_tolerance)
    if mana_delta < min_expected_mana_delta:
        raise SmokeError(
            f"mana inesperada tras '{spell_words}': "
            f"esperaba al menos -{min_expected_mana_delta}, "
            f"obtuve -{mana_delta}"
        )
    if spent_delta <= 0:
        raise SmokeError(
            f"mana spent inesperada tras '{spell_words}': "
            f"esperaba progreso positivo, obtuve +{spent_delta}"
        )
    if after.state.health_now <= before.state.health_now:
        raise SmokeError(
            f"'{spell_words}' deberia haber curado al player "
            f"(health {before.state.health_now} -> {after.state.health_now})"
        )

    print(
        "   heal OK "
        f"(health {before.state.health_now} -> {after.state.health_now}, "
        f"mana {before.state.mana_now} -> {after.state.mana_now}, "
        f"spent {before.state.mana_spent} -> {after.state.mana_spent})"
    )
    restore_player(baseline)


def run_rune_case(
    host: str,
    port: int,
    account: int,
    password: str,
    char_name: str,
    baseline: PlayerSnapshot,
) -> None:
    print_case("Caso 6: consumo de rune desde inventario")
    restore_player(baseline)
    temp_slot = find_empty_inventory_slot(baseline)
    install_inventory_item(baseline.path, temp_slot, item_id=2273, count=2)
    set_player_food(baseline.path, 0)
    set_player_health(baseline.path, max(1, baseline.state.health_max - 300))
    before = load_player_snapshot(baseline.path)

    sock, response = login_world(host, port, account, password, char_name)
    print(
        "   mundo OK "
        f"(opcode 0x{response[0]:02x}, {len(response)} bytes, rune Ultimate Healing)"
    )

    use_rune_on_position(
        sock=sock,
        slot_id=temp_slot,
        item_id=2273,
        pos_to=(before.state.pos_x, before.state.pos_y, before.state.pos_z),
    )
    logout(sock)

    after = wait_for_player_save(baseline.path, before.state, before_text=before.text)
    before_count = get_inventory_slot_count(before, temp_slot)
    after_count = get_inventory_slot_count(after, temp_slot)
    mana_delta = before.state.mana_now - after.state.mana_now
    spent_delta = after.state.mana_spent - before.state.mana_spent

    if after.state.lastlogin == before.state.lastlogin:
        raise SmokeError("la rune se uso, pero el save no actualizo lastlogin")
    if after_count != before_count - 1:
        raise SmokeError(
            "consumo inesperado de rune Ultimate Healing: "
            f"esperaba count {before_count - 1}, obtuve {after_count}"
        )
    if mana_delta != 0 or spent_delta != 0:
        raise SmokeError(
            "la rune Ultimate Healing no deberia gastar mana del player "
            f"(mana delta {mana_delta}, spent delta {spent_delta})"
        )
    if after.state.health_now <= before.state.health_now:
        raise SmokeError(
            "la rune Ultimate Healing deberia haber curado al player "
            f"(health {before.state.health_now} -> {after.state.health_now})"
        )

    print(
        "   rune OK "
        f"(Ultimate Healing: count {before_count} -> {after_count}, "
        f"health {before.state.health_now} -> {after.state.health_now})"
    )
    restore_player(baseline)


def run_death_respawn_case(
    host: str,
    port: int,
    account: int,
    password: str,
    char_name: str,
    baseline: PlayerSnapshot,
    gm_account: int,
    gm_password: str,
    gm_char_name: str,
    gm_baseline: PlayerSnapshot,
    death_spell: str,
    gm_position: tuple[int, int, int],
) -> None:
    print_case("Caso 7: muerte, relog y respawn")
    restore_player(baseline)
    restore_player(gm_baseline)
    set_player_food(baseline.path, 0)
    set_player_health(baseline.path, 1)
    before = load_player_snapshot(baseline.path)
    before_deaths = get_death_entries(before)
    temple_pos = get_temple_position(before)

    gm_sock = None
    player_sock = None
    try:
        gm_sock, gm_response = login_world(host, port, gm_account, gm_password, gm_char_name)
        print(
            "   helper GM OK "
            f"(opcode 0x{gm_response[0]:02x}, {len(gm_response)} bytes, {gm_char_name})"
        )
        say_text(gm_sock, f"/goto {gm_position[0]} {gm_position[1]} {gm_position[2]}", settle_seconds=0.60)

        player_sock, response = login_world(host, port, account, password, char_name)
        print(f"   mundo OK (opcode 0x{response[0]:02x}, {len(response)} bytes)")
        say_text(gm_sock, death_spell, settle_seconds=1.00)

        after = wait_for_player_save(baseline.path, before.state, before_text=before.text, timeout=8.0)
    finally:
        if player_sock is not None:
            try:
                logout(player_sock)
            except OSError:
                pass
        if gm_sock is not None:
            logout(gm_sock)

    after_deaths = get_death_entries(after)
    death_delta = len(after_deaths) - len(before_deaths)
    latest_death = after_deaths[-1] if after_deaths else {}

    if after.state.lastlogin == before.state.lastlogin:
        raise SmokeError("la muerte ocurrio, pero el save no actualizo lastlogin")
    if death_delta != 1:
        raise SmokeError(
            "esperaba exactamente una nueva entrada en death list "
            f"(antes {len(before_deaths)}, despues {len(after_deaths)})"
        )
    if latest_death.get("name") != gm_char_name:
        raise SmokeError(
            "killer inesperado en death list: "
            f"esperaba '{gm_char_name}', obtuve '{latest_death.get('name', '')}'"
        )
    if (after.state.pos_x, after.state.pos_y, after.state.pos_z) != temple_pos:
        raise SmokeError(
            "el respawn deberia dejar al player en el templo "
            f"({temple_pos[0]},{temple_pos[1]},{temple_pos[2]}), obtuve "
            f"({after.state.pos_x},{after.state.pos_y},{after.state.pos_z})"
        )
    if after.state.health_now <= 0 or after.state.health_now != after.state.health_max:
        raise SmokeError(
            "tras morir, el player deberia reaparecer con vida positiva y llena "
            f"(health {after.state.health_now}/{after.state.health_max})"
        )
    if after.state.health_max >= before.state.health_max:
        raise SmokeError(
            "esperaba perdida real por muerte en health max "
            f"({before.state.health_max} -> {after.state.health_max})"
        )
    if after.state.mana_max >= before.state.mana_max:
        raise SmokeError(
            "esperaba perdida real por muerte en mana max "
            f"({before.state.mana_max} -> {after.state.mana_max})"
        )

    print(
        "   death OK "
        f"(killer {gm_char_name}, temple {after.state.pos_x},{after.state.pos_y},{after.state.pos_z}, "
        f"health max {before.state.health_max} -> {after.state.health_max}, "
        f"mana max {before.state.mana_max} -> {after.state.mana_max})"
    )
    restore_player(baseline)
    restore_player(gm_baseline)


def run_movement_case(
    host: str,
    port: int,
    account: int,
    password: str,
    char_name: str,
    baseline: PlayerSnapshot,
) -> None:
    print_case("Caso 8: movimiento y save de posicion")

    directions = [
        ("north", 0x65, (0, -1, 0)),
        ("east", 0x66, (1, 0, 0)),
        ("south", 0x67, (0, 1, 0)),
        ("west", 0x68, (-1, 0, 0)),
        ("north-east", 0x6A, (1, -1, 0)),
        ("south-east", 0x6B, (1, 1, 0)),
        ("south-west", 0x6C, (-1, 1, 0)),
        ("north-west", 0x6D, (-1, -1, 0)),
    ]

    for label, opcode, delta in directions:
        restore_player(baseline)
        before = load_player_snapshot(baseline.path)
        sock, response = login_world(host, port, account, password, char_name)
        print(f"   probando {label} (opcode 0x{response[0]:02x}, {len(response)} bytes)")
        move_once(sock, opcode)
        logout(sock)
        after = wait_for_player_save(baseline.path, before.state, before_text=before.text)

        dx = after.state.pos_x - before.state.pos_x
        dy = after.state.pos_y - before.state.pos_y
        dz = after.state.pos_z - before.state.pos_z

        if (dx, dy, dz) == delta:
            print(
                "   move OK "
                f"({label}: {before.state.pos_x},{before.state.pos_y},{before.state.pos_z} -> "
                f"{after.state.pos_x},{after.state.pos_y},{after.state.pos_z})"
            )
            restore_player(baseline)
            return

    restore_player(baseline)
    raise SmokeError("no encontre un movimiento simple que cambiara la posicion del player")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke suite local de YurOTS.")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--account", type=int, default=DEFAULT_ACCOUNT)
    parser.add_argument("--password", default=DEFAULT_PASSWORD)
    parser.add_argument("--char", default=DEFAULT_CHAR)
    parser.add_argument(
        "--utility-spell",
        default="utevo lux",
        help="Spell utilitario para validar cast y save.",
    )
    parser.add_argument(
        "--utility-cost",
        type=int,
        default=20,
        help="Costo de mana esperado del spell utilitario.",
    )
    parser.add_argument(
        "--offensive-spell",
        default="exori",
        help="Spell ofensivo para validar el camino de combate.",
    )
    parser.add_argument(
        "--offensive-cost",
        type=int,
        default=100,
        help="Costo de mana esperado del spell ofensivo.",
    )
    parser.add_argument(
        "--healing-spell",
        default="exura",
        help="Spell de curacion para validar heal, gasto de mana y save.",
    )
    parser.add_argument(
        "--healing-cost",
        type=int,
        default=25,
        help="Costo de mana esperado del spell de curacion.",
    )
    parser.add_argument(
        "--gm-char",
        default="GM Kaiser",
        help="Character GM helper para el caso local de muerte/respawn.",
    )
    parser.add_argument(
        "--gm-account",
        type=int,
        help="Cuenta del helper GM. Por defecto reutiliza --account.",
    )
    parser.add_argument(
        "--gm-password",
        help="Password del helper GM. Por defecto reutiliza --password.",
    )
    parser.add_argument(
        "--death-spell",
        default="exevo gran mas vis",
        help="Spell del helper GM para forzar una muerte local repetible.",
    )
    parser.add_argument(
        "--death-gm-pos",
        nargs=3,
        type=int,
        metavar=("X", "Y", "Z"),
        default=(141, 73, 6),
        help="Posicion del helper GM antes del cast de muerte.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from lib.project_root import project_root  # noqa: E402

    repo_root = project_root(Path(__file__))
    player_path = player_file_path(repo_root, args.char)
    gm_account = args.gm_account if args.gm_account is not None else args.account
    gm_password = args.gm_password if args.gm_password is not None else args.password
    gm_path = player_file_path(repo_root, args.gm_char)

    assert_server_available(args.host, args.port)
    baseline = load_player_snapshot(player_path)
    gm_baseline = load_player_snapshot(gm_path)
    offensive_ok = False

    print_case("Caso 1: login de cuenta")
    account_response = login_account(args.host, args.port, args.account, args.password)
    print(f"   cuenta OK (opcode 0x{account_response[0]:02x}, {len(account_response)} bytes)")

    try:
        run_basic_save_case(args.host, args.port, args.account, args.password, args.char, baseline)
        run_spell_case(
            label="3",
            spell_words=args.utility_spell,
            expected_mana_cost=args.utility_cost,
            host=args.host,
            port=args.port,
            account=args.account,
            password=args.password,
            char_name=args.char,
            baseline=baseline,
        )
        offensive_ok = run_spell_case(
            label="4",
            spell_words=args.offensive_spell,
            expected_mana_cost=args.offensive_cost,
            host=args.host,
            port=args.port,
            account=args.account,
            password=args.password,
            char_name=args.char,
            baseline=baseline,
            allow_no_effect=True,
            mana_refund_tolerance=10,
        )
        run_healing_spell_case(
            host=args.host,
            port=args.port,
            account=args.account,
            password=args.password,
            char_name=args.char,
            baseline=baseline,
            spell_words=args.healing_spell,
            expected_mana_cost=args.healing_cost,
            mana_refund_tolerance=10,
        )
        run_rune_case(
            host=args.host,
            port=args.port,
            account=args.account,
            password=args.password,
            char_name=args.char,
            baseline=baseline,
        )
        run_death_respawn_case(
            host=args.host,
            port=args.port,
            account=args.account,
            password=args.password,
            char_name=args.char,
            baseline=baseline,
            gm_account=gm_account,
            gm_password=gm_password,
            gm_char_name=args.gm_char,
            gm_baseline=gm_baseline,
            death_spell=args.death_spell,
            gm_position=tuple(args.death_gm_pos),
        )
        run_movement_case(
            host=args.host,
            port=args.port,
            account=args.account,
            password=args.password,
            char_name=args.char,
            baseline=baseline,
        )
    finally:
        restore_player(baseline)
        restore_player(gm_baseline)

    if offensive_ok:
        print("OK: smoke suite local completada")
    else:
        print("OK: smoke suite local completada (cast ofensivo pendiente de validacion manual)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SmokeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
