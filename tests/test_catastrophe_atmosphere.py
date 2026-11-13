# -*- coding: utf-8 -*-
"""共享天空恢复、并发包络和粒子清理回归。"""
import unittest
import test_effect_events as fixtures
from effect_components import install
from dualvectorfoil_scripts.modules.effect import atmosphere, playback
from event_args import make_event_args


class Level(object):
    def __init__(self):
        self.Camera = self.Game = self
        install(self)
    def GetPosition(self):
        return (0, 3, 10)
    def GetCurrentDimension(self):
        return 0


class AtmosphereTests(unittest.TestCase):
    def setUp(self):
        self.level = Level()
        atmosphere.nyl.LvComp = playback.nyl.LvComp = self.level
        self.controller = atmosphere.CatastropheAtmosphere()
        self.now = 1.0

    def field(self, name, started=0.0):
        p = playback.FieldPlayback(name)
        p.start(make_event_args({'dimension': 0, 'run_id': name, 'center': (0, 3, 0), 'plane_y': 0}), started)
        p.clock = lambda: self.now
        return p

    def test_last_effect_restores_unmodified_sky_mode_and_values(self):
        original = self.level.SkyRender.color
        p = self.field('first')
        self.controller.update([p])
        self.assertTrue(self.level.SkyRender.use_color)
        self.assertLess(self.level.SkyRender.brightness, 0.2)
        p.clear()
        self.controller.update([p])
        self.assertFalse(self.level.SkyRender.use_color)
        self.assertFalse(self.level.SkyRender.use_brightness)
        self.assertEqual(self.level.SkyRender.brightness, 1.0)
        self.assertEqual(self.level.SkyRender.color, original)

    def test_preexisting_mod_override_is_preserved(self):
        sky = self.level.SkyRender
        sky.SetSkyColor((0.2, 0.3, 0.4, 1.0))
        sky.SetAmbientBrightness(0.65)
        p = self.field('first')
        self.controller.update([p])
        self.controller.clear()
        self.assertEqual(sky.color, (0.2, 0.3, 0.4, 1.0))
        self.assertEqual(sky.brightness, 0.65)
        self.assertTrue(sky.use_color and sky.use_brightness)

    def test_one_finished_task_does_not_restore_another_active_task(self):
        first, second = self.field('first'), self.field('second', 1.0)
        self.controller.update([first, second])
        self.now = 5.1
        first.clear()
        self.controller.update([first, second])
        self.assertTrue(self.level.SkyRender.use_color)
        second.clear()
        self.controller.update([first, second])
        self.assertFalse(self.level.SkyRender.use_color)

    def test_fog_tracks_sky_and_restores_engine_mode(self):
        fog = self.level.Fog
        original = fog.color
        p = self.field('first')
        self.controller.update([p])
        self.assertEqual(fog.color[:3], self.level.SkyRender.color[:3])
        self.assertEqual(fog.color[3], original[3])
        self.assertTrue(fog.use_color)
        p.clear()
        self.controller.update([p])
        self.assertEqual(fog.color, original)
        self.assertFalse(fog.use_color)

    def test_fog_fades_with_envelope_and_preserves_existing_override(self):
        fog = self.level.Fog
        original = (0.2, 0.3, 0.4, 0.5)
        fog.SetFogColor(original)
        p = self.field('first')
        self.now = 0.225
        self.controller.update([p])
        halfway = tuple((original[i] + (0.018, 0.012, 0.055)[i]) * 0.5 for i in range(3))
        for actual, expected in zip(fog.color[:3], halfway):
            self.assertAlmostEqual(actual, expected)
        self.now = 13.0
        self.controller.update([p])
        for actual, expected in zip(fog.color[:3], halfway):
            self.assertAlmostEqual(actual, expected)
        self.controller.clear()
        self.assertEqual(fog.color, original)
        self.assertTrue(fog.use_color)

    def test_fog_stays_until_last_concurrent_task_finishes(self):
        original = self.level.Fog.color
        first, second = self.field('first'), self.field('second', 1.0)
        self.controller.update([first, second])
        self.now = 15.1
        self.controller.update([first, second])
        self.assertTrue(self.level.Fog.use_color)
        self.now = 16.1
        self.controller.update([first, second])
        self.assertFalse(self.level.Fog.use_color)
        self.assertEqual(self.level.Fog.color, original)

    def test_particle_emitters_are_local_bounded_and_removed(self):
        first, second = self.field('first'), self.field('second')
        particles = self.level.ParticleSystem
        self.assertEqual(len(particles.live), 4)
        self.assertEqual(len(first.particles.ids), 2)
        first.clear()
        self.assertEqual(len(particles.live), 2)
        second.clear()
        self.assertEqual(particles.live, {})

    def test_particles_land_on_snapshot_plane_instead_of_source_center(self):
        """
        源中心与落点高度不同或多个任务并行时，各自使用快照平面。
        """
        for center, plane_y in (((5, 100, -8), 12.02), ((-7, -30, 9), -63.98)):
            p = playback.FieldPlayback('plane')
            p.start(make_event_args({
                'dimension': 0, 'run_id': 'plane',
                'center': center, 'plane_y': plane_y,
            }), 0.0)
            for name, pos, rotation in self.level.ParticleSystem.created[-2:]:
                self.assertEqual(pos, (center[0], plane_y, center[2]))
                self.assertEqual(rotation, (0.0, 0.0, 0.0))
            self.assertEqual(p.center, center)
            p.clear()

    def test_restarting_particle_bundle_releases_previous_emitters(self):
        p = self.field('first')
        previous = set(p.particles.ids)
        p.particles.start((20, 4, 0))
        particles = self.level.ParticleSystem
        self.assertEqual(len(particles.live), 2)
        self.assertTrue(previous.issubset(set(particles.removed)))
        self.assertFalse(previous.intersection(p.particles.ids))
        p.clear()
        self.assertEqual(particles.live, {})


if __name__ == '__main__':
    unittest.main()
