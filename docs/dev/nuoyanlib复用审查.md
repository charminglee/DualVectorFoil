# nuoyanlib 复用审查

审查日期：2026-11-13。

## 范围与方法

检查项目自有的 38 个运行时 Python 文件（含入口、公共配置、模块基类、业务模块、模板和运行时测试入口），同时检查离线测试、构建工具和资源生成路径。以项目内实际附带的 nuoyanlib 源码及导出表为准，没有升级或修改库、模板和公共工具。

专用 MCP 架构扫描和引用链扫描工具不可用，本次按 AGENTS.md 授权使用本地源码、AST 导入关系及 ModSDK 随附接口文档替代；没有执行专用 MCP 扫描。未启动游戏或使用 Computer Use。

## 已完成的等价复用

| 业务位置 | 原实现 | 使用的库接口 | 保留的语义 |
| --- | --- | --- | --- |
| `modules/foil/server.py:entity_contact_candidates` | 手工逐轴 floor | `nyl.pos_floor` | 负坐标向下取整；支撑点优先；脚底点去重；支撑高度偏移仍为 0.01 |
| `modules/foil/server.py:_launch` | SDK 朝向转换、逐轴加乘 | `nyl.rot2dir`、`nyl.vec_add`、`nyl.vec_mul` | 出生点向前 1.5 格，轨迹继续沿三维朝向前进配置距离 |
| `modules/foil/server.py:_launch` | 直接调用投射物组件并构造参数字典 | `nyl.launch_projectile` | 显式传入 position、direction 及 power/gravity/damage=0；保留创建失败、运动失败、消耗失败和冷却处理 |
| `modules/foil/server.py:_detonate` | 手工 floor 列表 | `list(nyl.pos_floor(pos))` | 保留列表类型与最终静止格点高度 |
| `modules/foil/server.py:_missing_chunks` | 手工 X/Z 除以 16 | `nyl.chunk_pos` | 保持二维区块键、负坐标和区块依赖索引 |
| `modules/effect/playback.py:start` | 手工计算长度并归一化 | `nyl.vec_length`、`nyl.vec_normalize` | 仍在长度大于 0.001 时归一化，否则使用向上方向；方向仅在触发时计算 |
| `modules/effect/atmosphere.py:update` | RGB 手工线性插值 | `nyl.lerp` | 相同目标颜色、包络和 alpha=1；只可能存在代数运算顺序导致的浮点末位差异 |

`launch_projectile` 会补充 `isDamageOwner=False`。本机 `E:/MCMod/Tools/ModSDK/mod/server/component/projectileCompServer.py` 的接口文档确认原接口默认不伤害创建者，因此与原先省略该字段一致。零值参数在库中按 `is not None` 判断，不会被当作缺省参数丢弃。

新增调用经入口导出检查：向量和数学接口由 common 导出到两端，投射物接口仅由 server 导出。业务引用链仍为：

- 服务端：`modMain -> foil.server -> _base.server / foil.palette / foil.deferred / nuoyanlib.server`。
- 客户端：`modMain -> effect.client -> effect.playback / effect.atmosphere -> nuoyanlib.client`。
- 离线验证：组件替身仅加载选定的真实库函数，不执行库入口或 SDK 初始化，也不复制库实现。

## 已使用库能力，无须重复改写

| 范围 | 当前复用情况 |
| --- | --- |
| 模组入口与注册 | `nuoyanlib.run`、`NyClientSystem`、`NyServerSystem`、模块枚举注册表、`nyl.get_system` |
| 事件 | 自定义事件使用 `nyl.event`；引擎同名回调由 `NySystemMeta` 自动套用 event，无须再加第二套监听 |
| 组件 | 业务统一通过 `nyl.CF`、`nyl.LvComp` 获取组件 |
| 实体与物品 | `nyl.get_all_entities`、`nyl.set_motion`、`nyl.deduct_inv_item` |
| 距离 | 客户端 `nyl.distance`、服务端观看者粗筛 `nyl.distance_square` |
| 常量 | 已使用库的 `StrEnum`、`Enum`、`auto`、`ordered` |

## 当前保留的实现

