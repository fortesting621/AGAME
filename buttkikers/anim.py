# -*- coding: utf-8 -*-
"""Тайминги анимаций: сколько кадров игры длится прыжок, перекат и удар.

Все анимации лежат в APNG по 30 кадров/с, но показываются в игре реже (шаг
просмотра задаёт MOVE_ANIM_FPS и подобные). Эти функции переводят «кадры
анимации» в «кадры игры» — отсюда и берутся все длительности в игре.
"""
from . import settings
from .settings import *  # noqa: F401,F403

def jump_duration(anim_n=0):
    """Длительность прыжка в кадрах игры.

    Анимация проигрывается со своей скоростью JUMP_ANIM_FPS, поэтому прыжок длится ровно
    столько, сколько нужно на всю анимацию: n / JUMP_ANIM_FPS секунд. Именно она задаёт
    длительность прыжка, а не наоборот.
    """
    n = anim_n or settings.JUMP_ANIM_N
    if n <= 0:
        return max(1, int(round(FPS * 0.5)))     # анимации нет — прыжок на полсекунды
    return max(1, int(round(n / JUMP_ANIM_FPS * FPS)))


def roll_duration(anim_n=0):
    """Длительность переката в кадрах игры.

    Как прыжок и удар: анимация идёт со своей частотой ROLL_ANIM_FPS, поэтому перекат
    длится ровно n / ROLL_ANIM_FPS секунд. Движение вперёд держится ровно столько, сколько
    идёт анимация, и остановить его нельзя.
    """
    n = anim_n or settings.ROLL_ANIM_N
    if n <= 0:
        return max(1, int(round(FPS * 0.5)))     # анимации нет — перекат на полсекунды
    return max(1, int(round(n / float(ROLL_ANIM_FPS) * FPS)))


def attack_duration(anim_n=0):
    """Длительность удара в кадрах игры.

    Как и прыжок: анимация проигрывается со своей скоростью ATTACK_ANIM_FPS, поэтому удар
    длится ровно столько, сколько нужно на всю анимацию — n / ATTACK_ANIM_FPS секунд.
    Без этого кадры шли бы по одному на игровой кадр и удар был бы вдвое быстрее.
    """
    if anim_n <= 0:
        return 1
    return max(1, int(round(anim_n / ATTACK_ANIM_FPS * FPS)))


def move_shown(total, fps=0):
    """Сколько кадров анимации реально показывается при заданной частоте (fps = 0 -> MOVE_ANIM_FPS).

    При частоте MOVE_SRC_FPS (30) показываются все кадры — как было раньше. При меньшем значении
    часть кадров пропускается, а длительность анимации (цикла, прыжка, приседа) от этого НЕ
    меняется: показанный кадр просто держится дольше.
    """
    if total <= 0:
        return 0
    rate = float(fps) if fps else float(MOVE_ANIM_FPS)
    return max(1, min(total, int(round(total * rate / float(MOVE_SRC_FPS)))))


def move_frame_index(game_frame, phase, total):
    """Номер кадра ЦИКЛИЧЕСКОЙ анимации движения: бег, крадущаяся ходьба, покой.

    Позиция считается в показах, а не в кадрах анимации: счётчик обновлений идёт со скоростью
    MOVE_ANIM_FPS (при 30 и FPS = 60 — каждый второй игровой кадр, как раньше), а на экран
    выводится только move_shown(total) кадров из total. Цикл поэтому занимает те же
    total / MOVE_SRC_FPS секунд — меняется только частота обновления. phase — сдвиг фазы в
    кадрах исходной анимации (у каждого игрока свой, чтобы не шли в унисон).
    """
    shown = move_shown(total)
    if shown <= 0:
        return 0
    tick = int(game_frame * float(MOVE_ANIM_FPS) / FPS)   # счётчик обновлений анимации
    pos = (tick + phase * shown // total) % shown          # позиция в цикле
    return int(round(pos * total / float(shown))) % total  # кадр анимации для этой позиции


def move_phase_for_frame(game_frame, total, target=0):
    """Обратный расчёт: фаза, при которой на кадре game_frame показывается кадр target.

    Нужна, чтобы переход «прыжок -> бег» начинался с нужного кадра анимации. Раньше фаза
    подбиралась как -(frame // 2), что верно только при MOVE_ANIM_FPS = 30: при другой частоте
    после приземления показывался случайный кадр цикла.

    Решается перебором: всего кадров немного (десятки), а перебор даёт ТОЧНОЕ попадание.
    Одной арифметикой не обойтись — в move_frame_index фаза и кадр связаны делением
    с округлением, и обратный ход промахивался бы на кадр. Вызывается только в момент
    приземления, поэтому цена перебора не имеет значения.

    target — кадр анимации, который должен оказаться на экране в момент game_frame.
    """
    if move_shown(total) <= 0:
        return 0
    want = int(target) % max(1, total)
    # Не каждый кадр анимации выводится на экран: при MOVE_ANIM_FPS меньше MOVE_SRC_FPS
    # часть кадров пропускается. Тогда берём ближайший из показываемых, иначе фаза не
    # подобралась бы совсем и бег стартовал бы со случайного кадра.
    if want not in {move_frame_index(0, p, total) for p in range(max(1, total))}:
        shown_frames = [move_frame_index(0, p, total) for p in range(max(1, total))]
        want = min(shown_frames, key=lambda f: (min(abs(f - want), total - abs(f - want)), f))
    for phase in range(max(1, total)):
        if move_frame_index(game_frame, phase, total) == want:
            return phase
    return 0        # недостижимо для total > 1, но пусть не будет исключения


def move_frame_thin(progress, total, fps=0):
    """Номер кадра ОДНОРАЗОВОЙ анимации движения по пройденной части 0..1 — прыжок, присед.

    Первый и последний кадры показываются всегда (поза в начале и в конце важна), между ними —
    только move_shown(total, fps) кадров вместо всех. Длительность задаёт вызывающий код, она не
    меняется: прыжок летит как раньше, присед длится как раньше.
    fps = 0 -> общий MOVE_ANIM_FPS; для прыжка передаётся MOVE_ANIM_JUMP_FPS.
    """
    if total <= 1:
        return 0
    shown = move_shown(total, fps)
    if shown <= 1:
        return 0
    pos = min(shown - 1, int(max(0.0, min(1.0, float(progress))) * shown))
    return min(total - 1, int(round(pos * (total - 1) / float(shown - 1))))


def move_frame_once(elapsed, dur, total, fps=0):
    """Номер кадра одноразовой анимации по прошедшим кадрам игры: elapsed из dur.

    Для прыжка: dur = self.jump_dur (его задаёт jump_duration()), total = self.jump_n,
    fps = MOVE_ANIM_JUMP_FPS (у прыжка своя частота, у остального — общая MOVE_ANIM_FPS).
    """
    return move_frame_thin(elapsed / float(max(1, dur)), total, fps)


def _scale_txt(sc):
    """Подпись множителя масштаба для HUD: число или «X/Y» для пары осей."""
    if isinstance(sc, (tuple, list)):
        return f"{float(sc[0]):.2f}/{float(sc[1]):.2f}"
    return f"{float(sc):.2f}" if sc else "1.00"