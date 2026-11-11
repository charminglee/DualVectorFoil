# -*- coding: utf-8 -*-
# =================================================
#  ⠀
#   Author: Nuoyan <https://github.com/charminglee>
#   Email : 1279735247@qq.com
#   Date  : 2026-10-26
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
enums.TimeEaseType = type("TimeEaseType", (), {'out_quad': "out_quad"})

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
constants.MOD_NAME = "DualVectorFoil"
constants.ItemId = type("ItemId", (), {'FOIL': "nuoyan:foil"})
constants.EntityId = type("EntityId", (), {'FOIL_PROJECTILE': "nuoyan:foil_projectile"})
constants.Attr = type("Attr", (), {'FLAT': "nuoyan:flat"})
constants.Data = type("Data", (), {'WORLD_V3': "nuoyan:world_v3"})
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
from dualvectorfoil_scripts.modules.foil.palette import plan_palette, empty_data, encode_index, world_position
from dualvectorfoil_scripts.modules.foil import server as foil_server
ITEM = "nuoyan:foil"
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
        self.state = make_plan([(0, 3, 0), (2, 3, 0)], (0, 0, 0))
        self.state.update({'origin': [0, 0, 0], 'phase': "moving"})
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
        self.assertEqual(self.client.playbacks[0].center, (0.5, 0.5, 0.5))
        self.state['move_cursor'] = 1
        self.state['moved'] = 1
        self.publish(10)
        self.assertEqual(len(self.bus.network), 1)
        self.state['phase'] = "complete"
        self.publish(11)
        self.assertEqual(len(self.bus.network), 1)
        self.assertTrue(self.client.playbacks[0].snapshot)

    def test_effect_client_owns_tick_and_dimension_callbacks(self):
        """
        验证 effect 客户端独立注册 tick 和维度切换回调。
        """
        updates = []
        self.client.playbacks = [type("Playback", (), {'_update': lambda unused: updates.append(True)})()]
        self.client.OnScriptTickClient(make_event_args({}))
        self.assertEqual(updates, [True])
        calls = []
        self.client.clear = lambda: calls.append(True)
        self.client.DimensionChangeClientEvent(
            make_event_args({'playerId': "other"}),
        )
        self.assertEqual(calls, [])
        self.client.DimensionChangeClientEvent(
            make_event_args({'playerId': "near"}),
        )
        self.assertEqual(calls, [True])


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


class LaunchEntity(object):
    """
    记录二向箔的位置、轨迹参数和运动器操作结果。
    """

    def __init__(self, pos):
        self.Pos = self.ActorMotion = self
        self.pos = pos
        self.motion_id = 0
        self.start_ok = self.stop_ok = self.position_ok = True
        self.track = None
        self.started = []
        self.velocities = []

    def GetPos(self):
        """
        返回二向箔当前所在的位置。
        """
        return self.pos

    def SetPos(self, pos):
        """
        模拟等待期间保持静止位置。
        """
        if self.position_ok:
            self.pos = tuple(pos)
        return self.position_ok

    def AddEntityTrackMotion(self, target, seconds, **kwargs):
        """
        记录轨迹终点、时长和缓动参数，允许模拟创建失败。
        """
        self.track = (target, seconds, kwargs)
        return self.motion_id

    def StartEntityMotion(self, motion_id):
        """
        记录启动请求，允许模拟启动失败。
        """
        self.started.append(motion_id)
        return self.start_ok

    def SetMotion(self, velocity):
        """
        记录轨迹完成后的残余速度清理。
        """
        self.velocities.append(velocity)
        return self.stop_ok


def make_plan(blocks, origin):
    start = tuple(min(p[i] for p in blocks) for i in range(3))
    end = tuple(max(p[i] for p in blocks) for i in range(3))
    world = LaunchWorld(blocks)
    return plan_palette(world.capture(start, end), start, origin, origin, 100, foil_server.flatten)


def plan_sources(state):
    return set(world_position(i, state['source_palette']['volume'], state['source_start']) for values in state['source_palette']['common'].values() for i in values)


