# 二向箔 / DualVectorFoil

网易《我的世界》基岩版模组，Python 2.7 + nuoyanlib，目标为本机网易 3.10.0.420447。当前版本 **0.1.0，完成离线验证，尚未进行实机测试**。

## 使用

将 `src/bp`、`src/rp` 作为配套行为包和资源包导入工作台。交付压缩包 `dist/DualVectorFoil-0.1.0.zip` 解压后就是这两个目录，未验证直接导入 ZIP 的工作台行为。

- 创造栏装备分类获取“二向箔”，或使用 `/give @s nuoyan:foil`。
- 合成配方：四角纸、四边玻璃、中心下界之星。
- 右键使用或对方块使用后发射；生存模式消耗一枚，创造模式不消耗。
- 发射后沿准星方向无重力直线飞行；接触目标或飞行两秒后开始展开，以命中位置确定统一的 Y 平面。
- 命中后从第一个接触方块出发，只处理通过六个面直接或间接相连的同一物体；不相连的方块和空气边界不会继续递归。
- 单个二向箔最多处理 500,000 个方块；实体数量不设上限，但只能是接触该物体的实体。每个维度只允许一枚二向箔处于飞行或处理中；上一枚处理完成后，可在同一维度再次投掷，不同维度互不阻塞。
- 聊天输入 `!foil` 查看当前维度的平面高度、物体方块数、已处理数量和等待状态。
- 搬移阶段接入局部空间跌落后处理：青金光环、平面网格、空间切片，以及标准档的折射与轻微色散。**着色器源码已加入，按用户要求未运行 shader 测试或实机测试。**

## 命名与目录

- Minecraft 物品、实体、脚本系统及内部持久化标识统一使用命名空间 `nuoyan`；几何体和渲染控制器分别采用 `geometry.nuoyan.*`、`controller.render.nuoyan.*`。
- 模组自有数据文件统一放在项目目录 `dual_vector_foil` 下，例如 `src/bp/entities/dual_vector_foil/`、`src/rp/models/entity/dual_vector_foil/` 和 `src/rp/textures/items/dual_vector_foil/`。
- `manifest.json`、语言表、`textures/item_texture.json` 等必须由引擎从固定路径读取的索引文件仍保留在资源包根目录。

## 已实现的行为

方块采用 **有符号 Morton 3D → 1D → 2D 可逆映射**。仅对命中方块所在六面连通物体中的格点建立输出，每个输入格点有唯一的输出格点，所有输出方块放在同一个 Y 坐标。搬移保留方块名、附加值、状态、可读取的方块实体 NBT 和含水层；源位置在目标写入成功后清除。落点覆盖尚未处理的地形时，先将原内容保存在分页日志中，后续从日志取出，避免把二维输出再次当作三维输入。

实体采用 **长方体表面展开图 + 排版**：将原模型各 cuboid 的表面切开、展开到 XZ 平面，继续使用原实体贴图。生成了 **196 套几何体、9,222 个零厚度面片**，资源目录覆盖 **125 类原版实体定义**，包括普通 Steve/Alex。这是资源覆盖计数，并非逐类实机通过计数。客户端逐实体替换模型；服务端保存二维化标记、关闭生物 AI 并约束位置。

连通物体扫描队列、搬移游标、正在搬移的快照和被覆盖的平面输入可保存并恢复。区块通过两个有界常加载窗口访问，遇到未加载区块或接口失败会等待重试。连通搜索在命中后同步执行，不再设置每 tick 候选格点预算；只有遇到未加载区块时才暂停，待区块就绪后继续。搬移阶段每维度每 tick 最多处理 `FOIL_BLOCKS_PER_TICK = 50` 个非空气方块。投掷门控按维度分别计算：同一维度同时只保留一枚飞行或处理中的二向箔，完成态不再占用槽位。

## 当前边界

