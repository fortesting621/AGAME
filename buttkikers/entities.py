# -*- coding: utf-8 -*-
"""Бойцы: Fighter (общая физика и удары), Player (управление), Enemy (ИИ).

Fighter не знает, кто он: у него есть полоса здоровья, прыжок, перекат и удары.
Player поверх него читает клавиши и геймпад, Enemy — решает, когда атаковать.
"""
import random

import pygame

from . import settings
from .settings import *  # noqa: F401,F403
from .anim import (
    attack_duration,
    jump_duration,
    move_frame_once,
    move_phase_for_frame,
    roll_duration,
)
from .gamepad import pad_state


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
        self.attack = None             # текущая атака: "punch" / "kik" / "kick" / None
        self.attack_timer = 0          # оставшиеся кадры атаки
        self.attack_hit = False        # уже ли атака попала в цель (один удар за анимацию)
        self.cooldown = 0              # кадры перезарядки между атаками
        self.combo = 0                 # счётчик серии ударов (усиливает урон)
        self.combo_timeout = 0         # кадр, после которого серия обнуляется
        self.flinch = 0                # кадры "отшатывания" от удара (нельзя действовать)
        self.knock = 0                 # сила отталкивания от удара
        self.was_moving = False        # двигался ли боец в этом кадре (для анимации бега)
        self.sit_t = 0                 # кадр анимации приседа: 0 — стоит, settings.SIT_ANIM_N-1 — сел
        self.sit_dir = 0               # 1 — садится, -1 — встаёт, 0 — стоит
        self.sit_acc = 0.0             # накопитель дробного шага таймера приседа (SIT_SPEED_MUL)
        self.game = None                # ссылка на Game (для проигрывания SFX персонажа)
        self.crouch_walking = False    # идёт ли крадущейся ходьбой (анимация crwalk)
        self.rolling = False          # идёт ли перекат (анимация roll)
        self.roll_t = 0               # кадров игры с начала переката
        self.roll_dur = 0             # сколько кадров длится перекат (вся анимация)
        self.roll_n = 0               # кадров в анимации этого переката
        self.roll_frame = 0           # текущий кадр анимации переката
        self.roll_cd = 0              # оставшиеся кадры кулдауна до следующего переката
        self.roll_trigger_held = False  # триггер был нажат в прошлом кадре (фронт нажатия)
        self.roll_edge = False     # триггер нажат именно в этом кадре (а не удерживается)
        self.entry_roll = False  # идёт ли входной перекат на старте раунда (персонаж из-за края)
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
    def attack_anim_n(self):
        """Кадров в анимации текущей атаки (0 — анимации нет, берётся запасная длительность)."""
        if self.attack == "punch":
            return settings.PUNCH_ANIM_N
        if self.attack == "kik":
            return settings.KIK_ANIM_N
        return settings.MMA_ANIM_N

    @property
    def attack_progress(self):
        """Прогресс текущей атаки от 0 (начало) до 1 (конец) — для выбора кадра анимации."""
        if self.attack is None:
            return 0.0
        dur = attack_duration(self.attack_anim_n or (PUNCH_FALLBACK if self.attack == "punch"
                                                    else KICK_FALLBACK))
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
        if self.attack == "kik":         # обычный удар ноги — слабее сильного
            return 16 + self.combo * 2, "kik"
        return 20 + self.combo * 2, "kick"

    def try_attack(self, kind, now):
        """Запуск атаки, если не занят и не перезаряжается."""
        if self.cooldown > 0 or self.attack is not None or self.dead:
            return
        self.attack = kind
        # Длительность удара = длина анимации по её собственной скорости (attack_duration),
        # иначе кадры шли бы по одному на игровой кадр и удар был бы вдвое быстрее.
        self.attack_timer = attack_duration(self.attack_anim_n or KICK_FALLBACK)
        self.attack_hit = False
        # Пауза до следующего удара: кулак — 3 кадра, обычная нога — 4, сильная нога — 5
        self.cooldown = {"punch": 3, "kik": 4}.get(kind, 5)
        if now > self.combo_timeout:                       # вышло время — сбрасываем серию
            self.combo = 0
        self.combo += 1
        if self.combo > 2:
            self.combo = 2        # максимум комбо — 3 удара подряд
        self.combo_timeout = now + 30
        # Звук удара: punch/kik/kick (mma). У каждого своя задержка из CHAR_SFX_DELAY_MS —
        # сильная нога звучит позже, на самом ударе.
        snd_key = "kick" if kind == "kick" else ("punch" if kind == "punch" else "kik")
        if getattr(self, "game", None):
            self.game.play_sfx_delayed(snd_key)

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
        self.jump_n = settings.JUMP_ANIM_N
        self.jump_dur = jump_duration(self.jump_n)
        self.jump_speed = length / self.jump_dur
        self.jump_frame = 0
        self.vel_y = 0
        # Звук прыжка: основной (случайный из jump1-4) и два дополнительных
        # (jumpALT.mp3, jumpALT2.mp3). Все три при каждом прыжке, у каждого своя
        # задержка в CHAR_SFX_DELAY_MS
        if getattr(self, "game", None):
            self.game.play_sfx_delayed("jump")
            self.game.play_sfx_delayed("jump_alt")
            self.game.play_sfx_delayed("jump_alt2")

    def try_roll(self):
        """Запуск переката, если не занят и не перезаряжается. True — перекат начался.

        Проверки внутри (как в try_attack), чтобы перекат нельзя было запустить из
        отшатывания, при ударе или во время кулдауна.
        """
        if self.cooldown > 0 or self.attack is not None or self.dead:
            return False
        if self.rolling or self.jumping or self.roll_cd > 0 or self.flinch > 0:
            return False
        self.start_roll()
        return True

    def start_roll(self):
        """Начать перекат: персонаж катится вперёд всю анимацию целиком.

        Движение нельзя прервать — ни отпусканием стика, ни нажатием другой кнопки, ни
        получением урона: пока идёт анимация (roll_t < roll_dur), боец едет вперёд сам.
        Урон перекат не отменяет, только отбрасывает — так что «прервать» нечем.

        Вызывать следует через try_roll() — он проверяет кулдаун и занятость.
        """
        self.rolling = True
        self.roll_t = 0
        self.roll_n = settings.ROLL_ANIM_N
        self.roll_dur = roll_duration(self.roll_n)
        self.roll_frame = 0
        self.roll_cd = ROLL_COOLDOWN_FRAMES
        # Перекат отменяет присед и крадущуюся ходьбу: это движение, а не блок.
        self.crouching = False
        self.now_blocking = False
        self.crouch_walking = False
        # Звук переката: roll.mp3 (звук качения) и шорох прыжка. У качения своя
        # задержка (SFX_ROLL_DELAY_MS), у шороха — из CHAR_SFX_DELAY_MS
        if getattr(self, "game", None):
            self.game.play_sfx_delayed("roll", SFX_ROLL_DELAY_MS)
            self.game.play_sfx_delayed("roll_jump")
        self.sit_t = 0
        self.sit_dir = 0
        self.sit_acc = 0.0

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
        if self.roll_cd > 0:            # отсчёт кулдауна между перекатами
            self.roll_cd -= 1
        if self.rolling:
            # Перекат: персонаж едет вперёд всю анимацию и не может остановиться — движение
            # задано самой анимацией, а не стиком. Скорость фиксированная (ROLL_SPEED_MUL),
            # направление — то, в которое он смотрел при старте (facing).
            # Отшатывание (knock) перекат не отменяет, только добавляется к движению.
            self.vel_x = MOVE * ROLL_SPEED_MUL * self.facing
            self.was_moving = True
            self.roll_t += 1
            if self.roll_t >= self.roll_dur:      # анимация доиграла — перекат закончен
                self.rolling = False
                self.roll_t = 0
                self.roll_frame = 0
                self.vel_x = 0
                # Входной перекат закончился — персонаж выехал на кадр, снова
                # зажимаем его камерой (иначе можно было бы уйти за левый край).
                self.entry_roll = False
                # Бег после переката начинается с той же фазы, что и после приземления.
                self.run_phase = move_phase_for_frame(frame, max(1, settings.RUN_ANIM_N),
                                                       RUN_START_FRAME)
            else:
                self.roll_frame = move_frame_once(self.roll_t, self.roll_dur, self.roll_n,
                                                  ROLL_ANIM_FPS)

        if self.jumping:
            # Прыжок: по вертикали не двигаемся — всё перемещение нарисован в анимации.
            # Идёт только таймер и смена кадра анимации. Частота кадров — общий переключатель
            # MOVE_ANIM_FPS (та же прореживание, что у бега), длительность прыжка задаёт
            # jump_duration() и от MOVE_ANIM_FPS не зависит.
            self.vel_y = 0
            self.on_ground = True
            self.jump_t += 1
            if self.jump_t >= self.jump_dur:     # анимация доиграла — приземление
                self.jumping = False
                self.jump_t = 0
                self.jump_frame = 0
                # Фаза бега сдвигается так, чтобы сразу после приземления на экране
                # был RUN_START_FRAME-й кадр бега, а не случайный кадр цикла.
                # Фаза считается обратным ходом от move_frame_index, поэтому работает
                # при любом MOVE_ANIM_FPS (раньше было -(frame // 2) — верно только для 30).
                self.run_phase = move_phase_for_frame(frame, max(1, settings.RUN_ANIM_N),
                                                       RUN_START_FRAME)
            else:
                self.jump_frame = move_frame_once(self.jump_t, self.jump_dur, self.jump_n,
                                                  MOVE_ANIM_JUMP_FPS)
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
        # Входной перекат: персонаж начинает раунд за левым краем кадра, поэтому на это
        # время разрешаем ему быть левее камеры — обычный зажим вернул бы его на кадр.
        left_limit = -START_ROLL_BACK_PX if self.entry_roll else cam
        self.x = max(left_limit, min(self.x, LEVEL_LEN - self.w))  # не даём уйти за уровень/камеру

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

    def start_entry_roll(self):
        """Входной перекат на старте раунда: кувырок из-за левого края кадра.

        Персонаж сдвигается назад за границу игрового кадра (x становится
        отрицательным — его не видно) и начинает перекат, поэтому он выкатывается
        на экран снизу, как будто выпрыгивает из-за края. Пока идёт перекат,
        entry_roll держит камеру на месте и разрешает уход левее неё.
        """
        if not START_ROLL_ON or self.entry_roll:
            return
        self.x -= START_ROLL_BACK_PX    # уезжает за левый край кадра (cam = 0 на старте)
        self.facing = 1                 # катиться вправо, на экран
        self.entry_roll = True          # разрешаем быть левее камеры и держим камеру
        self.start_roll()

    def update(self, cam, frame):
        # Состояние приседа, по которому отработала физика выше: высота хитбокса (h)
        # зависит от crouching, поэтому запоминаем его ДО super().update().
        was_crouching = self.crouching
        super().update(cam, frame)   # сначала базовая физика Fighter
        if self.dead:
            return

        # Чтение клавиш в зависимости от схемы управления
        keys = pygame.key.get_pressed()
        # Геймпад складывается с клавиатурой: нажато хоть на клавиатуре, хоть на паде.
        # pnum: 0 = P1 (1-й геймпад), 1 = P2 (2-й геймпад)
        gp_l, gp_r, gp_u, gp_d, gp_p, gp_n, gp_k, gp_roll = pad_state(self.pnum)
        if self.pnum == 1:                       # 2-й игрок использует стрелки + N/M/B
            left = keys[pygame.K_LEFT] or gp_l
            right = keys[pygame.K_RIGHT] or gp_r
            up = keys[pygame.K_UP] or gp_u
            down = keys[pygame.K_DOWN] or gp_d
            punch = keys[pygame.K_n] or gp_p
            kik = keys[pygame.K_b] or gp_n      # B — обычный удар ноги
            kick = keys[pygame.K_m] or gp_k
        elif self.mode == 1:                     # P1 в одиночной игре: и WASD, и стрелки
            left = keys[pygame.K_a] or keys[pygame.K_LEFT] or gp_l
            right = keys[pygame.K_d] or keys[pygame.K_RIGHT] or gp_r
            up = keys[pygame.K_w] or keys[pygame.K_UP] or gp_u
            down = keys[pygame.K_s] or keys[pygame.K_DOWN] or gp_d
            punch = keys[pygame.K_j] or gp_p      # Z свободен: переключает нижнюю панель
            kik = keys[pygame.K_k] or gp_n        # K — обычный удар ноги
            kick = keys[pygame.K_i] or gp_k      # I — сильный удар ногой (mma)
        else:                                    # P1 в кооперативе: только WASD + J/K/I
            left = keys[pygame.K_a] or gp_l
            right = keys[pygame.K_d] or gp_r
            up = keys[pygame.K_w] or gp_u
            down = keys[pygame.K_s] or gp_d
            punch = keys[pygame.K_j] or gp_p
            kik = keys[pygame.K_k] or gp_n
            kick = keys[pygame.K_i] or gp_k

        self.crouching = False
        # Фронт нажатия переката (roll_edge) считаем ЗДЕСЬ, до всех ранних return: флаг
        # «перекат нажат» должен обновляться каждый кадр, в том числе во время
        # переката и удара. Иначе при УДЕРЖАНИИ O перекат повторялся бы сам.
        # Перекат — клавиша O или правый триггер геймпада; на паузе (self.pnum == 0)
        # клавиша не читается, иначе игрок перекатывался бы на чужом нажатии.
        roll_now = gp_roll if self.pnum == 1 else (gp_roll or keys[pygame.K_o])
        self.roll_edge = roll_now and not self.roll_trigger_held
        self.roll_trigger_held = roll_now
        # Перекат уже идёт: персонаж катится сам, управление не действует. Управление
        # вернётся только когда анимация доиграет (rolling сбросится в Fighter.update).
        # vel_x и was_moving заданы в Fighter.update — там своя скорость переката.
        if self.rolling:
            return
        if self.attack is not None:
            # Время удара персонаж стоит на месте: бег, прыжок и присед не действуют.
            self.vel_x = 0
            self.was_moving = False
            return
        # Двигаться можно только в двух крайних позах анимации приседа:
        #   стоя (sit_t == 0) и полностью сидя (sit_t == SIT_ANIM_N-1 при нажатом "вниз").
        # Всё между ними — переход (садится ИЛИ встаёт), и двигаться там нельзя:
        # персонаж «едет» вверх ногами, пока меняет позу. Поэтому заблокированы и
        # подъём, и первый кадр после отпускания "вниз" (подъём там только начинается).
        # Опора на down, а не на was_crouching: выше self.crouching уже сброшен в False,
        # а was_crouching ещё True в кадре отпускания — и ходьба начиналась бы на кадр раньше.
        seated_now = down and self.sit_t >= settings.SIT_ANIM_N - 1
        standing_now = self.sit_t <= 0 and not down
        sit_locked = not self.jumping and not seated_now and not standing_now
        # Крадущаяся ходьба: персонаж УЖЕ сел и поехал. Идём вдвое медленнее ходьбы.
        crouch_walk = (not self.jumping and seated_now and (left or right)
                       and not sit_locked and self.flinch <= 0)
        if self.flinch <= 0:                     # в отшатывании игрок неуправляем
            # на земле — скорость ходьбы, в прыжке — скорость, посчитанная из длины прыжка
            if self.jumping:
                spd = self.jump_speed
            elif crouch_walk:
                spd = MOVE * CRWALK_SPEED_MUL
            else:
                spd = MOVE
            if not sit_locked:
                if left:
                    self.vel_x = -spd
                    self.facing = -1
                    self.moved += 1
                elif right:
                    self.vel_x = spd
                    self.facing = 1
                    self.moved += 1
            else:
                self.vel_x = 0
            if up and standing_now and not self.jumping and not self.jump_cd and JUMP_LEN > 0:
                # Прыжок только из полностью стоящей позы: из приседа и во время
                # подъёма прыгать нельзя (standing_now), иначе персонаж взлетал бы
                # прямо из сидячей позы. Нужно сначала отпустить "вниз" и встать.
                # прыжок: спрайт по вертикали не двигается, летит только по горизонтали
                self.start_jump(JUMP_LEN)
                self.jump_cd = JUMP_COOLDOWN_FRAMES
            if down and not self.jumping:  # присед = блокировка, только на земле
                self.crouching = True
                self.now_blocking = True
            # Физика выше считала пол по старой высоте хитбокса. Если высота изменилась
            # (присел / встал), прижимаем бойца к полу сразу — иначе он на кадр зависает
            # над полом и гравитация тянет его вниз: спрайт визуально «падает сверху».
            if self.crouching != was_crouching and not self.jumping and self.on_ground:
                self.y = CHARACTER_FLOOR_Y - self.h
                self.vel_y = 0
            if not self.jumping:
                # Перекат (клавиша O или правый триггер) — по фронту нажатия self.roll_edge,
                # посчитанному выше. Идёт перед ударами: если нажаты оба, перекат важнее.
                if self.roll_edge and not self.rolling:
                    self.try_roll()
                # удары только с земли: в прыжке не бьём ни кулаком, ни ногой
                if punch and not self.rolling:
                    self.try_attack("punch", frame)
                elif kik and not self.rolling:
                    self.try_attack("kik", frame)
                elif kick and not self.rolling:
                    self.try_attack("kick", frame)
        # для анимации бега: двигались и стоим на земле (и не заперты в недосиженном приседе)
        self.was_moving = ((left or right) and self.on_ground and self.flinch <= 0
                           and not sit_locked)
        # Крадущаяся ходьба — только когда реально сел и поехал: тогда рисуем crwalk
        # вместо спрайта бега. Пока не досел (sit_locked) — обычный спрайт стоя.
        self.crouch_walking = bool(crouch_walk and self.on_ground)
        # Анимация приседа: садится (кадры вперёд), держит позу, встаёт (кадры назад).
        # Кадры загружены уже развёрнутыми (SIT_REVERSE), так что 0 — стоя, конец — сел.
        n = settings.SIT_ANIM_N
        if n > 1:
            # Шаг таймера: один кадр анимации на FPS / SIT_ANIM_FPS / SIT_SPEED_MUL игровых
            # кадров. Шаг дробный, поэтому остаток копится в sit_acc — тогда любая скорость
            # работает честно, без округления. SIT_SPEED_MUL = 2.0 -> приседание вдвое
            # короче; частота просмотра кадров не меняется, она задаётся при отрисовке.
            sit_step = max(0.1, float(FPS) / float(SIT_ANIM_FPS) / max(0.1, float(SIT_SPEED_MUL)))
            if self.crouching:
                self.sit_dir = 1
                self.sit_acc += 1.0
                while self.sit_acc >= sit_step:
                    self.sit_acc -= sit_step
                    self.sit_t = min(n - 1, self.sit_t + 1)
            elif self.sit_t > 0:         # только что отпустили — проигрываем подъём
                self.sit_dir = -1
                self.sit_acc += 1.0
                while self.sit_acc >= sit_step:
                    self.sit_acc -= sit_step
                    self.sit_t -= 1
            else:
                self.sit_dir = 0
                self.sit_acc = 0.0


