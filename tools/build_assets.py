# -*- coding: utf-8 -*-
# =================================================
#  ⠀
#   Author: Nuoyan <https://github.com/charminglee>
#   Email : 1279735247@qq.com
#   Date  : 2026-10-21
#  ⠀
# =================================================


import json
import struct
import zlib

from build_geometry import ROOT, write_json


NAMESPACE = "nuoyan"
PROJECT_DIR = "dual_vector_foil"
ITEM_ID = NAMESPACE + ":foil"
PROJECTILE_ID = NAMESPACE + ":foil_projectile"
ICON_KEY = NAMESPACE + "_foil"
ICON_TEXTURE = "textures/items/%s/foil" % PROJECT_DIR
GEOMETRY_ID = "geometry.%s.projectile" % NAMESPACE
CONTROLLER_ID = "controller.render.%s.projectile" % NAMESPACE


# region Icon Generation ==================================================


def make_icon(path):
    """
    生成固定尺寸的二向箔 PNG 图标。
    """
    size = 32
    scanlines = []
    for y in range(size):
        row = bytearray()
        for x in range(size):
            # 原创像素符号：银白薄片与青色边缘。
            inside = 5 <= x <= 26 and 7 <= y <= 24
            edge = inside and (x in (5, 26) or y in (7, 24))
            cut = (x < 9 and y < 11) or (x > 22 and y > 20)
            color = (0, 0, 0, 0)
            if inside and not cut:
                color = (77, 228, 245, 255) if edge else (222 + (x + y) % 24, 239, 250, 255)
            if inside and not cut and (x + y) % 11 == 0:
                color = (165, 209, 226, 255)
            row.extend(color)
        scanlines.append(b"\x00" + bytes(row))

    def chunk(name, data):
        """
        构造一个 PNG 数据块。
        """
        return (
            struct.pack("!I", len(data))
            + name
            + data
            + struct.pack("!I", zlib.crc32(name + data) & 0xffffffff)
        )

    # 按 PNG 规范组合签名、头块、压缩像素和结束块。
    payload = b"\x89PNG\r\n\x1a\n" + chunk(
        b"IHDR",
        struct.pack("!2I5B", size, size, 8, 6, 0, 0, 0),
    )
    payload += chunk(
        b"IDAT",
        zlib.compress(b"".join(scanlines)),
    ) + chunk(b"IEND", b"")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


# endregion


# region Asset Generation ==================================================