- 六面连通按任意非空气方块计算，不要求方块类型相同。普通地表、建筑和地形通常连成一大片，因此可能很快达到 500,000 方块上限；达到上限后只处理扫描顺序中先发现的部分。
- 地形会被实际搬移，这是模组玩法本身；当前没有撤销功能。
- 实体的**模型厚度是 0**，引擎物理碰撞盒仍是原碰撞盒；第一人称视点、装备附件和个性化皮肤尚未做专门适配。
- 原版船、运输船的几何体没有出现在本机可读取 JSON 中，暂不转换。其他模组实体需提供模型并重新生成目录；未知模型不会用通用方片冒充。
- 原版动态行为仍存在：沙砾下落、液体流动、植物支撑、红石、门/床等多方块关系可能在搬移后变化。不能把“保留状态/NBT”理解为保留所有机械功能。末影箱内容由玩家数据管理。
- 实体不占用方块上限，代码也不设置实体数量上限；仍只捕获脚底或紧邻支撑方块属于该连通物体的实体。常加载接口不会加载离线区块的生物，实体在其实际进入加载范围后再检测。世界坐标边界、磁盘容量、区块加载和帧预算仍限制推进速度和实际范围。
- 各实体的多个渲染层、装备附件及不同客户端版本需要后续实机核对；当前不宣称所有原版/第三方模型都已兼容。
- 命名空间和持久化键已统一为 `nuoyan`；状态格式升级为 `v2`，不迁移旧试验世界中的旧命名空间物品、按半径扩散状态或平面日志。
- 空间跌落是颜色/深度后处理，只能限制局部空间，不能精确识别同一连通物体；光场内邻近表面也可能被着色。实际编译、画面、RNGL 和性能尚未验证。

## 空间跌落配置

在 `src/bp/dualvectorfoil_scripts/modules/effect/config.py` 中设置：

| 配置 | 默认 | 作用 |
| --- | --- | --- |
| `FOIL_FX_QUALITY` | `2` | `0` 关闭，`1` 低配光环/网格/切片，`2` 标准折射/色散 |
| `FOIL_FX_RADIUS` | `14.0` | 视觉半径，限制在 4～24 格，不改变方块处理范围 |
| `FOIL_FX_VIEW_DISTANCE` | `64.0` | 观看距离，末段淡出；完全背向时关闭通道 |
| `FOIL_FX_STRENGTH` | `0.8` | 总强度 0～1，0 关闭通道 |

单个客户端最多一个后处理 pass。源码预算为低配最多 2 次、标准档局部最多 5 次纹理读取；不是实测帧率结论。结束、切维度或状态超时后会清理。详见[空间跌落着色器说明](docs/dev/空间跌落着色器.md)。

`foil` 只负责业务，并通过 `MainServerSystem.BroadcastEvent` 在服务端本地发布 `FoilFieldState`。`EffectServer` 监听流程事件并计算低频视觉快照，跨端通知统一由 `MainServerSystem.NotifyToMultiClients` 发出；`EffectClient` 通过 `server_event` 监听 `MainServerSystem` 的事件并独立负责渲染更新。两个功能模块不互相导入实现；除 Python 2 必需的 `__init__.py` 外，`modules/effect` 和 `modules/foil` 各自只保留 `client.py`、`server.py`、`config.py`。按用户选择，`EffectClient` 保持无 `Destroy`，退出时交由引擎清理。

## 开发与离线验证

```powershell
py -3 tools/build_geometry.py
py -3 tools/build_assets.py
py -3 tools/build_space_fall.py
py -2 tools/compile_runtime.py
py -2 tests/test_mapping.py
py -2 tests/test_object_scan.py
py -2 tests/test_space_fall.py
py -2 tests/test_space_fall_bridge.py
py -2 tests/test_effect_events.py
py -3 tests/test_geometry.py
py -3 tools/validate.py
py -3 tools/package.py
```

`build_geometry.py --vanilla <资源包路径>` 可更换资源来源。`setup.py` 是已经运行过的模板初始化脚本，不要在当前工程再次运行。

- [算法研究与选型](docs/dev/算法研究与设计.md)
- [实现、API 依据与验证范围](docs/dev/实现与验证.md)
- [实体资源覆盖报告](docs/dev/geometry_report.json)
- [静态依赖检查报告](docs/dev/static_report.json)
- [空间跌落源码依据与性能预算](docs/dev/空间跌落着色器.md)

`src/bp/dualvectorfoil_scripts/common/config.py` 提供单次方块上限 `MAX_FOIL_BLOCKS = 500000`、实体上限 `MAX_FOIL_ENTITIES = None` 和每 tick 搬移上限 `FOIL_BLOCKS_PER_TICK = 50`；`common/project.py` 集中定义项目名、项目目录和命名空间。`modules/foil/config.py` 同时保存运行参数和生成的实体/模型索引；着色器配置集中在 `modules/effect/config.py`。`foil` 的地图映射、扫描、搬移、存档、世界适配、实体状态和事件载荷均在 `server.py`，客户端模型替换在 `client.py`；`effect` 的视觉状态与后处理在 `client.py`，快照转换、限频和附近玩家通知在 `server.py`。

初始工作目录为空且未启用 Git，本次没有初始化仓库或创建提交。
