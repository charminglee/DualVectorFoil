# -*- coding: utf-8 -*-
#  ================================================
#  ⠀
#    Copyright (c) 2026 Nuoyan
#  ⠀
#    Author: Nuoyan <https://github.com/charminglee>
#    Email : 1279735247@qq.com
#    Date  : 2026-10-4
#  ⠀
#  ================================================


if bool(0):
    from typing import Any
    from ..screen_node import NyScreenNode, NyScreenProxy


import math
from ....core import error
from ....core._utils import get_func, kwargs_defaults, try_exec, cached_property
from ....core._types._checker import args_type_check
from ....core.client.comp import ScreenNode, ViewBinder
from ....core.listener import listen_event, unlisten_event
from ....common.enum import ClientEvent
from ..ui_utils import _UIControlType
from .control import NyControl


__all__ = [
    "NyGridData",
    "ElemGroup",
    "NyGrid",
]


# 网格元素待渲染标记：引擎尚未创建对应元素时，先在渲染快照中占位，
# 待网格尺寸变更事件（引擎创建出新元素后）到来时自动补渲染
_RENDER_PENDING = object()


def _data_eq(a, b):
    # 判断两次渲染的数据是否等价；等价则跳过重渲染
    if a is b:
        return True
    try:
        return bool(a == b)
    except Exception:
        return False


