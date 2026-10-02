# BEAT-EM-UP «TOADS vs DRAGON»
# Скрипт игры на pygame. Запуск: launch.pyw (pythonw, без окна консоли)
# Управление:
#   P1: A/D — идти, W — прыжок, S — блок, J — кулак, K — нога
#   P2: ←/→, ↑, ↓, N/M
#   R — заново, Ctrl+R — перезапуск скрипта, Q — изоляция фона, +/- — масштаб фона, ESC — выход
import os
import random
import subprocess
import sys

import pygame

# --- БАЗА ПРОЕКТА: видимая область (окно игры) ---
# Фиксированный размер окна, в котором видно всю игру. Это фундамент: он НЕ зависит
# ни от одного фона, слоя, полосы или спрайта и не пересчитывается вместе с ними.
# Все координаты Y ниже — абсолютные пиксели экрана, они заданы своими числами
# и от окна не отталкиваются. Менять VIEW_W/VIEW_H здесь ничего не пересчитает:
# если окно изменится, остальные константы правят вручную и по одной.
VIEW_W, VIEW_H = 1200, 880  # видимая область игры, px
WIDTH, HEIGHT = VIEW_W, VIEW_H   # короткие имена — их использует весь код ниже

# --- Настройки мира ---
FPS = 60                    # кадров в секунду
ANIM_STEP = 8               # сколько кадров игры показывается одна картинка анимации фона
# Папка внутри screen/back, картинки в которой меняются по таймеру в реальном времени
# (например 99_seasons — сезонные фоны). Остальные анимации фона живут по ANIM_STEP.
SEASONS_DIR = "99_seasons"  # папка с картинками, которые меняются по таймеру
SEASONS_TIME = 1          # секунд на одну картинку из SEASONS_DIR; 0 — по ANIM_STEP
RUN_ALT_DIR = "sprites/char/run"   # анимированный .png отсюда — спрайт бега (первый по порядку; остальные игнорируем — переключение бега удалено)
JUMP_DIR = "sprites/char/jump"     # анимированный .png прыжка (APNG); None/пусто — спрайт бега
IDLE_DIR = "sprites/char/iddle"    # анимированный .png простоя (APNG); None/пусто — спрайт бега
PUNCH_DIR = "sprites/char/punch"   # анимированный .png удара рукой (APNG); None/пусто — спрайт бега
MMA_DIR = "sprites/char/mma"       # анимированный .png удара ногой (APNG); None/пусто — спрайт бега
IDLE_ANIM_FPS = 10           # скорость анимации простоя, кадров анимации в секунду
ATTACK_ANIM_FPS = 30         # скорость анимаций ударов (во всех APNG ровно 30 fps)
CHAR_SPRITE_SCALE = 1.5         # общий масштаб спрайтов бойцов: 1.0 — как есть, 1.5 — в полтора раза
RUN_SPRITE_SCALE = 0.96          # множитель масштаба только для спрайта бега (правится здесь)
RUN_SPRITE_DX = -10             # сдвиг спрайта бега по X, px (вместе со знаком по направлению взгляда)
JUMP_SPRITE_SCALE = 0.98         # множитель масштаба только для спрайта прыжка (правится здесь)
JUMP_SPRITE_DX = -20            # сдвиг спрайта прыжка по X, px (вместе со знаком по направлению взгляда)
CHAR_SPRITE_H = 82              # высота спрайта бойца в пикселях (до применения CHAR_SPRITE_SCALE)
FOOTSTEP_TIME = 20             # кадров между шагами (цикл бега 40 кадров → шаг каждые 20)

# --- Настройки звука ---
SOUND_ON = False             # главный выключатель: False — глушит всё (музыку и звуки)
MUSIC_ON = True             # True — фоновая музыка, False — без неё
MUSIC_FILE = "start-redused-noise.wav"   # трек фоновой музыки в меню (папка mus)
MUSIC_VOL = 1             # громкость фоновой музыки: трек меню
LEVEL_MUSIC = "sounds/lev1_forest.mp3"   # трек первого уровня (играет только в игре)
LEVEL_MUSIC_VOL = 0.6       # громкость фоновой музыки: трек уровня
MUSIC_FADE_STEP = 0.03      # насколько громкость меняется за кадр (0.03 → примерно 0.5 с)
SFX_ON = True                # True — проигрывать звуки нажатий, False — без них
SFX_START = "start nes-sfx29.wav"       # звук нажатия START (папка sounds)
SFX_START_VOL = 0.3         # громкость звука нажатия START
SFX_MENU = "menu nes-sfx23.wav"         # звук навигации в меню (папка sounds)
SFX_FOOTSTEP = "Footstep__005.wav"      # звук шагов (папка sounds)

