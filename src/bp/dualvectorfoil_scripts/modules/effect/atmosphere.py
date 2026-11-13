# -*- coding: utf-8 -*-
# =================================================
#
#   Author: Nuoyan <https://github.com/charminglee>
#   Email : 1279735247@qq.com
#   Date  : 2026-11-13
#
# =================================================


from ...nuoyanlib import client as nyl
from .config import PLAY_SECONDS, VIEW_DISTANCE
from .timeline import envelope


class CatastropheAtmosphere(object):
    """
    多任务共享天空与雾色控制器，按最强活动包络合成并恢复进入前的状态。
    """

    def __init__(self):
        self.previous = None
        self.previous_fog = None
        self.last = None

    def update(self, playbacks):
        """
        使用各轮独立时钟；最后一个有效光场结束时恢复天空、亮度与雾色。
        """
        camera = nyl.LvComp.Camera.GetPosition()
        dimension = nyl.LvComp.Game.GetCurrentDimension()
        power = 0.0
        for playback in playbacks:
            if not playback.snapshot or playback.snapshot['dimension'] != dimension or not camera:
                continue
            if nyl.distance(playback.center, camera) > VIEW_DISTANCE:
                continue
            age = playback.clock() - playback.started
            if 0.0 <= age < PLAY_SECONDS:
                power = max(power, envelope(age))
        if power < 0.001:
            self.clear()
            return
        sky = nyl.LvComp.SkyRender
        fog = nyl.LvComp.Fog
        if self.previous is None:
            self.previous = (sky.GetSkyColor(), sky.GetAmbientBrightness(), sky.GetUseSkyColor(), sky.GetUseAmbientBrightness())
            self.previous_fog = (fog.GetFogColor(), fog.GetUseFogColor())
        original, brightness, unused_color, unused_brightness = self.previous
        # 雾色与天空朝同一深蓝紫色平滑过渡，保留影响水下效果的雾色 alpha。
        target = (0.018, 0.012, 0.055)
        original_fog, unused_fog = self.previous_fog
        color = tuple(nyl.lerp(original[i], target[i], power) for i in range(3)) + (1.0,)
        fog_color = tuple(nyl.lerp(original_fog[i], target[i], power) for i in range(3)) + (original_fog[3],)
        current = (color, brightness * (1.0 - power * 0.88), fog_color)
        if self.last != current:
            sky.SetSkyColor(current[0])
            sky.SetAmbientBrightness(current[1])
            fog.SetFogColor(current[2])
            self.last = current

    def clear(self):
        """
        恢复之前由其他模组设置的颜色；原先无覆盖时恢复引擎动态天空。
        """
        if self.previous is None:
            return
        sky = nyl.LvComp.SkyRender
        color, brightness, use_color, use_brightness = self.previous
        sky.SetSkyColor(color)
        if not use_color:
            sky.ResetSkyColor()
        sky.SetAmbientBrightness(brightness)
        if not use_brightness:
            sky.ResetAmbientBrightness()
        # 自定义雾色恢复原值；原先由引擎控制时交还动态雾色，不改变雾效距离。
        fog = nyl.LvComp.Fog
        fog_color, use_fog = self.previous_fog
        fog.SetFogColor(fog_color)
        if not use_fog:
            fog.ResetFogColor()
        self.previous = None
        self.previous_fog = None
        self.last = None
