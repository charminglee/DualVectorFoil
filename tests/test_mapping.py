# -*- coding: utf-8 -*-
# =================================================
#  ⠀
#   Author: Nuoyan <https://github.com/charminglee>
#   Email : 1279735247@qq.com
#   Date  : 2026-10-21
#  ⠀
# =================================================


# region Mapping and Transfer Tests ==================================================


import os
import sys
import types
import unittest
from copy import deepcopy

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src", "bp"))


def module(name):
    """
    创建并注册指定名称的测试模块替身。
    """
    result = types.ModuleType(name)
    result.__path__ = []
    sys.modules[name] = result
    return result


for name in ("mod", "mod.server", "mod.common"):
    module(name)
server_api = module("mod.server.extraServerApi")
sys.modules['mod'].server = sys.modules['mod.server']
sys.modules['mod.server'].extraServerApi = server_api
enums = module("mod.common.minecraftEnum")
enums.GameType = type("GameType", (), {'Creative': 1})
enums.ItemPosType = type("ItemPosType", (), {'CARRIED': 0})
library = module("dualvectorfoil_scripts.nuoyanlib")
library.server = module(library.__name__ + ".server")
library.server.LvComp = object()
library.server.event = lambda *args, **kwargs: (lambda func: func)
constants = module("dualvectorfoil_scripts.common.constant")
constants.CLIENT_SYSTEM_NAME = "MainClientSystem"
constants.SERVER_SYSTEM_NAME = "MainServerSystem"
constants.ServerEvent = type("ServerEvent", (), {'FoilFieldState': "FoilFieldState"})
module("dualvectorfoil_scripts.modules._base.server").BaseServer = object

from dualvectorfoil_scripts.modules.foil.server import (
    PlanePages, advance_scan, begin_scan, flatten, prepare, run_batch, step, unflatten)


class MappingTests(unittest.TestCase):
    """
    验证三维格点到二维平面的唯一映射和可逆性。
    """

    def test_injective_roundtrip_all_signed_points(self):
        """
        验证正负坐标范围内的映射无碰撞且可往返还原。
        """
        origin = (-17, 62, 29)
        seen = set()
        for x in range(-16, 17):
            for y in range(-16, 17):
                for z in range(-16, 17):
                    p = (x, y, z)
                    q = flatten(p, origin)
                    self.assertEqual(q[1], origin[1])
                    self.assertEqual(unflatten(q, origin), p)
                    self.assertNotIn(q, seen)
                    seen.add(q)

    def test_large_and_stable_coordinates(self):
        """
        验证世界边界和极大坐标仍能稳定往返。
        """
        for p in [(29999900, 319, -29999900), (-10**18, -64, 10**18)]:
            self.assertEqual(unflatten(flatten(p, (0, 0, 0)), (0, 0, 0)), p)


class FakeWorld(object):
    """
    提供可注入读写失败的内存方块世界。
    """

    def __init__(self, blocks):
        self.blocks = dict((p, {'block': {'name': name, 'aux': 0}}) for p, name in blocks.items())
        self.fail_write = False
        self.fail_clear = False
        self.status = "ready"

    def ready(self, src, dst):
        """
        模拟目标世界或区块是否可操作。
        """
        return True

    def read(self, pos):
        """
        从内存方块表读取指定位置。
        """
        return self.blocks.get(pos, {'block': {'name': "minecraft:air", 'aux': 0}})

    def write(self, pos, snapshot):
        """
        把方块快照写入内存表并支持故障注入。
        """
        if self.fail_write:
            return False
        self.blocks[pos] = snapshot
        return True

    def clear(self, pos):
        """
        清除内存表中的指定方块并支持故障注入。
        """
        if self.fail_clear:
            return False
        self.blocks.pop(pos, None)
        return True


