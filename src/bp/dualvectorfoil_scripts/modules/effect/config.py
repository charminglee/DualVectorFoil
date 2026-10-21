# -*- coding: utf-8 -*-
# =================================================
#  ⠀
#   Author: Nuoyan <https://github.com/charminglee>
#   Email : 1279735247@qq.com
#   Date  : 2026-10-21
#  ⠀
# =================================================


# 空间跌落画质：0 关闭，1 低配（光环/切片/网格），2 标准（增加折射/色散）。
FOIL_FX_QUALITY = 2

# 视觉场半径与观看距离，单位为格；不改变实际二维化的方块范围。
FOIL_FX_RADIUS = 14.0
FOIL_FX_VIEW_DISTANCE = 64.0

# 总强度 [0, 1]；0 会关闭后处理通道。
FOIL_FX_STRENGTH = 0.8


# 协议名称与生命周期时间。
EFFECT = "nuoyan_space_fall"
EVENT = "FoilSpaceFallState"
SYNC_TICKS = 10  # 脚本 tick 为 30 Hz，稳定阶段最多 3 次/秒。
STALE_SECONDS = 2.5
FADE_IN = 0.45
FADE_OUT = 1.1
MIN_LIFETIME = 0.65

# 对外部配置限幅，避免无效值进入运行期。
RADIUS = min(24.0, max(4.0, float(FOIL_FX_RADIUS)))
VIEW_DISTANCE = max(RADIUS + 8.0, float(FOIL_FX_VIEW_DISTANCE))
QUALITY = min(2, max(0, int(FOIL_FX_QUALITY)))
STRENGTH = min(1.0, max(0.0, float(FOIL_FX_STRENGTH)))

# 折射最多为画面短边的 1%，色散为 0.1%；低配会跳过相关采样。
STYLE = (0.010, 0.75, 0.001, 1.0 if QUALITY == 2 else 0.0)
