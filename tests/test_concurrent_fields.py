# -*- coding: utf-8 -*-
"""同维度多任务隔离、区块唤醒、存档恢复和视觉路由的离线回归。"""
import unittest
from copy import deepcopy
import test_effect_events as fixtures
from test_palette import sandbox, MemoryWorld
from event_args import make_event_args
from dualvectorfoil_scripts.modules.foil import server as foil


class ConcurrentTests(unittest.TestCase):
    def setUp(self):
        self.old_budget = foil.FOIL_BLOCKS_PER_TICK
        self.addCleanup(setattr, foil, 'FOIL_BLOCKS_PER_TICK', self.old_budget)
        foil.FOIL_BLOCKS_PER_TICK = 50

    def scene(self):
        system, first_world, first = sandbox({(0, 1, 0): 'stone'})
        second = deepcopy(first)
        first['run_id'], second['run_id'] = 'first', 'second'
        second['origin'] = second['anchor'] = [100, 0, 100]
        system.fields['0:second'] = second
        second_world = MemoryWorld({(100, 1, 100): 'gold'})
        system.worlds['0:second'] = second_world
        system.tick = 100
        return system, first, second, first_world, second_world

    def test_detonation_keeps_existing_state_and_queues(self):
        system, first, second, unused, unused2 = self.scene()
        queue = system._move_queue(0, first)
        system.projectiles = {'shot': {'dimension': 0}}
        system.DestroyEntity = lambda entity: None
        system._process_field = lambda *args: None
        system._attach = lambda *args: None
        system._detonate('shot', (200, 4, 200))
        self.assertEqual(len(system.fields), 3)
        self.assertIs(system.fields['0'], first)
        self.assertIs(system.fields['0:second'], second)
        self.assertIs(system._move_queue(0, first), queue)
        self.assertEqual(len({state['run_id'] for state in system.fields.values()}), 3)

    def test_shared_budget_and_completion_do_not_reset_other_task(self):
        system, first, second, world1, world2 = self.scene()
        system._process_field(0, first)
        system._process_field('0:second', second)
        foil.FOIL_BLOCKS_PER_TICK = 1
        system._process_field(0, first)
        self.assertEqual(first['phase'], 'complete')
        self.assertIn('0:second', system.worlds)
        system._process_field('0:second', second)
        self.assertEqual(second['moved'], 0)
        system.tick += 1
        system._process_field('0:second', second)
        self.assertEqual(second['phase'], 'complete')
        self.assertEqual(world1.blocks, {foil.flatten((0, 1, 0), first['origin']): 'stone'})
        self.assertEqual(world2.blocks, {foil.flatten((100, 1, 100), second['origin']): 'gold'})

    def test_chunk_event_wakes_all_matching_tasks(self):
        system, first, second, world1, world2 = self.scene()
        system.fields['1:other'] = {'phase': 'complete'}
        called = []
        system._resume_chunk = lambda slot, args: called.append(slot)
        system.ChunkLoadedServerEvent(make_event_args({'dimension': 0}))
        self.assertEqual(set(called), {0, '0:second'})

    def test_two_pending_tasks_finish_on_real_chunk_callbacks(self):
        system, first, second, world1, world2 = self.scene()
        foil.FOIL_BLOCKS_PER_TICK = -1
        world1.is_loaded = world2.is_loaded = lambda pos: False
        for slot, state in [(0, first), ('0:second', second)]:
            system._process_field(slot, state)
            self.assertEqual(state['status'], 'waiting_chunks')
        world1.is_loaded = world2.is_loaded = lambda pos: True
        chunks = set()
        for state in [first, second]:
            for source in fixtures.plan_sources(state):
                target = foil.flatten(source, state['origin'])
                chunks.update((pos[0] // 16, pos[2] // 16) for pos in [source, target])
        for x, z in chunks:
            system.ChunkLoadedServerEvent(make_event_args({
                'dimension': 0, 'chunkPosX': x, 'chunkPosZ': z,
            }))
        self.assertEqual([first['phase'], second['phase']], ['complete', 'complete'])
        self.assertEqual([first['moved'], second['moved']], [1, 1])

    def test_entity_checks_other_tasks_after_a_contact_miss(self):
        tracker = foil.FlatEntities()
        class Components(object):
            def __init__(self):
                self.EngineType = self.ExtraData = self.Dimension = self.Pos = self
            def GetEngineTypeStr(self):
                return 'minecraft:pig'
            def GetExtraData(self, key):
                return None
            def GetEntityDimensionId(self):
                return 0
            def GetFootPos(self):
                return (100, 1, 100)
        old_cf = foil.nyl.CF
        self.addCleanup(setattr, foil.nyl, 'CF', old_cf)
        foil.nyl.CF = lambda entity: Components()
        captured = []
        def capture(entity, cf, kind, dimension, state, contacts, pos):
            captured.append(state['run_id'])
        tracker._capture = capture
        tracker._visit('pig', {'0': {'run_id': 'first'}, '0:second': {'run_id': 'second'},
                               '1:other': {'run_id': 'other'}},
                       {'0': set(), '0:second': {(100, 0, 100)}, '1:other': set()})
        self.assertEqual(set(captured), {'first', 'second'})

    def test_legacy_and_concurrent_tasks_restore_with_real_dimensions(self):
        system, first, second, unused, unused2 = self.scene()
        saved = deepcopy(system.fields)
        class Extra(object):
            def GetExtraData(self, key):
                return deepcopy(saved)
        class Level(object):
            ExtraData = Extra()
        old_level, old_adapter = foil.nyl.LvComp, foil.WorldAdapter
        self.addCleanup(setattr, foil.nyl, 'LvComp', old_level)
        self.addCleanup(setattr, foil, 'WorldAdapter', old_adapter)
        foil.nyl.LvComp = Level()
        foil.WorldAdapter = lambda dimension: dimension
        restored = foil.FoilServer('nuoyan', 'FoilServer')
        self.assertEqual(restored.worlds, {0: 0, '0:second': 0})
        self.assertEqual(restored.fields, saved)

    def test_broadcast_uses_world_dimension_and_independent_run_id(self):
        system, first, second, unused, unused2 = self.scene()
        received = []
        class Main(object):
            def BroadcastEvent(self, event, payload):
                received.append(payload)
        system.main_system = Main()
        foil.FoilServer._broadcast_field_state(system, '0:second', second)
        self.assertEqual(received[0]['dimension'], 0)
        self.assertEqual(received[0]['run_id'], 'second')

    def test_effect_forwards_each_task_independently(self):
        effect = fixtures.effect_server.EffectServer('nuoyan', 'EffectServer')
        sent = []
        effect._send = lambda args: sent.append(args.run_id)
        def event(run, phase):
            effect.FoilFieldState(make_event_args({'dimension': 0, 'run_id': run, 'phase': phase}))
        event('first', 'moving')
        event('second', 'moving')
        event('first', 'moving')
        event('first', 'complete')
        self.assertEqual(sent, ['first', 'second', 'first', 'first'])
        event('second', 'complete')
        self.assertEqual(sent[-1], 'second')

    def test_effect_forwards_completion_without_selecting_other_tasks(self):
        effect = fixtures.effect_server.EffectServer('nuoyan', 'EffectServer')
        sent = []
        effect._send = lambda args: sent.append((args.run_id, args.phase))
        for run, phase in [('first', 'moving'), ('second', 'moving'), ('second', 'complete')]:
            effect.FoilFieldState(make_event_args({'dimension': 0, 'run_id': run, 'phase': phase}))
        self.assertEqual(sent[-1], ('second', 'complete'))


if __name__ == '__main__':
    unittest.main()
