# -*- coding: utf-8 -*-
# =================================================
#  ⠀
#   Author: Nuoyan <https://github.com/charminglee>
#   Email : 1279735247@qq.com
#   Date  : 2026-11-13
#  ⠀
# =================================================


from time import time
from ...nuoyanlib import client as nyl
from ...common.constant import *
from .._base.client import BaseClient
from .config import *
from .playback import FieldPlayback
from .atmosphere import CatastropheAtmosphere


server_event = nyl.event(sys_name=SERVER_SYSTEM_NAME)


class EffectClient(BaseClient):
    """
    按任务去重，调度相互独立的单轮后处理，并复用空闲通道。
    """

    def __init__(self, namespace, system_name):
        super(EffectClient, self).__init__(namespace, system_name)
        self.playbacks = []
        self.seen = set()
        self.atmosphere = CatastropheAtmosphere()

    @server_event
    def FoilSpaceFallState(self, args):
        """
        每个任务只触发一次；心跳、进度和完成通知均不改变已有播放。
        """
        if not QUALITY or not STRENGTH or not args.active:
            return
        if args.dimension != nyl.LvComp.Game.GetCurrentDimension():
            return
        key = (args.dimension, args.run_id)
        if key in self.seen:
            return
        playback = self._acquire()
        if playback is None:
            return
        self.seen.add(key)
        playback.start(args, time())

    def _acquire(self):
        """
        优先复用已关闭通道；并发播放时按需新增独立后处理通道。
        """
        for playback in self.playbacks:
            playback._update()
            if not playback.snapshot and not playback.enabled and not playback.failed:
                return playback
        name = EFFECT if not self.playbacks else "%s_%d" % (EFFECT, len(self.playbacks))
        if self.playbacks and not nyl.LvComp.PostProcess.AddPostProcess(process_definition(name)):
            return None
        playback = FieldPlayback(name)
        self.playbacks.append(playback)
        return playback

    def OnScriptTickClient(self, args):
        """
        分别推进每一轮播放，结束后关闭对应通道。
        """
        owner_found = False
        for playback in self.playbacks:
            active = playback.snapshot and not playback.failed and playback.clock() - playback.started < PLAY_SECONDS
            playback.environment_owner = bool(active and not owner_found)
            if playback.environment_owner:
                owner_found = True
            playback._update()
        self.atmosphere.update(self.playbacks)

    def DimensionChangeClientEvent(self, args):
        """
        本机玩家切换维度时关闭全部本地光场，保留已播任务去重记录。
        """
        if args.playerId == nyl.PLAYER_ID:
            self.clear()

    def clear(self):
        """
        关闭所有播放；关闭失败的通道仍在 tick 中限频重试。
        """
        for playback in self.playbacks:
            playback.clear()
        self.atmosphere.clear()
