# -*- coding: utf-8 -*-
"""未加载区块暂存、事件应用及持久化恢复回归；仅供离线测试。"""
import unittest
from copy import deepcopy
from test_palette import sandbox
from event_args import make_event_args
from dualvectorfoil_scripts.modules.foil import server as foil
from dualvectorfoil_scripts.modules.foil.deferred import PendingMoves, reference_batch, scan_references
from dualvectorfoil_scripts.modules.foil.palette import PaletteContacts, encode_index


class DeferredTests(unittest.TestCase):
    def setUp(self):
        self.old_budget = foil.FOIL_BLOCKS_PER_TICK
        foil.FOIL_BLOCKS_PER_TICK = 50
        self.addCleanup(setattr, foil, 'FOIL_BLOCKS_PER_TICK', self.old_budget)

    def scene(self):
        blocks = {(0, 20, 0): 'stone', (1, 20, 0): 'stone', (2, 1, 0): 'stone'}
        system, world, state = sandbox(blocks, radius=30)
        state['run_id'] = 'deferred_test'
        system._process_field(0, state)
        blocked = set()
        checks = []
        def is_loaded(pos):
            checks.append(pos)
            return (pos[0] // 16, pos[2] // 16) not in blocked
        world.is_loaded = is_loaded
        target = foil.flatten((0, 20, 0), (0, 0, 0))
        chunk = (target[0] // 16, target[2] // 16)
        self.assertNotEqual(chunk, (0, 0))
        blocked.add(chunk)
        return system, world, state, blocked, chunk, checks, blocks

    def loaded(self, system, chunk, dimension=0):
        system.ChunkLoadedServerEvent(make_event_args({
            'dimension': dimension, 'chunkPosX': chunk[0], 'chunkPosZ': chunk[1],
        }))

    def test_unloaded_targets_are_deferred_and_loaded_blocks_continue(self):
        system, world, state, blocked, chunk, checks, blocks = self.scene()
        system._process_field(0, state)
        self.assertEqual(state['move_cursor'], 3)
        self.assertLess(state['moved'], 3)
        self.assertGreater(state['moved'], 0)
        self.assertEqual(state['moved'] + len(state['pending_moves']), 3)
        self.assertEqual(state['status'], 'waiting_chunks')
        self.assertEqual(world.blocks[(0, 20, 0)], 'stone')
        event = foil.build_field_event(0, state, 1)
        self.assertEqual(event['processed_count'], state['moved'])
        before = len(checks)
        for unused in range(10):
            system._process_field(0, state)
        self.assertEqual(len(checks), before, 'waiting items must not be polled each tick')

    def test_loaded_event_immediately_applies_related_entries_and_is_idempotent(self):
        system, world, state, blocked, chunk, checks, blocks = self.scene()
        system._process_field(0, state)
        blocked.clear()
        self.loaded(system, chunk)
        self.assertEqual(state['phase'], 'complete')
        self.assertEqual(state['moved'], 3)
        self.assertEqual(state['pending_moves'], {})
        self.assertEqual(world.blocks, {foil.flatten(pos, (0, 0, 0)): name for pos, name in blocks.items()})
        before = deepcopy(world.blocks)
        self.loaded(system, chunk)
        self.assertEqual(world.blocks, before)
        self.assertEqual(state['moved'], 3)

    def test_unrelated_or_wrong_dimension_event_does_not_poll_pending(self):
        system, world, state, blocked, chunk, checks, blocks = self.scene()
        system._process_field(0, state)
        before = len(checks)
        self.loaded(system, (1000, 1000))
        self.loaded(system, chunk, dimension=1)
        self.assertEqual(len(checks), before)

    def test_source_and_target_must_both_load_before_applying(self):
        system, world, state, blocked, chunk, checks, blocks = self.scene()
        blocked.add((0, 0))
        system._process_field(0, state)
        self.assertEqual(state['moved'], 0)
        blocked.remove(chunk)
        self.loaded(system, chunk)
        self.assertEqual(state['moved'], 0)
        self.assertEqual(world.blocks, blocks)
        blocked.clear()
        self.loaded(system, (0, 0))
        self.assertEqual(state['moved'], 3)

    def test_chunk_unloaded_again_is_redeferred_until_the_next_event(self):
        system, world, state, blocked, chunk, checks, blocks = self.scene()
        system._process_field(0, state)
        before = state['moved']
        self.loaded(system, chunk)
        self.assertEqual(state['moved'], before)
        self.assertEqual(state['status'], 'waiting_chunks')
        blocked.clear()
        self.loaded(system, chunk)
        self.assertEqual(state['phase'], 'complete')

    def test_saved_pending_references_resume_even_if_load_event_was_missed(self):
        system, world, state, blocked, chunk, checks, blocks = self.scene()
        system._process_field(0, state)
        saved = deepcopy(state)
        system.fields['0'] = saved
        blocked.clear()
        system._process_field(0, saved)
        self.assertEqual(saved['moved'], 3)
        self.assertEqual(saved['phase'], 'complete')
        self.assertEqual(world.reads, 1)

    def test_real_write_failure_retains_pending_then_retries_without_double_counting(self):
        system, world, state, blocked, chunk, checks, blocks = self.scene()
        system._process_field(0, state)
        blocked.clear()
        world.fail = True
        before = state['moved']
        self.loaded(system, chunk)
        self.assertEqual(state['moved'], before)
        self.assertGreater(len(state['pending_moves']), 0)
        world.fail = False
        system._process_field(0, state)
        self.assertEqual(state['moved'], 3)
        self.assertEqual(state['phase'], 'complete')

    def test_event_respects_budget_and_remaining_ready_items_continue_on_ticks(self):
        system, world, state, blocked, chunk, checks, blocks = self.scene()
        blocked.add((0, 0))
        system._process_field(0, state)
        blocked.clear()
        foil.FOIL_BLOCKS_PER_TICK = 1
        self.loaded(system, (0, 0))
        self.assertEqual(state['moved'], 1)
        system._process_field(0, state)
        self.assertEqual(state['moved'], 2)
        system._process_field(0, state)
        self.assertEqual(state['moved'], 3)

    def test_selected_reference_preserves_liquid_actor_and_container_index(self):
        system, world, state, blocked, chunk, checks, blocks = self.scene()
        refs = scan_references(state, 1)
        block, offset = refs[0]
        target = state['target_palette']
        index = target['common'][block][offset]
        target['extra'] = {('water', 0): [index]}
        target['actor'] = {'chest': {index: {'value': 7}}}
        state['nbt'] = {index: {'items': [7]}}
        batch = reference_batch(state, refs, PaletteContacts(state, True))
        self.assertEqual(batch['output']['extra'], target['extra'])
        self.assertEqual(batch['output']['actor'], target['actor'])
        self.assertEqual(state['nbt'][index], {'items': [7]})

    def test_multiple_load_events_and_tick_share_the_same_tick_budget(self):
        system, world, state, blocked, chunk, checks, blocks = self.scene()
        blocked.add((0, 0))
        system._process_field(0, state)
        blocked.clear()
        system.tick = 100
        foil.FOIL_BLOCKS_PER_TICK = 1
        self.loaded(system, (0, 0))
        self.loaded(system, chunk)
        system._process_field(0, state)
        self.assertEqual(state['moved'], 1)
        system.tick += 1
        system._process_field(0, state)
        self.assertEqual(state['moved'], 2)

    def test_wait_index_wakes_only_related_tokens_and_deduplicates_events(self):
        state = {'pending_moves': {1: ('a', 0), 2: ('b', 0)}}
        queue = PendingMoves(state)
        for unused in range(2):
            token, ref = queue.pop()
            queue.wait(token, {(token, 0), (9, 0)})
        self.assertEqual(queue.wake((1, 0)), 1)
        self.assertEqual(queue.wake((1, 0)), 0)
        self.assertEqual(len(queue.ready), 1)
        self.assertEqual(queue.waiters[(9, 0)], {2})


if __name__ == '__main__':
    unittest.main()
