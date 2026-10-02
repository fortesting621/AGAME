# BEAT-EM-UP «TOADS vs DRAGON»
# Скрипт игры на pygame. Запуск: launch.pyw (pythonw, без окна консоли)
# Управление:
#   P1: A/D — идти, W — прыжок, S — блок, J — кулак, K — нога
#   P2: ←/→, ↑, ↓, N/M
#   R — заново, Ctrl+R — перезапуск скрипта, Q — смена фона уровня, ESC — выход
import math
import os
import random
import subprocess
import sys

import pygame

# --- Настройки окна и мира ---
WIDTH, HEIGHT = 1200, 880   # размер экрана в пикселях
FPS = 60                    # кадров в секунду
ANIM_STEP = 8               # сколько кадров игры показывается одна картинка анимации фона
MUSIC_ON = False              # True — играть музыку из папки mus, False — без звука
MUSIC_FILE = "start-redused-noise.wav"   # трек для фоновой музыки
SFX_ON = True                # True — проигрывать звуки нажатий, False — без них
SFX_START = "start nes-sfx29.wav"       # звук нажатия START (папка sounds)
SFX_MENU = "menu nes-sfx23.wav"         # звук навигации в меню (папка sounds)
SFX_FOOTSTEP = "Footstep__005.wav"      # звук шагов (папка sounds)
SFX_START_VOL = 0.3         # громкость звука нажатия START
FOOTSTEP_TIME = 20             # кадров между шагами (цикл бега 40 кадров → шаг каждые 20)
MUSIC_FADE_STEP = 0.03         # насколько громкость меняется за кадр (0.03 → примерно 0.5 с)
TRANSITION = "blink"         # переход при старте: "blink" — мигание, "spiral" — спираль, "wipe" — диагональный вайп, "fade" — гаснение Байера
TRANS_TIME = 2              # кадров на переход
BLINK_CYCLE = 10             # кадров на цикл мигания (половина — темно, половина — картинка)
BLINK_STEP = 70              # насколько темнеет картинка за цикл (0..255)
FADE_TIME = 45             # кадров на ретро-затемнение в режиме "fade" (1 секунда 90)
FADE_PIXEL = 20              # размер блока «пикселя» ретро-эффекта
REVEAL_TIME = 30            # кадров на проявление уровня из темноты (обратный fade)
REVEAL_MODE = "wipe"         # как проявляется уровень: "bayer" — дизеринг, "wipe" — диагональной волной
INTRO_TIME = 60             # кадров на чёрный экран с названием уровня (2 секунды)
LEVEL_NUM = "УРОВЕНЬ ПЕРВЫЙ"   # номер уровня на заставке
LEVEL_NAME = "ДОРОГА В РАЙ"    # название уровня на заставке
FLOOR_Y = 620               # "пол" для фона/декораций (нижняя граница картинки фона)
CHARACTER_FLOOR_Y = 690     # линия, на которой стоят персонажи
# Уровень пола отдельно для каждого варианта (папка в sprites\lev).
# Значение — Y spлошной поверхности пола; None = авто (верх определяется по картинке).
# Пример: "fl2": 700 — поверхность варианта fl2 на 10 px ниже линии персонажей.
FLOOR_LEVEL = {
    "fl1": 680,
    "fl2": 680,
}
# Эти задние планы уже готовы к тайлингу вставкой — зеркалить и склеивать их не надо
NO_MIRROR = ("half",)
# Порядок фонов без числового префикса в имени (префикс вида 1_ 2_ задаёт порядок сам)
BACK_FALLBACK = ("back.png", "backnew-HALF.png", "river", "night river", "colorized")
TREES_H = 650             # высота слоя с объектами из sprites\trees (None — не рисовать)
BACK_H = 768               # общая высота задних планов: выше — режем, ниже — растягиваем
FLOOR_OVERLAP = {"fl2": 100}  # нахлёст картинок при склейке варианта пола, ключ — имя папки
LEVEL_LEN = 10000            # длина уровня по оси X
GRAVITY = 2.0               # ускорение свободного падения
MOVE = 12.0                  # скорость ходьбы
JUMP = -32                  # начальная скорость прыжка (отрицательная = вверх)
MAX_HP = 100                # максимальное здоровье игрока
NO_ENEMIES = True           # True — враги отключены (режим "чистого раннера")

SKY = (30, 26, 46)
SKY_D = (22, 20, 38)
ROAD = (90, 88, 84)
ROAD_D = (66, 64, 62)
SIDEWALK = (150, 148, 140)
PLAYER = (70, 200, 90)
PLAYER_D = (40, 130, 60)
PLAYER2 = (90, 150, 235)
PLAYER2_D = (50, 90, 170)
THUG = (190, 90, 90)
BRUISER = (140, 70, 200)
BOSS = (200, 60, 60)
SKIN = (235, 190, 150)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (220, 40, 40)
YELLOW = (255, 225, 60)
GREEN = (70, 200, 90)
GRAY = (150, 150, 150)
BARREL = (178, 120, 50)
BARREL_D = (120, 82, 34)


