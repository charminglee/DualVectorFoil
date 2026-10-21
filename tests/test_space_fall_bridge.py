# -*- coding: utf-8 -*-
# =================================================
#  ⠀
#   Author: Nuoyan <https://github.com/charminglee>
#   Email : 1279735247@qq.com
#   Date  : 2026-10-21
#  ⠀
# =================================================


# region Renderer Bridge Tests ==================================================


import os
import sys
import types
import unittest
from copy import deepcopy

from event_args import make_event_args

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src", "bp"))

# 单独运行本测试进程，替身不会修改磁盘上的库或 SDK。
# 单独运行本测试进程，替身不会修改磁盘上的库或 SDK。


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
library.client.LvComp = object()
library.client.PLAYER_ID = "near"


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

from dualvectorfoil_scripts.modules.effect import client as client
from dualvectorfoil_scripts.modules.effect import server as sync
from dualvectorfoil_scripts.modules.effect.config import EFFECT, EVENT
from dualvectorfoil_scripts.modules.foil.server import build_field_event


class FakePost(object):
    """
    记录后处理开关和参数调用。
    """

    def __init__(self):
        self.calls = []
        self.fail = None

    def SetEnableByName(self, name, value):
        """
        记录并模拟后处理通道开关结果。
        """
        self.calls.append(("enable", name, value))
        return self.fail != ("enable" if value else "disable")

    def SetParameter(self, effect, name, value):
        """
        记录并模拟后处理参数设置结果。
        """
        self.calls.append(("parameter", effect, name, value))
        return self.fail != name


class FakeLevel(object):
    """
    提供客户端摄像机、维度和后处理接口替身。
    """

    def __init__(self):
        self.Game = self.Camera = self
        self.PostProcess = FakePost()
        self.dimension = 0
        self.position = (0.0, 3.0, 10.0)

    def GetCurrentDimension(self):
        """
        返回测试客户端的当前维度。
        """
        return self.dimension

    def GetPosition(self):
        """
        返回测试摄像机位置。
        """
        return self.position

    def GetForward(self):
        """
        返回测试摄像机朝向。
        """
        return (0.0, 0.0, -1.0)


class BridgeTests(unittest.TestCase):
    """
    验证后处理桥的启用、更新、失败和清理。
    """

    def setUp(self):
        """
        初始化客户端时间、摄像机和渲染器替身。
        """
        self.clock = 0.0
        client.time = lambda: self.clock
        self.level = FakeLevel()
        library.client.LvComp = self.level
        client.nyl.LvComp = self.level
        self.renderer = client.SpaceFallRenderer()
        self.payload = {'dimension': 0, 'active': True, 'center': (0.0, 3.0, 0.0),
                        'plane_y': 0.02, 'progress': 0.5, 'run_id': 0}

    def start(self):
        """
        启动一次可见的空间跌落效果。
        """
        self.renderer.receive(make_event_args(self.payload))
        self.clock = 0.6
        self.renderer.update()

    def test_enable_once_parameter_updates_and_cleanup(self):
        """
        验证通道只启用一次、参数持续更新并可清理。
        """
        self.start()
        self.renderer.update()
        calls = self.level.PostProcess.calls
        self.assertEqual(calls.count(("enable", EFFECT, True)), 1)
        parameters = [item for item in calls if item[0] == "parameter"]
        self.assertEqual(
            [item[2] for item in parameters],
            ["style", "field", "shape", "field", "shape"],
        )
        self.renderer.clear()
        self.assertFalse(self.renderer.enabled)
        self.assertEqual(calls[-1], ("enable", EFFECT, False))
        before = len(calls)
        self.renderer.update()
        self.assertEqual(len(calls), before)

    def test_dimension_transition_disables_immediately(self):
        """
        验证维度切换后立即关闭后处理。
        """
        self.start()
        self.level.dimension = -1
        self.renderer.update()
        self.assertFalse(self.renderer.enabled)
        self.assertIsNone(self.renderer.state.snapshot)

    def test_complete_and_missing_heartbeat_disable(self):
        """
        验证完成消息或心跳缺失都会关闭效果。
        """
        for complete in (True, False):
            self.setUp()
            self.start()
            if complete:
                self.clock = 1.0
                self.renderer.receive(
                    make_event_args(dict(self.payload, active=False)),
                )
            self.clock = 4.0
            self.renderer.update()
            self.assertFalse(self.renderer.enabled)
            self.assertIsNone(self.renderer.state.snapshot)

    def test_parameter_failure_closes_effect(self):
        """
        验证任一参数失败都会关闭效果。
        """
        self.level.PostProcess.fail = "shape"
        self.start()
        self.assertTrue(self.renderer.failed)
        self.assertFalse(self.renderer.enabled)
        self.assertEqual(self.level.PostProcess.calls[-1], ("enable", EFFECT, False))

    def test_disable_failure_is_retried_without_busy_loop(self):
        """
        验证关闭失败会限频重试而不会忙循环。
        """
        self.start()
        self.level.PostProcess.fail = "disable"
        self.renderer.clear()
        count = len(self.level.PostProcess.calls)
        self.renderer.update()
        self.assertEqual(len(self.level.PostProcess.calls), count)
        self.level.PostProcess.fail = None
        self.clock += 1.1
        self.renderer.update()
        self.assertFalse(self.renderer.enabled)

    def test_disabled_quality_has_no_postprocess_calls(self):
        """
        验证画质关闭时不会调用后处理接口。
        """
        previous = client.QUALITY
        client.QUALITY = 0
        self.addCleanup(setattr, client, "QUALITY", previous)
        self.start()
        self.assertFalse(self.level.PostProcess.calls)

    def test_other_dimension_event_is_ignored(self):
        """
        验证其他维度的视觉事件会被忽略。
        """
        self.renderer.receive(
            make_event_args(dict(self.payload, dimension=1)),
        )
        self.renderer.update()
        self.assertIsNone(self.renderer.state.snapshot)
        self.assertFalse(self.level.PostProcess.calls)


