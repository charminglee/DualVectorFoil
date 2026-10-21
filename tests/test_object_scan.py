# -*- coding: utf-8 -*-
# =================================================
#  ⠀
#   Author: Nuoyan <https://github.com/charminglee>
#   Email : 1279735247@qq.com
#   Date  : 2026-10-21
#  ⠀
# =================================================


# region Object Scan Tests ==================================================


import os
import sys
import types
import unittest

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

from dualvectorfoil_scripts.common.config import (
    FOIL_BLOCKS_PER_TICK,
    MAX_FOIL_BLOCKS,
    MAX_FOIL_ENTITIES,
)
from dualvectorfoil_scripts.modules.foil.server import (
    advance_scan,
    begin_scan,
    entity_contact_candidates,
)


class ScanWorld(object):
    """
    提供可控制读取、区块等待和方块表的世界替身。
    """

    def __init__(self, blocks, fail_position=None):
        self.blocks = set(blocks)
        self.fail_position = fail_position
        self.status = "ready"

    def ready(self, pos, target):
        """
        模拟区块是否已加载，并可让指定位置等待一次。
        """
        if pos == self.fail_position:
            self.fail_position = None
            self.status = "loading_chunks"
            return False
        self.status = "ready"
        return True

    def read(self, pos):
        """
        按内存方块表返回目标格点快照。
        """
        name = "minecraft:stone" if pos in self.blocks else "minecraft:air"
        return {'block': {'name': name, 'aux': 0}}


def collect(world, anchor, block_limit=100000):
    """
    反复推进扫描直到完成并返回选中方块。
    """
    state = {}
    begin_scan(state, anchor)
    while True:
        complete, status, capped = advance_scan(
            state,
            world,
            -64,
            319,
            None,
            block_limit,
            29999900,
        )
        if complete:
            return set(tuple(pos) for pos in state['object']), status, capped


class ObjectScanTests(unittest.TestCase):
    """
    验证六面连通扫描、等待重试和方块上限。
    """

    def test_only_six_face_connected_component_is_selected(self):
        """
        验证只选择与命中方块六面连通的组件。
        """
        blocks = {(0, 0, 0), (1, 0, 0), (2, 0, 0), (2, 1, 0), (2, 1, 1), (20, 0, 0)}
        selected, status, capped = collect(ScanWorld(blocks), (0, 0, 0))
        self.assertEqual(selected, blocks - {(20, 0, 0)})
        self.assertEqual(status, "ready")
        self.assertFalse(capped)

    def test_unlimited_budget_completes_in_single_call(self):
        """
        验证无预算限制时一次调用即可完成扫描。
        """
        state = {}
        begin_scan(state, (0, 0, 0))
        complete, status, capped = advance_scan(
            state, ScanWorld({(0, 0, 0), (1, 0, 0)}), -64, 319, None, 100000, 29999900)
        self.assertTrue(complete)
        self.assertEqual(status, "ready")
        self.assertFalse(capped)
        self.assertEqual(len(state['object']), 2)
        self.assertNotIn('scan_queue', state)

    def test_diagonal_block_is_not_connected(self):
        """
        验证仅对角相邻的方块不属于同一物体。
        """
        selected, status, capped = collect(ScanWorld({(0, 0, 0), (1, 1, 0)}), (0, 0, 0))
        self.assertEqual(selected, {(0, 0, 0)})

    def test_block_limit_stops_component_traversal(self):
        """
        验证扫描在达到方块上限时停止并标记触顶。
        """
        blocks = set((x, 0, 0) for x in range(10))
        selected, status, capped = collect(ScanWorld(blocks), (0, 0, 0), block_limit=4)
        self.assertEqual(len(selected), 4)
        self.assertEqual(status, "block_limit")
        self.assertTrue(capped)

    def test_unready_chunk_retries_same_cursor(self):
        """
        验证未加载区块会保留同一扫描游标并重试。
        """
        world = ScanWorld({(0, 0, 0), (1, 0, 0)}, fail_position=(1, 0, 0))
        state = {}
        begin_scan(state, (0, 0, 0))
        complete, status, capped = advance_scan(state, world, -64, 319, 10, 100, 29999900)
        self.assertFalse(complete)
        self.assertEqual(status, "loading_chunks")
        self.assertEqual(state['object'], [[0, 0, 0]])
        complete = False
        while not complete:
            complete, status, capped = advance_scan(state, world, -64, 319, 10, 100, 29999900)
        self.assertEqual({tuple(pos) for pos in state['object']}, {(0, 0, 0), (1, 0, 0)})

    def test_entity_on_top_of_object_matches_support_block(self):
        """
        验证站在物体上的实体能匹配脚底支撑方块。
        """
        self.assertEqual(entity_contact_candidates((2.5, 1.0, -3.5))[0], (2, 0, -4))
        self.assertEqual(entity_contact_candidates((2.5, 1.2, -3.5))[0], (2, 1, -4))

    def test_config_limits(self):
        """
        验证公共配置中的方块数和每 tick 上限。
        """
        self.assertEqual(MAX_FOIL_BLOCKS, 500000)
        self.assertIsNone(MAX_FOIL_ENTITIES)
        self.assertEqual(FOIL_BLOCKS_PER_TICK, 50)


if __name__ == "__main__":
    unittest.main()


# endregion
