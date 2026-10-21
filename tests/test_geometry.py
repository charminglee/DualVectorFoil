# -*- coding: utf-8 -*-
# =================================================
#  ⠀
#   Author: Nuoyan <https://github.com/charminglee>
#   Email : 1279735247@qq.com
#   Date  : 2026-10-21
#  ⠀
# =================================================


# region Geometry Tests ==================================================


import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from build_geometry import unfold, resolve_inheritance, read_json


def cubes(model):
    """
    收集几何模型中所有骨骼的立方体面片。
    """
    return [cube for bone in model['bones'] for cube in bone.get('cubes', [])]


class GeometryTests(unittest.TestCase):
    """
    验证实体表面展开算法的面积和布局性质。
    """

    def test_east_facing_zero_width_plane_keeps_its_texture(self):
        """
        验证零厚度朝东平面不会丢失 UV 贴图。
        """
        model = unfold("geometry.arrow", {'bones': [{'name': "body", 'cubes': [
            {'size': [0, 5, 16], 'uv': {'east': {'uv': [0, 0]}}}]}]})
        flat = cubes(model)
        self.assertEqual(len(flat), 1)
        self.assertEqual(flat[0]['size'], [16, 0, 5])
        self.assertEqual(flat[0]['uv']['up']['uv_size'], [16, 5])

    def test_box_surface_area_is_preserved(self):
        """
        验证展开后的面片总面积等于原长方体表面积。
        """
        geometry = {
            'texturewidth': 64,
            'textureheight': 64,
            'bones': [
                {
                    'name': "body",
                    'cubes': [
                        {
                            'origin': [0, 0, 0],
                            'size': [8, 12, 4],
                            'uv': [0, 0],
                        },
                    ],
                },
            ],
        }
        net = cubes(unfold("geometry.test", geometry))
        self.assertEqual(len(net), 6)
        area = sum(c['size'][0] * c['size'][2] for c in net)
        self.assertEqual(area, 2 * (8 * 12 + 12 * 4 + 8 * 4))
        for c in net:
            self.assertEqual(c['origin'][1], 0)
            self.assertEqual(c['size'][1], 0)

    def test_legacy_inheritance_overrides_by_bone_name(self):
        """
        验证旧版几何继承按骨骼名称覆盖父级定义。
        """
        result, errors = resolve_inheritance({
            'geometry.base': {
                'texturewidth': 32,
                'bones': [
                    {'name': "head", 'cubes': [1]},
                    {'name': "body"},
                ],
            },
            'geometry.child:geometry.base': {
                'bones': [{'name': "head", 'cubes': [2]}],
            },
        })
        self.assertFalse(errors)
        self.assertEqual(result['geometry.child']['texturewidth'], 32)
        bones = {bone['name']: bone for bone in result['geometry.child']['bones']}
        self.assertEqual(bones['head']['cubes'], [2])

    def test_every_generated_surface_is_coplanar_and_disjoint(self):
        """
        验证生成目录中的面片均共面且互不重叠。
        """
        path = (
            Path(__file__).resolve().parents[1]
            / "src/rp/models/entity/dual_vector_foil/flat_entities.geo.json"
        )
        models = read_json(path)['minecraft:geometry']
        for model in models:
            flat = cubes(model)
            self.assertTrue(flat)
            for index, a in enumerate(flat):
                self.assertEqual(a['origin'][1], 0)
                self.assertEqual(a['size'][1], 0)
                for b in flat[index + 1:]:
                    overlap_x = min(
                        a['origin'][0] + a['size'][0],
                        b['origin'][0] + b['size'][0],
                    ) - max(a['origin'][0], b['origin'][0])
                    overlap_z = min(
                        a['origin'][2] + a['size'][2],
                        b['origin'][2] + b['size'][2],
                    ) - max(a['origin'][2], b['origin'][2])
                    self.assertFalse(
                        overlap_x > 0.0001 and overlap_z > 0.0001,
                        model['description']['identifier'],
                    )

    def test_empty_and_mesh_models_do_not_silently_turn_into_boxes(self):
        """
        验证空模型和网格模型不会被静默转换为方盒。
        """
        with self.assertRaises(ValueError):
            unfold("geometry.mesh", {'bones': [{'name': "mesh", 'poly_mesh': {'positions': [0]}}]})


if __name__ == "__main__":
    unittest.main()


# endregion
