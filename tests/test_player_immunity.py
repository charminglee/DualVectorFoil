# -*- coding: utf-8 -*-
"""二向箔玩家免疫与旧状态清理的离线回归测试。"""

import unittest
from copy import deepcopy

import test_effect_events as fixtures

client_api = fixtures.module("mod.client.extraClientApi")
fixtures.sys.modules['mod'].client = fixtures.sys.modules['mod.client']
fixtures.sys.modules['mod.client'].extraClientApi = client_api

from dualvectorfoil_scripts.modules.foil.client import FoilClient
from dualvectorfoil_scripts.modules.foil.server import FlatEntities
from dualvectorfoil_scripts.modules.foil.config import ATTR


class StoredData(object):
    """保存旧玩家标记并记录读写。"""

    def __init__(self, value=None):
        self.value = value
        self.writes = []

    def GetExtraData(self, key):
        return self.value

    def SetExtraData(self, key, value):
        self.writes.append(value)
        self.value = value
        return True

    GetAttr = GetExtraData
    SetAttr = SetExtraData


class EntityComponents(object):
    """记录位置、重力、AI 和渲染修改，避免依赖游戏。"""

    def __init__(self, kind):
        self.kind = kind
        self.ExtraData = StoredData()
        self.ModAttr = StoredData()
        self.EngineType = self.Dimension = self.Pos = self.Gravity = self
        self.Attr = self.ControlAi = self.ActorRender = self
        self.calls = []
        self.geometry_ok = True
        self.rebuild_ok = True

    def GetEngineTypeStr(self):
        return self.kind

    def GetEntityDimensionId(self):
        return 0

    def GetFootPos(self):
        return (0.5, 1.0, 0.5)

    def SetFootPos(self, pos):
        self.calls.append(('pos', pos))

    def SetGravity(self, value):
        self.calls.append(('gravity', value))

    def SetPersistent(self, value):
        self.calls.append(('persistent', value))

    def SetBlockControlAi(self, *args):
        self.calls.append(('ai', args))

    def GetActorRenderParams(self, *args):
        return ['default']

    def AddPlayerGeometry(self, key, geometry):
        self.calls.append(('player_geometry', key, geometry))
        return self.geometry_ok

    def SetPlayerItemInHandVisible(self, value):
        self.calls.append(('hand_visible', value))
        return True

    def RebuildPlayerRender(self):
        self.calls.append(('rebuild_player',))
        return self.rebuild_ok

    def AddGeometryToOneActor(self, entity_id, key, geometry):
        self.calls.append(('actor_geometry', entity_id, key, geometry))
        return True

    def RebuildRenderForOneActor(self):
        self.calls.append(('rebuild_actor',))
        return True


class PlayerImmunityTests(unittest.TestCase):
    """玩家不得捕获、恢复冻结或替换模型，非玩家仍可二维化。"""

    def setUp(self):
        self.components = {
            'player': EntityComponents("minecraft:player"),
            'pig': EntityComponents("minecraft:pig"),
        }
        self.tracker = FlatEntities()
        self.client = FoilClient("DualVectorFoil", "FoilClient")
        self.fields = {'0': {'origin': [0, 0, 0], 'run_id': "test"}}
        self.object_sets = {'0': {(0, 0, 0)}}
        self.player_data = {
            'kind': "minecraft:player",
            'dimension': 0,
            'pos': (10.5, 2.0, 10.5),
            'run_id': "old",
        }
        for library in (fixtures.library.server, fixtures.library.client):
            if hasattr(library, "CF"):
                self.addCleanup(setattr, library, "CF", library.CF)
            else:
                self.addCleanup(delattr, library, "CF")
            library.CF = lambda entity_id: self.components[entity_id]
        had_motion = hasattr(fixtures.library.server, "set_motion")
        old_motion = getattr(fixtures.library.server, "set_motion", None)
        if had_motion:
            self.addCleanup(setattr, fixtures.library.server, "set_motion", old_motion)
        else:
            self.addCleanup(delattr, fixtures.library.server, "set_motion")
        fixtures.library.server.set_motion = lambda entity_id, value: (
            self.components[entity_id].calls.append(('motion', value))
        )

    def test_touching_player_is_not_captured_or_modified(self):
        self.tracker._visit("player", self.fields, self.object_sets)
        player = self.components['player']
        self.assertNotIn('player', self.tracker.active)
        self.assertEqual(player.calls, [])
        self.assertEqual(player.ExtraData.writes, [])
        self.assertEqual(player.ModAttr.writes, [])

    def test_saved_player_marker_is_cleared_before_restore(self):
        player = self.components['player']
        player.ExtraData.value = deepcopy(self.player_data)
        player.ModAttr.value = deepcopy(self.player_data)
        self.tracker._visit("player", self.fields, self.object_sets)
        self.assertNotIn('player', self.tracker.active)
        self.assertIsNone(player.ExtraData.value)
        self.assertIsNone(player.ModAttr.value)
        self.assertEqual(player.calls, [('gravity', 0.0)])
        self.tracker._visit("player", self.fields, self.object_sets)
        self.assertEqual(player.calls, [('gravity', 0.0)])

    def test_active_player_is_released_without_position_or_motion_writes(self):
        self.tracker.active['player'] = deepcopy(self.player_data)
        self.tracker.hold()
        self.assertNotIn('player', self.tracker.active)
        self.assertEqual(self.components['player'].calls, [('gravity', 0.0)])

    def test_synced_only_player_marker_is_cleared(self):
        player = self.components['player']
        player.ModAttr.value = deepcopy(self.player_data)
        self.tracker._visit("player", {}, {})
        self.assertIsNone(player.ModAttr.value)
        self.assertEqual(player.calls, [('gravity', 0.0)])

    def test_touching_nonplayer_still_captures_and_holds(self):
        self.tracker._visit("pig", self.fields, self.object_sets)
        self.assertIn('pig', self.tracker.active)
        self.assertIn(('gravity', -0.000001), self.components['pig'].calls)
        self.assertIn(('motion', (0.0, 0.0, 0.0)), self.components['pig'].calls)
        self.assertIn(('persistent', True), self.components['pig'].calls)

    def test_player_with_stale_tag_never_installs_flat_geometry(self):
        self.components['player'].ModAttr.value = deepcopy(self.player_data)
        self.client._apply("player")
        self.assertNotIn('player', self.client.applied)
        self.assertEqual(self.components['player'].calls, [])

    def test_existing_flat_player_geometry_is_restored(self):
        self.client.applied['player'] = (
            "minecraft:player", {'default': "geometry.humanoid.customSlim"},
        )
        self.client._apply("player")
        self.assertNotIn('player', self.client.applied)
        self.assertEqual(self.components['player'].calls, [
            ('player_geometry', 'default', "geometry.humanoid.customSlim"),
            ('hand_visible', True), ('rebuild_player',),
        ])

    def test_failed_player_render_restore_keeps_retry_record(self):
        self.client.applied['player'] = (
            "minecraft:player", {'default': "geometry.humanoid.custom"},
        )
        self.components['player'].rebuild_ok = False
        self.client._restore_player("player")
        self.assertIn('player', self.client.applied)

    def test_nonplayer_still_receives_flat_geometry(self):
        self.components['pig'].ModAttr.value = {'kind': "minecraft:pig"}
        self.client._apply("pig")
        self.assertIn('pig', self.client.applied)
        self.assertTrue(any(call[0] == 'actor_geometry'
                            for call in self.components['pig'].calls))


if __name__ == "__main__":
    unittest.main()
