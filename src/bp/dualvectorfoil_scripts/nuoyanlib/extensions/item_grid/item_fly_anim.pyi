# -*- coding: utf-8 -*-
#  ================================================
#  ⠀
#    Copyright (c) 2026 Nuoyan
#  ⠀
#    Author: Nuoyan <https://github.com/charminglee>
#    Email : 1279735247@qq.com
#    Date  : 2026-9-8
#  ⠀
#  ================================================


from typing import Union, List, Optional
from mod.client.ui.screenNode import ScreenNode
from mod.client.ui.controls.baseUIControl import BaseUIControl
from mod.client.ui.controls.itemRendererUIControl import ItemRendererUIControl
from ...core._types._typing import FTuple2, Self


_NAMESPACE: str
_ITEM_FLY_PANEL_NAME: str
_UI_NAME_ITEM_FLY_PANEL: str
_UI_PATH_FLY_ITEM_0: str


class ItemFlyAnim(object):
    __screen_node: ScreenNode
    _item_fly_queue: List[int]
    _fly_ir: List[ItemRendererUIControl]
    item_fly_panel: Optional[BaseUIControl]
    def __init__(self: Self, screen_node: ScreenNode) -> None: ...
    def Create(self) -> None: ...
    def _clone_new_ir(self) -> Optional[ItemRendererUIControl]: ...
    def _get_idle_ir_index(self) -> int: ...
    def PlayItemFlyAnim(
        self,
        item_dict: dict,
        from_pos: FTuple2,
        to_pos: FTuple2,
        ui_size: Union[float, FTuple2],
    ) -> bool: ...
