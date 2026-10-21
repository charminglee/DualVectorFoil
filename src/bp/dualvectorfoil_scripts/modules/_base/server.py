# -*- coding: utf-8 -*-
# =================================================
#  ⠀
#   Author: Nuoyan <https://github.com/charminglee>
#   Email : 1279735247@qq.com
#   Date  : 2026-10-21
#  ⠀
# =================================================


import mod.server.extraServerApi as server_api

from ...nuoyanlib import server as nyl
from ...common.constant import *
from ...main_server import MainServerSystem


client_event = nyl.event(sys_name=CLIENT_SYSTEM_NAME)
server_event = nyl.event(sys_name=SERVER_SYSTEM_NAME)


# region Server System Base ==================================================


class BaseServer(nyl.NyServerSystem):
    """
    服务端业务系统基类。
    """

    def __init__(self, namespace, system_name):
        super(BaseServer, self).__init__(namespace, system_name)
        # 缓存主服务端系统，供业务模块使用统一入口。
        self.main_system = nyl.get_system(SERVER_SYSTEM_NAME)  # type: MainServerSystem


# endregion
