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
from ...common.config import *
from .._base.client import BaseClient
from .config import *


client_event = nyl.event(sys_name=CLIENT_SYSTEM_NAME)
server_event = nyl.event(sys_name=SERVER_SYSTEM_NAME)


# region Entity Presentation ==================================================


class FoilClient(BaseClient):
    """
    二向箔客户端表现系统。
    """

    def __init__(self, namespace, system_name):
        super(FoilClient, self).__init__(namespace, system_name)

        # 维护 AOI 实体、已安装模型和不支持自定义模型的玩家。
        self.tracked = {nyl.PLAYER_ID}
        self.applied = {}
        self.unsupported = set()
        self.tick = 0

    def AddEntityClientEvent(self, args):
        """
        把进入客户端 AOI 的实体加入跟踪集合。
        """
        # 新实体进入 AOI 后等待下一次批量安装。
        self.tracked.add(args.id)

    def AddPlayerCreatedClientEvent(self, args):
        """
        记录新建玩家并允许重新安装二维模型。
        """
        # 玩家皮肤可能异步重建，因此移除旧安装记录。
        entity_id = args.playerId
        self.tracked.add(entity_id)
        self.applied.pop(entity_id, None)

    def RemoveEntityClientEvent(self, args):
        """
        移除已离开客户端 AOI 的实体状态。
        """
        # 实体离开 AOI 时同步清理本地缓存。
        self._forget(args.id)

    def RemovePlayerAOIClientEvent(self, args):
        """
        移除已离开玩家 AOI 的玩家状态。
        """
        # 玩家离开 AOI 时同步清理本地缓存。
        self._forget(args.playerId)

    def OnScriptTickClient(self, args):
        """
        定期补齐实体跟踪并安装二维模型。
        """
        # 每十帧执行一次批量同步，避免逐帧扫描渲染器。
        self.tick += 1
        if self.tick % 10:
            return

        # 补齐系统注册前已进入 AOI 的实体，兼容脚本重新加载。
        live = set(client_api.GetEngineActor().keys() + client_api.GetPlayerList())
        self.tracked.intersection_update(live)
        self.tracked.update(live)

        # 删除已经离开 AOI 的模型安装记录。
        for entity_id in list(self.applied):
            if entity_id not in live:
                self.applied.pop(entity_id)

        # 只为尚未成功安装的实体替换几何。
        for entity_id in self.tracked:
            if entity_id not in self.applied:
                self._apply(entity_id)

    def _forget(self, entity_id):
        """
        清理指定实体的本地跟踪和安装记录。
        """
        # 三类缓存都按实体编号独立清理。
        self.tracked.discard(entity_id)
        self.applied.pop(entity_id, None)
        self.unsupported.discard(entity_id)

    def _apply(self, entity_id):
        """
        按实体类型和渲染键替换为预生成的二维几何。
        """
        # 只有服务端已标记为二维化的实体才替换几何。
        cf = nyl.CF(entity_id)
        data = cf.ModAttr.GetAttr(ATTR)
        if not data:
            return
        # 根据实体类型选择生成的渲染键目录。
        kind = data['kind']
        catalog = ENTITY_GEOMETRIES.get(kind)
        if not catalog:
            return
        render = cf.ActorRender
        catalog = dict(catalog)

        # 玩家模型需要区分默认与 slim，未知自定义皮肤保持原样。
        if kind == "minecraft:player":
            style = render.GetModelStyle()
            if style == "custom":
                if entity_id not in self.unsupported:
                    print(
                        "[DualVectorFoil] custom player geometry is not in "
                        "the generated catalog: " + entity_id
                    )
                    self.unsupported.add(entity_id)
                return
            if style == "slim":
                catalog['default'] = "geometry.humanoid.customSlim"
        # 获取实体当前实际使用的渲染键，避免覆盖不存在的层。
        keys = render.GetActorRenderParams(entity_id, "geometry")
        if not keys:
            return
        changed = {}
        for key, original in catalog.items():
            if key not in keys:
                continue

            # 二维几何目录使用原始模型名作为索引。
            geometry = GEOMETRIES[original]
            if kind == "minecraft:player":
                ok = render.AddPlayerGeometry(key, geometry)
            else:
                ok = render.AddGeometryToOneActor(entity_id, key, geometry)
            if not ok:
                return
            changed[key] = original
        if not changed:
            return

        # 玩家走独立重建设置，普通实体只重建单个 Actor。
        if kind == "minecraft:player":
            render.SetPlayerItemInHandVisible(False)
            result = render.RebuildPlayerRender()
        else:
            result = render.RebuildRenderForOneActor()
        if result:
            self.applied[entity_id] = (kind, changed)


# endregion
