# -*- coding: utf-8 -*-
#  ================================================
#  ⠀
#    Copyright (c) 2026 Nuoyan
#  ⠀
#    Author: Nuoyan <https://github.com/charminglee>
#    Email : 1279735247@qq.com
#    Date  : 2026-10-1
#  ⠀
#  ================================================


from __future__ import division
from collections import defaultdict
import mod.server.extraServerApi as s_api
from mod.server.system.serverSystem import ServerSystem
from mod.common.minecraftEnum import EntityType
from ...common.mc_math.vector import vec_mul
from .. import _logging, _env
from ..system import NuoyanLibBaseSystem
from .comp import ServerSystem, CF


class NuoyanLibServerSystem(NuoyanLibBaseSystem, ServerSystem):
    _instance = None

    def __init__(self, namespace, system_name):
        ServerSystem.__init__(self, namespace, system_name)
        NuoyanLibBaseSystem.__init__(self)
        NuoyanLibServerSystem._instance = self
        self.query_cache = defaultdict(dict)
        self.unsync_query = {}
        self.callback_data = {}
        self.move_entity_data = {}

        ns, sys_name = s_api.GetEngineNamespace(), s_api.GetEngineSystemName()
        self.native_listen(ns, sys_name, "EntityRemoveEvent", self.EntityRemoveEvent)

        ns, sys_name_c, sys_name_s = _env.LIB_NAME, _env.LIB_CLIENT_NAME, _env.LIB_SERVER_NAME
        self.native_listen(ns, sys_name_c, "UiInitFinished", self.UiInitFinished)
        self.native_listen(ns, sys_name_c, "_BroadcastToAllClient", self._BroadcastToAllClient)
        self.native_listen(ns, sys_name_c, "_NotifyToMultiClients", self._NotifyToMultiClients)
        self.native_listen(ns, sys_name_c, "_NotifyToClient", self._NotifyToClient)
        self.native_listen(ns, sys_name_c, "_SetQueryVar", self._SetQueryVar)
        self.native_listen(ns, sys_name_c, "_NuoyanLibCall", self._NuoyanLibCall)
        self.native_listen(ns, sys_name_c, "_NuoyanLibCallReturn", self._NuoyanLibCallReturn)

        _logging.info("NuoyanLibServerSystem inited")

    def Destroy(self):
        NuoyanLibBaseSystem.Destroy(self)
        from ..listener import unlisten_all_events
        for system in _env.SERVER_SYSTEMS.values():
            unlisten_all_events(system)

    # region Events ====================================================================================================

    def EntityRemoveEvent(self, args):
        entity_id = args['id']
        if entity_id in CF._cache:
            del CF._cache[entity_id]

    def UiInitFinished(self, args):
        player_id = args['__id__']
        if self.query_cache:
            query_args = {
                eid: query_dict.items()
                for eid, query_dict in self.query_cache.items()
            }
            self.NotifyToClient(player_id, "_SetQueryVar", query_args)
        self.sync_all(player_id)

    # endregion

    # region Broadcast =================================================================================================

    def _BroadcastToAllClient(self, args):
        event_name = args['event_name']
        event_data = args['event_data']
        ns = args['ns']
        sys_name = args['sys_name']
        if isinstance(event_data, dict) and '__id__' in args:
            event_data['__id__'] = args['__id__']
        ServerSystem(ns, sys_name).BroadcastToAllClient(event_name, event_data)

    def _NotifyToMultiClients(self, args):
        player_ids = args['player_ids']
        event_name = args['event_name']
        event_data = args['event_data']
        ns = args['ns']
        sys_name = args['sys_name']
        if isinstance(event_data, dict) and '__id__' in args:
            event_data['__id__'] = args['__id__']
        ServerSystem(ns, sys_name).NotifyToMultiClients(player_ids, event_name, event_data)

    def _NotifyToClient(self, args):
        player_id = args['player_id']
        event_name = args['event_name']
        event_data = args['event_data']
        ns = args['ns']
        sys_name = args['sys_name']
        if isinstance(event_data, dict) and '__id__' in args:
            event_data['__id__'] = args['__id__']
        ServerSystem(ns, sys_name).NotifyToClient(player_id, event_name, event_data)

    # endregion

    # region set_query_mod_var =========================================================================================

    def _SetQueryVar(self, args):
        player_id = args['__id__']
        del args['__id__']

        for entity_id, query_list in args.items():
            for name, value in query_list:
                self.query_cache[entity_id][name] = value

        players = s_api.GetPlayerList() or []
        players = [pid for pid in players if pid != player_id]
        if players:
            self.NotifyToMultiClients(players, "_SetQueryVar", args)

    def set_query_mod_var(self, entity_id, name, value, sync):
        self.unsync_query[(entity_id, name)] = value
        if sync:
            self.sync_query_mod_var()

    def sync_query_mod_var(self):
        args = defaultdict(list)
        while self.unsync_query:
            (entity_id, name), value = self.unsync_query.popitem()
            args[entity_id].append((name, value))
            self.query_cache[entity_id][name] = value
        if args:
            self.BroadcastToAllClient("_SetQueryVar", args)

    # endregion

    # region call ======================================================================================================

    def _NuoyanLibCall(self, args):
        ns = args['ns']
        sys_name = args['sys_name']
        method = args['method']
        delay_ret = args['delay_ret']
        call_args = args['args']
        call_kwargs = args['kwargs']
        uuid = args['uuid']
        player_id = args['__id__']
        if uuid:
            def callback(*cb_args):
                ret_args = {'uuid': uuid, 'cb_args': cb_args}
                self.NotifyToClient(player_id, "_NuoyanLibCallReturn", ret_args)
        else:
            callback = None
        from ...common.communicate import _call_local
        _call_local(ns, sys_name, method, callback, delay_ret, call_args, call_kwargs)

    def _NuoyanLibCallReturn(self, args):
        uuid = args['uuid']
        cb_args = args['cb_args']
        from ...common.communicate import _call_callback
        _call_callback(uuid, -1, cb_args)

    # endregion

    # region move_entity ======================================================================================================

    def Update(self):
        for entity_id in self.move_entity_data.keys():
            self._move_entity_next(entity_id)

    def move_entity(self, entity_id, direction, dist, move_time, easing):
        h = 1e-8
        dist_func = lambda x: dist * easing(x)
        speed_func = lambda x: (dist_func(x + h) - dist_func(x - h)) / (2 * h)
        cf = CF(entity_id)
        if cf.EngineType.GetEngineType() == EntityType.Player:
            set_motion = cf.ActorMotion.SetPlayerMotion
        else:
            set_motion = cf.ActorMotion.SetMotion
        move_time = int(move_time * 30)
        self.move_entity_data[entity_id] = {
            'direction': direction,
            'speed_func': speed_func,
            'set_motion': set_motion,
            'move_time': move_time,
            'tick': move_time,
            # 'p': cf.Pos.GetFootPos(),
        }
        set_motion((0, 0, 0))
        self._move_entity_next(entity_id)

    def _move_entity_next(self, entity_id):
        data = self.move_entity_data[entity_id]
        direction = data['direction']
        speed_func = data['speed_func']
        set_motion = data['set_motion']
        move_time = data['move_time']
        data['tick'] -= 1
        t = 1 - data['tick'] / move_time
        if t < 1:
            motion = vec_mul(direction, speed_func(t))
            set_motion(motion)
        else:
            del self.move_entity_data[entity_id]
            set_motion((0, 0, 0))

    # endregion


def instance():
    if not NuoyanLibServerSystem._instance:
        NuoyanLibServerSystem._instance = s_api.GetSystem(_env.LIB_NAME, _env.LIB_SERVER_NAME)
    return NuoyanLibServerSystem._instance




















