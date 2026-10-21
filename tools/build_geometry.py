# -*- coding: utf-8 -*-
# =================================================
#  ⠀
#   Author: Nuoyan <https://github.com/charminglee>
#   Email : 1279735247@qq.com
#   Date  : 2026-10-21
#  ⠀
# =================================================


import argparse
import copy
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAMESPACE = "nuoyan"
PROJECT_DIR = "dual_vector_foil"
DEFAULT_VANILLA = Path(
    r"S:\MCStudioDownload\game\MinecraftPE_Netease\3.10.0.420447"
    r"\data\resource_packs\vanilla"
)
JSONC = re.compile(r'"(?:\\.|[^"\\])*"|//[^\r\n]*|/\*[\s\S]*?\*/|,(?=\s*[}\]])')


# region Geometry Generation ==================================================


def read_json(path):
    """
    读取允许行注释和尾逗号的 JSONC 文件。
    """
    # 去掉 JSONC 注释和尾逗号，再交给标准 JSON 解析器。
    text = path.read_text(encoding="utf-8-sig")
    text = JSONC.sub(lambda match: match[0] if match[0].startswith("\"") else "", text)
    return json.loads(text)


def write_json(path, value):
    """
    以紧凑 UTF-8 JSON 格式写入生成文件。
    """
    # 生成目录使用紧凑格式，减少资源包体积。
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n"
    path.write_text(text, encoding="utf-8")


def quote_key(value):
    """
    把目录键格式化为项目约定的单引号字符串。
    """
    escaped = value.replace("\\", "\\\\").replace("'", "\\'")
    return "'" + escaped + "'"


def format_mapping(value, level=0):
    """
    按项目风格递归格式化字符串键值目录。
    """
    indent = "    " * level
    child_indent = indent + "    "
    lines = ["{"]
    for key, item in sorted(value.items()):
        prefix = child_indent + quote_key(key) + ": "
        if isinstance(item, dict):
            # 嵌套目录与父键同行开始，子项统一缩进四格。
            nested = format_mapping(item, level + 1)
            lines.append(prefix + nested[0])
            lines.extend(nested[1:-1])
            lines.append(nested[-1] + ",")
        else:
            lines.append(prefix + json.dumps(item, ensure_ascii=False) + ",")
    lines.append(indent + "}")
    return lines


def box_uv(cube, bone):
    """
    解析长方体的 UV 布局并把镜像应用到对应面。
    """
    # 显式 UV 字典直接复制，简写 UV 则展开为六面布局。
    w, h, d = cube['size']
    value = cube.get('uv', [0, 0])
    if isinstance(value, dict):
        return copy.deepcopy(value)
    u, v = value
    result = {
        'west': {'uv': [u, v + d], 'uv_size': [d, h]},
        'north': {'uv': [u + d, v + d], 'uv_size': [w, h]},
        'east': {'uv': [u + d + w, v + d], 'uv_size': [d, h]},
        'south': {'uv': [u + 2 * d + w, v + d], 'uv_size': [w, h]},
        'up': {'uv': [u + d, v], 'uv_size': [w, d]},
        'down': {'uv': [u + d + w, v + d], 'uv_size': [w, -d]},
    }
    if cube.get('mirror', bone.get('mirror', False)):
        # 镜像会交换东西面并翻转每面的水平 UV 方向。
        result['west'], result['east'] = result['east'], result['west']
        for face in result.values():
            face['uv'][0] += face['uv_size'][0]
            face['uv_size'][0] *= -1
    return result


