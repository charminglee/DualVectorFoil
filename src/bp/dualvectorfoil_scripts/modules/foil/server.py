# -*- coding: utf-8 -*-
# =================================================
#  ⠀
#   Author: Nuoyan <https://github.com/charminglee>
#   Email : 1279735247@qq.com
#   Date  : 2026-10-21
#  ⠀
# =================================================


from collections import OrderedDict
from copy import deepcopy
from math import floor
from uuid import uuid4
import mod.server.extraServerApi as server_api
from mod.common.minecraftEnum import GameType, ItemPosType
from ...nuoyanlib import server as nyl
from ...common.constant import *
from ...common.config import *
from .._base.server import BaseServer
from .config import *


client_event = nyl.event(sys_name=CLIENT_SYSTEM_NAME)
server_event = nyl.event(sys_name=SERVER_SYSTEM_NAME)


# region 有符号格点到二维 Morton 平面坐标 ==================================================


def zigzag(value):
    """
    把有符号整数转换为 ZigZag 无符号整数。
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
    # 逐位写入各轴，得到紧凑的交织编码。
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
    把三维格点映射到统一的二维输出平面。
    """
    # 先把三个相对坐标转为非负值，再压缩为二维坐标。
    local = [zigzag(pos[i] - origin[i]) for i in range(3)]
    u, v = deinterleave(interleave(local), 2)
    return (origin[0] + unzigzag(u), origin[1], origin[2] + unzigzag(v))


def unflatten(pos, origin):
    """
    从二维平面格点还原原始三维格点。
    """
    # 从二维平面取出交织值，并恢复三个相对坐标。
    uv = [zigzag(pos[0] - origin[0]), zigzag(pos[2] - origin[2])]
    xyz = deinterleave(interleave(uv), 3)
    return tuple(origin[i] + unzigzag(xyz[i]) for i in range(3))


# endregion


# region 六面连通物体扫描 ==================================================


DIRECTIONS = (
    (1, 0, 0),
    (-1, 0, 0),
    (0, 1, 0),
    (0, -1, 0),
    (0, 0, 1),
    (0, 0, -1),
)


def position_key(pos):
    """
    生成用于去重的稳定格点字符串键。
    """
    return "%d:%d:%d" % (pos[0], pos[1], pos[2])


def _inside(pos, min_y, max_y, world_limit):
    """
    判断格点是否位于配置的维度高度和世界边界内。
    """
    return (
        min_y <= pos[1] <= max_y
        and abs(pos[0]) <= world_limit
        and abs(pos[2]) <= world_limit
    )


def entity_contact_candidates(pos):
    """
    返回脚底紧邻下方与脚底格点，避免把站在物体上的实体漏掉。
    """
    # 脚底位置与支撑位置可能落在相邻格点，分别保留。
    x, z = int(floor(pos[0])), int(floor(pos[2]))
    foot_y = int(floor(pos[1]))
    support_y = int(floor(pos[1] - 0.01))
    result = [(x, support_y, z)]
    foot = (x, foot_y, z)
    if foot != result[0]:
        result.append(foot)
    return result


def begin_scan(state, anchor):
    """
    初始化六面连通物体扫描状态。
    """
    # 新扫描只保留锚点、游标和去重集合。
    anchor = tuple(anchor)
    state['scan_queue'] = [list(anchor)]
    state['scan_cursor'] = 0
    state['scan_seen'] = {position_key(anchor): True}
    state['object'] = []
    state['capped'] = False


def _clear_scan_state(state):
    """
    清理已完成扫描使用的临时队列与集合。
    """
    state.pop('scan_queue', None)
    state.pop('scan_cursor', None)
    state.pop('scan_seen', None)


def _compact_queue(state, queue, cursor):
    """
    压缩已处理扫描队列并重置游标。
    """
    # 只删除已经处理的前缀，避免队列无限增长。
    if cursor:
        del queue[:cursor]
    state['scan_cursor'] = 0