class FakePages(object):
    """
    提供可注入保存失败的内存分页日志。
    """

    def __init__(self):
        self.data = {}
        self.fail_save = False
        self.flush_count = 0

    def get(self, pos):
        """
        读取内存分页中的目标格点。
        """
        return self.data.get(pos)

    def put(self, pos, value):
        """
        把原始快照写入内存分页。
        """
        self.data[pos] = value

    def flush(self, state):
        """
        记录持久化次数并模拟保存结果。
        """
        self.flush_count += 1
        return not self.fail_save


class TransferTests(unittest.TestCase):
    """
    验证批量搬移、续跑、日志恢复和失败安全。
    """

    def test_air_does_not_wait_for_or_generate_destination_chunks(self):
        """
        验证空气方块不会等待或生成目标区块。
        """

        class SourceOnlyWorld(FakeWorld):
            """
            只允许读取源位置的测试世界。
            """

            def ready(self, src, dst):
                """
                模拟目标世界或区块是否可操作。
                """
                return not (dst)
        state = {'origin': (0, 0, 0)}
        prepare(state, (100, 30, 100))
        self.assertTrue(step(state, SourceOnlyWorld({}), FakePages()))

    def test_batch_moves_fifty_blocks_with_two_persists(self):
        """
        验证五十格批次只执行两次持久化。
        """
        sources = [(x, 1, 0) for x in range(50)]
        world = FakeWorld(dict((pos, "stone") for pos in sources))
        pages = FakePages()
        state = {'origin': (0, 0, 0), 'move_cursor': 0, 'moved': 0}
        complete, status = run_batch(state, sources, world, pages)
        self.assertTrue(complete)
        self.assertEqual(status, "ready")
        self.assertEqual(state['move_cursor'], 50)
        self.assertEqual(state['moved'], 50)
        self.assertEqual(pages.flush_count, 2)
        self.assertNotIn('batch', state)
        for source in sources:
            self.assertNotIn(source, world.blocks)
            destination = flatten(source, state['origin'])
            self.assertEqual(world.blocks[destination]['block']['name'], "stone")

    def test_batch_resumes_from_failed_world_write(self):
        """
        验证世界写入或清除失败后可从批次游标续跑。
        """
        sources = [(0, 1, 0), (1, 1, 0)]
        world = FakeWorld(dict((pos, "stone") for pos in sources))
        pages = FakePages()
        state = {'origin': (0, 0, 0), 'move_cursor': 0, 'moved': 0}
        fail_at = {sources[0]}
        original_clear = world.clear

        def clear(pos):
            """
            清除内存表中的指定方块并支持故障注入。
            """
            if pos in fail_at:
                return False
            return original_clear(pos)

        world.clear = clear
        complete, status = run_batch(state, sources, world, pages)
        self.assertFalse(complete)
        self.assertEqual(status, "clear_failed")
        self.assertIn('batch', state)
        self.assertEqual(state['move_cursor'], 0)
        fail_at.clear()
        complete, status = run_batch(state, sources, world, pages)
        self.assertTrue(complete)
        self.assertEqual(state['move_cursor'], 2)
        self.assertEqual(state['moved'], 2)
        self.assertNotIn('batch', state)

    def test_restart_replays_journal_without_consuming_new_output(self):
        """
        验证重启重放日志时不会吞掉新的目标位置内容。
        """
        state = {'origin': (0, 0, 0)}
        src = (0, 1, 0)
        dst = flatten(src, state['origin'])
        world, pages = FakeWorld({src: "stone", dst: "gold"}), FakePages()
        prepare(state, src)
        world.fail_clear = True
        self.assertFalse(step(state, world, pages))
        restarted = deepcopy(state)
        world.fail_clear = False
        self.assertTrue(step(restarted, world, pages))
        self.assertEqual(world.read(dst)['block']['name'], "stone")
        self.assertEqual(pages.get(dst)['original']['block']['name'], "gold")

    def test_dense_connected_cube_survives_reordered_transfers(self):
        """
        验证稠密连通立方体在乱序搬移后仍保持全部内容。
        """
        scan_state = {}
        original = {}
        for x in range(-3, 4):
            for y in range(-3, 4):
                for z in range(-3, 4):
                    original[(x, y, z)] = "block_%d_%d_%d" % (x, y, z)
        world, pages = FakeWorld(original), FakePages()
        begin_scan(scan_state, (0, 0, 0))
        while True:
            complete, status, capped = advance_scan(
                scan_state,
                world,
                -64,
                319,
                1000,
                100000,
                29999900,
            )
            if complete:
                break
        self.assertEqual(len(scan_state['object']), 343)
        state = {'origin': (0, 0, 0), 'move_cursor': 0, 'moved': 0}
        for start in range(0, len(scan_state['object']), 50):
            sources = [tuple(source) for source in scan_state['object'][start:start + 50]]
            complete, status = run_batch(state, sources, world, pages)
            self.assertTrue(complete)
        for pos, name in original.items():
            self.assertEqual(world.read(flatten(pos, state['origin']))['block']['name'], name)
        self.assertTrue(all(pos[1] == 0 for pos in world.blocks))

    def test_overwritten_future_input_is_preserved(self):
        """
        验证输出覆盖未来输入时原内容会进入分页日志。
        """
        state = {'origin': (0, 0, 0)}
        first = (0, 1, 0)
        overwritten = flatten(first, state['origin'])
        second_dest = flatten(overwritten, state['origin'])
        self.assertNotEqual(overwritten, second_dest)
        world = FakeWorld({first: "stone", overwritten: "gold"})
        pages = FakePages()
        prepare(state, first)
        self.assertTrue(step(state, world, pages))
        prepare(state, overwritten)
        self.assertTrue(step(state, world, pages))
        self.assertEqual(world.read(overwritten)['block']['name'], "stone")
        self.assertEqual(world.read(second_dest)['block']['name'], "gold")

    def test_failures_never_erase_source(self):
        """
        验证持久化、写入或清除失败时不会提前删除源方块。
        """
        src = (0, 1, 0)
        state = {'origin': (0, 0, 0)}
        world, pages = FakeWorld({src: "stone"}), FakePages()
        prepare(state, src)
        pages.fail_save = True
        self.assertFalse(step(state, world, pages))
        self.assertEqual(world.read(src)['block']['name'], "stone")
        pages.fail_save, world.fail_write = False, True
        self.assertFalse(step(state, world, pages))
        self.assertEqual(world.read(src)['block']['name'], "stone")
        world.fail_write, world.fail_clear = False, True
        self.assertFalse(step(state, world, pages))
        world.fail_clear = False
        self.assertTrue(step(state, world, pages))
        self.assertTrue(step(state, world, pages))
        self.assertEqual(world.read(flatten(src, state['origin']))['block']['name'], "stone")


