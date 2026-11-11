# -*- coding: utf-8 -*-
# =================================================
#
#   Author: Nuoyan <https://github.com/charminglee>
#   Email : 1279735247@qq.com
#   Date  : 2026-11-12
#
# =================================================


"""按区块唤醒待搬移引用；仅保存原调色板引用，不复制世界快照或导入 SDK。"""


from collections import deque
from .palette import _ordered_groups, _remap_layers, empty_data, world_position


def scan_references(state, budget):
    """
    按原分组顺序推进遍历游标，实际成功数由搬移完成后单独累计。
    """
    groups = _ordered_groups(state)
    group, cursor = state['group_index'], state['group_cursor']
    remaining = state['block_count'] - state['move_cursor']
    if budget != -1:
        remaining = min(remaining, budget)
    result = []
    while remaining > 0 and group < len(groups):
        block = groups[group]
        positions = state['source_palette']['common'][block]
        end = min(cursor + remaining, len(positions))
        result.extend((block, index) for index in range(cursor, end))
        remaining -= end - cursor
        cursor = end
        if cursor == len(positions):
            group, cursor = group + 1, 0
    state['group_index'], state['group_cursor'] = group, cursor
    state['move_cursor'] += len(result)
    return result


def reference_positions(state, reference):
    """
    从同类型配对列表还原一项待搬移方块的源和目标世界坐标。
    """
    block, offset = reference
    source, target = state['source_palette'], state['target_palette']
    return (
        world_position(source['common'][block][offset], source['volume'], state['source_start']),
        world_position(target['common'][block][offset], target['volume'], state['target_start']),
    )


def reference_batch(state, references, target_contacts):
    """
    只为已就绪引用构造写入和清源数据，所有附层沿用相同索引筛选。
    """
    source, target = state['source_palette'], state['target_palette']
    output, clear = empty_data(target['volume'], target), empty_data(source['volume'])
    target_indices, clear_indices = {}, []
    for block, offset in references:
        index = source['common'][block][offset]
        destination = target['common'][block][offset]
        output['common'].setdefault(block, []).append(destination)
        target_indices[destination] = destination
        pos = world_position(index, source['volume'], state['source_start'])
        if pos not in target_contacts:
            clear_indices.append(index)
    _remap_layers(target, output, target_indices)
    clear['common'][('minecraft:air', 0)] = clear_indices
    return {'output': output, 'clear': clear, 'count': len(references)}


class PendingMoves(object):
    """
    持久化引用与运行期区块反向索引分离；加载事件仅唤醒相关引用。
    """

    def __init__(self, state):
        self.entries = state.setdefault('pending_moves', {})
        self.ready = deque(self.entries)
        self.queued = set(self.entries)
        self.waiters, self.dependencies = {}, {}

    def add(self, state, reference):
        """
        使用唯一源索引作为任务内编号，并登记为待检查引用。
        """
        block, offset = reference
        token = state['source_palette']['common'][block][offset]
        self.entries[token] = reference
        self.retry(token)

    def retry(self, token):
        """
        去除旧依赖并登记一次重试，避免重复加载事件制造重复写入。
        """
        self._unwatch(token)
        if token not in self.queued:
            self.ready.append(token)
            self.queued.add(token)

    def _unwatch(self, token):
        """
        从先前登记的少量区块集合中移除引用，不扫描其他区块。
        """
        for chunk in self.dependencies.pop(token, ()):
            self.waiters[chunk].discard(token)
            if not self.waiters[chunk]:
                del self.waiters[chunk]

    def wait(self, token, chunks):
        """
        暂存源或目标仍未就绪的引用，后续由对应加载事件唤醒。
        """
        self._unwatch(token)
        self.dependencies[token] = chunks
        for chunk in chunks:
            self.waiters.setdefault(chunk, set()).add(token)

    def wake(self, chunk):
        """
        只将当前加载区块关联的引用排入待应用队列。
        """
        tokens = list(self.waiters[chunk]) if chunk in self.waiters else []
        for token in tokens:
            self.retry(token)
        return len(tokens)

    def pop(self):
        """
        提取一项待检查引用，成功写入前仍保留持久化记录。
        """
        token = self.ready.popleft()
        self.queued.remove(token)
        return token, self.entries[token]

    def complete(self, token):
        """
        目标、NBT 与清源均成功后删除待处理记录。
        """
        self._unwatch(token)
        del self.entries[token]
