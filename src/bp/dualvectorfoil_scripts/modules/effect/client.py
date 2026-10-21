# -*- coding: utf-8 -*-
# =================================================
#  ⠀
#   Author: Nuoyan <https://github.com/charminglee>
#   Email : 1279735247@qq.com
#   Date  : 2026-10-21
#  ⠀
# =================================================


from math import exp
from time import time
from ...nuoyanlib import client as nyl
from ...common.constant import *
from ...common.config import *
from .._base.client import BaseClient
from .config import *


client_event = nyl.event(sys_name=CLIENT_SYSTEM_NAME)
server_event = nyl.event(sys_name=SERVER_SYSTEM_NAME)


# region 空间跌落客户端系统 ==================================================


def smooth_unit(value):
    """
    把数值限幅到 0 至 1 并应用平滑阶跃曲线。
    """
    value = min(1.0, max(0.0, value))
    return value * value * (3.0 - 2.0 * value)


class EffectClient(BaseClient):
    """
    空间跌落客户端系统。
    """

    def __init__(self, namespace, system_name):
        super(EffectClient, self).__init__(namespace, system_name)

        # 初始化视觉快照、位置插值和后处理状态。
        self.snapshot = None
        self.center = None
        self.started = self.last_seen = self.last_frame = 0.0
        self.stopped = None
        self.enabled = False
        self.failed = False
        self.disable_retry = 0.0

    @server_event
    def FoilSpaceFallState(self, args):
        """
        接收二向箔流程的跨端视觉快照。
        """
        # 画质关闭、强度为零或已失败时不接收新状态。
        if not QUALITY or not STRENGTH or self.failed:
            return

        # 只处理当前客户端维度。
        if args.dimension == nyl.LvComp.Game.GetCurrentDimension():
            self._receive_snapshot(args, time())

    def OnScriptTickClient(self, args):
        """
        在客户端脚本 tick 中刷新后处理状态。
        """
        self._update()

    def DimensionChangeClientEvent(self, args):
        """
        本机玩家切换维度时立即清理视觉状态。
        """
        if args.playerId == nyl.PLAYER_ID:
            self.clear()

    def _receive_snapshot(self, args, now):
        """
        接收服务端视觉快照并更新本地时间状态。
        """
        # 完成消息只延长当前效果，不把余辉移动到新的位置。
        if not args.active:
            if (
                self.snapshot
                and self.snapshot['dimension'] == args.dimension
                and self.snapshot['run_id'] == args.run_id
            ):
                # 保留最后可见中心，完成消息不会把余辉移到最后一个远处方块。
                self.snapshot['progress'] = args.progress
                if not self.stopped:
                    self.stopped = max(now, self.started + MIN_LIFETIME)
            return

        # 新任务、超时或维度变化都需要重新开始一次淡入。
        fresh = (
            not self.snapshot
            or self.stopped
            or now - self.last_seen > STALE_SECONDS
            or self.snapshot['run_id'] != args.run_id
            or self.snapshot['dimension'] != args.dimension
        )
        if fresh or nyl.distance_square(self.center, args.center) > (RADIUS * 2.0) ** 2:
            # 搜索前沿跨越较远分支时重新展开，避免光场扫过两点间的无关区域。
            self.center = tuple(args.center)
            self.started = self.last_frame = now

        # 保存固定字段副本并刷新心跳，避免外部继续修改当前帧参数。
        self.snapshot = {
            'dimension': args.dimension,
            'run_id': args.run_id,
            'active': args.active,
            'center': tuple(args.center),
            'plane_y': args.plane_y,
            'progress': args.progress,
        }
        self.last_seen = now
        self.stopped = None

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

        # 心跳超时后进入淡出阶段。
        if not self.stopped and now - self.last_seen > STALE_SECONDS:
            self.stopped = self.last_seen + STALE_SECONDS
        if self.stopped and now >= self.stopped + FADE_OUT:
            self.clear()
            return None

        # 平滑插值视觉中心，限制单帧时间差避免卡顿后跳变。
        dt = min(0.25, max(0.0, now - self.last_frame))
        self.last_frame = now
        blend = 1.0 - exp(-8.0 * dt)
        target = self.snapshot['center']
        self.center = tuple(
            self.center[i] + (target[i] - self.center[i]) * blend
            for i in range(3)
        )

        # 同时包住源位置的局部球体和位于输出平面的光盘。
        distance = nyl.distance(self.center, camera)
        plane_center = (self.center[0], self.snapshot['plane_y'], self.center[2])
        plane_distance = nyl.distance(plane_center, camera)
        distance = min(distance, plane_distance)
        source_dot = sum((self.center[i] - camera[i]) * forward[i] for i in range(3))
        plane_dot = sum((plane_center[i] - camera[i]) * forward[i] for i in range(3))

        # 超出观看距离或完全位于摄像机背后时不启用后处理。
        if distance >= VIEW_DISTANCE or max(source_dot, plane_dot) < -RADIUS:
            return None

        # 组合攻击、释放和远距离衰减，生成当前帧强度。
        age = max(0.0, now - self.started)
        attack = smooth_unit(age / FADE_IN)
        release = (
            1.0
            if not self.stopped
            else 1.0 - smooth_unit((now - self.stopped) / FADE_OUT)
        )
        far_fade = 1.0 - smooth_unit((distance / VIEW_DISTANCE - 0.7) / 0.3)
        strength = STRENGTH * attack * release * far_fade
        if strength < 0.001:
            return None

        # 光环随淡入扩张，并返回 field 与 shape 两个 vec4 参数。
        radius = RADIUS * (0.3 + 0.7 * attack)
        return (
            self.center + (radius,),
            (
                self.snapshot['plane_y'],
                strength,
                age % 24.0,
                self.snapshot['progress'],
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

        # 摄像机接口不可用时关闭后处理。
        camera = nyl.LvComp.Camera.GetPosition()
        forward = nyl.LvComp.Camera.GetForward()
        if not camera or not forward:
            self._disable()
            return

        # 根据当前状态计算本帧参数。
        parameters = self._frame(time(), dimension, camera, forward)
        if not parameters:
            self._disable()
            return

        # 首次使用时启用通道并写入固定风格参数。
        post = nyl.LvComp.PostProcess
        if not self.enabled:
            if not post.SetEnableByName(EFFECT, True):
                self._fail("enable")
                return
            self.enabled = True
            if not post.SetParameter(EFFECT, "style", STYLE):
                self._fail("style")
                return
        # 首次启用默认强度为零，两个动态 vec4 都成功后才出现画面。
        for name, value in zip(("field", "shape"), parameters):
            if not post.SetParameter(EFFECT, name, value):
                self._fail(name)
                return

    def _fail(self, operation):
        """
        记录后处理操作失败并关闭当前效果。
        """
        if not self.failed:
            print("[DualVectorFoil] space fall postprocess failed: " + operation)
        self.failed = True
        self.clear()

    def _disable(self):
        """
        关闭后处理通道，并在接口失败时保留有限重试。
        """
        if not self.enabled or time() < self.disable_retry:
            return
        if nyl.LvComp.PostProcess.SetEnableByName(EFFECT, False):
            self.enabled = False
            return
        # 接口有失败返回；保留 enabled，以便下一秒重试关闭，而不是遗留常驻效果。
        self.disable_retry = time() + 1.0
        if not self.failed:
            print("[DualVectorFoil] space fall postprocess failed: disable")
        self.failed = True

    def clear(self):
        """
        清空当前视觉快照、插值中心和后处理通道。
        """
        # 先清空状态，再尝试关闭后处理通道。
        self.snapshot = None
        self.center = None
        self.stopped = None
        self._disable()


# endregion
