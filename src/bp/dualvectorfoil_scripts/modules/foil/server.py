# -*- coding: utf-8 -*-
# =================================================
#  ⠀
#   Author: Nuoyan <https://github.com/charminglee>
#   Email : 1279735247@qq.com
#   Date  : 2026-11-12
#  ⠀
# =================================================


from copy import deepcopy
from math import floor
from time import time
from uuid import uuid4
import mod.server.extraServerApi as server_api
from mod.common.minecraftEnum import GameType, ItemPosType
from ...nuoyanlib import server as nyl
from ...common.constant import *
from ...common.config import *
from ...common.diagnostics import get_log
from .._base.server import BaseServer
from .config import *
from .palette import PaletteContacts, palette_regions, plan_palette, slice_batch, source_at, world_position
from .deferred import PendingMoves, reference_batch, reference_positions, scan_references


client_event = nyl.event(sys_name=CLIENT_SYSTEM_NAME)
server_event = nyl.event(sys_name=SERVER_SYSTEM_NAME)


# region 有符号格点到二维 Morton 平面坐标 ==================================================


def zigzag(value):
    """
    把有符号整数无损映射为非负整数：0、-1、1、-2、2 对应 0、1、2、3、4。

    正负坐标分别占用偶数和奇数，不依赖固定字长，供后续位交织使用。
    """
    return value * 2 if value >= 0 else -value * 2 - 1


def unzigzag(value):
    """
    把 ZigZag 无符号整数还原为有符号整数。
    """
    return value // 2 if value % 2 == 0 else -(value // 2) - 1


def interleave(values):
    """
    按位交织多个整数。
    """
    # 第 axis 个分量的第 bit 位放在 bit*width+axis，类似拉链轮流取各轴位。
    # 每个输入位都有唯一位置，deinterleave 可以完全拆回，不会丢失坐标信息。
    values = list(values)
    width = len(values)
    code, bit = 0, 0
    while any(values):
        for axis in range(width):
            code |= (values[axis] & 1) << (bit * width + axis)
            values[axis] >>= 1
        bit += 1
    return code


