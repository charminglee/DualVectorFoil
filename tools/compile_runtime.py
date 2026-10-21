# -*- coding: utf-8 -*-
# =================================================
#  ⠀
#   Author: Nuoyan <https://github.com/charminglee>
#   Email : 1279735247@qq.com
#   Date  : 2026-10-21
#  ⠀
# =================================================


import json
import os
import sys


# region Runtime Compilation ==================================================


# 定位运行时脚本目录并累计编译结果。
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
runtime = os.path.join(root, "src", "bp", "dualvectorfoil_scripts")
count = 0
errors = []

# 逐个编译 Python 文件但不执行，也不生成 pyc。
for directory, dirs, files in os.walk(runtime):
    dirs[:] = [name for name in dirs if name != "__pycache__"]
    for name in files:
        if not name.endswith(".py"):
            continue
        path = os.path.join(directory, name)
        with open(path, "rb") as source:
            text = source.read()
        try:
            compile(text, path, "exec")
        except (SyntaxError, ValueError) as error:
            errors.append({
                'file': path,
                'error': str(error),
            })
        count += 1

# 输出机器可读摘要，并在非 Python 2.7 或存在错误时失败。
result = {
    'python': sys.version.split()[0],
    'compiled': count,
    'errors': errors,
}
print(json.dumps(result))
sys.exit(1 if errors or sys.version_info[:2] != (2, 7) else 0)


# endregion
