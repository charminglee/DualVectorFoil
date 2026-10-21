# -*- coding: utf-8 -*-
# =================================================
#  ⠀
#   Author: Nuoyan <https://github.com/charminglee>
#   Email : 1279735247@qq.com
#   Date  : 2026-10-21
#  ⠀
# =================================================


import ast
import json
import uuid
from pathlib import Path

from build_space_fall import EFFECT, definition

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "src/bp/dualvectorfoil_scripts"
NAMESPACE = "nuoyan"
PROJECT_DIR = "dual_vector_foil"
ITEM_ID = NAMESPACE + ":foil"
PROJECTILE_ID = NAMESPACE + ":foil_projectile"
PROJECT_SCOPED_DIRS = (
    "src/bp/entities",
    "src/bp/netease_items_beh",
    "src/bp/recipes",
    "src/rp/entity",
    "src/rp/models/entity",
    "src/rp/netease_items_res",
    "src/rp/render_controllers",
    "src/rp/textures/items",
    "src/rp/shaders",
)
EXPECTED_PROJECT_ASSETS = (
    "src/bp/entities/dual_vector_foil/foil_projectile.json",
    "src/bp/netease_items_beh/dual_vector_foil/foil.json",
    "src/bp/recipes/dual_vector_foil/foil.json",
    "src/rp/entity/dual_vector_foil/foil_projectile.entity.json",
    "src/rp/models/entity/dual_vector_foil/foil.geo.json",
    "src/rp/models/entity/dual_vector_foil/flat_entities.geo.json",
    "src/rp/netease_items_res/dual_vector_foil/foil.json",
    "src/rp/render_controllers/dual_vector_foil/foil.render_controllers.json",
    "src/rp/textures/items/dual_vector_foil/foil.png",
    "src/rp/shaders/dual_vector_foil/glsl/space_fall.vertex",
    "src/rp/shaders/dual_vector_foil/glsl/space_fall.fragment",
)
LEGACY_ASSETS = (
    "src/bp/entities/foil_projectile.json",
    "src/bp/netease_items_beh/foil.json",
    "src/bp/recipes/foil.json",
    "src/rp/entity/foil_projectile.entity.json",
    "src/rp/models/entity/foil.geo.json",
    "src/rp/models/entity/flat_entities.geo.json",
    "src/rp/netease_items_res/foil.json",
    "src/rp/render_controllers/foil.render_controllers.json",
    "src/rp/textures/items/dualvector_foil.png",
)


# region Offline Validation ==================================================


def load_json(relative):
    """
    读取项目内指定相对路径的 JSON 文件。
    """
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def validate_space_fall_resources():
    """
    仅检查 JSON 与文件引用；按用户要求不编译、运行或测试 shader。
    """
    # 校验两个后处理入口都只追加一次本模组通道。
    sources = load_json("docs/dev/space_fall_sources.json")
    checked = []
    for filename, provenance in sources.items():
        configured = load_json("src/rp/graphics_settings/" + filename)
        assert configured['render_order'].count(EFFECT) == 1
        effects = [item for item in configured['process_array'] if item['name'] == EFFECT]
        assert effects == [definition()]
        assert len(effects[0]['pass_array']) == 1
        assert not effects[0]['enable']
        assert [item['name'] for item in effects[0]['paras']] == [
            "field",
            "shape",
            "style",
        ]
        assert all(len(item['value']) == 4 for item in effects[0]['paras'])
        source = Path(provenance['source'])
        if source.is_file():
            vanilla = json.loads(source.read_text(encoding="utf-8"))
            assert configured['render_order'][:-1] == vanilla['render_order']
            assert configured['process_array'][:-1] == vanilla['process_array']
            checked.append(filename)
    # 材质只能声明本模组效果，并引用项目内 shader。
    material = load_json("src/rp/materials/postprocess.material")
    assert set(material) == {EFFECT}
    for key in ("vertexShader", "fragmentShader"):
        path = Path(material[EFFECT][key])
        assert path.parts[:2] == ("shaders", PROJECT_DIR)
        assert (ROOT / "src/rp" / path.parent / "glsl" / path.name).is_file()
    return {
        'effect': EFFECT,
        'passes': 1,
        'default_enabled': False,
        'parameters': ["field", "shape", "style"],
        'floats': 12,
        'vanilla_pipelines_preserved': sorted(checked),
        'shader_tests': "not_run_per_user_request",
        'game_test': "not_run_per_user_request",
    }