class NyGridData(list):
    """
    网格数据对象，参照 React 的数据流设计，实现数据驱动的网格自动管理。

    网格数据对象本身即数据源（继承于列表），只需像操作列表一样操作数据，
    每次修改都会自动对网格进行增量刷新，无需手动调用刷新接口。

    设计逻辑与 React 的对应关系：

    - ``NyGridData`` 相当于组件的 state，是唯一数据源；
    - ``render_func`` 渲染函数相当于组件的 render，声明每个元素如何展示数据；
    - 修改数据相当于 setState，触发网格自动刷新；
    - 自动刷新基于数据对比实现（相当于 React 的协调），只有数据发生变化的元素才会被重渲染；
    - ``refresh()`` 相当于 forceUpdate，用于原地修改数据对象内部后的强制刷新。

    说明
    ----

    - 渲染函数接受三个参数：元素的 NyControl 实例、元素对应的数据、元素索引。
    - 由于网格元素的位置是固定的，数据始终按索引顺序对齐渲染，因此无需 React 的 key 机制。
    - 初始化时传入的 ``src`` 会被复制，之后两者互不影响（与 React 中 props 与 state 的关系一致）。
    - 数据量超过网格容量时，超出部分不会被渲染；设置 ``auto_size=True`` 后，网格容量将自动跟随数据长度。

    示例
    ----

    >>> def render_item(cell, item, index):
    ...     cell.text = item["name"]
    >>> data = nyl.NyGridData([{"name": "苹果"}, {"name": "香蕉"}], render_item)
    >>> self.grid.bind_data(data)
    >>> data.append({"name": "樱桃"})   # 修改数据即自动增量刷新，只渲染新增的元素
    >>> data[0] = {"name": "梨"}        # 只重渲染该元素
    >>> data[0]["name"] = "桃"          # 原地修改数据对象内部不会触发自动刷新
    >>> data.refresh(0)                 # 强制重渲染索引为 0 的元素
    >>> data.refresh()                  # 强制重渲染所有元素

    参见
    ----

    - ``NyGrid.bind_data()`` -- 将网格数据对象绑定到网格。

    -----

    :param iterable src: 网格初始数据；默认为空
    :param function render_func: 渲染函数，接受三个参数，分别为元素的 NyControl 实例、元素对应的数据、元素索引；也可在绑定前通过属性赋值设置；绑定网格时该函数必须可调用
    :param Any default: 默认数据；当网格容量大于数据长度时，超出部分将使用默认数据渲染；默认为 None
    :param bool|None auto_size: 是否将网格容量自动同步为数据长度；默认为 None，表示自动判断——StackGrid 或已配置 ``cell_visible_binding`` 的网格自动开启，其余关闭；设为 True 或 False 可强制指定
    """

    def __init__(self, src=(), render_func=None, default=None, auto_size=None):
        list.__init__(self, src)
        self.render_func = render_func
        self.default = default
        self.auto_size = auto_size
        self.grid = None
        self._rendered = []

    def _notify(self):
        if self.grid is not None:
            self.grid._refresh_data(self)

    def refresh(self, index=None):
        """
        强制重渲染网格元素（相当于 React 的 forceUpdate）。

        说明
        ----

        常规的修改数据操作会自动增量刷新网格，无需调用本接口。
        当原地修改了数据对象内部（如修改了列表中字典的值）时，自动刷新无法感知这类变化，
        需调用本接口强制刷新。

        示例
        ----

        >>> data[0]["count"] += 1
        >>> data.refresh(0) # 只强制重渲染索引为 0 的元素
        >>> data.refresh()  # 强制重渲染所有元素

        参见
        ----

        - ``NyGrid.bind_data()`` -- 将网格数据对象绑定到网格。

        -----

        :param int|None index: 元素索引，支持负数索引；默认为 None，表示重渲染所有元素

        :return: 无
        :rtype: None

        :raise TypeError: index 不是 int 时抛出
        :raise IndexError: index 超出网格容量范围时抛出
        """
        if index is not None and not isinstance(index, int):
            raise TypeError("'index' must be int, not %s" % type(index).__name__)
        if self.grid is not None:
            self.grid._refresh_data(self, force=True, index=index)

    def __setitem__(self, index, value):
        """设置元素，并自动增量刷新绑定的网格。"""
        list.__setitem__(self, index, value)
        self._notify()

    def __delitem__(self, index):
        """删除元素，并自动增量刷新绑定的网格。"""
        list.__delitem__(self, index)
        self._notify()

    def append(self, item):
        """追加元素，并自动增量刷新绑定的网格。"""
        list.append(self, item)
        self._notify()

    def extend(self, other):
        """追加多个元素，并自动增量刷新绑定的网格。"""
        list.extend(self, other)
        self._notify()

    def insert(self, index, item):
        """插入元素，并自动增量刷新绑定的网格。"""
        list.insert(self, index, item)
        self._notify()

    def pop(self, index=-1):
        """移除元素，并自动增量刷新绑定的网格。"""
        item = list.pop(self, index)
        self._notify()
        return item

    def remove(self, item):
        """移除元素，并自动增量刷新绑定的网格。"""
        list.remove(self, item)
        self._notify()

    def reverse(self):
        """反转元素顺序，并自动增量刷新绑定的网格。"""
        list.reverse(self)
        self._notify()

    def sort(self, cmp=None, key=None, reverse=False):
        """排序元素，并自动增量刷新绑定的网格。"""
        list.sort(self, cmp, key, reverse)
        self._notify()

    def __iadd__(self, other):
        list.extend(self, other)
        self._notify()
        return self


def _process_grid_index(index, l):
    if isinstance(index, int):
        if index < 0:
            index += l
        if index < 0 or index >= l:
            raise IndexError("NyGrid index out of range")
        return [index]
    else:
        return range(*index.indices(l))


def _index_2_coord(i, dx):
    return i % dx, i / dx


def _coord_2_index(x, y, dx):
    return y * dx + x


