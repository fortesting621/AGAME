# -*- coding: utf-8 -*-
"""Геймпад: чтение стика, крестовины, кнопок и аналоговых триггеров.

Индекс 0 достаётся первому игроку, индекс 1 — второму (см. pad_state).
Список открытых геймпадов живёт в settings.PADS: он пересоздаётся при каждом
init_gamepads, поэтому читать его надо через settings, а не копию из импорта.
"""
import pygame

from . import settings
from .settings import *  # noqa: F401,F403


# Геймпад в Windows через pygame: индекс 0 достаётся первому игроку, индекс 1 — второму.
# Раскладка кнопок стандартная (XInput/DInput): 0=A, 1=B, 2=X, 3=Y, 7=Start, 8=Back.
# На стике работает ось 0 (влево-вправо) и ось 1 (вверх-вниз), плюс крестовина (hat 0).
def init_gamepads():
    """Открыть геймпады. Возвращает список подключённых (максимум 2: P1 и P2)."""
    settings.PADS = []
    if not GAMEPAD_ON:
        return settings.PADS
    try:
        pygame.joystick.init()
        count = pygame.joystick.get_count()
    except pygame.error:
        return settings.PADS
    for i in range(min(count, 2)):
        try:
            js = pygame.joystick.Joystick(i)
            js.init()
            settings.PADS.append(js)
        except pygame.error:
            pass
    return settings.PADS


def pad_trigger(idx, axis=ROLL_TRIGGER_AXIS):
    """Нажат ли аналоговый триггер геймпада idx (по умолчанию правый).

    У Xbox 360 триггеры приходят как ОСИ, а не кнопки: в покое ось = +1.0, при нажатии
    уходит в -1.0. Поэтому нажатие — это значение НИЖЕ порога, а не выше, как у стика.
    """
    if not GAMEPAD_ON or idx >= len(settings.PADS):
        return False
    js = settings.PADS[idx]
    if axis < 0 or axis >= js.get_numaxes():
        return False
    try:
        return js.get_axis(axis) < -ROLL_TRIGGER_THRESH
    except pygame.error:
        return False


def pad_trigger_left(idx, axis=PAD_LT_AXIS):
    """Нажат ли ЛЕВЫЙ аналоговый триггер геймпада idx.

    Ось зеркальна правому триггеру: у Xbox 360 левый в покое = -1.0 и при нажатии уходит
    в +1.0, а правый — наоборот. Поэтому здесь нажатие — значение ВЫШЕ порога.
    Раньше изоляция висела на PAD_BTN_ISOLATE = (6,), но на этом пульте кнопка 6 —
    это Start: нажатие одновременно начинало игру и переключало изоляцию. Настоящий
    триггер приходит как ось, а не как событие JOYBUTTONDOWN, поэтому ловится здесь.
    """
    if not GAMEPAD_ON or idx >= len(settings.PADS):
        return False
    js = settings.PADS[idx]
    if axis < 0 or axis >= js.get_numaxes():
        return False
    try:
        return js.get_axis(axis) > PAD_LT_THRESH
    except pygame.error:
        return False


def pad_state(idx):
    """(влево, вправо, вверх, вниз, кулак, обычная нога, сильная нога, перекат)
    с геймпада idx (0 = P1, 1 = P2)."""
    if not GAMEPAD_ON or idx >= len(settings.PADS):
        return (False,) * 8
    js = settings.PADS[idx]
    dz = PAD_DEADZONE

    def ax(i):
        return js.get_axis(i) if i < js.get_numaxes() else 0.0

    def btn(i):
        return bool(js.get_button(i)) if i < js.get_numbuttons() else False

    try:
        hx, hy = js.get_hat(0) if js.get_numhats() else (0, 0)
    except pygame.error:
        hx, hy = 0, 0
    left = ax(0) < -dz or hx < 0
    right = ax(0) > dz or hx > 0
    up = ax(1) < -dz or hy > 0 or btn(0)    # стик, крестовина или кнопка A (A = только прыжок)
    down = ax(1) > dz or hy < 0
    # A (btn 0) намеренно НЕ входит в удар рукой: она уже прыжок, иначе одно
    # нажатие давало прыжок + удар. Удар рукой — только X (btn 2), как J на клавиатуре.
    punch = btn(2)                   # X — удар рукой (как J)
    kik = btn(1)                    # B — обычный удар ноги (как L)
    kick = btn(3)                   # Y — сильный удар ногой (как K)
    roll = pad_trigger(idx)         # правый триггер — перекат
    return left, right, up, down, punch, kik, kick, roll


def pad_menu(idx):
    """(вверх, вниз, старт) с геймпада — для навигации в главном меню."""
    if not GAMEPAD_ON or idx >= len(settings.PADS):
        return False, False, False
    js = settings.PADS[idx]
    dz = PAD_DEADZONE

    def ax(i):
        return js.get_axis(i) if i < js.get_numaxes() else 0.0

    def btn(i):
        return bool(js.get_button(i)) if i < js.get_numbuttons() else False

    try:
        hx, hy = js.get_hat(0) if js.get_numhats() else (0, 0)
    except pygame.error:
        hx, hy = 0, 0
    up = ax(1) < -dz or hy > 0 or btn(3)
    down = ax(1) > dz or hy < 0 or btn(1)
    start = btn(0) or btn(7)        # A или Start — начать игру
    return up, down, start