class Enemy(Fighter):
    """Враг с простым ИИ. Видов и уровней нет — все враги одинаковые.

    Параметр kind оставлен только для совместимости с вызовом из кода спавна: на
    характеристики врага он больше не влияет. Все берутся из настроек ENEMY_*.
    """

    def __init__(self, x, kind=None):
        self.kind = kind
        # Размер, здоровье, скорость и дальность атаки — общие для всех врагов
        # (ENEMY_SCALE / ENEMY_HP / ENEMY_SPEED / ENEMY_ATTACK_RANGE). Раньше виды
        # отличались друг от друга, но разных врагов в игре больше нет.
        super().__init__(x, ENEMY_HP if ENEMY_HP is not None else 45, THUG, "THUG",
                         scale=ENEMY_SCALE)
        self.speed = ENEMY_SPEED           # скорость погони
        self.attack_range = ENEMY_ATTACK_RANGE   # дистанция начала атаки
        self.now_blocking = False
        self.hp = int(self.hp * self.scale)   # здоровье растёт с размером
        # ENEMY_HP, если задан, заменяет здоровье у всех видов: так враг сразу становится
        # безобидным (ENEMY_HP = 1 — падает от любого удара). None — своё у каждого вида.
        if ENEMY_HP is not None:
            self.hp = int(ENEMY_HP)
        self.max_hp = self.hp
        # Сдвиг фазы ходьбы: у каждого врага свой, иначе вся толпа шагала бы в унисон.
        # run_phase при этом пересчитывается при приземлении (Fighter.update), поэтому
        # после прыжка фаза снова станет 0 — это заметно только на кадрах прыжка.
        self.run_phase = random.randrange(0, 12)

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