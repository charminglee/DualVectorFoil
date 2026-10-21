# -*- coding: utf-8 -*-
# =================================================
#  ⠀
#   Author: Nuoyan <https://github.com/charminglee>
#   Email : 1279735247@qq.com
#   Date  : 2026-10-21
#  ⠀
# =================================================


from .common.constant import (
    ClientModule,
    CLIENT_SYSTEM_NAME,
    CLIENT_SYSTEM_PATH,
    MOD_NAME,
    ServerModule,
    SERVER_SYSTEM_NAME,
    SERVER_SYSTEM_PATH,
)
from . import nuoyanlib


nuoyanlib.run(
    MOD_NAME,
    clients=[(CLIENT_SYSTEM_NAME, CLIENT_SYSTEM_PATH)] + [module.value for module in ClientModule],
    servers=[(SERVER_SYSTEM_NAME, SERVER_SYSTEM_PATH)] + [module.value for module in ServerModule],
)
