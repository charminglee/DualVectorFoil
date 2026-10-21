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
from ...common.constant import CLIENT_SYSTEM_NAME, SERVER_SYSTEM_NAME
from .._base.server import BaseServer
from .config import EVENT, QUALITY, RADIUS, STRENGTH, SYNC_TICKS, VIEW_DISTANCE


client_event = nyl.event(sys_name=CLIENT_SYSTEM_NAME)
server_event = nyl.event(sys_name=SERVER_SYSTEM_NAME)


# region 公开流程事件到常数大小视觉快照 ==================================================


def distance_squared(a, b):
    """
    计算两个三维点之间的平方距离。
    """
    return sum((a[i] - b[i]) ** 2 for i in range(3))


def make_snapshot(args):
    """
    把公开流程事件转换为视觉参数，不访问 foil 内部状态。
    """
    # 空目标没有可渲染的平面，直接跳过。
    count = args.block_count
    if not count:
        return None

    # 输出固定大小快照，避免把完整方块列表传入客户端。
    return {
        'dimension': args.dimension,
        'run_id': args.run_id,
        'active': args.phase == "moving",
        'center': [pos + 0.5 for pos in args.source],
        'plane_y': args.origin[1] + 1.02,
        'progress': min(1.0, float(args.processed_count) / count),
    }


# endregion


# region 附近玩家筛选和限频通知 ==================================================


class SpaceFallSync(object):
    """
    筛选附近玩家并限频发送空间跌落视觉快照。
    """

    def __init__(self, system):
        self.system = system
        self.viewers = {}
        self.last_tick = {}
        self.run_ids = {}

    def send(self, args):
        """
        根据流程事件发送、停发或限频更新视觉快照。
        """
        # 画质或强度关闭时不产生跨端流量。
        if not QUALITY or not STRENGTH:
            return

        # 同一任务移动阶段按协议 tick 数限频。
        dimension, tick = args.dimension, args.tick
        previous_tick = self.last_tick.get(dimension)
        if (
            args.phase == "moving"
            and self.run_ids.get(dimension) == args.run_id
            and previous_tick is not None
            and 0 <= tick - previous_tick < SYNC_TICKS
        ):
            return

        # 空目标不发送视觉快照。
        snapshot = make_snapshot(args)
        if snapshot is None:
            return

        # 活跃任务记录限频信息，完成消息立即清理。
        if snapshot['active']:
            self.last_tick[dimension] = tick
            self.run_ids[dimension] = snapshot['run_id']
        else:
            self.last_tick.pop(dimension, None)

        # 计算观看者变化，先通知离开的玩家再向当前玩家广播。
        previous = self.viewers.get(dimension, set())
        current = self._nearby(dimension, snapshot) if snapshot['active'] else set()
        departed = previous - current
        if departed:
            stopped = dict(snapshot, active=False)
            self.system.main_system.NotifyToMultiClients(list(departed), EVENT, stopped)
        if current:
            self.system.main_system.NotifyToMultiClients(list(current), EVENT, snapshot)
        self.viewers[dimension] = current

    def _nearby(self, dimension, snapshot):
        """
        筛选目标维度内可能看到视觉场的在线玩家。
        """
        result = set()
        center = snapshot['center']
        plane = (center[0], snapshot['plane_y'], center[2])

        # 留出第三人称摄像机距离和光场半径的余量，细粒度剔除由客户端执行。
        limit = (VIEW_DISTANCE + RADIUS + 16.0) ** 2
        for player_id in server_api.GetPlayerList():
            cf = nyl.CF(player_id)

            # 非目标维度的玩家不参与同步。
            if cf.Dimension.GetEntityDimensionId() != dimension:
                continue

            # 靠近源中心或输出平面的玩家都保留。
            pos = cf.Pos.GetPos()
            if pos is not None and min(
                distance_squared(pos, center),
                distance_squared(pos, plane),
            ) < limit:
                result.add(player_id)
        return result


# endregion


# region 系统入口 ==================================================


class EffectServer(BaseServer):
    """
    空间跌落服务端系统。
    """

    def __init__(self, namespace, system_name):
        super(EffectServer, self).__init__(namespace, system_name)

        # 创建只依赖公开事件载荷的视觉同步器。
        self.space_fall = SpaceFallSync(self)

    @server_event
    def FoilFieldState(self, args):
        """
        接收二向箔服务端本地流程事件。
        """
        # 由同步器决定是否发送以及发送给哪些玩家。
        self.space_fall.send(args)


# endregion