# --- Настройки уровней и слоёв ---
# Все Y ниже — абсолютные координаты экрана, не производные от размера окна.
CHARACTER_FLOOR_Y = 625     # линия, на которой стоят персонажи (и базовая линия пола)
LEVEL_LEN = 20000            # длина уровня по оси X
FLOOR_Y = 680               # "пол" для фона/декораций (нижняя граница картинки фона)
FLOOR_LEVEL = {
    "fl1": 610,
    "fl2": 610,
}                            # Y сплошной поверхности пола по вариантам; нет ключа — авто
FLOOR_OVERLAP = {"fl2": 100}  # нахлёст картинок при склейке варианта пола
FLOOR_ON = True             # пол
FLOOR_DIR = "sprites/floor"  # каждая вложенная папка — один вариант пола, F
FLOOR_PARALLAX = 1.0       # скорость пола: 1.0 — 1:1 с камерой

# --- Слои по порядку отрисовки: задний план → par 2 → par 1 → персонажи → lay 0 → пол ---
# Низ полосы каждого слоя привязан к общей линии LAYERS_Y. Флаги *_ON: False — слой
# не грузится и не рисуется совсем.
LAYERS_Y = 700              # линия привязки по высоте для всех слоёв
LAYERS_LIFT = 70            # подъём всех слоёв над LAYERS_Y (задний фон не затрагивается)
HUD_H = 88                  # высота чёрной панели внизу кадра: строка 1 — здоровье/счёт/прогресс,
                            # строка 2 — подсказка по клавишам, строка 3 — активные режимы
HUD_ON = False              # True — панель видна на старте, False — скрыта (клавиша Z — показать/скрыть)
BACK_ON = True              # задний план
BACK_DIR = "screen/back"   # картинки и папки-анимации (клавиша E)
BACK_SCALE = 1.0            # стартовый масштаб заднего плана: 1.0 — как есть, 0.5 — вдвое меньше.
                            # Фон рисуется как объект уровня: верх прижат к верхней границе
                            # окна, обрезки нет — не влезшее просто уходит за край экрана.
                            # Во время игры масштаб меняется клавишами +/- (см. ниже)
BACK_SCALE_STEP = 0.05      # шаг изменения масштаба клавишами +/- (5%)
BACK_SCALE_MIN = 0.05       # нижняя граница масштаба (1/20 натуральной величины)
BACK_SCALE_MAX = 10.0       # верхняя граница масштаба (x10)
BACK_PARALLAX = 0.05        # скорость заднего плана: 1.0 — 1:1 с камерой
BACK_FALLBACK = ("back.png", "river", "night river", "colorized")  # порядок без префикса

# --- Режим изоляции заднего фона (клавиша Q) ---
# Когда включен, видны только три слоя: задний фон, персонажи и пол.
# Остальные (par 1, par 2, lay 0, par NEW, враги, HUD) скрыты — удобно смотреть сам фон.
ISOLATE_ON = False          # True — изоляция включена сразу при запуске партии
# Слои par 1, par 2 и lay 0 собираются одинаково (build_strip): картинки склеиваются в
# полосу, <номер> — порядок, _<сдвиг> — сдвиг по вертикали (со знаком).
PAR1_ON = True              # слой 1
PAR1_DIR = "screen/par1"   # объекты между задним планом и персонажами
PAR1_H = 650               # минимальная высота полосы (None — не рисовать)
PAR1_PARALLAX = 1.0        # скорость слоя 1: 1.0 — 1:1 с камерой
PAR2_ON = True              # слой 2
PAR2_DIR = "screen/par 2"
PAR2_H = 680               # минимальная высота полосы (None — не рисовать)
PAR2_PARALLAX = 0.7        # скорость слоя 2: 1.0 — 1:1 с камерой
LAY0_ON = True              # слой 0
LAY0_DIR = "screen/lay 0"   # рисуется последним, поверх пола и персонажей
LAY0_H = 768               # минимальная высота полосы (None — не рисовать)
LAY0_PARALLAX = 1.0        # скорость слоя 0: 1.0 — 1:1 с камерой
        # par NEW: рисуется последним, поверх всех остальных слоёв, включая пол.
        # Слой самодостаточный: работает даже если прочие слои выключены, поэтому
        # par_ok (общий признак загруженных фонов) он не трогает.
# Правила те же, что у слоёв выше: build_strip, <номер> — порядок, _<сдвиг> — сдвиг по вертикали.
PARNEW_ON = True            # слой par NEW
PARNEW_DIR = "screen/par NEW"
PARNEW_H = 680              # минимальная высота полосы (None — не рисовать)
PARNEW_PARALLAX = 1.5       # скорость слоя: 1.0 — 1:1 с камерой, 1.5 — в полтора раза быстрее

