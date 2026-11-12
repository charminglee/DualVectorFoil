# -*- coding: utf-8 -*-
# =================================================
#  ⠀
#   Author: Nuoyan <https://github.com/charminglee>
#   Email : 1279735247@qq.com
#   Date  : 2026-10-21
#  ⠀
# =================================================


# region Space Fall State Tests ==================================================


import json
import os
import sys
import types
import unittest

from event_args import make_event_args
from effect_components import install

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
library.client = module(library.__name__ + ".client")
library.server = module(library.__name__ + ".server")


def event(name="", ns="", sys_name="", **kwargs):
    """
    构造不产生额外行为的测试事件装饰器。
    """
    if callable(name):
        return name
    return lambda function: function


library.client.event = library.server.event = event
library.client.PLAYER_ID = "near"
library.client.LvComp = object()
library.server.LvComp = object()


def distance_square(left, right):
    """
    计算测试坐标之间的平方距离。
    """
    return sum((left[index] - right[index]) ** 2 for index in range(3))


def distance(left, right):
    """
    计算测试坐标之间的距离。
    """
    return distance_square(left, right) ** 0.5


library.client.distance_square = distance_square
library.client.distance = distance
library.server.distance_square = distance_square


class Member(object):
    """
    提供注册表枚举值的简单成员替身。
    """

    def __init__(self, value):
        self.value = value


class TestBase(object):
    """
    提供系统基类所需的最小初始化接口。
    """

    def __init__(self, namespace, system_name):
        self.namespace = namespace
        self.systemName = system_name


constants = module("dualvectorfoil_scripts.common.constant")
constants.MOD_NAMESPACE = "nuoyan"
constants.CLIENT_SYSTEM_NAME = "MainClientSystem"
constants.SERVER_SYSTEM_NAME = "MainServerSystem"
constants.ServerEvent = type("ServerEvent", (), {'FoilFieldState': "FoilFieldState"})
constants.ServerModule = type("ServerModule", (), {
    'Effect': Member(("EffectServer", "dualvectorfoil_scripts.modules.effect.server")),
})
module("dualvectorfoil_scripts.modules._base.client").BaseClient = TestBase
module("dualvectorfoil_scripts.modules._base.server").BaseServer = TestBase

from dualvectorfoil_scripts.modules.effect.playback import FieldPlayback
from dualvectorfoil_scripts.modules.effect.server import EffectServer
from dualvectorfoil_scripts.modules.effect.config import FADE_OUT, RADIUS, STRENGTH, PLAY_SECONDS
from dualvectorfoil_scripts.modules.foil.server import build_field_event


def snapshot(active=True, center=(0.0, 3.0, 0.0), dimension=0):
    """
    构造空间跌落视觉快照测试数据。
    """
    return make_event_args({
        'dimension': dimension,
        'run_id': 0,
        'active': active,
        'center': center,
        'plane_y': 0.02,
        'progress': 0.25,
    })