def advance_scan(state, world, min_y, max_y, budget=None,
                 block_limit=MAX_FOIL_BLOCKS, world_limit=WORLD_LIMIT):
    """
    处理有限数量的候选格点，返回完成状态、原因和是否触顶。
    """
    # 取出扫描上下文，预算只在本次调用内消耗。
    queue = state['scan_queue']
    seen = state['scan_seen']
    object_blocks = state['object']
    cursor = state['scan_cursor']
    processed = 0
    while cursor < len(queue) and (not budget or processed < budget):
        pos = tuple(queue[cursor])

        # 超出高度或世界边界的候选格点不继续扩散。
        if not _inside(pos, min_y, max_y, world_limit):
            cursor += 1
            processed += 1
            continue
        # 区块或方块读取未就绪时保留当前游标并等待下一 tick。
        if not world.ready(pos, None):
            _compact_queue(state, queue, cursor)
            return False, world.status or "waiting_chunks", False
        snapshot = world.read(pos)
        if not snapshot:
            _compact_queue(state, queue, cursor)
            return False, "waiting_io", False
        cursor += 1
        processed += 1
        state['scan_cursor'] = cursor
        # 空气只作为搜索边界，不进入结果集合。
        if snapshot['block']['name'] == AIR['name']:
            continue
        # 记录非空气方块，并在达到配置上限时提前结束。
        object_blocks.append(list(pos))
        if len(object_blocks) >= block_limit:
            state['capped'] = True
            _clear_scan_state(state)
            return True, "block_limit", True
        # 只向六个相邻格点扩散，保证物体按面连通。
        for direction in DIRECTIONS:
            neighbor = (
                pos[0] + direction[0],
                pos[1] + direction[1],
                pos[2] + direction[2],
            )
            key = position_key(neighbor)
            if key in seen:
                continue
            seen[key] = True
            if _inside(neighbor, min_y, max_y, world_limit):
                queue.append(list(neighbor))
    # 本轮预算耗尽后压缩队列；为空表示扫描完成。
    _compact_queue(state, queue, cursor)
    if not queue:
        _clear_scan_state(state)
        return True, "ready", False
    return False, "scanning", False


# endregion


# region 方块读取、写入和常加载窗口 ==================================================


def same_block(left, right):
    """
    判断两个方块快照是否具有相同名称和附加值。
    """
    return bool(
        left
        and right
        and left['name'] == right['name']
        and left.get('aux', 0) == right.get('aux', 0)
    )


def relocate_nbt(data, pos):
    """
    复制方块实体 NBT 并重写其中的坐标字段。
    """
    # 深拷贝后兼容普通值和网易 NBT 包装值的坐标字段。
    data = deepcopy(data)
    for index, name in enumerate(("x", "y", "z")):
        if name not in data:
            continue
        if isinstance(data[name], dict) and '__value__' in data[name]:
            data[name]['__value__'] = pos[index]
        else:
            data[name] = pos[index]
    return data


