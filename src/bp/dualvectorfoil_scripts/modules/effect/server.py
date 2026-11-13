# -*- coding: utf-8 -*-
# =================================================
#  ⠀
#   Author: Nuoyan <https://github.com/charminglee>
#   Email : 1279735247@qq.com
#   Date  : 2026-11-13
#  ⠀
# =================================================


import mod.server.extraServerApi as server_api
from ...nuoyanlib import server as nyl
from ...common.constant import *
from .._base.server import BaseServer
from .config import *


server_event = nyl.event(sys_name=SERVER_SYSTEM_NAME)


class EffectServer(BaseServer):
    """
    按任务向附近玩家发送一次播放触发，不控制客户端播放进度或结束。
    """

    def __init__(self, namespace, system_name):
        super(EffectServer, self).__init__(namespace, system_name)
        self.viewers = {}
        self.last_tick = {}

    @server_event
    def FoilFieldState(self, args):
        """
        各个任务分别处理，允许同维度多个独立特效同时触发。
        """
        self._send(args)

    def _make_snapshot(self, args):
        """
        只传固定光场中心与平面；兼容保留的进度字段恒为零。
        """
        if not args.block_count:
            return None
        return {
            'dimension': args.dimension,
            'run_id': args.run_id,
            'active': True,
            'center': [pos + 0.5 for pos in args.origin],
            'plane_y': args.origin[1] + 1.02,
            'progress': 0.0,
        }

    def _send(self, args):
        """
        限频筛选同维度观看者；每名玩家对每个任务只接收一次触发。
        """
        if not QUALITY or not STRENGTH or args.phase != "moving":
            return
        key = (args.dimension, args.run_id)
        if key in self.last_tick and 0 <= args.tick - self.last_tick[key] < SYNC_TICKS:
            return
        snapshot = self._make_snapshot(args)
        if not snapshot:
            return
        self.last_tick[key] = args.tick
        if key not in self.viewers:
            self.viewers[key] = set()
        current = self._nearby(args.dimension, snapshot) - self.viewers[key]
        if current:
            self.main_system.NotifyToMultiClients(list(current), ServerEvent.FoilSpaceFallState, snapshot)
            self.viewers[key].update(current)

    def _nearby(self, dimension, snapshot):
        """
        筛选目标维度内可能看到视觉场的在线玩家。
        """
        result = set()
        center = snapshot['center']
        plane = (center[0], snapshot['plane_y'], center[2])

        # 服务端按玩家位置做宽松的距离平方粗筛，省去逐玩家开方；
        # 光场半径和摄像机余量避免漏发，实际相机朝向与淡出由客户端细筛。
        limit = (VIEW_DISTANCE + RADIUS + 16.0) ** 2
        for player_id in server_api.GetPlayerList():
            cf = nyl.CF(player_id)

            # 非目标维度的玩家不参与同步。
            if cf.Dimension.GetEntityDimensionId() != dimension:
                continue

            # 靠近源中心或输出平面的玩家都保留。
            pos = cf.Pos.GetPos()
            if pos and min(nyl.distance_square(pos, center), nyl.distance_square(pos, plane)) < limit:
                result.add(player_id)
        return result
