# -*- coding: utf-8 -*-
# =================================================
#  ⠀
#   Author: Nuoyan <https://github.com/charminglee>
#   Email : 1279735247@qq.com
#   Date  : 2026-10-21
#  ⠀
# =================================================


import mod.server.extraServerApi as server_api
from mod.common.minecraftEnum import *
from ...nuoyanlib import server as nyl
from ...nuoyanlib.server import LvComp, CF
from ...common.constant import *
from ...common.config import *
from .._base.server import BaseServer
from .config import *


client_event = nyl.event(sys_name=CLIENT_SYSTEM_NAME)
server_event = nyl.event(sys_name=SERVER_SYSTEM_NAME)


# region Server Module Template ==================================================


class TemplateServer(BaseServer):
    """
    服务端功能模块模板。
    """

    def __init__(self, namespace, system_name):
        super(TemplateServer, self).__init__(namespace, system_name)

    # region Engine Events ==================================================

    # endregion

    # region Custom Events ==================================================

    # endregion


# endregion
