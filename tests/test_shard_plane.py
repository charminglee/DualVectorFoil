# -*- coding: utf-8 -*-
"""采样实际资源中的 Molang 算式，验证碎片落面、朝向和停留阶段。"""
import json
import math
import os
import random
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def evaluate(expression, age, lifetime, seed):
    """
    仅求值本次资源使用的算术子集；不是引擎 Molang 兼容性测试。
    """
    if not isinstance(expression, (str, type(u""))):
        return expression
    values = {'particle_age': age, 'particle_lifetime': lifetime}
    values.update(('particle_random_' + str(i + 1), seed[i]) for i in range(3))
    for name, value in values.items():
        expression = expression.replace('variable.' + name, repr(value))
    for name in ('sin', 'cos', 'min', 'pow'):
        expression = expression.replace('math.' + name, name)
    return eval(expression, {'__builtins__': {}}, {
        'sin': lambda angle: math.sin(math.radians(angle)),
        'cos': lambda angle: math.cos(math.radians(angle)),
        'min': min, 'pow': pow,
    })


class ShardPlaneTests(unittest.TestCase):
    def test_scattered_positions_settle_flat_and_hold_before_fading(self):
        """
        多组随机种子覆盖回落全过程、落面后的静止以及可见停留窗口。
        """
        rng = random.Random(42)
        for name in ('cataclysm_shards', 'cataclysm_embers'):
            path = os.path.join(ROOT, 'src', 'rp', 'particles', 'dual_vector_foil', name + '.json')
            with open(path) as stream:
                components = json.load(stream)['particle_effect']['components']
            motion = components['minecraft:particle_motion_parametric']
            billboard = components['minecraft:particle_appearance_billboard']
            self.assertEqual(billboard['facing_camera_mode'], 'direction_z')
            self.assertEqual(billboard['direction']['mode'], 'custom_direction')
            lifetime = components['minecraft:particle_lifetime_expression']['max_lifetime']
            landing = lifetime * 0.75
            for seed in [(0, 0, 0), (1, 1, 1)] + [tuple(rng.random() for _ in range(3)) for _ in range(32)]:
                sample = lambda expression, age: evaluate(expression, age, lifetime, seed)
                origin = [sample(expr, 0) for expr in motion['relative_position']]
                spin = sample(motion['rotation'], landing)
                for index in range(49):
                    age = lifetime * index / 48.0
                    position = [sample(expr, age) for expr in motion['relative_position']]
                    self.assertEqual(position[0], origin[0])
                    self.assertEqual(position[2], origin[2])
                    self.assertGreaterEqual(position[1], -1e-10)
                    direction = [sample(expr, age) for expr in billboard['direction']['custom_direction']]
                    self.assertAlmostEqual(sum(v * v for v in direction), 1.0)
                    if age < landing:
                        continue
                    self.assertAlmostEqual(position[1], 0.0)
                    self.assertAlmostEqual(direction[0], 0.0)
                    self.assertAlmostEqual(direction[1], 1.0)
                    self.assertAlmostEqual(direction[2], 0.0)
                    self.assertEqual(sample(motion['rotation'], age), spin)
                alpha = components['minecraft:particle_appearance_tinting']['color'][3]
                self.assertAlmostEqual(sample(alpha, landing), 1.0)
                self.assertAlmostEqual(sample(alpha, landing + 0.5), 1.0)
                self.assertAlmostEqual(sample(alpha, lifetime), 0.0)


if __name__ == '__main__':
    unittest.main()
