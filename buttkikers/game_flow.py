# -*- coding: utf-8 -*-
"""Часть Game: рестарт, переходы, заставка уровня, музыка."""
import os
import random
import subprocess
import sys

import pygame

from .settings import *  # noqa: F401,F403

from .entities import Player



class GameFlow:
    """Ход партии: рестарт, переходы, заставка уровня, музыка, старт раунда.

    Здесь вся «режиссура» игры: перезапуск процесса, сброс партии, мигание и
    вайп между экранами, затемнение/проявление заставки уровня с её текстом,
    громкость музыки (в меню своя, в игре другая) и запуск самого раунда.
    """

    def restart_script(self):
        """Полный рестарт: запускает игру заново в отдельном процессе без окна консоли.

        Из исходника — это pythonw.exe + сам скрипт. Из собранного exe — просто запуск
        самого exe (внутри PyInstaller уже всё умеет, второй экземпляр поднимается сам).
        """
        if getattr(sys, "frozen", False):
            subprocess.Popen([sys.executable], cwd=BASE_DIR)
        else:
            py = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
            if not os.path.exists(py):
                py = sys.executable
            subprocess.Popen([py, os.path.join(BASE_DIR, "buttkikers_united.py")], cwd=BASE_DIR)
        pygame.quit()
        sys.exit()


    def reset(self, players=None):
        """Сброс партии: персонажи, камера, счёт, враги, слои параллакса."""
        print("[DEBUG] reset called")
        if players is None:
            players = getattr(self, "num_players", 1)
        self.num_players = players
        self.players = [Player(i, players) for i in range(players)]
        for pl in self.players:
            pl.game = self            # ссылка на игру: из Fighter играем SFX персонажа
        self.frame = 0
        self.cam = 0
        self.state = "title"           # состояния: title / play / win / lose
        self.score = 0
        self.enemies = []
        # Точки появления врагов по мере продвижения (включённые только если НЕ NO_ENEMIES).
        # Видов и уровней нет — все враги одинаковые, поэтому в точке только X.
        self.spawn_points = [600, 950, 1500, 1900, 2400, 2900,
                             3100, 3700, 4200, 5000]
        self.spawn_idx = 0
        self.win_t = 0                 # таймер экрана победы
        self.lose_t = 0                # таймер экрана поражения
        self.mode_sel = 0              # выбранный пункт в меню (1/2 игрока)
        # Панель информации на старте партии выключена и убрана вниз. Пока идёт переход,
        # заставка уровня и проявление, её нет на экране. Включает её start_round() —
        # с hud_anim = 0, и оттуда она выезжает снизу вверх один раз. Без этого сброса
        # панель оставалась бы видимой (hud_anim = 1) от прошлого раунда, а потом
        # start_round() дёргал её вниз и она показывалась снизу вверх второй раз.
        self.hud_on = False
        self.hud_anim = 0.0
        self.load_parallax(force=False)   # слои уже загружены — берём из кеша


    def make_wipe_order(self):
        """Порядок пиксельных ячеек для диагонального вайпа: по диагонали, с разбросом."""
        cells = []
        cols = (WIDTH + FADE_PIXEL - 1) // FADE_PIXEL
        rows = (HEIGHT + FADE_PIXEL - 1) // FADE_PIXEL
        for cy in range(rows):
            for cx in range(cols):
                cells.append((cx + cy + random.random() * 0.9, cx, cy))
        cells.sort()
        return [(cx * FADE_PIXEL, cy * FADE_PIXEL) for _, cx, cy in cells]


    def start_transition(self, players):
        """Запускает переход к партии (режим выбирает TRANSITION)."""
        if TRANSITION == "wipe" and self.trans_order_mode != "wipe":
            self.trans_order = self.make_wipe_order()
            self.trans_order_mode = "wipe"
        self.trans_players = players
        self.trans_t = 0
        self.music_off = True          # музыка плавно стихает на переходе
        self.music_paused = False
        self.trans_done = 0
        self.trans_started = False
        self.trans_active = True
        self.trans_overlay.fill((0, 0, 0, 0))
        # Панель информации убираем сразу на старте перехода, а не в reset(): reset()
        # случается позже (экран уже закрылся), и до него панель от прошлого раунда
        # ещё стояла бы на месте. Теперь её нет с первого кадра перехода, и включает
        # её start_round() на первом кадре игры — панель выезжает снизу вверх один раз.
        self.hud_on = False
        self.hud_anim = 0.0


    def start_level_intro(self):
        """Экран погас — показываем заставку уровня: пауза, появление, показ, затухание."""
        self.state = "intro"
        self.intro_t = INTRO_TIME
        self.trans_paused = True
        print(f"[DEBUG] заставка: чёрный {INTRO_BLACK_TIME} + переход {INTRO_FADE_FRAMES} "
              f"({INTRO_FADE_STEPS} такт(ов) по {INTRO_FADE_TICK} кадр) + показ "
              f"{INTRO_SHOW_TIME} + затухание {INTRO_FADE_FRAMES} = {INTRO_TIME} кадров")


    def interscreen_text_image(self):
        """Слой ПОВЕРХ заставки — картинка text.(png|jpg|...) из папки заставки.

        Ищется так же, как основная заставка (сначала прямо в INTERSCREEN_DIR, потом в
        её подпапке с именем уровня), но по имени LEVEL_INTERSCREEN_TEXT. Масштабируется
        и кэшируется так же. Возвращает None, если файла нет — тогда рисуется одна
        заставка без текста поверх.
        """
        if self.interscreen_text_loaded:
            return self.interscreen_text_img
        self.interscreen_text_loaded = True
        name = LEVEL_INTERSCREEN_TEXT
        if not INTERSCREEN_DIR or not name:
            return None
        path = self.find_interscreen_file(name)
        if path is None:
            return None
        try:
            im = self.load_interscreen_img(path)
        except pygame.error as e:
            print(f"[DEBUG] слой текста заставки не читается: {path} ({e})")
            return None
        self.interscreen_text_img = im
        print(f"[DEBUG] слой текста заставки: {os.path.basename(path)} — "
              f"{im.get_width()}x{im.get_height()}")
        return im


    def find_interscreen_file(self, name):
        """Путь к файлу <name>.(jpg|png|bmp|...) в INTERSCREEN_DIR или в его подпапке
        <LEVEL_INTERSCREEN>/<name>. None, если такого файла нет."""
        base = BASE_DIR
        root = os.path.join(base, *INTERSCREEN_DIR.replace("\\", "/").split("/"))
        for folder in (root, os.path.join(root, LEVEL_INTERSCREEN)):
            if not os.path.isdir(folder):
                continue
            for fn in sorted(os.listdir(folder)):
                stem, ext = os.path.splitext(fn)
                if stem.lower() == name.lower() and ext.lower() in (".jpg", ".jpeg", ".png", ".bmp"):
                    return os.path.join(folder, fn)
        return None


    @staticmethod
    def load_interscreen_img(path):
        """Читает картинку заставки и вписывает её в окно: масштаб по меньшей стороне,
        не увеличивая (коэффициент не больше 1.0). Пропорции сохраняются."""
        im = pygame.image.load(path)
        im = im.convert_alpha() if im.get_flags() & pygame.SRCALPHA else im.convert()
        k = min(WIDTH / im.get_width(), HEIGHT / im.get_height(), 1.0)
        if k < 1.0:
            im = pygame.transform.smoothscale(
                im, (max(1, int(im.get_width() * k)), max(1, int(im.get_height() * k))))
        return im


    def interscreen_image(self):
        """Заставка уровня: картинка с именем уровня из INTERSCREEN_DIR, пропорции сохраняются.

        Ищется файл <LEVEL_INTERSCREEN>.(jpg|png|bmp|...) — сначала прямо в папке
        screen/intersceen, потом в её подпапке с таким же именем. Масштабируется по меньшей
        стороне так, чтобы целиком влезла в окно, и центрируется. Кэшируется: грузим один раз.
        """
        if self.interscreen_loaded:
            return self.interscreen_img
        self.interscreen_loaded = True
        name = LEVEL_INTERSCREEN
        if not INTERSCREEN_DIR or not name:
            return None
        path = self.find_interscreen_file(name)
        if path is None:
            print(f"[DEBUG] заставка уровня «{name}» не найдена в {INTERSCREEN_DIR}")
            return None
        try:
            im = self.load_interscreen_img(path)
        except pygame.error as e:
            print(f"[DEBUG] заставка не читается: {path} ({e})")
            return None
        self.interscreen_img = im
        print(f"[DEBUG] заставка уровня: {os.path.basename(path)} — "
              f"{im.get_width()}x{im.get_height()}")
        return im


    def skip_intro(self, src=""):
        """Пропуск заставки уровня: сразу к затуханию.

        Значение intro_t = INTRO_FADE_FRAMES — это ровно начало фазы затухания, то есть
        пропускаются чёрный экран, появление картинки и её показ. Если затухание уже
        идёт (intro_t <= INTRO_FADE_FRAMES), ничего не трогаем — иначе второй нажим
        назад по времени откатил бы переход на показ картинки.
        """
        if self.intro_t > INTRO_FADE_FRAMES:
            self.intro_t = INTRO_FADE_FRAMES
            print(f"[DEBUG] {src} на заставке — переход к затуханию, intro_t={self.intro_t}")


    def intro_alpha(self):
        """Прозрачность заставки уровня для текущего кадра: 0 — чёрный экран, 255 — картинка."""
        return self.intro_alpha_for(self.intro_t)


    def intro_alpha_for(self, intro_t):
        """Прозрачность по схеме чёрный экран -> появление -> показ -> затухание.

        Считает фазы от intro_t (кадров до конца заставки) тем же способом, что и раньше:
        INTRO_BLACK_TIME чёрного экрана, появление и затухание по INTRO_FADE_FRAMES
        разбиты на INTRO_FADE_STEPS тактов по INTRO_FADE_TICK кадров — внутри такта альфа
        не меняется, поэтому переход дискретный. 0 или 1 такт — плавное затухание.
        """
        elapsed = INTRO_TIME - max(0, intro_t)
        fade = INTRO_FADE_FRAMES
        if elapsed < INTRO_BLACK_TIME:
            return 0
        t = elapsed - INTRO_BLACK_TIME
        if t < fade:                                    # появление
            return min(255, (t + 1) * 255 // fade) if INTRO_FADE_STEPS <= 1 else \
                min(255, (t // INTRO_FADE_TICK + 1) * 255 // INTRO_FADE_STEPS)
        t -= fade
        if t < INTRO_SHOW_TIME:                         # картинка видна целиком
            return 255
        t -= INTRO_SHOW_TIME
        if t < fade:                                    # затухание теми же ступенями
            return max(0, 255 - (t + 1) * 255 // fade) if INTRO_FADE_STEPS <= 1 else \
                max(0, 255 - (t // INTRO_FADE_TICK + 1) * 255 // INTRO_FADE_STEPS)
        return 0


    def intro_text_alpha(self):
        """Прозрачность слоя текста — по СВОЕМУ ритму, отдельно от заставки.

        Текст появляется позже и держится дольше: INTRO_TEXT_DELAY кадров после начала
        появления заставки, затем своё появление, своя пауза и своё затухание.
        Всё считается от фактического числа кадров с начала интро (не от intro_t),
        поэтому текст гарантированно доигрывает свой затухание даже если базовый таймер
        уходит в минус.
        """
        elapsed = INTRO_TIME - self.intro_t   # кадров с начала интро (intro_t может быть < 0)
        if elapsed < INTRO_TEXT_DELAY:                   # текст ещё не начал появляться
            return 0
        t = elapsed - INTRO_TEXT_DELAY
        fade = max(1, INTRO_TEXT_FADE)
        if t < fade:                                     # своё появление
            return min(255, (t + 1) * 255 // fade)
        t -= fade
        if t < INTRO_TEXT_SHOW_TIME:                     # текст держится на экране
            return 255
        t -= INTRO_TEXT_SHOW_TIME
        if t < fade:                                     # своё затухание
            return max(0, 255 - (t + 1) * 255 // fade)
        return 0


    def draw_level_intro(self):
        """Заставка уровня: чёрный экран -> дискретное появление -> показ -> дискретное затухание.

        Сама картинка берётся из screen/intersceen, а если её нет — рисуется чёрный экран
        с названием уровня (такты применяются к нему так же).
        """
        self.screen.fill(BLACK)
        alpha = self.intro_alpha()
        if alpha <= 0:                 # пауза перед показом — просто чёрный экран
            return
        img = self.interscreen_image()
        if img is None:
            # Заставки нет — рисуем чёрный экран с названием уровня (если уже пора)
            if alpha > 0:
                num = self.pixel_font_ru.render(LEVEL_NUM, True, (170, 170, 180))
                name = self.pixel_font_ru.render(LEVEL_NAME, True, YELLOW)
                name = pygame.transform.scale(name, (name.get_width() * 2, name.get_height() * 2))
                num.set_alpha(alpha)
                name.set_alpha(alpha)
                self.screen.blit(num, (WIDTH // 2 - num.get_width() // 2, HEIGHT // 2 - 100))
                self.screen.blit(name, (WIDTH // 2 - name.get_width() // 2, HEIGHT // 2 - 30))
            return
        frame = img
        if alpha < 255:                # проявление/затухание — рисуем копию с альфой
            frame = img.copy()
            frame.set_alpha(alpha)
        self.screen.blit(frame, ((WIDTH - frame.get_width()) // 2,
                                 (HEIGHT - frame.get_height()) // 2))
        # Слой с текстом — ПОВЕРХ заставки и по СВОЕМУ ритму (intro_text_alpha):
        # своя задержка, своё появление, своя пауза и своё затухание. Рисуется всегда,
        # даже если основной картинки нет — слой самодостаточный.
        text_img = self.interscreen_text_image()
        if text_img is not None:
            talpha = self.intro_text_alpha()
            if talpha > 0:
                tframe = text_img
                if talpha < 255:
                    tframe = text_img.copy()
                    tframe.set_alpha(talpha)
                self.screen.blit(tframe, ((WIDTH - tframe.get_width()) // 2,
                                          (HEIGHT - tframe.get_height()) // 2))


    def toggle_music_pause(self):
        """Клавиша P — пауза/продолжение музыки в игре (громкость уходит плавно)."""
        if not self.music_ok or self.music_off:
            return
        self.music_paused = not self.music_paused
        print(f"[DEBUG] music paused={self.music_paused}")


    def update_music(self):
        """Музыка каждый кадр: плавное затухание/возврат громкости, пауза по P, перезапуск трека."""
        self.update_level_music()
        if not self.music_ok:
            return
        if self.level_music_ok and self.level_music.get_num_channels() > 0:
            pygame.mixer.music.stop()                  # на уровне играет свой трек — меню молчит
            return
        vol = pygame.mixer.music.get_volume()
        target = MUSIC_VOL if SOUND_ON else 0.0  # SOUND_ON = False держит громкость на нуле
        quiet = self.music_off or self.music_paused
        if vol > 0.001 and quiet:                  # плавно стихаем
            pygame.mixer.music.set_volume(max(0.0, vol - MUSIC_FADE_STEP))
        elif vol < target - 0.001 and not quiet:    # плавно возвращаем
            pygame.mixer.music.set_volume(min(target, vol + MUSIC_FADE_STEP))
        if self.music_paused and not self.music_really_paused and vol <= 0.001 and pygame.mixer.music.get_busy():
            pygame.mixer.music.pause()             # совсем стихло — встаём на паузу
            self.music_really_paused = True
        elif not self.music_paused and self.music_really_paused:
            pygame.mixer.music.unpause()           # снятие паузы — с того же места
            self.music_really_paused = False
        elif self.music_off and vol <= 0.001 and pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()              # дозвучали в тишину — стоп
        elif not quiet and not pygame.mixer.music.get_busy():
            pygame.mixer.music.play(-1)            # трек закончился — играем заново


    def update_level_music(self):
        """Трек уровня: играет только в партии (state == 'play'), в меню — глушится и молчит."""
        if not self.level_music_ok:
            return
        snd = self.level_music
        target = LEVEL_MUSIC_VOL if SOUND_ON else 0.0
        playing = self.state == "play" and not self.music_paused
        if playing:
            if snd.get_num_channels() == 0:            # трек начался — с тишины
                snd.set_volume(0.0)
                snd.play(loops=-1)
            vol = snd.get_volume()
            if vol < target - 0.001:                  # плавно появляется, как в меню
                snd.set_volume(min(target, vol + MUSIC_FADE_STEP))
        elif snd.get_num_channels() > 0:
            snd.set_volume(0.0)                       # на паузе/в меню — глушим
            snd.stop()


    def start_round(self):
        """Партия началась: музыка снова идёт (громкость плавно возвращается к 1.0)."""
        self.state = "play"
        self.music_off = False
        self.music_paused = False
        self.music_really_paused = False
        # Каждый игрок начинает раунд кувырком из-за левого края кадра: сдвигается
        # назад за границу и выкатывается на экран. entry_roll держит камеру на месте,
        # пока перекат не кончился (см. game_loop.update).
        for pl in self.players:
            pl.start_entry_roll()
        if HUD_ON_LEVEL_START:
            # Панель подсказок включается здесь — на первом кадре игры. В reset() она
            # уже выключена и убрана вниз, поэтому на экране её до этого момента нет,
            # и здесь она выезжает снизу вверх ровно один раз.
            self.hud_on = True
            self.hud_anim = 0.0


    def start_level_reveal(self):
        """После заставки уровень проявляется из темноты (диагональным вайпом)."""
        self.state = "reveal"
        self.reveal_t = 0
        self.reveal_done = 0
        self.reveal_surface.fill((0, 0, 0, 255))   # первый кадр проявления — сразу темно
        # Входной кувырок начинается ЗДЕСЬ, а не в start_round(): проявление идёт
        # REVEAL_TIME кадров, и в них персонаж рисуется стоящим на кадре. Если ждать
        # конца проявления, он сначала стоит, потом прыгает за край и выкатывается.
        # Теперь он уезжает за левый край сразу и на всём проявлении уже катится.
        for pl in self.players:
            pl.start_entry_roll()


    def update_reveal(self):
        """Проявление уровня: темнота уходит диагональной волной (вайп)."""
        self.reveal_t += 1
        if self.trans_order is None or self.trans_order_mode != "wipe":
            self.trans_order = self.make_wipe_order()
            self.trans_order_mode = "wipe"
        n = len(self.trans_order)
        target = int(self.reveal_t * n / max(1, REVEAL_TIME))
        for i in range(self.reveal_done, target):
            x, y = self.trans_order[i]
            self.reveal_surface.fill((0, 0, 0, 0), (x, y, FADE_PIXEL, FADE_PIXEL))
        self.reveal_done = target
        if self.reveal_t >= REVEAL_TIME:      # темнота ушла — играем
            self.reveal_surface.fill((0, 0, 0, 0))
            self.start_round()


    def update_blink(self):
        """Мигание перед стартом: картинка то появляется, то пропадает, каждый раз тусклее."""
        cycle, phase = divmod(self.trans_t, BLINK_CYCLE)
        dim = min(255, cycle * BLINK_STEP)
        dark = phase < BLINK_CYCLE // 2                  # половину цикла экран полностью чёрный
        self.trans_overlay.fill((0, 0, 0, 255 if dark else dim))
        if dim >= 255:                                   # экран ушёл в темноту — показываем заставку
            self.trans_active = False
            self.start_level_intro()
            print(f"[DEBUG] Blink done, state={self.state}")


    def update_transition(self):
        """Продвигает переход на один кадр; партия включается под закрытием экрана."""
        self.trans_t += 1
        if TRANSITION == "blink":
            self.update_blink()
            return
        n = len(self.trans_order)
        half = max(1, TRANS_TIME // 2)
        if self.trans_t <= half:                      # закрываем экран (вайп)
            target = int(self.trans_t / half * n)
            for i in range(self.trans_done, target):
                x, y = self.trans_order[i]
                self.trans_overlay.fill(BLACK, (x, y, FADE_PIXEL, FADE_PIXEL))
            self.trans_done = target
            if not self.trans_started:
                self.trans_started = True
                self.reset(self.trans_players)
                self.start_level_intro()   # экран закрыт — показываем заставку уровня
        else:                                          # открываем, показывая уровень
            target = int((self.trans_t - half) / (TRANS_TIME - half) * n)
            for i in range(self.trans_done, target):
                x, y = self.trans_order[i]
                self.trans_overlay.fill((0, 0, 0, 0), (x, y, FADE_PIXEL, FADE_PIXEL))
            self.trans_done = target
            if self.trans_t >= TRANS_TIME:
                self.trans_active = False


    def draw_transition(self):
        """Поверх экрана — эффект перехода: мигание или диагональный вайп."""
        if self.state == "reveal":         # уровень проявляется из темноты
            self.screen.blit(self.reveal_surface, (0, 0))
            return
        if not self.trans_active or self.trans_paused:
            return
        self.screen.blit(self.trans_overlay, (0, 0))