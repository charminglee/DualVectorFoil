# -*- coding: utf-8 -*-
"""MCDK 显式测试入口：只创建未接入地形搬移任务的抛射物，超时自动清理。"""
import mod.server.extraServerApi as api
from ..common.constant import MOD_NAME


_entities = []


def mcdk_test_rays_start(pos=None, dimension=None):
    """
    创建静止的正式抛射物实体；45 秒兜底销毁，不注册二向箔爆发任务。
    """
    mcdk_test_rays_stop()
    factory = api.GetEngineCompFactory()
    player = api.GetPlayerList()[0]
    if pos is None:
        base = factory.CreatePos(player).GetPos()
        pos = (base[0], base[1] + 3.0, base[2] + 6.0)
    if dimension is None:
        dimension = factory.CreateDimension(player).GetEntityDimensionId()
    system = api.GetSystem(MOD_NAME, "FoilServer")
    entity = system.CreateEngineEntityByTypeStr("nuoyan:foil_projectile", tuple(pos), (0.0, 0.0), dimension)
    if entity:
        _entities.append(entity)
        factory.CreateGame(api.GetLevelId()).AddTimer(45.0, system.DestroyEntity, entity)
    return {'case': 'projectile_rays_spawn', 'ok': bool(entity), 'entity': entity, 'pos': pos}


def mcdk_test_rays_move():
    """
    使用引擎轨迹运动平移四格，观察发射源跟随与停下后的持续发射。
    """
    if not _entities:
        return {'ok': False, 'stage': 'no_entity'}
    factory = api.GetEngineCompFactory()
    entity = _entities[0]
    pos = factory.CreatePos(entity).GetPos()
    target = (pos[0] + 4.0, pos[1], pos[2])
    motion = factory.CreateActorMotion(entity)
    track = motion.AddEntityTrackMotion(target, 3.0, startPos=pos)
    started = motion.StartEntityMotion(track)
    return {'case': 'projectile_rays_move', 'ok': bool(started), 'target': target}


def mcdk_test_rays_stop():
    """
    显式清理本测试创建的实体，不操作玩家和已有二向箔任务。
    """
    system = api.GetSystem(MOD_NAME, "FoilServer")
    results = [system.DestroyEntity(entity) for entity in _entities]
    _entities[:] = []
    return {'case': 'projectile_rays_cleanup', 'removed': results, 'ok': all(results)}
