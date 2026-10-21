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


class Member(object):
    """
    提供注册表枚举值的简单成员替身。
    """

    def __init__(self, value):
        self.value = value


constants = module("dualvectorfoil_scripts.common.constant")
constants.MOD_NAMESPACE = "nuoyan"
constants.CLIENT_SYSTEM_NAME = "MainClientSystem"
constants.SERVER_SYSTEM_NAME = "MainServerSystem"
constants.ServerEvent = type("ServerEvent", (), {'FoilFieldState': "FoilFieldState"})
constants.ServerModule = type("ServerModule", (), {
    'Effect': Member(("EffectServer", "dualvectorfoil_scripts.modules.effect.server")),
})
module("dualvectorfoil_scripts.modules._base.client").BaseClient = object
module("dualvectorfoil_scripts.modules._base.server").BaseServer = object

from dualvectorfoil_scripts.modules.effect.client import SpaceFallState
from dualvectorfoil_scripts.modules.effect.server import make_snapshot
from dualvectorfoil_scripts.modules.effect.config import FADE_OUT, RADIUS, STRENGTH, STALE_SECONDS
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
    """
    验证空间跌落时间包络和可见性状态机。
    """

    def setUp(self):
        """
        用活跃快照初始化视觉状态。
        """
        self.state = SpaceFallState()
        self.state.receive(snapshot(), 0.0)

    def frame(self, now, dimension=0, camera=(0.0, 3.0, 10.0), forward=(0.0, 0.0, -1.0)):
        """
        以默认摄像机参数请求当前视觉帧。
        """
        return self.state.frame(now, dimension, camera, forward)

    def test_attack_and_complete_release(self):
        """
        验证视觉场淡入、完成淡出和最终清理。
        """
        self.assertFalse(self.frame(0.0))
        field, shape = self.frame(0.6)
        self.assertAlmostEqual(field[3], RADIUS)
        self.assertAlmostEqual(shape[1], STRENGTH)
        self.state.receive(snapshot(False, (80.0, 3.0, 0.0)), 1.0)
        field, shape = self.frame(1.3)
        self.assertEqual(field[:3], (0.0, 3.0, 0.0))
        self.assertGreater(shape[1], 0)
        self.assertLess(shape[1], STRENGTH)
        self.assertFalse(self.frame(1.0 + FADE_OUT))
        self.assertFalse(self.state.snapshot)

    def test_small_object_keeps_a_visible_lifetime(self):
        """
        验证小物体完成时仍保留最短可见时间。
        """
        self.state.receive(snapshot(False), 0.03)
        self.assertGreater(self.frame(0.5)[1][1], STRENGTH * 0.9)

    def test_heartbeat_does_not_restart_attack(self):
        """
        验证同位置心跳不会重新触发淡入。
        """
        self.frame(0.6)
        self.state.receive(snapshot(center=(2.0, 3.0, 0.0)), 1.0)
        field, shape = self.frame(1.1)
        self.assertGreater(field[0], 0.0)
        self.assertLess(field[0], 2.0)
        self.assertAlmostEqual(shape[1], STRENGTH)
        self.assertEqual(self.state.started, 0.0)

    def test_far_branch_restarts_without_sweeping_intermediate_space(self):
        """
        验证搜索前沿跳跃时直接迁移中心而不扫过中间区域。
        """
        self.state.receive(snapshot(center=(100.0, 3.0, 0.0)), 1.0)
        self.assertEqual(self.state.center, (100.0, 3.0, 0.0))
        self.assertEqual(self.state.started, 1.0)

    def test_silence_expires_and_late_heartbeat_restarts(self):
        """
        验证心跳超时后淡出，迟到事件可重新开始。
        """
        self.assertFalse(self.frame(STALE_SECONDS + FADE_OUT + 0.1))
        self.assertFalse(self.state.snapshot)
        self.state.receive(snapshot(), 10.0)
        self.assertEqual(self.state.started, 10.0)

    def test_dimension_and_visibility(self):
        """
        验证维度切换、距离和背向剔除。
        """
        self.assertFalse(self.frame(0.5, camera=(0.0, 3.0, 100.0)))
        self.assertTrue(self.state.snapshot)
        self.assertFalse(self.frame(0.6, camera=(0.0, 3.0, 30.0), forward=(0.0, 0.0, 1.0)))
        self.assertTrue(self.frame(0.7))
        self.assertFalse(self.frame(0.8, dimension=-1))
        self.assertFalse(self.state.snapshot)

    def test_plane_visibility_when_source_is_high_above_camera(self):
        """
        验证源位置很高时输出平面仍可进入视野。
        """
        self.state.receive(snapshot(center=(0.0, 100.0, 0.0)), 1.0)
        self.assertTrue(self.frame(1.6))

    def test_stop_without_start_and_duplicate_stop(self):
        """
        验证未开始视觉场时停止和重复停止均安全。
        """
        self.state.clear()
        self.state.receive(snapshot(False), 1.0)
        self.assertFalse(self.state.snapshot)
        self.state.receive(snapshot(), 2.0)
        self.state.receive(snapshot(False), 3.0)
        self.state.receive(snapshot(False), 4.0)
        self.assertEqual(self.state.stopped, 3.0)

    def test_animation_phase_is_bounded_for_long_tasks(self):
        """
        验证长时间任务的动画相位保持有界。
        """
        self.state.receive(snapshot(), 100000.0)
        shape = self.frame(100001.0)[1]
        self.assertTrue(0.0 <= shape[2] < 24.0)


class ProtocolTests(unittest.TestCase):
    """
    验证视觉协议不会遍历方块列表或污染事件数据。
    """

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
                return (-5, 319, 7)

            def __iter__(self):
                raise AssertionError("block list must not be iterated")
        state = {
            'object': IndexOnly(),
            'move_cursor': 500000,
            'origin': [0, 60, 0],
            'phase': "complete",
        }
        event = build_field_event(0, state, 10)
        self.assertNotIn('object', event)
        payload = make_snapshot(make_event_args(event))
        self.assertEqual(payload['center'], [-4.5, 319.5, 7.5])
        self.assertEqual(payload['progress'], 1.0)
        self.assertFalse(payload['active'])
        self.assertLess(len(json.dumps(payload)), 180)

    def test_empty_target_has_no_visual_snapshot(self):
        """
        验证空目标不会产生视觉快照。
        """
        state = {'object': [], 'move_cursor': 0, 'origin': [0, 60, 0], 'phase': "complete"}
        event = build_field_event(0, state, 0)
        self.assertFalse(event['source'])
        self.assertFalse(make_snapshot(make_event_args(event)))

    def test_local_event_does_not_alias_mutable_world_data(self):
        """
        验证本地事件载荷隔离可变世界数据。
        """
        state = {'object': [[1, 2, 3]], 'move_cursor': 0, 'origin': [0, 60, 0], 'phase': "moving"}
        event = build_field_event(0, state, 5)
        state['object'][0][0] = 999
        state['origin'][1] = 100
        self.assertEqual(event['source'], (1, 2, 3))
        self.assertEqual(event['origin'], (0, 60, 0))
        before = dict(event)
        make_snapshot(make_event_args(event))
        self.assertEqual(event, before)


if __name__ == "__main__":
    unittest.main()


# endregion