class WorldAdapter(object):
    """
    封装指定维度的区块加载、方块读写和常加载窗口。
    """

    def __init__(self, dimension):
        # 缓存当前维度需要的 ModSDK 组件入口。
        self.dimension = dimension
        self.info = nyl.LvComp.BlockInfo
        self.states = nyl.LvComp.BlockState
        self.chunks = nyl.LvComp.ChunkSource
        self.areas = {}
        self.status = "ready"

    def ready(self, source, target):
        """
        确认源位置以及可选目标位置所在区块可操作。
        """
        self.status = "ready"
        return self._ensure("source", source) and (
            not target or self._ensure("target", target)
        )

    def _ensure(self, role, pos):
        """
        检查世界边界并按需为指定角色创建常加载区块窗口。
        """
        # 先拒绝超出世界水平边界的格点。
        if max(abs(pos[0]), abs(pos[2])) > WORLD_LIMIT:
            self.status = "world_boundary"
            return False

        # 已加载区块直接读取，避免同步扫描跨区块时反复销毁和创建常加载窗口。
        if self.chunks.CheckChunkState(self.dimension, pos):
            return True

        # 源和目标各自维护一个常加载窗口，区块变化时重建。
        key = "%s_%d_%s" % (MOD_NAME, self.dimension, role)
        chunk = (pos[0] // 16, pos[2] // 16)
        if role not in self.areas or self.areas[role] != chunk:
            self.chunks.DeleteArea(key)
            pad = LOAD_PADDING
            lo = (pos[0] - pad, 0, pos[2] - pad)
            hi = (pos[0] + pad, 0, pos[2] + pad)
            if not self.chunks.SetAddArea(key, self.dimension, lo, hi):
                self.status = "load_area_failed"
                return False
            self.areas[role] = chunk

        # 新增窗口后仍需等待目标区块真正加载完成。
        if not self.chunks.CheckChunkState(self.dimension, pos):
            self.status = "loading_chunks"
            return False
        return True

    def read(self, pos):
        """
        读取并封装指定位置的可移动方块快照。
        """
        # 方块接口失败时返回等待状态，由调用方重试。
        block = self.info.GetBlockNew(pos, self.dimension)
        if not block:
            return None
        # 空气只需保留统一的最小快照。
        if block['name'] == AIR['name']:
            return {'block': dict(AIR)}

        # 非空气方块同时读取状态、方块实体和液体信息。
        states = self.states.GetBlockStates(pos, self.dimension)
        if not states:
            return None
        return {
            'block': block,
            'states': states,
            'nbt': self.info.GetBlockEntityData(self.dimension, pos),
            'liquid': self.info.GetLiquidBlock(pos, self.dimension),
        }

    def write(self, pos, snapshot):
        """
        把方块、状态、液体和方块实体数据写入目标位置。
        """
        # 先写基础方块；同名同 aux 时跳过，避免清空容器内容。
        block = snapshot['block']
        current = self.info.GetBlockNew(pos, self.dimension)
        # SetBlockNew 同名同 aux 返回 False，且重复设置容器会清空物品。
        if not same_block(current, block):
            if not self.info.SetBlockNew(pos, block, 0, self.dimension, False, False):
                self.status = "write_failed"
                return False
        # 只有存在差异时才写入方块状态。
        states = snapshot.get('states')
        if states and self.states.GetBlockStates(pos, self.dimension) != states:
            if not self.states.SetBlockStates(pos, states, self.dimension):
                self.status = "states_failed"
                return False
        # 液体层与基础方块分开比较和恢复。
        liquid = snapshot.get('liquid')
        existing_liquid = self.info.GetLiquidBlock(pos, self.dimension)
        if not same_block(liquid or AIR, existing_liquid or AIR):
            if not self.info.SetLiquidBlock(pos, liquid or AIR, self.dimension):
                self.status = "liquid_failed"
                return False
        # 方块实体数据最后写入，并重定位其中的坐标字段。
        nbt = snapshot.get('nbt')
        if nbt and not self.info.SetBlockEntityData(
            self.dimension,
            pos,
            relocate_nbt(nbt, pos),
        ):
            self.status = "nbt_failed"
            return False
        return True

    def clear(self, pos):
        """
        清除指定位置的方块内容。
        """
        # 已经是空气时无需再次调用世界写入。
        if same_block(self.info.GetBlockNew(pos, self.dimension), AIR):
            return True
        result = self.info.SetBlockNew(pos, AIR, 0, self.dimension, False, False)
        if not result:
            self.status = "clear_failed"
        return result

    def close(self):
        """
        关闭该世界适配器创建的常加载区块窗口。
        """
        # 释放源位置和目标位置创建的常加载窗口。
        for role in ("source", "target"):
            self.chunks.DeleteArea("%s_%d_%s" % (MOD_NAME, self.dimension, role))
        self.areas.clear()


# endregion


# region 目标平面分页存档 ==================================================


class PlanePages(object):
    """
    按区块分页持久化输出平面中被覆盖的原始内容。
    """

    def __init__(self, extra, dimension, all_states, run_id=0):
        self.extra = extra
        self.dimension = dimension
        self.all_states = all_states
        self.run_id = run_id
        self.cache = OrderedDict()
        self.dirty = set()

    def _page(self, pos):
        """
        计算格点所属分页键和单元键并加载缓存。
        """
        # 默认分页按维度与区块坐标命名。
        page_key = "%s%d:%d:%d" % (
            PAGE_PREFIX,
            self.dimension,
            pos[0] // 16,
            pos[2] // 16,
        )
        if self.run_id:
            # 新任务增加 run_id，避免复用旧任务的覆盖日志。
            page_key = "%s%d:run:%s:%d:%d" % (
                PAGE_PREFIX,
                self.dimension,
                self.run_id,
                pos[0] // 16,
                pos[2] // 16,
            )

        # 单元键只记录区块内的局部横坐标。
        cell_key = "%d:%d" % (pos[0] % 16, pos[2] % 16)
        if page_key not in self.cache:
            self.cache[page_key] = self.extra.GetExtraData(page_key) or {}
        return page_key, cell_key

    def get(self, pos):
        """
        读取目标格点已保存的原始快照。
        """
        page_key, cell_key = self._page(pos)
        return self.cache[page_key].get(cell_key)

    def put(self, pos, value):
        """
        保存目标格点的原始快照并标记分页脏数据。
        """
        # 保存深拷贝，避免世界对象后续变化污染日志。
        page_key, cell_key = self._page(pos)
        self.cache[page_key][cell_key] = deepcopy(value)
        self.dirty.add(page_key)

    def flush(self, state):
        """
        保存脏分页、任务状态并限制内存缓存规模。
        """
        # 先逐页保存覆盖日志。
        for key in self.dirty:
            if not self.extra.SetExtraData(key, self.cache[key], False):
                return False
        # 再保存任务状态和全局游标。
        if not self.extra.SetExtraData(STATE_KEY, self.all_states, False):
            return False
        if not self.extra.SaveExtraData():
            return False
        # 持久化成功后才清理脏标记和超额缓存。
        self.dirty.clear()
        while len(self.cache) > 16:
            self.cache.popitem(last=False)
        return True


# endregion


# region 批量搬移和失败续跑 ==================================================


def step(state, world, pages):
    """
    执行单格搬移并返回是否可以推进游标。
    """
    # 没有待执行操作时无需推进。
    if 'pending' not in state or not state['pending']:
        return False
    pending = state['pending']
    src, dst = tuple(pending['src']), tuple(pending['dst'])
    # 首次执行时读取源快照并缓存在待执行记录中。
    if 'snapshot' not in pending:
        if not world.ready(src, None):
            return False
        entry = pages.get(src) if src[1] == state['origin'][1] else None
        snapshot = entry['original'] if entry else world.read(src)
        if not snapshot:
            return False
        pending['snapshot'] = snapshot

    # 空气和原位置方块只需标记完成。
    snapshot = pending['snapshot']
    if snapshot['block']['name'] == AIR['name'] or src == dst:
        return True
    # 目标区块未就绪时保留当前操作等待重试。
    if not world.ready(src, dst):
        return False
    # 首次覆盖目标位置时先保存原内容。
    if not pages.get(dst):
        original = world.read(dst)
        if not original:
            return False
        pages.put(dst, {'original': original})
    # 日志必须先落盘，之后才允许修改世界。
    if not pages.flush(state):
        return False
    if not world.write(dst, snapshot):
        return False
    # 位于输出平面且已有覆盖日志的源格点无需清除。
    if src[1] == state['origin'][1] and pages.get(src):
        return True
    return world.clear(src)


def prepare(state, source):
    """
    为单个方块建立源位置、目标位置和待执行状态。
    """
    # 源位置保留元组，目标位置在创建时一次计算。
    state['pending'] = {
        'src': tuple(source),
        'dst': flatten(source, state['origin']),
    }


def _prepare_batch(state, sources, world, pages):
    """
    预读并验证一批搬移操作，建立可重放日志。
    """
    # 批次先完整预读，再进入执行阶段。
    operations = []
    moved = 0
    origin_y = state['origin'][1]
    for source in sources:
        src = tuple(source)
        dst = flatten(src, state['origin'])
        # 读取源方块前确认区块已加载。
        if not world.ready(src, None):
            return False, world.status or "waiting_chunks"
        entry = pages.get(src) if src[1] == origin_y else None
        snapshot = entry['original'] if entry else world.read(src)
        if not snapshot:
            return False, "waiting_io"
        is_air = snapshot['block']['name'] == AIR['name']
        # 空气和原位方块只记录跳过操作。
        if is_air or src == dst:
            operations.append({
                'src': list(src),
                'dst': list(dst),
                'snapshot': snapshot,
                'skip': True,
                'count': 0 if is_air else 1,
            })
            if not is_air:
                moved += 1
            continue
        # 真正搬移前同时确认源和目标区块。
        if not world.ready(src, dst):
            return False, world.status or "waiting_chunks"
        # 目标格点首次被覆盖时保存原内容。
        if not pages.get(dst):
            original = world.read(dst)
            if not original:
                return False, "waiting_io"
            pages.put(dst, {'original': original})
        operations.append({
            'src': list(src),
            'dst': list(dst),
            'snapshot': snapshot,
            'skip': False,
            'count': 1,
        })
        moved += 1
    state['batch'] = {
        'ops': operations,
        'cursor': 0,
        'moved': moved,
        'journal_saved': False,
    }
    return True, "ready"


def _execute_batch(state, world, pages):
    """
    执行已准备的搬移批次并持久化最终游标。
    """
    # 从保存的游标继续执行，保证失败后可以重放。
    batch = state['batch']
    operations = batch['ops']
    cursor = batch['cursor']
    origin_y = state['origin'][1]
    while cursor < len(operations):
        operation = operations[cursor]
        src, dst = tuple(operation['src']), tuple(operation['dst'])
        if not operation['skip']:
            # 写入前重新确认区块状态。
            if not world.ready(src, dst):
                return False, world.status or "waiting_chunks"
            if not world.write(dst, operation['snapshot']):
                status = world.status if world.status != "ready" else "write_failed"
                return False, status

            # 输出平面中已有日志的源格点不再清除。
            if not (src[1] == origin_y and pages.get(src)):
                if not world.clear(src):
                    status = world.status if world.status != "ready" else "clear_failed"
                    return False, status
        cursor += 1
        batch['cursor'] = cursor

    state['move_cursor'] += len(operations)
    state['moved'] += batch['moved']
    state.pop('batch', None)
    # 世界写入完成后保存游标与计数；失败时旧 batch 可从日志安全重放。
    if not pages.flush(state):
        return False, "waiting_io"
    return True, "ready"


def run_batch(state, sources, world, pages):
    """
    计划并执行一组搬移，日志与最终进度各持久化一次。
    """
    # 没有旧批次时先准备一次完整计划。
    if 'batch' not in state or not state['batch']:
        complete, status = _prepare_batch(state, sources, world, pages)
        if not complete:
            return False, status
    batch = state['batch']
    # 覆盖日志写入后记录标记，避免重复持久化同一批次。
    if not batch['journal_saved']:
        batch['journal_saved'] = True
        if not pages.flush(state):
            batch['journal_saved'] = False
            return False, "waiting_io"
    return _execute_batch(state, world, pages)


# endregion


# region 对 effect 模块发布的精简流程事件 ==================================================


def build_field_event(dimension, state, tick):
    """
    构造二向箔本地广播使用的精简只读事件载荷。
    """
    # 只读取当前游标对应的一项，不复制整个方块列表。
    blocks = state.get('object') or []
    count = len(blocks)
    cursor = state['move_cursor']
    source = tuple(blocks[min(cursor, count - 1)]) if count else None
    return {
        'dimension': dimension,
        'run_id': state.get('run_id', 0),
        'phase': state['phase'],
        'tick': tick,
        'origin': tuple(state['origin']),
        'source': source,
        'processed_count': cursor,
        'block_count': count,
    }


# endregion


# region 接触物体的实体二维化状态 ==================================================


class FlatEntities(object):
    """
    扫描接触目标物体的实体并维持二维化冻结状态。
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
        # 已处理实体无需重复扫描。
        if entity_id in self.active:
            return

        # 优先恢复持久化的二维化标记，兼容脚本重载。
        cf = nyl.CF(entity_id)
        saved = cf.ExtraData.GetExtraData(ATTR)
        if saved:
            self.active[entity_id] = saved
            cf.ModAttr.SetAttr(ATTR, saved)
            if saved['kind'] != "minecraft:player":
                cf.ControlAi.SetBlockControlAi(False, True)
            return

        # 投射物和未生成二维目录的实体不参与捕获。
        kind = cf.EngineType.GetEngineTypeStr()
        if kind == PROJECTILE or kind not in ENTITY_GEOMETRIES:
            return
        # 只使用当前维度已扫描完成的物体索引。
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
        if MAX_FOIL_ENTITIES:
            captured = sum(
                1
                for data in self.active.values()
                if data.get('dimension') == dimension
                and data.get('run_id', 0) == state.get('run_id', 0)
            )
            if captured >= MAX_FOIL_ENTITIES:
                return
        # 脚底坐标通常落在物体上方空气层；同时检查脚底与紧邻下方。
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
        if not cf.ExtraData.SetExtraData(ATTR, saved):
            return
        # 同步内存、属性复制和持久化标记，非玩家实体同时关闭 AI。
        self.active[entity_id] = saved
        cf.ModAttr.SetAttr(ATTR, saved)
        if kind != "minecraft:player":
            cf.Attr.SetPersistent(True)
            cf.ControlAi.SetBlockControlAi(False, True)
        self._hold(entity_id, saved)

    def hold(self):
        """
        约束所有二维化实体的重力、速度和位置。
        """
        # 每 tick 约束全部二维化实体，防止重力或外力改变位置。
        for entity_id, data in self.active.items():
            self._hold(entity_id, data)

    def _hold(self, entity_id, data):
        """
        把单个二维化实体固定在输出平面位置。
        """
        # 实体切换维度后跳过，避免把旧位置写入错误世界。
        cf = nyl.CF(entity_id)
        if cf.Dimension.GetEntityDimensionId() != data['dimension']:
            return
        # SDK 的 0 表示回退世界重力；用极小负值并逐帧约束位置。
        cf.Gravity.SetGravity(-0.000001)
        nyl.set_motion(entity_id, (0.0, 0.0, 0.0))
        cf.Pos.SetFootPos(tuple(data['pos']))

    def remove(self, entity_id):
        """
        移除已销毁实体的二维化缓存。
        """
        self.active.pop(entity_id, None)


# endregion


# region 系统入口 ==================================================


def get_item_name(item):
    """
    读取新版物品名，并兼容旧版事件字段。
    """
    if 'newItemName' in item:
        return item['newItemName']
    if 'itemName' in item:
        return item['itemName']
    return None


class FoilServer(BaseServer):
    """
    二向箔服务端系统。
    """

    def __init__(self, namespace, system_name):
        super(FoilServer, self).__init__(namespace, system_name)
        # 加载持久化任务并按维度建立运行期索引。
        self.extra = nyl.LvComp.ExtraData
        self.fields = self.extra.GetExtraData(STATE_KEY) or {}
        self.worlds, self.pages = {}, {}
        self.object_sets, self.object_set_counts = {}, {}
        self.projectiles, self.cooldowns = {}, {}
        self.entities = FlatEntities()
        self.tick = 0
        # 恢复未完成任务并重新发布正在搬移的状态。
        for key, state in self.fields.items():
            dimension = int(key)
            self._sync_object_set(dimension, state)
            if state.get('phase') != "complete":
                self._attach(dimension)
            if state.get('phase') == "moving":
                self._broadcast_field_state(dimension, state)

    def _attach(self, dimension):
        """
        为指定维度建立世界适配器和分页日志。
        """
        # 同一维度只保留一套世界适配器和分页对象。
        if dimension in self.worlds:
            return
        self.worlds[dimension] = WorldAdapter(dimension)
        run_id = self.fields[str(dimension)].get('run_id', 0)
        self.pages[dimension] = PlanePages(
            self.extra,
            dimension,
            self.fields,
            run_id,
        )

    def _detach(self, dimension):
        """
        关闭并移除指定维度的运行期世界资源。
        """
        # 先关闭世界窗口，再移除分页引用。
        world = self.worlds.pop(dimension, None)
        if world:
            world.close()
        self.pages.pop(dimension, None)

    def _sync_object_set(self, dimension, state):
        """
        把已扫描方块增量同步到实体接触索引。
        """
        # 只追加尚未同步的扫描结果。
        key = str(dimension)
        object_set = self.object_sets.setdefault(key, set())
        blocks = state.get('object') or []
        start = self.object_set_counts.get(key, 0)
        for pos in blocks[start:]:
            object_set.add(tuple(pos))
        self.object_set_counts[key] = len(blocks)

    def ServerItemTryUseEvent(self, args):
        """
        拦截二向箔右键使用并尝试发射。
        """
        # 只拦截手持二向箔的事件。
        item = args.itemDict or {}
        if get_item_name(item) != ITEM:
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
        if get_item_name(item) != ITEM:
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
        判断指定维度是否存在仍在飞行的二向箔实体。
        """
        return any(shot.get('dimension') == dimension for shot in self.projectiles.values())

    def _launch(self, player_id):
        """
        校验玩家、维度和物品状态后创建二向箔投射物。
        """
        # 先检查玩家冷却，避免重复创建实体。
        if self.tick < self.cooldowns.get(player_id, 0):
            return

        # 当前维度必须显式配置高度范围。
        cf = nyl.CF(player_id)
        dimension = cf.Dimension.GetEntityDimensionId()
        if dimension not in HEIGHTS:
            self._message(player_id, "这个自定义维度尚未配置高度范围。")
            return
        # 同一维度只允许一个尚未完成的任务。
        if self._field_active(dimension):
            self._message(player_id, "这个维度已经在二维化；输入 !foil 可查看进度。")
            return
        # 同一维度只允许一个飞行中的投射物。
        if self._projectile_active(dimension):
            return

        # 校验手持物品和数量信息。
        item = cf.Item.GetPlayerItem(ItemPosType.CARRIED)
        if not item or get_item_name(item) != ITEM:
            return
        # 位置或朝向不可用时取消发射。
        pos, rot = cf.Pos.GetPos(), cf.Rot.GetRot()
        if not pos or not rot:
            return
        # 从朝向构造无重力飞行向量和前向出生点。
        direction = server_api.GetDirFromRot(rot)
        spawn = tuple(pos[i] + direction[i] * 1.5 for i in range(3))
        entity_id = nyl.LvComp.Projectile.CreateProjectileEntity(
            player_id,
            PROJECTILE,
            {
                'position': spawn,
                'direction': direction,
                'power': 1.5,
                'gravity': 0.0,
                'damage': 0.0,
            },
        )
        if not entity_id or entity_id == "-1":
            return
        # 生存模式消耗一枚；扣减失败时销毁刚创建的投射物。
        if nyl.LvComp.Game.GetPlayerGameType(player_id) != GameType.Creative:
            if not cf.Item.SetInvItemNum(cf.Item.GetSelectSlotId(), item['count'] - 1):
                self.DestroyEntity(entity_id)
                return
        # 记录飞行期限、最近位置和发起玩家。
        self.projectiles[entity_id] = {
            'dimension': dimension,
            'deadline': self.tick + FUSE_TICKS,
            'last_pos': spawn,
            'playerId': player_id,
        }
        self.cooldowns[player_id] = self.tick + LAUNCH_COOLDOWN
        self._message(player_id, "二向箔已发射，接触目标或两秒后展开。")

    def _message(self, player_id, message):
        """
        向发起二向箔的玩家发送状态消息。
        """
        # 未绑定玩家的旧存档不发送消息。
        if player_id:
            nyl.CF(player_id).Msg.NotifyOneMessage(player_id, message)

    def ProjectileDoHitEffectEvent(self, args):
        """
        二向箔投射物命中后记录落点并销毁实体。
        """
        # 只处理本系统创建并仍记录中的投射物。
        entity_id = args.id
        if entity_id not in self.projectiles:
            return
        self._detonate(entity_id, (args.x, args.y, args.z))

    def _detonate(self, entity_id, pos):
        """
        根据投射物落点建立新的二维化任务。
        """
        # 先移出飞行表并销毁实体，防止重复引爆。
        shot = self.projectiles.pop(entity_id)
        dimension = shot['dimension']
        player_id = shot.get('playerId')
        self.DestroyEntity(entity_id)
        # 命中前已有任务时只完成本次投射物清理。
        if self._field_active(dimension):
            return

        # 把接触点限制在配置高度和世界边界内。
        low, high = HEIGHTS[dimension]
        anchor = [int(floor(p)) for p in pos]
        if (
            anchor[1] < low
            or anchor[1] > high
            or abs(anchor[0]) > WORLD_LIMIT
            or abs(anchor[2]) > WORLD_LIMIT
        ):
            self._message(player_id, "二向箔没有接触到可处理的世界方块。")
            return
        # 输出平面保持在可放置方块的高度范围内。
        plane_y = min(high - 2, max(low + 2, anchor[1]))
        state = {
            'run_id': uuid4().hex,
            'origin': [anchor[0], plane_y, anchor[2]],
            'anchor': anchor,
            'phase': "scanning",
            'pending': None,
            'move_cursor': 0,
            'moved': 0,
            'status': "scanning",
            'capped': False,
            'playerId': player_id,
        }
        begin_scan(state, anchor)
        # 新任务重新建立物体索引，旧任务的集合与增量游标不能沿用。
        self.object_sets.pop(str(dimension), None)
        self.object_set_counts.pop(str(dimension), None)
        self.fields[str(dimension)] = state
        self._sync_object_set(dimension, state)
        self._attach(dimension)
        # 立即保存初始任务，然后尝试推进首轮扫描。
        self._save()
        self._process_field(dimension, state)

    def OnScriptTickServer(self, args):
        """
        推进投射物、扫描、搬移、实体约束和定期存档。
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

        # 定期保存任务和分页游标。
        if self.tick % SAVE_INTERVAL == 0:
            self._save()

    def _update_projectiles(self):
        """
        更新二向箔投射物位置并在超时或失效时引爆。
        """
        # 复制键列表，允许循环内销毁并移除投射物。
        for entity_id, shot in list(self.projectiles.items()):
            pos = nyl.CF(entity_id).Pos.GetPos()
            # 保留最后一次有效位置，超时后仍可在原落点展开。
            if pos:
                shot['last_pos'] = pos
            if not pos or self.tick >= shot['deadline']:
                self._detonate(entity_id, shot['last_pos'])

    def _process_field(self, dimension, state):
        """
        推进指定维度的扫描或批量搬移阶段。
        """
        # 完成态只用于查询，不再占用世界资源。
        phase = state.get('phase')
        if phase == "complete":
            return
        # 首次处理时按需建立世界适配器和分页日志。
        self._attach(dimension)
        world, pages = self.worlds[dimension], self.pages[dimension]
        if phase == "scanning":
            # 扫描阶段不设每 tick 候选预算，遇到区块未就绪才暂停。
            complete, status, capped = advance_scan(
                state,
                world,
                HEIGHTS[dimension][0],
                HEIGHTS[dimension][1],
                None,
                MAX_FOIL_BLOCKS,
                WORLD_LIMIT,
            )
            self._sync_object_set(dimension, state)
            state['status'] = status
            if not complete:
                return

            # 空物体直接结束任务。
            if not state['object']:
                self._finish_field(
                    dimension,
                    state,
                    "no_object",
                    "二向箔命中的位置不是可二维化的方块。",
                )
                return

            # 扫描完成后切换到有界批量搬移阶段。
            state['phase'] = "moving"
            state['move_cursor'] = 0
            state['status'] = "moving"
            self._save()
            self._broadcast_field_state(dimension, state)
            if capped:
                self._message(
                    state.get('playerId'),
                    "连通物体已达到 %d 方块上限，只处理已发现部分。"
                    % MAX_FOIL_BLOCKS,
                )
            else:
                self._message(
                    state.get('playerId'),
                    "已识别连通物体，共 %d 个方块。"
                    % len(state['object']),
                )
            return

        # 每 tick 只提交配置数量的方块给搬移批次。
        start = state['move_cursor']
        end = min(start + FOIL_BLOCKS_PER_TICK, len(state['object']))
        sources = [tuple(state['object'][index]) for index in range(start, end)]
        complete, status = run_batch(state, sources, world, pages)
        if not complete:
            state['status'] = status
            return
        # 全部处理完成后写入终态并释放资源。
        if state['move_cursor'] >= len(state['object']):
            status = "block_limit" if state.get('capped') else "complete"
            self._finish_field(dimension, state, status, "二向箔二维化完成。")
        else:
            state['status'] = "moving"

    def _finish_field(self, dimension, state, status, message):
        """
        结束任务、广播最终状态、释放资源和通知玩家。
        """
        # 先固定终态，再广播、释放资源并通知发起玩家。
        state['phase'] = "complete"
        state['status'] = status
        state['pending'] = None
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
            message = "二向箔 Y=%d | 物体块=%d | 已处理块=%d | %s" % (
                state['origin'][1],
                len(state.get('object') or []),
                state['moved'],
                state['status'],
            )
        nyl.CF(args.playerId).Msg.NotifyOneMessage(args.playerId, message)

    def _save(self):
        """
        把任务、分页日志和搬移进度写入额外数据。
        """
        # 失败只记录日志；运行期对象仍可继续推进并等待下一次保存。
        if not self.extra.SetExtraData(STATE_KEY, self.fields):
            print("[DualVectorFoil] failed to save object frontier")


# endregion
