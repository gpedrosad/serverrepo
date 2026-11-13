#!/usr/bin/env python3
"""Regresiones de Frozen Isle: llegada efectiva, bote modular y spawns únicos. Solo dry-run."""
import contextlib
import importlib.util
import io
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('frozen', Path(__file__).with_name('generate-frozen-isle.py'))
frozen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(frozen)


class FrozenIsleRegression(unittest.TestCase):
    def run_generator(self):
        log = io.StringIO()
        with patch.object(sys, 'argv', ['generate-frozen-isle.py', '--dry-run']), \
                contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
            result = frozen.main()
        return result, log.getvalue()

    def test_default_map_has_all_monsters_and_no_validation_errors(self):
        result, log = self.run_generator()
        self.assertEqual(result, 0, log)
        self.assertIn('(86 monstruos)', log)

    def test_original_blocked_south_landing_is_rejected(self):
        build = frozen.build_caves

        def broken(seed):
            caves = build(seed)
            x, y = caves['down']
            caves['t9'][x, y + 1] = [357]
            return caves

        with patch.object(frozen, 'build_caves', broken):
            result, log = self.run_generator()
        self.assertEqual(result, 1)
        self.assertIn('llegada real (56, 52) bloqueada', log)

    def test_missing_middle_boat_piece_is_rejected(self):
        build = frozen.build_surface

        def broken(seed, blocking):
            tiles, info = build(seed, blocking)
            middle = next(c for c, item in info['boat'].items() if item == 3594)
            tiles[middle] = [frozen.WATER]
            return tiles, info

        with patch.object(frozen, 'build_surface', broken):
            result, log = self.run_generator()
        self.assertEqual(result, 1)
        self.assertIn('falta pieza 3594', log)

    def test_duplicate_absolute_spawn_is_rejected(self):
        place = frozen.place

        def broken(*args, **kwargs):
            spawns = place(*args, **kwargs)
            if len(spawns) > 1:
                name, _pos, delay = spawns[-1][2][0]
                spawns[-1][2][0] = (name, spawns[0][2][0][1], delay)
            return spawns

        with patch.object(frozen, 'place', broken):
            result, log = self.run_generator()
        self.assertEqual(result, 1)
        self.assertIn('posición repetida o bloqueada', log)


if __name__ == '__main__':
    unittest.main()
