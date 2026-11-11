# -*- coding: utf-8 -*-
# =================================================
#   Author: Nuoyan <https://github.com/charminglee>
#   Email : 1279735247@qq.com
#   Date  : 2026-11-12
# =================================================


"""仅供 MCDK 显式调用的真实调色板回归测试，结束时恢复场景。"""


from copy import deepcopy
from math import floor
from time import time
import mod.server.extraServerApi as api
from ..nuoyanlib import server as nyl
from ..modules.foil import server as foil
from ..modules.foil.palette import empty_data, encode_index, world_position


_tick_test = None


def stable_nbt(data):
    """
    排除实机确认会被箱子更新消费的临时解配对标记。
    """
    result = deepcopy(data)
    result.pop('forceunpair', None)
    return result


def mcdk_test_palette_fall(budget=2, live_ticks=False):
    """
    在玩家上方隔离场景中验证正式调度、状态、NBT、球边界和源目标重叠。
    """
    global _tick_test
    if _tick_test:
        return {'case': "palette_fall", 'ok': False, 'stage': "test_already_running"}
    players = api.GetPlayerList()
    if not players:
        return {'case': "palette_fall", 'ok': False, 'stage': "no_player"}
    cf = nyl.CF(players[0])
    dimension = cf.Dimension.GetEntityDimensionId()
    live = api.GetSystem(foil.MOD_NAME, "FoilServer")
    if live._field_active(dimension):
        return {'case': "palette_fall", 'ok': False, 'stage': "active_field"}
    pos = cf.Pos.GetFootPos()
    center = (int(floor(pos[0])), int(floor(pos[1])) + 110, int(floor(pos[2])))
    low = (center[0] - 16, center[1] - 4, center[2] - 16)
    high = (center[0] + 16, center[1] + 4, center[2] + 16)
    world = foil.WorldAdapter(dimension)
    if not world.ready_region("test", low, high):
        world.close()
        return {'case': "palette_fall", 'ok': False, 'stage': world.status}
    backup = world.capture(low, high)
    if backup is None:
        world.close()
        return {'case': "palette_fall", 'ok': False, 'stage': "backup_failed"}
    # 测试异常仍恢复场景与配置，异常本身不吞掉。
    old_budget = foil.FOIL_BLOCKS_PER_TICK
    started = time()
    result = {'case': "palette_fall", 'budget': budget, 'ok': False}
    try:
        blank = empty_data(backup['volume'])
        blank['common'][('minecraft:air', 0)] = list(range(33 * 9 * 33))
        assert world.apply(blank, low), "clear_arena"
        fixtures = [
            ((0, 1, 0), "minecraft:stone", 0),
            ((1, 0, 0), "minecraft:gold_block", 0),
            ((-2, 0, 0), "minecraft:chest", 2),
            ((0, -1, 1), "minecraft:oak_stairs", 3),
            ((3, 0, 0), "minecraft:diamond_block", 0),
            ((3, 3, 3), "minecraft:emerald_block", 0),
            ((-1, 1, -1), "minecraft:dark_oak_leaves", 0),
        ]
        # 稠密球体让默认 50 配置也真正跨多个游戏 tick。
        occupied = set(item[0] for item in fixtures)
        fixtures.extend(((x, y, z), "minecraft:stone", 0)
                        for x in range(-3, 4) for y in range(-3, 4) for z in range(-3, 4)
                        if x*x + y*y + z*z <= 9 and (x, y, z) not in occupied)
        expected, source_snapshots = {}, {}
        for local, name, aux in fixtures:
            source = tuple(center[i] + local[i] for i in range(3))
            assert world.info.SetBlockNew(source, {'name': name, 'aux': aux}, 0, dimension, False, False), "place_fixture"
            if sum(value * value for value in local) > 9:
                continue
            target = foil.flatten(source, center)
            expected[target] = name
            source_snapshots[target] = nyl.LvComp.BlockState.GetBlockStates(source, dimension)
        chest = (center[0] - 2, center[1], center[2])
        assert nyl.LvComp.Item.SpawnItemToContainer({'itemName': "minecraft:diamond", 'count': 7, 'auxValue': 0}, 0, chest, dimension), "chest_items"
        chest_nbt = world.info.GetBlockEntityData(dimension, chest)
        stairs = (center[0], center[1] - 1, center[2] + 1)
        assert world.info.SetLiquidBlock(stairs, {'name': "minecraft:water", 'aux': 0}, dimension), "waterlog_stairs"
        liquid = world.info.GetLiquidBlock(stairs, dimension)
        # 使用独立系统对象调用正式调度，不改玩家实际任务及存档。
        system = foil.FoilServer.__new__(foil.FoilServer)
        system.fields, system.worlds = {}, {dimension: world}
        system.object_sets, system.target_sets = {}, {}
        system.tick = 0
        system._save = lambda: True
        system._message = lambda *args: None
        system._broadcast_field_state = lambda *args: None
        state = {
            'origin': list(center), 'anchor': list(center), 'radius': 3,
            'phase': "capturing", 'status': "capturing", 'block_count': 0,
            'move_cursor': 0, 'moved': 0, 'run_id': "mcdk_palette_test",
        }
        system.fields[str(dimension)] = state
        foil.FOIL_BLOCKS_PER_TICK = budget
        if live_ticks:
            _tick_test = {
                'world': world, 'backup': backup, 'low': low, 'budget': old_budget,
                'live': live, 'previous': live.fields.get(str(dimension)),
                'state': state, 'dimension': dimension, 'expected': expected,
                'states': source_snapshots, 'center': center, 'chest': chest,
                'nbt': chest_nbt, 'stairs': stairs, 'liquid': liquid,
                'started': time(), 'start_tick': live.tick,
            }
            live.fields[str(dimension)] = state
            live._process_field(dimension, state)
            return {'case': "palette_live_ticks", 'ok': True, 'stage': "started", 'budget': budget, 'blocks': state['block_count']}
        increments = []
        for tick in range(130):
            before = state['moved']
            system._process_field(dimension, state)
            increments.append(state['moved'] - before)
            if state['phase'] == "complete":
                break
        checks = {
            'complete': state['phase'] == "complete",
            'count': state['block_count'] == len(expected),
            'blocks': all(world.info.GetBlockNew(p, dimension)['name'] == name for p, name in expected.items()),
            'states': all(nyl.LvComp.BlockState.GetBlockStates(p, dimension) == states for p, states in source_snapshots.items()),
            'outside_sphere': world.info.GetBlockNew((center[0] + 3, center[1] + 3, center[2] + 3), dimension)['name'] == "minecraft:emerald_block",
            'source_cleared': world.info.GetBlockNew((center[0], center[1] + 1, center[2]), dimension)['name'] == "minecraft:air",
            'liquid': world.info.GetLiquidBlock(foil.flatten(stairs, center), dimension) == liquid,
            'chest_nbt': world.info.GetBlockEntityData(dimension, foil.flatten(chest, center)) == foil.relocate_nbt(chest_nbt, foil.flatten(chest, center)),
            'chest_items': nyl.LvComp.Item.GetContainerItem(foil.flatten(chest, center), 0, dimension)['count'] == 7,
            'budget': (len(increments) == 1 if budget == -1 else max(increments) <= budget),
        }
        # 真实 ExtraData 往返验证 tuple 键和调色板索引可持久化。
        key = "nuoyan:mcdk_palette_roundtrip"
        extra = nyl.LvComp.ExtraData
        checks['persistence'] = bool(extra.SetExtraData(key, state, False)) and extra.GetExtraData(key) == state
        extra.SetExtraData(key, None, False)
        observations = [{'pos': p, 'expected': name, 'actual': world.info.GetBlockNew(p, dimension)} for p, name in expected.items()]
        result['sources'] = {block[0]: [world_position(i, state['source_palette']['volume'], state['source_start']) for i in values] for block, values in state['source_palette']['common'].items()}
        result.update({'ok': all(checks.values()), 'checks': checks, 'observations': observations, 'increments': increments, 'blocks': state['block_count'], 'status': state['status'], 'duration_ms': int((time() - started) * 1000)})
    finally:
        if not _tick_test:
            foil.FOIL_BLOCKS_PER_TICK = old_budget
            result['restored'] = world.apply(backup, low)
            world.close()
    result['ok'] = result['ok'] and result['restored']
    return result


