# -*- coding: utf-8 -*-
# =================================================
#
#   Author: Nuoyan <https://github.com/charminglee>
#   Email : 1279735247@qq.com
#   Date  : 2026-11-13
#
# =================================================


from ...nuoyanlib import client as nyl
from ...common.diagnostics import get_log


class CatastropheParticles(object):
    """
    单个二向箔的天空裂隙序列帧、空间碎片与近地余烬，统一清理。
    """

    def __init__(self):
        self.ids = []

    def start(self, center):
        """
        仅创建三个有界发射器，粒子运动由引擎的 Molang 驱动。
        """
        self.clear()
        comp = nyl.LvComp.ParticleSystem
        for name, height in (("cataclysm_rift_v2", 38.0), ("cataclysm_shards", 0.0), ("cataclysm_embers", 0.0)):
            pos = (center[0], center[1] + height, center[2])
            particle_id = comp.Create("nuoyan:" + name, pos, (0.0, 0.0, 0.0))
            if particle_id:
                self.ids.append(particle_id)
            else:
                get_log(self, "effect.particles").event("create_failed", level="ERROR", effect=name, pos=pos)

    def clear(self):
        """
        结束或切维度时主动移除发射器；已自然结束的实例允许返回失败。
        """
        for particle_id in self.ids:
            nyl.LvComp.ParticleSystem.Remove(particle_id)
        self.ids = []