class LaunchWorld(object):
    """
    为最终静止位置的调色板捕获提供方块表，不执行真实世界写入。
    """

    def __init__(self, blocks):
        self.blocks = set(blocks)
        self.status = "ready"

    def capture(self, start, end):
        volume = (end[2] - start[2] + 1, end[0] - start[0] + 1, end[1] - start[1] + 1)
        data = empty_data(volume)
        data['common'][('minecraft:stone', 0)] = [encode_index(tuple(p[i] - start[i] for i in range(3)), volume) for p in self.blocks]
        return data

    def capture_nbt(self, state):
        return {}


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
        self.had_get_enum = hasattr(server_api, "GetMinecraftEnum")
        self.original_get_enum = getattr(server_api, "GetMinecraftEnum", None)

        self.player_dimension = 0
        self.messages = []
        self.created = []
        self.destroyed = []
        self.shots = {}
        self.player = LaunchPlayer(0, self.messages)

        def components(entity_id):
            """
            区分玩家与投射物，并保留各实体的测试状态。
            """
            if entity_id not in self.created:
                self.player.dimension = self.player_dimension
                return self.player
            if entity_id not in self.shots:
                param = library.server.LvComp.Projectile.params[self.created.index(entity_id)]
                self.shots[entity_id] = LaunchEntity(tuple(param['position']))
            return self.shots[entity_id]

        library.server.CF = components
        library.server.LvComp = LaunchComponents(self.created)
        server_api.GetDirFromRot = lambda rot: (0.0, 0.0, 1.0)
        server_api.GetMinecraftEnum = lambda: enums
        Base.bus = Bus()

        self.foil = FoilServer.__new__(FoilServer)
        ServerBase.__init__(self.foil, "nuoyan", "FoilServer")
        self.foil.main_system = ServerBase("nuoyan", "MainServerSystem")
        self.foil.fields = {}
        self.foil.projectiles = {}
        self.foil.cooldowns = {}
        self.foil.tick = 100
        self.foil._detach = lambda dimension: None
        self.foil._save = lambda: True
        self.foil.DestroyEntity = self.destroyed.append
        self.state = make_plan([(0, 0, 0)], (0, 0, 0))
        self.state.update({'run_id': "old-run", 'origin': [0, 0, 0], 'anchor': [0, 0, 0],
                           'phase': "moving", 'status': "moving", 'playerId': "launcher"})

        def restore_get_dir():
            """
            恢复测试前的方向向量接口。
            """
            if self.had_get_dir:
                setattr(server_api, "GetDirFromRot", self.original_get_dir)
            else:
                delattr(server_api, "GetDirFromRot")

        def restore_get_enum():
            """
            恢复测试前的枚举查询接口。
            """
            if self.had_get_enum:
                setattr(server_api, "GetMinecraftEnum", self.original_get_enum)
            else:
                delattr(server_api, "GetMinecraftEnum")

        self.addCleanup(setattr, library.server, "CF", self.original_cf)
        self.addCleanup(setattr, library.server, "LvComp", self.original_components)
        self.addCleanup(setattr, Base, "bus", self.original_bus)
        self.addCleanup(restore_get_dir)
        self.addCleanup(restore_get_enum)

    def launch(self, dimension):
        """
        在指定维度调用发射流程并返回是否创建投射物。
        """
        before = len(self.created)
        self.player_dimension = dimension
        self.foil._launch("launcher")
        return len(self.created) > before

    def test_active_field_allows_same_dimension_launch(self):
        """
        验证同维度有未完成任务时仍可发射。
        """
        self.foil.fields['0'] = self.state
        self.assertTrue(self.launch(0))
        self.assertEqual(self.created, ["shot-1"])

        self.foil._finish_field(0, self.state, "complete", "二向箔二维化完成。")
        self.assertEqual(self.state['phase'], "complete")
        self.foil.tick += 1000
        self.assertTrue(self.launch(0))
        self.assertEqual(self.created, ["shot-1", "shot-2"])

    def test_inflight_projectile_allows_same_dimension_launch(self):
        """
        验证已有投射物不阻塞同维度发射，玩家冷却仍生效。
        """
        self.foil.projectiles['existing'] = {'dimension': 0}
        self.assertTrue(self.launch(0))
        self.assertFalse(self.launch(0))
        self.foil.tick += 1000
        self.assertTrue(self.launch(1))
        self.assertEqual(self.created, ["shot-1", "shot-2"])

    def test_different_players_can_launch_in_same_dimension_on_same_tick(self):
        """
        两名玩家可在同一 tick 向同维度发射，冷却各自独立。
        """
        self.assertTrue(self.launch(0))
        self.foil._launch("another-player")
        self.assertEqual(self.created, ["shot-1", "shot-2"])
        self.assertEqual([shot['dimension'] for shot in self.foil.projectiles.values()], [0, 0])

    def test_launch_projectile_is_gravity_free_and_uses_aim_direction(self):
        """
        验证投射物无重力并沿玩家朝向发射。
        """
        self.assertTrue(self.launch(0))
        param = library.server.LvComp.Projectile.params[0]
        self.assertEqual(param['gravity'], 0.0)
        self.assertEqual(tuple(param['direction']), (0.0, 0.0, 1.0))

    def test_custom_dimension_can_launch_without_height_configuration(self):
        """
        自定义维度无需配置高度即可创建投射物。
        """
        self.assertTrue(self.launch(42))
        self.assertEqual(self.foil.projectiles['shot-1']['dimension'], 42)

    def test_detonation_preserves_resting_height_without_clamping(self):
        """
        旧坐标边界内外和自定义维度均以静止格点建立输出平面。
        """
        self.foil.object_sets = {}
        self.foil._sync_object_set = lambda *args: None
        self.foil._attach = lambda dimension: None
        self.foil._process_field = lambda *args: None
        for dimension, height, coordinate in ((0, -64, 2), (0, 319, 2), (0, -1000, 2), (42, 1000, 2),
                                               (0, 5, 40000000), (0, 5, -40000000)):
            self.foil.fields = {}
            self.foil.projectiles['shot'] = {'dimension': dimension}
            self.foil._detonate('shot', (coordinate + 0.8, height + 0.7, coordinate - 0.2))
            state = self.foil.fields[str(dimension)]
            self.assertEqual(state['anchor'], [coordinate, height, coordinate - 1])
            self.assertEqual(state['origin'], [coordinate, height, coordinate - 1])

    def test_active_field_in_another_dimension_does_not_block(self):
        """
        验证其他维度的未完成任务不会阻塞当前发射。
        """
        self.foil.fields['1'] = self.state
        self.assertTrue(self.launch(0))
        self.assertEqual(self.created, ["shot-1"])

    def stop_flight(self, pos=None, motion_id=0):
        """
        模拟原生轨迹完成事件，并可指定实际停靠位置。
        """
        entity = self.shots['shot-1']
        entity.pos = pos if pos else entity.track[0]
        self.foil.EntityMotionStopServerEvent(
            make_event_args({'entityId': "shot-1", 'motionId': motion_id}),
        )

    def prepare_world(self, blocks):
        """
        使用真实展开与调色板映射逻辑，替换世界读写和存档接口。
        """
        self.foil.worlds = {0: LaunchWorld(blocks)}
        self.foil.target_sets = {}
        self.foil.object_sets = {}
        self.foil._attach = lambda dimension: None

    def test_configured_distance_duration_and_decelerating_native_track(self):
        """
        修改配置后，实际轨迹按三维朝向使用新距离、时长和减速曲线。
        """
        original_distance = foil_server.FOIL_FLIGHT_DISTANCE
        original_seconds = foil_server.FOIL_FLIGHT_SECONDS
        self.addCleanup(setattr, foil_server, "FOIL_FLIGHT_DISTANCE", original_distance)
        self.addCleanup(setattr, foil_server, "FOIL_FLIGHT_SECONDS", original_seconds)
        foil_server.FOIL_FLIGHT_DISTANCE = 25.0
        foil_server.FOIL_FLIGHT_SECONDS = 4.5
        server_api.GetDirFromRot = lambda rot: (0.6, 0.8, 0.0)

        self.assertTrue(self.launch(0))
        target, seconds, options = self.shots['shot-1'].track
        self.assertEqual(target, (15.9, 24.2, 10.0))
        self.assertEqual(seconds, 4.5)
        for actual, expected in zip(options['startPos'], (0.9, 4.2, 10.0)):
            self.assertAlmostEqual(actual, expected)
        self.assertEqual(options['ease'], "out_quad")
        self.assertEqual(self.shots['shot-1'].started, [0])
        self.assertEqual(library.server.LvComp.Projectile.params[0]['power'], 0.0)

    def test_collisions_are_cancelled_without_shortening_flight_or_wait(self):
        """
        方块和实体碰撞均不能触发展开，其他投射物不受影响。
        """
        self.launch(0)
        for target_type in ("BLOCK", "ENTITY"):
            args = make_event_args({'id': "shot-1", 'hitTargetType': target_type, 'cancel': False})
            self.foil.ProjectileDoHitEffectEvent(args)
            self.assertTrue(args.cancel)
            self.assertNotIn('deadline', self.foil.projectiles['shot-1'])
            self.assertEqual(self.foil.fields, {})
        args = make_event_args({'id': "unrelated", 'cancel': False})
        self.foil.ProjectileDoHitEffectEvent(args)
        self.assertFalse(args.cancel)
        self.assertEqual(self.destroyed, [])

    def test_six_second_countdown_starts_only_after_actual_motion_completion(self):
        """
        即使飞行超出预计时间，也须静止后再等足 180 tick 才能展开。
        """
        self.launch(0)
        self.foil.tick = 1000
        self.foil._update_projectiles()
        self.assertEqual(self.foil.fields, {})
        self.assertEqual(self.destroyed, [])
        self.assertNotIn('deadline', self.foil.projectiles['shot-1'])

        self.prepare_world([(0, 3, 23)])
        self.stop_flight()
        self.assertEqual(self.foil.projectiles['shot-1']['deadline'], 1180)
        self.assertEqual(self.shots['shot-1'].velocities, [(0.0, 0.0, 0.0)])
        self.assertTrue(self.launch(0))
        self.assertFalse(self.launch(1))
        self.foil.tick = 1179
        self.foil._update_projectiles()
        self.assertEqual(self.foil.fields, {})
        self.foil.tick = 1180
        self.foil._update_projectiles()
        self.assertEqual(self.foil.fields['0']['phase'], "moving")
        self.assertEqual(self.destroyed, ["shot-1"])

    def test_other_motion_and_duplicate_completion_do_not_restart_countdown(self):
        """
        不匹配的运动器和重复完成事件不会启动或延长等待。
        """
        self.launch(0)
        self.stop_flight(motion_id=99)
        self.assertNotIn('deadline', self.foil.projectiles['shot-1'])
        self.stop_flight()
        deadline = self.foil.projectiles['shot-1']['deadline']
        self.foil.tick += 20
        self.stop_flight()
        self.assertEqual(self.foil.projectiles['shot-1']['deadline'], deadline)

    def test_final_position_selects_sphere_and_floors_negative_coordinates(self):
        """
        选中球内孤立方块，负坐标球心向下取整。
        """
        self.launch(0)
        self.prepare_world([(-4, 4, 12), (-3, 4, 12), (0, 3, 15)])
        self.stop_flight(pos=(-3.2, 4.7, 12.8))
        self.foil.tick += 180
        self.foil._update_projectiles()
        state = self.foil.fields['0']
        self.assertEqual(state['anchor'], [-4, 4, 12])
        self.assertEqual(plan_sources(state), {(-4, 4, 12), (-3, 4, 12), (0, 3, 15)})

    def test_final_air_also_selects_blocks_in_sphere(self):
        """
        球心为空气时，仍然获取球内所有非空气方块。
        """
        self.launch(0)
        self.prepare_world([(0, 3, 15), (0, 2, 23)])
        self.stop_flight()
        self.foil.tick += 180
        self.foil._update_projectiles()
        state = self.foil.fields['0']
        self.assertEqual(state['status'], "moving")
        self.assertEqual(plan_sources(state), {(0, 3, 15), (0, 2, 23)})
        self.assertTrue(self.launch(0))

    def test_wait_keeps_actual_stop_position(self):
        """
        等待期间发生位置偏移时恢复静止点，再从原静止点展开。
        """
        self.launch(0)
        self.prepare_world([(0, 3, 23)])
        self.stop_flight()
        self.shots['shot-1'].pos = (4.0, 8.0, 20.0)
        self.foil.tick += 180
        self.foil._update_projectiles()
        self.assertEqual(self.shots['shot-1'].pos, (0.0, 3.0, 23.5))
        self.assertEqual(self.foil.fields['0']['anchor'], [0, 3, 23])

    def test_missing_entity_releases_slot_without_early_fall(self):
        """
        飞行或等待期间实体失效，均只释放槽位而不提前展开。
        """
        self.launch(0)
        self.shots['shot-1'].pos = None
        self.foil._update_projectiles()
        self.assertEqual(self.foil.projectiles, {})
        self.assertEqual(self.foil.fields, {})
        self.foil.tick += 1000
        self.assertTrue(self.launch(0))
        self.shots['shot-2'].pos = None
        self.foil.projectiles['shot-2']['deadline'] = self.foil.tick + 180
        self.foil._update_projectiles()
        self.assertEqual(self.foil.fields, {})
        self.assertEqual(self.foil.projectiles, {})

    def test_motion_creation_or_start_failure_does_not_consume_item(self):
        """
        轨迹创建或启动失败时清理实体，不扣除生存物品。
        """
        library.server.LvComp.Game.GetPlayerGameType = lambda player_id: 0
        failed_add = LaunchEntity((0, 3, 11.5))
        failed_add.motion_id = -1
        failed_start = LaunchEntity((0, 3, 11.5))
        failed_start.start_ok = False
        self.shots.update({'shot-1': failed_add, 'shot-2': failed_start})
        self.foil._launch("launcher")
        self.foil._launch("launcher")
        self.assertEqual(self.destroyed, ["shot-1", "shot-2"])
        self.assertEqual(self.foil.projectiles, {})
        self.assertEqual(self.player.item.count, 1)

    def test_invalid_flight_configuration_does_not_create_or_consume(self):
        """
        零距离和负时长配置不会创建实体或消耗物品。
        """
        for name, value in (("FOIL_FLIGHT_DISTANCE", 0.0), ("FOIL_FLIGHT_SECONDS", -1.0)):
            original = getattr(foil_server, name)
            setattr(foil_server, name, value)
            self.foil._launch("launcher")
            setattr(foil_server, name, original)
        self.assertEqual(self.created, [])
        self.assertEqual(self.player.item.count, 1)


if __name__ == "__main__":
    unittest.main()


# endregion
