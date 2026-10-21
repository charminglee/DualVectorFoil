# -*- coding: utf-8 -*-
# =================================================
#  ⠀
#   Author: Nuoyan <https://github.com/charminglee>
#   Email : 1279735247@qq.com
#   Date  : 2026-10-21
#  ⠀
# =================================================


# 单个二向箔最多二维化的方块总数，不是单个分支的递归深度；实体不占用此额度。
MAX_FOIL_BLOCKS = 500000

# 单个二向箔捕获的实体数上限；None 表示不限制。
MAX_FOIL_ENTITIES = None

# 二维化搬移阶段每个服务端 tick 最多处理的方块数。
FOIL_BLOCKS_PER_TICK = 50
