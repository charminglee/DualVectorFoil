# -*- coding: utf-8 -*-
# =================================================
#  ⠀
#   Author: Nuoyan <https://github.com/charminglee>
#   Email : 1279735247@qq.com
#   Date  : 2026-11-11
#  ⠀
# =================================================


def mcdk_test_player_immunity_server():
    """
    仅供 MCP 显式调用的服务端自检：玩家接触候选物体也不被修改。
    """
    import mod.server.extraServerApi as api
    from ..nuoyanlib import server as nyl
    from ..common.constant import Attr
    from ..modules.foil.server import entity_contact_candidates

    # 只调用玩家捕获入口，不发射、不扫描地形、不写入世界方块。
    system = api.GetSystem(MOD_NAME, "FoilServer")
    if not system:
        return {'case': "player_immunity_server", 'ok': False, 'stage': "system_missing"}
    if not hasattr(system.entities, "_release_player"):
        return {'case': "player_immunity_server", 'ok': False, 'stage': "reload_required"}
    results = []
    for player_id in api.GetPlayerList():
        cf = nyl.CF(player_id)
        pos = cf.Pos.GetFootPos()
        if not pos:
            results.append({'player': player_id, 'ok': False, 'stage': "position_missing"})
            continue
        key = str(cf.Dimension.GetEntityDimensionId())
        before = (pos, cf.Rot.GetRot(), cf.Gravity.GetGravity())
        state = {'origin': list(pos), 'run_id': "mcdk_player_immunity"}
        system.entities._visit(
            player_id, {key: state}, {key: set(entity_contact_candidates(pos))},
        )
        # 使用实际玩家组件核对位置、朝向、重力以及两类旧标记。
        after = (cf.Pos.GetFootPos(), cf.Rot.GetRot(), cf.Gravity.GetGravity())
        held = player_id in system.entities.active
        saved = cf.ExtraData.GetExtraData(Attr.FLAT)
        synced = cf.ModAttr.GetAttr(Attr.FLAT)
        results.append({
            'player': player_id,
            'ok': before == after and not held and not saved and not synced,
            'held': held,
            'saved': saved,
            'synced': synced,
            'unchanged': before == after,
        })
    return {
        'case': "player_immunity_server",
        'ok': bool(results) and all(result['ok'] for result in results),
        'players': results,
        'tick': system.tick,
    }


def mcdk_test_player_immunity_client():
    """
    仅供 MCP 显式调用的客户端自检：玩家模型不进入二维渲染缓存。
    """
    import mod.client.extraClientApi as api
    from ..nuoyanlib import client as nyl
    from ..common.constant import MOD_NAME
    from ..modules.foil.config import Attr

    # 只检查当前客户端的本机玩家，不改动相机或输入配置。
    system = api.GetSystem(MOD_NAME, "FoilClient")
    if not system:
        return {'case': "player_immunity_client", 'ok': False, 'stage': "system_missing"}
    if not hasattr(system, "_restore_player"):
        return {'case': "player_immunity_client", 'ok': False, 'stage': "reload_required"}
    player_id = api.GetLocalPlayerId()
    system._apply(player_id)
    flat_model = player_id in system.applied
    synced = nyl.CF(player_id).ModAttr.GetAttr(Attr.FLAT)
    return {
        'case': "player_immunity_client",
        'ok': not flat_model and not synced,
        'flat_model': flat_model,
        'synced': synced,
    }