class ElemGroup(object):
    __slots__ = ('grid', 'cell_list', '_len')

    _ALLOWED_SET_ATTRS = (
        'position',
        'anchor_from',
        'anchor_to',
        'clip_offset',
        'clip_children',
        'full_position_x',
        'full_position_y',
        'full_size_x',
        'full_size_y',
        'global_position',
        'max_size',
        'min_size',
        'size',
        'visible',
        'alpha',
        'layer',
        'touch_enable',
        'property_bag',
    )
    _ALLOWED_GET_ATTRS = (
        'name',
        'path',
        'parent_path',
        'parent',
        'position',
        'anchor_from',
        'anchor_to',
        'clip_offset',
        'clip_children',
        'full_position_x',
        'full_position_y',
        'full_size_x',
        'full_size_y',
        'global_position',
        'max_size',
        'min_size',
        'size',
        'visible',
        'layer',
        'property_bag',
    )
    _ALLOWED_METHODS = (
        # 'to_button',
        # 'to_image',
        # 'to_label',
        # 'to_input_panel',
        # 'to_stack_panel',
        # 'to_edit_box',
        # 'to_netease_paper_doll',
        # 'to_item_renderer',
        # 'to_scroll_view',
        # 'to_grid',
        # 'to_progress_bar',
        # 'to_toggle',
        # 'to_slider',
        # 'to_selection_wheel',
        # 'to_combo_box',
        # 'to_mini_map',
        'add_child',
        'clone_from',
        'SetPosition',
        'SetFullSize',
        'GetFullSize',
        'SetFullPosition',
        'GetFullPosition',
        'SetAnchorFrom',
        'GetAnchorFrom',
        'SetAnchorTo',
        'GetAnchorTo',
        'SetClipOffset',
        'GetClipOffset',
        'SetClipsChildren',
        'GetClipsChildren',
        'SetMaxSize',
        'GetMaxSize',
        'SetMinSize',
        'GetMinSize',
        'GetPosition',
        'GetGlobalPosition',
        'SetSize',
        'GetSize',
        'SetVisible',
        'GetVisible',
        'SetTouchEnable',
        'SetAlpha',
        'SetLayer',
        'GetPath',
        'GetChildByName',
        'GetChildByPath',
        'resetAnimation',
        'PauseAnimation',
        'PlayAnimation',
        'StopAnimation',
        'SetAnimation',
        'RemoveAnimation',
        'SetAnimEndCallback',
        'RemoveAnimEndCallback',
        'IsAnimEndCallbackRegistered',
        'GetPropertyBag',
        'SetPropertyBag',
    )

    def __init__(self, grid, cell_list):
        self.grid = grid
        self.cell_list = cell_list
        self._len = len(cell_list)

    def __iter__(self):
        return iter(self.cell_list)

    def __len__(self):
        return self._len

    @args_type_check((int, slice))
    def __getitem__(self, item):
        return self.cell_list[item]

    def __setattr__(self, key, value):
        if key in ElemGroup.__slots__:
            object.__setattr__(self, key, value)
        if key not in ElemGroup._ALLOWED_SET_ATTRS:
            raise AttributeError("can't set attribute '%s' to ElemGroup object" % key)
        # 批量设置属性
        for cell in self.cell_list:
            setattr(cell, key, value)

    def __getattr__(self, key):
        if key in ElemGroup._ALLOWED_GET_ATTRS:
            # 批量获取属性
            return [getattr(cell, key) for cell in self.cell_list]
        elif key in ElemGroup._ALLOWED_METHODS:
            # 批量调用方法
            def func(*args, **kwargs):
                res = []
                for cell in self.cell_list:
                    res.append(getattr(cell, key)(*args, **kwargs))
                return res
            return func
        raise AttributeError("can't get attribute '%s' from ElemGroup object" % key)


