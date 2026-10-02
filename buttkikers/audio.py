# -*- coding: utf-8 -*-
"""Звук: поиск файлов в папке sounds и проигрывание (очередь с задержкой).

find_sfx/find_sfx_all ищут звук по имени, а если такого файла нет — берут любой
подходящий по слову из имени (см. SFX_MENU_KEY и подобные). Класс GameAudio —
часть Game: очередь отложенных звуков удара и шаги.
"""
import os
import random


from .settings import *  # noqa: F401,F403


def find_sfx(name, keyword="", subdir=""):
    """Путь к звуковому файлу из папки sounds (или sounds/subdir) или None.

    Сначала ищется файл с точным именем name. Если его нет — ищется любой звуковой файл
    (расширения из SFX_EXT), у которого keyword встречается в имени без учёта регистра.
    Благодаря этому звук подхватывается и как "menu.mp3", и как "Menu SFX 23.wav" —
    важен только формат и нужное слово в имени. keyword пустой — ищем только точное имя.
    subdir — вложенная папка (например "char" для звуков персонажа), без неё ищем в sounds.
    Можно указать как "char", так и "sounds/char" — префикс sounds/ не дублируется.
    """
    if not name and not subdir:
        return None
    sub = subdir.replace("/", os.sep).replace("\\", os.sep)
    if sub.lower().startswith("sounds" + os.sep):
        sub = sub[len("sounds") + 1:]          # уже с префиксом sounds — не добавляем второй раз
    sdir = os.path.join(BASE_DIR, "sounds", sub)
    exact = os.path.join(sdir, name)
    if os.path.exists(exact):
        return exact
    key = keyword.lower()
    if not key:
        return None
    try:
        found = sorted(n for n in os.listdir(sdir)
                       if n.lower().endswith(SFX_EXT)
                       and key in os.path.splitext(n)[0].lower())
    except OSError:
        return None
    return os.path.join(sdir, found[0]) if found else None


def find_sfx_all(prefix, subdir="", exclude=()):
    """Все звуковые файлы в папке sounds/subdir, имя которых начинается с prefix.

    Нужно для действий с несколькими вариантами звука: префикс "jump" находит
    jump1.mp3, jump2.mp3, jump3.mp3, jump4.mp3. Расширения берутся из SFX_EXT,
    сравнение без учёта регистра. Список отсортирован — порядок стабильный между
    запусками. Нет папки или нет файлов — пустой список.
    exclude — имена файлов, которые не надо брать (обычно значения из CHAR_SFX):
    например jumpALT.mp3 начинается с "jump", но привязан к своему действию и в
    случайные варианты прыжка попадать не должен.
    """
    sub = subdir.replace("/", os.sep).replace("\\", os.sep)
    if sub.lower().startswith("sounds" + os.sep):
        sub = sub[len("sounds") + 1:]
    sdir = os.path.join(BASE_DIR, "sounds", sub)
    low = (prefix or "").lower()
    skip = {str(e).lower() for e in exclude}
    if not low:
        return []
    try:
        names = sorted(n for n in os.listdir(sdir)
                       if n.lower().endswith(SFX_EXT)
                       and n.lower() not in skip
                       and os.path.splitext(n)[0].lower().startswith(low))
    except OSError:
        return []
    return [os.path.join(sdir, n) for n in names]


class GameAudio:
    """Часть Game: проигрывание звуков — очередь с задержкой и шаги.

    play_sfx уважает общий выключатель SOUND_ON и громкость, отложенные звуки
    (удар приходит на паре кадров позже начала анимации) копятся в очереди и
    выдаются по таймеру, шаги звучат через FOOTSTEP_TIME кадров на ходу.
    """


    def play_sfx(self, name):
        """Проигрывает короткий звук по имени (self.sfx).

        Если в self.sfx под этим именем лежит СПИСОК (действие с несколькими
        вариантами из CHAR_SFX_RANDOM, например прыжок jump1-jump4), играет один
        случайный вариант. Последний прозвучавший вариант исключается из выбора,
        чтобы соседние прыжки не звучали одинаково.
        """
        if not SOUND_ON:
            return
        snd = self.sfx.get(name)
        if snd is None:
            return
        if not isinstance(snd, list):
            snd.play()
            return
        # Несколько вариантов: случайный, но не тот, что только что прозвучал.
        last = self.sfx_last.get(name, -1)
        pool = [i for i in range(len(snd)) if i != last] or list(range(len(snd)))
        idx = random.choice(pool)
        self.sfx_last[name] = idx
        snd[idx].play()


    def play_sfx_delayed(self, name, ms=None):
        """Проигрывает звук персонажа с задержкой из CHAR_SFX_DELAY_MS.

        ms — строка с количеством миллисекунд (как в CHAR_SFX_DELAY_MS). Если ms не задан,
        берётся значение для name. "0" / пустая строка — звук сразу, без очереди.
        Иначе звук ставится в очередь self.sfx_queue и играет через указанное число кадров
        (update_sfx_queue уменьшает счётчик и проигрывает, когда он дошёл до нуля).
        """
        if not SOUND_ON:
            return
        if name not in self.sfx:
            return
        if ms is None:
            ms = CHAR_SFX_DELAY_MS.get(name, "0")
        try:
            delay_ms = float(str(ms).strip())
        except (TypeError, ValueError):
            print(f"[SFX] неверная задержка для {name}: {ms!r} — играю сразу")
            delay_ms = 0.0
        frames = int(round(delay_ms / 1000.0 * FPS))
        if frames <= 0:
            self.play_sfx(name)
        else:
            self.sfx_queue.append([frames, name])


    def update_sfx_queue(self):
        """Продвигает очередь отложенных звуков: счётчик кадров вниз, на нуле — проигрывание."""
        if not self.sfx_queue:
            return
        left = []
        for item in self.sfx_queue:
            item[0] -= 1
            if item[0] <= 0:
                self.play_sfx(item[1])
            else:
                left.append(item)
        self.sfx_queue = left

    def update_footsteps(self, pl):
        """Шаги: звук каждые FOOTSTEP_TIME кадров, пока боец бежит по земле.

        Во время переката шагов нет: персонаж катится, а не бежит (was_moving при
        перекате тоже True — скорость задаёт сама анимация), иначе шли бы rapid
        шаги поверх звука переката.
        """
        if pl.dead or pl.jumping or pl.rolling or not pl.on_ground or not pl.was_moving:
            pl.step_t = 0                      # стоим — первый шаг сразу на старте бега
            return
        if pl.step_t > 0:
            pl.step_t -= 1
            return
        # Крадущийся идёт вдвое медленнее бега (CRWALK_SPEED_MUL = 0.5), поэтому и
        # шаги вдвое реже: интервал делим на скорость крадущегося шага. Поменяете
        # CRWALK_SPEED_MUL — частота шагов поедет вместе с ним.
        step_every = FOOTSTEP_TIME
        if pl.crouch_walking:
            step_every = int(round(FOOTSTEP_TIME / max(0.1, float(CRWALK_SPEED_MUL))))
        pl.step_t = step_every
        self.play_sfx("step")