# -*- coding: utf-8 -*-
# =================================================
#  ⠀
#   Author: Nuoyan <https://github.com/charminglee>
#   Email : 1279735247@qq.com
#   Date  : 2026-11-13
#  ⠀
# =================================================


# 空间跌落画质：0 关闭，1 低配（坍缩切片/断裂光带），2 标准（增加压缩折射/色散）。
FOIL_FX_QUALITY = 2

# 视觉场半径与观看距离，单位为格；不改变实际二维化的方块范围。
FOIL_FX_RADIUS = 100.0
FOIL_FX_VIEW_DISTANCE = 256.0

# 总强度 [0, 1]；0 会关闭后处理通道。
FOIL_FX_STRENGTH = 1.0


# 同步间隔使用服务端脚本 tick；以下生命周期参数使用客户端墙钟秒数。
# 每个任务只触发一次，所有动画参数由本轮客户端墙钟时间推导。
EFFECT = "nuoyan_space_fall"
EVENT = "FoilSpaceFallState"
SYNC_TICKS = 10  # 仅限制附近玩家的检查频率，不续期动画。
PLAY_SECONDS = 5.0
FADE_IN = 0.45
FADE_OUT = 1.1

# 对外部配置限幅，避免无效值进入运行期。
RADIUS = min(160.0, max(4.0, float(FOIL_FX_RADIUS)))
VIEW_DISTANCE = max(RADIUS + 8.0, float(FOIL_FX_VIEW_DISTANCE))
QUALITY = min(2, max(0, int(FOIL_FX_QUALITY)))
STRENGTH = min(1.0, max(0.0, float(FOIL_FX_STRENGTH)))

# style 的四分量依次为折射幅度、切片辉光增益、色散幅度和标准画质开关。
# 折射基础幅度为画面短边的 2.8%，色散为 0.3%；低配会跳过相关采样。
STYLE = (0.028, 0.95, 0.003, 1.0 if QUALITY == 2 else 0.0)


def process_definition(name):
    """
    为并发光场创建独立参数的单通道配置，复用现有空间跌落材质。
    """
    return {
        'name': name,
        'enable': False,
        'paras': [
            {'name': "field", 'value': [0.0, 0.0, 0.0, RADIUS], 'range': [-30000000.0, 30000000.0]},
            {'name': "shape", 'value': [0.0, 0.0, 0.0, 0.0], 'range': [-512.0, 512.0]},
            {'name': "style", 'value': list(STYLE), 'range': [0.0, 1.0]},
        ],
        'pass_array': [
            {
                'render_target': {'width': 1.0, 'height': 1.0},
                'material': EFFECT,
                'depth_enable': True,
            },
        ],
    }
