# -*- coding: utf-8 -*-
"""Часть Game: загрузка ресурсов и создание окна."""
import os


import pygame

from . import settings
from .settings import *  # noqa: F401,F403
from .anim import attack_duration, jump_duration
from .audio import find_sfx, find_sfx_all

from .gamepad import init_gamepads


class GameLoad:
    """Старт игры и загрузка всего: анимации бойца, слои параллакса, пол, звуки, шрифты.

    Здесь же живёт __init__: он создаёт окно и затем вызывает reset().
    Число кадров в каждой загруженной анимации кладётся в settings (settings.RUN_ANIM_N и
    подобные), чтобы остальные модули читали реальные значения.
    """

    def __init__(self):
        pygame.init()
        self.pad_nav_cd = 0           # кадры до следующего пункта меню при удержании стика
        self.pad_lt_held = False       # левый триггер был нажат в прошлом кадре (фронт)
        self.pad_lt_cd = 0             # кадры до следующего переключения изоляции
        self.pad_check_t = 0
        self.pad_missed = 0
        self.pad_reopen_t = 0           # счётчик перепроверки геймпадов (PAD_CHECK_FRAMES)
        self.pad_connected = False     # геймпад подключён: панель показывает управление геймпадом,
                                 # иначе — управление с клавиатуры
        pads = init_gamepads()
        if pads:
            for i, js in enumerate(pads):
                print(f"[DEBUG] геймпад P{i + 1}: {js.get_name()}")
            self.pad_connected = True
        elif GAMEPAD_ON:
            print("[DEBUG] геймпад не найден — играем с клавиатуры")
        self.audio_ok = False          # микшер звука инициализирован
        if MUSIC_ON or SFX_ON:
            try:
                pygame.mixer.init()
                self.audio_ok = True
            except pygame.error:
                self.audio_ok = False
        self.music_ok = False          # фоновый трек загружен
        self.music_off = False         # музыка заглушена на время перехода/заставки
        self.music_paused = False      # пауза музыки по клавише P
        self.music_really_paused = False   # микшер реально стоит на паузе (громкость уже 0)
        self.music_name = ""           # имя играющего трека ("" — уровень ещё не начинал)
        if self.audio_ok and MUSIC_ON:
            try:
                pygame.mixer.music.load(os.path.join(BASE_DIR,
                                                     "mus", MUSIC_FILE))
                pygame.mixer.music.set_volume(MUSIC_VOL if SOUND_ON else 0.0)
                self.music_ok = True
            except pygame.error:
                self.music_ok = False
        self.level_music_ok = False    # трек уровня загружен
        if self.audio_ok and MUSIC_ON and LEVEL_MUSIC:
            path = os.path.join(BASE_DIR,
                                *LEVEL_MUSIC.replace("\\", "/").split("/"))
            if os.path.exists(path):
                try:
                    self.level_music = pygame.mixer.Sound(path)
                    self.level_music.set_volume(LEVEL_MUSIC_VOL if SOUND_ON else 0.0)
                    self.level_music_ok = True
                except pygame.error:
                    self.level_music_ok = False
        self.sfx = {}
        self.sfx_queue = []            # отложенные звуки персонажа: [кадров_осталось, имя]
        self.sfx_last = {}             # индекс варианта, который только что прозвучал (для случайного выбора)
        if self.audio_ok and SFX_ON:
            for key, fn, word in (("start", SFX_START, ""),
                                  ("menu", SFX_MENU, SFX_MENU_KEY),
                                  ("step", SFX_FOOTSTEP, SFX_FOOTSTEP_KEY)):
                sfx_path = find_sfx(fn, word)
                if not sfx_path:
                    print(f"[SFX] нет файла: {key} — {fn}")
                    continue
                try:
                    self.sfx[key] = pygame.mixer.Sound(sfx_path)
                    print(f"[SFX] {key}: {os.path.basename(sfx_path)}")
                except pygame.error:
                    print(f"[SFX] не читается: {sfx_path}")
            if "step" in self.sfx:
                self.sfx["step"].set_volume(SFX_FOOTSTEP_VOL)   # громкость шагов — в настройках
            if "start" in self.sfx:
                self.sfx["start"].set_volume(SFX_START_VOL)   # нажатие START — тише
            if "menu" in self.sfx:
                self.sfx["menu"].set_volume(SFX_MENU_VOL)     # выбор в меню — своя громкость
            # Звуки персонажа (sounds/char): прыжок и удары. Ключ в CHAR_SFX — действие,
            # файл ищется по имени анимации (сильная нога -> mma), плюс запасной поиск
            # по слову в имени, чтобы файл можно было переименовать.
            for key, fn in CHAR_SFX.items():
                if not fn:
                    continue
                sfx_path = find_sfx(fn, os.path.splitext(fn)[0], CHAR_SOUND_DIR)
                if not sfx_path:
                    print(f"[SFX] нет звука персонажа: {key} — {fn}")
                    continue
                try:
                    snd = pygame.mixer.Sound(sfx_path)
                    snd.set_volume(CHAR_SFX_VOL)
                    self.sfx[key] = snd
                    print(f"[SFX] {key}: {os.path.basename(sfx_path)} ({CHAR_SOUND_DIR})")
                except pygame.error:
                    print(f"[SFX] не читается: {sfx_path}")
            # Действия с несколькими вариантами: подбираем ВСЕ файлы по префиксу
            # (jump -> jump1, jump2, ...) и храним списком. play_sfx выбирает из списка
            # случайный, поэтому добавил новый файл — вариантов станет больше.
            # Файлы из CHAR_SFX (например jumpALT.mp3) исключаем: они привязаны к своему
            # действию, хотя имя и начинается с того же префикса.
            for key, prefix in CHAR_SFX_RANDOM.items():
                paths = find_sfx_all(prefix, CHAR_SOUND_DIR, CHAR_SFX.values())
                variants = []
                for path in paths:
                    try:
                        snd = pygame.mixer.Sound(path)
                        snd.set_volume(CHAR_SFX_VOL)
                        variants.append(snd)
                    except pygame.error:
                        print(f"[SFX] не читается: {path}")
                if not variants:
                    print(f"[SFX] нет звуков персонажа: {key} — файлы {prefix}* в {CHAR_SOUND_DIR}")
                    continue
                self.sfx[key] = variants
                names = ", ".join(os.path.basename(p) for p in paths)
                print(f"[SFX] {key}: {len(variants)} варианта(ов) наугад — {names}")
            # Своя громкость для отдельных звуков (качение, доп. звук прыжка) —
            # общая CHAR_SFX_VOL им не применяется. Список — в CHAR_SFX_VOL_OWN.
            for key, vol in CHAR_SFX_VOL_OWN.items():
                if key in self.sfx:
                    self.sfx[key].set_volume(vol)
                    print(f"[SFX] {key}: своя громкость {vol}")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("ButtKIkers United — BEAT-EM-UP")
        self.clock = pygame.time.Clock()
        self.font_big = pygame.font.SysFont("arial", 50)
        self.font_m = pygame.font.SysFont("arial", 22)
        self.font_s = pygame.font.SysFont("arial", 15)
        # Пиксельный шрифт для заголовков меню (англ.)
        self.pixel_font = pygame.font.Font(
            os.path.join(BASE_DIR, "fonts", "PressStart2P.ttf"), 20)
        # Шрифт с поддержкой кириллицы для меню
        self.pixel_font_ru = pygame.font.Font(
            os.path.join(BASE_DIR, "fonts", "Tiny5.ttf"), 32)
        # Пиксельный шрифт панели подсказок по Z: тот же Tiny5 (кириллица), но
        # своим кеглем — панель читается крупно и в стиле остальных надписей
        self.font_panel = pygame.font.Font(
            os.path.join(BASE_DIR, "fonts", PANEL_FONT_FILE), PANEL_FONT_SIZE)
        # Кэш полупрозрачных полос панели по высоте (см. GameLoop.panel_band)
        self.panel_bands = {}
        # Заставка титульного экрана
        try:
            img = pygame.image.load(os.path.join(BASE_DIR, "screen", "6fin.png")).convert_alpha()
        except pygame.error:
            img = None
        self.title_img = img
        # Заставка уровня из screen/intersceen грузится один раз и масштабируется под окно.
        self.interscreen_img = None
        self.interscreen_loaded = False
        # Слой с текстом поверх заставки (text.png) — тоже грузится один раз
        self.interscreen_text_img = None
        self.interscreen_text_loaded = False
        # Стрелка выбора режима в меню
        base = BASE_DIR
        # Спрайт бега: первый анимированный .png из папки RUN_ALT_DIR (кроме run.png).
        # Покадровые папки не читаем. Порядок задаёт числовой префикс имени.
        self.run_variants = []
        altdir = os.path.join(base, RUN_ALT_DIR)
        if os.path.isdir(altdir):
            entries = sorted(
                (self.prefix_order(name), name, os.path.join(altdir, name))
                for name in os.listdir(altdir)
                if name.lower().endswith(".png") and name.lower() != "run.png")
            for order, name, full in entries:
                frames = self.load_apng_frames(full)
                if frames:
                    self.run_variants.append((name, frames))
        if not self.run_variants:                      # запасной источник — run.png (APNG)
            frames = self.load_run_frames(base)
            if frames:
                self.run_variants.append(("run.png", frames))
        self.run_variants = [(n, self.trim_frames(f)) for n, f in self.run_variants]
        settings.RUN_ANIM_N = len(self.run_variants[0][1]) if self.run_variants else 0
        self.run_frames = self.run_variants[0][1] if self.run_variants else []
        # Анимация прыжка: первый анимированный .png из папки JUMP_DIR, тем же порядком.
        # Если папки нет или .png не анимированные — self.jump_frames пустой и в прыжке
        # рисуется спрайт бега, как раньше.
        self.jump_frames = []
        self.jump_name = ""
        if JUMP_DIR:
            jdir = os.path.join(base, *JUMP_DIR.replace("\\", "/").split("/"))
            if os.path.isdir(jdir):
                jentries = sorted(
                    (self.prefix_order(name), name, os.path.join(jdir, name))
                    for name in os.listdir(jdir) if name.lower().endswith(".png")
                )
                for order, name, full in jentries:
                    frames = self.trim_frames(self.load_apng_frames(full))
                    if frames:
                        self.jump_name, self.jump_frames = name, frames
                        break
        # Кадров в анимации знает только загрузка — сохраняем, чтобы прыжок мог
        # посчитать свою длительность (jump_duration).
        settings.JUMP_ANIM_N = len(self.jump_frames)
        # Анимация простоя: первый анимированный .png из папки IDLE_DIR, тем же порядком.
        # Если папки нет или .png не анимированные — self.idle_frames пустой и в покое
        # рисуется спрайт бега, как раньше.
        self.idle_frames = []
        self.idle_name = ""
        if IDLE_DIR:
            idir = os.path.join(base, *IDLE_DIR.replace("\\", "/").split("/"))
            if os.path.isdir(idir):
                ientries = sorted(
                    (self.prefix_order(name), name, os.path.join(idir, name))
                    for name in os.listdir(idir) if name.lower().endswith(".png")
                )
                for order, name, full in ientries:
                    frames = self.trim_frames(self.load_apng_frames(full))
                    if frames:
                        self.idle_name, self.idle_frames = name, frames
                        break
        if self.idle_frames:
            print(f"[DEBUG] idle: {self.idle_name} — {len(self.idle_frames)} кадров "
                  f"@ {IDLE_ANIM_FPS} fps")
        # Анимация приседа: первый анимированный .png из папки SIT_DIR, тем же порядком.
        # В sit.png кадры идут задом наперёд (сначала стоя, потом приседание), поэтому при
        # SIT_REVERSE разворачиваем их: 0 — стоя, последний — сел.
        self.sit_frames = []
        self.sit_name = ""
        if SIT_DIR:
            sdir = os.path.join(base, *SIT_DIR.replace("\\", "/").split("/"))
            if os.path.isdir(sdir):
                sentries = sorted(
                    (self.prefix_order(name), name, os.path.join(sdir, name))
                    for name in os.listdir(sdir) if name.lower().endswith(".png")
                )
                for order, name, full in sentries:
                    frames = self.trim_frames(self.load_apng_frames(full))
                    if frames:
                        self.sit_name, self.sit_frames = name, frames
                        break
        settings.SIT_ANIM_N = len(self.sit_frames)
        if SIT_REVERSE and self.sit_frames:
            self.sit_frames = self.sit_frames[::-1]
        if self.sit_frames:
            print(f"[DEBUG] присед: {self.sit_name} — {settings.SIT_ANIM_N} кадров "
                  f"@ {SIT_ANIM_FPS} fps"
                  + ("  (кадры развёрнуты: sit.png шёл задом наперёд)" if SIT_REVERSE else ""))
        # Анимация крадущейся ходьбы: первый анимированный .png из папки CRWALK_DIR.
        # Показываем ВСЕ кадры (без прореживания, как у ударов) и идём вдвое медленнее,
        # поэтому анимация проходится вдвое быстрее бега — иначе она «зависла» бы.
        self.crwalk_frames = []
        self.crwalk_name = ""
        if CRWALK_DIR:
            cdir = os.path.join(base, *CRWALK_DIR.replace("\\", "/").split("/"))
            if os.path.isdir(cdir):
                centries = sorted(
                    (self.prefix_order(name), name, os.path.join(cdir, name))
                    for name in os.listdir(cdir) if name.lower().endswith(".png")
                )
                for order, name, full in centries:
                    frames = self.trim_frames(self.load_apng_frames(full))
                    if frames:
                        self.crwalk_name, self.crwalk_frames = name, frames
                        break
        settings.CRWALK_ANIM_N = len(self.crwalk_frames)
        if self.crwalk_frames:
            print(f"[DEBUG] крадущаяся ходьба: {self.crwalk_name} — {settings.CRWALK_ANIM_N} кадров "
                  f"@ {CRWALK_ANIM_FPS} fps, скорость x{CRWALK_SPEED_MUL}")
        # Анимация переката: первый анимированный .png из папки ROLL_DIR.
        # Кадры показываются ВСЕ (без прореживания) и по своей частоте — это движение,
        # а не удар, поэтому ATTACK_FRAME_SKIP к нему не применяется.
        self.roll_frames = []
        self.roll_name = ""
        if ROLL_DIR:
            rdir = os.path.join(base, *ROLL_DIR.replace("\\", "/").split("/"))
            if os.path.isdir(rdir):
                rentries = sorted(
                    (self.prefix_order(name), name, os.path.join(rdir, name))
                    for name in os.listdir(rdir) if name.lower().endswith(".png")
                )
                for order, name, full in rentries:
                    frames = self.trim_frames(self.load_apng_frames(full))
                    if frames:
                        self.roll_name, self.roll_frames = name, frames
                        break
        settings.ROLL_ANIM_N = len(self.roll_frames)
        if self.roll_frames:
            print(f"[DEBUG] перекат: {self.roll_name} — {settings.ROLL_ANIM_N} кадров "
                  f"@ {ROLL_ANIM_FPS} fps, скорость x{ROLL_SPEED_MUL}")
        # Анимация удара рукой: первый анимированный .png из папки PUNCH_DIR, тем же порядком.
        # Длительность удара берётся из неё, чтобы кадры не прокручивались быстрее анимации.
        self.punch_frames = []
        self.punch_name = ""
        if PUNCH_DIR:
            pdir = os.path.join(base, *PUNCH_DIR.replace("\\", "/").split("/"))
            if os.path.isdir(pdir):
                pentries = sorted(
                    (self.prefix_order(name), name, os.path.join(pdir, name))
                    for name in os.listdir(pdir) if name.lower().endswith(".png")
                )
                for order, name, full in pentries:
                    # ATTACK_FRAME_SKIP выкидывает каждый N-й кадр (2 = каждый второй).
                    # Длительность удара считается по оставшимся кадрам, поэтому прореживание
                    # ровно в ATTACK_FRAME_SKIP раз ускоряет анимацию.
                    src = self.trim_frames(self.load_apng_frames(full))
                    frames = src[::ATTACK_FRAME_SKIP] if ATTACK_FRAME_SKIP > 1 else src
                    if frames:
                        self.punch_name, self.punch_frames = name, frames
                        punch_src = len(src)
                        break
        settings.PUNCH_ANIM_N = len(self.punch_frames)
        if self.punch_frames:
            print(f"[DEBUG] удар рукой: {self.punch_name} — {settings.PUNCH_ANIM_N} кадров "
                  f"из {punch_src} "
                  f"@ {ATTACK_ANIM_FPS} fps, длительность удара "
                  f"{attack_duration(settings.PUNCH_ANIM_N)} кадр "
                  f"({attack_duration(settings.PUNCH_ANIM_N) / FPS:.2f} с)")
        else:
            print("[DEBUG] удар рукой: анимация не найдена, длительность удара "
                  f"{PUNCH_FALLBACK} кадр")
        # Анимация сильного удара ногой: то же самое, но из папки MMA_DIR.
        self.mma_frames = []
        self.mma_name = ""
        if MMA_DIR:
            mdir = os.path.join(base, *MMA_DIR.replace("\\", "/").split("/"))
            if os.path.isdir(mdir):
                mentries = sorted(
                    (self.prefix_order(name), name, os.path.join(mdir, name))
                    for name in os.listdir(mdir) if name.lower().endswith(".png")
                )
                for order, name, full in mentries:
                    src = self.trim_frames(self.load_apng_frames(full))
                    frames = src[::ATTACK_FRAME_SKIP] if ATTACK_FRAME_SKIP > 1 else src
                    if frames:
                        self.mma_name, self.mma_frames = name, frames
                        mma_src = len(src)
                        break
        settings.MMA_ANIM_N = len(self.mma_frames)
        if self.mma_frames:
            print(f"[DEBUG] удар ногой (сильный): {self.mma_name} — {settings.MMA_ANIM_N} кадров "
                  f"из {mma_src} "
                  f"@ {ATTACK_ANIM_FPS} fps, длительность удара "
                  f"{attack_duration(settings.MMA_ANIM_N)} кадр "
                  f"({attack_duration(settings.MMA_ANIM_N) / FPS:.2f} с)")
        else:
            print("[DEBUG] удар ногой (сильный): анимация не найдена, длительность удара "
                  f"{KICK_FALLBACK} кадр")
        # Анимация обычного удара ногой: то же самое, но из папки KIK_DIR.
        self.kik_frames = []
        self.kik_name = ""
        if KIK_DIR:
            kdir = os.path.join(base, *KIK_DIR.replace("\\", "/").split("/"))
            if os.path.isdir(kdir):
                kentries = sorted(
                    (self.prefix_order(name), name, os.path.join(kdir, name))
                    for name in os.listdir(kdir) if name.lower().endswith(".png")
                )
                for order, name, full in kentries:
                    src = self.trim_frames(self.load_apng_frames(full))
                    frames = src[::ATTACK_FRAME_SKIP] if ATTACK_FRAME_SKIP > 1 else src
                    if frames:
                        self.kik_name, self.kik_frames = name, frames
                        kik_src = len(src)
                        break
        settings.KIK_ANIM_N = len(self.kik_frames)
        if self.kik_frames:
            print(f"[DEBUG] удар ногой (обычный): {self.kik_name} — {settings.KIK_ANIM_N} кадров "
                  f"из {kik_src} "
                  f"@ {ATTACK_ANIM_FPS} fps, длительность удара "
                  f"{attack_duration(settings.KIK_ANIM_N)} кадр "
                  f"({attack_duration(settings.KIK_ANIM_N) / FPS:.2f} с)")
        else:
            print("[DEBUG] удар ногой (обычный): анимация не найдена, длительность удара "
                  f"{KICK_FALLBACK} кадр")
        # Анимации ВРАГА из папки ENEMY_WALK_DIR. Каждая ищется ПО ИМЕНИ (ENEMY_ANIM_FILES),
        # а не «первый .png по алфавиту»: иначе punch.png, вставленный в папку, встал бы
        # перед walk.png и враг пошёл бы с анимацией удара. Имя файла настраивается в
        # settings.py, порядок файлов на диске значения не имеет.
        # Состояния без своего файла (kik, mma, jump) берутся из анимаций игрока — см. src
        # ниже. Если файла нет или кадров в нём нет, соответствующий список пустой, и
        # враг рисуется спрайтом игрока (как было раньше).
        self.enemy_walk_frames = []
        self.enemy_walk_name = ""
        self.enemy_frames = {}          # state -> кадры СВОЕЙ анимации врага (если есть)
        edir = ""
        if ENEMY_WALK_DIR:
            edir = os.path.join(base, *ENEMY_WALK_DIR.replace("\\", "/").split("/"))
        # Порядок по ENEMY_ANIM_FILES (состояния), в каждом — имя файла; если файла нет,
        # берётся первый одноимённый по префиксу (например "punch2.png" для "punch").
        eentries = []
        if os.path.isdir(edir):
            eentries = sorted((self.prefix_order(name), name, os.path.join(edir, name))
                              for name in os.listdir(edir) if name.lower().endswith(".png"))
        for state, fname in ENEMY_ANIM_FILES.items():
            stem = os.path.splitext(fname)[0]
            got = []
            for order, name, full in eentries:
                if os.path.splitext(name)[0].lower() == stem.lower():
                    got = self.trim_frames(self.load_apng_frames(full))
                    if got:
                        self.enemy_frames[state] = got
                        if state == "erun":
                            self.enemy_walk_name, self.enemy_walk_frames = name, got
                    break
            label = f"{state}: {fname}"
            print(f"[DEBUG] анимация врага {label} — "
                  + (f"{len(got)} кадров" if got else "не найдена, спрайт игрока"))
        settings.ENEMY_WALK_ANIM_N = len(self.enemy_walk_frames)
        settings.ENEMY_DEATH_ANIM_N = len(self.enemy_frames.get("death") or ())
        # Размер врага — по содержимому спрайта, а не по кадру. Кадр шире бойца почти
        # вдвое (walk.png: 236x170, боец 113x151), поэтому при масштабировании по кадру
        # враг выходил на экране меньше своего спрайта, а удары и прыжок меняли размер на
        # ходу. Множители ENEMY_STATE_FIT приводят каждое состояние врага к высоте ходьбы.
        # Заимствованные кадры игрока подставляются в src, свои — в enemy_frames.
        self.enemy_fill = {}
        if self.enemy_walk_frames:
            walk_fh, walk_fw = self.anim_fill(self.enemy_walk_frames)
            self.enemy_fill["erun"] = (walk_fh, walk_fw)
            # Множители считаются ТОЛЬКО по своим анимациям врага: спрайты игрока врагу
            # не подставляются, поэтому состояния без своего файла (kik, mma, jump) в
            # ENEMY_STATE_FIT не попадают — для них фита нет, а рисуется поза покоя.
            settings.ENEMY_STATE_FIT = {}
            for state, frames in self.enemy_frames.items():
                st_fh, st_fw = self.anim_fill(frames)
                # Высота приводится к высоте ходьбы, ширина — с тем же коэффициентом,
                # иначе пропорции бойца в ударе отличались бы от ходьбы.
                fit = walk_fh / st_fh if st_fh > 0 else 1.0
                self.enemy_fill[state] = (st_fh, st_fw)
                settings.ENEMY_STATE_FIT[state] = fit
            fit_txt = ", ".join(f"{k}={v:.2f}" for k, v in settings.ENEMY_STATE_FIT.items())
            print(f"[DEBUG] размер врага: заполнение кадра ходьбы {walk_fh:.0%} по высоте, "
                  f"{walk_fw:.0%} по ширине; подгонка кадров удара/прыжка: {fit_txt or '—'}")
        dur = jump_duration()
        spd = JUMP_LEN / dur if dur else 0
        print(f"[DEBUG] прыжок: длина {JUMP_LEN} px, анимация {JUMP_ANIM_FPS} fps -> "
              f"длительность {dur / FPS:.2f} с ({dur} кадр), "
              f"скорость {spd:.1f} px/кадр (ходьба {MOVE:.1f}"
              f"{', прыжок быстрее' if spd > MOVE else ', прыжок медленнее' if spd < MOVE else ''}), "
              f"кулдаун {JUMP_COOLDOWN:.2f} с"
              + (f", кадров в анимации {settings.JUMP_ANIM_N}" if settings.JUMP_ANIM_N else ", анимации нет"))
        spr_path = os.path.join(base, "sprites", "choose.png")
        self.choose_img = None
        if os.path.exists(spr_path):
            try:
                self.choose_img = pygame.image.load(spr_path).convert_alpha()
            except pygame.error:
                self.choose_img = None
        # Параллакс-фон: задний план переключается клавишей E, слои 1 и 2 всегда включены
        self.par_backs = []           # список (имя файла, картинка) задних слоёв
        self.par_back_name = ""       # название активного заднего слоя (подпись на экране)
        self.par2 = None              # слой 2 (полоса из PAR2_DIR), всегда рисуется
        self.lay0_img = None          # слой 0 (полоса из LAY0_DIR): рисуется последним, поверх всех
        self.parnew_img = None        # слой par NEW: рисуется поверх вообще всего, включая пол
        self.parnew_pad = 0           # верхний отступ полосы par NEW (для сдвигов из имён)
        self.floor_img = None         # пол уровня (активный вариант)
        self.floor_row = 0            # строка сплошной поверхности в картинке пола
        self.floor_name = ""          # имя варианта пола (fl1 / fl2 ...)
        self.floors = []              # варианты пола: (имя, полоса, строка поверхности)
        self.floor_idx = 0            # индекс активного варианта пола
        self.par_back_idx = 0         # индекс активного заднего слоя в par_backs
        self.back_scale = 1.0    # относительная подстройка масштаба клавишами +/- (1.0 = как задано именем)
        self.isolate = ISOLATE_ON     # режим изоляции фона (Q): видны фон, персонаж и пол
        self.hud_on = HUD_ON          # панель информации внизу (Z / Select — переключить)
        # hud_anim — насколько панель уже выехала снизу вверх: 0 = уехала совсем,
        # 1 = стоит на месте. Прокручивает update_hud_anim по настройке HUD_ANIM_FRAMES
        self.hud_anim = 0.0
        self.hud_h = HUD_H            # текущая высота панели (по числу строк)
        self.par_ok = False           # загрузились ли слои параллакса
        self.load_parallax()
        self.trans_active = False     # идёт ли переход к партии
        self.trans_t = 0              # кадры перехода
        self.trans_done = 0           # сколько ячеек уже обработано в режиме "wipe"
        self.trans_started = False    # партия уже запущена внутри перехода
        self.trans_players = 1        # сколько игроков запускаем после перехода
        self.trans_order = None       # порядок ячеек вайпа (создаётся при первом старте)
        self.trans_order_mode = None  # для какого режима построен trans_order
        self.trans_overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self.trans_overlay.fill((0, 0, 0, 0))
        self.trans_paused = False    # переход на паузе, пока показан экран уровня
        self.intro_t = 0             # кадров до конца заставки уровня
        self.reveal_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)  # проявление уровня
        self.reveal_surface.fill((0, 0, 0, 0))
        self.reveal_t = 0            # кадров проявления
        self.reveal_done = 0         # сколько ячеек уже открыто в режиме "wipe"
        self.reset()


    def load_run_frames(self, base):
        """Запасной источник анимации бега — только анимированный run.png (APNG через Pillow).
        Покадровые папки больше не читаются."""
        frames = []
        apng = os.path.join(base, *RUN_ALT_DIR.replace("\\", "/").split("/"), "run.png")
        if os.path.exists(apng):
            frames = self.load_apng_frames(apng)
        return frames


    @staticmethod
    def load_apng_frames(path):
        """Кадры из APNG через Pillow. Если по правому и нижнему краю идёт сплошная
        чёрная рамка в 1 px (артефакт исходника) — она срезается, как у run.png."""
        if not os.path.exists(path):
            return []
        try:
            from PIL import Image
            img = Image.open(path)
            cut = 0
            frames = []
            for i in range(getattr(img, "n_frames", 1)):
                img.seek(i)
                frame = img.convert("RGBA")
                if not i:
                    cut = 1 if GameLoad.has_black_border(frame) else 0
                if cut:
                    w, h = frame.size
                    frame = frame.crop((0, 0, max(1, w - cut), max(1, h - cut)))
                w, h = frame.size
                raw = frame.tobytes()
                frames.append(pygame.image.frombuffer(raw, (w, h), "RGBA").convert_alpha())
            return frames
        except Exception:
            return []


    @staticmethod
    def trim_frames(frames, px=2):
        """Срезает px пикселей со всех четырёх краёв каждого кадра (рамка-артефакт исходников)."""
        out = []
        for im in frames:
            w, h = im.get_size()
            if w <= 2 * px or h <= 2 * px:
                out.append(im)
                continue
            out.append(im.subsurface(pygame.Rect(px, px, w - 2 * px, h - 2 * px)).copy())
        return out


    @staticmethod
    def anim_fill(frames):
        """(доля высоты, доля ширины) кадра, занятая персонажем, 0..1.

        Считается по ОБЩЕМУ прямоугольнику всех кадров, а не по каждому отдельно: тогда
        взаимное положение персонажа внутри анимации (его качание, выпад вперёд) не
        меняется и соседние кадры не «прыгают». Один общий прямоугольник — это и есть
        размер спрайта по содержимому, без пустых прозрачных полей.

        Нужен, чтобы масштабировать по персонажу, а не по пустому кадру. У walk.png
        персонаж занимает 113x151 из 236x170, то есть по ширине меньше половины кадра:
        при масштабировании по кадру враг выходил на экране заметно меньше своего спрайта.
        Пустой список или пустые кадры — (1.0, 1.0), то есть масштаб как есть.
        """
        if not frames:
            return (1.0, 1.0)
        fw, fh = frames[0].get_size()
        union = None
        for im in frames:
            try:
                box = im.get_bounding_rect()   # непрозрачная часть Surface с альфой
            except pygame.error:
                continue
            if box.width <= 0 or box.height <= 0:
                continue
            union = box.copy() if union is None else union.union(box)
        if union is None or fw <= 0 or fh <= 0:
            return (1.0, 1.0)
        return (max(0.05, min(1.0, union.height / float(fh))),
                max(0.05, min(1.0, union.width / float(fw))))

    @staticmethod
    def has_black_border(im):
        """True — справа и снизу сплошная чёрная непрозрачная полоса в 1 px."""
        w, h = im.size
        if w < 3 or h < 3:
            return False
        px = im.load()
        for y in range(h):
            p = px[w - 1, y]
            if p[3] == 0 or max(p[:3]) > 12:
                return False
        for x in range(w):
            p = px[x, h - 1]
            if p[3] == 0 or max(p[:3]) > 12:
                return False
        return True


    @staticmethod
    def prefix_order(name):
        """Числовой префикс имени задаёт порядок (2_run -> 2, 4hi1 -> 4), без цифр — в конец."""
        head = name.split("_", 1)[0]
        digits = ""
        for ch in head:                           # ведущие цифры имени
            if ch.isdigit():
                digits += ch
            else:
                break
        return (int(digits) if digits else 9999, name)


    def load_parallax(self, force=True):
        """Загружает параллакс: задние планы из BACK_DIR (клавиша E) и слой 2 из PAR2_DIR.
        Без force слои не перечитываются — используется уже загруженный кеш."""
        if not force and self.par_ok:
            return
        base = BASE_DIR
        self.par_backs = []
        self.par2 = None
        self.par_ok = False
        # Задние планы: картинки — статичные слои, папки — анимации.
        # Числовой префикс в имени (1_ 2_ 3_...) задаёт порядок появления при смене фонов.
        backdir = os.path.join(base, *BACK_DIR.replace("\\", "/").split("/"))
        self.anim_cache = {}
        if BACK_ON and os.path.isdir(backdir):
            entries = []
            for name in os.listdir(backdir):
                p = os.path.join(backdir, name)
                if os.path.isdir(p):
                    entries.append((self.back_order(name), name, "anim", p))
                elif name.lower().endswith((".png", ".jpg", ".jpeg")):
                    entries.append((self.back_order(name), name, "static", p))
            entries.sort(key=lambda e: e[:2])
            for order, fn, kind, p in entries:
                # Собственный масштаб фона из суффикса имени ("..._80" -> 0.8);
                # без суффикса — None, тогда работает общий BACK_SCALE.
                own = self.back_scale_of(fn)
                if kind == "anim":
                    self.par_backs.append((fn, kind, p, own))   # кадры читаем лениво
                    continue
                try:
                    pic = pygame.image.load(p)
                    pic = self.mirror_glue(pic)          # зеркалим и склеиваем для бесшовного тайлинга
                    self.par_backs.append((fn, kind, pic.convert(), own))
                except pygame.error:
                    pass
        # Слой 2 (par 2): полоса из картинок папки PAR2_DIR по тем же правилам, что и слой 1.
        p2dir = os.path.join(base, *PAR2_DIR.replace("\\", "/").split("/"))
        self.par2, self.par2_pad = self.build_strip(p2dir, PAR2_H) \
            if PAR2_ON else (None, 0)
        self.load_trees()
        l0dir = os.path.join(base, *LAY0_DIR.replace("\\", "/").split("/"))
        self.lay0_img, self.lay0_pad = self.build_strip(l0dir, LAY0_H) \
            if LAY0_ON else (None, 0)
        # Слой par NEW: полоса по тем же правилам, рисуется поверх всех остальных.
        pndir = os.path.join(base, *PARNEW_DIR.replace("\\", "/").split("/"))
        self.parnew_img, self.parnew_pad = self.build_strip(
            pndir, PARNEW_H) if PARNEW_ON else (None, 0)
        self.load_floors()
        if self.par_backs:
            self.par_back_idx %= len(self.par_backs)
            self.par_back_name = self.par_backs[self.par_back_idx][0]
        else:
            self.par_back_name = ""
        if self.par_backs or self.par2 is not None:
            self.par_ok = True


    @staticmethod
    def floor_surface_row(im):
        """Строка, на которой стоит персонаж: верх сплошной поверхности.
        У картинок с прозрачностью (сверху трава) ищем первую плотную строку,
        у непрозрачных — просто верхний край."""
        w, h = im.get_size()
        if not (im.get_flags() & pygame.SRCALPHA):
            return 0
        step = max(1, w // 64)
        for y in range(h):
            solid = sum(1 for x in range(0, w, step) if im.get_at((x, y))[3] > 200)
            if solid / float(len(range(0, w, step))) > 0.8:
                return y
        return 0


    def load_floor_variant(self, folder):
        """Вариант пола из папки: одна картинка — как есть, несколько — склеиваются
        по порядку (они чередуются друг за другом при прокрутке)."""
        imgs = []
        for fn in sorted(f for f in os.listdir(folder)
                         if f.lower().endswith((".png", ".jpg", ".jpeg"))):
            try:
                imgs.append(pygame.image.load(os.path.join(folder, fn)))
            except pygame.error:
                pass
        if not imgs:
            return None
        rows = [self.floor_surface_row(im) for im in imgs]
        if len(imgs) == 1:
            return (os.path.basename(folder), imgs[0].convert_alpha(), rows[0])
        top = min(rows)                       # выравниваем поверхности на одной линии
        overlap = FLOOR_OVERLAP.get(os.path.basename(folder), 0)
        overlap = max(0, min(overlap, min(im.get_width() for im in imgs) - 1))
        width = sum(im.get_width() for im in imgs) - overlap * (len(imgs) - 1)
        height = max(im.get_height() + top - r for im, r in zip(imgs, rows))
        strip = pygame.Surface((width, height), pygame.SRCALPHA)
        x = 0
        for im, r in zip(imgs, rows):
            strip.blit(im, (x, top - r))
            x += im.get_width() - overlap       # следующая картинка внахлёст на overlap
        return (os.path.basename(folder), strip.convert_alpha(), top)


    @staticmethod
    def build_strip(folder, height):
        """Склеивает полосу слоя из картинок и gap-файлов папки.
        Картинка (.png/.jpg): имя задаёт всё — <номер> — порядок (ведущие цифры, без номера
        в конец), последнее число после _ — сдвиг по вертикали относительно базовой линии
        слоя (2_100.png = второй, поднять на 100; 2_-50.png = опустить на 50).
        Gap: любой файл, который НЕ картинка, а в имени число — ширина прозрачного зазора:
        1_200 (порядок 1, зазор 200 px), 150 (зазор 150 px, в конец).
        Расширение у gap-файла любое (.txt, .gap, без расширения) — важно только имя.
        Полоса растёт вниз/вверх так, чтобы ни одна картинка не срезалась; поэтому
        возвращает (полоса, top_pad) — сколько строк сверху добавлено под сдвиги вверх.
        None, если папки нет, в ней ничего нечего рисовать или height не задан."""
        if not height or not os.path.isdir(folder):
            return None
        items = []
        for fn in os.listdir(folder):
            name = os.path.splitext(fn)[0]
            if os.path.splitext(fn)[1].lower() in (".png", ".jpg", ".jpeg"):
                items.append((GameLoad.strip_order(name), fn, GameLoad.strip_shift(name), 0))
            else:
                gap = GameLoad.gap_width(name)              # не картинка: число в имени = зазор
                if gap:
                    items.append((GameLoad.strip_order(name), fn, 0, gap))
        items.sort(key=lambda it: (it[0], it[1]))
        imgs = []
        for order, fn, shift, gap in items:
            if gap:                                    # gap-файл — прозрачное место в полосе
                imgs.append((None, 0, gap))
                continue
            try:
                im = pygame.image.load(os.path.join(folder, fn))
            except pygame.error:
                continue
            if im.get_height() <= 2:                   # вырожденная полоска-заглушка — не рисуем
                continue
            imgs.append((im, shift, 0))
        if not imgs:
            return None
        # Ширина полосы: сумма ширин картинок плюс все gap-зазоры между ними
        width = sum((im.get_width() if im is not None else 0) + gap for im, _, gap in imgs)
        # Базовая линия слоя — LAYERS_Y, верху полосы соответствует Y = LAYERS_Y - height.
        # Картинка со сдвигом s должна лечь на строку height - s от верха, поэтому под сдвиги
        # вверх нужен запас top_pad; вниз полоса просто дорастает. Так сдвиг виден, а края
        # картинок не срезаются (иначе blit молча срезал бы верх или низ).
        top_pad = max([0] + [s for im, s, _ in imgs if im is not None])
        need = max([height] + [top_pad - s + im.get_height()
                               for im, s, _ in imgs if im is not None])
        strip = pygame.Surface((width, need), pygame.SRCALPHA)
        x = 0
        for im, shift, gap in imgs:
            if im is not None:
                strip.blit(im, (x, top_pad - shift))   # верх картинок — на базовой линии слоя
                x += im.get_width()
            x += gap                                    # gap — пустое место, ничего не рисуем
        return strip.convert_alpha(), top_pad


    @staticmethod
    def strip_order(name):
        """Порядок элемента полосы по имени: ведущие цифры (1_200 -> 1, 4hi1 -> 4), без цифр — в конец."""
        digits = ""
        for ch in name:
            if ch.isdigit():
                digits += ch
            else:
                break
        return int(digits) if digits else 9999


    @staticmethod
    def strip_shift(name):
        """Сдвиг по вертикали из имени: последнее число после _ (4 -> 0, 2_20 -> 20, 1_-50 -> -50)."""
        nums = [p for p in name.split("_")[1:] if p.lstrip("-").isdigit()]
        return int(nums[-1]) if nums else 0


    @staticmethod
    def gap_width(name):
        """Ширина gap-зазора из имени не-картинки: последнее число после _ (1_200 -> 200),
        иначе всё имя, если оно число (150 -> 150). 0 — это не gap-файл."""
        parts = name.split("_")
        tail = parts[-1] if len(parts) > 1 else parts[0]
        if tail.isdigit():
            return int(tail) if int(tail) > 0 else 0
        return 0


    @staticmethod
    def layer_y(im, height, top_pad):
        """Y полосы на экране: низ полосы на LAYERS_Y - LAYERS_LIFT, верх на LAYERS_Y - LAYERS_LIFT - height."""
        return LAYERS_Y - LAYERS_LIFT - height - top_pad


    def load_trees(self):
        """Слой 1: полоса из картинок папки PAR1_DIR по общим правилам (см. build_strip)."""
        base = BASE_DIR
        folder = os.path.join(base, *PAR1_DIR.replace("\\", "/").split("/"))
        self.par1_img, self.par1_pad = self.build_strip(folder, PAR1_H) \
            if PAR1_ON else (None, 0)


    def load_floors(self):
        """Читаем варианты пола из папки FLOOR_DIR (каждая вложенная папка — один вариант)."""
        base = BASE_DIR
        levdir = os.path.join(base, *FLOOR_DIR.replace("\\", "/").split("/"))
        self.floors = []
        if FLOOR_ON and os.path.isdir(levdir):
            for name in sorted(d for d in os.listdir(levdir)
                               if d.lower().startswith("fl")
                               and os.path.isdir(os.path.join(levdir, d))):
                v = self.load_floor_variant(os.path.join(levdir, name))
                if v:
                    self.floors.append(v)
        self.set_floor(getattr(self, "floor_idx", 0))


    def set_floor(self, idx):
        """Вариант пола выбирается загрузкой (F больше не переключает). Уровень берётся из
        FLOOR_LEVEL (верх части ключа), None — авто: по верхней сплошной поверхности."""
        if not self.floors:
            self.floor_idx = 0
            self.floor_name, self.floor_img, self.floor_row = "", None, 0
            self.floor_y = CHARACTER_FLOOR_Y
            return
        self.floor_idx = idx % len(self.floors)
        self.floor_name, self.floor_img, self.floor_row = self.floors[self.floor_idx]
        level = FLOOR_LEVEL.get(self.floor_name, None)
        surface = CHARACTER_FLOOR_Y if level is None else level
        self.floor_y = surface - self.floor_row