from __future__ import annotations

import tempfile
import unittest
import sys
import os
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

import data


def write_player(
    players_dir: Path,
    name: str,
    *,
    level: int = 10,
    exp: int = 1000,
    voc: int = 1,
    frags: int = 0,
    bounty: int | None = 0,
    lastlogin: int = 1_710_000_000,
) -> Path:
    bounty_attr = "" if bounty is None else f' bounty="{bounty}"'
    xml = f"""<?xml version="1.0"?>
<player name="{name}" account="100000" sex="1" lookdir="2" exp="{exp}" voc="{voc}" level="{level}" access="0" cap="300" maxdepotitems="1000" lastlogin="{lastlogin}" maglevel="5" soul="100"{bounty_attr} banned="0">
  <health now="100" max="100" food="0" />
  <mana now="50" max="50" spent="0" />
  <look type="130" head="0" body="0" legs="0" feet="0" />
  <skills>
    <skill skillid="2" level="50" tries="0" />
    <skill skillid="4" level="40" tries="0" />
  </skills>
  <skull type="0" kills="{frags}" ticks="0" absolve="0" />
</player>
"""
    path = players_dir / f"{name.lower()}.xml"
    path.write_text(xml, encoding="utf-8")
    return path


class PeakPersistenceTests(unittest.TestCase):
    def test_players_peak_persists_across_server_resets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            players_dir = root / "players"
            players_dir.mkdir()
            otinfo = root / "OTINFO"
            otinfo.write_text("", encoding="utf-8")
            online = root / "online.xml"
            online.write_text("<online></online>", encoding="utf-8")
            state_file = root / "daily.json"
            peak_file = root / "peak.json"

            fake_status_high = {
                "online": True,
                "players_online": 12,
                "players_max": 28,
                "players_peak": 12,
                "uptime_seconds": 60,
                "servername": "Retro76",
                "version": "",
            }
            fake_status_reset = {
                **fake_status_high,
                "players_online": 3,
                "players_peak": 3,
            }

            with patch("data.server_status_from_files", return_value=fake_status_high):
                payload = data.build_payload(
                    players_dir,
                    otinfo,
                    online,
                    state_file,
                    "127.0.0.1",
                    7171,
                    "127.0.0.1",
                    peak_file,
                )
            self.assertEqual(payload["server"]["players_peak"], 12)

            with patch("data.server_status_from_files", return_value=fake_status_reset):
                payload = data.build_payload(
                    players_dir,
                    otinfo,
                    online,
                    state_file,
                    "127.0.0.1",
                    7171,
                    "127.0.0.1",
                    peak_file,
                )
            self.assertEqual(payload["server"]["players_peak"], 12)


class ServerStatusFromFilesTests(unittest.TestCase):
    def test_reads_players_from_online_xml_without_socket(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            online = root / "online.xml"
            online.write_text(
                """<?xml version="1.0"?>
<online>
  <player name="Alice" level="10" voc="1" exp="1000"/>
  <player name="Bob" level="8" voc="2" exp="500"/>
</online>
""",
                encoding="utf-8",
            )
            config = root / "config.lua"
            config.write_text('maxplayers = "200"\n', encoding="utf-8")
            peak = root / "peak.json"

            with patch.dict(os.environ, {"OT_STATUS_SOURCE": "file"}, clear=False):
                status = data.server_status_from_files(online, config, peak)

            self.assertEqual(status["players_online"], 2)
            self.assertEqual(status["players_max"], 200)
            self.assertTrue(status["online"])
            self.assertEqual(status["source"], "file")


class MostWantedDataTests(unittest.TestCase):
    def test_parse_player_reads_bounty_and_defaults_to_zero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            players_dir = Path(tmp)
            with_bounty = write_player(players_dir, "Hunter One", bounty=45000)
            without_bounty = write_player(players_dir, "Hunter Two", bounty=None)

            parsed_with = data.parse_player(with_bounty)
            parsed_without = data.parse_player(without_bounty)

            self.assertIsNotNone(parsed_with)
            self.assertIsNotNone(parsed_without)
            self.assertEqual(parsed_with["bounty"], 45000)
            self.assertEqual(parsed_without["bounty"], 0)

    def test_build_payload_returns_public_most_wanted_sorted_by_reward(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            players_dir = root / "players"
            players_dir.mkdir()
            otinfo = root / "OTINFO"
            otinfo.write_text("", encoding="utf-8")
            online = root / "online.xml"
            online.write_text("<online></online>", encoding="utf-8")
            state_file = root / "daily.json"

            write_player(players_dir, "Alpha", bounty=5000, level=20)
            write_player(players_dir, "Beta", bounty=12000, level=18)
            write_player(players_dir, "Yurez", bounty=99999, level=99)
            write_player(players_dir, "Gamma", bounty=0, level=30)

            fake_status = {
                "online": False,
                "players_online": 0,
                "players_max": 28,
                "players_peak": 0,
                "uptime_seconds": 0,
                "uptime_fmt": "0s",
                "servername": "Retro76",
                "version": "",
            }

            with patch("data.server_status_from_files", return_value=fake_status):
                payload = data.build_payload(
                    players_dir,
                    otinfo,
                    online,
                    state_file,
                    "127.0.0.1",
                    7171,
                    "127.0.0.1",
                )

            self.assertEqual([row["name"] for row in payload["most_wanted"]], ["Beta", "Alpha"])
            self.assertEqual(payload["most_wanted"][0]["bounty"], 12000)
            self.assertEqual(payload["most_wanted"][0]["bounty_fmt"], "12.000")


if __name__ == "__main__":
    unittest.main()
