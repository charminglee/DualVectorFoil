# -*- coding: utf-8 -*-
# =================================================
#  ⠀
#   Author: Nuoyan <https://github.com/charminglee>
#   Email : 1279735247@qq.com
#   Date  : 2026-10-21
#  ⠀
# =================================================


# region Mapping and Transfer Tests ==================================================


import os
import sys
import types
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src", "bp"))


def module(name):
    """
    创建并注册指定名称的测试模块替身。
    """
    result = types.ModuleType(name)
    result.__path__ = []
    sys.modules[name] = result
    return result


for name in ("mod", "mod.server", "mod.common"):
    module(name)
server_api = module("mod.server.extraServerApi")
sys.modules['mod'].server = sys.modules['mod.server']
sys.modules['mod.server'].extraServerApi = server_api
enums = module("mod.common.minecraftEnum")
enums.GameType = type("GameType", (), {'Creative': 1})
enums.ItemPosType = type("ItemPosType", (), {'CARRIED': 0})
library = module("dualvectorfoil_scripts.nuoyanlib")
library.server = module(library.__name__ + ".server")
library.server.LvComp = object()
library.server.event = lambda *args, **kwargs: (lambda func: func)
constants = module("dualvectorfoil_scripts.common.constant")
constants.CLIENT_SYSTEM_NAME = "MainClientSystem"
constants.SERVER_SYSTEM_NAME = "MainServerSystem"
constants.ServerEvent = type("ServerEvent", (), {'FoilFieldState': "FoilFieldState"})
module("dualvectorfoil_scripts.modules._base.server").BaseServer = object

from dualvectorfoil_scripts.modules.foil.server import (
    flatten, unflatten)


class MappingTests(unittest.TestCase):
    """
    验证三维格点到二维平面的唯一映射和可逆性。
    """

    def test_injective_roundtrip_all_signed_points(self):
        """
        验证正负坐标范围内的映射无碰撞且可往返还原。
        """
        origin = (-17, 62, 29)
        seen = set()
        for x in range(-16, 17):
            for y in range(-16, 17):
                for z in range(-16, 17):
                    p = (x, y, z)
                    q = flatten(p, origin)
                    self.assertEqual(q[1], origin[1])
                    self.assertEqual(unflatten(q, origin), p)
                    self.assertNotIn(q, seen)
                    seen.add(q)

    def test_large_and_stable_coordinates(self):
        """
        验证世界边界和极大坐标仍能稳定往返。
        """
        for p in [(29999900, 319, -29999900), (-10**18, -64, 10**18)]:
            self.assertEqual(unflatten(flatten(p, (0, 0, 0)), (0, 0, 0)), p)


if __name__ == "__main__":
    unittest.main()
