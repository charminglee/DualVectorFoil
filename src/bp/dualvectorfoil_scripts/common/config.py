# -*- coding: utf-8 -*-
# =================================================
#  ⠀
#   Author: Nuoyan <https://github.com/charminglee>
#   Email : 1279735247@qq.com
#   Date  : 2026-11-11
#  ⠀
# =================================================


# 单个二向箔最多二维化的方块总数，不是单个分支的递归深度；实体不占用此额度。
MAX_FOIL_BLOCKS = 500000

# 单个二向箔捕获的实体数上限；-1 表示不限制。
MAX_FOIL_ENTITIES = -1

# 二维化搬移阶段每个服务端 tick 最多处理的方块数。
FOIL_BLOCKS_PER_TICK = 50

# 二向箔从前向出生点继续飞行的距离（格），必须大于 0。
FOIL_FLIGHT_DISTANCE = 12.0

# 二向箔逐渐减速至静止所需的时间（秒），必须大于 0。
FOIL_FLIGHT_SECONDS = 3.0