class StateTests(unittest.TestCase):
    """固定十五秒单轮包络与固定中心，不读取业务进度。"""
    def setUp(self):
        library.client.LvComp = install(type("Level", (), {'Camera': type("Camera", (), {'GetPosition': lambda self: (0, 3, 10)})()})())
        self.effect = FieldPlayback("nuoyan_space_fall")
        self.effect.start(snapshot(), 0.0)

    def frame(self, now, dimension=0, camera=(0.0, 3.0, 10.0), forward=(0.0, 0.0, -1.0)):
        return self.effect._frame(now, dimension, camera, forward)

    def test_one_round_envelope_and_exact_deadline(self):
        self.assertFalse(self.frame(0.0))
        self.assertAlmostEqual(self.frame(0.6)[1][1], STRENGTH)
        self.assertAlmostEqual(self.frame(3.0)[1][1], STRENGTH)
        self.assertGreater(self.frame(PLAY_SECONDS - FADE_OUT / 2.0)[1][1], 0)
        self.assertLess(self.frame(PLAY_SECONDS - FADE_OUT / 2.0)[1][1], STRENGTH)
        self.assertFalse(self.frame(PLAY_SECONDS))
        self.assertFalse(self.effect.snapshot)

    def test_progress_comes_only_from_elapsed_time(self):
        shape = self.frame(2.5)[1]
        self.assertEqual(shape[2], 2.5)
        self.assertAlmostEqual(shape[3], 1.074074074074074)
        self.assertNotIn('progress', self.effect.snapshot)

    def test_frozen_center_and_source_independent_plane_visibility(self):
        self.assertEqual(self.frame(1.0)[0][:3], (0.0, 3.0, 0.0))
        self.effect.start(snapshot(center=(0.0, 100.0, 0.0)), 1.0)
        self.assertTrue(self.frame(1.6))

    def test_dimension_and_visibility(self):
        self.assertFalse(self.frame(0.5, camera=(0.0, 3.0, 300.0)))
        self.assertTrue(self.effect.snapshot)
        self.assertTrue(self.frame(0.6, camera=(0.0, 3.0, 30.0), forward=(0.0, 0.0, 1.0)))
        self.assertTrue(self.frame(0.7))
        self.assertFalse(self.frame(0.8, dimension=-1))
        self.assertFalse(self.effect.snapshot)


class ProtocolTests(unittest.TestCase):
    """
    验证视觉协议不会遍历方块列表或污染事件数据。
    """

    def setUp(self):
        """
        初始化空间跌落服务端系统。
        """
        self.effect = EffectServer("nuoyan", "EffectServer")

    def test_snapshot_never_walks_or_serializes_block_list(self):
        """
        验证快照只读取最终方块而不会遍历完整方块列表。
        """

        class IndexOnly(object):
            """
            提供只支持索引访问的方块序列替身。
            """

            def __len__(self):
                return 500000

            def __getitem__(self, index):
                if index != 499999:
                    raise AssertionError("unexpected traversal")
                return 0

            def __iter__(self):
                raise AssertionError("block list must not be iterated")
        state = {
            'source_palette': {'volume': (1, 1, 1), 'common': {'test': IndexOnly()}},
            'source_start': (-5, 319, 7), 'groups': ['test'], 'group_index': 0, 'group_cursor': 500000, 'block_count': 500000,
            'move_cursor': 500000,
            'origin': [0, 60, 0],
            'phase': "complete",
        }
        event = build_field_event(0, state, 10)
        self.assertNotIn('object', event)
        payload = self.effect._make_snapshot(make_event_args(event))
        self.assertEqual(payload['center'], [0.5, 60.5, 0.5])
        self.assertEqual(payload['progress'], 0.0)
        self.assertTrue(payload['active'])
        self.assertLess(len(json.dumps(payload)), 180)

    def test_empty_target_has_no_visual_snapshot(self):
        """
        验证空目标不会产生视觉快照。
        """
        state = {'block_count': 0, 'move_cursor': 0, 'origin': [0, 60, 0], 'phase': "complete"}
        event = build_field_event(0, state, 0)
        self.assertFalse(event['source'])
        self.assertFalse(self.effect._make_snapshot(make_event_args(event)))

    def test_local_event_does_not_alias_mutable_world_data(self):
        """
        验证本地事件载荷隔离可变世界数据。
        """
        state = {'source_palette': {'volume': (1, 1, 1), 'common': {'test': [0]}}, 'source_start': [1, 2, 3], 'groups': ['test'], 'group_index': 0, 'group_cursor': 0, 'block_count': 1, 'move_cursor': 0, 'origin': [0, 60, 0], 'phase': "moving"}
        event = build_field_event(0, state, 5)
        state['source_start'][0] = 999
        state['origin'][1] = 100
        self.assertEqual(event['source'], (1, 2, 3))
        self.assertEqual(event['origin'], (0, 60, 0))
        before = dict(event)
        self.effect._make_snapshot(make_event_args(event))
        self.assertEqual(event, before)


if __name__ == "__main__":
    unittest.main()


# endregion
