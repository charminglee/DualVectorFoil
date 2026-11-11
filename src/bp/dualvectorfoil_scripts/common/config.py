# -*- coding: utf-8 -*-
# =================================================
#  ⠀
#   Author: Nuoyan <https://github.com/charminglee>
#   Email : 1279735247@qq.com
#   Date  : 2026-11-11
#  ⠀
# =================================================


# 跌落球形半径，单位为格；球心为二向箔最终静止位置所在格点。
FOIL_FALL_RADIUS = 60

# 单个二向箔捕获的实体数上限；-1 表示不限制。
MAX_FOIL_ENTITIES = -1

# 每个服务端 tick 应用的方块数；-1 在区块就绪后即刻完成全部跌落。
FOIL_BLOCKS_PER_TICK = 50

# 二向箔从前向出生点继续飞行的距离（格），必须大于 0。
FOIL_FLIGHT_DISTANCE = 12.0

# 二向箔逐渐减速至静止所需的时间（秒），必须大于 0。
FOIL_FLIGHT_SECONDS = 3.0
