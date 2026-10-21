# -*- coding: utf-8 -*-
# =================================================
#  ⠀
#   Author: Nuoyan <https://github.com/charminglee>
#   Email : 1279735247@qq.com
#   Date  : 2026-10-21
#  ⠀
# =================================================


from ..nuoyanlib.common.enum import StrEnum, auto, IntEnum, Enum, ordered


MOD_NAME = "DualVectorFoil"
MOD_NAME_S = MOD_NAME.lower()
CLIENT_SYSTEM_NAME = "MainClientSystem"
CLIENT_SYSTEM_PATH = "{0}_scripts.main_client".format(MOD_NAME_S)
SERVER_SYSTEM_NAME = "MainServerSystem"
SERVER_SYSTEM_PATH = "{0}_scripts.main_server".format(MOD_NAME_S)
MODULES_PATH = "{0}_scripts.modules".format(MOD_NAME_S)
UI_CLS_PATH = "{0}_scripts.ui".format(MOD_NAME_S)


class ClientModule(Enum):
    """
    客户端功能模块注册表。
    """
    Effect = ordered(("EffectClient", MODULES_PATH + ".effect.client"))
    Foil = ordered(("FoilClient", MODULES_PATH + ".foil.client"))


class ServerModule(Enum):
    """
    服务端功能模块注册表。
    """
    Effect = ordered(("EffectServer", MODULES_PATH + ".effect.server"))
    Foil = ordered(("FoilServer", MODULES_PATH + ".foil.server"))


class ClientEvent(StrEnum):
    """
    客户端自定义事件名称集合。
    """
    pass


class ServerEvent(StrEnum):
    """
    服务端自定义事件名称集合。
    """
    FoilFieldState = "FoilFieldState"










