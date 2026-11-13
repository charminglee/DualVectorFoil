# -*- coding: utf-8 -*-
"""验证复用真实库函数后的坐标边界与天空方向回退。"""

import unittest

import test_effect_events as fixtures
from dualvectorfoil_scripts.modules.foil.server import entity_contact_candidates
from dualvectorfoil_scripts.modules.effect.playback import FieldPlayback
from event_args import make_event_args


class ReuseTests(unittest.TestCase):
    def test_contact_points_keep_negative_floor_and_support_priority(self):
        self.assertEqual(entity_contact_candidates((-0.1, -1.0, -16.1)), [
            (-1, -2, -17), (-1, -1, -17),
        ])
        self.assertEqual(entity_contact_candidates((-0.1, -1.1, -16.1)), [
            (-1, -2, -17),
        ])

    def test_chunk_edges_keep_negative_coordinates(self):
        for x, expected in ((-16.01, -2), (-16.0, -1), (-0.01, -1), (0, 0), (15.99, 0), (16, 1)):
            self.assertEqual(fixtures.library.server.chunk_pos((x, -64, x)), (expected, expected))

    def test_sky_direction_keeps_near_zero_fallback(self):
        previous = getattr(fixtures.library.client, 'LvComp', None)
        self.addCleanup(setattr, fixtures.library.client, 'LvComp', previous)
        for offset in (0.0, 0.0009, 0.002, 10.0):
            camera = type("Camera", (), {'GetPosition': lambda self: (0.0, 38.0, 0.0)})()
            fixtures.library.client.LvComp = type("Level", (), {'Camera': camera})()
            playback = FieldPlayback("test")
            playback.particles.start = lambda center: None
            playback.start(make_event_args({
                'dimension': 0, 'run_id': "test", 'plane_y': 0,
                'center': (offset, 0.0, 0.0),
            }), 0.0)
            self.assertEqual(playback.sky_direction, (1.0, 0.0, 0.0) if offset > 0.001 else (0.0, 1.0, 0.0))


if __name__ == "__main__":
    unittest.main()
