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


from typing import Dict, Union, Tuple, Callable, TypeVar, Optional, Any, List, Iterator, overload, Iterable, Generic, ClassVar
from mod.client.ui.controls.gridUIControl import GridUIControl
from ....core._types._typing import ITuple2, STuple, T, T2, SlotsType, ArgsDict, NyScreenBaseT
from ....core._types._checker import args_type_check
from ....core._utils import cached_property
from .control import NyControl


__NyControlT = TypeVar("__NyControlT", covariant=True, bound=NyControl)
__GridCallbackType = Callable[[], Any]


def _data_eq(a: Any, b: Any) -> bool: ...


class NyGridData(list, Generic[T, T2]):
    render_func: Callable[[NyControl, T, int], Any]
    """
    渲染函数，接受三个参数，分别为元素的 NyControl 实例、元素对应的数据、元素索引。
    
    声明每个元素如何展示数据，相当于 React 组件的 render。绑定网格时该函数必须可调用。
    """
    default: Optional[T2]
    """ 网格容量大于数据长度时，超出部分使用的默认数据。 """
    auto_size: Optional[bool]
    """
    是否将网格容量自动同步为数据长度。
    
    默认为 None，表示自动判断：StackGrid 或已配置 cell_visible_binding 的网格自动开启，其余关闭。
    """
    grid: Optional["NyGrid"]
    """ 当前网格数据对象绑定的网格的 ``NyGrid`` 实例。 """
    _rendered: List[Any]
    def __init__(
        self,
        src: Iterable[T] = (),
        render_func: Optional[Callable[[NyControl, T, int], Any]] = None,
        default: Optional[T2] = None,
        auto_size: Optional[bool] = None,
    ) -> None: ...
    def _notify(self) -> None: ...
    def refresh(self, index: Optional[int] = None) -> None:
        """
        强制重渲染网格元素（相当于 React 的 forceUpdate）。
        
        当原地修改了数据对象内部（如修改了列表中字典的值）时，自动刷新无法感知这类变化，需调用本接口强制刷新。
        """
    def __setitem__(self, index: Union[int, slice], value: Union[T, Iterable[T]]) -> None:
        """ 设置元素，并自动增量刷新绑定的网格。 """
    def __delitem__(self, index: Union[int, slice]) -> None:
        """ 删除元素，并自动增量刷新绑定的网格。 """
    def append(self, item: T) -> None:
        """ 追加元素，并自动增量刷新绑定的网格。 """
    def extend(self, other: Iterable[T]) -> None:
        """ 追加多个元素，并自动增量刷新绑定的网格。 """
    def insert(self, index: int, item: T) -> None:
        """ 插入元素，并自动增量刷新绑定的网格。 """
    def pop(self, index: int = -1) -> T:
        """ 移除元素，并自动增量刷新绑定的网格。 """
    def remove(self, item: T) -> None:
        """ 移除元素，并自动增量刷新绑定的网格。 """
    def reverse(self) -> None:
        """ 反转元素顺序，并自动增量刷新绑定的网格。 """
    def sort(self, cmp: Optional[Callable[..., Any]] = None, key: Optional[Callable[[T], Any]] = None, reverse: bool = False) -> None:
        """ 排序元素，并自动增量刷新绑定的网格。 """
    def __iadd__(self, other: Iterable[T]) -> "NyGridData[T, T2]": ...


def _process_grid_index(index: Union[int, slice], l: int) -> List[int]: ...
def _index_2_coord(i: int, dx: int) -> ITuple2: ...
def _coord_2_index(x: int, y: int, dx: int) -> int: ...