def net_faces(cube, bone):
    """
    把长方体六个可见面展开为共面的表面网格。
    """
    # 先解析 UV，并补齐缺省的面尺寸。
    uv = box_uv(cube, bone)
    base = cube['size']
    if any(not isinstance(n, (float, int)) or n < 0 for n in base):
        raise ValueError("non-numeric or negative cube size")
    bw, bh, bd = base
    sizes = {
        'west': [bd, bh],
        'east': [bd, bh],
        'north': [bw, bh],
        'south': [bw, bh],
        'up': [bw, bd],
        'down': [bw, bd],
    }
    for name, face in uv.items():
        if name in sizes:
            face.setdefault('uv_size', sizes[name])
    inflate = cube.get('inflate', bone.get('inflate', 0))
    w, h, d = [max(0, n + 2 * inflate) if n else 0 for n in base]
    faces = [
        ("west", 0, d, d, h),
        ("north", d, d, w, h),
        ("east", d + w, d, d, h),
        ("south", 2 * d + w, d, w, h),
        ("up", d, 0, w, d),
        ("down", d, d + h, w, d),
    ]
    net_width, net_height = 2 * (w + d), h + 2 * d
    if 0 in (w, h, d):
        # 原生箭、火球等本来就是双面片；保留实际声明的每一个面。
        visible = [
            (name, width, height)
            for name, _, _, width, height in faces
            if name in uv and width > 0 and height > 0
        ]
        offset = 0
        faces = []
        for name, fw, fh in visible:
            faces.append((name, offset, 0, fw, fh))
            offset += fw
        net_width = offset
        net_height = max([fh for _, _, fh in visible] or [0])
    result = []
    for name, x, z, fw, fh in faces:
        if fw <= 0 or fh <= 0 or name not in uv:
            continue
        texture = uv[name]
        if 'uv' not in texture:
            raise ValueError("face without uv")
        texture.setdefault('uv_size', [fw, fh])
        # 上下面共面，几何厚度严格为 0；下表面使用反向 V，保证背面可读。
        front = {
            key: value
            for key, value in texture.items()
            if key in ("uv", "uv_size", "material_instance")
        }
        back = copy.deepcopy(front)
        back['uv'][1] += back['uv_size'][1]
        back['uv_size'][1] *= -1
        result.append({
            'origin': [x, 0, z],
            'size': [fw, 0, fh],
            'uv': {'up': front, 'down': back},
        })
    return result, net_width, net_height


def unfold(identifier, geometry):
    """
    把完整几何模型展开并排版到单一平面。
    """
    # 收集每个可渲染骨骼的独立表面展开图。
    nets = []
    for bone in geometry.get('bones', []):
        if bone.get('neverRender'):
            continue
        if bone.get('poly_mesh') or bone.get('texture_meshes'):
            raise ValueError("mesh geometry requires a separate parameterizer")
        for cube in bone.get('cubes', []):
            faces, width, height = net_faces(cube, bone)
            if faces:
                nets.append((faces, width, height))
    if not nets:
        raise ValueError("geometry has no supported faces")
    # Shelf 排版只移动完整的长方体展开图，各 cuboid 不相互遮盖。
    area = sum((w + 1) * (h + 1) for _, w, h in nets)
    row_width = max(max(w for _, w, _ in nets), math.sqrt(area))
    x = z = row_height = max_x = 0
    cubes = []
    for faces, width, height in nets:
        if x > 0 and x + width > row_width:
            x, z, row_height = 0, z + row_height + 1, 0
        for face in faces:
            face['origin'][0] += x
            face['origin'][2] += z
            cubes.append(face)
        max_x = max(max_x, x + width)
        x += width + 1
        row_height = max(row_height, height)
    max_z = z + row_height
    for cube in cubes:
        cube['origin'][0] = round(cube['origin'][0] - max_x / 2, 5)
        cube['origin'][2] = round(cube['origin'][2] - max_z / 2, 5)
    # 描述信息保留源贴图尺寸，并将中心平移到几何原点附近。
    source_description = geometry.get('description', {})
    name = "geometry.%s.flat." % NAMESPACE + identifier.removeprefix("geometry.")
    return {
        'description': {
            'identifier': name,
            'texture_width': source_description.get(
                'texture_width',
                geometry.get('texturewidth', 64),
            ),
            'texture_height': source_description.get(
                'texture_height',
                geometry.get('textureheight', 32),
            ),
            'visible_bounds_width': max(max_x, max_z) / 16 + 2,
            'visible_bounds_height': 2,
            'visible_bounds_offset': [0, 0, 0],
        },
        # 保留空骨骼名称供原版动画查找；展开面是独立根，不随原骨骼抬离平面。
        'bones': (
            [
                {'name': bone['name'], 'pivot': [0, 0, 0]}
                for bone in geometry.get('bones', [])
            ]
            + [
                {
                    'name': "%s_flat_surface" % NAMESPACE,
                    'pivot': [0, 0, 0],
                    'cubes': cubes,
                },
            ]
        ),
    }


