# -*- coding: utf-8 -*-
# =================================================
#   Author: Nuoyan <https://github.com/charminglee>
#   Email : 1279735247@qq.com
#   Date  : 2026-11-11
# =================================================


"""调色板索引的球形筛选、一次性二维映射与批次切片；不访问 ModSDK。"""


def decode_index(index, volume):
    """
    还原 SDK 的 YXZ 线性索引；volume 顺序为宽 Z、长 X、高 Y。
    """
    width, length, height = volume
    y, remainder = divmod(index, width * length)
    x, z = divmod(remainder, width)
    return x, y, z


def encode_index(pos, volume):
    """
    将局部整数格点编码为 SDK 调色板线性索引。
    """
    return (pos[1] * volume[1] + pos[0]) * volume[0] + pos[2]


def world_position(index, volume, start):
    """
    还原调色板索引对应的世界格点。
    """
    local = decode_index(index, volume)
    return tuple(start[axis] + local[axis] for axis in range(3))


def empty_data(volume, template=None):
    """
    创建稀疏调色板，沿用原有状态表但不隐式填充缺失格点。
    """
    return {
        'volume': volume, 'common': {}, 'extra': {}, 'actor': {},
        'states': template['states'] if template else {},
        'extraStates': template['extraStates'] if template else {},
        'void': False, 'eliminateAir': False,
    }


def _remap_layers(data, result, indices):
    """
    按同一索引映射同步处理含水层与方块实体描述。
    """
    for block, positions in data['extra'].items():
        selected = [indices[index] for index in positions if index in indices]
        if selected:
            result['extra'][block] = selected
    for kind, actors in data['actor'].items():
        selected = dict(
            (indices[index], actor) for index, actor in actors.items()
            if index in indices
        )
        if selected:
            result['actor'][kind] = selected


def plan_palette(data, start, center, origin, radius, mapper, world_limit):
    """
    直接变换调色板字典，保留球内所有非空气块并一次算完二维目标。

    先缓存各轴的位交织贡献，再用或运算组合，避免每个方块重复逐位循环。
    source 与 target 中同类型列表逐项对应，后续帧只切片，不再查询源世界。
    """
    volume = data['volume']
    source = empty_data(volume, data)
    dimensions = (volume[1], volume[2], volume[0])
    tables = []
    # Morton 位互不重叠，独立轴贡献可以按位合并后再做 ZigZag 逆变换。
    for axis, size in enumerate(dimensions):
        table = []
        for offset in range(size):
            pos = list(origin)
            pos[axis] = start[axis] + offset
            mapped = mapper(pos, origin)
            uv = (mapped[0] - origin[0], mapped[2] - origin[2])
            table.append(tuple(v * 2 if v >= 0 else -v * 2 - 1 for v in uv))
        tables.append(table)
    targets, selected = {}, {}
    min_x = min_z = world_limit
    max_x = max_z = -world_limit
    radius_squared = radius * radius
    # 只遍历引擎返回的字典，不枚举球体中的空气，不再计算连通性。
    for block, positions in data['common'].items():
        if block[0] in ("minecraft:air", "minecraft:structure_void"):
            continue
        kept, mapped_positions = [], []
        for index in positions:
            x, y, z = decode_index(index, volume)
            wx, wy, wz = start[0] + x, start[1] + y, start[2] + z
            if (wx - center[0]) ** 2 + (wy - center[1]) ** 2 + (wz - center[2]) ** 2 > radius_squared:
                continue
            ux, vx = tables[0][x]
            uy, vy = tables[1][y]
            uz, vz = tables[2][z]
            u, v = ux | uy | uz, vx | vy | vz
            tx = origin[0] + (u // 2 if u % 2 == 0 else -(u // 2) - 1)
            tz = origin[2] + (v // 2 if v % 2 == 0 else -(v // 2) - 1)
            if max(abs(tx), abs(tz)) > world_limit:
                return None
            kept.append(index)
            mapped_positions.append((tx, 0, tz))
            selected[index] = index
            min_x, max_x = min(min_x, tx), max(max_x, tx)
            min_z, max_z = min(min_z, tz), max(max_z, tz)
        if kept:
            source['common'][block] = kept
            targets[block] = mapped_positions
    _remap_layers(data, source, selected)
    target_volume = (max_z - min_z + 1, max_x - min_x + 1, 1) if selected else (0, 0, 0)
    target = empty_data(target_volume, data)
    mapping = {}
    for block, positions in targets.items():
        encoded = [encode_index((p[0] - min_x, 0, p[2] - min_z), target_volume) for p in positions]
        target['common'][block] = encoded
        mapping.update(zip(source['common'][block], encoded))
    _remap_layers(source, target, mapping)
    return {
        'source_palette': source, 'target_palette': target,
        'source_start': tuple(start), 'target_start': (min_x, origin[1], min_z),
        'groups': list(source['common']), 'block_count': len(selected),
        'move_cursor': 0, 'moved': 0, 'group_index': 0, 'group_cursor': 0,
    }


class PaletteContacts(object):
    """
    用紧凑源索引集合进行实体接触判定，避免复制百万个世界坐标元组。
    """

    def __init__(self, state, target=False):
        prefix = "target" if target else "source"
        data = state[prefix + '_palette']
        self.start = state[prefix + '_start']
        self.volume = data['volume']
        self.indices = set(index for positions in data['common'].values() for index in positions)

    def __contains__(self, pos):
        """
        世界格点位于调色板包围盒内且有实际方块时返回真。
        """
        local = tuple(pos[axis] - self.start[axis] for axis in range(3))
        if not (0 <= local[0] < self.volume[1] and 0 <= local[1] < self.volume[2] and 0 <= local[2] < self.volume[0]):
            return False
        return encode_index(local, self.volume) in self.indices


def source_at(state):
    """
    常数时间读取当前分组游标的源格点，用于本地视觉事件。
    """
    if not state['block_count']:
        return None
    finished = state['group_index'] >= len(state['groups'])
    group = min(state['group_index'], len(state['groups']) - 1)
    positions = state['source_palette']['common'][state['groups'][group]]
    cursor = len(positions) - 1 if finished else min(state['group_cursor'], len(positions) - 1)
    return world_position(positions[cursor], state['source_palette']['volume'], state['source_start'])


def slice_batch(state, budget, target_contacts):
    """
    按预计算顺序生成本帧目标和清除调色板，-1 取出全部剩余方块。
    """
    source, target = state['source_palette'], state['target_palette']
    output, clear = empty_data(target['volume'], target), empty_data(source['volume'])
    group, cursor, count = state['group_index'], state['group_cursor'], 0
    remaining = state['block_count'] - state['move_cursor'] if budget == -1 else budget
    target_indices, clear_indices = {}, []
    while remaining > 0 and group < len(state['groups']):
        block = state['groups'][group]
        sources, destinations = source['common'][block], target['common'][block]
        end = min(cursor + remaining, len(sources))
        output['common'][block] = destinations[cursor:end]
        for index, destination in zip(sources[cursor:end], destinations[cursor:end]):
            target_indices[destination] = destination
            pos = world_position(index, source['volume'], state['source_start'])
            # 任何最终落点都不清除，防止跨帧源/目标重叠擦掉先前已落下的方块。
            if pos not in target_contacts:
                clear_indices.append(index)
        taken = end - cursor
        count += taken
        remaining -= taken
        cursor = end
        if cursor == len(sources):
            group += 1
            cursor = 0
    _remap_layers(target, output, target_indices)
    clear['common'][('minecraft:air', 0)] = clear_indices
    return {'output': output, 'clear': clear, 'count': count, 'group': group, 'cursor': cursor}