class Fighter:
    """Базовый боец: общие физика, здоровье, атаки, реакции на удар.
    От него наследуются Player (игрок) и Enemy (враг)."""

    def __init__(self, x, hp, color, name, scale=1.0):
        self.x = x                     # позиция по X в мире уровня
        self.y = CHARACTER_FLOOR_Y - 82 * scale  # стартовая позиция по Y (стоим на линии пола)
        self.vel_x = 0                 # горизонтальная скорость
        self.vel_y = 0                 # вертикальная скорость (гравитация)
        self.hp = hp                   # текущее здоровье
        self.max_hp = hp               # максимум здоровья (для полоски)
        self.color = color             # основной цвет тела
        self.name = name               # имя (P1, P2, THUG...)
        self.scale = scale             # масштаб размера (боссы крупнее)
        self.facing = 1                # направление взгляда: 1 = вправо, -1 = влево
        self.on_ground = True          # стоит ли на земле
        self.crouching = False         # присел (блок)
        self.attack = None             # текущая атака: "punch" / "kick" / None
        self.attack_timer = 0          # оставшиеся кадры атаки
        self.attack_hit = False        # уже ли атака попала в цель (один удар за анимацию)
        self.cooldown = 0              # кадры перезарядки между атаками
        self.combo = 0                 # счётчик серии ударов (усиливает урон)
        self.combo_timeout = 0         # кадр, после которого серия обнуляется
        self.flinch = 0                # кадры "отшатывания" от удара (нельзя действовать)
        self.knock = 0                 # сила отталкивания от удара
        self.was_moving = False        # двигался ли боец в этом кадре (для анимации бега)
        self.dead = False              # мёртв ли
        self.dead_timer = 0            # кадры после смерти (для уборки трупа)
        self.dead_fall = 0             # прогресс "падения" тела на землю
        self.ai_timer = 0              # таймер принятия решений ИИ (у врагов)
        self.bias = random.choice([-1, 1])  # личное предпочтение направления (для отскоков)

    @property
    def w(self):
        return int(44 * self.scale)    # ширина хитбокса персонажа

    @property
    def h(self):
        return int((50 if self.crouching else 82) * self.scale)  # высота (присев — ниже)

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)  # hitbox (collider)

    def hitbox(self):
        """Хитбокс активной атаки (кулак/нога вытянуты в сторону взгляда)."""
        if self.attack is None:
            return None
        r = self.rect
        if self.attack == "punch":
            w, h, oy = 46, int(24 * self.scale), int(30 * self.scale)
        else:  # kick — длиннее и выше
            w, h, oy = 62, int(30 * self.scale), int(36 * self.scale)
        hx = r.right if self.facing > 0 else r.left - w  # прямоугольник перед лицом
        return pygame.Rect(hx, r.y + oy, w, h)

    def attack_damage(self):
        """Урон текущей атаки. Комбо (combo) даёт бонус к урону."""
        if self.attack == "punch":
            base = 12 + self.combo * 3
            return base, "punch"
        return 20 + self.combo * 2, "kick"

    def try_attack(self, kind, now):
        """Запуск атаки, если не занят и не перезаряжается."""
        if self.cooldown > 0 or self.attack is not None or self.dead:
            return
        self.attack = kind
        self.attack_timer = 7 if kind == "punch" else 12  # длительность анимации
        self.attack_hit = False
        self.cooldown = 3 if kind == "punch" else 5       # пауза до следующего удара
        if now > self.combo_timeout:                       # вышло время — сбрасываем серию
            self.combo = 0
        self.combo += 1
        if self.combo > 2:
            self.combo = 2        # максимум комбо — 3 удара подряд
        self.combo_timeout = now + 30

    def take_hit(self, dmg, dir_side, blocking=False):
        """Получение урона. Если блокирует — урон вдвое меньше."""
        if self.dead:
            return
        if blocking:
            dmg = dmg // 2
        self.hp -= dmg
        self.attack = None        # сбиваем атаку противника
        self.attack_timer = 0
        self.flinch = 7
        self.knock = (dir_side or self.bias) * 6  # отталкивание в сторону удара
        if self.hp <= 0:
            self.hp = 0
            self.dead = True
            self.dead_fall = 0

    def update(self, cam, frame):
        """Базовая симуляция: атаки, перезарядки, гравитация, движение, границы уровня."""
        now = frame
        if self.dead:
            self.dead_timer += 1
            self.dead_fall += 3.0     # тело "падает" на землю
            if self.dead_fall > 15:
                self.dead_fall = 15
            return

        if self.flinch > 0:           # затухание отшатывания
            self.flinch -= 1
        if self.knock:                # затухание отталкивания (инерция)
            self.x += self.knock
            self.knock *= 0.67
            if abs(self.knock) < 0.4:
                self.knock = 0

        if self.attack is not None:   # анимация атаки идёт по таймеру
            self.attack_timer -= 1
            if self.attack_timer <= 0:
                self.attack = None
        if self.cooldown > 0:
            self.cooldown -= 1

        self.vel_y += GRAVITY         # гравитация
        self.y += self.vel_y
        if self.y >= CHARACTER_FLOOR_Y - self.h:
            self.y = CHARACTER_FLOOR_Y - self.h
            self.vel_y = 0
            self.on_ground = True
        else:
            self.on_ground = False

        self.was_moving = abs(self.vel_x) > 0.05
        self.x += self.vel_x          # горизонтальное движение
        self.vel_x = 0
        self.x = max(cam, min(self.x, LEVEL_LEN - self.w))  # не даём уйти за уровень/камеру

        if self.now_blocking:         # сброс флага блока после обработки
            self.now_blocking = False


class Player(Fighter):
    """Игрок. Обрабатывает нажатия клавиш и превращает их в действия бойца."""

    def __init__(self, pnum=0, mode=1):
        name = "P1" if pnum == 0 else "P2"
        color = PLAYER if pnum == 0 else PLAYER2
        super().__init__(100 * pnum, MAX_HP, color, name, scale=2.0)  # старт: P1=0, P2=100; scale=2.0 — персонаж в 2 раза крупнее
        self.pnum = pnum          # номер игрока (0 = P1, 1 = P2)
        self.mode = mode          # число игроков в партии (1 или 2)
        self.now_blocking = False  # блок активен в этом кадре
        self.moved = 0            # счётчик пройденных кадров движения (отладка)
        self.was_moving = False    # двигался ли игрок в этом кадре (для анимации бега)
        self.step_t = 0           # кадров до следующего шага

    def update(self, cam, frame):
        super().update(cam, frame)   # сначала базовая физика Fighter
        if self.dead:
            return

        # Чтение клавиш в зависимости от схемы управления
        keys = pygame.key.get_pressed()
        if self.pnum == 1:                       # 2-й игрок использует стрелки + N/M
            left = keys[pygame.K_LEFT]
            right = keys[pygame.K_RIGHT]
            up = keys[pygame.K_UP]
            down = keys[pygame.K_DOWN]
            punch = keys[pygame.K_n]
            kick = keys[pygame.K_m]
        elif self.mode == 1:                     # P1 в одиночной игре: и WASD, и стрелки
            left = keys[pygame.K_a] or keys[pygame.K_LEFT]
            right = keys[pygame.K_d] or keys[pygame.K_RIGHT]
            up = keys[pygame.K_w] or keys[pygame.K_UP]
            down = keys[pygame.K_s] or keys[pygame.K_DOWN]
            punch = keys[pygame.K_z] or keys[pygame.K_j]
            kick = keys[pygame.K_x] or keys[pygame.K_k]
        else:                                    # P1 в кооперативе: только WASD + J/K
            left = keys[pygame.K_a]
            right = keys[pygame.K_d]
            up = keys[pygame.K_w]
            down = keys[pygame.K_s]
            punch = keys[pygame.K_j]
            kick = keys[pygame.K_k]

        self.crouching = False
        if self.flinch <= 0:                     # в отшатывании игрок неуправляем
            if left:
                self.vel_x = -MOVE
                self.facing = -1
                self.moved += 1
            elif right:
                self.vel_x = MOVE
                self.facing = 1
                self.moved += 1
            if up and self.on_ground:            # прыжок только с земли
                self.vel_y = JUMP
                self.on_ground = False
            if down:
                self.crouching = True            # присед = блокировка
                self.now_blocking = True
            if punch:
                self.try_attack("punch", frame)
            elif kick:
                self.try_attack("kick", frame)
        # для анимации бега: двигались и стоим на земле
        self.was_moving = (left or right) and self.on_ground and self.flinch <= 0


class Enemy(Fighter):
    """Враг с простым ИИ. Виды: thug (громила), bruiser (бризер/брузер), boss (AXIS)."""

    def __init__(self, x, kind):
        self.kind = kind
        if kind == "thug":
            super().__init__(x, 45, THUG, "THUG")
            self.speed = 2.2           # скорость погони
            self.attack_range = 70     # дистанция начала атаки
        elif kind == "bruiser":
            super().__init__(x, 80, BRUISER, "BRUTE")
            self.scale = 1.2           # крупнее обычного
            self.speed = 1.5
            self.attack_range = 80
        else:                          # boss — большой и прочный
            super().__init__(x, 180, BOSS, "AXIS")
            self.scale = 1.6
            self.speed = 0.9
            self.attack_range = 110
        self.now_blocking = False
        self.hp = int(self.hp * self.scale)   # здоровье растёт с размером
        self.max_hp = self.hp

    def ai_update(self, player, cam, frame):
        """Простой ИИ: приблизиться, встать в радиус атаки и бить/прыгать."""
        if self.dead or player.dead:
            return
        dx = player.x - self.x
        dist = abs(dx)
        self.facing = 1 if dx > 0 else -1
        self.crouching = False

        if self.flinch > 0:            # в отшатывании враг не действует
            return

        if dist > self.attack_range + 20:      # далеко — бежим к игроку
            self.vel_x = self.facing * self.speed
        elif dist < self.attack_range:         # близко — иногда бьём/прыгаем
            self.ai_timer -= 1
            if self.ai_timer <= 0:
                self.ai_timer = random.randint(15, 45)
                if random.random() < 0.55:
                    kind = "punch" if random.random() < 0.6 else "kick"
                    self.try_attack(kind, frame)
                elif random.random() < 0.3 and self.on_ground:
                    self.vel_y = -26            # враг прыгает на игрока
        else:                                    # пограничная зона — подкрадываемся
            self.vel_x = self.facing * min(self.speed, dist * 0.1)