| 代码或能力 | 相关库接口 | 不直接替换的原因 |
| --- | --- | --- |
| 单个非玩家实体的几何替换和重建 | `add_entity_render_resources` | 库内部调用 `AddActorGeometry(etype, ...)`、`RebuildActorRender(etype)`，按实体类型修改；业务调用 `AddGeometryToOneActor`、`RebuildRenderForOneActor`，只修改被标记的单个实体。替换会扩大影响范围 |
| 投射物轨迹运动 | `move_entity`、`start_mover` | 库不返回运动器 ID 或启动成功状态；`move_entity` 的穿墙分支还是空实现。业务必须保存 motion_id、处理失败并匹配实际停止事件 |
| 静止时清速度 | `set_motion` | 此处必须检查 `SetMotion` 成功与否；库封装返回 None，不能替代现有条件判断。其他无需检查返回值的冻结路径已使用库接口 |
| 粒子创建 | `spawn_particle` | 库会在 Create 后额外调用 `EmitManually`，当前业务只调用 Create。是否改为手工发射会影响现有发射器行为，需要另外确认；本次保留 |
| 稀疏调色板、状态/含水层/NBT、Morton 映射 | 方块工具、NBT 模块 | 库没有对应的批量稀疏调色板迁移、可逆三维到二维映射或 NBT 重定位实现；NBT 模块当前无实际函数 |
| `palette.py`、`deferred.py` 的球内筛选、空间分区与引用队列 | `is_in_sphere`、`chunk_pos`、位置生成器 | 热循环处理的是紧凑索引、三维分区及配对引用，库接口不对应这些数据结构；公共纯算法保持不导入 SDK，不枚举额外空气格点 |
| `effect/config.py` 限幅与 `timeline.py` 三次平滑包络 | `clamp`、`Curve.Easing` | 配置与时间轴保持纯算法；从库包入口导入会引入 SDK 初始化。现有 smoothstep 也不等于 IN_OUT_CUBIC 等预设缓动，不更换时间曲线 |
| `BusinessLog` | 库内部 `_logging`、`call_interval` | 业务日志有对象/流键隔离、签名变化立即输出、抑制计数及固定业务前缀。库内部日志和按函数墙钟节流都不能等价提供这些行为 |
| 维度冷却、每 tick 预算、任务去重 | `delay`、`repeat`、`call_interval` | 业务按维度/任务及脚本 tick 计数；库定时器和函数墙钟节流会改变时钟、分组和触发语义 |
| 本地广播和指定观看者跨端同步 | `broadcast_to_all_systems`、`SyncData`、`call` | 现有 BroadcastEvent 保持本地主服务端事件源；跨端只通知指定观看者。替换为全系统广播或状态同步会改变接收范围、来源或去重行为 |
| AOI 实体补齐、在线玩家列表 | `get_all_entities` 等 | `get_all_entities` 是服务端接口，客户端不能跨端使用；在线玩家原生查询没有更直接的库封装 |
| 后处理参数、天空状态恢复、粒子清理 | 客户端 effect 工具 | 库没有对应的后处理通道与天空覆盖状态恢复封装，继续通过 LvComp 调用组件 |
| 开发工具和测试入口 | 数学、定时器等工具 | 构建工具运行于离线 Python 3，不能引入依赖游戏环境的库入口；运行时诊断保留对底层组件和原始状态的直接观察，避免测试与业务共用同一封装而失去对照 |
| JSON、GLSL、模型和其他资源 | 无 | 属于引擎资源或离线生成数据，不由运行时 Python 库替代 |

## 离线验证

- `C:/Python27/python.exe -B tools/compile_runtime.py`：Python 2.7.18，118 个运行时文件全部编译通过，不生成 pyc。
- 14 个测试脚本各自独立进程运行：共 125 项，117 项通过，8 项失败；几何测试使用 Python 3，其余使用 Python 2.7。
- 本次新增 3 项边界用例全部通过：负坐标脚底/支撑点、负区块边界、近零天空方向回退。
- 失败项在修改前源码副本中复现，修改前后失败集合一致：业务日志 2 项；发射事件 5 项（其中 4 项缺少 LaunchWorld.is_loaded，1 项为既有非法飞行配置校验断言）；调色板 1 项（用例禁止捕获后立即发生的区块检查）。本次未扩展修改这些问题。
- 新增库调用对应的组件替身由 `tests/nuoyanlib_exports.py` 从项目附带库源码中提取函数编译；库文件未修改。朝向配置用例同步改为替换当前调用的 `rot2dir` 入口。
- AST 导入清单、基线对照副本、逐脚本结果和日志保存在 `.tmp/nuoyanlib_review/`，不纳入 Git。

以上仅证明离线编译、算法边界及组件替身下的回归结果，不代表游戏运行或视觉效果已经验证。
