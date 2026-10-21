# -*- coding: utf-8 -*-
# =================================================
#  ⠀
#   Author: Nuoyan <https://github.com/charminglee>
#   Email : 1279735247@qq.com
#   Date  : 2026-10-21
#  ⠀
# =================================================


from copy import deepcopy


class EventArgs(object):
    """
    用属性形式承载事件参数，模拟 ModSDK 回调对象。
    """

    def __init__(self, values=None):
        for name, value in (values or {}).items():
            setattr(self, name, value)


def make_event_args(values):
    """
    把事件载荷转换成支持属性访问的参数对象。
    """
    if isinstance(values, EventArgs):
        return deepcopy(values)
    return EventArgs(deepcopy(values))