def resolve_inheritance(raw):
    """
    解析旧版几何继承并返回合并结果与错误。
    """
    # 把标识符拆分为父级链和当前定义。
    definitions = {
        key.split(":")[0]: (key.split(":")[1:], value)
        for key, value in raw.items()
    }
    resolved = {}

    def resolve(name, visiting):
        """
        递归解析指定几何及其父级定义。
        """
        # 已解析定义直接复用。
        if name in resolved:
            return resolved[name]
        if name in visiting or name not in definitions:
            raise ValueError("missing or circular geometry inheritance: " + name)
        # 先递归合并父级，再用当前骨骼和字段覆盖。
        parents, own = definitions[name]
        result = {}
        bones = {}
        for parent in reversed(parents):
            base = copy.deepcopy(resolve(parent, visiting + [name]))
            bones.update({bone['name']: bone for bone in base.pop('bones', [])})
            result.update(base)
        result.update({key: value for key, value in own.items() if key != "bones"})
        for bone in own.get('bones', []):
            combined = bones.get(bone['name'], {}).copy()
            combined.update(copy.deepcopy(bone))
            bones[bone['name']] = combined
        result['bones'] = list(bones.values())
        resolved[name] = result
        return result

    errors = {}
    for name in definitions:
        try:
            resolve(name, [])
        except ValueError as error:
            errors[name] = str(error)
    return resolved, errors


def generate(vanilla):
    """
    扫描原版模型并生成二维实体几何目录。
    """
    # 扫描所有原版几何定义，并记录无法解析的文件。
    geometry_sources = {}
    parse_errors = []
    for path in sorted((vanilla / "models").rglob("*.json")):
        try:
            data = read_json(path)
        except (ValueError, OSError) as error:
            parse_errors.append({
                'file': str(path.relative_to(vanilla)),
                'error': str(error),
            })
            continue
        for item in data.get('minecraft:geometry', []):
            geometry_sources[item['description']['identifier']] = item
        for key, value in data.items():
            if key.startswith("geometry."):
                geometry_sources[key] = value
    # 解析继承后，将每个受支持的几何展开为二维目录项。
    geometry_sources, inheritance_errors = resolve_inheritance(geometry_sources)
    generated, names, unsupported = [], {}, dict(inheritance_errors)
    for identifier, geometry in sorted(geometry_sources.items()):
        try:
            item = unfold(identifier, geometry)
        except (ValueError, KeyError, TypeError) as error:
            unsupported[identifier] = str(error)
            continue
        generated.append(item)
        names[identifier] = item['description']['identifier']
    # 再把客户端实体绑定到已生成的二维几何。
    entities, skipped = {}, {}
    for path in sorted((vanilla / "entity").rglob("*.json")):
        data = read_json(path)
        description = data.get('minecraft:client_entity', {}).get('description', {})
        kind = description.get('identifier')
        geometry = description.get('geometry', {})
        if not kind or not geometry:
            continue
        missing = [name for name in geometry.values() if name not in names]
        if missing:
            skipped[kind] = missing
            continue
        entities[kind] = geometry
    write_json(
        ROOT / "src/rp/models/entity" / PROJECT_DIR / "flat_entities.geo.json",
        {
            'format_version': "1.12.0",
            'minecraft:geometry': generated,
        },
    )

    # 更新脚本配置中由生成器维护的实体目录块。
    catalog = ROOT / "src/bp/dualvectorfoil_scripts/modules/foil/config.py"
    catalog_text = catalog.read_text(encoding="utf-8")
    begin = "# >>> GENERATED ENTITY CATALOG; tools/build_geometry.py replaces this block."
    end = "# <<< END GENERATED ENTITY CATALOG"
    start = catalog_text.index(begin)
    finish = catalog_text.index(end, start) + len(end)
    geometry_lines = format_mapping(names)
    entity_lines = format_mapping(entities)
    catalog_block = (
        begin
        + "\nGEOMETRIES = "
        + geometry_lines[0]
        + "\n"
        + "\n".join(geometry_lines[1:])
        + "\n\nENTITY_GEOMETRIES = "
        + entity_lines[0]
        + "\n"
        + "\n".join(entity_lines[1:])
        + "\n"
        + end
    )
    catalog.write_text(
        catalog_text[:start] + catalog_block + catalog_text[finish:],
        encoding="utf-8",
    )

    # 写入覆盖报告并输出本次生成摘要。
    report = {
        'source': str(vanilla),
        'geometry_count': len(names),
        'entity_count': len(entities),
        'unsupported_geometry': unsupported,
        'unsupported_entities': skipped,
        'parse_errors': parse_errors,
        'supported_entities': sorted(entities),
        'zero_thickness_faces': sum(
            len(geometry['bones'][-1]['cubes'])
            for geometry in generated
        ),
    }
    write_json(ROOT / "docs/dev/geometry_report.json", report)
    summary = {
        key: report[key]
        for key in ("geometry_count", "entity_count", "zero_thickness_faces")
    }
    print(json.dumps(summary, ensure_ascii=False))
    print("unsupported geometries:", len(unsupported), "parse errors:", len(parse_errors))


# endregion


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--vanilla", type=Path, default=DEFAULT_VANILLA)
    args = parser.parse_args()
    generate(args.vanilla)
