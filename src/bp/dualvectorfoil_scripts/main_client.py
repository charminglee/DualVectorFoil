# -*- coding: utf-8 -*-
# =================================================
#  ⠀
#   Author: Nuoyan <https://github.com/charminglee>
#   Email : 1279735247@qq.com
#   Date  : 2026-10-21
#  ⠀
# =================================================


import mod.client.extraClientApi as client_api
from mod.common.minecraftEnum import *

from .nuoyanlib import client as nyl
from .nuoyanlib.client import LvComp, PlrComp, CF, PLAYER_ID
from .common.constant import *
from .common.config import *


client_event = nyl.event(sys_name=CLIENT_SYSTEM_NAME)
server_event = nyl.event(sys_name=SERVER_SYSTEM_NAME)


# region Client System Entry ==================================================


class MainClientSystem(nyl.NyClientSystem):
    """
    主客户端系统入口。
    """

    def __init__(self, namespace, system_name):
        super(MainClientSystem, self).__init__(namespace, system_name)

    # region Engine Events ==================================================

    # endregion

    # region Custom Events ==================================================

    # endregion


# endregion
