# -*- coding: utf-8 -*-
# =================================================
#  ⠀
#   Author: Nuoyan <https://github.com/charminglee>
#   Email : 1279735247@qq.com
#   Date  : 2026-10-21
#  ⠀
# =================================================


# region Event Routing Tests ==================================================


import os
import sys
import types
import unittest
from copy import deepcopy

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


for name in ("mod", "mod.server", "mod.client", "mod.common"):
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
    构造记录绑定来源的事件装饰器替身。
    """

    def decorate(function):
        """
        给回调附加可供测试总线识别的来源信息。
        """
        function._test_event = (ns or "nuoyan", sys_name or "engine", name or function.__name__)
        return function
    if callable(name):
        function, name = name, ""
        return decorate(function)
    return decorate


library.client.event = library.server.event = event
library.client.PLAYER_ID = "near"
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


# 引擎侧枚举的替身；实际注册字符串/顺序另由 validate.py 核对源文件。
constants = module("dualvectorfoil_scripts.common.constant")
constants.MOD_NAMESPACE = "nuoyan"
constants.SERVER_SYSTEM_NAME = "MainServerSystem"
constants.CLIENT_SYSTEM_NAME = "MainClientSystem"
constants.ServerEvent = type("ServerEvent", (), {'FoilFieldState': "FoilFieldState"})
constants.ServerModule = type("ServerModule", (), {
    'Effect': Member(("EffectServer", "dualvectorfoil_scripts.modules.effect.server")),
    'Foil': Member(("FoilServer", "dualvectorfoil_scripts.modules.foil.server")),
})


class Bus(object):
    """
    模拟 nuoyanlib 的本地广播和跨端通知总线。
    """

    def __init__(self):
        self.listeners = {}
        self.local = []
        self.network = []

    def register(self, system):
        """
        按事件来源注册系统回调。
        """
        for name in dir(system):
            callback = getattr(system, name)
            function = getattr(callback, "im_func", callback)
            source = getattr(function, "_test_event", None)
            if source:
                self.listeners.setdefault((system.side,) + source, []).append(callback)

    def deliver(self, side, source, payload):
        """
        向匹配来源的回调投递事件载荷。
        """
        for callback in self.listeners.get((side,) + source, []):
            callback(make_event_args(payload))

    def NotifyToMultiClients(self, system, players, name, payload):
        """
        记录跨端通知并投递给本地测试客户端。
        """
        source = (system.namespace, system.systemName, name)
        self.network.append((source, set(players), deepcopy(payload)))
        if "near" in players:
            self.deliver("client", source, payload)


class Base(object):
    """
    记录系统名称并模拟事件发送接口。
    """
    bus = None

    def __init__(self, namespace, system_name):
        self.namespace, self.systemName = namespace, system_name

    def BroadcastEvent(self, name, payload):
        """
        记录本地广播并立即投递给同侧订阅者。
        """
        source = (self.namespace, self.systemName, name)
        self.bus.local.append((source, deepcopy(payload)))
        self.bus.deliver(self.side, source, payload)

    def NotifyToMultiClients(self, players, name, payload):
        """
        记录跨端通知并投递给本地测试客户端。
        """
        source = (self.namespace, self.systemName, name)
        self.bus.network.append((source, set(players), deepcopy(payload)))
        if "near" in players:
            self.bus.deliver("client", source, payload)


class ServerBase(Base):
    """
    标记为服务端的测试系统基类。
    """
    side = "server"


class ClientBase(Base):
    """
    标记为客户端的测试系统基类。
    """
    side = "client"


module("dualvectorfoil_scripts.modules._base.server").BaseServer = ServerBase
module("dualvectorfoil_scripts.modules._base.client").BaseClient = ClientBase


class Player(object):
    """
    提供维度和位置接口的玩家替身。
    """
    Dimension = None
    Pos = None

    def __init__(self):
        self.Dimension = self.Pos = self

    def GetEntityDimensionId(self):
        """
        模拟 ModSDK GetEntityDimensionId 接口。
        """
        return 0

    def GetPos(self):
        """
        模拟 ModSDK GetPos 接口。
        """
        return (0, 3, 10)


library.server.CF = lambda player_id: Player()
server_api.GetPlayerList = lambda: ["near"]

from dualvectorfoil_scripts.modules.foil.server import FoilServer
from dualvectorfoil_scripts.modules.foil.config import ITEM
from dualvectorfoil_scripts.modules.effect import server as effect_server
from dualvectorfoil_scripts.modules.effect import client as effect_client
from dualvectorfoil_scripts.modules.effect.config import EVENT


class EventLevel(object):
    """
    提供空间跌落客户端所需的维度与摄像机接口。
    """

    def __init__(self):
        self.Game = self.Camera = self

    def GetCurrentDimension(self):
        """
        返回测试客户端所在维度。
        """
        return 0

    def GetPosition(self):
        """
        返回测试摄像机位置。
        """
        return (0.0, 3.0, 10.0)

    def GetForward(self):
        """
        返回测试摄像机朝向。
        """
        return (0.0, 0.0, -1.0)


class EventRouteTests(unittest.TestCase):
    """
    验证本地广播与跨端视觉事件路由。
    """

    def setUp(self):
        """
        初始化发射测试所需的组件替身和系统状态。
        """
        self.bus = Base.bus = Bus()
        self.foil = FoilServer.__new__(FoilServer)
        ServerBase.__init__(self.foil, "nuoyan", "FoilServer")
        self.foil.main_system = ServerBase("nuoyan", "MainServerSystem")
        self.foil.tick = 0
        self.state = {'origin': [0, 0, 0], 'object': [(0, 3, 0), (2, 3, 0)],
                      'move_cursor': 0, 'phase': "moving"}
        self.effects = effect_server.EffectServer("nuoyan", "EffectServer")
        self.effects.main_system = ServerBase("nuoyan", "MainServerSystem")
        self.effects.main_system.NotifyToMultiClients = (
            lambda players, name, payload: self.bus.NotifyToMultiClients(
                self.effects.main_system, players, name, payload))
        self.bus.register(self.effects.main_system)
        self.level = EventLevel()
        library.client.LvComp = self.level
        effect_client.nyl.LvComp = self.level
        effect_client.time = lambda: 0.0
        self.client = effect_client.EffectClient("nuoyan", "EffectClient")

    def publish(self, tick):
        """
        publish 对应的测试辅助逻辑。
        """
        self.foil.tick = tick
        self.foil._broadcast_field_state(0, self.state)

    def test_foil_publishes_locally_without_an_effect_subscriber(self):
        """
        验证没有 effect 订阅者时 foil 仍然发布本地事件。
        """
        self.publish(0)
        self.assertFalse(self.bus.network)
        source, payload = self.bus.local[-1]
        self.assertEqual(source, ("nuoyan", "MainServerSystem", "FoilFieldState"))
        self.assertNotIn('object', payload)
        self.assertNotIn('center', payload)
        self.assertEqual(payload['source'], (0, 3, 0))

    def test_actual_system_handlers_route_local_event_then_effect_network(self):
        """
        验证真实系统回调会先处理本地事件，再由 effect 发出跨端通知。
        """
        self.bus.register(self.effects)
        self.bus.register(self.client)
        for tick in range(10):
            self.publish(tick)
        self.assertEqual(len(self.bus.local), 10)
        self.assertEqual(len(self.bus.network), 1)
        self.assertEqual(self.bus.network[0][0], ("nuoyan", "MainServerSystem", EVENT))
        self.assertEqual(self.client.snapshot['center'], (0.5, 3.5, 0.5))
        self.state['move_cursor'] = 1
        self.publish(10)
        self.assertEqual(self.client.snapshot['progress'], 0.5)
        self.state['phase'] = "complete"
        self.publish(11)
        self.assertEqual(len(self.bus.network), 3)
        self.assertTrue(self.client.stopped)

    def test_effect_client_owns_tick_and_dimension_callbacks(self):
        """
        验证 effect 客户端独立注册 tick 和维度切换回调。
        """
        updates = []
        self.client._update = lambda: updates.append(True)
        self.client.OnScriptTickClient(make_event_args({}))
        self.assertEqual(updates, [True])
        self.client.snapshot = {'dimension': 0, 'run_id': 0}
        self.client.DimensionChangeClientEvent(
            make_event_args({'playerId': "other"}),
        )
        self.assertTrue(self.client.snapshot)
        self.client.DimensionChangeClientEvent(
            make_event_args({'playerId': "near"}),
        )
        self.assertFalse(self.client.snapshot)


class LaunchItem(object):
    """
    模拟玩家手持物品和堆叠数量。
    """

    def __init__(self):
        self.slot = 0
        self.count = 1

    def GetPlayerItem(self, pos_type):
        """
        模拟 ModSDK GetPlayerItem 接口。
        """
        return {'newItemName': ITEM, 'count': self.count}

    def GetSelectSlotId(self):
        """
        模拟 ModSDK GetSelectSlotId 接口。
        """
        return self.slot

    def SetInvItemNum(self, slot, count):
        """
        模拟 ModSDK SetInvItemNum 接口。
        """
        self.count = count
        return True


class LaunchProjectile(object):
    """
    记录创建的投射物参数。
    """

    def __init__(self, created):
        self.created = created
        self.params = []

    def CreateProjectileEntity(self, spawner_id, identifier, param):
        """
        模拟 ModSDK CreateProjectileEntity 接口。
        """
        entity_id = "shot-%d" % (len(self.created) + 1)
        self.created.append(entity_id)
        self.params.append(param)
        return entity_id


class LaunchGame(object):
    """
    模拟玩家游戏模式查询。
    """

    def GetPlayerGameType(self, player_id):
        """
        模拟 ModSDK GetPlayerGameType 接口。
        """
        return enums.GameType.Creative


class LaunchComponents(object):
    """
    组合发射测试需要的 ModSDK 组件替身。
    """

    def __init__(self, created):
        self.Projectile = LaunchProjectile(created)
        self.Game = LaunchGame()


class LaunchPlayer(object):
    """
    提供发射流程所需的玩家组件替身。
    """

    def __init__(self, dimension, messages):
        self.dimension = dimension
        self.messages = messages
        self.Dimension = self.Item = self.Pos = self.Rot = self.Msg = self
        self.item = LaunchItem()

    def GetEntityDimensionId(self):
        """
        模拟 ModSDK GetEntityDimensionId 接口。
        """
        return self.dimension

    def GetPlayerItem(self, pos_type):
        """
        模拟 ModSDK GetPlayerItem 接口。
        """
        return self.item.GetPlayerItem(pos_type)

    def GetSelectSlotId(self):
        """
        模拟 ModSDK GetSelectSlotId 接口。
        """
        return self.item.GetSelectSlotId()

    def SetInvItemNum(self, slot, count):
        """
        模拟 ModSDK SetInvItemNum 接口。
        """
        return self.item.SetInvItemNum(slot, count)

    def GetPos(self):
        """
        模拟 ModSDK GetPos 接口。
        """
        return (0.0, 3.0, 10.0)

    def GetRot(self):
        """
        模拟 ModSDK GetRot 接口。
        """
        return (0.0, 0.0, 0.0)

    def NotifyOneMessage(self, player_id, message):
        """
        模拟 ModSDK NotifyOneMessage 接口。
        """
        self.messages.append((player_id, message))


class LaunchGuardTests(unittest.TestCase):
    """
    验证每维度一个处理槽位，完成态不会永久阻止再次投掷。
    """

    def setUp(self):
        """
        初始化发射测试所需的组件替身和系统状态。
        """
        self.original_cf = library.server.CF
        self.original_components = library.server.LvComp
        self.original_bus = Base.bus
        self.had_get_dir = hasattr(server_api, "GetDirFromRot")
        self.original_get_dir = getattr(server_api, "GetDirFromRot", None)

        self.player_dimension = 0
        self.messages = []
        self.created = []
        library.server.CF = lambda player_id: LaunchPlayer(self.player_dimension, self.messages)
        library.server.LvComp = LaunchComponents(self.created)
        server_api.GetDirFromRot = lambda rot: (0.0, 0.0, 1.0)
        Base.bus = Bus()

        self.foil = FoilServer.__new__(FoilServer)
        ServerBase.__init__(self.foil, "nuoyan", "FoilServer")
        self.foil.main_system = ServerBase("nuoyan", "MainServerSystem")
        self.foil.fields = {}
        self.foil.projectiles = {}
        self.foil.cooldowns = {}
        self.foil.tick = 100
        self.foil._detach = lambda dimension: None
        self.foil._save = lambda: None
        self.state = {'run_id': "old-run", 'origin': [0, 0, 0],
                      'anchor': [0, 0, 0], 'object': [[0, 0, 0]],
                      'move_cursor': 0, 'moved': 0, 'phase': "moving",
                      'status': "moving", 'capped': False, 'playerId': "launcher"}

        def restore_get_dir():
            """
            恢复测试前的方向向量接口。
            """
            if self.had_get_dir:
                setattr(server_api, "GetDirFromRot", self.original_get_dir)
            else:
                delattr(server_api, "GetDirFromRot")

        self.addCleanup(setattr, library.server, "CF", self.original_cf)
        self.addCleanup(setattr, library.server, "LvComp", self.original_components)
        self.addCleanup(setattr, Base, "bus", self.original_bus)
        self.addCleanup(restore_get_dir)

    def launch(self, dimension):
        """
        在指定维度调用发射流程并返回是否创建投射物。
        """
        before = len(self.created)
        self.player_dimension = dimension
        self.foil._launch("launcher")
        return len(self.created) > before

    def test_active_field_blocks_same_dimension_until_completion(self):
        """
        验证未完成任务只阻塞同维度发射。
        """
        self.foil.fields['0'] = self.state
        self.assertFalse(self.launch(0))
        self.assertEqual(self.created, [])

        self.foil._finish_field(0, self.state, "complete", "二向箔二维化完成。")
        self.assertEqual(self.state['phase'], "complete")
        self.foil.tick += 1000
        self.assertTrue(self.launch(0))
        self.assertEqual(self.created, ["shot-1"])

    def test_inflight_projectile_blocks_only_its_dimension(self):
        """
        验证飞行中的投射物只阻塞其所在维度。
        """
        self.foil.projectiles['existing'] = {'dimension': 0}
        self.assertFalse(self.launch(0))
        self.assertTrue(self.launch(1))
        self.assertEqual(self.created, ["shot-1"])

    def test_launch_projectile_is_gravity_free_and_uses_aim_direction(self):
        """
        验证投射物无重力并沿玩家朝向发射。
        """
        self.assertTrue(self.launch(0))
        param = library.server.LvComp.Projectile.params[0]
        self.assertEqual(param['gravity'], 0.0)
        self.assertEqual(tuple(param['direction']), (0.0, 0.0, 1.0))

    def test_active_field_in_another_dimension_does_not_block(self):
        """
        验证其他维度的未完成任务不会阻塞当前发射。
        """
        self.foil.fields['1'] = self.state
        self.assertTrue(self.launch(0))
        self.assertEqual(self.created, ["shot-1"])


if __name__ == "__main__":
    unittest.main()


# endregion