class Barrel:
    """Бочка-декорация/препятствие (в текущей версии выключена)."""

    def __init__(self, x):
        self.x = x
        self.y = FLOOR_Y - 46          # стоит на полу
        self.hp = 2                    # ломается с двух ударов
        self.dead = False

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), 40, 46)


class Game:
    """Главный класс игры: инициализация, загрузка ресурсов, игровой цикл, отрисовка."""

    def __init__(self):
        pygame.init()
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
        if self.audio_ok and MUSIC_ON:
            try:
                pygame.mixer.music.load(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                     "mus", MUSIC_FILE))
                self.music_ok = True
            except pygame.error:
                self.music_ok = False
        self.sfx = {}
        if self.audio_ok and SFX_ON:
            for key, fn in (("start", SFX_START), ("menu", SFX_MENU), ("step", SFX_FOOTSTEP)):
                sfx_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sounds", fn)
                if os.path.exists(sfx_path):
                    try:
                        self.sfx[key] = pygame.mixer.Sound(sfx_path)
                    except pygame.error:
                        pass
            if "step" in self.sfx:
                self.sfx["step"].set_volume(0.25)      # шаги не должны перебивать игру
            if "start" in self.sfx:
                self.sfx["start"].set_volume(SFX_START_VOL)   # нажатие START — тише
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("TOADS vs DRAGON — BEAT-EM-UP")
        self.clock = pygame.time.Clock()
        self.font_big = pygame.font.SysFont("arial", 50)
        self.font_m = pygame.font.SysFont("arial", 22)
        self.font_s = pygame.font.SysFont("arial", 15)
        # Пиксельный шрифт для заголовков меню (англ.)
        self.pixel_font = pygame.font.Font(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts", "PressStart2P.ttf"), 20)
        # Шрифт с поддержкой кириллицы для меню
        self.pixel_font_ru = pygame.font.Font(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts", "Tiny5.ttf"), 32)
        # Заставка титульного экрана
        try:
            img = pygame.image.load(os.path.join(os.path.dirname(os.path.abspath(__file__)), "screen", "6fin.png")).convert_alpha()
        except pygame.error:
            img = None
        self.title_img = img
        # Стрелка выбора режима в меню
        base = os.path.dirname(os.path.abspath(__file__))
        # Кадры анимации бега (извлечены из an\run.png, 20 кадров 128x128)
        self.run_frames = self.load_run_frames(base)
        spr_path = os.path.join(base, "sprites", "choose.png")
        self.choose_img = None
        if os.path.exists(spr_path):
            try:
                self.choose_img = pygame.image.load(spr_path).convert_alpha()
            except pygame.error:
                self.choose_img = None
        self.level_bg = None
        self.level_sel = 0
        # Параллакс-фон: задние слои (переключение клавишей E) и передний (front)
        self.par_backs = []           # список (имя файла, картинка) задних слоёв
        self.par_back_name = ""       # название активного заднего слоя (подпись на экране)
        self.par_front = None         # первый слой (скорость 1.0 = камера)
        self.par_fronts = []          # варианты первого слоя: (имя, картинка или None)
        self.par_front_idx = 0        # 0 = первый слой отсутствует
        self.par_first_name = "нет"   # имя активного варианта первого слоя
        self.floor_img = None         # пол уровня (активный вариант)
        self.floor_row = 0            # строка сплошной поверхности в картинке пола
        self.floor_name = ""          # имя варианта пола (fl1 / fl2 ...)
        self.floors = []              # варианты пола: (имя, полоса, строка поверхности)
        self.floor_idx = 0            # индекс активного варианта пола
        self.par_back_idx = 0         # индекс активного заднего слоя в par_backs
        self.par_ok = False           # загрузились ли слои параллакса
        self.use_parallax = True      # сейчас включён только параллакс-уровень
        self.load_parallax()
        self.fade_tiles = self.make_fade_tiles()   # тайлы сетки Байера для режима "fade"
        self.trans_active = False     # идёт ли переход к партии
        self.trans_t = 0              # кадры перехода
        self.trans_step = 0           # ступенька затемнения для режима "fade"
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
        # Запасной тайлинг-фон (для level_sel=0 до смены через Q) — уровни ОТКЛЮЧЕНЫ
        # lv_path = os.path.join(base, "screen", "1lev_tiled.jpg")
        # if os.path.exists(lv_path):
        #     try:
        #         raw = pygame.image.load(lv_path).convert()
        #         lw = raw.get_width()
        #         lh = FLOOR_Y
        #         scaled = pygame.transform.smoothscale(raw, (int(lw * lh / raw.get_height()), lh))
        #         self.level_bg = pygame.Surface((LEVEL_LEN, lh), pygame.SRCALPHA)
        #         sw, sh = scaled.get_size()
        #         for tx in range(0, LEVEL_LEN, sw):     # тайлим картинку на всю длину уровня
        #             self.level_bg.blit(scaled, (tx, 0))
        #     except pygame.error:
        #         self.level_bg = None
        self.reset()

    def load_run_frames(self, base):
        """Загружает кадры анимации бега игрока.
        Источник: папка an\\run (run_00.png..run_19.png) или run.png (APNG, распаковка через Pillow)."""
        frames = []
        dir_run = os.path.join(base, "an", "run")
        if os.path.isdir(dir_run):
            names = sorted(f for f in os.listdir(dir_run) if f.lower().endswith(".png"))
            for nm in names:
                try:
                    frames.append(pygame.image.load(os.path.join(dir_run, nm)).convert_alpha())
                except pygame.error:
                    pass
            if frames:
                return frames
        # Распаковка APNG run.png в набор кадров через Pillow (если доступен)
        apng = os.path.join(base, "an", "run.png")
        if os.path.exists(apng):
            try:
                from PIL import Image
                img = Image.open(apng)
                for i in range(getattr(img, "n_frames", 1)):
                    img.seek(i)
                    frame = img.convert("RGBA")
                    w, h = frame.size
                    # срезаем чёрную рамку-артефакт по краям (1px справа/снизу у исходника)
                    frame = frame.crop((0, 0, max(1, w - 1), max(1, h - 1)))
                    size = frame.size
                    raw = frame.tobytes()
                    surf = pygame.image.frombuffer(raw, size, "RGBA").convert_alpha()
                    frames.append(surf)
            except Exception:
                frames = []
        return frames

    def load_parallax(self, force=True):
        """Загружает параллакс: задние планы из папки screen\back (движутся медленнее
        камеры, переключение клавишей E) и первый слой (front, скорость 1.0, клавиша Q).
        Без force слои не перечитываются — используется уже загруженный кеш."""
        if not force and self.par_ok:
            return
        base = os.path.dirname(os.path.abspath(__file__))
        self.par_backs = []
        self.par_front = None
        self.par_ok = False
        # Задние планы лежат в screen\back: картинки — статичные слои, папки — анимации.
        # Числовой префикс в имени (1_ 2_ 3_...) задаёт порядок появления при смене фонов.
        backdir = os.path.join(base, "screen", "back")
        self.anim_cache = {}
        if os.path.isdir(backdir):
            entries = []
            for name in os.listdir(backdir):
                p = os.path.join(backdir, name)
                if os.path.isdir(p):
                    entries.append((self.back_order(name), name, "anim", p))
                elif name.lower().endswith((".png", ".jpg", ".jpeg")):
                    entries.append((self.back_order(name), name, "static", p))
            entries.sort(key=lambda e: e[:2])
            for order, fn, kind, p in entries:
                if kind == "anim":
                    self.par_backs.append((fn, kind, p))   # кадры читаем лениво
                    continue
                try:
                    pic = pygame.image.load(p)
                    if not any(k in fn.lower() for k in NO_MIRROR):
                        pic = self.mirror_glue(pic)
                    self.par_backs.append((fn, kind, self.fit_height(pic).convert()))
                except pygame.error:
                    pass
        # Первый слой параллакса: варианты листаются клавишей Q.
        # Вариант 0 — слоя нет; далее Paralax-frontCON.png и всё, что лежит в screen\front.
        self.par_fronts = [("нет", None)]
        front = os.path.join(base, "screen", "Paralax-frontCON.png")
        if os.path.exists(front):
            try:
                # первому слою альфа обязательна: сквозь него видно задний фон
                self.par_fronts.append(
                    ("Paralax-frontCON.png", pygame.image.load(front).convert_alpha()))
            except pygame.error:
                pass
        fdir = os.path.join(base, "screen", "front")
        if os.path.isdir(fdir):
            for fn in sorted(f for f in os.listdir(fdir)
                             if f.lower().endswith((".png", ".jpg", ".jpeg"))):
                try:
                    self.par_fronts.append(
                        (fn, pygame.image.load(os.path.join(fdir, fn)).convert_alpha()))
                except pygame.error:
                    pass
        self.set_par_front(getattr(self, "par_front_idx", 0))
        self.load_trees()
        self.load_floors()
        if self.par_backs:
            self.par_back_idx %= len(self.par_backs)
            self.par_back_name = self.par_backs[self.par_back_idx][0]
        else:
            self.par_back_name = ""
        if self.par_backs or self.par_front is not None:
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

    def load_trees(self):
        """Слой с объектами из sprites\\trees. Имя файла задаёт порядок и сдвиг:
        <номер>_<сдвиг>.png — номер по порядку, сдвиг в пикселях вверх (2_100.png = второй,
        поднять на 100). Без префикса — в конец, сдвиг 0. Высота слоя — TREES_H."""
        base = os.path.dirname(os.path.abspath(__file__))
        tdir = os.path.join(base, "sprites", "trees")
        self.trees_img = None
        if not TREES_H or not os.path.isdir(tdir):
            return
        items = []
        for fn in os.listdir(tdir):
            if not fn.lower().endswith((".png", ".jpg", ".jpeg")):
                continue
            name = os.path.splitext(fn)[0]
            head = name.split("_", 1)[0]
            digits = ""
            for ch in head:                           # порядок — ведущие цифры имени (4hi1 -> 4)
                if ch.isdigit():
                    digits += ch
                else:
                    break
            order = int(digits) if digits else 9999   # без номера — в конец
            try:
                shift = int(name.split("_")[1])       # сдвиг вверх в пикселях (1_20 -> 20, 3_-5 -> вниз 5)
            except (IndexError, ValueError):
                shift = 0
            items.append((order, fn, shift))
        items.sort(key=lambda it: (it[0], it[1]))
        imgs = []
        for order, fn, shift in items:
            try:
                imgs.append((pygame.image.load(os.path.join(tdir, fn)), shift))
            except pygame.error:
                pass
        if not imgs:
            return
        height = TREES_H                              # высота слоя фиксированная — новые файлы её не двигают
        strip = pygame.Surface((sum(im.get_width() for im, _ in imgs), height), pygame.SRCALPHA)
        x = 0
        for im, shift in imgs:
            strip.blit(im, (x, -shift))              # верх картинок на верхней линии слоя
            x += im.get_width()
        self.trees_img = strip.convert_alpha()

    def load_floors(self):
        """Читаем варианты пола из sprites\\lev\\fl* (каждая папка — один вариант)."""
        base = os.path.dirname(os.path.abspath(__file__))
        levdir = os.path.join(base, "sprites", "lev")
        self.floors = []
        if os.path.isdir(levdir):
            for name in sorted(d for d in os.listdir(levdir)
                               if d.lower().startswith("fl")
                               and os.path.isdir(os.path.join(levdir, d))):
                v = self.load_floor_variant(os.path.join(levdir, name))
                if v:
                    self.floors.append(v)
        self.set_floor(getattr(self, "floor_idx", 0))

    def set_floor(self, idx):
        """Вариант пола переключается клавишей F. Уровень берётся из FLOOR_LEVEL
        (верх части ключа), None — авто: по верхней сплошной поверхности картинки."""
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

    @staticmethod
    def fit_height(im, height=None):
        """Приводит задний план к общей высоте BACK_H: что выше — режем по нижнему
        краю (земля), что ниже — растягиваем. Так все фоны стоят на одной высоте."""
        height = BACK_H if height is None else height
        w, h = im.get_size()
        if not height or h == height:
            return im
        if h > height:                       # лишнее снизу (земля) — отрезаем
            return im.subsurface((0, 0, w, height)).copy()
        nw = max(1, int(round(w * float(height) / h)))
        return pygame.transform.smoothscale(im, (nw, height))

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

    def set_par_front(self, idx):
        """Выбор варианта первого слоя параллакса (None = первый слой отсутствует)."""
        if not self.par_fronts:
            self.par_front_idx = 0
            self.par_first_name, self.par_front = "нет", None
            return
        self.par_front_idx = idx % len(self.par_fronts)
        self.par_first_name, self.par_front = self.par_fronts[self.par_front_idx]

    def get_anim_frames(self, idx, folder):
        """Кадры анимированного фона читаем только когда он выбран, потом держим в кеше."""
        if idx in self.anim_cache:
            return self.anim_cache[idx]
        frames = []
        for fn in sorted(f for f in os.listdir(folder)
                         if f.lower().endswith((".png", ".jpg", ".jpeg"))):
                try:
                    frames.append(self.fit_height(
                        self.mirror_glue(pygame.image.load(os.path.join(folder, fn)))))
                except pygame.error:
                    pass
        self.anim_cache[idx] = frames
        self.par_backs[idx] = (f"{os.path.basename(folder)} ({len(frames)} кадра)", "anim", frames)
        if self.par_back_idx == idx:
            self.par_back_name = self.par_backs[idx][0]
        return frames

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

    def play_sfx(self, name):
        """Проигрывает короткий звук по имени (self.sfx) — например, на START."""
        snd = self.sfx.get(name)
        if snd is not None:
            snd.play()

    def update_footsteps(self, pl):
        """Шаги: звук каждые FOOTSTEP_TIME кадров, пока боец бежит по земле."""
        if pl.dead or not pl.on_ground or not pl.was_moving:
            pl.step_t = 0                      # стоим — первый шаг сразу при старте бега
            return
        if pl.step_t > 0:
            pl.step_t -= 1
            return
        pl.step_t = FOOTSTEP_TIME
        self.play_sfx("step")

    def restart_script(self):
        """Полный рестарт скрипта: запускает себя заново в отдельном процессе pythonw."""
        py = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        if not os.path.exists(py):
            py = sys.executable
        subprocess.Popen([py, os.path.abspath(__file__)], cwd=os.path.dirname(os.path.abspath(__file__)))
        pygame.quit()
        sys.exit()

    def reset(self, players=None):
        """Сброс партии: персонажи, камера, счёт, враги, фон уровня."""
        print(f"[DEBUG] reset called, level_sel={self.level_sel}")
        if players is None:
            players = getattr(self, "num_players", 1)
        self.num_players = players
        self.players = [Player(i, players) for i in range(players)]
        self.frame = 0
        self.cam = 0
        self.state = "title"           # состояния: title / play / win / lose
        self.score = 0
        self.enemies = []
        # self.barrels = [Barrel(900), Barrel(2100), Barrel(3300), Barrel(4600)]  # бочки выключены
        self.boss_spawned = False
        # Точки и типы врагов по мере продвижения (включённые только если НЕ NO_ENEMIES)
        self.spawn_points = [(600, "thug"), (950, "thug"), (1500, "bruiser"),
                             (1900, "thug"), (2400, "bruiser"), (2900, "thug"),
                             (3100, "thug"), (3700, "bruiser"), (4200, "thug"),
                             (5000, "bruiser")]
        self.spawn_idx = 0
        self.win_t = 0                 # таймер экрана победы
        self.lose_t = 0                # таймер экрана поражения
        self.mode_sel = 0              # выбранный пункт в меню (1/2 игрока)
        self.load_level_bg()

    def make_fade_tiles(self):
        """Готовит 17 тайлов сетки Байера 4×4 — ступенчатое ретро-затемнение экрана."""
        bayer = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]
        tiles = []
        for lvl in range(17):
            t = pygame.Surface((4 * FADE_PIXEL, 4 * FADE_PIXEL), pygame.SRCALPHA)
            for ty in range(4):
                for tx in range(4):
                    if bayer[ty][tx] < lvl:
                        t.fill(BLACK, (tx * FADE_PIXEL, ty * FADE_PIXEL,
                                       FADE_PIXEL, FADE_PIXEL))
            tiles.append(t)
        return tiles

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

    def make_spiral_order(self):
        """Порядок ячеек для спирального вайпа: расширяющийся виток от центра экрана."""
        cells = []
        cols = (WIDTH + FADE_PIXEL - 1) // FADE_PIXEL
        rows = (HEIGHT + FADE_PIXEL - 1) // FADE_PIXEL
        cx0 = (cols - 1) / 2
        cy0 = (rows - 1) / 2
        rmax = max(cx0, cy0) or 1
        turns = 3.0
        for cy in range(rows):
            for cx in range(cols):
                dx = (cx - cx0) / rmax
                dy = (cy - cy0) / rmax
                ang = math.atan2(dy, dx) / (2 * math.pi)
                rad = min(1.0, (dx * dx + dy * dy) ** 0.5)
                key = (ang + rad * turns + random.random() * 0.004) % 1.0
                cells.append((key, cx, cy))
        cells.sort()
        return [(cx * FADE_PIXEL, cy * FADE_PIXEL) for _, cx, cy in cells]

    def start_transition(self, players):
        """Запускает переход к партии (режим выбирает TRANSITION)."""
        if TRANSITION != "fade" and self.trans_order_mode != TRANSITION:
            self.trans_order = (self.make_wipe_order() if TRANSITION == "wipe"
                                else self.make_spiral_order())
            self.trans_order_mode = TRANSITION
        self.trans_players = players
        self.trans_t = 0
        self.music_off = True          # музыка плавно стихает на переходе
        self.music_paused = False
        self.trans_step = 0
        self.trans_done = 0
        self.trans_started = False
        self.trans_active = True
        if TRANSITION != "fade":
            self.trans_overlay.fill((0, 0, 0, 0))

    def start_level_intro(self):
        """Экран погас — показываем чёрную заставку с названием уровня."""
        self.state = "intro"
        self.intro_t = INTRO_TIME
        self.trans_paused = True

    def draw_level_intro(self):
        """Чёрный экран: «УРОВЕНЬ ПЕРВЫЙ — ДОРОГА В РАЙ» перед началом партии."""
        self.screen.fill(BLACK)
        num = self.pixel_font_ru.render(LEVEL_NUM, True, (170, 170, 180))
        name = self.pixel_font_ru.render(LEVEL_NAME, True, YELLOW)
        name = pygame.transform.scale(name, (name.get_width() * 2, name.get_height() * 2))
        self.screen.blit(num, (WIDTH // 2 - num.get_width() // 2, HEIGHT // 2 - 100))
        self.screen.blit(name, (WIDTH // 2 - name.get_width() // 2, HEIGHT // 2 - 30))

    def toggle_music_pause(self):
        """Клавиша P — пауза/продолжение музыки в игре (громкость уходит плавно)."""
        if not self.music_ok or self.music_off:
            return
        self.music_paused = not self.music_paused
        print(f"[DEBUG] music paused={self.music_paused}")

    def update_music(self):
        """Музыка каждый кадр: плавное затухание/возврат громкости, пауза по P, перезапуск трека."""
        if not self.music_ok:
            return
        vol = pygame.mixer.music.get_volume()
        quiet = self.music_off or self.music_paused
        if vol > 0.001 and quiet:                  # плавно стихаем
            pygame.mixer.music.set_volume(max(0.0, vol - MUSIC_FADE_STEP))
        elif vol < 0.999 and not quiet:            # плавно возвращаем
            pygame.mixer.music.set_volume(min(1.0, vol + MUSIC_FADE_STEP))
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

    def start_round(self):
        """Партия началась: музыка снова идёт (громкость плавно возвращается к 1.0)."""
        self.state = "play"
        self.music_off = False
        self.music_paused = False
        self.music_really_paused = False

    def start_level_reveal(self):
        """После заставки уровень проявляется из темноты (режим REVEAL_MODE)."""
        self.state = "reveal"
        self.reveal_t = 0
        self.reveal_done = 0
        self.reveal_surface.fill((0, 0, 0, 255))   # первый кадр проявления — сразу темно

    def update_reveal(self):
        """Проявление уровня: "bayer" — сетка дизеринга, "wipe" — темнота уходит диагональной волной."""
        self.reveal_t += 1
        if REVEAL_MODE == "wipe":
            if self.trans_order is None or self.trans_order_mode != "wipe":
                self.trans_order = self.make_wipe_order()
                self.trans_order_mode = "wipe"
            n = len(self.trans_order)
            target = int(self.reveal_t * n / max(1, REVEAL_TIME))
            for i in range(self.reveal_done, target):
                x, y = self.trans_order[i]
                self.reveal_surface.fill((0, 0, 0, 0), (x, y, FADE_PIXEL, FADE_PIXEL))
            self.reveal_done = target
        else:
            # каждый кадр заново собираем темноту: сначала гаснут крупные пиксели, потом мелкие
            step = 16 - min(16, (self.reveal_t + 1) * 16 // max(1, REVEAL_TIME))   # 16 — чёрный, 0 — чисто
            tile = self.fade_tiles[step]
            self.reveal_surface.fill((0, 0, 0, 0))
            tw, th = tile.get_size()
            for ty in range(0, HEIGHT, th):
                for tx in range(0, WIDTH, tw):
                    self.reveal_surface.blit(tile, (tx, ty))
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
        if TRANSITION == "fade":
            self.trans_step = min(16, self.trans_t * 16 // FADE_TIME)
            if self.trans_t >= FADE_TIME:
                self.trans_active = False
                self.start_level_intro()
                print(f"[DEBUG] Fade done, state={self.state}")
            return
        n = len(self.trans_order)
        half = max(1, TRANS_TIME // 2)
        if self.trans_t <= half:                      # закрываем экран (вайп или спираль)
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
        """Поверх экрана — эффект перехода: гаснение, диагональный вайп или спираль."""
        if self.state == "reveal":         # уровень проявляется из темноты
            self.screen.blit(self.reveal_surface, (0, 0))
            return
        if not self.trans_active or self.trans_paused:
            return
        if TRANSITION != "fade":
            self.screen.blit(self.trans_overlay, (0, 0))
            return
        tile = self.fade_tiles[min(16, self.trans_step)]
        tw, th = tile.get_size()
        for ty in range(0, HEIGHT, th):
            for tx in range(0, WIDTH, tw):
                self.screen.blit(tile, (tx, ty))

    def load_level_bg(self):
        """Загрузка фона текущего уровня.
        Параллакс включён (use_parallax) — грузятся слои back/front;
        иначе — простой фон по level_sel (0/1/2, сейчас отключено)."""
        if self.use_parallax:
            print(f"[DEBUG] load_level_bg: беру параллакс (back/front) из кеша")
            self.load_parallax(force=False)
            return
        base = os.path.dirname(os.path.abspath(__file__))
        if self.level_sel == 2:
            # Третий уровень: тайловый фон, картинка повторяется подряд
            level_file = "ComfyUI_temp_vfffm_00015_.png"
            print(f"[DEBUG] load_level_bg: level_sel={self.level_sel} -> {level_file} (тайлинг)")
            lv_path = os.path.join(base, "screen", level_file)
            self.level_bg = None
            self.level_bg_y = -130        # сдвиг фона по вертикали (подгонка под экран)
            if os.path.exists(lv_path):
                try:
                    raw = pygame.image.load(lv_path).convert()
                    th = 672              # целевая высота тайла (как у остальных уровней)
                    tw = int(raw.get_width() * th / raw.get_height())
                    scaled = pygame.transform.smoothscale(raw, (tw, th))
                    # Склеиваем тайлы в одну непрерывную ленту шириной LEVEL_LEN
                    self.level_bg = pygame.Surface((LEVEL_LEN, th), pygame.SRCALPHA)
                    sw, sh = scaled.get_size()
                    for tx in range(0, LEVEL_LEN, sw):
                        self.level_bg.blit(scaled, (tx, 0))
                except pygame.error:
                    self.level_bg = None
            return
        level_file = "2lev.jpg" if self.level_sel == 1 else "1levonepiece.png"
        print(f"[DEBUG] load_level_bg: level_sel={self.level_sel} -> {level_file}")
        lv_path = os.path.join(base, "screen", level_file)
        self.level_bg = None
        self.level_bg_y = -130        # сдвиг фона по вертикали (подгонка под экран)
        if os.path.exists(lv_path):
            try:
                raw = pygame.image.load(lv_path).convert()
                self.level_bg = raw    # используем как есть, без тайлинга
            except pygame.error:
                self.level_bg = None

    def run(self):
        """Главный игровой цикл: события, обновление логики, отрисовка, синхронизация по FPS."""
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        sys.exit()
                    if event.key == pygame.K_F5:
                        self.reset()                          # принудительный сброс
                    if event.key == pygame.K_r:
                        if event.mod & pygame.KMOD_CTRL:
                            self.restart_script()             # Ctrl+R — рестарт процесса
                        else:
                            self.reset()                      # R — сброс партии
                    if event.key == pygame.K_e and self.use_parallax:     # E — смена заднего слоя параллакса
                        if len(self.par_backs) > 1:
                            self.par_back_idx = (self.par_back_idx + 1) % len(self.par_backs)
                            self.par_back_name = self.par_backs[self.par_back_idx][0]
                            print(f"[DEBUG] E pressed, back layer -> {self.par_back_name}")
                        else:
                            print("[DEBUG] E pressed, но других задних слоёв нет")
                    if event.key == pygame.K_p and self.state == "play":   # P — пауза музыки
                        self.toggle_music_pause()
                    if event.key == pygame.K_q and self.use_parallax:   # Q — смена первого слоя параллакса
                        if len(self.par_fronts) > 1:
                            self.set_par_front(self.par_front_idx + 1)
                            print(f"[DEBUG] Q pressed, первый слой -> {self.par_first_name}")
                        else:
                            print("[DEBUG] Q pressed, других вариантов первого слоя нет")
                    if event.key == pygame.K_f:               # F — смена варианта пола
                        if len(self.floors) > 1:
                            self.set_floor(self.floor_idx + 1)
                            print(f"[DEBUG] F pressed, пол -> {self.floor_name}")
                        else:
                            print("[DEBUG] F pressed, других вариантов пола нет")
                    if event.key == pygame.K_F6:               # F6 — перезагрузка фона (параллакс / уровень)
                        print(f"[DEBUG] F6 pressed, level_sel={self.level_sel} -> {(self.level_sel + 1) % 3} use_parallax={self.use_parallax}")
                        if self.use_parallax:
                            self.load_parallax()              # перезагружаем слои параллакса
                        else:
                            self.level_sel = (self.level_sel + 1) % 3
                            self.load_level_bg()
                        print(f"[DEBUG] After load_level_bg: level_bg={self.level_bg}, size={self.level_bg.get_size() if self.level_bg else None}")
                    if self.state == "title":                 # навигация в главном меню
                        if self.trans_active:
                            pass
                        elif event.key in (pygame.K_UP, pygame.K_w):
                            self.mode_sel = (self.mode_sel - 1) % 2
                            self.play_sfx("menu")
                        elif event.key in (pygame.K_DOWN, pygame.K_s):
                            self.mode_sel = (self.mode_sel + 1) % 2
                            self.play_sfx("menu")
                        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE, pygame.K_z):
                            self.play_sfx("start")               # звук сразу, до перехода
                            print(f"[DEBUG] ENTER pressed, level_sel={self.level_sel}")
                            self.start_transition(self.mode_sel + 1)
                            print(f"[DEBUG] Transition started, mode={TRANSITION}")
                if (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                        and self.state == "title" and not self.trans_active):
                    self.play_sfx("start")                       # клик мышью — тоже начать
                    self.start_transition(self.mode_sel + 1)

            self.frame += 1
            self.update()
            self.update_music()            # музыка: плавная громкость, пауза по P, перезапуск

            self.draw()
            self.draw_transition()
            pygame.display.flip()
            self.clock.tick(FPS)

    def update(self):
        """Обновление всего мира: камера, игроки, спавн и поведение врагов, коллизии."""
        if self.trans_active:             # переход при старте партии
            if not self.trans_paused:     # на паузе, пока показан экран уровня
                self.update_transition()

        if self.state == "intro":          # чёрный экран с названием уровня
            self.intro_t -= 1
            if self.intro_t <= 0:
                self.trans_paused = False
                if not self.trans_started:  # переход уже закончился (blink/fade) — создаём уровень
                    self.trans_started = True
                    self.reset(self.trans_players)   # reset() ставит state="title", поэтому state — после
                    self.start_level_reveal()        # уровень проявляется из темноты
                else:                                # wipe/spiral — экран откроется сам
                    self.start_round()
            return

        if self.state == "reveal":         # плавное проявление уровня из темноты
            self.update_reveal()
            return

        players = self.players
        alive = [pl for pl in players if not pl.dead]

        if self.state == "title":
            return

        # Камера следует за самым правым живым игроком (не выходя за уровень)
        if alive:
            rightmost = max(pl.x for pl in alive)
        else:
            rightmost = players[0].x
        self.cam = int(max(0, min(rightmost - WIDTH // 3, LEVEL_LEN - WIDTH)))

        for pl in players:
            pl.update(self.cam, self.frame)
            self.update_footsteps(pl)

        # Проверка условий победы/поражения
        if self.state == "play":
            if not alive:
                self.state = "lose"        # все игроки погибли
                self.lose_t = 0
            if alive and any(pl.x > LEVEL_LEN - 60 for pl in alive):
                self.state = "win"         # дошли до конца уровня
                self.win_t = 0

        # Спавн врагов по мере продвижения игрока
        if self.state == "play" and not NO_ENEMIES:
            while self.spawn_idx < len(self.spawn_points):
                sx, kind = self.spawn_points[self.spawn_idx]
                if rightmost + WIDTH >= sx:
                    left = sx < self.cam
                    ex = sx - 200 if left else sx        # если точка позади камеры — отодвигаем вперёд
                    self.enemies.append(Enemy(max(50, ex), kind))
                    self.spawn_idx += 1
                else:
                    break

            if not self.boss_spawned and rightmost > 4800:
                self.boss_spawned = True                 # босс в конце уровня
                self.enemies.append(Enemy(max(50, 5200), "boss"))

        # Поведение врагов + удаление трупов
        if not NO_ENEMIES:
            for e in self.enemies[:]:
                if e.dead:
                    e.update(self.cam, self.frame)
                    if e.dead_timer > 60:
                        self.enemies.remove(e)           # труп убран через 60 кадров
                    continue
                target = alive[0] if alive else players[0]
                e.ai_update(target, self.cam, self.frame)
                e.update(self.cam, self.frame)
                self.bump_world(e)                       # расталкивание с препятствиями

        if not NO_ENEMIES:
            # Атаки игроков по врагам
            if self.state == "play":
                for pl in players:
                    if pl.dead or pl.attack is None or pl.attack_hit:
                        continue
                    hb = pl.hitbox()
                    if hb:
                        for e in self.enemies:
                            if e.dead:
                                continue
                            if hb.colliderect(e.rect):
                                dmg, _ = pl.attack_damage()
                                e.take_hit(dmg, pl.facing, e.now_blocking)
                                self.score += 100         # очки за попадание
                                pl.attack_hit = True      # один удар за анимацию
                                break

            # Атаки врагов по игрокам
            for e in self.enemies:
                if e.dead or e.attack is None or e.attack_hit:
                    continue
                hb = e.hitbox()
                if hb:
                    for pl in players:
                        if pl.dead:
                            continue
                        if hb.colliderect(pl.rect):
                            dmg, _ = e.attack_damage()
                            pl.take_hit(dmg, e.facing, pl.now_blocking)
                            e.attack_hit = True
                            break

            # Контакты игрок-враг (прыжок сверху сбивает врага)
            for e in self.enemies:
                if e.dead:
                    continue
                for pl in players:
                    if pl.dead:
                        continue
                    if pl.rect.colliderect(e.rect):
                        if pl.vel_y > 0 and pl.on_ground is False:
                            e.take_hit(30, 0)             # удар ногами с воздуха
                            pl.vel_y = -10                # отскок
                        else:
                            pl.x += -pl.facing * 4        # столкновение — небольшой откат
                            if pl.now_blocking:
                                pl.x += -pl.facing * 2    # блок сильнее держит позицию

            # Враг не может выйти за камеру глубоко влево и вправо за уровень
            for e in self.enemies:
                e.x = max(self.cam, min(e.x, LEVEL_LEN - e.w))

    # def bump_world(self, ent):
    #     """Расталкивание с бочками (БОЧКИ СЕЙЧАС ВЫКЛЮЧЕНЫ)."""
    #     for b in self.barrels:
    #         if not b.dead and ent.rect.colliderect(b.rect):
    #             if ent.x < b.x:
    #                 ent.x = b.x - ent.w
    #             else:
    #                 ent.x = b.x + 40

    def draw(self):
        """Отрисовка кадра: фон, персонажи, интерфейс, экраны конца партии."""
        if self.state == "title":
            self.draw_title()
            return
        if self.state == "intro":
            self.draw_level_intro()
            return
        if self.frame == 1:
            print(f"[DEBUG] draw: state={self.state}, level_bg={self.level_bg.get_size() if self.level_bg else 'None'}")
        self.screen.fill(SKY)
        cam = self.cam

        for i in range(len(self.sky_blocks())):
            pass                       # заглушка (небо рисуется через фон)

        # Фон: параллакс из двух слоёв (back=0.5 камеры, front=1.0)
        if self.par_ok and (self.par_backs or self.par_front is not None):
            # Каждый слой прижимаем к низу экрана со сдвигом -130 (по его высоте)
            def layer_y(im):
                return HEIGHT - im.get_height() - 130
            def draw_layer(im, off):
                y = layer_y(im)
                # Чёрные полосы сверху и снизу
                if y > 0:
                    pygame.draw.rect(self.screen, BLACK, (0, 0, WIDTH, y))
                bottom = y + im.get_height()
                if bottom < HEIGHT:
                    pygame.draw.rect(self.screen, BLACK, (0, bottom, WIDTH, HEIGHT - bottom))
                self.draw_loop_image(im, off, y)      # по кругу, но только видимый кусок
            # Задний слой: движется медленнее камеры
            if self.par_backs:
                kind, pic = self.par_backs[self.par_back_idx][1:]
                if kind == "anim":
                    pic = self.get_anim_frames(self.par_back_idx, pic)
                    if not pic:
                        pic = None
                    else:
                        pic = pic[(self.frame // ANIM_STEP) % len(pic)]
                if pic is not None:
                    draw_layer(pic, int(cam * 0.7))
            # Первый слой: движется 1:1 с камерой
            if self.par_front is not None:
                draw_layer(self.par_front, cam)
        elif self.level_bg is not None:
            off = cam                  # смещение фона = камере (движение 1:1)
            bg_w = self.level_bg.get_width()
            bg_h = self.level_bg.get_height()
            y = HEIGHT - bg_h + getattr(self, 'level_bg_y', 0)  # прижать картинку к низу экрана
            # Черные полосы сверху и снизу (картинка не закрывает весь экран)
            if y > 0:
                pygame.draw.rect(self.screen, BLACK, (0, 0, WIDTH, y))
            bottom = y + bg_h
            if bottom < HEIGHT:
                pygame.draw.rect(self.screen, BLACK, (0, bottom, WIDTH, HEIGHT - bottom))
            # Рисуем фон от левого края уровня (x=0)
            self.screen.blit(self.level_bg, (-off, y))

        # Враги
        if not NO_ENEMIES:
            scale_rank = {"thug": 3, "bruiser": 4, "boss": 5}
            for e in self.enemies:
                self.draw_fighter(e, cam, e.kind, rank=scale_rank[e.kind])

        # Слой с объектами: за персонажем, едет 1:1 с камерой.
        # Положение не зависит от варианта пола — одинаково на всех фонах.
        if getattr(self, "trees_img", None) is not None:
            self.draw_loop_image(self.trees_img, cam, CHARACTER_FLOOR_Y - TREES_H)

        # Игроки
        for pl in self.players:
            if not pl.dead or pl.dead_fall < 15:
                self.draw_fighter(pl, cam, "player", rank=2)

        # Пол: всегда поверх главного персонажа, едет 1:1 с камерой.
        if self.floor_img is not None:
            self.draw_loop_image(self.floor_img, cam, self.floor_y)

        self.draw_hud()

        # Экран победы/поражения
        if self.state == "win":
            self.win_t += 1
            t = self.font_big.render("LEVEL CLEAR!", True, YELLOW)
            self.screen.blit(t, (WIDTH // 2 - t.get_width() // 2, 180))
            if self.win_t > 20:
                h = self.font_s.render("R — заново   Ctrl+R — перезапуск", True, WHITE)
                self.screen.blit(h, (WIDTH // 2 - h.get_width() // 2, 240))
        elif self.state == "lose":
            self.lose_t += 1
            t = self.font_big.render("GAME OVER", True, RED)
            self.screen.blit(t, (WIDTH // 2 - t.get_width() // 2, 180))
            if self.lose_t > 20:
                h = self.font_s.render("R — заново   Ctrl+R — перезапуск", True, WHITE)
                self.screen.blit(h, (WIDTH // 2 - h.get_width() // 2, 240))

    def sky_blocks(self):
        return []                      # заглушка (небо рисуется фоном)

    def draw_title(self):
        """Главное меню: заставка + выбор режима (1 или 2 игрока)."""
        self.screen.fill((0, 0, 0))
        img = self.title_img
        if img is not None:
            th = 660
            tw = int(img.get_width() * th / img.get_height())
            scaled = pygame.transform.smoothscale(img, (tw, th))
            self.screen.blit(scaled, ((WIDTH - tw) // 2, 20))
        else:
            # Текстовый заголовок, если картинки нет
            t = self.font_big.render("TOADS vs DRAGON", True, YELLOW)
            self.screen.blit(t, (WIDTH // 2 - t.get_width() // 2, 160))

        # Пункты меню
        sel = self.mode_sel
        for i, label in enumerate(["1 ИГРОК", "2 ИГРОКА"]):
            c = YELLOW if i == sel else (200, 200, 210)
            s = self.pixel_font_ru.render(" " + label, True, c)
            sx = WIDTH // 2 - s.get_width() // 2
            if i == 0:
                sx -= 10               # выравнивание первой строки
            sy = 656 + i * 36
            self.screen.blit(s, (sx, sy))
            if i == sel and self.choose_img is not None:   # стрелка у выбранного пункта
                cy = sy + 7
                self.screen.blit(self.choose_img, (WIDTH // 2 - self.choose_img.get_width() - 88, cy))

        # Мигающая подсказка "ENTER — НАЧАТЬ"
        if (self.frame // 15) % 2 == 0:
            s = self.pixel_font_ru.render("ENTER — НАЧАТЬ", True, (137, 223, 255))
            self.screen.blit(s, (WIDTH // 2 - s.get_width() // 2, 736))

        # Подсказка по навигации
        hint = self.pixel_font_ru.render(
            "W/S или ↑/↓ — выбор   ESC — выход",
            True, (180, 180, 190))
        self.screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, 816))

    def draw_fighter(self, f, cam, variant, rank):
        """Отрисовка бойца спрайтом бега — единственная анимация на текущем этапе.
        В движении кадры идут по кругу, в покое показывается первый кадр."""
        x = int(f.x - cam)
        y = int(f.y)
        if y < -20 or x < -100 or x > WIDTH + 100:
            return                     # персонаж вне экрана — не рисуем
        if getattr(f, "dead", False) or not self.run_frames:
            return                     # мёртвых и без спрайтов не рисуем
        if f.was_moving:
            frame = self.run_frames[(self.frame // 2) % len(self.run_frames)]
        else:
            frame = self.run_frames[0]
        th = int(82 * f.scale)          # высота спрайта = рост стоящего бойца
        tw = max(1, int(frame.get_width() * th / frame.get_height()))
        img = pygame.transform.scale(frame, (tw, th))
        if f.facing < 0:
            img = pygame.transform.flip(img, True, False)
        sx = x + (f.w - tw) // 2      # центрируем по хитбоксу
        sy = y + f.h - th             # низ спрайта на линии пола
        self.screen.blit(img, (sx, sy))

    def draw_hud(self):
        """Верхняя панель: полоски здоровья, счёт, прогресс, подсказка управления."""
        pygame.draw.rect(self.screen, BLACK, (0, 0, WIDTH, 52))
        xs = [10, 340]                 # позиции баров здоровья P1 и P2
        for i, pl in enumerate(self.players):
            base = xs[i]
            hi = max(0, pl.hp)
            c1 = GREEN if i == 0 else (110, 170, 255)
            pygame.draw.rect(self.screen, GRAY, (base, 8, 200, 12))
            pygame.draw.rect(self.screen, c1, (base, 8, 200 * hi / MAX_HP, 12))
            t = self.font_s.render(f"P{i+1} {int(hi)}/{MAX_HP}", True, WHITE)
            self.screen.blit(t, (base, 2))

        # Счёт
        sc = self.font_m.render(f"SCORE {self.score}", True, YELLOW)
        self.screen.blit(sc, (WIDTH // 2 - sc.get_width() // 2, 2))

        # Прогресс по уровню
        prog = self.font_s.render("PROGRESS", True, GRAY)
        self.screen.blit(prog, (WIDTH - 150, 2))
        pygame.draw.rect(self.screen, GRAY, (WIDTH - 90, 8, 80, 10))
        right = max(pl.x for pl in self.players)
        frac = min(1, max(0, (right - 100) / (LEVEL_LEN - WIDTH)))
        pygame.draw.rect(self.screen, YELLOW, (WIDTH - 90, 8, int(80 * frac), 10))

        # Подсказка управления (зависит от режима)
        if self.num_players == 1:
            hl = "←→/AD — идти   ↑/W — прыжок  ↓/S — блок   Z/J — кулак   X/K — нога   R — заново   Ctrl+R — перезапуск   ESC — выход"
        else:
            hl = "P1: A/D·W·S·J/K     P2: ←→·↑·↓·N/M     R — заново   Ctrl+R — перезапуск   ESC — выход"
        hint = self.font_s.render(hl, True, WHITE)
        self.screen.blit(hint, (10, HEIGHT - 20))

        # Название активного заднего слоя параллакса (правый нижний угол)
        if self.par_back_name:
            bn = self.font_s.render(
                f"ФОН: {self.par_back_name} (E)   СЛОЙ 1: {self.par_first_name} (Q)"
                f"   ПОЛ: {self.floor_name} (F)", True, YELLOW)
            self.screen.blit(bn, (WIDTH - bn.get_width() - 10, HEIGHT - 20))


if __name__ == "__main__":
    Game().run()