# -*- coding: utf-8 -*-
# =================================================
#  ⠀
#   Author: Nuoyan <https://github.com/charminglee>
#   Email : 1279735247@qq.com
#   Date  : 2026-10-21
#  ⠀
# =================================================


# region Effect System Tests ==================================================


import os
import sys
import types
import unittest
from copy import deepcopy

from event_args import make_event_args
from effect_components import install
from nuoyanlib_exports import install_exports

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
install_exports(library.client)


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
constants.ServerEvent = type("ServerEvent", (), {'FoilFieldState': "FoilFieldState", 'FoilSpaceFallState': "FoilSpaceFallState"})
constants.ServerModule = type("ServerModule", (), {
    'Effect': Member(("EffectServer", "dualvectorfoil_scripts.modules.effect.server")),
})
module("dualvectorfoil_scripts.modules._base.client").BaseClient = TestBase
module("dualvectorfoil_scripts.modules._base.server").BaseServer = TestBase

from dualvectorfoil_scripts.modules.effect import playback as playback_module
from dualvectorfoil_scripts.modules.effect import client as client
from dualvectorfoil_scripts.modules.effect import server as sync
from dualvectorfoil_scripts.modules.effect.config import EFFECT, PLAY_SECONDS
from dualvectorfoil_scripts.common.constant import ServerEvent
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
        install(self)

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
    """独立通道、固定单轮、重复触发去重及关闭失败回归。"""
    def setUp(self):
        self.clock = 0.0
        client.time = playback_module.time = lambda: self.clock
        self.level = FakeLevel()
        client.nyl.LvComp = playback_module.nyl.LvComp = self.level
        self.created = []
        self.level.PostProcess.AddPostProcess = lambda definition: self.created.append(definition) or True
        self.effect = client.EffectClient("nuoyan", "EffectClient")
        self.payload = {'dimension': 0, 'active': True, 'center': (0.0, 3.0, 0.0),
                        'plane_y': 0.02, 'progress': 0.5, 'run_id': 'first'}

    def receive(self, **changes):
        self.effect.FoilSpaceFallState(make_event_args(dict(self.payload, **changes)))

    def tick(self, now):
        self.clock = now
        self.effect.OnScriptTickClient(make_event_args({}))

    def start(self):
        self.receive()
        self.tick(0.6)

    def test_fixed_duration_ignores_progress_completion_and_heartbeats(self):
        self.start()
        first = self.effect.playbacks[0]
        for now in (1.0, 2.0, 3.0, 4.0):
            self.clock = now
            self.receive(progress=1.0, center=(500, 3, 0))
            self.receive(active=False)
            self.tick(now)
        self.assertEqual(first.started, 0.0)
        self.assertEqual(first.center, (0.0, 3.0, 0.0))
        self.assertTrue(first.enabled)
        self.tick(PLAY_SECONDS)
        self.assertFalse(first.enabled)
        self.assertFalse(first.snapshot)
        self.clock = 20
        self.receive()
        self.assertFalse(first.snapshot)
        self.assertEqual(len(self.effect.playbacks), 1)

    def test_two_fields_have_independent_parameters_and_deadlines(self):
        self.start()
        self.clock = 1.0
        self.receive(run_id='second', center=(10, 3, 0))
        self.tick(1.6)
        first, second = self.effect.playbacks
        self.assertNotEqual(first.effect_name, second.effect_name)
        self.assertEqual([p.started for p in self.effect.playbacks], [0.0, 1.0])
        self.assertEqual(len(self.created), 1)
        self.assertEqual(self.created[0]['pass_array'][0]['material'], EFFECT)
        shape_calls = [call for call in self.level.PostProcess.calls if call[0] == 'parameter' and call[2] == 'shape']
        self.assertEqual(set(call[1] for call in shape_calls), {first.effect_name, second.effect_name})
        self.tick(PLAY_SECONDS)
        self.assertFalse(first.enabled)
        self.assertTrue(second.enabled)
        self.tick(PLAY_SECONDS + 1.0)
        self.assertFalse(second.enabled)

    def test_finished_channel_is_reused(self):
        self.start()
        self.tick(PLAY_SECONDS)
        self.clock = PLAY_SECONDS + 1.0
        self.receive(run_id='second')
        self.tick(PLAY_SECONDS + 1.6)
        self.assertEqual(len(self.effect.playbacks), 1)
        self.assertFalse(self.created)
        self.assertTrue(self.effect.playbacks[0].enabled)

    def test_silence_does_not_end_round_early(self):
        self.start()
        self.tick(3.0)
        self.assertTrue(self.effect.playbacks[0].enabled)
        self.tick(PLAY_SECONDS)
        self.assertFalse(self.effect.playbacks[0].enabled)

    def test_dimension_transition_clears_all_without_replay(self):
        self.start()
        self.level.dimension = -1
        self.tick(1.0)
        self.assertFalse(self.effect.playbacks[0].enabled)
        self.level.dimension = 0
        self.receive()
        self.assertFalse(self.effect.playbacks[0].snapshot)

    def test_parameter_failure_closes_its_channel(self):
        self.level.PostProcess.fail = 'shape'
        self.start()
        self.assertTrue(self.effect.playbacks[0].failed)
        self.assertFalse(self.effect.playbacks[0].enabled)

    def test_disable_failure_is_retried_without_busy_loop(self):
        self.start()
        self.level.PostProcess.fail = 'disable'
        self.effect.clear()
        count = len(self.level.PostProcess.calls)
        self.tick(0.6)
        self.assertEqual(len(self.level.PostProcess.calls), count)
        self.level.PostProcess.fail = None
        self.tick(1.7)
        self.assertFalse(self.effect.playbacks[0].enabled)

    def test_camera_unavailable_still_expires(self):
        self.start()
        self.level.Camera.GetPosition = lambda: None
        self.tick(PLAY_SECONDS)
        self.assertFalse(self.effect.playbacks[0].snapshot)
        self.assertFalse(self.effect.playbacks[0].enabled)

    def test_other_dimension_and_stop_only_do_not_start(self):
        self.receive(dimension=1)
        self.receive(active=False)
        self.assertFalse(self.effect.playbacks)

    def test_second_channel_failure_does_not_stop_first(self):
        self.start()
        post = self.level.PostProcess
        original = post.SetParameter
        post.SetParameter = lambda name, parameter, value: (
            False if name != EFFECT and parameter == 'shape' else original(name, parameter, value))
        self.clock = 1
        self.receive(run_id='second')
        self.tick(1.6)
        first, second = self.effect.playbacks
        self.assertTrue(first.enabled)
        self.assertFalse(first.failed)
        self.assertTrue(second.failed)
        self.assertFalse(second.enabled)

    def test_shader_wave_uses_single_round_time_instead_of_wrapping(self):
        path = os.path.join(ROOT, 'src', 'rp', 'shaders', 'dual_vector_foil', 'glsl', 'sky_rift_v14.fragment')
        source = open(path, 'rb').read()
        self.assertIn('float phase = clamp(EXTRA_VECTOR2.z / 5.0, 0.0, 1.0);', source)
        self.assertNotIn('fract(seconds / 3.0)', source)

    def test_collapse_shader_removes_all_old_circular_outlines(self):
        path = os.path.join(ROOT, 'src', 'rp', 'shaders', 'dual_vector_foil', 'glsl', 'sky_rift_v14.fragment')
        source = open(path, 'rb').read()
        for old_shape in ('float disc =', 'float rim =', 'float waveRadius =', 'float echo =', 'float planeRadius ='):
            self.assertNotIn(old_shape, source)
        self.assertIn('float collapseSheet(', source)
        self.assertIn('vec3 apocalypseSky(', source)
        self.assertIn('float collapse = smoothstep(0.22, 0.83, phase);', source)
        # Keep the existing sampling ceiling and near-camera/depth guards.
        self.assertEqual(source.count('texture2D('), 5)
        self.assertIn('if (depth < 0.8)', source)
        self.assertIn('sceneDepth - t', source)

    def test_add_channel_failure_does_not_stop_existing_round(self):
        self.start()
        self.level.PostProcess.AddPostProcess = lambda definition: False
        self.clock = 1
        self.receive(run_id='second')
        self.assertEqual(len(self.effect.playbacks), 1)
        self.assertEqual(self.effect.playbacks[0].started, 0.0)


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
        初始化附近玩家和 effect 服务端系统。
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

        self.main_system = MainSystem()
        self.server = sync.EffectServer("nuoyan", "EffectServer")
        self.server.main_system = self.main_system
        self.state = {'source_palette': {'volume': (1, 2, 1), 'common': {'test': [0, 1]}}, 'source_start': (0, 3, 0), 'groups': ['test'], 'group_index': 0, 'group_cursor': 0, 'block_count': 2, 'move_cursor': 0,
                      'origin': [0, 0, 0], 'phase': "moving"}

    def NotifyToMultiClients(self, players, event, payload):
        """
        记录测试系统发出的玩家列表和载荷。
        """
        self.calls.append((set(players), event, deepcopy(payload)))

    def send(self, tick):
        """
        以指定 tick 向 effect 服务端投递流程事件。
        """
        self.server.FoilFieldState(make_event_args(build_field_event(0, self.state, tick)))

    def test_nearby_filter_same_tick_dedup_and_late_join(self):
        """
        验证附近筛选、同 tick 去重和迟到玩家补发。
        """
        self.send(0)
        self.send(0)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.calls[0][:2], (set(["near"]), ServerEvent.FoilSpaceFallState))
        self.players['late'] = FakePlayer(0, (0, 3, 12))
        self.send(10)
        self.assertEqual(self.calls[-1][0], set(["late"]))

    def test_completion_and_repeat_updates_do_not_control_playback(self):
        self.send(0)
        self.state['move_cursor'] = 1
        self.send(10)
        self.state['phase'] = 'complete'
        self.send(11)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.calls[0][2]['progress'], 0.0)
        self.assertTrue(self.calls[0][2]['active'])

    def test_two_tasks_in_same_dimension_both_trigger(self):
        self.state['run_id'] = 'first'
        self.send(0)
        self.state['run_id'] = 'second'
        self.send(1)
        self.assertEqual([call[2]['run_id'] for call in self.calls], ['first', 'second'])

    def test_tick_rollback_does_not_replay_already_notified_viewers(self):
        self.send(100)
        self.send(1)
        self.assertEqual(len(self.calls), 1)



if __name__ == "__main__":
    unittest.main()


# endregion
