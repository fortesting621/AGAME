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
# Раскладка кнопок у этого пульта ИЗМЕРЕНА (pad_learn.py), а не взята из документации:
# 0=A, 1=B, 2=X, 3=Y, 4=LB, 5=RB, 6=Start, 7=Select, 8-10 не используются.
# Оси: 0/1 — левый стик, 2/3 — правый стик, 4 — LT, 5 — RT. У этого пульта триггеры
# идут как 16-битные оси: В ПОКОЕ они стоят в -1.0, при нажатии уходят в +1.0
# (замерено axis_probe.py), поэтому нажатие ловится по значению ВЫШЕ порога.
# На стике работает ось 0 (влево-вправо) и ось 1 (вверх-вниз), плюс крестовина (hat 0).
def current_pad_count():
    """Сколько геймпадов сейчас открыто (список живёт в settings.PADS)."""
    return len(settings.PADS)


def reopen_gamepads():
    """Переоткрыть пульты: закрыть старые хендлы и открыть заново.

    Зачем: USB-пульт засыпает по энергосбережению. SDL оставляет его в списке
    (get_count() == 1), но события и оси с «усыпшего» хендла не приходят — они
    навсегда остаются в покое, и перекат/панорама (аналиоговые триггеры) молчат.
    Пересоздание хендла возвращает живые значения. Старые хендлы закрываются
    через quit(), иначе они копятся в pygame и течёт число SDL-устройств.
    """
    for js in settings.PADS:
        try:
            js.quit()
        except pygame.error:
            pass
    return init_gamepads()


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
    """Нажат ли аналоговый правый триггер геймпада idx (перекат).

    У этого пульта триггеры приходят как ОСИ, а не кнопки, и замерено (axis_probe.py):
    в покое ось = -1.0, при нажатии уходит в +1.0. Поэтому нажатие — это значение
    ВЫШЕ порога, как у левого триггера. Раньше здесь стояло условие «ниже порога»,
    написанное под другой пульт: на нашем покой -1.0 проходил как нажатие всегда,
    и перекат срабатывал сам на первом кадре игры, а реальное нажатие RT не работало.
    """
    if not GAMEPAD_ON or idx >= len(settings.PADS):
        return False
    js = settings.PADS[idx]
    if axis < 0 or axis >= js.get_numaxes():
        return False
    try:
        return js.get_axis(axis) > ROLL_TRIGGER_THRESH
    except pygame.error:
        return False


def pad_trigger_left(idx, axis=PAD_LT_AXIS):
    """Нажат ли ЛЕВЫЙ аналоговый триггер геймпада idx (панорама/изоляция фона).

    Ось ведёт себя так же, как правый триггер: покой = -1.0, нажатие = +1.0, поэтому
    здесь нажатие — значение ВЫШЕ порога.
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
    kik = btn(1)                    # B — обычный удар ноги (как K)
    kick = btn(3)                   # Y — сильный удар ногой (как I)
    roll = pad_trigger(idx)         # правый триггер — перекат (как O)
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