# --- Настройки переходов и эффектов ---
TRANSITION = "blink"         # переход при старте: "blink" — мигание, "wipe" — диагональный вайп
TRANS_TIME = 2              # кадров на переход
BLINK_CYCLE = 10             # кадров на цикл мигания (половина — темно, половина — картинка)
BLINK_STEP = 70              # насколько темнеет картинка за цикл (0..255)
FADE_PIXEL = 20              # размер блока «пикселя» ретро-эффекта (вайп и проявление)
REVEAL_TIME = 15            # кадров на проявление уровня из темноты
INTRO_TIME = 20             # кадров на чёрный экран с названием уровня (2 секунды)
LEVEL_NUM = "УРОВЕНЬ ПЕРВЫЙ"   # номер уровня на заставке
LEVEL_NAME = "ДОРОГА В РАЙ"    # название уровня на заставке
GRAVITY = 2.0               # ускорение свободного падения
MOVE = 12.0                  # скорость ходьбы
# Прыжок. Вертикального перемещения нет: прыжок целиком нарисован в самой анимации
# jump.png, поэтому боец остаётся на линии пола и по вертикали не сдвигается.
# Задаётся только длина прыжка — сколько боец пролетает по горизонтали за время анимации.
# Длительность задаёт сама анимация (JUMP_ANIM_FPS), поэтому скорость зависит от длины:
#   скорость в прыжке = JUMP_LEN / jump_duration()
#   длина под скорость ходьбы = MOVE * jump_duration()  (сейчас 12 * 62 = 744 px)
# Возьмёшь длину меньше — прыжок поедет медленнее ходьбы и будет выглядеть как замедление.
JUMP_LEN = 744               # длина прыжка, px (0 — прыжок выключен)
JUMP_ANIM_FPS = 30           # скорость проигрывания анимации прыжка, кадров/с (как в самом PNG)
JUMP_COOLDOWN = 1.5          # секунд между прыжками: кулдаун от взлёта до следующего; 0 — без ограничения
ENEMY_JUMP_RATIO = 0.8       # во сколько раз короче прыжок врага
JUMP_COOLDOWN_FRAMES = int(round(JUMP_COOLDOWN * FPS))      # кулдаун в кадрах
JUMP_ANIM_N = 0              # кадров в загруженной анимации прыжка; заполняется при загрузке
RUN_ANIM_N = 0               # кадров в загруженной анимации бега; заполняется при загрузке
PUNCH_ANIM_N = 0             # кадров в загруженной анимации удара рукой; 0 — анимации нет
PUNCH_FALLBACK = 7           # длительность удара в кадрах, если анимация не загрузилась
MMA_ANIM_N = 0               # кадров в загруженной анимации удара ногой; 0 — анимации нет
KICK_FALLBACK = 12           # длительность удара ногой в кадрах, если анимации нет


def jump_duration(anim_n=0):
    """Длительность прыжка в кадрах игры.

    Анимация проигрывается со своей скоростью JUMP_ANIM_FPS, поэтому прыжок длится ровно
    столько, сколько нужно на всю анимацию: n / JUMP_ANIM_FPS секунд. Именно она задаёт
    длительность прыжка, а не наоборот.
    """
    n = anim_n or JUMP_ANIM_N
    if n <= 0:
        return max(1, int(round(FPS * 0.5)))     # анимации нет — прыжок на полсекунды
    return max(1, int(round(n / JUMP_ANIM_FPS * FPS)))


def attack_duration(anim_n=0):
    """Длительность удара в кадрах игры.

    Как и прыжок: анимация проигрывается со своей скоростью ATTACK_ANIM_FPS, поэтому удар
    длится ровно столько, сколько нужно на всю анимацию — n / ATTACK_ANIM_FPS секунд.
    Без этого кадры шли бы по одному на игровой кадр и удар был бы вдвое быстрее.
    """
    if anim_n <= 0:
        return 1
    return max(1, int(round(anim_n / ATTACK_ANIM_FPS * FPS)))


MAX_HP = 100                # максимальное здоровье игрока
NO_ENEMIES = True           # True — враги отключены (режим "чистого раннера")

