# -*- coding: utf-8 -*-
"""调色板数据协议、球形筛选、重叠搬移、预算和失败重试回归。"""
import unittest
from copy import deepcopy
from math import sqrt
import test_effect_events as fixtures
from dualvectorfoil_scripts.modules.foil import server as foil
from dualvectorfoil_scripts.modules.foil.palette import (
    PaletteContacts, decode_index, empty_data, encode_index, plan_palette,
    slice_batch, world_position,
)


def make_data(blocks, start, volume):
    data = empty_data(volume)
    for pos, name in blocks.items():
        index = encode_index(tuple(pos[i] - start[i] for i in range(3)), volume)
        data['common'].setdefault((name, 0), []).append(index)
    return data


class MemoryWorld(object):
    def __init__(self, blocks):
        self.blocks = dict(blocks)
        self.status = 'ready'
        self.reads = 0
        self.fail = False
        self.closed = False

    def ready_region(self, *args):
        return True

    def capture(self, start, end):
        self.reads += 1
        volume = (end[2] - start[2] + 1, end[0] - start[0] + 1, end[1] - start[1] + 1)
        return make_data(self.blocks, start, volume)

    def capture_nbt(self, state):
        return {}

    def move(self, state, batch):
        if self.fail:
            self.status = 'injected_write_failure'
            return False
        for data, start in ((batch['output'], state['target_start']), (batch['clear'], state['source_start'])):
            for block, indices in data['common'].items():
                for index in indices:
                    pos = world_position(index, data['volume'], start)
                    if block[0] == 'minecraft:air':
                        self.blocks.pop(pos, None)
                    else:
                        self.blocks[pos] = block[0]
        return True

    def close(self):
        self.closed = True


def sandbox(blocks, radius=3):
    system = foil.FoilServer.__new__(foil.FoilServer)
    world = MemoryWorld(blocks)
    state = {'origin': [0, 0, 0], 'anchor': [0, 0, 0], 'radius': radius,
             'phase': 'capturing', 'block_count': 0, 'move_cursor': 0, 'moved': 0}
    system.fields = {'0': state}
    system.worlds = {0: world}
    system.object_sets, system.target_sets = {}, {}
    system._save = lambda: True
    system._broadcast_field_state = lambda *args: None
    system._message = lambda *args: None
    return system, world, state


