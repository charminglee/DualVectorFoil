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

from typing import List, Optional, Dict, Tuple
from mod.client.system.clientSystem import ClientSystem
from ...core._types._typing import Self, ArgsDict
from ...core._utils import singleton
from ...core.listener import _lib_sys_event, ClientEventProxy


@singleton
class ItemGridClient(ClientEventProxy, ClientSystem):
    item_grid_path: Dict[str, Tuple[str, bool]]
    item_grid_size: Dict[str, int]
    item_grid_items: Dict[str, List[Optional[dict]]]
    registered_keys: Dict[str, List[str]]
    def __init__(self: Self, namespace: str, system_name: str) -> None: ...
    @_lib_sys_event
    def _UpdateItemGrids(self, args: ArgsDict) -> None: ...
    def register_item_grid(self, key: str, ui_cls_path: str, path: str, size: int, is_single: bool) -> bool: ...
