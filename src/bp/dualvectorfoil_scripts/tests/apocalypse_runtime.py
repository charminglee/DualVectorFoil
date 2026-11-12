# -*- coding: utf-8 -*-
# =================================================
#
#   Author: Nuoyan <https://github.com/charminglee>
#   Email : 1279735247@qq.com
#   Date  : 2026-11-13
#
# =================================================


"""仅供 MCDK 显式调用的末日视觉测试；不搬动方块，不创建真实游戏实体。"""


from math import sqrt
from time import time
from uuid import uuid4
import mod.client.extraClientApi as api
from ..nuoyanlib import client as nyl
from ..common.constant import MOD_NAME


_records = []
_baseline = None


def mcdk_test_fx_start(distance=65.0, hold_phase=None, count=1):
    """
    测试入口：前方生成纯视觉演出；hold_phase 只供截图冻结，不改变正式逻辑。
    """
    global _baseline
    system = api.GetSystem(MOD_NAME, "EffectClient")
    system.clear()
    for playback in system.playbacks:
        playback.clock = time
    sky = nyl.LvComp.SkyRender
    _baseline = (sky.GetSkyColor(), sky.GetAmbientBrightness(), sky.GetUseSkyColor(), sky.GetUseAmbientBrightness())
    camera, forward = nyl.LvComp.Camera.GetPosition(), nyl.LvComp.Camera.GetForward()
    if not camera or not forward:
        return {'case': 'apocalypse_visual', 'ok': False, 'stage': 'camera_not_ready'}
    length = max(0.001, sqrt(forward[0] ** 2 + forward[2] ** 2))
    center = (camera[0] + forward[0] / length * distance, camera[1] - 2.0, camera[2] + forward[2] / length * distance)
    dimension = nyl.LvComp.Game.GetCurrentDimension()
    _records[:] = []
    for index in range(count):
        class Args(object):
            pass
        args = Args()
        args.active, args.dimension, args.run_id = True, dimension, "mcdk_fx_" + uuid4().hex
        args.center = (center[0] + index * 35.0, center[1], center[2])
        args.plane_y, args.progress = center[1] + 1.02, 0.0
        system.FoilSpaceFallState(args)
    if hold_phase is not None:
        for playback in system.playbacks:
            if playback.snapshot:
                held = playback.started + float(hold_phase) * 5.0
                playback.clock = lambda value=held: value
                for particle_id in playback.particles.ids:
                    nyl.LvComp.Game.AddTimer(2.0, nyl.LvComp.ParticleSystem.Pause, particle_id)
    else:
        for delay in (0.15, 0.9, 2.0, 3.5, 5.3):
            nyl.LvComp.Game.AddTimer(delay, _record)
    system.OnScriptTickClient(None)
    return mcdk_test_fx_report()


def _record():
    """
    测试计时器：记录正式 tick 推进后的状态，不干预播放。
    """
    _records.append(mcdk_test_fx_report(include_records=False))


def mcdk_test_fx_report(include_records=True):
    """
    测试入口：返回真实通道、粒子存在状态、天空和清理结果。
    """
    system = api.GetSystem(MOD_NAME, "EffectClient")
    rows = []
    for p in system.playbacks:
        rows.append({'name': p.effect_name, 'active': bool(p.snapshot), 'failed': p.failed,
                     'enabled': nyl.LvComp.PostProcess.CheckEnabledByName(p.effect_name),
                     'particles': len(p.particles.ids),
                     'particles_alive': sum(bool(nyl.LvComp.ParticleSystem.Exist(i)) for i in p.particles.ids),
                     'owner': p.environment_owner, 'run_id': p.snapshot['run_id'] if p.snapshot else None,
                     'age': round(p.clock() - p.started, 3) if p.snapshot else None})
    sky = nyl.LvComp.SkyRender
    result = {'case': "apocalypse_visual", 'ok': not any(p.failed for p in system.playbacks),
              'channels': rows, 'sky': sky.GetSkyColor(), 'ambient': sky.GetAmbientBrightness(),
              'sky_override': sky.GetUseSkyColor(), 'ambient_override': sky.GetUseAmbientBrightness(),
              'baseline': _baseline, 'fps': nyl.LvComp.Game.GetFps(), 'time': time()}
    if include_records:
        result['records'] = list(_records)
    return result


def mcdk_test_fx_stop():
    """
    测试入口：解除截图时钟并恢复所有测试视觉状态。
    """
    system = api.GetSystem(MOD_NAME, "EffectClient")
    system.clear()
    for playback in system.playbacks:
        playback.clock = time
    return mcdk_test_fx_report()


def mcdk_test_fx_overlap():
    """
    测试入口：两轮错开 1.2 秒触发，检查首轮退出后环境控制权接续。
    """
    result = mcdk_test_fx_start(85.0)
    system = api.GetSystem(MOD_NAME, "EffectClient")
    center = next(p.center for p in system.playbacks if p.snapshot)
    dimension = nyl.LvComp.Game.GetCurrentDimension()

    def followup():
        """
        测试计时器：通过正式事件入口触发第二轮，不清理第一轮。
        """
        class Args(object):
            pass
        args = Args()
        args.active, args.dimension, args.run_id = True, dimension, "mcdk_fx_" + uuid4().hex
        args.center, args.plane_y, args.progress = (center[0] + 35.0, center[1], center[2]), center[1] + 1.02, 0.0
        system.FoilSpaceFallState(args)
    nyl.LvComp.Game.AddTimer(1.2, followup)
    nyl.LvComp.Game.AddTimer(6.5, _record)
    return result


_repeat_reports = []


def mcdk_test_fx_repeat(rounds=3):
    """
    测试入口：连续单轮实播，分别核对五秒后的通道、粒子与环境恢复。
    """
    _repeat_reports[:] = []

    def begin():
        """
        测试计时器：触发独立一轮实际播放。
        """
        mcdk_test_fx_start(85.0)

    def finish():
        """
        测试计时器：收集完整退场后的真实状态。
        """
        report = mcdk_test_fx_report(False)
        report['cleaned'] = not any(row['active'] or row['enabled'] or row['particles'] for row in report['channels'])
        report['restored'] = not report['sky_override'] and not report['ambient_override'] and abs(report['ambient'] - 1.0) < 0.001
        _repeat_reports.append(report)
    for index in range(rounds):
        if index == 0:
            begin()
        else:
            nyl.LvComp.Game.AddTimer(index * 5.8, begin)
        nyl.LvComp.Game.AddTimer(index * 5.8 + 5.4, finish)
    return {'case': "apocalypse_repeated_live", 'ok': True, 'scheduled': rounds}


def mcdk_test_fx_repeat_report():
    """
    测试入口：返回已完成轮次及清理通过数。
    """
    return {'case': "apocalypse_repeated_live", 'completed': len(_repeat_reports),
            'passed': sum(bool(r['ok'] and r['cleaned'] and r['restored']) for r in _repeat_reports),
            'rounds': list(_repeat_reports)}
