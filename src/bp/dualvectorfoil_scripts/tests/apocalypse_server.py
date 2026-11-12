# -*- coding: utf-8 -*-
# =================================================
#
#   Author: Nuoyan <https://github.com/charminglee>
#   Email : 1279735247@qq.com
#   Date  : 2026-11-13
#
# =================================================


"""仅供 MCDK 显式调用：视觉播放期间验证服务端回调、放块及临时实体，立即恢复。"""


from math import floor
from time import time
import mod.server.extraServerApi as api
from ..nuoyanlib import server as nyl
from ..common.constant import MOD_NAME


_probe = None


def mcdk_test_fx_server_start():
    """
    测试入口：五秒期间记录真实服务端 tick 进展，不触发二向箔搬移。
    """
    global _probe
    system = api.GetSystem(MOD_NAME, "FoilServer")
    _probe = {'started': time(), 'tick': system.tick}
    return {'case': "visual_server_ticks", 'ok': True, 'start': dict(_probe)}


def mcdk_test_fx_server_probe():
    """
    测试入口：只在空气位置临时放石块并恢复，临时生成一只猪后立即移除。
    """
    system = api.GetSystem(MOD_NAME, "FoilServer")
    player = api.GetPlayerList()[0]
    cf = nyl.CF(player)
    pos = cf.Pos.GetPos()
    dimension = cf.Dimension.GetEntityDimensionId()
    target = (int(floor(pos[0])) + 4, int(floor(pos[1])) + 3, int(floor(pos[2])))
    info = nyl.LvComp.BlockInfo
    original = info.GetBlockNew(target, dimension)
    if not original or original['name'] != "minecraft:air":
        return {'case': "visual_server_interaction", 'ok': False, 'stage': "probe_position_not_air"}
    started = time()
    placed = info.SetBlockNew(target, {'name': "minecraft:stone", 'aux': 0}, 0, dimension, False, False)
    actual = info.GetBlockNew(target, dimension)
    restored = info.SetBlockNew(target, original, 0, dimension, False, False)
    after = info.GetBlockNew(target, dimension)
    entity = system.CreateEngineEntityByTypeStr("minecraft:pig", (target[0] + 0.5, target[1] + 1.0, target[2] + 0.5), (0.0, 0.0), dimension)
    removed = system.DestroyEntity(entity) if entity else False
    return {'case': "visual_server_interaction", 'ok': bool(placed and restored and actual['name'] == "minecraft:stone" and after['name'] == "minecraft:air" and entity and removed),
            'block_restored': after, 'entity_created': bool(entity), 'entity_removed': bool(removed),
            'duration_ms': round((time() - started) * 1000, 3), 'tick': system.tick,
            'tick_delta': system.tick - _probe['tick'] if _probe else None,
            'elapsed': time() - _probe['started'] if _probe else None}


def mcdk_test_broadcast_visual(distance=85.0):
    """
    测试入口：只广播公开流程事件，验证正式服务端到客户端视觉链路。
    """
    from uuid import uuid4
    from ..common.constant import ServerEvent
    player = api.GetPlayerList()[0]
    cf = nyl.CF(player)
    pos = cf.Pos.GetPos()
    direction = api.GetDirFromRot(cf.Rot.GetRot())
    length = max(0.001, (direction[0] ** 2 + direction[2] ** 2) ** 0.5)
    origin = (int(pos[0] + direction[0] / length * distance), int(pos[1] - 2), int(pos[2] + direction[2] / length * distance))
    system = api.GetSystem(MOD_NAME, "FoilServer")
    run_id = "mcdk_e2e_" + uuid4().hex
    event = {'dimension': cf.Dimension.GetEntityDimensionId(), 'run_id': run_id, 'phase': "moving", 'tick': system.tick,
             'origin': origin, 'source': origin, 'block_count': 1, 'processed_count': 0}
    system.main_system.BroadcastEvent(ServerEvent.FoilFieldState, event)
    return {'case': "visual_event_route", 'ok': True, 'run_id': run_id, 'origin': origin}