class ExtraData(object):
    """
    提供内存版额外数据持久化接口。
    """

    def __init__(self):
        self.values = {}

    def GetExtraData(self, key):
        """
        读取并深拷贝内存额外数据。
        """
        return deepcopy(self.values.get(key))

    def SetExtraData(self, key, value, autoSave=False):
        """
        保存并深拷贝内存额外数据。
        """
        self.values[key] = deepcopy(value)
        return True

    def SaveExtraData(self):
        """
        模拟额外数据保存成功。
        """
        return True


class StorageTests(unittest.TestCase):
    """
    验证分页日志的保存、淘汰和恢复。
    """

    def test_evicted_negative_coordinate_pages_can_be_restored(self):
        """
        验证负坐标分页被淘汰后仍可从额外数据恢复。
        """
        extra = ExtraData()
        pages = PlanePages(extra, 0, {})
        for i in range(-30, 30):
            pages.put((i * 16 + 3, 50, -1), {'original': i})
            self.assertTrue(pages.flush({}))
        self.assertLessEqual(len(pages.cache), 16)
        restored = PlanePages(extra, 0, {})
        for i in range(-30, 30):
            self.assertEqual(restored.get((i * 16 + 3, 50, -1))['original'], i)


if __name__ == "__main__":
    unittest.main()


# endregion