SKY = (30, 26, 46)
PLAYER = (70, 200, 90)
PLAYER2 = (90, 150, 235)
THUG = (190, 90, 90)
BRUISER = (140, 70, 200)
BOSS = (200, 60, 60)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (220, 40, 40)
YELLOW = (255, 225, 60)
GREEN = (70, 200, 90)
GRAY = (150, 150, 150)


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
        self.jump_frame = 0            # текущий кадр анимации прыжка
        self.jump_cd = 0               # оставшиеся кадры кулдауна до следующего прыжка
        self.jumping = False           # идёт ли прыжок (анимация проигрывается)
        self.jump_t = 0                # кадров игры с начала прыжка
        self.jump_dur = 0              # сколько кадров длится прыжок (вся анимация)
        self.jump_n = 0                # кадров в анимации этого прыжка
        self.jump_speed = 0.0          # горизонтальная скорость во время прыжка, px/кадр
        self.run_phase = 0             # сдвиг фазы бега: вход в анимацию всегда с 0-го кадра
        self.idle_phase = 0            # сдвиг фазы анимации простоя (свой у каждого игрока)
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

    @property
    def attack_progress(self):
        """Прогресс текущей атаки от 0 (начало) до 1 (конец) — для выбора кадра анимации."""
        if self.attack is None:
            return 0.0
        dur = (attack_duration(PUNCH_ANIM_N or PUNCH_FALLBACK) if self.attack == "punch"
               else attack_duration(MMA_ANIM_N or KICK_FALLBACK))
        left = max(0, self.attack_timer)
        return min(1.0, max(0.0, 1.0 - left / dur))

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
        # Длительность удара = длина анимации по её собственной скорости (attack_duration),
        # иначе кадры шли бы по одному на игровой кадр и удар был бы вдвое быстрее.
        self.attack_timer = (attack_duration(PUNCH_ANIM_N or PUNCH_FALLBACK)
                             if kind == "punch"
                             else attack_duration(MMA_ANIM_N or KICK_FALLBACK))
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

    def start_jump(self, length):
        """Начать прыжок на length px.

        По вертикали не двигаемся: прыжок целиком нарисован в анимации, боец остаётся на
        линии пола. Длительность прыжка задаёт сама анимация (JUMP_ANIM_FPS), а скорость
        подбирается так, чтобы за это время боец пролетел ровно length px.
        """
        self.jumping = True
        self.jump_t = 0
        self.jump_n = JUMP_ANIM_N
        self.jump_dur = jump_duration(self.jump_n)
        self.jump_speed = length / self.jump_dur
        self.jump_frame = 0
        self.vel_y = 0

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
        if self.jump_cd > 0:           # отсчёт кулдауна между прыжками
            self.jump_cd -= 1

        if self.jumping:
            # Прыжок: по вертикали не двигаемся — всё перемещение нарисовано в анимации.
            # Идёт только таймер и смена кадра анимации со своей скоростью JUMP_ANIM_FPS.
            self.vel_y = 0
            self.on_ground = True
            self.jump_t += 1
            if self.jump_t >= self.jump_dur:     # анимация доиграла — приземление
                self.jumping = False
                self.jump_t = 0
                self.jump_frame = 0
                # Фаза бега сдвигается так, чтобы сразу после приземления на экране
                # был 0-й кадр бега, а не случайный кадр цикла.
                self.run_phase = -(frame // 2) % max(1, RUN_ANIM_N)
            else:
                last = self.jump_n - 1 if self.jump_n > 0 else 0
                self.jump_frame = min(last, int(self.jump_t * JUMP_ANIM_FPS / FPS))
        else:
            self.vel_y += GRAVITY         # гравитация
            self.y += self.vel_y
            if self.y >= CHARACTER_FLOOR_Y - self.h:
                self.y = CHARACTER_FLOOR_Y - self.h
                self.vel_y = 0
                self.on_ground = True
            else:
                self.on_ground = False

        # Время удара персонаж стоит на месте: горизонтальное движение не применяется.
        if self.attack is None:
            self.was_moving = abs(self.vel_x) > 0.05
            self.x += self.vel_x      # горизонтальное движение
        else:
            self.was_moving = False
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
        self.idle_phase = pnum * 5  # сдвиг фазы простоя: у P2 анимация с другого кадра
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
            punch = keys[pygame.K_j]           # Z свободен: переключает нижнюю панель
            kick = keys[pygame.K_x] or keys[pygame.K_k]
        else:                                    # P1 в кооперативе: только WASD + J/K
            left = keys[pygame.K_a]
            right = keys[pygame.K_d]
            up = keys[pygame.K_w]
            down = keys[pygame.K_s]
            punch = keys[pygame.K_j]
            kick = keys[pygame.K_k]

        self.crouching = False
        if self.attack is not None:
            # Время удара персонаж стоит на месте: бег, прыжок и присед не действуют.
            self.vel_x = 0
            self.was_moving = False
            return
        if self.flinch <= 0:                     # в отшатывании игрок неуправляем
            # на земле — скорость ходьбы, в прыжке — скорость, посчитанная из длины прыжка
            spd = self.jump_speed if self.jumping else MOVE
            if left:
                self.vel_x = -spd
                self.facing = -1
                self.moved += 1
            elif right:
                self.vel_x = spd
                self.facing = 1
                self.moved += 1
            if up and not self.jumping and not self.jump_cd and JUMP_LEN > 0:
                # прыжок: спрайт по вертикали не двигается, летит только по горизонтали
                self.start_jump(JUMP_LEN)
                self.jump_cd = JUMP_COOLDOWN_FRAMES
            if down:
                self.crouching = True            # присед = блокировка
                self.now_blocking = True
            if punch and not self.jumping:
                # удар рукой только с земли: в прыжке персонаж не бьёт кулаком
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
                elif random.random() < 0.3 and not self.jumping:
                    self.start_jump(JUMP_LEN * ENEMY_JUMP_RATIO)   # враг прыгает на игрока
        else:                                    # пограничная зона — подкрадываемся
            self.vel_x = self.facing * min(self.speed, dist * 0.1)


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
        self.music_name = ""           # имя играющего трека ("" — уровень ещё не начинал)
        if self.audio_ok and MUSIC_ON:
            try:
                pygame.mixer.music.load(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                     "mus", MUSIC_FILE))
                pygame.mixer.music.set_volume(MUSIC_VOL if SOUND_ON else 0.0)
                self.music_ok = True
            except pygame.error:
                self.music_ok = False
        self.level_music_ok = False    # трек уровня загружен
        if self.audio_ok and MUSIC_ON and LEVEL_MUSIC:
            path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                *LEVEL_MUSIC.replace("\\", "/").split("/"))
            if os.path.exists(path):
                try:
                    self.level_music = pygame.mixer.Sound(path)
                    self.level_music.set_volume(LEVEL_MUSIC_VOL if SOUND_ON else 0.0)
                    self.level_music_ok = True
                except pygame.error:
                    self.level_music_ok = False
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
        global RUN_ANIM_N
        RUN_ANIM_N = len(self.run_variants[0][1]) if self.run_variants else 0
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
        global JUMP_ANIM_N
        JUMP_ANIM_N = len(self.jump_frames)
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
                    frames = self.trim_frames(self.load_apng_frames(full))
                    if frames:
                        self.punch_name, self.punch_frames = name, frames
                        break
        global PUNCH_ANIM_N
        PUNCH_ANIM_N = len(self.punch_frames)
        if self.punch_frames:
            print(f"[DEBUG] удар рукой: {self.punch_name} — {PUNCH_ANIM_N} кадров "
                  f"@ {ATTACK_ANIM_FPS} fps, длительность удара "
                  f"{attack_duration(PUNCH_ANIM_N)} кадр "
                  f"({attack_duration(PUNCH_ANIM_N) / FPS:.2f} с)")
        else:
            print("[DEBUG] удар рукой: анимация не найдена, длительность удара "
                  f"{PUNCH_FALLBACK} кадр")
        # Анимация удара ногой: то же самое, но из папки MMA_DIR.
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
                    frames = self.trim_frames(self.load_apng_frames(full))
                    if frames:
                        self.mma_name, self.mma_frames = name, frames
                        break
        global MMA_ANIM_N
        MMA_ANIM_N = len(self.mma_frames)
        if self.mma_frames:
            print(f"[DEBUG] удар ногой: {self.mma_name} — {MMA_ANIM_N} кадров "
                  f"@ {ATTACK_ANIM_FPS} fps, длительность удара "
                  f"{attack_duration(MMA_ANIM_N)} кадр "
                  f"({attack_duration(MMA_ANIM_N) / FPS:.2f} с)")
        else:
            print("[DEBUG] удар ногой: анимация не найдена, длительность удара "
                  f"{KICK_FALLBACK} кадр")
        dur = jump_duration()
        spd = JUMP_LEN / dur if dur else 0
        print(f"[DEBUG] прыжок: длина {JUMP_LEN} px, анимация {JUMP_ANIM_FPS} fps -> "
              f"длительность {dur / FPS:.2f} с ({dur} кадр), "
              f"скорость {spd:.1f} px/кадр (ходьба {MOVE:.1f}"
              f"{', прыжок быстрее' if spd > MOVE else ', прыжок медленнее' if spd < MOVE else ''}), "
              f"кулдаун {JUMP_COOLDOWN:.2f} с"
              + (f", кадров в анимации {JUMP_ANIM_N}" if JUMP_ANIM_N else ", анимации нет"))
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
        self.back_scale = BACK_SCALE    # текущий масштаб заднего фона (меняется клавишами +/-)
        self.isolate = ISOLATE_ON     # режим изоляции фона (Q): видны фон, персонаж и пол
        self.hud_on = HUD_ON          # панель показателей внизу (Z — переключить)
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
                    cut = 1 if Game.has_black_border(frame) else 0
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
        base = os.path.dirname(os.path.abspath(__file__))
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
                if kind == "anim":
                    self.par_backs.append((fn, kind, p))   # кадры читаем лениво
                    continue
                try:
                    pic = pygame.image.load(p)
                    pic = self.mirror_glue(pic)          # зеркалим и склеиваем для бесшовного тайлинга
                    self.par_backs.append((fn, kind, pic.convert()))
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
                items.append((Game.strip_order(name), fn, Game.strip_shift(name), 0))
            else:
                gap = Game.gap_width(name)              # не картинка: число в имени = зазор
                if gap:
                    items.append((Game.strip_order(name), fn, 0, gap))
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
        base = os.path.dirname(os.path.abspath(__file__))
        folder = os.path.join(base, *PAR1_DIR.replace("\\", "/").split("/"))
        self.par1_img, self.par1_pad = self.build_strip(folder, PAR1_H) \
            if PAR1_ON else (None, 0)

    def load_floors(self):
        """Читаем варианты пола из папки FLOOR_DIR (каждая вложенная папка — один вариант)."""
        base = os.path.dirname(os.path.abspath(__file__))
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
        self.par_backs[idx] = (f"{os.path.basename(folder)} ({len(frames)} кадра)", "anim", frames)
        if self.par_back_idx == idx:
            self.par_back_name = self.par_backs[idx][0]
        return frames

    def back_scaled(self, im):
        """Задний план, умноженный на текущий масштаб self.back_scale. Общий масштаб на обе
        оси, без обрезки. Результат кэшируем: пересчитываем только когда сменилась картинка
        или масштаб (иначе масштабировали бы огромную картинку каждый кадр)."""
        w, h = im.get_size()
        dw, dh = max(1, int(w * self.back_scale)), max(1, int(h * self.back_scale))
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

    def play_sfx(self, name):
        """Проигрывает короткий звук по имени (self.sfx) и громкости, заданной для START."""
        if not SOUND_ON:
            return
        snd = self.sfx.get(name)
        if snd is not None:
            snd.play()

    def update_footsteps(self, pl):
        """Шаги: звук каждые FOOTSTEP_TIME кадров, пока боец бежит по земле."""
        if pl.dead or pl.jumping or not pl.on_ground or not pl.was_moving:
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
        """Сброс партии: персонажи, камера, счёт, враги, слои параллакса."""
        print("[DEBUG] reset called")
        if players is None:
            players = getattr(self, "num_players", 1)
        self.num_players = players
        self.players = [Player(i, players) for i in range(players)]
        self.frame = 0
        self.cam = 0
        self.state = "title"           # состояния: title / play / win / lose
        self.score = 0
        self.enemies = []
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

    def start_level_reveal(self):
        """После заставки уровень проявляется из темноты (диагональным вайпом)."""
        self.state = "reveal"
        self.reveal_t = 0
        self.reveal_done = 0
        self.reveal_surface.fill((0, 0, 0, 255))   # первый кадр проявления — сразу темно

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
                    if event.key == pygame.K_e:                   # E — смена заднего слоя параллакса
                        if len(self.par_backs) > 1:
                            self.par_back_idx = (self.par_back_idx + 1) % len(self.par_backs)
                            self.par_back_name = self.par_backs[self.par_back_idx][0]
                            print(f"[DEBUG] E pressed, back layer -> {self.par_back_name}")
                        else:
                            print("[DEBUG] E pressed, но других задних слоёв нет")
                    if event.key == pygame.K_p and self.state == "play":   # P — пауза музыки
                        self.toggle_music_pause()
                    if event.key == pygame.K_f:               # F — смена варианта пола
                        if len(self.floors) > 1:
                            self.set_floor(self.floor_idx + 1)
                            print(f"[DEBUG] F pressed, пол -> {self.floor_name}")
                        else:
                            print("[DEBUG] F pressed, других вариантов пола нет")
                    if event.key in (pygame.K_EQUALS, pygame.K_KP_PLUS):   # +/- — масштаб заднего фона
                        self.back_scale = min(BACK_SCALE_MAX,
                                              round(self.back_scale + BACK_SCALE_STEP, 3))
                        print(f"[DEBUG] + масштаб фона: {self.back_scale:.2f}")
                    elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                        self.back_scale = max(BACK_SCALE_MIN,
                                              round(self.back_scale - BACK_SCALE_STEP, 3))
                        print(f"[DEBUG] - масштаб фона: {self.back_scale:.2f}")
                    if event.key == pygame.K_q:               # Q — режим изоляции фона
                        self.isolate = not self.isolate
                        print(f"[DEBUG] Q pressed, изоляция фона: {'ВКЛ' if self.isolate else 'ВЫКЛ'}")
                    if event.key == pygame.K_z and self.state not in ("title", "intro"):
                        # Z — показать/скрыть нижнюю панель (в меню Z по-прежнему запускает игру)
                        self.hud_on = not self.hud_on
                        print(f"[DEBUG] Z pressed, панель: {'ВКЛ' if self.hud_on else 'ВЫКЛ'}")
                    if event.key == pygame.K_F6:               # F6 — перезагрузка слоёв параллакса
                        self.load_parallax()
                        print(f"[DEBUG] F6 pressed, слои перезагружены, par_ok={self.par_ok}")
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
                            print("[DEBUG] ENTER pressed")
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
                if not self.trans_started:  # переход уже закончился (blink) — создаём уровень
                    self.trans_started = True
                    self.reset(self.trans_players)   # reset() ставит state="title", поэтому state — после
                    self.start_level_reveal()        # уровень проявляется из темноты
                else:                                # wipe — экран откроется сам
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

    def draw(self):
        """Отрисовка кадра: фон, персонажи, интерфейс, экраны конца партии."""
        if self.state == "title":
            self.draw_title()
            return
        if self.state == "intro":
            self.draw_level_intro()
            return
        self.screen.fill(SKY)
        cam = self.cam

        # Фон: задний план (BACK_SCALE, BACK_PARALLAX) и слой 2 (PAR2_PARALLAX)
        if self.par_ok and (self.par_backs or self.par2 is not None):
            # Задний слой: объект уровня, верх прижат к верхней границе окна (y = 0),
            # масштаб общий BACK_SCALE, обрезки нет. Движется медленнее камеры.
            if self.par_backs:
                name, kind, pic = self.par_backs[self.par_back_idx]
                if kind == "anim":
                    pic = self.get_anim_frames(self.par_back_idx, pic)
                    if not pic:
                        pic = None
                    elif SEASONS_TIME > 0 and name.startswith(SEASONS_DIR):
                        # Сезонные фоны: смена картинки по реальному времени,
                        # чтобы 3 секунды были настоящими, а не кадрами игры.
                        step = max(1, int(round(SEASONS_TIME * FPS)))
                        pic = pic[(self.frame // step) % len(pic)]
                    else:
                        pic = pic[(self.frame // ANIM_STEP) % len(pic)]
                if pic is not None:
                    self.draw_loop_image(self.back_scaled(pic), int(cam * BACK_PARALLAX), 0)

        # Слой 2: верхом полосы на LAYERS_Y - PAR2_H, базовая линия слоя — LAYERS_Y
        if self.par2 is not None and not self.isolate:
            self.draw_loop_image(self.par2, int(cam * PAR2_PARALLAX),
                                 self.layer_y(self.par2, PAR2_H, self.par2_pad))

        # Враги (в изоляции скрыты)
        if not NO_ENEMIES and not self.isolate:
            scale_rank = {"thug": 3, "bruiser": 4, "boss": 5}
            for e in self.enemies:
                self.draw_fighter(e, cam, e.kind, rank=scale_rank[e.kind])

        # Слой 1 (объекты из PAR1_DIR): за персонажем, скорость PAR1_PARALLAX.
        # Базовая линия слоя — общая LAYERS_Y, верх полосы — LAYERS_Y - PAR1_H.
        if getattr(self, "par1_img", None) is not None and not self.isolate:
            self.draw_loop_image(self.par1_img, int(cam * PAR1_PARALLAX),
                                 self.layer_y(self.par1_img, PAR1_H, self.par1_pad))

        # Игроки
        for pl in self.players:
            if not pl.dead or pl.dead_fall < 15:
                self.draw_fighter(pl, cam, "player", rank=2)

        # Слой 0: рисуется предпоследним, поверх персонажей и пола.
        # Базовая линия слоя — общая LAYERS_Y, верх полосы — LAYERS_Y - LAY0_H.
        if self.lay0_img is not None and not self.isolate:
            self.draw_loop_image(self.lay0_img, int(cam * LAY0_PARALLAX),
                                 self.layer_y(self.lay0_img, LAY0_H, self.lay0_pad))

        # Пол: перекрывает и персонажей, и слой 0.
        if self.floor_img is not None:
            self.draw_loop_image(self.floor_img, int(cam * FLOOR_PARALLAX), self.floor_y)

        # Слой par NEW: самый верхний слой, перекрывает и пол, и всё остальное.
        if getattr(self, "parnew_img", None) is not None and not self.isolate:
            self.draw_loop_image(self.parnew_img, int(cam * PARNEW_PARALLAX),
                                 self.layer_y(self.parnew_img, PARNEW_H, self.parnew_pad))

        if self.isolate:
            # Изоляция: чистый вид (фон + персонаж + пол), вместо HUD — панель с подсказкой
            if self.hud_on:
                top = HEIGHT - HUD_H
                pygame.draw.rect(self.screen, BLACK, (0, top, WIDTH, HUD_H))
                t = self.font_s.render("ИЗОЛЯЦИЯ ФОНА — Q (выйти)", True, YELLOW)
                self.screen.blit(t, (WIDTH // 2 - t.get_width() // 2, top + 36))
        elif self.hud_on:
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
        """Отрисовка бойца: в ударе — спрайт удара, в прыжке — спрайт прыжка,
        в движении — кадры бега по кругу, в покое — отдельная анимация простоя."""
        x = int(f.x - cam)
        y = int(f.y)
        scale = CHAR_SPRITE_SCALE    # общий масштаб спрайта; для бега свой множитель
        dx = 0                       # сдвиг спрайта по X; для бега свой, против направления взгляда
        if y < -20 or x < -100 or x > WIDTH + 100:
            return                     # персонаж вне экрана — не рисуем
        if getattr(f, "dead", False) or not self.run_frames:
            return                     # мёртвых и без спрайтов не рисуем
        if f.attack == "punch" and self.punch_frames:
            # Удар рукой: кадр анимации по прогрессу атаки. Номер кадра считает Fighter
            # через attack_progress, чтобы не тянуть лишние счётчики.
            idx = int(f.attack_progress * len(self.punch_frames))
            frame = self.punch_frames[min(max(0, idx), len(self.punch_frames) - 1)]
        elif f.attack == "kick" and self.mma_frames:
            # Удар ногой: своя анимация, кадр так же по прогрессу атаки.
            idx = int(f.attack_progress * len(self.mma_frames))
            frame = self.mma_frames[min(max(0, idx), len(self.mma_frames) - 1)]
        elif f.jumping and self.jump_frames:
            # В прыжке спрайт не смещается по вертикали — показываем кадр анимации,
            # номер которого Fighter считает по времени (JUMP_ANIM_FPS).
            frame = self.jump_frames[min(max(0, f.jump_frame), len(self.jump_frames) - 1)]
            scale *= JUMP_SPRITE_SCALE      # свой множитель масштаба для прыжка
            dx = JUMP_SPRITE_DX * f.facing     # спрайт прыжка смещён назад по направлению взгляда
        elif f.was_moving:
            # Фаза бега привязана к f.run_phase: он сдвигается при приземлении, чтобы
            # переход «прыжок -> бег» начинался с 0-го кадра, а не со случайного.
            frame = self.run_frames[((self.frame // 2) + f.run_phase) % len(self.run_frames)]
            scale *= RUN_SPRITE_SCALE       # свой множитель масштаба для бега
            dx = RUN_SPRITE_DX * f.facing     # и свой сдвиг назад по направлению взгляда
        elif self.idle_frames:
            # Стоим на месте: цикл простоя. Смещение f.idle_phase (у каждого игрока
            # своё), чтобы P1 и P2 не дышали синхронно.
            step = max(1, int(round(FPS / IDLE_ANIM_FPS)))
            frame = self.idle_frames[((self.frame // step) + f.idle_phase) % len(self.idle_frames)]
        else:
            frame = self.run_frames[0]
            scale *= RUN_SPRITE_SCALE       # запасной кадр — тоже спрайт бега
            dx = RUN_SPRITE_DX * f.facing
        th = max(1, int(CHAR_SPRITE_H * f.scale * scale))   # высота спрайта бойца на экране
        tw = max(1, int(frame.get_width() * th / frame.get_height()))
        img = pygame.transform.scale(frame, (tw, th))
        if f.facing < 0:
            img = pygame.transform.flip(img, True, False)
        sx = x + (f.w - tw) // 2 + dx  # центрируем по хитбоксу + сдвиг бега назад
        sy = y + f.h - th             # низ спрайта на линии пола
        self.screen.blit(img, (sx, sy))

    def draw_hud(self):
        """Чёрная панель внизу кадра: здоровье, счёт, прогресс, подсказки, активные режимы."""
        top = HEIGHT - HUD_H
        pygame.draw.rect(self.screen, BLACK, (0, top, WIDTH, HUD_H))
        xs = [10, 340]                 # позиции баров здоровья P1 и P2
        for i, pl in enumerate(self.players):
            base = xs[i]
            hi = max(0, pl.hp)
            c1 = GREEN if i == 0 else (110, 170, 255)
            pygame.draw.rect(self.screen, GRAY, (base, top + 8, 200, 12))
            pygame.draw.rect(self.screen, c1, (base, top + 8, 200 * hi / MAX_HP, 12))
            t = self.font_s.render(f"P{i+1} {int(hi)}/{MAX_HP}", True, WHITE)
            self.screen.blit(t, (base, top + 2))

        # Счёт
        sc = self.font_m.render(f"SCORE {self.score}", True, YELLOW)
        self.screen.blit(sc, (WIDTH // 2 - sc.get_width() // 2, top + 2))

        # Прогресс по уровню
        prog = self.font_s.render("PROGRESS", True, GRAY)
        self.screen.blit(prog, (WIDTH - 150, top + 2))
        pygame.draw.rect(self.screen, GRAY, (WIDTH - 90, top + 8, 80, 10))
        right = max(pl.x for pl in self.players)
        frac = min(1, max(0, (right - 100) / (LEVEL_LEN - WIDTH)))
        pygame.draw.rect(self.screen, YELLOW, (WIDTH - 90, top + 8, int(80 * frac), 10))

        # Подсказка управления (зависит от режима) — второй строкой панели, по центру
        if self.num_players == 1:
            hl = "←→/AD — идти   ↑/W — прыжок  ↓/S — блок   J — кулак   X/K — нога   Z — панель   R — заново   Ctrl+R — перезапуск   ESC — выход"
        else:
            hl = "P1: A/D·W·S·J/K     P2: ←→·↑·↓·N/M     Z — панель   R — заново   Ctrl+R — перезапуск   ESC — выход"
        hint = self.font_s.render(hl, True, WHITE)
        self.screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, top + 30))

        # Активные режимы (фон, масштаб, пол, прыжок) — третьей строкой панели, по центру
        if self.par_back_name:
            jump_info = (f"   ПРЫЖОК: {self.jump_name} ({JUMP_LEN}px, "
                         f"размер {JUMP_SPRITE_SCALE:.2f})") if self.jump_frames else ""
            idle_info = f"   ПОКОЙ: {self.idle_name} ({IDLE_ANIM_FPS} fps)" if self.idle_frames else ""
            punch_info = f"   УДАР: {self.punch_name}" if self.punch_frames else ""
            mma_info = f"   НОГА: {self.mma_name}" if self.mma_frames else ""
            bn = self.font_s.render(
                f"ФОН: {self.par_back_name} (E)   МАСШТАБ: {self.back_scale:.2f} (+/-)"
                f"   БЕГ: {RUN_SPRITE_SCALE:.2f}"
                f"   ПОЛ: {self.floor_name} (F){jump_info}{idle_info}{punch_info}{mma_info}",
                True, YELLOW)
            self.screen.blit(bn, (WIDTH // 2 - bn.get_width() // 2, top + 52))


if __name__ == "__main__":
    Game().run()