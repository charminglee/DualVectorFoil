# -*- coding: utf-8 -*-
# =================================================
#
#   Author: Nuoyan <https://github.com/charminglee>
#   Email : 1279735247@qq.com
#   Date  : 2026-11-13
#
# =================================================


from .config import OPEN_SECONDS, SPREAD_SECONDS, PLAY_SECONDS, FADE_IN, FADE_OUT


def smooth_unit(value):
    """
    限幅到零至一，并生成端点导数为零的三次平滑权重。
    """
    value = min(1.0, max(0.0, value))
    return value * value * (3.0 - 2.0 * value)


def sky_progress(age):
    """
    零至一展开，随后一至二扩散；全覆盖后保持二直到复原结束。
    """
    return smooth_unit(age / OPEN_SECONDS) + smooth_unit((age - OPEN_SECONDS) / SPREAD_SECONDS)


def envelope(age):
    """
    环境与后处理共用淡入、六秒停留和四秒恢复的同一包络。
    """
    if age < 0.0 or age >= PLAY_SECONDS:
        return 0.0
    return smooth_unit(age / FADE_IN) * (1.0 - smooth_unit((age - (PLAY_SECONDS - FADE_OUT)) / FADE_OUT))
