# -*- coding: utf-8 -*-
# =================================================
#  ⠀
#   Author: Nuoyan <https://github.com/charminglee>
#   Email : 1279735247@qq.com
#   Date  : 2026-11-13
#  ⠀
# =================================================


from time import time
from ...nuoyanlib import client as nyl
from ...common.diagnostics import get_log
from .config import *
from .particles import CatastropheParticles


def smooth_unit(value):
    """
    把数值限幅到 0 至 1，并用三次 smoothstep 生成平滑权重。

    f(t) = 3t² - 2t³ 在两端取值为 0、1，且端点导数都为零，
    用于淡入、淡出和距离衰减时，可避免线性权重启停处的突变。
    """
    value = min(1.0, max(0.0, value))
    return value * value * (3.0 - 2.0 * value)


class FieldPlayback(object):
    """
    维护视觉快照的生命周期，并把世界空间参数传给后处理。

    每个实例独占一个后处理通道，在固定中心播放五秒后关闭。
    多个实例的时间和参数独立，已结束通道由管理器复用。
    """

    def __init__(self, effect_name):
        self.effect_name = effect_name
        self.snapshot = None
        self.center = None
        self.started = 0.0
        self.enabled = False
        self.failed = False
        self.disable_retry = 0.0
        self.clock = time
        self.particles = CatastropheParticles()
        self.environment_owner = True

    def start(self, args, now):
        """
        固定本轮中心和开始时间；后续进度与完成消息不参与播放。
        """
        self.snapshot = {
            'dimension': args.dimension,
            'run_id': args.run_id,
            'plane_y': args.plane_y,
        }
        self.center = tuple(args.center)
        self.clock = time
        self.started = now
        self.particles.start(self.center)

    def _frame(self, now, dimension, camera, forward):
        """
        根据当前时间、维度和摄像机生成后处理参数。
        """
        # 没有快照时无需计算。
        if not self.snapshot:
            return None

        # 维度切换后立即释放旧视觉效果。
        if dimension != self.snapshot['dimension']:
            self.clear()
            return None

        # 墙钟计时只走一轮；不依赖服务端心跳、搬移进度或完成消息。
        age = max(0.0, now - self.started)
        if age >= PLAY_SECONDS:
            self.clear()
            return None

        # 源中心与输出平面中心可能高度相差很大；取较近距离、较前点积，
        # 让两端任意一处可见时都保留效果，避免只看见落点时被源位置误剔除。
        distance = nyl.distance(self.center, camera)
        plane_center = (self.center[0], self.snapshot['plane_y'], self.center[2])
        plane_distance = nyl.distance(plane_center, camera)
        distance = min(distance, plane_distance)
        source_dot = sum((self.center[i] - camera[i]) * forward[i] for i in range(3))
        plane_dot = sum((plane_center[i] - camera[i]) * forward[i] for i in range(3))

        # 超出观看距离或完全位于摄像机背后时不启用后处理。
        if distance >= VIEW_DISTANCE:
            return None

        # 强度为配置值、淡入、淡出和距离权重的乘积，任一项为零即不可见。
        # 距离权重在观看半径前 70% 保持为 1，仅在最外侧 30% 平滑衰减。
        attack = smooth_unit(age / FADE_IN)
        release = 1.0 - smooth_unit((age - (PLAY_SECONDS - FADE_OUT)) / FADE_OUT)
        far_fade = 1.0 - smooth_unit((distance / VIEW_DISTANCE - 0.7) / 0.3)
        strength = STRENGTH * attack * release * far_fade
        if strength < 0.001:
            return None

        # field=(中心 xyz, 半径)，shape=(输出平面 y, 强度, 本轮秒数, 本轮时间进度)。
        radius = RADIUS * (0.3 + 0.7 * attack)
        return (
            self.center + (radius,),
            (
                self.snapshot['plane_y'],
                strength,
                age,
                min(1.0, age / PLAY_SECONDS),
            ),
        )

    def _update(self):
        """
        按当前视觉状态刷新后处理参数。
        """
        # 禁用或失败状态只负责释放已启用的通道。
        if self.failed or not QUALITY or not STRENGTH:
            self.clear()
            return

        # 没有活动快照时无需继续设置参数。
        if not self.snapshot:
            self._disable()
            return

        # 维度变化后立即清理旧效果。
        dimension = nyl.LvComp.Game.GetCurrentDimension()
        if dimension != self.snapshot['dimension']:
            self.clear()
            return

        # 即使摄像机暂不可用，也必须准时结束并释放本轮。
        if self.clock() - self.started >= PLAY_SECONDS:
            self.clear()
            return

        # 摄像机接口不可用时关闭后处理。
        camera = nyl.LvComp.Camera.GetPosition()
        forward = nyl.LvComp.Camera.GetForward()
        if not camera or not forward:
            get_log(self, "effect.client").sample("camera_unavailable", level="WARNING")
            self._disable()
            return

        # 根据当前状态计算本帧参数。
        parameters = self._frame(self.clock(), dimension, camera, forward)
        if not parameters:
            self._disable()
            return

        # 首次使用时启用通道并写入固定风格参数。
        post = nyl.LvComp.PostProcess
        if not self.enabled:
            if not post.SetEnableByName(self.effect_name, True):
                self._fail("enable")
                return
            self.enabled = True
            if not post.SetParameter(self.effect_name, "style", STYLE):
                self._fail("style")
                return
        # 首次启用默认强度为零，两个动态 vec4 都成功后才出现画面。
        for name, value in zip(("field", "shape"), parameters):
            if name == "field" and not self.environment_owner:
                value = value[:3] + (-value[3],)
            if not post.SetParameter(self.effect_name, name, value):
                self._fail(name)
                return

    def _fail(self, operation):
        """
        记录后处理操作失败并关闭当前效果。
        """
        self.failed = True
        self.clear()

    def _disable(self):
        """
        关闭后处理通道，并在接口失败时保留有限重试。
        """
        if not self.enabled or self.clock() < self.disable_retry:
            return
        if nyl.LvComp.PostProcess.SetEnableByName(self.effect_name, False):
            self.enabled = False
            return
        # 关闭失败时不能把 enabled 提前置假，否则后续再无机会释放通道；
        # 保留标记并每秒重试，failed 同时阻止新快照重新开启已故障的效果。
        self.disable_retry = self.clock() + 1.0
        self.failed = True

    def clear(self):
        """
        清空当前视觉快照、插值中心和后处理通道。
        """
        # 清空本轮状态，并保留关闭失败的重试状态。
        self.snapshot = None
        self.center = None
        self.particles.clear()
        self._disable()
