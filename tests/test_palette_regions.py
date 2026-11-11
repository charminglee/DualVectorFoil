# -*- coding: utf-8 -*-
"""局部调色板写入、失败读回边界与分层索引回归；仅供离线测试。"""
import unittest
from copy import deepcopy
import test_effect_events as fixtures
from dualvectorfoil_scripts.modules.foil import server as foil
from dualvectorfoil_scripts.modules.foil.palette import (
    empty_data, encode_index, palette_regions, world_position,
)


def world_layers(data, start):
    result = {}
    for layer in ('common', 'extra'):
        result[layer] = dict((world_position(index, data['volume'], start), block)
                             for block, indices in data[layer].items() for index in indices)
    result['actor'] = dict((world_position(index, data['volume'], start), (kind, value))
                           for kind, actors in data['actor'].items() for index, value in actors.items())
    return result


class NativeBlocks(object):
    """模拟原生稀疏写入；总返回 False，迫使正式适配器执行读回校验。"""
    def __init__(self):
        self.cells = {'common': {}, 'extra': {}}
        self.states = {'states': {}, 'extraStates': {}}
        self.writes, self.reads = [], []
        self.drop_write = False
        self.drop_states = False

    def GetBlankBlockPalette(self):
        return self

    def DeserializeBlockPalette(self, data):
        self.pending = deepcopy(data)
        return True

    def SetBlockByBlockPalette(self, palette, dimension, start, rotation, conflict):
        self.writes.append((deepcopy(self.pending), start))
        if not self.drop_write:
            values = world_layers(self.pending, start)
            for layer, states in (('common', 'states'), ('extra', 'extraStates')):
                self.cells[layer].update(values[layer])
                self.states[states].update(self.pending[states])
        return False

    def capture(self, start, end):
        volume = (end[2] - start[2] + 1, end[0] - start[0] + 1, end[1] - start[1] + 1)
        # 旧实现会在这里申请整个 152 万格平面；不让测试真的枚举这些格点。
        assert max(volume) <= 16, ('unbounded_readback', volume)
        self.reads.append((start, end))
        data = empty_data(volume)
        for layer, states in (('common', 'states'), ('extra', 'extraStates')):
            for pos, block in self.cells[layer].items():
                if all(start[i] <= pos[i] <= end[i] for i in range(3)):
                    local = tuple(pos[i] - start[i] for i in range(3))
                    data[layer].setdefault(block, []).append(encode_index(local, volume))
            if not self.drop_states:
                data[states] = deepcopy(self.states[states])
        return data


def adapter():
    native = NativeBlocks()
    world = foil.WorldAdapter.__new__(foil.WorldAdapter)
    world.dimension, world.status = 0, 'ready'
    world.blocks = native
    world.capture = native.capture
    return world, native