class ElemGroup(Iterable[__NyControlT]):
    __slots__ = ('grid', 'cell_list', '_len')
    _ALLOWED_SET_ATTRS: ClassVar[STuple]
    _ALLOWED_GET_ATTRS: ClassVar[STuple]
    _ALLOWED_METHODS: ClassVar[STuple]
    grid: NyGrid
    cell_list: List[__NyControlT]
    _len: int
    def __init__(self, grid: NyGrid, cell_list: List[__NyControlT]) -> None: ...
    def __iter__(self) -> Iterator[__NyControlT]: ...
    def __len__(self) -> int: ...
    @overload
    def __getitem__(self, item: int) -> __NyControlT: ...
    @overload
    def __getitem__(self, item: slice) -> List[__NyControlT]: ...
    def __setattr__(self, key: str, value: Any) -> None: ...
    def __getattr__(self, key: str) -> Union[List[Any], Callable[[...], List[Any]]]: ...


class NyGrid(NyControl[NyScreenBaseT]):
    UPDATE: ClassVar[int]
    """ 网格元素刷新时触发。 """
    LOADED: ClassVar[int]
    """ 网格初次加载完成时触发。 """
    _base_control: GridUIControl
    __grid_size: int
    __template_name: str
    _callback_map: Dict[int, List[__GridCallbackType]]
    _loaded: bool
    is_stack_grid: bool
    """ 是否是 StackGrid 。 """
    cell_visible_binding: str
    """ 用于控制网格元素 ``visible`` 的绑定名称。 """
    collection_name_: str
    """ 网格集合名称。 """
    gd_obj: Optional[NyGridData]
    """ 绑定到当前网格的网格数据对象。 """
    def __init__(
        self,
        ny_screen_node: NyScreenBaseT,
        path: str,
        *,
        is_stack_grid: bool = False,
        template_name: str = "",
        cell_visible_binding: str = "",
        collection_name: str = "",
    ) -> None: ...
    @args_type_check(str)
    def __truediv__(self, other: str) -> NyControl[NyScreenBaseT]: ...
    __div__ = __truediv__
    def __grid_update__(self, args: ArgsDict) -> None: ...
    @cached_property
    def template_name(self) -> str: ...
    @property
    def rows(self) -> List[List[Optional[NyControl[NyScreenBaseT]]]]: ...
    @property
    def columns(self) -> List[List[Optional[NyControl[NyScreenBaseT]]]]: ...
    @property
    def grid_size(self) -> int: ...
    @grid_size.setter
    def grid_size(self, val: int) -> None: ...
    @property
    def dimension(self) -> ITuple2: ...
    @dimension.setter
    def dimension(self, val: ITuple2) -> None: ...
    @args_type_check((int, slice, tuple))
    def __getitem__(
        self,
        item: Union[int, slice, Tuple[Union[int, slice], Union[int, slice]]]
    ) -> Union[NyControl[NyScreenBaseT], ElemGroup, None]: ...
    def get_cell_index(self, cell: Union[str, NyControl[NyScreenBaseT]]) -> int: ...
    @args_type_check(NyGridData)
    def bind_data(self, gd: NyGridData) -> None: ...
    def _need_auto_size(self, gd: NyGridData) -> bool: ...
    def _try_get_cell(self, index: int) -> Optional[NyControl[NyScreenBaseT]]: ...
    def _render_cell(self, gd: NyGridData, index: int, item: Any) -> bool: ...
    def _refresh_data(self, gd: NyGridData, force: bool = ..., index: Optional[int] = ...) -> None: ...
    def get_cell(self, index: int) -> Optional[NyControl[NyScreenBaseT]]: ...
    def get_all_cells(self) -> List[NyControl[NyScreenBaseT]]: ...
    def set_callback(
        self,
        func: __GridCallbackType,
        *cb_types: int
    ) -> None: ...
    def remove_callback(
        self,
        func: __GridCallbackType,
        *cb_types: int
    ) -> None: ...
    def _return_cell_visible(self, index: int) -> bool: ...
    set_grid_dimension = SetGridDimension = GridUIControl.SetGridDimension
    get_gridd_item = GetGriddItem = GridUIControl.GetGridItem
