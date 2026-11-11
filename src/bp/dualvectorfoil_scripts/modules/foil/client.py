# -*- coding: utf-8 -*-
# =================================================
#  ⠀
#   Author: Nuoyan <https://github.com/charminglee>
#   Email : 1279735247@qq.com
#   Date  : 2026-11-11
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

    仅消费服务端同步的二维化标记并替换几何；位置、重力与实体持久化由
    服务端维护。AOI 事件记录增量，周期性全量补齐用于恢复重载或事件遗漏。
    """

    def __init__(self, namespace, system_name):
        super(FoilClient, self).__init__(namespace, system_name)
        # 维护 AOI 实体和已安装模型
        self.tracked = set()
        self.applied = {}
        self.tick = 0

    def AddEntityClientEvent(self, args):
        """
        把进入客户端 AOI 的实体加入跟踪集合。
        """
        # 新实体进入 AOI 后等待下一次批量安装
        self.tracked.add(args.id)

    def RemoveEntityClientEvent(self, args):
        """
        移除已离开客户端 AOI 的实体状态。
        """
        # 实体离开 AOI 时同步清理本地缓存
        self._forget(args.id)

    def OnScriptTickClient(self, args):
        """
        定期补齐实体跟踪并安装二维模型。
        """
        # 每十个客户端脚本 tick 批量同步一次，把渲染器查询和重建移出逐 tick 热路径
        self.tick += 1
        if self.tick % 10:
            return

        # 补齐系统注册前已进入 AOI 的实体，兼容脚本重新加载
        live = client_api.GetEngineActor().keys()
        self.tracked.intersection_update(live)
        self.tracked.update(live)

        # 删除已经离开 AOI 的模型安装记录。
        for entity_id in self.applied:
            if entity_id not in live:
                self.applied.pop(entity_id)

        # applied 仅在重建成功后写入
        # 属性或渲染参数尚未就绪的实体保持未安装，下一轮会自动重试，避免 AOI 进入早于属性复制时永久漏掉二维表现
        for entity_id in self.tracked:
            if entity_id not in self.applied:
                self._apply(entity_id)

    def _forget(self, entity_id):
        """
        清理指定实体的本地跟踪和安装记录。
        """
        # 缓存按实体编号独立清理
        self.tracked.discard(entity_id)
        self.applied.pop(entity_id, None)

    def _apply(self, entity_id):
        """
        按实体类型和渲染键替换为预生成的二维几何。

        ENTITY_GEOMETRIES 先将实体类型、渲染层键对应到原几何，GEOMETRIES
        再将原几何对应到离线生成的平面模型；这里不实时压缩顶点或改动贴图。
        """
        # 玩家不参与模型替换
        cf = nyl.CF(entity_id)
        if cf.EngineType.GetEngineTypeStr() == "minecraft:player":
            return
        # 只有服务端已标记为二维化的非玩家实体才替换几何
        data = cf.ModAttr.GetAttr(Attr.FLAT)
        if not data:
            return
        # 根据实体类型选择生成的渲染键目录
        kind = data['kind']
        if kind == "minecraft:player":
            return
        if kind not in ENTITY_GEOMETRIES or not ENTITY_GEOMETRIES[kind]:
            return
        render = cf.ActorRender
        catalog = dict(ENTITY_GEOMETRIES[kind])

        # 实际渲染键与预生成目录取交集，只替换当前存在的层；保留原键名，让既有渲染控制器继续通过相同的键选取几何
        keys = render.GetActorRenderParams(entity_id, "geometry")
        if not keys:
            return
        changed = {}
        for key, original in catalog.items():
            if key not in keys:
                continue

            # 二维几何目录使用原始模型名作为索引
            geometry = GEOMETRIES[original]
            ok = render.AddGeometryToOneActor(entity_id, key, geometry)
            if not ok:
                return
            changed[key] = original
        if not changed:
            return

        # 只重建受影响的非玩家Actor
        result = render.RebuildRenderForOneActor()
        if result:
            self.applied[entity_id] = (kind, changed)


# endregion
