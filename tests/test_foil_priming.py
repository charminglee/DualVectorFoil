# -*- coding: utf-8 -*-
"""先发特效、延迟捕获、任务隔离及视觉去重的离线时序回归。"""
import unittest
from copy import deepcopy

import test_effect_events as fixtures
from test_palette import MemoryWorld
from event_args import make_event_args
from dualvectorfoil_scripts.modules.foil import server as foil
from dualvectorfoil_scripts.modules.effect import server as effect


class PrimingTests(unittest.TestCase):
    def setUp(self):
        self.old_budget = foil.FOIL_BLOCKS_PER_TICK
        self.addCleanup(setattr, foil, 'FOIL_BLOCKS_PER_TICK', self.old_budget)
        foil.FOIL_BLOCKS_PER_TICK = 50
        self.system = foil.FoilServer('nuoyan', 'FoilServer')
        self.events = []
        self.notices = []
        self.removed = []
        self.attachments = []
        self.worlds = {}
        self.effect = effect.EffectServer('nuoyan', 'EffectServer')
        self.effect._nearby = lambda dimension, snapshot: set(['near'])
        outer = self

        class Main(object):
            def BroadcastEvent(self, name, payload):
                outer.events.append(deepcopy(payload))
                outer.effect.FoilFieldState(make_event_args(payload))

            def NotifyToMultiClients(self, players, name, payload):
                outer.notices.append((outer.system.tick, deepcopy(payload)))

        self.system.main_system = self.effect.main_system = Main()
        self.system.DestroyEntity = self.removed.append
        self.system._message = lambda *args: None
        self.system._attach = self.attach

    def attach(self, slot):
        self.attachments.append(slot)
        self.system.worlds[slot] = self.worlds[slot]

    def detonate(self, name='shot', pos=(0, 0, 0), dimension=0, blocks=None):
        self.system.projectiles[name] = {'dimension': dimension}
        self.system._detonate(name, pos)
        slot = [key for key, state in self.system.fields.items()
                if state['run_id'] == self.events[-1]['run_id']][0]
        slot = foil.field_slot(slot)
        self.worlds[slot] = MemoryWorld({(0, 1, 0): 'stone'} if blocks is None else blocks)
        return slot, self.system.fields[str(slot)]

    def test_notice_precedes_all_world_access_and_capture_starts_at_tick_fifteen(self):
        slot, state = self.detonate()
        self.assertEqual(foil.PRIMING_TICKS, 15)
        self.assertEqual(len(self.notices), 1)
        self.assertEqual(self.events[0]['phase'], 'priming')
        self.assertEqual(self.events[0]['block_count'], 0)
        self.assertEqual(self.notices[0][0], 0)
        self.assertEqual(self.attachments, [])
        self.assertEqual(self.system.object_sets, {})
        self.assertEqual(self.system.projectiles, {})
        for tick in range(15):
            self.system.tick = tick
            self.system._process_field(slot, state)
        self.assertEqual(self.attachments, [])
        self.assertEqual(self.worlds[slot].reads, 0)
        self.assertNotIn('source_palette', state)
        self.system.tick = 15
        self.system._process_field(slot, state)
        self.assertEqual(self.worlds[slot].reads, 1)
        self.assertEqual(state['phase'], 'moving')
        self.assertNotIn('capture_tick', state)
        self.assertEqual(len(self.notices), 1, 'moving must not replay the priming effect')
        self.assertEqual(self.notices[0][1]['run_id'], state['run_id'])

    def test_same_tick_loop_does_not_bypass_delay(self):
        slot, state = self.detonate()
        self.system.entities = type('Entities', (), {'scan': lambda *args: None, 'hold': lambda *args: None})()
        self.system._update_projectiles = lambda: None
        for tick in range(1, 15):
            self.system.OnScriptTickServer(None)
            self.assertEqual(state['phase'], 'priming')
        self.system.OnScriptTickServer(None)
        self.assertEqual(state['phase'], 'moving')
        self.assertEqual(self.worlds[slot].reads, 1)

    def test_concurrent_tasks_keep_independent_deadlines_and_dimensions(self):
        first_slot, first = self.detonate()
        self.system.tick = 5
        second_slot, second = self.detonate('second')
        third_slot, third = self.detonate('third', dimension=1)
        self.assertEqual([first['capture_tick'], second['capture_tick'], third['capture_tick']], [15, 20, 20])
        self.assertEqual([e['dimension'] for e in self.events], [0, 0, 1])
        self.system.tick = 15
        for slot, state in ((first_slot, first), (second_slot, second), (third_slot, third)):
            self.system._process_field(slot, state)
        self.assertEqual(first['phase'], 'moving')
        self.assertEqual(second['phase'], 'priming')
        self.assertEqual(third['phase'], 'priming')
        self.system.tick = 20
        self.system._process_field(second_slot, second)
        self.system._process_field(third_slot, third)
        self.assertEqual(second['phase'], 'moving')
        self.assertEqual(third['phase'], 'moving')
        self.assertEqual(len(self.notices), 3)

    def test_capture_failure_retries_without_replaying_or_restarting_delay(self):
        slot, state = self.detonate()
        self.system.tick = 15
        capture = self.worlds[slot].capture
        self.worlds[slot].capture = lambda *args: None
        self.system._process_field(slot, state)
        self.assertEqual(state['status'], 'palette_read_failed')
        self.assertEqual(state['phase'], 'capturing')
        self.worlds[slot].capture = capture
        self.system.tick = 16
        self.system._process_field(slot, state)
        self.assertEqual(state['phase'], 'moving')
        self.assertEqual(len(self.notices), 1)

    def test_unlimited_mode_waits_then_completes_without_replaying_effect(self):
        foil.FOIL_BLOCKS_PER_TICK = -1
        slot, state = self.detonate()
        self.system.tick = 14
        self.system._process_field(slot, state)
        self.assertEqual(self.worlds[slot].reads, 0)
        self.assertEqual(self.worlds[slot].blocks, {(0, 1, 0): 'stone'})
        self.system.tick = 15
        self.system._process_field(slot, state)
        self.assertEqual(state['phase'], 'complete')
        self.assertEqual(state['moved'], 1)
        self.assertEqual(len(self.notices), 1)
        self.assertNotIn(slot, self.system.worlds)

    def test_empty_area_still_plays_before_capture_and_then_finishes(self):
        slot, state = self.detonate(blocks={})
        self.assertEqual(len(self.notices), 1)
        self.system.tick = 15
        self.system._process_field(slot, state)
        self.assertEqual(state['phase'], 'complete')
        self.assertEqual(state['status'], 'no_blocks')
        self.assertEqual(len(self.notices), 1)


if __name__ == '__main__':
    unittest.main()
