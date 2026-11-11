# -*- coding: utf-8 -*-
# =================================================
#
#   Author: Nuoyan <https://github.com/charminglee>
#   Email : 1279735247@qq.com
#   Date  : 2026-11-12
#
# =================================================


"""模组业务日志；不导入 SDK，不配置或修改引擎与内置库的日志器。"""


from time import time


class BusinessLog(object):
    """
    输出固定前缀的业务日志，并按稳定流键合并重复高频消息。
    """

    def __init__(self, scope):
        self.scope = scope
        self.streams = {}

    def event(self, event, level="INFO", **fields):
        """
        输出事件及有界字段，不序列化任务快照或完整调色板。
        """
        details = " ".join("%s=%s" % (key, repr(value)[:512]) for key, value in sorted(fields.items()))
        print("[DualVectorFoil][%s][%s] %s ts=%.3f %s" % (self.scope, level, event, time(), details))

    def sample(self, event, signature=None, key=None, interval=5.0, level="INFO", **fields):
        """
        首次与签名变化立即记录，相同事件每五秒输出并汇总省略次数。
        """
        now = time()
        if signature is None:
            signature = (level, fields['reason'] if 'reason' in fields else None)
        stream = key if key is not None else event
        if stream in self.streams:
            previous = self.streams[stream]
            if previous[1] == signature and 0 <= now - previous[0] < interval:
                previous[2] += 1
                return
            fields['suppressed'] = previous[2]
        self.streams[stream] = [now, signature, 0]
        self.event(event, level, **fields)


def get_log(owner, scope):
    """
    按业务对象延迟创建日志器，日志节流信息不写入世界持久化数据。
    """
    if not hasattr(owner, '_business_log'):
        owner._business_log = BusinessLog(scope)
    return owner._business_log
