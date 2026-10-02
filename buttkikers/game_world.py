# -*- coding: utf-8 -*-
"""Часть Game: фон, слои параллакса и пол."""
import os


import pygame

from .settings import *  # noqa: F401,F403



class GameWorld:
    """Мир вокруг бойцов: задний фон, полосы параллакса, пол, режим изоляции.

    Рисует всё, что не является бойцами и не является панелью: фоновые картинки
    (в том числе анимации-папки и масштаб из суффикса имени), слои par1/par2/
    lay0/parNEW и пол. Каждый слой — полоса, склеенная из картинок (build_strip).
    """

    @staticmethod
    def back_order(name):
        """Порядок фона по имени: числовой префикс (1_ 2_ 3_...) — порядок появления.
        Без префикса — по списку BACK_FALLBACK, затем по алфавиту."""
        try:
            return (int(name.split("_")[0]), 0, name)
        except ValueError:
            try:
                return (9999, BACK_FALLBACK.index(name), name)
            except ValueError:
                return (9999, 9999, name)


    def cycle_backdrop(self, step, src=""):
        """Переключение заднего фона на step (+1 вперёд, -1 назад). src — для отладки."""
        if len(self.par_backs) <= 1:
            print(f"[DEBUG] {src} — других задних слоёв нет")
            return
        self.par_back_idx = (self.par_back_idx + step) % len(self.par_backs)
        self.par_back_name = self.par_backs[self.par_back_idx][0]
        # Кэш масштабирования относится к прошлой картинке — сбрасываем, иначе новый фон
        # нарисуется старым размером (back_scaled сверяет исходник в кэше).
        self.back_cache = None
        self.print_backdrop()


    def toggle_isolate(self, src=""):
        """Переключение изоляции фона (Q с клавиатуры, LT на геймпаде).
        В изоляции видны только задний фон, персонажи и пол."""
        self.isolate = not self.isolate
        print(f"[DEBUG] {src} — изоляция фона: "
              f"{'ВКЛ' if self.isolate else 'ВЫКЛ'}")


    def print_backdrop(self):
        """Печать активного фона и его масштаба (суффикс имени задаёт базовый)."""
        own = None
        if self.par_backs:
            entry = self.par_backs[self.par_back_idx]
            own = entry[3] if len(entry) > 3 else None
        base = own if own is not None else BACK_SCALE
        print(f"[DEBUG] задний фон -> {self.par_back_name} | масштаб {base:.2f}")


    @staticmethod
    def back_scale_of(name):
        """Масштаб фона из суффикса имени: "1_new river_80" -> 0.80, "2_river_125" -> 1.25.

        Ищем последнее "_NNN" в имени. Число без точки читается как ПРОЦЕНТЫ:
        "_80" -> 0.80, "_125" -> 1.25. С точкой — как готовое значение: "_0.8" -> 0.8.
        Без суффикса возвращаем None, тогда применяется общий BACK_SCALE.
        Расширение отбрасываем ТОЛЬКО по списку картинок: os.path.splitext резал бы
        и имя с точкой в масштабе ("river_1.25" -> "river_1" + ".25").
        """
        if not BACK_SCALE_SUFFIX:
            return None
        stem = name
        for ext in (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"):
            if stem.lower().endswith(ext):
                stem = stem[: -len(ext)]
                break
        head, sep, tail = stem.rpartition("_")
        if not sep or not tail:
            return None
        try:
            val = float(tail)          # "_80" -> 80.0 -> 0.8; "_1.25" -> 1.25
        except ValueError:
            return None
        if "." not in tail:
            val /= 100.0               # целое число — это проценты
        if not (BACK_SCALE_MIN <= val <= BACK_SCALE_MAX):
            return None                # вне диапазона — считаем, что суффикса нет
        return val
        return val


    @staticmethod
    def mirror_glue(im):
        """Задний план: зеркалим картинку и склеиваем с оригиналом.
        Стык левого и правого края становится бесшовным, дальше тайлинг идёт вставкой."""
        w, h = im.get_size()
        if w <= 0 or h <= 0:
            return im
        out = pygame.Surface((w * 2, h), pygame.SRCALPHA)
        out.blit(im, (0, 0))
        out.blit(pygame.transform.flip(im, True, False), (w, 0))
        return out.convert_alpha() if im.get_flags() & pygame.SRCALPHA else out.convert()


    def get_anim_frames(self, idx, folder):
        """Кадры анимированного фона читаем только когда он выбран, потом держим в кеше.
        Картинки грузим как есть — размер задаёт BACK_SCALE при отрисовке."""
        if idx in self.anim_cache:
            return self.anim_cache[idx]
        frames = []
        for fn in sorted(f for f in os.listdir(folder)
                         if f.lower().endswith((".png", ".jpg", ".jpeg"))):
            try:
                frames.append(self.mirror_glue(pygame.image.load(os.path.join(folder, fn))))
            except pygame.error:
                pass
        self.anim_cache[idx] = frames
        # Имя для подписи и собственный масштаб из суффикса сохраняем — 4-е поле нужно
        # дальше при отрисовке, без него фон нарисовался бы с общим BACK_SCALE.
        own = self.par_backs[idx][3] if len(self.par_backs[idx]) > 3 else None
        self.par_backs[idx] = (f"{os.path.basename(folder)} ({len(frames)} кадра)",
                               "anim", frames, own)
        if self.par_back_idx == idx:
            self.par_back_name = self.par_backs[idx][0]
        return frames


    def back_scaled(self, im, scale=None):
        """Задний план, умноженный на масштаб scale (по умолчанию — текущий
        self.back_eff_scale, иначе self.back_scale). Общий масштаб на обе оси, без обрезки.
        Результат кэшируем: пересчитываем только когда сменилась картинка или масштаб
        (иначе масштабировали бы огромную картинку каждый кадр)."""
        if scale is None:
            scale = getattr(self, "back_eff_scale", None)
            if scale is None:
                scale = self.back_scale
        w, h = im.get_size()
        dw, dh = max(1, int(w * scale)), max(1, int(h * scale))
        cache = getattr(self, "back_cache", None)
        if cache is not None and cache[0] is im and cache[1:] == (w, h, dw, dh):
            return cache[4]                    # та же картинка и тот же размер — отдаём готовое
        scaled = im if (dw, dh) == (w, h) else pygame.transform.smoothscale(im, (dw, dh))
        self.back_cache = (im, w, h, dw, dh, scaled)   # исходник держим в кэше, чтобы не пересчитывать
        return scaled


    def draw_loop_image(self, im, off, y):
        """Рисует картинку по кругу, копируя на экран только видимый кусок."""
        w, h = im.get_size()
        if w <= 0 or h <= 0:
            return
        first = min(w - int(off) % w, WIDTH)          # сколько берём до конца файла
        self.screen.blit(im, (0, y), (int(off) % w, 0, first, h))
        x = first
        while x < WIDTH:                                # дальше — снова с начала файла
            part = min(w, WIDTH - x)
            self.screen.blit(im, (x, y), (0, 0, part, h))
            x += part