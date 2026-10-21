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
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = Path(r"S:\MCStudioDownload\game\MinecraftPE_Netease\3.10.0.420447\data")
EFFECT = "nuoyan_space_fall"


# region Effect Generation ==================================================


def definition():
    """
    返回本模组空间跌落后处理通道的默认定义。
    """
    # 单个 pass 使用四个动态参数，默认保持关闭。
    return {
        'name': EFFECT,
        'enable': False,
        'paras': [
            {
                'name': "field",
                'value': [0.0, 0.0, 0.0, 14.0],
                'range': [-30000000.0, 30000000.0],
            },
            {
                'name': "shape",
                'value': [0.0, 0.0, 0.0, 0.0],
                'range': [-512.0, 512.0],
            },
            {
                'name': "style",
                'value': [0.010, 0.75, 0.001, 1.0],
                'range': [0.0, 1.0],
            },
        ],
        'pass_array': [
            {
                'render_target': {'width': 1.0, 'height': 1.0},
                'material': EFFECT,
                'depth_enable': True,
            },
        ],
    }


def write_json(path, value):
    """
    以缩进 UTF-8 JSON 格式写入生成文件。
    """
    # 保留缩进便于审查生成的官方后处理配置。
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    path.write_text(text, encoding="utf-8")


def main():
    """
    合并官方后处理配置并生成材质和来源记录。
    """
    # 命令行只允许覆盖目标游戏数据目录。
    parser = argparse.ArgumentParser(
        description="从目标网易包体保留内置后处理，只追加本模组的默认关闭通道。",
    )
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    args = parser.parse_args()
    vanilla = args.data / "resource_packs/vanilla_netease"
    provenance = {}
    # 两个固定入口分别保留 legacy / RNGL 原有的材质变体和渲染顺序。
    for name in ("post_process.json", "post_process_rngl.json"):
        source = vanilla / "graphics_settings" / name
        # 深拷贝原始配置，保留官方既有渲染顺序和 pass。
        original = json.loads(source.read_text(encoding="utf-8"))
        merged = copy.deepcopy(original)
        assert EFFECT not in merged['render_order']
        merged['render_order'].append(EFFECT)
        merged['process_array'].append(definition())
        write_json(ROOT / "src/rp/graphics_settings" / name, merged)
        provenance[name] = {
            'source': str(source),
            'sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
            'preserved_processes': len(original['process_array']),
        }

    # 材质声明使用本模组自有 shader 路径和固定采样状态。
    material = {
        'vertexShader': "shaders/dual_vector_foil/space_fall.vertex",
        'fragmentShader': "shaders/dual_vector_foil/space_fall.fragment",
        'vertexFields': [{'field': "Position"}, {'field': "UV0"}],
        'samplerStates': [
            {'samplerIndex': 0, 'textureWrap': "Clamp", 'textureFilter': "Bilinear"},
            {'samplerIndex': 2, 'textureWrap': "Clamp", 'textureFilter': "Point"},
        ],
        'states': ["DisableDepthTest"],
        'msaaSupport': "Both",
    }
    # postprocess.material 是官方自定义后处理固定入口；只声明本模组材质。
    write_json(ROOT / "src/rp/materials/postprocess.material", {EFFECT: material})
    write_json(ROOT / "docs/dev/space_fall_sources.json", provenance)
    print("Generated one disabled space-fall pass; preserved both vanilla pipelines.")


# endregion


if __name__ == "__main__":
    main()
