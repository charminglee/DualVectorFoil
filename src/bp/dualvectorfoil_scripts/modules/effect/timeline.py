# -*- coding: utf-8 -*-
# =================================================
#
#   Author: Nuoyan <https://github.com/charminglee>
#   Email : 1279735247@qq.com
#   Date  : 2026-11-13
#
# =================================================


from .config import OPEN_SECONDS, SPREAD_SECONDS, HOLD_SECONDS, RESTORE_SECONDS, PLAY_SECONDS, FADE_IN, FADE_OUT


def smooth_unit(value):
    """
    限幅到零至一，并生成端点导数为零的三次平滑权重。
    """
    value = min(1.0, max(0.0, value))
    return value * value * (3.0 - 2.0 * value)


def sky_progress(age):
    """
    展开和扩散后停留六秒；恢复时先收回天空裂纹，再合上主裂口。
    """
    restore_start = OPEN_SECONDS + SPREAD_SECONDS + HOLD_SECONDS
    if age <= restore_start:
        return smooth_unit(age / OPEN_SECONDS) + smooth_unit((age - OPEN_SECONDS) / SPREAD_SECONDS)
    # 四秒恢复的前六成收回裂纹，后四成让裂口两侧向中间闭合。
    retreat_seconds = RESTORE_SECONDS * 0.6
    closing_age = age - restore_start
    return (
        2.0
        - smooth_unit(closing_age / retreat_seconds)
        - smooth_unit((closing_age - retreat_seconds) / (RESTORE_SECONDS - retreat_seconds))
    )


def envelope(age):
    """
    环境与后处理共用淡入、六秒停留和四秒恢复的同一包络。
    """
    if age < 0.0 or age >= PLAY_SECONDS:
        return 0.0
    return smooth_unit(age / FADE_IN) * (1.0 - smooth_unit((age - (PLAY_SECONDS - FADE_OUT)) / FADE_OUT))