def main():
    """
    生成模组清单、物品、配方、实体、本地化和图标资源。
    """
    # 更新两个包的清单名称、版本和描述。
    bp, rp = ROOT / "src/bp", ROOT / "src/rp"
    for pack, name in ((bp, "二向箔 · 行为"), (rp, "二向箔 · 资源")):
        data = json.loads((pack / "manifest.json").read_text(encoding="utf-8"))
        data['header']['name'] = name
        data['header']['description'] = "三维格点展开与实体零厚度表面展开 · 0.1.0"
        data['header']['version'] = [0, 1, 0]
        data['modules'][0]['version'] = [0, 1, 0]
        data['modules'][0]['description'] = data['header']['description']
        write_json(pack / "manifest.json", data)
    # 行为包依赖资源包，并保持版本一致。
    behavior = json.loads((bp / "manifest.json").read_text(encoding="utf-8"))
    resources = json.loads((rp / "manifest.json").read_text(encoding="utf-8"))
    behavior['dependencies'] = [{'uuid': resources['header']['uuid'], 'version': [0, 1, 0]}]
    write_json(bp / "manifest.json", behavior)
    # 生成行为包物品和资源包图标定义。
    description = {
        'identifier': ITEM_ID,
        'category': "Equipment",
        'register_to_create_menu': True,
    }
    write_json(
        bp / "netease_items_beh" / PROJECT_DIR / "foil.json",
        {
            'format_version': "1.10",
            'minecraft:item': {
                'description': description,
                'components': {
                    'minecraft:max_stack_size': 1,
                    'minecraft:foil': True,
                },
            },
        },
    )
    write_json(
        rp / "netease_items_res" / PROJECT_DIR / "foil.json",
        {
            'format_version': "1.10",
            'minecraft:item': {
                'description': {
                    'identifier': ITEM_ID,
                    'category': "Equipment",
                },
                'components': {'minecraft:icon': ICON_KEY},
            },
        },
    )

    # 注册物品贴图图集。
    write_json(
        rp / "textures/item_texture.json",
        {
            'resource_pack_name': NAMESPACE,
            'texture_name': "atlas.items",
            'texture_data': {ICON_KEY: {'textures': ICON_TEXTURE}},
        },
    )

    # 生成固定材料配方。
    write_json(
        bp / "recipes" / PROJECT_DIR / "foil.json",
        {
            'format_version': "1.12",
            'minecraft:recipe_shaped': {
                'description': {'identifier': ITEM_ID},
                'tags': ["crafting_table"],
                'pattern': ["PGP", "GNG", "PGP"],
                'key': {
                    'P': {'item': "minecraft:paper"},
                    'G': {'item': "minecraft:glass"},
                    'N': {'item': "minecraft:nether_star"},
                },
                'result': {'item': ITEM_ID, 'count': 1},
            },
        },
    )

    # 生成无重力投射物实体定义。
    write_json(
        bp / "entities" / PROJECT_DIR / "foil_projectile.json",
        {
            'format_version': "1.16.0",
            'minecraft:entity': {
                'description': {
                    'identifier': PROJECTILE_ID,
                    'is_spawnable': False,
                    'is_summonable': False,
                    'is_experimental': False,
                },
                'components': {
                    'minecraft:collision_box': {
                        'width': 0.25,
                        'height': 0.25,
                    },
                    'minecraft:projectile': {
                        'on_hit': {'remove_on_hit': {}},
                        'anchor': 1,
                        'power': 1.5,
                        'gravity': 0.0,
                        'angle_offset': 0.0,
                        'offset': [0, 0, 0],
                    },
                    'minecraft:physics': {},
                    'minecraft:pushable': {
                        'is_pushable': False,
                        'is_pushable_by_piston': False,
                    },
                    'netease:custom_entity_type': {
                        'value': "projectile_entity",
                    },
                },
            },
        },
    )

    # 生成客户端实体、渲染控制器和二维投射物模型。
    write_json(
        rp / "entity" / PROJECT_DIR / "foil_projectile.entity.json",
        {
            'format_version': "1.10.0",
            'minecraft:client_entity': {
                'description': {
                    'identifier': PROJECTILE_ID,
                    'materials': {'default': "entity_alphatest"},
                    'textures': {'default': ICON_TEXTURE},
                    'geometry': {'default': GEOMETRY_ID},
                    'render_controllers': [CONTROLLER_ID],
                },
            },
        },
    )
    write_json(
        rp / "render_controllers" / PROJECT_DIR / "foil.render_controllers.json",
        {
            'format_version': "1.8.0",
            'render_controllers': {
                CONTROLLER_ID: {
                    'geometry': "Geometry.default",
                    'materials': [{'*': "Material.default"}],
                    'textures': ["Texture.default"],
                },
            },
        },
    )
    write_json(
        rp / "models/entity" / PROJECT_DIR / "foil.geo.json",
        {
            'format_version': "1.12.0",
            'minecraft:geometry': [
                {
                    'description': {
                        'identifier': GEOMETRY_ID,
                        'texture_width': 32,
                        'texture_height': 32,
                        'visible_bounds_width': 2,
                        'visible_bounds_height': 2,
                    },
                    'bones': [
                        {
                            'name': "foil",
                            'pivot': [0, 0, 0],
                            'cubes': [
                                {
                                    'origin': [-4, -4, 0],
                                    'size': [8, 8, 0],
                                    'uv': {
                                        'north': {
                                            'uv': [0, 0],
                                            'uv_size': [32, 32],
                                        },
                                        'south': {
                                            'uv': [32, 0],
                                            'uv_size': [-32, 32],
                                        },
                                    },
                                },
                            ],
                        },
                    ],
                },
            ],
        },
    )

    # 写入中英文名称并生成图标文件。
    zh_text = "item.%s.name=二向箔\nentity.%s.name=二向箔\n" % (
        ITEM_ID,
        PROJECTILE_ID,
    )
    en_text = (
        "item.%s.name=Dual Vector Foil\n"
        "entity.%s.name=Dual Vector Foil\n"
    ) % (ITEM_ID, PROJECTILE_ID)
    (rp / "texts/zh_CN.lang").write_text(zh_text, encoding="utf-8")
    (rp / "texts/en_US.lang").write_text(en_text, encoding="utf-8")
    write_json(rp / "texts/languages.json", ["zh_CN", "en_US"])
    make_icon(rp / "textures/items" / PROJECT_DIR / "foil.png")
    print("item, recipe, projectile, localization and icon generated")


# endregion


if __name__ == "__main__":
    main()
