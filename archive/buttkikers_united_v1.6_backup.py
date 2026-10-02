# BEAT-EM-UP «TOADS vs DRAGON»
# Скрипт игры на pygame. Запуск: launch.pyw (pythonw, без окна консоли)
# Управление:
#   P1: A/D — идти, W — прыжок, S — блок, J — кулак, K — нога
#   P2: ←/→, ↑, ↓, N/M
#   R — заново, Ctrl+R — перезапуск скрипта, Q — смена фона уровня, ESC — выход
import os
import random
import subprocess
import sys

import pygame

# --- Настройки окна и мира ---
WIDTH, HEIGHT = 1200, 880   # размер экрана в пикселях
FPS = 60                    # кадров в секунду
FLOOR_Y = 620               # "пол" для фона/декораций (нижняя граница картинки фона)
CHARACTER_FLOOR_Y = 690     # линия, на которой стоят персонажи
LEVEL_LEN = 6000            # длина уровня по оси X
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
        self.audio_ok = False          # музыка не подключается (mixer не инициализируется)
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
        self.par_front = None         # передний слой (скорость 1.0 = камера)
        self.par_back_idx = 0         # индекс активного заднего слоя в par_backs
        self.par_ok = False           # загрузились ли слои параллакса
        self.use_parallax = True      # сейчас включён только параллакс-уровень
        self.load_parallax()
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

    def load_parallax(self):
        """Загружает параллакс: задние слои (движутся медленнее камеры, переключение
        клавишей E) и передний слой (front, скорость 1.0). Файлы берутся из папки screen."""
        base = os.path.dirname(os.path.abspath(__file__))
        self.par_backs = []
        self.par_front = None
        self.par_ok = False
        for nm in ("back.png", "backnew.png", "backnew-HALF.png", "4-HALF.png"):
            p = os.path.join(base, "screen", nm)
            if os.path.exists(p):
                try:
                    self.par_backs.append((nm, pygame.image.load(p).convert_alpha()))
                except pygame.error:
                    pass
        front = os.path.join(base, "screen", "Paralax-frontCON.png")
        if os.path.exists(front):
            try:
                self.par_front = pygame.image.load(front).convert_alpha()
            except pygame.error:
                self.par_front = None
        if self.par_backs:
            self.par_back_idx %= len(self.par_backs)
            self.par_back_name = self.par_backs[self.par_back_idx][0]
        else:
            self.par_back_name = ""
        if self.par_backs or self.par_front is not None:
            self.par_ok = True

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

    def load_level_bg(self):
        """Загрузка фона текущего уровня.
        Параллакс включён (use_parallax) — грузятся слои back/front;
        иначе — простой фон по level_sel (0/1/2, сейчас отключено)."""
        if self.use_parallax:
            print(f"[DEBUG] load_level_bg: загружаю параллакс (back/front)")
            self.load_parallax()
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
                    if event.key == pygame.K_q:               # Q — перезагрузка фона (параллакс / уровень)
                        print(f"[DEBUG] Q pressed, level_sel={self.level_sel} -> {(self.level_sel + 1) % 3} use_parallax={self.use_parallax}")
                        if self.use_parallax:
                            self.load_parallax()              # перезагружаем слои параллакса
                        else:
                            self.level_sel = (self.level_sel + 1) % 3
                            self.load_level_bg()
                        print(f"[DEBUG] After load_level_bg: level_bg={self.level_bg}, size={self.level_bg.get_size() if self.level_bg else None}")
                    if self.state == "title":                 # навигация в главном меню
                        if event.key in (pygame.K_UP, pygame.K_w):
                            self.mode_sel = (self.mode_sel - 1) % 2
                        elif event.key in (pygame.K_DOWN, pygame.K_s):
                            self.mode_sel = (self.mode_sel + 1) % 2
                        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE, pygame.K_z):
                            print(f"[DEBUG] ENTER pressed, level_sel={self.level_sel}")
                            self.reset(self.mode_sel + 1)
                            print(f"[DEBUG] After reset, level_bg={'loaded' if self.level_bg else 'None'}")
                            self.state = "play"
                            print(f"[DEBUG] State changed to: {self.state}")
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.state == "title":
                    self.reset(self.mode_sel + 1)             # клик мышью — тоже начать
                    self.state = "play"

            self.frame += 1
            self.update()

            if self.audio_ok and not pygame.mixer.music.get_busy():
                pygame.mixer.music.play(-1)                   # (заглушка; музыка не активна)

            self.draw()
            pygame.display.flip()
            self.clock.tick(FPS)

    def update(self):
        """Обновление всего мира: камера, игроки, спавн и поведение врагов, коллизии."""
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
                w = im.get_width()
                x = off % w
                # тайлим слой влево, чтобы показывалась правильная часть
                for tx in range(-w, WIDTH + w, w):
                    self.screen.blit(im, (tx - x, y))
            # Задний слой: движется медленнее камеры
            if self.par_backs:
                draw_layer(self.par_backs[self.par_back_idx][1], int(cam * 0.7))
            # Передний слой: движется 1:1 с камерой
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

        # Игроки
        for pl in self.players:
            if not pl.dead or pl.dead_fall < 15:
                self.draw_fighter(pl, cam, "player", rank=2)

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
            bn = self.font_s.render(f"ФОН: {self.par_back_name}  (E — смена)", True, YELLOW)
            self.screen.blit(bn, (WIDTH - bn.get_width() - 10, HEIGHT - 20))


if __name__ == "__main__":
    Game().run()