# -*- coding: utf-8 -*-
"""MCDK 显式测试入口：采样正式资源动画创建的发射器；不额外创建粒子。"""
from time import time
import mod.client.extraClientApi as api


_samples = []


def mcdk_test_rays_sample(entity, reset=False, expected_active=True):
    """
    在有界句柄范围查找绑定到测试实体的发射器；跨循环检查存活和位置。
    当前客户端的内部数量统计接口抛出 SystemError，因此不使用它们。
    """
    if reset:
        _samples[:] = []
    comp = api.GetEngineCompFactory().CreateParticleSystem(api.GetLevelId())
    emitters = []
    for handle in range(1, 1025):
        if comp.Exist(handle) and comp.GetBindingID(handle) == entity:
            emitters.append({'id': handle, 'pos': comp.GetPos(handle, False),
                             'mode': comp.GetFacingMode(handle),
                             'age': comp.GetVariable(handle, "variable.emitter_age")})
    sample = {'time': time(), 'emitters': emitters, 'scan_limit': 1024}
    _samples.append(sample)
    # 句柄探测只用于存活与绑定检查，不能代替引擎的精确实例/粒子计数。
    active = bool(emitters)
    valid_mode = all(item['mode'] == "direction_y" for item in emitters)
    return {'case': 'projectile_rays_live', 'ok': active == expected_active and valid_mode,
            'sample': sample, 'samples': list(_samples)}


def mcdk_test_rays_view(restore=False):
    """
    固定测试摄像机，在玩家上方观察实体发光与遮挡；结束解锁恢复引擎控制。
    """
    factory = api.GetEngineCompFactory()
    camera = factory.CreateCamera(api.GetLevelId())
    if restore:
        return {'ok': camera.UnLockCamera()}
    pos = factory.CreatePos(api.GetLocalPlayerId()).GetPos()
    eye = (pos[0], pos[1] + 3.0, pos[2] - 2.0)
    return {'ok': camera.LockCamera(eye, (0.0, 0.0, 0.0)),
            'target': (pos[0], pos[1] + 3.0, pos[2] + 6.0)}