class NyGrid(NyControl):
    """
    网格控件类。

    -----

    关于 ``cell_visible_binding`` 与 ``collection_name`` 参数的说明：

    - 该参数用于 ``.grid_size`` 、 ``.dimension`` 等接口，实现动态设置网格元素的数量（多余元素将通过设置 ``visible`` 为 ``False`` 的方式隐藏），不使用该接口可忽略这两个参数。
    - 由于网格控件的特性，设置元素的 ``visible`` 需要使用绑定，请在你的 **网格模板控件** 的 json 中添加以下绑定，然后将 ``"binding_name"`` 的值设置给 ``cell_visible_binding`` 参数 。
    ::

        "bindings": [
            {
                "binding_type": "collection",
                "binding_collection_name": "grid_collection_name", //此处需要与网格的"collection_name"字段相同
                "binding_name": "#namespace.binding_name", //可自定义
                "binding_name_override": "#visible",
                "binding_condition": "always"
            }
        ]
    - 最后，将 **网格** json 中的 ``"collection_name"`` 字段的值设置给 ``collection_name`` 参数即可。

    示例
    ----

    >>> self.grid = nyl.NyGrid(self, "/panel/grid")
    >>> self.grid.dimension = (3, 2)
    >>> self.first_cell = self.grid[0]

    参见
    ----

    - ``NyGridData`` -- 网格数据对象，参照 React 的数据流设计，实现数据驱动的网格自动管理。
    - ``NyControl.to_gird()`` -- 将通用控件实例转换为网格控件实例。

    -----

    :param NyScreenNode|NyScreenProxy ny_screen_node: 持有该网格控件的 NyScreenNode 或 NyScreenProxy 实例
    :param str path: 控件路径
    :param bool is_stack_grid: [仅关键字参数] 是否是 StackGrid；默认为 False
    :param str template_name: [仅关键字参数] 网格模板控件名称，即 "grid_item_template" 字段或UI编辑器中的网格“内容”所使用的控件；仅模板控件名称以数字结尾时需要传入该参数
    :param str cell_visible_binding: [仅关键字参数] 用于控制网格元素 visible 的绑定名称，详见上方说明
    :param str collection_name: [仅关键字参数] 网格集合名称，详见上方说明
    """

    CONTROL_TYPE = _UIControlType.GRID

    UPDATE = 1 << 0
    LOADED = 1 << 1

    @kwargs_defaults(
        is_stack_grid=False,
        template_name="",
        cell_visible_binding="",
        collection_name="",
    )
    def __init__(self, ny_screen_node, path, **kwargs):
        NyControl.__init__(self, ny_screen_node, path)

        self.__grid_size = -1
        self._callback_map = {
            NyGrid.UPDATE: [],
            NyGrid.LOADED: [],
        }
        self._loaded = False
        self.is_stack_grid = kwargs['is_stack_grid']
        self.gd_obj = None

        template_name = kwargs['template_name']
        if template_name and "." in template_name:
            template_name = template_name.split(".")[-1]
        self.__template_name = template_name

        self.cell_visible_binding = kwargs['cell_visible_binding']
        self.collection_name_ = kwargs['collection_name']
        if self.cell_visible_binding and self.collection_name_:
            self.ny_screen_node.build_binding(
                self._return_cell_visible, ViewBinder.BF_BindBool, self.cell_visible_binding, self.collection_name_
            )

        listen_event(self.__grid_update__, ClientEvent.GridComponentSizeChangedClientEvent)

    def __ui_destroy__(self):
        unlisten_event(self.__grid_update__, ClientEvent.GridComponentSizeChangedClientEvent)
        self.ny_screen_node.unbuild_binding(self._return_cell_visible)
        if self.gd_obj is not None:
            self.gd_obj.grid = None
        self.gd_obj = None
        self._callback_map = None
        NyControl.__ui_destroy__(self)

    def __grid_update__(self, args):
        path = args['path']
        idx = path.index("/", 1)
        root_name = path[1: idx]
        if root_name != self._screen_node.name:
            return
        path = path[idx:]
        if path != self.path:
            return

        if self.gd_obj:
            # 引擎事件到来说明网格元素可能已重建，进行一次协调以补渲染待渲染元素
            try_exec(self._refresh_data, self.gd_obj)
        if not self._loaded:
            self._loaded = True
            for func in self._callback_map[NyGrid.LOADED]:
                try_exec(func)
        for func in self._callback_map[NyGrid.UPDATE]:
            try_exec(func)

    # region Properties ================================================================================================

    @cached_property
    def template_name(self):
        """
        [只读属性]

        网格模板控件名称。

        即 ``"grid_item_template"`` 字段或UI编辑器中的网格“内容”所使用的控件。

        :rtype: str
        """
        if not self.__template_name:
            children_names = self._screen_node.GetChildrenName(self.path)
            if children_names:
                name = children_names[0]
                for i in name[::-1]:
                    if not i.isdigit():
                        return name[:int(i) + 1]
        else:
            return self.__template_name

    @property
    def rows(self):
        """
        [只读属性]

        按行获取网格所有元素的二维列表，第一维为行（y 坐标），第二维为列（x 坐标）。

        元素获取不到时对应位置为 None。

        :rtype: list[list[NyControl|None]]
        """
        dx, dy = self.dimension
        return [
            [self.get_cell(y * dx + x) for x in xrange(dx)]
            for y in xrange(dy)
            ]

    @property
    def columns(self):
        """
        [只读属性]

        按列获取网格所有元素的二维列表，第一维为列（x 坐标），第二维为行（y 坐标）。

        元素获取不到时对应位置为 None。

        :rtype: list[list[NyControl|None]]
        """
        dx, dy = self.dimension
        return [
            [self.get_cell(y * dx + x) for y in xrange(dy)]
            for x in xrange(dx)
            ]

    @property
    def grid_size(self):
        """
        [可读写属性]

        网格的容量，即元素数量。

        说明
        ----

        对于非StackGrid网格，设置 ``grid_size`` 不会改变网格的列数。
        例如一个 3x3（3 行 3 列）网格，设置 ``grid_size=5`` 后将变成 2x3，且最末尾元素会被隐藏。
        同理，若设置 ``grid_size=13``，则网格变成 5x3，末尾 2 个元素会被隐藏。

        :rtype: int
        """
        if self.__grid_size < 0:
            bag = self.property_bag
            return bag.get('#grid_number_size', 0) if bag else 0
        else:
            return self.__grid_size

    @grid_size.setter
    def grid_size(self, val):
        """
        [可读写属性]

        网格的容量，即元素数量。

        说明
        ----

        对于非 StackGrid 网格，设置 ``grid_size`` 不会改变网格的列数。
        例如一个 3x3（3 行 3 列）网格，设置 ``grid_size=5`` 后将变成 2x3，且最末尾元素会被隐藏。
        同理，若设置 ``grid_size=13``，则网格变成 5x3，末尾 2 个元素会被隐藏。

        :type val: int
        """
        if val == self.grid_size:
            return
        if val < 0:
            raise ValueError("'grid_size' must be >= 0")
        if self.is_stack_grid:
            self._screen_node.SetStackGridCount(self.path, val)
        else:
            dx, dy = self.dimension
            new_dy = int(math.ceil(float(val) / dx))
            if new_dy != dy:
                self._base_control.SetGridDimension((dx, new_dy))
        self.__grid_size = val

    @property
    def dimension(self):
        """
        [可读写属性]

        获取网格的 xy 大小。

        当网格为 StackGrid 时， y 值固定为 0。

        :rtype: tuple[int,int]
        """
        return NyGrid.__get_dim(self._base_control.mScreenName, self._base_control.FullPath())

    @dimension.setter
    def dimension(self, val):
        """
        [可读写属性]

        设置网格的 xy 大小。

        当网格为 StackGrid 时，忽略传入的 y 值。

        :type val: tuple[int,int]
        """
        if val == self.dimension:
            return
        if self.is_stack_grid:
            if val[0] < 0:
                raise ValueError("'dimension' value must be >= 0")
            self._screen_node.SetStackGridCount(self.path, val[0])
            self.__grid_size = val[0]
        else:
            if val[0] < 0 or val[1] < 0:
                raise ValueError("'dimension' value must be >= 0")
            self._base_control.SetGridDimension(val)
            size = val[0] * val[1]
            if self.__grid_size <= 0 or size < self.__grid_size:
                self.__grid_size = size

    # endregion

    # region Common ====================================================================================================

    @args_type_check((int, slice, tuple))
    def __getitem__(self, item):
        """
        根据特定规则获取网格单个或多个元素。

        获取指定位置的元素：

        - ``grid[i]`` -- 按从左到右从上到下的顺序（下同）获取索引为 i 的元素，支持负数索引。
        - ``grid[x,⠀y]`` -- 获取坐标为 (x, y) 的元素，坐标从 0 开始，向右为X轴正方向，向下为Y轴正方向（下同）。

        利用切片获取多个元素：

        - ``grid[start:stop]`` -- 与列表切片类似，获取索引为 start 到 stop 的元素（不包括 stop，下同）。
        - ``grid[x,⠀start:stop]`` -- 获取指定x坐标上，y坐标为 start 到 stop 的元素。
        - ``grid[start:stop,⠀y]`` -- 获取指定y坐标上，x坐标为 start 到 stop 的元素。
        - ``grid[start1:stop1,⠀start2:stop2]`` -- 获取x坐标为 start1 到 stop1，y坐标为 start2 到 stop2 的元素。

        示例
        ----

        >>> first = self.grid[0]
        >>> top_row = self.grid[:, 0]
        >>> selected = self.grid[0:2]

        -----

        :param int|slice|tuple[int|slice,int|slice] item: 详见上方说明

        :return: 获取单个元素时，返回该元素的 NyControl 实例；获取多个元素时，返回 ElemGroup 对象；获取不到元素时返回 None
        :rtype: NyControl|ElemGroup|None
        """
        dx, dy = self.dimension
        if isinstance(item, tuple):
            x, y = item
            xr = _process_grid_index(x, dx)
            yr = _process_grid_index(y, dy)
            index_list = [_coord_2_index(x, y, dx) for x in xr for y in yr]

        else:
            size = dx * dy
            index_list = _process_grid_index(item, size)

        if not index_list:
            return
        if len(index_list) == 1:
            return self.get_cell(index_list[0])
        else:
            cell_list = [self.get_cell(i) for i in index_list]
            return ElemGroup(self, cell_list)

    def get_cell_index(self, cell):
        """
        获取指定元素在网格中的索引。

        -----

        :param str|NyControl cell: 网格元素的路径或实例

        :return: 元素索引
        :rtype: int
        """
        path = cell if isinstance(cell, str) else cell.path
        return int(path.split(self.template_name)[-1]) - 1

    @args_type_check(NyGridData)
    def bind_data(self, gd):
        """
        绑定网格数据对象，绑定后立即进行首次渲染。

        说明
        ----

        绑定后，修改数据会自动增量刷新网格；网格因引擎事件重建元素（如容量变化）时，也会自动补渲染待渲染的元素。
        将新的数据对象绑定到已绑定数据的网格时，原数据对象将自动解除绑定。

        关于 ``NyGridData`` 的 ``auto_size`` 参数的自动判断：

        - StackGrid 网格：自动开启，元素数量即网格大小；
        - 配置了 ``cell_visible_binding`` 与 ``collection_name`` 的网格：自动开启，可通过绑定隐藏多余元素；
        - 其余网格：自动关闭（避免静默改变网格尺寸），数据量超过容量时超出部分不渲染。

        示例
        ----

        >>> def on_render(cell, item, index):
        ...     cell.text = item
        >>> data = nyl.NyGridData(["第一项", "第二项"], on_render)
        >>> self.grid.bind_data(data)

        参见
        ----

        - ``NyGridData`` -- 网格数据对象。

        -----

        :param NyGridData gd: 网格数据对象

        :return: 无
        :rtype: None

        :raise TypeError: gd 不是 NyGridData 或其 render_func 不可调用时抛出
        """
        if not callable(gd.render_func):
            raise TypeError("'render_func' of NyGridData must be callable")
        if self.gd_obj is not None and self.gd_obj is not gd:
            self.gd_obj.grid = None
        self.gd_obj = gd
        gd.grid = self
        gd._rendered = []
        self._refresh_data(gd)

    def get_cell(self, index):
        """
        获取索引为 ``index`` 的元素的 ``NyControl`` 实例。

        示例
        ----

        >>> cell = self.grid.get_cell(0)
        >>> cell.visible = True

        参见
        ----

        - ``NyGrid.get_all_cells()`` -- 获取网格所有元素的 NyControl 实例。

        -----

        :param int index: 索引

        :return: 元素的 NyControl 实例，获取不到时返回 None
        :rtype: NyControl|None
        """
        return self / (self.template_name + str(index + 1))

    def get_all_cells(self):
        """
        获取网格所有元素的 ``NyControl`` 实例。

        示例
        ----

        >>> for cell in self.grid.get_all_cells():
        ...     cell.visible = True

        参见
        ----

        - ``get_cell()`` -- 获取指定索引的网格元素。

        -----

        :return: 网格所有元素的 NyControl 实例列表
        :rtype: list[NyControl]
        """
        return [self.get_cell(i) for i in xrange(self.grid_size)]

    def set_callback(self, func, *cb_types):
        """
        设置网格回调函数。

        说明
        ----

        支持同时设置多个同类型的回调，例如同时设置两个按钮抬起回调，按设置顺序依次触发。

        示例
        ----

        >>> def on_grid_update(args):
        ...     print(args)
        >>> self.grid.set_callback(on_grid_update, nyl.NyGrid.UPDATE)

        参见
        ----

        - ``NyGrid.remove_callback()`` -- 移除网格回调函数。

        -----

        :param function func: 回调函数
        :param int cb_types: [变长位置参数] 回调类型，请使用 NyGrid 枚举值；可同时传入多个类型

        :return: 无
        :rtype: None
        """
        for t in cb_types:
            lst = self._callback_map[t]
            if func not in lst:
                lst.append(func)

    def remove_callback(self, func, *cb_types):
        """
        移除网格回调函数。

        示例
        ----

        >>> self.grid.remove_callback(on_grid_update, nyl.NyGrid.UPDATE)

        参见
        ----

        - ``NyGrid.set_callback()`` -- 设置网格回调函数。

        -----

        :param function func: 回调函数
        :param int cb_types: [变长位置参数] 回调类型，请使用 NyGrid 枚举值；可同时传入多个类型

        :return: 无
        :rtype: None
        """
        for t in cb_types:
            lst = self._callback_map[t]
            if func in lst:
                lst.remove(func)

    # endregion

    # region Internal ==================================================================================================

    def _need_auto_size(self, gd):
        if gd.auto_size is not None:
            return gd.auto_size
        return self.is_stack_grid or bool(self.cell_visible_binding and self.collection_name_)

    def _try_get_cell(self, index):
        try:
            return self.get_cell(index)
        except error.ControlNotFoundError:
            return None

    def _render_cell(self, gd, index, item):
        cell = self._try_get_cell(index)
        if cell is None:
            return False
        gd.render_func(cell, item, index)
        return True

    def _refresh_data(self, gd, force=False, index=None):
        # 网格数据协调：对比数据与上次渲染快照，只重渲染发生变化的元素
        if index is not None:
            capacity = self.grid_size
            if index < 0:
                index += capacity
            if index < 0 or index >= capacity:
                raise IndexError("NyGridData index out of range")
            item = gd[index] if index < len(gd) else gd.default
            if self._render_cell(gd, index, item):
                snapshot = gd._rendered
                if index < len(snapshot):
                    snapshot[index] = item
                self._screen_node.UpdateScreen()
            return
        if self._need_auto_size(gd) and self.grid_size != len(gd):
            self.grid_size = len(gd)
        capacity = self.grid_size
        snapshot = gd._rendered
        new_snapshot = []
        rendered = False
        for i in xrange(capacity):
            item = gd[i] if i < len(gd) else gd.default
            old = snapshot[i] if i < len(snapshot) else _RENDER_PENDING
            if force or old is _RENDER_PENDING or not _data_eq(old, item):
                if self._render_cell(gd, i, item):
                    new_snapshot.append(item)
                    rendered = True
                else:
                    new_snapshot.append(_RENDER_PENDING)
            else:
                new_snapshot.append(old)
        gd._rendered = new_snapshot
        if rendered:
            self._screen_node.UpdateScreen()

    def _return_cell_visible(self, index):
        return self.visible and (self.__grid_size < 0 or index < self.__grid_size)

    __get_dim = staticmethod(
        get_func( # noqa
            ScreenNode,
            (103, 117, 105),
            (103, 101, 116, 95, 103, 114, 105, 100, 95, 100, 105, 109, 101, 110, 115, 105, 111, 110)
        )
    )

    # endregion

    # region Compatibility =============================================================================================

    set_grid_dimension = SetGridDimension = lambda s, *a, **k: s._base_control.SetGridDimension(*a, **k)
    get_gridd_item     = GetGriddItem     = lambda s, *a, **k: s._base_control.GetGridItem(*a, **k)

    # endregion
