# AGENTS.md

- 全程中文，终端使用 `pwsh`。运行时代码兼容 Python 2.7。
- `src/bp/dualvectorfoil_scripts` 为脚本包，`src/rp` 为资源包；二向箔业务放在 `modules/foil`，着色器 Python 与配置放在 `modules/effect`，公共纯算法不导入 ModSDK。
- 功能模块间通过事件通信，不互相导入实现；同端使用 `BroadcastEvent` 本地广播，只有必要的服务端到客户端数据使用跨端通知。
- 基于本地一般项目模板与 nuoyanlib；不修改内置库。服务端改变世界，客户端仅改变实体表现。
- 本次用户授权以本地源码、官方文档及静态依赖检查替代缺失的专用 MCP 扫描/检索工具，必须如实记录，不声称做过 MCP 扫描。
- 用户要求先不实机测试。离线验证不能视为游戏运行证明。
- 项目启用 Git 后，验证完成的改动拆为原子提交；当前目录创建时没有 Git，不自动初始化。
- 所有 Minecraft 资源标识、几何/渲染控制器和脚本系统命名空间统一使用 `nuoyan`。
- 模组自有行为包/资源包文件必须放在 `entities/dual_vector_foil/` 等同级项目子目录；`manifest.json`、语言表等引擎固定路径除外。
- 二向箔只处理命中首方块所在的六面连通非空气物体；单次方块上限和实体上限配置位于 `common/config.py`。