def mcdk_test_palette_poll():
    """
    检查真实 OnScriptTickServer 推进的测试，并恢复世界、任务和配置。
    """
    global _tick_test
    if not _tick_test:
        return {'case': "palette_live_ticks", 'ok': False, 'stage': "no_test"}
    job = _tick_test
    state, live, world = job['state'], job['live'], job['world']
    if state['phase'] != "complete" and time() - job['started'] < 15:
        return {'case': "palette_live_ticks", 'ok': False, 'stage': "running", 'moved': state['moved'], 'status': state['status']}
    try:
        checks = {
            'complete': state['phase'] == "complete",
            'blocks': all(world.info.GetBlockNew(pos, job['dimension'])['name'] == name for pos, name in job['expected'].items()),
            'states': all(nyl.LvComp.BlockState.GetBlockStates(pos, job['dimension']) == value for pos, value in job['states'].items()),
            'chest_nbt': stable_nbt(world.info.GetBlockEntityData(job['dimension'], foil.flatten(job['chest'], job['center']))) == stable_nbt(foil.relocate_nbt(job['nbt'], foil.flatten(job['chest'], job['center']))),
            'chest_items': nyl.LvComp.Item.GetContainerItem(foil.flatten(job['chest'], job['center']), 0, job['dimension'])['count'] == 7,
            'liquid': world.info.GetLiquidBlock(foil.flatten(job['stairs'], job['center']), job['dimension']) == job['liquid'],
        }
        return_value = {'case': "palette_live_ticks", 'ok': all(checks.values()), 'checks': checks,
                        'blocks': state['moved'], 'elapsed_ticks': live.tick - job['start_tick']}
        if not checks['chest_nbt']:
            actual = world.info.GetBlockEntityData(job['dimension'], foil.flatten(job['chest'], job['center']))
            expected = foil.relocate_nbt(job['nbt'], foil.flatten(job['chest'], job['center']))
            return_value['nbt_difference'] = {key: (expected.get(key), actual.get(key)) for key in set(expected) | set(actual) if expected.get(key) != actual.get(key)}
    finally:
        live._detach(job['dimension'])
        key = str(job['dimension'])
        live.object_sets.pop(key, None)
        if job['previous']:
            live.fields[key] = job['previous']
            live._sync_object_set(job['dimension'], job['previous'])
        else:
            live.fields.pop(key, None)
        live._save()
        foil.FOIL_BLOCKS_PER_TICK = job['budget']
        restored = world.apply(job['backup'], job['low'])
        world.close()
        _tick_test = None
    return_value['restored'] = restored
    return_value['ok'] = return_value['ok'] and restored
    return return_value


def mcdk_test_palette_radius(radius=60):
    """
    只读真实地形，测量区域获取与球形映射耗时，不修改世界。
    """
    from ..modules.foil.palette import plan_palette
    player = api.GetPlayerList()[0]
    cf = nyl.CF(player)
    dimension = cf.Dimension.GetEntityDimensionId()
    center = tuple(int(floor(value)) for value in cf.Pos.GetFootPos())
    start = (center[0] - radius, center[1] - radius, center[2] - radius)
    end = (center[0] + radius, center[1] + radius, center[2] + radius)
    world = foil.WorldAdapter(dimension)
    try:
        if not world.ready_region("benchmark", start, end):
            return {'case': "palette_radius", 'ok': False, 'stage': world.status}
        t0 = time()
        data = world.capture(start, end)
        t1 = time()
        state = plan_palette(data, start, center, center, radius, foil.flatten, foil.WORLD_LIMIT)
        t2 = time()
        return {'case': "palette_radius", 'ok': bool(state), 'radius': radius, 'blocks': state['block_count'], 'capture_ms': int((t1 - t0) * 1000), 'mapping_ms': int((t2 - t1) * 1000)}
    finally:
        world.close()