def deinterleave(code, width):
    """
    从交织整数中拆出指定数量的原始分量。
    """
    # 按编码位轮转拆回各轴。
    values = [0] * width
    bit = 0
    while code:
        values[bit % width] |= (code & 1) << (bit // width)
        code >>= 1
        bit += 1
    return values


def flatten(pos, origin):
    """
    把三维格点一一映射到 origin 高度的二维整数平面。

    三轴相对坐标先 ZigZag，再按三路交织成整数，随后按两路拆分为 u、v。
    这里重新分配坐标位，而非直接丢弃高度，因此不同源格点不会映射重合；
    映射可逆，但不保证保持原物体的欧氏距离、形状或相邻关系。
    """
    # 先把三个相对坐标转为非负值，再压缩为二维坐标。
    local = [zigzag(pos[i] - origin[i]) for i in range(3)]
    u, v = deinterleave(interleave(local), 2)
    return (origin[0] + unzigzag(u), origin[1], origin[2] + unzigzag(v))


def unflatten(pos, origin):
    """
    使用同一个 origin 逆转 flatten 的两路/三路位分配。

    只读取输出平面的 X、Z；调用方应传入由 flatten 产生的平面格点。
    """
    # 从二维平面取出交织值，并恢复三个相对坐标。
    uv = [zigzag(pos[0] - origin[0]), zigzag(pos[2] - origin[2])]
    xyz = deinterleave(interleave(uv), 3)
    return tuple(origin[i] + unzigzag(xyz[i]) for i in range(3))


# endregion


# region 调色板读取、应用和区块加载 ==================================================


def entity_contact_candidates(pos):
    """
    返回脚底紧邻下方与脚底格点，避免把站在物体上的实体漏掉。
    """
    # floor 对负坐标向下取整，避免 int 截断到零而误选邻格；向下偏移 0.01
    # 用于脚底恰好在整数高度时找到支撑方块，同时保留脚底所在格点。
    x, z = int(floor(pos[0])), int(floor(pos[2]))
    foot_y = int(floor(pos[1]))
    support_y = int(floor(pos[1] - 0.01))
    result = [(x, support_y, z)]
    foot = (x, foot_y, z)
    if foot != result[0]:
        result.append(foot)
    return result


def relocate_nbt(data, pos):
    """
    复制方块实体 NBT 并重定位坐标。
    """
    data = deepcopy(data)
    for axis, name in enumerate(("x", "y", "z")):
        if name not in data:
            continue
        if isinstance(data[name], dict) and '__value__' in data[name]:
            data[name]['__value__'] = pos[axis]
        else:
            data[name] = pos[axis]
    return data


class WorldAdapter(object):
    """
    批量读取和写入调色板，只对方块实体补充完整 NBT。
    """

    def __init__(self, dimension):
        self.dimension = dimension
        self.blocks = nyl.LvComp.Block
        self.info = nyl.LvComp.BlockInfo
        self.chunks = nyl.LvComp.ChunkSource
        self.status = "ready"
        self.last_error = None

    def capture(self, start, end):
        """
        一次获取区域调色板；保留空气以区分合法空区域与接口失败。
        """
        palette = self.blocks.GetBlockPaletteBetweenPos(self.dimension, start, end, False)
        return palette.SerializeBlockPalette() if palette else None

    def is_loaded(self, pos):
        """
        仅检查实际格点所属区块，不申请常加载或等待其他区块。
        """
        return self.chunks.CheckChunkState(self.dimension, tuple(pos))

    def capture_nbt(self, state):
        """
        调色板 actor 仅含描述，完整容器 NBT 在计划建立时一次补齐。
        """
        data = state['source_palette']
        result = {}
        actor_indices = set(index for actors in data['actor'].values() for index in actors)
        targets = dict(
            (source, target) for block in state['groups']
            for source, target in zip(data['common'][block], state['target_palette']['common'][block])
            if source in actor_indices
        ) if actor_indices else {}
        for actors in data['actor'].values():
            for index in actors:
                pos = world_position(index, data['volume'], state['source_start'])
                nbt = self.info.GetBlockEntityData(self.dimension, pos)
                if nbt:
                    result[targets[index]] = nbt
        return result

    def apply(self, data, start):
        """
        按实际分区写入本批格点，失败校验最多读取 16 格边长的局部范围。
        """
        self.last_error = None
        started, regions = time(), 0
        for region, region_start in palette_regions(data, start):
            regions += 1
            if not self._apply_region(region, region_start):
                get_log(self, "foil.server.world").sample(
                    "write_failed", signature=self.last_error, level="ERROR",
                    dimension=self.dimension, region_start=region_start, volume=region['volume'],
                    regions=regions, error=self.last_error, duration_ms=round((time() - started) * 1000, 3),
                )
                return False
        if regions:
            get_log(self, "foil.server.world").sample(
                "write_batch", dimension=self.dimension, regions=regions,
                duration_ms=round((time() - started) * 1000, 3),
            )
        return True

    def _apply_region(self, data, start):
        """
        写入紧凑局部调色板，保留接口失败后的严格幂等校验。
        """
        palette = self.blocks.GetBlankBlockPalette()
        if not palette.DeserializeBlockPalette(data):
            self.status = "palette_decode_failed"
            self.last_error = {'reason': "decode_failed", 'start': start, 'volume': data['volume']}
            return False
        if not self.blocks.SetBlockByBlockPalette(palette, self.dimension, tuple(start), 0, 0):
            if not self._matches(data, start):
                self.status = "palette_write_failed"
                return False
            get_log(self, "foil.server.world").sample(
                "write_verified", dimension=self.dimension, start=start, volume=data['volume'],
            )
        return True

    def _matches(self, data, start):
        """
        SDK 对全部同名格点可能返回 False；仅对当前局部分区读回校验。
        """
        width, length, height = data['volume']
        end = (start[0] + length - 1, start[1] + height - 1, start[2] + width - 1)
        actual = self.capture(tuple(start), end)
        if actual is None:
            self.last_error = {'reason': "readback_failed", 'start': start, 'volume': data['volume']}
            return False
        for layer, states in (('common', 'states'), ('extra', 'extraStates')):
            if not self._matches_layer(data, actual, start, layer, states):
                return False
        return True

    def _matches_layer(self, data, actual, start, layer, states):
        """
        核对单层格点及状态，记录首个不匹配位置供 MCDK 诊断。
        """
        for block, positions in data[layer].items():
            if not positions:
                continue
            pos = world_position(positions[0], data['volume'], start)
            if block not in actual[layer]:
                self.last_error = {
                    'reason': "missing_block", 'layer': layer,
                    'expected': block, 'pos': pos,
                    'actual': [key for key, values in actual[layer].items() if positions[0] in values],
                }
                return False
            actual_state = actual[states][block] if block in actual[states] else None
            if block in data[states] and actual_state != data[states][block]:
                self.last_error = {
                    'reason': "state_mismatch", 'layer': layer, 'pos': pos,
                    'expected': data[states][block], 'actual': actual_state,
                }
                return False
            available = set(actual[layer][block])
            for index in positions:
                if index not in available:
                    self.last_error = {
                        'reason': "position_mismatch", 'layer': layer, 'expected': block,
                        'pos': world_position(index, data['volume'], start),
                        'actual': [key for key, values in actual[layer].items() if index in values],
                    }
                    return False
        return True

    def move(self, state, batch):
        """
        批量放置目标、恢复容器 NBT 后清源，失败时不推进游标。
        """
        if not self.apply(batch['output'], state['target_start']):
            return False
        for positions in batch['output']['common'].values():
            for index in positions:
                if index not in state['nbt']:
                    continue
                pos = world_position(index, batch['output']['volume'], state['target_start'])
                if not self.info.SetBlockEntityData(self.dimension, pos, relocate_nbt(state['nbt'][index], pos)):
                    self.status = "nbt_failed"
                    self.last_error = {'reason': "nbt_failed", 'pos': pos}
                    get_log(self, "foil.server.world").sample(
                        "nbt_failed", signature=pos, level="ERROR", dimension=self.dimension, pos=pos,
                    )
                    return False
        return self.apply(batch['clear'], state['source_start'])


# endregion


# region 对 effect 模块发布的精简流程事件 ==================================================


def build_field_event(dimension, state, tick):
    """
    构造二向箔本地广播使用的精简只读事件载荷。
    """
    # 只读取当前调色板分组游标，不复制大规模方块清单。
    count = state['block_count']
    cursor = state['move_cursor']
    source = state['active_source'] if 'active_source' in state else source_at(state) if count else None
    return {
        'dimension': dimension,
        'run_id': state.get('run_id', 0),
        'phase': state['phase'],
        'tick': tick,
        'origin': tuple(state['origin']),
        'source': source,
        'processed_count': state['moved'] if 'moved' in state else cursor,
        'block_count': count,
    }


# endregion


# region 接触物体的实体二维化状态 ==================================================


class FlatEntities(object):
    """
    扫描接触目标物体的实体并维持二维化冻结状态。

    服务端只负责接触判定、持久化目标和物理约束，通过 ModAttr 同步标记；
    客户端根据该标记安装预生成几何。玩家不参与处理。
    """

    def __init__(self):
        self.active = {}

    def scan(self, fields, object_sets):
        """
        清理失效实体并扫描当前接触目标物体的实体。
        """
        # 先清理已销毁实体，避免缓存无界增长。
        live = set(nyl.get_all_entities())
        for entity_id in list(self.active):
            if entity_id not in live:
                self.active.pop(entity_id)
        # 再尝试捕获当前仍存活但尚未标记的实体。
        for entity_id in live:
            self._visit(entity_id, fields, object_sets)

    def _visit(self, entity_id, fields, object_sets):
        """
        判断单个实体是否应进入二维化状态并保存其标记。
        """
        # 玩家不参与二维化。
        cf = nyl.CF(entity_id)
        kind = cf.EngineType.GetEngineTypeStr()
        if kind == "minecraft:player":
            return
        # 已处理的非玩家实体无需重复扫描。
        if entity_id in self.active:
            return

        # 优先恢复非玩家实体持久化的二维化标记，兼容脚本重载。
        saved = cf.ExtraData.GetExtraData(Attr.FLAT)
        if saved:
            self.active[entity_id] = saved
            cf.ModAttr.SetAttr(Attr.FLAT, saved)
            cf.ControlAi.SetBlockControlAi(False, True)
            get_log(self, "foil.server.entities").sample(
                "restored", entity_id=entity_id, kind=kind, run_id=saved.get('run_id'), active=len(self.active),
            )
            return

        # 投射物和未生成二维目录的实体不参与捕获。
        if kind == EntityId.FOIL_PROJECTILE or kind not in ENTITY_GEOMETRIES:
            return
        # 只使用当前维度已捕获的调色板索引。
        dimension = cf.Dimension.GetEntityDimensionId()
        key = str(dimension)
        if key not in fields or key not in object_sets:
            return
        state = fields[key]
        object_keys = object_sets[key]
        pos = cf.Pos.GetFootPos()
        if not state or not object_keys or not pos:
            return

        # 可选实体上限按当前任务分别计数。
        if MAX_FOIL_ENTITIES >= 0:
            captured = sum(
                1
                for data in self.active.values()
                if data.get('dimension') == dimension and data.get('run_id', 0) == state.get('run_id', 0)
            )
            if captured >= MAX_FOIL_ENTITIES:
                return
        # 使用原调色板的格点索引做成员查询，无须为每个实体遍历所有方块。
        # 这是脚底/支撑点接触判定，不是实体碰撞箱与整个物体的精确相交测试。
        block_pos = next(
            (
                candidate
                for candidate in entity_contact_candidates(pos)
                if candidate in object_keys
            ),
            None,
        )
        if not block_pos:
            return
        # 保存二维目标位置、类型、维度和任务标识。
        target = flatten(block_pos, state['origin'])
        saved = {
            'pos': (target[0] + 0.5, target[1] + 1.02, target[2] + 0.5),
            'kind': kind,
            'dimension': dimension,
            'run_id': state.get('run_id', 0),
        }
        if not cf.ExtraData.SetExtraData(Attr.FLAT, saved):
            get_log(self, "foil.server.entities").sample(
                "persist_failed", level="ERROR", entity_id=entity_id, run_id=saved['run_id'],
            )
            return
        # 同步内存、属性复制和持久化标记，非玩家实体同时关闭 AI。
        self.active[entity_id] = saved
        cf.ModAttr.SetAttr(Attr.FLAT, saved)
        cf.Attr.SetPersistent(True)
        cf.ControlAi.SetBlockControlAi(False, True)
        self._hold(entity_id, saved)
        get_log(self, "foil.server.entities").sample(
            "captured", entity_id=entity_id, kind=kind, dimension=dimension,
            run_id=saved['run_id'], target=saved['pos'], active=len(self.active),
        )

    def hold(self):
        """
        约束所有二维化实体的重力、速度和位置。
        """
        # 每 tick 约束全部二维化实体，防止重力或外力改变位置。
        for entity_id, data in list(self.active.items()):
            self._hold(entity_id, data)
        if self.active:
            get_log(self, "foil.server.entities").sample("holding", active=len(self.active))

    def _hold(self, entity_id, data):
        """
        把单个二维化实体固定在输出平面位置。
        """
        cf = nyl.CF(entity_id)
        # 实体切换维度后跳过，避免把旧位置写入错误世界。
        if cf.Dimension.GetEntityDimensionId() != data['dimension']:
            return
        # SDK 的 0 表示回退世界重力，不能拿它表示零重力；极小负值减小下落，
        # 再每 tick 清速度并回写脚底位置，抵消 AI 之外的重力或外部推动。
        cf.Gravity.SetGravity(-0.000001)
        nyl.set_motion(entity_id, (0.0, 0.0, 0.0))
        cf.Pos.SetFootPos(tuple(data['pos']))

    def remove(self, entity_id):
        """
        移除已销毁实体的二维化缓存。
        """
        removed = self.active.pop(entity_id, None)
        if removed:
            get_log(self, "foil.server.entities").sample("removed", entity_id=entity_id, active=len(self.active))


# endregion


# region 系统入口 ==================================================


class FoilServer(BaseServer):
    """
    调度投射物和 capturing -> moving -> complete 的持久化任务。

    每维度只保留一个活动任务；重载时恢复调色板计划和分组游标。
    """

    def __init__(self, namespace, system_name):
        super(FoilServer, self).__init__(namespace, system_name)
        # 加载持久化任务并按维度建立运行期索引。
        self.extra = nyl.LvComp.ExtraData
        self.fields = self.extra.GetExtraData(Data.WORLD_V3) or {}
        self.worlds = {}
        self.target_sets = {}
        self.object_sets = {}
        self.projectiles, self.cooldowns = {}, {}
        self.entities = FlatEntities()
        self.tick = 0
        get_log(self, "foil.server").event(
            "init", fields=len(self.fields), radius=FOIL_FALL_RADIUS, budget=FOIL_BLOCKS_PER_TICK,
        )
        # 恢复未完成任务并重新发布正在搬移的状态。
        for key, state in self.fields.items():
            dimension = int(key)
            get_log(self, "foil.server").event(
                "restore_field", dimension=dimension, run_id=state.get('run_id'),
                phase=state.get('phase'), status=state.get('status'),
                moved=state.get('moved'), count=state.get('block_count'),
            )
            self._sync_object_set(dimension, state)
            if state.get('phase') != "complete":
                self._attach(dimension)
            if state.get('phase') == "moving":
                self._broadcast_field_state(dimension, state)

    def _attach(self, dimension):
        """
        为指定维度建立世界适配器和调色板计划。
        """
        # 同一维度只保留一套世界适配器。
        if dimension in self.worlds:
            return
        self.worlds[dimension] = WorldAdapter(dimension)
        state = self.fields[str(dimension)]
        if 'target_palette' in state:
            self.target_sets[str(dimension)] = PaletteContacts(state, target=True)

    def _detach(self, dimension):
        """
        释放任务的世界适配器、目标索引和搬移队列。
        """
        self.worlds.pop(dimension, None)
        self.target_sets.pop(str(dimension), None)
        if hasattr(self, '_move_queues'):
            self._move_queues.pop(dimension, None)
        if hasattr(self, '_move_budgets'):
            self._move_budgets.pop(dimension, None)

    def _sync_object_set(self, dimension, state):
        """
        已建立快照时使用紧凑调色板索引进行实体接触判定。
        """
        if 'source_palette' in state:
            self.object_sets[str(dimension)] = PaletteContacts(state)

    def ServerItemTryUseEvent(self, args):
        """
        拦截二向箔右键使用并尝试发射。
        """
        # 只拦截手持二向箔的事件。
        item = args.itemDict or {}
        if 'newItemName' not in item or item['newItemName'] != ItemId.FOIL:
            return
        # 取消原生使用并进入统一发射流程。
        args.cancel = True
        self._launch(args.playerId)

    def ServerItemUseOnEvent(self, args):
        """
        对方块使用二向箔时取消原生交互并尝试发射。
        """
        # 只拦截对方块使用二向箔的事件。
        item = args.itemDict or {}
        if 'newItemName' not in item or item['newItemName'] != ItemId.FOIL:
            return
        # 阻止原生交互后进入统一发射流程。
        args.ret = True
        self._launch(args.entityId)

    def _field_active(self, dimension):
        """
        判断指定维度是否存在尚未完成的二向箔任务。
        """
        key = str(dimension)
        if key not in self.fields:
            return False
        return self.fields[key].get('phase') != "complete"

    def _projectile_active(self, dimension):
        """
        判断指定维度是否存在飞行或静止等待中的二向箔实体。
        """
        return any(shot.get('dimension') == dimension for shot in self.projectiles.values())

    def _launch(self, player_id):
        """
        校验玩家、维度和物品状态后创建二向箔投射物。
        """
        # 先检查玩家冷却，避免重复创建实体。
        if self.tick < self.cooldowns.get(player_id, 0):
            get_log(self, "foil.server").sample("launch_rejected", reason="cooldown", player_id=player_id)
            return
        # 无效飞行配置不创建实体，也不扣除物品。
        if FOIL_FLIGHT_DISTANCE <= 0 or FOIL_FLIGHT_SECONDS <= 0:
            get_log(self, "foil.server").sample("launch_rejected", level="ERROR", reason="flight_config")
            self._message(player_id, "二向箔飞行距离和减速时长必须大于 0。")
            return
        if FOIL_FALL_RADIUS < 0 or (FOIL_BLOCKS_PER_TICK != -1 and FOIL_BLOCKS_PER_TICK <= 0):
            get_log(self, "foil.server").sample("launch_rejected", level="ERROR", reason="fall_config")
            self._message(player_id, "跌落半径不能为负数，每帧方块数必须为正数或 -1。")
            return

        # 获取玩家所在维度。
        cf = nyl.CF(player_id)
        dimension = cf.Dimension.GetEntityDimensionId()
        # 同一维度只允许一个尚未完成的任务。
        if self._field_active(dimension):
            get_log(self, "foil.server").sample("launch_rejected", reason="active_field", dimension=dimension)
            self._message(player_id, "这个维度已经在二维化；输入 !foil 可查看进度。")
            return
        # 同一维度只允许一个飞行或静止等待中的投射物。
        if self._projectile_active(dimension):
            get_log(self, "foil.server").sample("launch_rejected", reason="active_projectile", dimension=dimension)
            return

        # 校验手持物品和数量信息。
        item = cf.Item.GetPlayerItem(ItemPosType.CARRIED)
        if not item or 'newItemName' not in item or item['newItemName'] != ItemId.FOIL:
            get_log(self, "foil.server").sample("launch_rejected", reason="item", player_id=player_id)
            return
        # 位置或朝向不可用时取消发射。
        pos, rot = cf.Pos.GetPos(), cf.Rot.GetRot()
        if not pos or not rot:
            get_log(self, "foil.server").sample("launch_rejected", level="WARNING", reason="position_or_rotation", player_id=player_id)
            return
        # 从朝向构造前向出生点和配置距离对应的轨迹终点。
        direction = server_api.GetDirFromRot(rot)
        spawn = tuple(pos[i] + direction[i] * 1.5 for i in range(3))
        target = tuple(spawn[i] + direction[i] * FOIL_FLIGHT_DISTANCE for i in range(3))
        entity_id = nyl.LvComp.Projectile.CreateProjectileEntity(
            player_id,
            EntityId.FOIL_PROJECTILE,
            {
                'position': spawn,
                'direction': direction,
                'power': 0.0,
                'gravity': 0.0,
                'damage': 0.0,
            },
        )
        if not entity_id or entity_id == "-1":
            get_log(self, "foil.server").sample("launch_failed", level="ERROR", reason="create_projectile", player_id=player_id)
            return
        # out_quad 的归一化位移为 1-(1-t)^2，速度随 t 线性减小，到终点为零。
        # 轨迹运动负责位移，投射物初始动力和重力均置零；碰撞回调取消原生
        # 命中处理，避免途中触发，停止后的等待则由实际运动完成事件启动。
        motion = nyl.CF(entity_id).ActorMotion
        motion_id = motion.AddEntityTrackMotion(
            target,
            FOIL_FLIGHT_SECONDS,
            startPos=spawn,
            ease=server_api.GetMinecraftEnum().TimeEaseType.out_quad,
        )
        if motion_id == -1 or not motion.StartEntityMotion(motion_id):
            get_log(self, "foil.server").event("launch_failed", level="ERROR", reason="track_motion", entity_id=entity_id, motion_id=motion_id)
            self.DestroyEntity(entity_id)
            return
        # 生存模式消耗一枚；扣减失败时销毁刚创建的投射物。
        if nyl.LvComp.Game.GetPlayerGameType(player_id) != GameType.Creative:
            if not cf.Item.SetInvItemNum(cf.Item.GetSelectSlotId(), item['count'] - 1):
                get_log(self, "foil.server").event("launch_failed", level="ERROR", reason="consume_item", entity_id=entity_id)
                self.DestroyEntity(entity_id)
                return
        # 只记录运动器和发起玩家；六秒倒计时在轨迹完成后开始。
        self.projectiles[entity_id] = {
            'dimension': dimension,
            'motion_id': motion_id,
            'playerId': player_id,
        }
        self.cooldowns[player_id] = self.tick + LAUNCH_COOLDOWN
        get_log(self, "foil.server").event(
            "launched", player_id=player_id, entity_id=entity_id, dimension=dimension,
            motion_id=motion_id, spawn=spawn, target=target, flight_seconds=FOIL_FLIGHT_SECONDS,
        )
        self._message(player_id, "二向箔已发射，减速静止六秒后开始维度跌落。")

    def _message(self, player_id, message):
        """
        向发起二向箔的玩家发送状态消息。
        """
        # 未绑定玩家的旧存档不发送消息。
        if player_id:
            nyl.CF(player_id).Msg.NotifyOneMessage(player_id, message)

    def ProjectileDoHitEffectEvent(self, args):
        """
        取消二向箔的原生碰撞，避免穿行时提前展开或移除。
        """
        # 只处理本系统创建并仍记录中的投射物。
        entity_id = args.id
        if entity_id not in self.projectiles:
            return
        args.cancel = True

    def EntityMotionStopServerEvent(self, args):
        """
        二向箔轨迹顺利完成后固定实际位置并开始六秒倒计时。
        """
        # 只响应当前二向箔的轨迹完成事件，重复事件不能重置计时。
        entity_id = args.entityId
        if entity_id not in self.projectiles:
            return
        shot = self.projectiles[entity_id]
        if args.motionId != shot['motion_id'] or 'deadline' in shot:
            return
        # 清除残余速度并保存实际静止位置，后续不再跟随碰撞落点。
        cf = nyl.CF(entity_id)
        pos = cf.Pos.GetPos()
        if not pos or not cf.ActorMotion.SetMotion((0.0, 0.0, 0.0)):
            get_log(self, "foil.server").event("settle_failed", level="ERROR", entity_id=entity_id, pos=pos)
            self.projectiles.pop(entity_id)
            self.DestroyEntity(entity_id)
            return
        shot['stop_pos'] = tuple(pos)
        shot['deadline'] = self.tick + SETTLE_TICKS
        get_log(self, "foil.server").event("settled", entity_id=entity_id, pos=pos, deadline_tick=shot['deadline'])

    def _detonate(self, entity_id, pos):
        """
        根据二向箔静止位置建立新的二维化任务。
        """
        # 先移出飞行表并销毁实体，防止重复引爆。
        shot = self.projectiles.pop(entity_id)
        dimension = shot['dimension']
        player_id = shot.get('playerId')
        self.DestroyEntity(entity_id)
        # 等待期间已有任务时只完成本次投射物清理。
        if self._field_active(dimension):
            get_log(self, "foil.server").event("detonate_skipped", reason="active_field", dimension=dimension)
            return

        # 静止位置所在格点作为球心，空气球心同样处理半径内方块。
        anchor = [int(floor(p)) for p in pos]
        # 输出平面直接使用静止格点高度。
        state = {
            'run_id': uuid4().hex,
            'origin': list(anchor),
            'anchor': anchor,
            'phase': "capturing",
            'radius': FOIL_FALL_RADIUS,
            'block_count': 0,
            'move_cursor': 0,
            'moved': 0,
            'status': "capturing",
            'playerId': player_id,
        }
        self.object_sets.pop(str(dimension), None)
        self.fields[str(dimension)] = state
        get_log(self, "foil.server").event(
            "field_created", run_id=state['run_id'], dimension=dimension, anchor=anchor,
            origin=state['origin'], radius=state['radius'], entity_id=entity_id, player_id=player_id,
        )
        self._sync_object_set(dimension, state)
        self._attach(dimension)
        # 保存初始任务，随后一次读取球形包围盒并建立映射。
        self._save()
        self._process_field(dimension, state)

    def OnScriptTickServer(self, args):
        """
        推进投射物、调色板捕获、逐帧应用和实体约束。
        """
        # 先推进投射物和已有任务。
        self.tick += 1
        self._update_projectiles()
        for key, state in list(self.fields.items()):
            self._process_field(int(key), state)
            if state.get('phase') == "moving":
                self._broadcast_field_state(int(key), state)
        # 实体扫描按低频间隔执行，位置约束每 tick 执行。
        if self.tick % ENTITY_INTERVAL == 0:
            self.entities.scan(self.fields, self.object_sets)
        self.entities.hold()

        # 定期保存调色板计划和分组游标。
        if self.tick % SAVE_INTERVAL == 0:
            self._save()

    def _update_projectiles(self):
        """
        等待轨迹完成，并在静止六秒后从固定位置展开。
        """
        # 复制键列表，允许循环内销毁并移除投射物。
        for entity_id, shot in list(self.projectiles.items()):
            cf = nyl.CF(entity_id)
            pos = cf.Pos.GetPos()
            # 实体失效只释放当前维度槽位，不能提前触发维度跌落。
            if not pos:
                get_log(self, "foil.server").event("projectile_lost", level="WARNING", entity_id=entity_id)
                self.projectiles.pop(entity_id)
                continue
            if 'deadline' not in shot:
                continue
            # 静止等待时保持原位置，避免外力改变球形处理范围。
            if tuple(pos) != shot['stop_pos'] and not cf.Pos.SetPos(shot['stop_pos']):
                get_log(self, "foil.server").sample("projectile_hold_failed", level="ERROR", entity_id=entity_id, target=shot['stop_pos'])
                continue
            if self.tick >= shot['deadline']:
                self._detonate(entity_id, shot['stop_pos'])

    def _process_field(self, dimension, state):
        """
        调度任务并限频记录状态、进度、失败明细和本次调度耗时。
        """
        if state['phase'] == "complete":
            return
        started = time()
        result = self._advance_field(dimension, state)
        world = self.worlds[dimension] if dimension in self.worlds else None
        status = state['status']
        error = getattr(world, 'last_error', None) if "fail" in status else None
        level = "ERROR" if "fail" in status or status == "invalid_config" else "INFO"
        get_log(self, "foil.server").sample(
            "field_state", key="field:%s" % dimension,
            signature=(state.get('run_id'), state['phase'], status, error), level=level,
            dimension=dimension, run_id=state.get('run_id'), phase=state['phase'], status=status,
            moved=state['moved'], count=state['block_count'], error=error,
            scanned=state['move_cursor'], pending=len(state.get('pending_moves', {})),
            duration_ms=round((time() - started) * 1000, 3),
        )
        return result

    def _advance_field(self, dimension, state):
        """
        一次建立球形调色板映射，后续 tick 仅应用预计算切片。
        """
        if state['phase'] == "complete":
            return
        if state['radius'] < 0 or (FOIL_BLOCKS_PER_TICK != -1 and FOIL_BLOCKS_PER_TICK <= 0):
            state['status'] = "invalid_config"
            return
        self._attach(dimension)
        world = self.worlds[dimension]
        if state['phase'] == "capturing":
            center, radius = state['anchor'], int(floor(state['radius']))
            # 不预裁剪坐标范围，球内方块以调色板实际返回的数据为准。
            start = tuple(value - radius for value in center)
            end = tuple(value + radius for value in center)
            started = time()
            get_log(self, "foil.server").sample(
                "capture_started", signature=(state.get('run_id'), start, end),
                run_id=state.get('run_id'), dimension=dimension, start=start, end=end,
            )
            data = world.capture(start, end)
            get_log(self, "foil.server").sample(
                "capture", signature=(state.get('run_id'), data is not None),
                level="INFO" if data is not None else "ERROR",
                run_id=state.get('run_id'), dimension=dimension, start=start, end=end,
                ok=data is not None, duration_ms=round((time() - started) * 1000, 3),
            )
            if data is None:
                state['status'] = "palette_read_failed"
                return
            started = time()
            get_log(self, "foil.server").event("plan_started", run_id=state.get('run_id'), dimension=dimension)
            plan = plan_palette(data, start, center, state['origin'], state['radius'], flatten)
            get_log(self, "foil.server").event(
                "plan", run_id=state.get('run_id'), dimension=dimension,
                count=plan['block_count'], duration_ms=round((time() - started) * 1000, 3),
            )
            state.update(plan)
            if not state['block_count']:
                self._finish_field(dimension, state, "no_blocks", "跌落半径内没有可处理方块。")
                return
            started = time()
            state['nbt'] = world.capture_nbt(state)
            get_log(self, "foil.server").event(
                "capture_nbt", run_id=state.get('run_id'), count=len(state['nbt']),
                duration_ms=round((time() - started) * 1000, 3),
            )
            state['phase'] = "moving"
            state['status'] = "moving"
            self._sync_object_set(dimension, state)
            self.target_sets[str(dimension)] = PaletteContacts(state, target=True)
            if not self._save():
                state['status'] = "waiting_io"
                state['plan_saved'] = False
                return
            state['plan_saved'] = True
            self._broadcast_field_state(dimension, state)
            self._message(state.get('playerId'), "已获取球形调色板，共 %d 个方块。" % state['block_count'])
            # 普通模式从下一帧开始；-1 在同次调用完成全部世界写入。
            if FOIL_BLOCKS_PER_TICK != -1:
                return
        if not state.get('plan_saved'):
            if not self._save():
                state['status'] = "waiting_io"
                return
            state['plan_saved'] = True
        queue = self._move_queue(dimension, state)
        for reference in scan_references(state, FOIL_BLOCKS_PER_TICK):
            queue.add(state, reference)
        self._drain_moves(dimension, state, queue)

    def _move_queue(self, dimension, state):
        """
        重建待处理索引一次，兼容旧任务游标及持久化恢复后的已加载区块。
        """
        if not hasattr(self, '_move_queues'):
            self._move_queues = {}
        queue = self._move_queues[dimension] if dimension in self._move_queues else None
        if queue is None or queue.entries is not state.get('pending_moves'):
            queue = PendingMoves(state)
            self._move_queues[dimension] = queue
        return queue

    def _drain_moves(self, dimension, state, queue):
        """
        应用当前已就绪引用；未加载项登记依赖，真实写入失败项保留重试。
        """
        world = self.worlds[dimension]
        limit = len(queue.ready) if FOIL_BLOCKS_PER_TICK == -1 else min(len(queue.ready), FOIL_BLOCKS_PER_TICK)
        # 加载事件与普通 tick 共用预算，避免多个加载回调在同帧集中写入。
        if FOIL_BLOCKS_PER_TICK != -1 and hasattr(self, 'tick'):
            if not hasattr(self, '_move_budgets'):
                self._move_budgets = {}
            previous_tick, used = self._move_budgets.get(dimension, (self.tick, 0))
            if previous_tick != self.tick:
                used = 0
            limit = max(0, min(limit, FOIL_BLOCKS_PER_TICK - used))
            self._move_budgets[dimension] = (self.tick, used + limit)
        ready, loaded = [], {}
        for unused in range(limit):
            token, reference = queue.pop()
            missing = self._missing_chunks(world, state, reference, loaded)
            if missing:
                queue.wait(token, missing)
            else:
                ready.append((token, reference))
        if ready:
            references = [reference for token, reference in ready]
            batch = reference_batch(state, references, self.target_sets[str(dimension)])
            if not world.move(state, batch):
                for token, reference in ready:
                    queue.retry(token)
                state['status'] = world.status
                return
            for token, reference in ready:
                queue.complete(token)
            state['moved'] += len(ready)
            state['active_source'] = reference_positions(state, references[-1])[0]
        if state['move_cursor'] == state['block_count'] and not queue.entries:
            self._finish_field(dimension, state, "complete", "二向箔二维化完成。")
            return
        state['status'] = "moving" if state['move_cursor'] < state['block_count'] or queue.ready else "waiting_chunks"

    def _missing_chunks(self, world, state, reference, loaded):
        """
        同一调度内缓存源和目标区块检查，只检查实际涉及的区块。
        """
        missing = set()
        for pos in reference_positions(state, reference):
            chunk = (pos[0] // 16, pos[2] // 16)
            if chunk not in loaded:
                loaded[chunk] = world.is_loaded(pos)
            if not loaded[chunk]:
                missing.add(chunk)
        return missing

    @nyl.event
    def ChunkLoadedServerEvent(self, args):
        """
        对应区块加载后立即应用相关暂存项，剩余就绪项交由正常 tick 消化。
        """
        key = str(args.dimension)
        if key not in self.fields or self.fields[key]['phase'] != "moving":
            return
        if FOIL_BLOCKS_PER_TICK != -1 and FOIL_BLOCKS_PER_TICK <= 0:
            return
        state = self.fields[key]
        self._attach(args.dimension)
        queue = self._move_queue(args.dimension, state)
        awakened = queue.wake((args.chunkPosX, args.chunkPosZ))
        if not awakened:
            return
        get_log(self, "foil.server").sample(
            "chunk_resumed", dimension=args.dimension, chunk=(args.chunkPosX, args.chunkPosZ),
            awakened=awakened, pending=len(queue.entries), run_id=state.get('run_id'),
        )
        self._drain_moves(args.dimension, state, queue)
        if state['phase'] == "moving":
            self._broadcast_field_state(args.dimension, state)

    def _finish_field(self, dimension, state, status, message):
        """
        结束任务、广播最终状态、释放资源和通知玩家。
        """
        # 先固定终态，再广播、释放资源并通知发起玩家。
        state['phase'] = "complete"
        state['status'] = status
        get_log(self, "foil.server").event(
            "field_finished", run_id=state.get('run_id'), dimension=dimension,
            status=status, moved=state['moved'], count=state['block_count'],
            pending=len(state.get('pending_moves', {})),
        )
        self._broadcast_field_state(dimension, state)
        self._detach(dimension)
        self._message(state.get('playerId'), message)
        self._save()

    def _broadcast_field_state(self, dimension, state):
        """
        在主服务端本地广播二向箔流程状态。
        """
        event = build_field_event(dimension, state, self.tick)
        self.main_system.BroadcastEvent(ServerEvent.FoilFieldState, event)

    def EntityRemoveEvent(self, args):
        """
        同步清理已移除实体的本地二维化缓存。
        """
        # 实体销毁后不再保留二维化缓存。
        self.projectiles.pop(args.id, None)
        self.entities.remove(args.id)

    def ServerChatEvent(self, args):
        """
        响应 !foil 聊天命令并输出当前任务进度。
        """
        # 只响应精确的 !foil 命令。
        if args.message.strip() != "!foil":
            return

        # 拦截聊天并读取玩家当前维度。
        args.cancel = True
        dimension = nyl.CF(args.playerId).Dimension.GetEntityDimensionId()
        key = str(dimension)
        message = "二向箔：当前维度尚未发射。"
        # 存在任务时输出平面高度、物体总数、处理进度和状态。
        if key in self.fields:
            state = self.fields[key]
            message = "二向箔 Y=%d | 物体块=%d | 已处理块=%d | 暂存块=%d | %s" % (
                state['origin'][1],
                state['block_count'],
                state['moved'],
                len(state.get('pending_moves', {})),
                state['status'],
            )
        nyl.CF(args.playerId).Msg.NotifyOneMessage(args.playerId, message)

    def _save(self):
        """
        把调色板计划与分组游标写入额外数据。
        """
        # 失败只记录日志；运行期对象仍可继续推进并等待下一次保存。
        started = time()
        saved = self.extra.SetExtraData(Data.WORLD_V3, self.fields)
        get_log(self, "foil.server").sample(
            "save", signature=bool(saved), level="INFO" if saved else "ERROR",
            ok=bool(saved), fields=len(self.fields), duration_ms=round((time() - started) * 1000, 3),
        )
        return saved


# endregion
