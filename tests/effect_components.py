# -*- coding: utf-8 -*-
"""末日演出本地组件替身，记录粒子生命周期及天空恢复。"""


class FakeParticles(object):
    def __init__(self):
        self.next_id = 1
        self.live = {}
        self.created = []
        self.removed = []

    def Create(self, name, pos, rot):
        particle_id = self.next_id
        self.next_id += 1
        self.live[particle_id] = name
        self.created.append((name, pos, rot))
        return particle_id

    def Remove(self, particle_id):
        self.removed.append(particle_id)
        self.live.pop(particle_id, None)
        return True


class FakeSky(object):
    def __init__(self):
        self.color = (0.4, 0.6, 1.0, 1.0)
        self.brightness = 1.0
        self.use_color = False
        self.use_brightness = False

    def GetSkyColor(self):
        return self.color

    def GetAmbientBrightness(self):
        return self.brightness

    def GetUseSkyColor(self):
        return self.use_color

    def GetUseAmbientBrightness(self):
        return self.use_brightness

    def SetSkyColor(self, color):
        self.color = color
        self.use_color = True
        return True

    def SetAmbientBrightness(self, brightness):
        self.brightness = brightness
        self.use_brightness = True
        return True

    def ResetSkyColor(self):
        self.use_color = False
        return True

    def ResetAmbientBrightness(self):
        self.use_brightness = False
        return True


def install(level):
    level.ParticleSystem = FakeParticles()
    level.SkyRender = FakeSky()
    return level
