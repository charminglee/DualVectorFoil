# -*- coding: utf-8 -*-
"""天空裂缝的时间边界、参数接线、固定方向与资源隔离回归。"""
import json
import os
import unittest

import test_space_fall_bridge as fixtures
from dualvectorfoil_scripts.modules.effect import timeline
from dualvectorfoil_scripts.modules.effect.config import PLAY_SECONDS, process_definition
from event_args import make_event_args


class SkyRiftTests(unittest.TestCase):
    def test_full_coverage_holds_exactly_six_seconds(self):
        self.assertEqual(PLAY_SECONDS, 15.0)
        self.assertEqual(timeline.sky_progress(0.0), 0.0)
        self.assertEqual(timeline.sky_progress(2.0), 1.0)
        for age in (5.0, 8.0, 11.0):
            self.assertEqual(timeline.sky_progress(age), 2.0)
            self.assertEqual(timeline.envelope(age), 1.0)
        self.assertLess(timeline.envelope(11.1), 1.0)
        self.assertAlmostEqual(timeline.envelope(13.0), 0.5)
        self.assertEqual(timeline.envelope(15.0), 0.0)

    def test_open_spread_and_restore_are_monotonic(self):
        progress = [timeline.sky_progress(index * 0.05) for index in range(101)]
        self.assertEqual(progress, sorted(progress))
        restore = [timeline.envelope(11.0 + index * 0.05) for index in range(81)]
        self.assertEqual(restore, sorted(restore, reverse=True))

    def test_direction_is_captured_once_and_rift_particle_is_absent(self):
        level = fixtures.FakeLevel()
        fixtures.client.nyl.LvComp = level
        p = fixtures.playback_module.FieldPlayback('nuoyan_space_fall')
        args = make_event_args({'dimension': 0, 'run_id': 'sky', 'center': (0, 3, 0), 'plane_y': 0})
        p.start(args, 0.0)
        direction = p.sky_direction
        level.position = (8, 6, 7)
        frame = p._frame(8.0, 0, level.position, (1, 0, 0))
        self.assertEqual(p.sky_direction, direction)
        self.assertEqual(frame[1][3], 2.0)
        self.assertAlmostEqual(sum(x * x for x in direction), 1.0)
        self.assertEqual(len(level.ParticleSystem.created), 2)
        self.assertFalse(any('rift' in row[0] for row in level.ParticleSystem.created))

    def test_both_pipelines_match_dynamic_parameter_layout(self):
        expected = ['field', 'shape', 'style']
        self.assertEqual([p['name'] for p in process_definition('test')['paras']], expected)
        for name in ('post_process.json', 'post_process_rngl.json'):
            path = os.path.join(fixtures.ROOT, 'src', 'rp', 'graphics_settings', name)
            with open(path) as stream:
                data = json.load(stream)
            effect = [p for p in data['process_array'] if p['name'] == 'nuoyan_space_fall'][0]
            self.assertFalse(effect['enable'])
            self.assertEqual([p['name'] for p in effect['paras']], expected)


if __name__ == '__main__':
    unittest.main()
