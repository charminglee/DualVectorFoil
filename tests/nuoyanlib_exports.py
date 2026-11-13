# -*- coding: utf-8 -*-
"""离线加载本次复用的真实库函数，避免启动 SDK 或复制库实现。"""

import ast
import math
import os


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIBRARY = os.path.join(ROOT, "src", "bp", "dualvectorfoil_scripts", "nuoyanlib")


def install_exports(target):
    """
    只编译所需函数及其纯算法依赖，在组件替身的命名空间内执行。
    """
    sources = (
        ("common/mc_math/mc_math.py", ("pos_floor", "chunk_pos", "lerp")),
        ("common/mc_math/vector.py", (
            "rot2dir", "vec_add", "vec_mul", "vec_length", "vec_length2",
            "is_zero_vec", "vec_normalize", "_is_scalar",
        )),
        ("server/entity.py", ("launch_projectile",)),
    )
    target.__dict__.update((name, getattr(math, name)) for name in (
        "sin", "cos", "radians", "sqrt",
    ))
    for relative, names in sources:
        if relative.startswith("server/") and not target.__name__.endswith(".server"):
            continue
        path = os.path.join(LIBRARY, *relative.split("/"))
        with open(path, "rb") as source:
            tree = ast.parse(source.read(), path)
        tree.body = [node for node in tree.body if (
            isinstance(node, ast.FunctionDef) and node.name in names
            or isinstance(node, ast.ImportFrom) and node.module == "__future__"
            or isinstance(node, ast.Assign) and any(
                isinstance(item, ast.Name) and item.id == "_ZERO_EPS"
                for item in node.targets
            )
        )]
        eval(compile(tree, path, "exec"), target.__dict__)