class PaletteTests(unittest.TestCase):
    def test_sdk_asymmetric_index_layout(self):
        volume = (5, 3, 4)
        # SDK 实机确认 Z 最快，随后 X，最后 Y；不能用对称立方体掩盖轴互换。
        self.assertEqual(encode_index((1, 2, 3), volume), 38)
        self.assertEqual(decode_index(38, volume), (1, 2, 3))
        self.assertEqual(world_position(38, volume, (-7, -64, 12)), (-6, -62, 15))

    def test_sphere_includes_disconnected_blocks_and_excludes_corners(self):
        blocks = {(0, 1, 0): 'stone', (3, 0, 0): 'gold', (3, 3, 0): 'dirt'}
        data = make_data(blocks, (-3, -3, -3), (7, 7, 7))
        plan = plan_palette(data, (-3, -3, -3), (0, 0, 0), (0, 0, 0), 3, foil.flatten, foil.WORLD_LIMIT)
        contacts = PaletteContacts(plan)
        self.assertEqual(plan['block_count'], 2)
        self.assertIn((3, 0, 0), contacts)
        self.assertNotIn((3, 3, 0), contacts)
        self.assertNotIn((0, 0, 0), contacts)

    def test_precomputed_mapping_matches_original_for_signed_asymmetric_volume(self):
        start, volume, center = (-4, -2, 5), (7, 5, 3), (-2, -1, 8)
        blocks = {world_position(i, volume, start): 'b%d' % i for i in range(105)}
        data = make_data(blocks, start, volume)
        plan = plan_palette(data, start, center, center, 20, foil.flatten, foil.WORLD_LIMIT)
        for block in plan['groups']:
            source = world_position(plan['source_palette']['common'][block][0], volume, start)
            target = world_position(plan['target_palette']['common'][block][0], plan['target_palette']['volume'], plan['target_start'])
            self.assertEqual(target, foil.flatten(source, center))

    def test_liquid_and_actor_layers_follow_same_index_and_filter(self):
        data = make_data({(1, 0, 0): 'chest', (2, 2, 2): 'chest'}, (0, 0, 0), (3, 3, 3))
        inside, outside = encode_index((1, 0, 0), data['volume']), encode_index((2, 2, 2), data['volume'])
        data['extra'] = {('water', 0): [inside, outside]}
        data['actor'] = {'chest': {inside: {'value': 7}, outside: {'value': 8}}}
        plan = plan_palette(data, (0, 0, 0), (0, 0, 0), (0, 0, 0), 1, foil.flatten, foil.WORLD_LIMIT)
        target = plan['target_palette']
        index = target['common'][('chest', 0)][0]
        self.assertEqual(target['extra'][('water', 0)], [index])
        self.assertEqual(target['actor']['chest'], {index: {'value': 7}})
        batch = slice_batch(plan, -1, PaletteContacts(plan, True))
        self.assertEqual(batch['output']['extra'], target['extra'])
        self.assertEqual(batch['output']['actor'], target['actor'])

    def test_world_boundary_rejects_whole_plan(self):
        data = make_data({(9, 1, 0): 'stone'}, (9, 0, 0), (1, 1, 2))
        self.assertIsNone(plan_palette(data, (9, 0, 0), (9, 0, 0), (9, 0, 0), 3, foil.flatten, 9))

    def test_dense_overlap_and_retry_preserve_all_original_values(self):
        blocks = {(x, y, z): 'b%d_%d_%d' % (x, y, z) for x in range(-3, 4) for y in range(-3, 4) for z in range(-3, 4) if x*x+y*y+z*z <= 9}
        system, world, state = sandbox(blocks)
        old = foil.FOIL_BLOCKS_PER_TICK
        foil.FOIL_BLOCKS_PER_TICK = 7
        self.addCleanup(setattr, foil, 'FOIL_BLOCKS_PER_TICK', old)
        system._process_field(0, state)
        frozen = deepcopy(state['target_palette'])
        world.fail = True
        system._process_field(0, state)
        self.assertEqual(state['moved'], 0)
        world.fail = False
        # 从持久化格式恢复系统，不能重新读取已经被覆盖的输入。
        system.fields['0'] = state = deepcopy(state)
        for tick in range(100):
            before = state['moved']
            system._process_field(0, state)
            self.assertLessEqual(state['moved'] - before, 7)
            if state['phase'] == 'complete':
                break
        self.assertEqual(world.reads, 1)
        self.assertEqual(state['target_palette'], frozen)
        self.assertEqual(state['moved'], len(blocks))
        self.assertEqual(world.blocks, {foil.flatten(pos, (0, 0, 0)): name for pos, name in blocks.items()})
        self.assertTrue(world.closed)

    def test_minus_one_finishes_in_capture_call(self):
        system, world, state = sandbox({(0, 1, 0): 'stone', (3, 0, 0): 'gold'})
        old = foil.FOIL_BLOCKS_PER_TICK
        foil.FOIL_BLOCKS_PER_TICK = -1
        self.addCleanup(setattr, foil, 'FOIL_BLOCKS_PER_TICK', old)
        system._process_field(0, state)
        self.assertEqual(state['phase'], 'complete')
        self.assertEqual(state['moved'], 2)
        self.assertEqual(world.reads, 1)

    def test_empty_sphere_completes_without_writing(self):
        system, world, state = sandbox({})
        system._process_field(0, state)
        self.assertEqual(state['phase'], 'complete')
        self.assertEqual(state['status'], 'no_blocks')

    def test_failed_plan_persistence_does_not_modify_world(self):
        blocks = {(0, 1, 0): 'stone'}
        system, world, state = sandbox(blocks)
        system._save = lambda: False
        system._process_field(0, state)
        self.assertEqual(state['status'], 'waiting_io')
        self.assertEqual(world.blocks, blocks)
        self.assertEqual(state['moved'], 0)

    def test_more_than_old_block_limit_is_planned_without_truncation(self):
        radius, side = 50, 101
        data = empty_data((side, side, side))
        data['common'][('minecraft:stone', 0)] = list(range(side ** 3))
        plan = plan_palette(data, (-50, -50, -50), (0, 0, 0), (0, 0, 0), radius, foil.flatten, foil.WORLD_LIMIT)
        # 按二维截面的整数柱高独立计数，确认不会在旧的五十万额度截断。
        expected = sum(2 * int(sqrt(radius * radius - x*x - y*y)) + 1
                       for x in range(-radius, radius + 1)
                       for y in range(-radius, radius + 1) if x*x + y*y <= radius*radius)
        self.assertGreater(expected, 500000)
        self.assertEqual(plan['block_count'], expected)

    def test_zero_budget_does_not_write_or_advance(self):
        blocks = {(0, 1, 0): 'stone'}
        system, world, state = sandbox(blocks)
        old = foil.FOIL_BLOCKS_PER_TICK
        foil.FOIL_BLOCKS_PER_TICK = 0
        self.addCleanup(setattr, foil, 'FOIL_BLOCKS_PER_TICK', old)
        system._process_field(0, state)
        self.assertEqual(state['status'], 'invalid_config')
        self.assertEqual(world.blocks, blocks)


if __name__ == '__main__':
    unittest.main()
