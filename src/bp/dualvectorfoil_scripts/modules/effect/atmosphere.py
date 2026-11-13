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
    多任务共享天空控制器，按最强活动包络合成并恢复进入前的状态。
    """

    def __init__(self):
        self.previous = None
        self.last = None

    def update(self, playbacks):
        """
        使用各轮独立时钟；最后一个有效光场结束时恢复天空与天空亮度。
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
        if self.previous is None:
            self.previous = (sky.GetSkyColor(), sky.GetAmbientBrightness(), sky.GetUseSkyColor(), sky.GetUseAmbientBrightness())
        original, brightness, unused_color, unused_brightness = self.previous
        color = tuple(nyl.lerp(original[i], (0.018, 0.012, 0.055)[i], power) for i in range(3)) + (1.0,)
        current = (color, brightness * (1.0 - power * 0.88))
        if self.last != current:
            sky.SetSkyColor(current[0])
            sky.SetAmbientBrightness(current[1])
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
        self.previous = None
        self.last = None