class FakeDimension(object):
    """
    提供维度编号查询替身。
    """

    def __init__(self, value):
        self.value = value

    def GetEntityDimensionId(self):
        """
        返回测试实体的维度编号。
        """
        return self.value


class FakePos(object):
    """
    提供实体位置查询替身。
    """

    def __init__(self, value):
        self.value = value

    def GetPos(self):
        """
        返回测试实体位置。
        """
        return self.value


class FakePlayer(object):
    """
    按玩家编号返回维度和位置组件替身。
    """

    def __init__(self, dimension, position):
        self.Dimension = FakeDimension(dimension)
        self.Pos = FakePos(position)


class FakeCF(object):
    """
    包装单个测试玩家并提供位置和维度组件。
    """

    def __init__(self, player):
        self._player = player
        self.Dimension = player.Dimension
        self.Pos = player.Pos


class SyncTests(unittest.TestCase):
    """
    验证附近玩家筛选、限频和完成通知。
    """

    def setUp(self):
        """
        初始化客户端时间、摄像机和渲染器替身。
        """
        self.players = {'near': FakePlayer(0, (0, 3, 10)), 'far': FakePlayer(0, (1000, 3, 10)),
                        'other': FakePlayer(1, (0, 3, 10))}
        library.server.CF = lambda player_id: FakeCF(self.players[player_id])
        sync.nyl.CF = library.server.CF
        sync.server_api.GetPlayerList = lambda: list(self.players)
        self.calls = []
        outer = self

        class MainSystem(object):
            """
            记录主服务端系统的跨端通知。
            """

            def NotifyToMultiClients(self, players, event, payload):
                """
                记录测试系统发出的玩家列表和载荷。
                """
                outer.NotifyToMultiClients(players, event, payload)

        class EffectSystem(object):
            """
            提供 effect 服务端测试入口所需的系统引用。
            """
            main_system = MainSystem()
        self.main_system = EffectSystem()
        self.sender = sync.SpaceFallSync(self.main_system)
        self.state = {'object': [(0, 3, 0), (1, 3, 0)], 'move_cursor': 0,
                      'origin': [0, 0, 0], 'phase': "moving"}

    def NotifyToMultiClients(self, players, event, payload):
        """
        记录测试系统发出的玩家列表和载荷。
        """
        self.calls.append((set(players), event, deepcopy(payload)))

    def send(self, tick):
        """
        以指定 tick 向同步器投递流程事件。
        """
        self.sender.send(make_event_args(build_field_event(0, self.state, tick)))

    def test_nearby_filter_same_tick_dedup_and_late_join(self):
        """
        验证附近筛选、同 tick 去重和迟到玩家补发。
        """
        self.send(0)
        self.send(0)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.calls[0][:2], (set(["near"]), EVENT))
        self.players['late'] = FakePlayer(0, (0, 3, 12))
        self.send(10)
        self.assertEqual(self.calls[-1][0], set(["near", "late"]))

    def test_departure_and_finish_notify_previous_viewers(self):
        """
        验证离开范围或任务完成时通知上一批观看者。
        """
        self.send(0)
        self.players['near'].Dimension.value = 1
        self.send(10)
        self.assertFalse(self.calls[-1][2]['active'])
        self.players['near'].Dimension.value = 0
        self.send(20)
        self.state['phase'] = "complete"
        self.state['move_cursor'] = 2
        self.send(21)
        self.assertEqual(self.calls[-1][0], set(["near"]))
        self.assertFalse(self.calls[-1][2]['active'])
        self.assertFalse(self.sender.viewers[0])

    def test_effect_module_throttles_tick_events_but_not_completion(self):
        """
        验证 effect 模块限频移动事件但立即发送完成事件。
        """
        for tick in range(10):
            self.send(tick)
        self.assertEqual(len(self.calls), 1)
        self.state['move_cursor'] = 1
        self.send(10)
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(self.calls[-1][2]['progress'], 0.5)
        self.state['phase'] = "complete"
        self.send(11)
        self.assertEqual(len(self.calls), 3)
        self.assertFalse(self.calls[-1][2]['active'])

    def test_reloaded_foil_tick_counter_can_restart_notification(self):
        """
        验证 foil 重新加载导致 tick 回退时仍可恢复通知。
        """
        self.send(100)
        self.send(1)
        self.assertEqual(len(self.calls), 2)


if __name__ == "__main__":
    unittest.main()


# endregion