def main():
    """
    执行资源、命名空间、目录、依赖、端侧边界和 UUID 的离线验证。
    """
    # 所有资源 JSON 必须能被标准解析器读取。
    files = sorted((ROOT / "src").rglob("*.json"))
    for path in files:
        json.loads(path.read_text(encoding="utf-8"))

    # 检查两个清单的四个 UUID 唯一且版本依赖一致。
    manifests = [load_json("src/%s/manifest.json" % pack) for pack in ("bp", "rp")]
    ids = [manifest['header']['uuid'] for manifest in manifests]
    ids += [
        module['uuid']
        for manifest in manifests
        for module in manifest['modules']
    ]
    assert len(set(ids)) == 4
    for value in ids:
        uuid.UUID(value)
    assert manifests[0]['dependencies'][0]['uuid'] == manifests[1]['header']['uuid']
    assert manifests[0]['dependencies'][0]['version'] == manifests[1]['header']['version']

    # 必需资源必须存在，旧的未分目录资源不得残留。
    for relative in EXPECTED_PROJECT_ASSETS:
        assert (ROOT / relative).is_file(), relative
    for relative in LEGACY_ASSETS:
        assert not (ROOT / relative).exists(), relative
    for base in PROJECT_SCOPED_DIRS:
        folder = ROOT / base
        for path in folder.rglob("*"):
            if (
                path.is_file()
                and path.suffix
                in (".json", ".png", ".tga", ".jpg", ".jpeg", ".vertex", ".fragment")
            ):
                assert path.relative_to(folder).parts[0] == PROJECT_DIR, path

    # 检查物品、配方、投射物、渲染控制器和贴图图集的接线。
    bp_item = load_json("src/bp/netease_items_beh/dual_vector_foil/foil.json")
    rp_item = load_json("src/rp/netease_items_res/dual_vector_foil/foil.json")
    recipe = load_json("src/bp/recipes/dual_vector_foil/foil.json")
    bp_entity = load_json("src/bp/entities/dual_vector_foil/foil_projectile.json")
    rp_entity = load_json("src/rp/entity/dual_vector_foil/foil_projectile.entity.json")
    controller = load_json(
        "src/rp/render_controllers/dual_vector_foil/foil.render_controllers.json",
    )
    texture_atlas = load_json("src/rp/textures/item_texture.json")
    assert bp_item['minecraft:item']['description']['identifier'] == ITEM_ID
    assert rp_item['minecraft:item']['description']['identifier'] == ITEM_ID
    assert recipe['minecraft:recipe_shaped']['description']['identifier'] == ITEM_ID
    assert recipe['minecraft:recipe_shaped']['result']['item'] == ITEM_ID
    assert bp_entity['minecraft:entity']['description']['identifier'] == PROJECTILE_ID
    assert rp_entity['minecraft:client_entity']['description']['identifier'] == PROJECTILE_ID
    rp_description = rp_entity['minecraft:client_entity']['description']
    assert rp_description['geometry']['default'] == "geometry.nuoyan.projectile"
    bp_components = bp_entity['minecraft:entity']['components']
    assert bp_components['minecraft:projectile']['gravity'] == 0.0
    assert bp_components['netease:custom_entity_type']['value'] == "projectile_entity"
    projectile_controller = controller['render_controllers'][
        'controller.render.nuoyan.projectile'
    ]
    assert projectile_controller['geometry'] == "Geometry.default"
    assert texture_atlas['resource_pack_name'] == NAMESPACE
    assert (
        texture_atlas['texture_data']['nuoyan_foil']['textures']
        == "textures/items/dual_vector_foil/foil"
    )
    for relative in ("src/rp/texts/zh_CN.lang", "src/rp/texts/en_US.lang"):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "item.%s.name=" % ITEM_ID in text
        assert "entity.%s.name=" % PROJECTILE_ID in text

    # NySystemMeta 自动装饰同名引擎事件；别名装饰器同样归入监听清单。
    listener_source = (SCRIPTS / "nuoyanlib/core/listener.py").read_text(
        encoding="utf-8",
    )
    listener_tree = ast.parse(listener_source)
    engine_events = set()
    for node in listener_tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name)
            and target.id in ("ALL_CLIENT_ENGINE_EVENTS", "ALL_SERVER_ENGINE_EVENTS")
            for target in node.targets
        ):
            engine_events.update(ast.literal_eval(node.value))

    # 确认 nuoyanlib 会在系统销毁时注销全部事件。
    for side in ("client", "server"):
        lifecycle_path = SCRIPTS / (
            "nuoyanlib/core/%s/_lib_%s.py" % (side, side)
        )
        lifecycle = lifecycle_path.read_text(encoding="utf-8")
        assert "def Destroy(self):" in lifecycle
        assert "_env.%s_SYSTEMS.values()" % side.upper() in lifecycle
        assert "unlisten_all_events(system)" in lifecycle

    # 遍历业务模块，建立相对导入图和事件回调清单。
    graph, event_lists = {}, {}
    for path in sorted(SCRIPTS.rglob("*.py")):
        relative = path.relative_to(SCRIPTS)
        # 内置库和模板不参与项目业务依赖统计。
        if "nuoyanlib" in relative.parts or "__template" in relative.parts:
            continue
        text = path.read_text(encoding="utf-8")
        assert "$MOD_NAME$" not in text and "$DATE$" not in text
        tree = ast.parse(text)
        name = ".".join(relative.with_suffix("").parts)
        parent = name.split(".")[:-1]
        dependencies = []
        event_aliases = set()
        # 收集 event() 装饰器别名。
        for node in tree.body:
            if (
                isinstance(node, ast.Assign)
                and isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Attribute)
                and node.value.func.attr == "event"
            ):
                event_aliases.update(
                    target.id
                    for target in node.targets
                    if isinstance(target, ast.Name)
                )

        # 校验相对导入目标存在，并识别引擎事件或装饰器事件。
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.level:
                prefix = parent[:len(parent) - node.level + 1]
                parts = prefix + (node.module.split(".") if node.module else [])
                destination = SCRIPTS.joinpath(*parts)
                target_exists = (
                    destination.is_dir()
                    or destination.with_suffix(".py").is_file()
                )
                assert target_exists, (name, parts)
                if not node.module:
                    for alias in node.names:
                        target = destination / alias.name
                        target_exists = (
                            target.is_dir()
                            or target.with_suffix(".py").is_file()
                        )
                        assert target_exists, (name, alias.name)
                dependencies.append(".".join(parts))
            if isinstance(node, ast.FunctionDef):
                registered = node.name in engine_events
                for decorator in node.decorator_list:
                    target = decorator.func if isinstance(decorator, ast.Call) else decorator
                    if (
                        (isinstance(target, ast.Attribute) and target.attr == "event")
                        or (
                            isinstance(target, ast.Name)
                            and target.id in event_aliases
                        )
                    ):
                        registered = True
                if registered:
                    event_lists.setdefault(name, []).append(node.name)
        graph[name] = dependencies
        events = event_lists.get(name, [])
        assert len(events) == len(set(events)), name
    # 端侧专属模块用于阻断跨端业务导入。
    server_only = {
        "modules.effect.server",
        "modules.foil.server",
        "main_server",
        "modules._base.server",
    }
    client_only = {
        "modules.effect.client",
        "modules.foil.client",
        "main_client",
        "modules._base.client",
    }

    def walk(node, trail):
        """
        递归收集项目作用域文件引用。
        """
        assert node not in trail, ("circular dependency", trail, node)
        reachable = {node}
        for other in graph.get(node, []):
            reachable.update(walk(other, trail + [node]))
        return reachable

    # 遍历每个业务模块的完整可达依赖，检查端侧隔离和模块边界。
    for name in graph:
        reachable = walk(name, [])
        if name in server_only:
            assert not reachable.intersection(client_only), name
        if name in client_only:
            assert not reachable.intersection(server_only), name
        if name.startswith("modules.foil."):
            assert not any(item.startswith("modules.effect.") for item in reachable), name
        if name.startswith("modules.effect."):
            assert not any(item.startswith("modules.foil.") for item in reachable), name
        if name in ("modules.effect.config", "modules.foil.config"):
            assert not reachable.intersection(server_only | client_only), name
            config_path = SCRIPTS.joinpath(*name.split(".")).with_suffix(".py")
            source = config_path.read_text(encoding="utf-8")
            assert "nuoyanlib" not in source and "import mod." not in source, name

    # 每个功能模块只允许 client、server、config 和包初始化文件。
    for package in ("effect", "foil"):
        folder = SCRIPTS / "modules" / package
        source_files = {path.name for path in folder.glob("*.py")}
        assert source_files == {
            "__init__.py",
            "client.py",
            "server.py",
            "config.py",
        }, source_files

    # 校验命名空间、系统路径和模块注册顺序。
    constants = (SCRIPTS / "common/constant.py").read_text(encoding="utf-8")
    project_meta = (SCRIPTS / "common/project.py").read_text(encoding="utf-8")
    assert "MOD_NAMESPACE = \"nuoyan\"" in project_meta
    assert "MOD_NAME = \"DualVectorFoil\"" in project_meta
    assert "PROJECT_DIR = \"dual_vector_foil\"" in project_meta
    assert "from .project import MOD_NAME, MOD_NAMESPACE, PROJECT_DIR" in constants
    assert "\"FoilClient\", MODULES_PATH + \".foil.client\"" in constants
    assert "\"FoilServer\", MODULES_PATH + \".foil.server\"" in constants
    assert "\"EffectClient\", MODULES_PATH + \".effect.client\"" in constants
    assert "\"EffectServer\", MODULES_PATH + \".effect.server\"" in constants
    assert constants.index("\"EffectServer\"") < constants.index("\"FoilServer\"")
    assert not list((SCRIPTS / "modules/foil").glob("space_fall*.py"))
    mod_main = (SCRIPTS / "modMain.py").read_text(encoding="utf-8")
    assert "MOD_NAMESPACE" in mod_main
    assert "nuoyanlib.run(\n    MOD_NAMESPACE," in mod_main

    # 公共配置和生成目录必须位于约定文件。
    common_config = (SCRIPTS / "common/config.py").read_text(encoding="utf-8")
    assert "MAX_FOIL_BLOCKS = 500000" in common_config
    assert "MAX_FOIL_ENTITIES = None" in common_config
    assert "FOIL_BLOCKS_PER_TICK = 50" in common_config
    assert "FOIL_FX_" not in common_config
    config = (SCRIPTS / "modules/foil/config.py").read_text(encoding="utf-8")
    assert (
        "from ...common.config import FOIL_BLOCKS_PER_TICK, "
        "MAX_FOIL_BLOCKS, MAX_FOIL_ENTITIES"
    ) in config
    assert "from ...common.project import MOD_NAMESPACE" in config
    assert "NAMESPACE = MOD_NAMESPACE" in config
    assert "# >>> GENERATED ENTITY CATALOG" in config
    assert "# <<< END GENERATED ENTITY CATALOG" in config

    # 读取生成的实体目录，供后续资源覆盖检查使用。
    catalog_tree = ast.parse(config)
    catalog = {}
    for node in catalog_tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id in ("GEOMETRIES", "ENTITY_GEOMETRIES"):
                catalog[target.id] = ast.literal_eval(node.value)
    assert set(catalog) == {"GEOMETRIES", "ENTITY_GEOMETRIES"}

    # 二向箔实现必须仍由单一服务端文件承载。
    server = (SCRIPTS / "modules/foil/server.py").read_text(encoding="utf-8")
    required_server_tokens = (
        "def flatten(",
        "DIRECTIONS = (",
        "def advance_scan(",
        "class WorldAdapter(",
        "class PlanePages(",
        "def run_batch(",
        "def build_field_event(",
        "class FlatEntities(",
        "class FoilServer(",
        "MAX_FOIL_ENTITIES is not None",
        "entity_contact_candidates",
    )
    for token in required_server_tokens:
        assert token in server, token

    # 禁止重新引入曾计划过的拆分模块。
    forbidden_server_tokens = (
        "from .mapping import",
        "from .object_scan import",
        "from .transfer import",
        "from .storage import",
        "from .world import",
        "from .entities import",
        "from .events import",
    )
    for token in forbidden_server_tokens:
        assert token not in server, token
    assert "HEIGHTS[dimension][1]," in server
    assert "end = min(start + FOIL_BLOCKS_PER_TICK, len(state['object']))" in server
    assert "run_batch(state, sources, world, pages)" in server
    assert "MAX_FOIL_BLOCKS" in server and "WORLD_LIMIT" in server
    assert "source_position" not in server
    assert "state[\"radius\"]" not in server
    assert "self.main_system.BroadcastEvent(ServerEvent.FoilFieldState," in server
    assert "NotifyTo" not in server and "BroadcastToAllClient" not in server

    # 检查 effect 模块仍然拆分视觉状态、渲染桥和系统入口。
    effect_client = (SCRIPTS / "modules/effect/client.py").read_text(encoding="utf-8")
    assert "class SpaceFallState(" in effect_client
    assert "class SpaceFallRenderer(" in effect_client
    assert "class EffectClient(" in effect_client
    assert "space_fall_client" not in effect_client
    assert "space_fall_state" not in effect_client
    effect_server = (SCRIPTS / "modules/effect/server.py").read_text(encoding="utf-8")
    assert "def make_snapshot(" in effect_server
    assert "class SpaceFallSync(" in effect_server
    assert "client_event = nyl.event(sys_name=CLIENT_SYSTEM_NAME)" in effect_server
    assert "server_event = nyl.event(sys_name=SERVER_SYSTEM_NAME)" in effect_server
    assert "self.system.main_system.NotifyToMultiClients(" in effect_server
    assert "self.system.NotifyToMultiClients(" not in effect_server
    assert "def FoilFieldState(self, args):" in effect_server
    assert "self.space_fall.send(args)" in effect_server
    assert "space_fall_sync" not in effect_server
    assert "space_fall_state" not in effect_server

    # 生成器必须继续声明统一命名空间和关键资源字段。
    for relative in ("tools/build_assets.py", "tools/build_geometry.py"):
        generator = (ROOT / relative).read_text(encoding="utf-8")
        assert "NAMESPACE = \"nuoyan\"" in generator, relative
        assert "PROJECT_DIR = \"dual_vector_foil\"" in generator, relative
    geometry_generator = (ROOT / "tools/build_geometry.py").read_text(encoding="utf-8")
    assert "modules/foil/config.py" in geometry_generator
    assert "# >>> GENERATED ENTITY CATALOG" in geometry_generator
    assets_generator = (ROOT / "tools/build_assets.py").read_text(encoding="utf-8")
    assert "'gravity': 0.0" in assets_generator
    assert "'netease:custom_entity_type':" in assets_generator
    assert "'value': \"projectile_entity\"" in assets_generator

    # 验证生成的几何目录覆盖所有实体引用的几何。
    geometry_file = ROOT / "src/rp/models/entity/dual_vector_foil/flat_entities.geo.json"
    models = json.loads(geometry_file.read_text(encoding="utf-8"))['minecraft:geometry']
    names = {item['description']['identifier'] for item in models}
    assert len(names) == len(models)
    assert all(name.startswith("geometry.%s." % NAMESPACE) for name in names)
    assert set(catalog['GEOMETRIES'].values()) <= names
    for kind, geometry in catalog['ENTITY_GEOMETRIES'].items():
        assert set(geometry.values()) <= set(catalog['GEOMETRIES']), kind
    projectile_model = load_json("src/rp/models/entity/dual_vector_foil/foil.geo.json")
    projectile_description = projectile_model['minecraft:geometry'][0]['description']
    assert projectile_description['identifier'] == "geometry.nuoyan.projectile"

    # 全项目扫描旧命名空间残留。
    scan_roots = (
        SCRIPTS,
        ROOT / "src/bp/entities",
        ROOT / "src/bp/netease_items_beh",
        ROOT / "src/bp/recipes",
        ROOT / "src/rp/entity",
        ROOT / "src/rp/models/entity",
        ROOT / "src/rp/netease_items_res",
        ROOT / "src/rp/render_controllers",
        ROOT / "src/rp/texts",
        ROOT / "src/rp/textures",
    )
    for root in scan_roots:
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix not in (".py", ".json", ".lang"):
                continue
            text = path.read_text(encoding="utf-8")
            assert ":dualvector" not in text.lower(), path
            assert "geometry.dualvector." not in text.lower(), path
            assert "controller.render.dualvector." not in text.lower(), path

    # 汇总静态检查结果并写入可复查报告。
    space_fall = validate_space_fall_resources()
    result = {
        'kind': "offline_static_check_not_mcp_or_game",
        'namespace': NAMESPACE,
        'project_dir': PROJECT_DIR,
        'namespace_uniform': True,
        'asset_layout': True,
        'max_foil_blocks': 500000,
        'max_foil_entities': None,
        'foil_blocks_per_tick': 50,
        'json_files': len(files),
        'runtime_business_modules': len(graph),
        'geometry_count': len(models),
        'entity_count': len(catalog['ENTITY_GEOMETRIES']),
        'event_listeners': event_lists,
        'imports': graph,
        'uuid_unique': True,
        'no_cross_side_business_imports': True,
        'no_foil_effect_implementation_imports': True,
        'local_event_source': "nuoyan:MainServerSystem:FoilFieldState",
        'effect_network_source': "nuoyan:MainServerSystem:FoilSpaceFallState",
        'event_unregistration': "nuoyanlib_registered_systems_destroy",
        'space_fall': space_fall,
    }
    output = ROOT / "docs/dev/static_report.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary_keys = (
        "namespace",
        "project_dir",
        "namespace_uniform",
        "asset_layout",
        "max_foil_blocks",
        "max_foil_entities",
        "foil_blocks_per_tick",
        "json_files",
        "runtime_business_modules",
        "geometry_count",
        "entity_count",
        "uuid_unique",
    )
    summary = {key: result[key] for key in summary_keys}
    print(json.dumps(summary, ensure_ascii=False))


# endregion


if __name__ == "__main__":
    main()
