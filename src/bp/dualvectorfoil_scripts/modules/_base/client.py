# -*- coding: utf-8 -*-
# =================================================
#  ⠀
#   Author: Nuoyan <https://github.com/charminglee>
#   Email : 1279735247@qq.com
#   Date  : 2026-10-21
#  ⠀
# =================================================


import mod.client.extraClientApi as client_api

from ...nuoyanlib import client as nyl
from ...common.constant import *
from ...main_client import MainClientSystem


client_event = nyl.event(sys_name=CLIENT_SYSTEM_NAME)
server_event = nyl.event(sys_name=SERVER_SYSTEM_NAME)


# region Client System Base ==================================================


class BaseClient(nyl.NyClientSystem):
    """
    客户端业务系统基类。
    """

    def __init__(self, namespace, system_name):
        super(BaseClient, self).__init__(namespace, system_name)
        # 缓存主客户端系统，供业务模块使用统一入口。
        self.main_system = nyl.get_system(CLIENT_SYSTEM_NAME)  # type: MainClientSystem


# endregion