class RegionTests(unittest.TestCase):
    def test_partition_preserves_signed_world_positions_states_liquid_and_actor(self):
        start, volume = (-33, -18, -17), (80, 90, 70)
        data = empty_data(volume)
        a = ('minecraft:chest', 2)
        b = ('minecraft:oak_stairs', 3)
        water = ('minecraft:water', 0)
        data['common'] = {a: [0, encode_index((17, 20, 16), volume)], b: [encode_index((89, 69, 79), volume)]}
        data['states'] = {a: {'facing': 2}, b: {'facing': 3}, ('unused', 0): {}}
        data['extra'] = {water: [data['common'][b][0]]}
        data['extraStates'] = {water: {'depth': 0}}
        data['actor'] = {'chest': {data['common'][a][1]: {'items': [7]}}}
        before = deepcopy(data)
        expected = world_layers(data, start)
        combined = {'common': {}, 'extra': {}, 'actor': {}}
        for region, region_start in palette_regions(data, start):
            self.assertLessEqual(max(region['volume']), 16)
            self.assertNotIn(('unused', 0), region['states'])
            for layer, values in world_layers(region, region_start).items():
                combined[layer].update(values)
            for states in ('states', 'extraStates'):
                for block, value in region[states].items():
                    self.assertEqual(value, data[states][block])
        self.assertEqual(combined, expected)
        self.assertEqual(data, before)

    def test_50_sparse_points_do_not_read_full_1520000_cell_plane(self):
        data = empty_data((764, 1987, 1))
        block = ('minecraft:stone', 0)
        data['common'][block] = [encode_index((i * 32, 0, (i % 20) * 32), data['volume']) for i in range(50)]
        world, native = adapter()
        native.cells['common'][(10000, 0, 10000)] = ('untouched', 0)
        self.assertTrue(world.apply(data, (-1000, 70, -500)))
        self.assertEqual(len(native.reads), 50)
        self.assertTrue(all(start == end for start, end in native.reads))
        self.assertEqual(native.cells['common'][(10000, 0, 10000)], ('untouched', 0))
        self.assertEqual(len(native.cells['common']), 51)

    def test_false_return_is_accepted_only_when_all_expected_layers_match(self):
        data = empty_data((2, 1, 1))
        data['common'] = {('stairs', 3): [0, 1]}
        data['states'] = {('stairs', 3): {'facing': 3}}
        data['extra'] = {('water', 0): [1]}
        data['extraStates'] = {('water', 0): {'depth': 0}}
        world, native = adapter()
        self.assertTrue(world.apply(data, [1, 2, 3]))
        native.drop_write = True
        native.cells['extra'].clear()
        self.assertFalse(world.apply(data, [1, 2, 3]))
        self.assertEqual(world.status, 'palette_write_failed')
        self.assertEqual(world.last_error['layer'], 'extra')
        self.assertEqual(world.last_error['pos'], (1, 2, 4))

    def test_missing_state_is_reported_without_keyerror(self):
        data = empty_data((1, 1, 1))
        data['common'] = {('stone', 0): [0]}
        data['states'] = {('stone', 0): {'value': 1}}
        world, native = adapter()
        native.drop_states = True
        self.assertFalse(world.apply(data, (1, 2, 3)))
        self.assertEqual(world.last_error['reason'], 'state_mismatch')
        self.assertEqual(world.last_error['pos'], (1, 2, 3))

    def test_empty_batch_never_writes_or_reads(self):
        world, native = adapter()
        self.assertTrue(world.apply(empty_data((764, 1987, 1)), (0, 0, 0)))
        self.assertEqual(native.writes, [])
        self.assertEqual(native.reads, [])

    def test_holes_in_compact_region_preserve_unrelated_blocks(self):
        data = empty_data((1000, 1000, 1))
        data['common'] = {('stone', 0): [0, 2]}
        world, native = adapter()
        native.cells['common'][(0, 0, 1)] = ('untouched', 0)
        self.assertTrue(world.apply(data, (0, 0, 0)))
        self.assertEqual(native.cells['common'][(0, 0, 1)], ('untouched', 0))
        self.assertEqual(native.writes[0][0]['volume'], (3, 1, 1))
        self.assertEqual(native.reads, [((0, 0, 0), (0, 0, 2))])

    def test_later_partition_failure_can_be_retried_without_resetting_progress(self):
        data = empty_data((100, 100, 1))
        data['common'] = {('stone', 0): [0, encode_index((32, 0, 32), data['volume'])]}
        world, native = adapter()
        original = native.SetBlockByBlockPalette
        def fail_second(palette, dimension, start, rotation, conflict):
            native.drop_write = len(native.writes) == 1
            return original(palette, dimension, start, rotation, conflict)
        native.SetBlockByBlockPalette = fail_second
        self.assertFalse(world.apply(data, (-10, 5, -10)))
        self.assertEqual(len(native.cells['common']), 1)
        native.SetBlockByBlockPalette = original
        native.drop_write = False
        self.assertTrue(world.apply(data, (-10, 5, -10)))
        self.assertEqual(native.cells['common'], world_layers(data, (-10, 5, -10))['common'])
        self.assertIsNone(world.last_error)

    def test_real_failure_keeps_batch_cursor_and_source_intact(self):
        data = empty_data((1, 1, 1))
        data['common'] = {('stone', 0): [0]}
        world, native = adapter()
        native.drop_write = True
        world.info = None
        batch = {'output': data, 'clear': data, 'count': 1}
        state = {'target_start': (10, 5, 0), 'source_start': (0, 5, 0),
                 'move_cursor': 0, 'moved': 0, 'nbt': {}}
        self.assertFalse(world.move(state, batch))
        self.assertEqual(state['move_cursor'], 0)
        self.assertEqual(len(native.writes), 1)
        self.assertEqual(world.last_error['pos'], (10, 5, 0))


if __name__ == '__main__':
    unittest.main()
