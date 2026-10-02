# -*- coding: utf-8 -*-
"""Часть Game: игровой цикл, логика кадра и отрисовка."""

import sys

import pygame

from .settings import *  # noqa: F401,F403
from .anim import _scale_txt, move_frame_index, move_frame_thin
from .entities import Enemy
from .gamepad import init_gamepads, pad_menu, pad_trigger_left


class GameLoop:
    """Игровой цикл: события, логика кадра, отрисовка и нижняя панель.

    run() крутит цикл и держит FPS, update() двигает бойцов и ведёт состояния
    партии (бой/победа/поражение), draw() собирает картинку из слоёв мира,
    бойцов и HUD. Клавиши читаются здесь же, поэтому все раскладки управления
    (P1/P2, геймпад) видны в одном файле.
    """

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
                        self.cycle_backdrop(1, "E")
                    if event.key == pygame.K_p and self.state == "play":   # P — пауза музыки
                        self.toggle_music_pause()
                    if event.key == pygame.K_f:               # F — смена варианта пола
                        if len(self.floors) > 1:
                            self.set_floor(self.floor_idx + 1)
                            print(f"[DEBUG] F pressed, пол -> {self.floor_name}")
                        else:
                            print("[DEBUG] F pressed, других вариантов пола нет")
                    if event.key in (pygame.K_EQUALS, pygame.K_KP_PLUS):   # +/- — масштаб заднего фона
                        # Множитель поверх масштаба из имени файла/папки, а не абсолютное
                        # значение: иначе подстройка одного фона ломала бы все остальные.
                        self.back_scale = min(BACK_SCALE_MAX,
                                              round(self.back_scale + BACK_SCALE_STEP, 3))
                        print(f"[DEBUG] + масштаб фона: x{self.back_scale:.2f}")
                    elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                        self.back_scale = max(BACK_SCALE_MIN,
                                              round(self.back_scale - BACK_SCALE_STEP, 3))
                        print(f"[DEBUG] - масштаб фона: x{self.back_scale:.2f}")
                    if event.key == pygame.K_q:               # Q — режим изоляции фона
                        self.toggle_isolate("Q")
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
                if event.type in (pygame.JOYDEVICEADDED, pygame.JOYDEVICEREMOVED):
                    # геймпад подключили/отключили — переоткрываем список
                    pads = init_gamepads()
                    self.pad_info = (f"ГЕЙМПАД: P1 — 1-й, P2 — 2-й ({len(pads)} подкл.)   "
                                     "стик/крестовина   A — прыжок   X — кулак   "
                                     "B — нога   Y — нога сильная   "
                                     "LB/RB — фон вперёд   RT — назад   LT — изоляция фона   "
                                     "Start — заставка") if pads else ""
                    for i, js in enumerate(pads):
                        print(f"[DEBUG] геймпад P{i + 1}: {js.get_name()}")
                if event.type == pygame.JOYBUTTONDOWN and self.state == "intro":
                    # Любая кнопка на заставке уровня — сразу к затуханию: пропускаем
                    # чёрный экран, появление и показ картинки. Индекс Start у разных
                    # падов разный (7, 8, ...), поэтому реагируем на любую кнопку —
                    # там больше ничего нажать нельзя.
                    self.skip_intro(f"кнопка {event.button}")
                elif (event.type == pygame.KEYDOWN and self.state == "intro"
                      and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER,
                                        pygame.K_SPACE, pygame.K_z)):
                    # Enter / Пробел / Z — то же, что кнопка геймпада: пропуск заставки
                    self.skip_intro(f"клавиша {pygame.key.name(event.key)}")
                elif event.type == pygame.JOYBUTTONDOWN and self.state == "title" \
                        and not self.trans_active and event.button in (0, 7, 8):
                    # A / Start / Guide — начать игру с геймпада
                    self.play_sfx("start")
                    self.start_transition(self.mode_sel + 1)
                elif event.type == pygame.JOYBUTTONDOWN and self.state == "play":
                    # LB/RB — следующий задний фон, RT — предыдущий, LT — изоляция (Q).
                    # Срабатывает только при нажатии (JOYBUTTONDOWN), а не по удержанию,
                    # иначе фон перелистывался бы сам, пока кнопка зажата.
                    # Порядок важен: изоляцию проверяем первее листания — LT раньше
                    # числился в PAD_BTN_BG_PREV, и его нельзя оставлять в обоих списках.
                    if event.button in PAD_BTN_ISOLATE:
                        self.toggle_isolate(f"геймпад btn{event.button}")
                    elif event.button in PAD_BTN_BG_NEXT:
                        self.cycle_backdrop(1, f"геймпад btn{event.button}")
                    elif event.button in PAD_BTN_BG_PREV:
                        self.cycle_backdrop(-1, f"геймпад btn{event.button}")

            self.frame += 1
            self.update()
            self.update_pad_menu()           # навигация меню с геймпада
            self.update_music()            # музыка: плавная громкость, пауза по P, перезапуск
            self.update_sfx_queue()         # отложенные звуки ударов (CHAR_SFX_DELAY_MS)
            self.update_pad_triggers()      # левый триггер — изоляция фона (ось, не кнопка)

            self.draw()
            self.draw_transition()
            pygame.display.flip()
            self.clock.tick(FPS)


    def update_pad_triggers(self):
        """Левый триггер геймпада — переключение изоляции фона (как Q).

        Триггер аналоговый, поэтому события JOYBUTTONDOWN он не даёт — нажатие ловится
        по фронту: переключаем только в момент, когда ось впервые ушла вверх. Иначе при
        УДЕРЖАНИИ триггера изоляция мигала бы каждый кадр. Повторное срабатывание
        возможно только после отпускания.
        """
        lt = pad_trigger_left(0)
        lt_edge = lt and not self.pad_lt_held
        self.pad_lt_held = lt
        if self.state != "play":
            return                      # как и раньше, изоляция переключается только в игре
        if self.pad_lt_cd > 0:
            self.pad_lt_cd -= 1
        if not lt_edge:
            return
        if self.pad_lt_cd > 0:
            return
        self.pad_lt_cd = PAD_LT_REPEAT_FRAMES
        self.toggle_isolate("геймпад LT (левый триггер)")


    def update_pad_menu(self):
        """Навигация главного меню стиком/крестовиной: шаг с повтором при удержании.

        Кнопка старта (A/Start) обрабатывается событием JOYBUTTONDOWN, здесь только выбор
        пункта. Работает только в состоянии title и когда нет перехода.
        """
        if self.state != "title" or self.trans_active:
            self.pad_nav_cd = 0
            return
        up, down, _ = pad_menu(0)
        if not (up or down):
            self.pad_nav_cd = 0
            return
        if self.pad_nav_cd > 0:
            self.pad_nav_cd -= 1
            return
        self.pad_nav_cd = PAD_MENU_REPEAT
        self.mode_sel = (self.mode_sel + (1 if down else -1)) % 2
        self.play_sfx("menu")


    def update(self):
        """Обновление всего мира: камера, игроки, спавн и поведение врагов, коллизии."""
        if self.trans_active:             # переход при старте партии
            if not self.trans_paused:     # на паузе, пока показан экран уровня
                self.update_transition()

        if self.state == "intro":          # чёрный экран с названием уровня
            self.intro_t -= 1
            # Заставка заканчивается только когда base-таймер истёк И текст полностью погас.
            # intro_text_alpha() вернёт 0, когда свой цикл (задержка + появление + пауза + затухание)
            # завершён. Это гарантирует, что text.png не обрывается на полуслове.
            if self.intro_t <= 0 and self.intro_text_alpha() == 0:
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
                entry = self.par_backs[self.par_back_idx]
                name, kind, pic = entry[0], entry[1], entry[2]
                own_scale = entry[3] if len(entry) > 3 else None
                # Базовый масштаб: свой из суффикса имени, иначе общий BACK_SCALE.
                # Плюс относительная подстройка клавишами +/- (self.back_scale, по умолчанию 1.0).
                self.back_eff_scale = (own_scale if own_scale is not None else BACK_SCALE) \
                    * self.back_scale
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
                    self.draw_loop_image(self.back_scaled(pic, self.back_eff_scale),
                                         int(cam * BACK_PARALLAX), 0)

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
            t = self.font_big.render("ButtKIkers United", True, YELLOW)
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
        dx = 0                       # сдвиг спрайта по X (берётся из SPRITE_OFFSET)
        dy = 0                       # сдвиг спрайта по Y (берётся из SPRITE_OFFSET)
        state = "idle"               # имя состояния для SPRITE_OFFSET и SPRITE_SCALE
        if y < -20 or x < -100 or x > WIDTH + 100:
            return                     # персонаж вне экрана — не рисуем
        if getattr(f, "dead", False) or not self.run_frames:
            return                     # мёртвых и без спрайтов не рисуем
        if f.attack == "punch" and self.punch_frames:
            # Удар рукой: кадр анимации по прогрессу атаки. Номер кадра считает Fighter
            # через attack_progress, чтобы не тянуть лишние счётчики.
            idx = int(f.attack_progress * len(self.punch_frames))
            frame = self.punch_frames[min(max(0, idx), len(self.punch_frames) - 1)]
            state = "punch"
        elif f.attack == "kik" and self.kik_frames:
            # Обычный удар ногой: своя анимация kik.png, кадр так же по прогрессу атаки.
            idx = int(f.attack_progress * len(self.kik_frames))
            frame = self.kik_frames[min(max(0, idx), len(self.kik_frames) - 1)]
            state = "kik"
        elif f.attack == "kick" and self.mma_frames:
            # Удар ногой: своя анимация, кадр так же по прогрессу атаки.
            idx = int(f.attack_progress * len(self.mma_frames))
            frame = self.mma_frames[min(max(0, idx), len(self.mma_frames) - 1)]
            state = "mma"
        elif getattr(f, "rolling", False) and self.roll_frames:
            # Перекат: кадр по времени (f.roll_frame считает Fighter от ROLL_ANIM_FPS).
            # Проверка стоит выше прыжка и бега — перекат это движение, он всё перекрывает.
            frame = self.roll_frames[min(max(0, f.roll_frame), len(self.roll_frames) - 1)]
            state = "roll"
        elif f.jumping and self.jump_frames:
            # В прыжке спрайт не смещается по вертикали — показываем кадр анимации,
            # номер которого Fighter считает по времени (JUMP_ANIM_FPS).
            frame = self.jump_frames[min(max(0, f.jump_frame), len(self.jump_frames) - 1)]
            state = "jump"
        elif self.crwalk_frames and getattr(f, "crouch_walking", False):
            # Крадущаяся ходьба: персонаж сел и едет. Частота кадров — общий переключатель
            # MOVE_ANIM_FPS; длительность цикла задаёт CRWALK_ANIM_FPS, боец при этом
            # перемещается вдвое медленнее бега (CRWALK_SPEED_MUL).
            frame = self.crwalk_frames[move_frame_index(self.frame, f.run_phase,
                                                        len(self.crwalk_frames))]
            state = "crwalk"
        elif self.sit_frames and (f.crouching or getattr(f, "sit_dir", 0) != 0):
            # Присед: сидящая поза (f.sit_t дошёл до конца) и подъём после отпускания.
            # Таймер sit_t идёт с ускорением SIT_SPEED_MUL, а частота ПРОСМОТРА кадров остаётся
            # прежней (MOVE_ANIM_FPS) — переход короче, поз в нём меньше. Крайние кадры
            # (стоит / сел) показываются всегда.
            sit_t = max(0, getattr(f, "sit_t", 0))
            sit_n = len(self.sit_frames)
            sit_fps = float(MOVE_ANIM_FPS) / max(0.1, float(SIT_SPEED_MUL))
            frame = self.sit_frames[move_frame_thin(sit_t / float(max(1, sit_n - 1)), sit_n, sit_fps)]
            state = "sit"
        elif f.was_moving:
            # Фаза бега привязана к f.run_phase: он сдвигается при приземлении, чтобы
            # переход «прыжок -> бег» начинался с 0-го кадра, а не со случайного.
            # Частота обновления задаётся MOVE_ANIM_FPS, длительность цикла — та же.
            frame = self.run_frames[move_frame_index(self.frame, f.run_phase, len(self.run_frames))]
            state = "run"
        elif self.idle_frames:
            # Стоим на месте: цикл покоя под тем же переключателем MOVE_ANIM_FPS. Смещение
            # f.idle_phase (у каждого игрока своё), чтобы P1 и P2 не дышали синхронно.
            frame = self.idle_frames[move_frame_index(self.frame, f.idle_phase,
                                                      len(self.idle_frames))]
        else:
            frame = self.run_frames[0]
            state = "run"
        ox, oy, by_facing = SPRITE_OFFSET.get(state, (0, 0, False))
        dx = ox * f.facing if by_facing else ox
        dy = oy
        # Масштаб спрайта — свой для каждой анимации (SPRITE_SCALE). Число — на обе оси,
        # пара (X, Y) — по одной каждой.
        sc = SPRITE_SCALE.get(state, 1.0)
        sx_mul, sy_mul = sc if isinstance(sc, (tuple, list)) else (sc, sc)
        base_h = CHAR_SPRITE_H * f.scale * CHAR_SPRITE_SCALE   # базовая высота бойца на экране
        th = max(1, int(base_h * sy_mul))                      # высота спрайта на экране
        tw = max(1, int(frame.get_width() * base_h * sx_mul / frame.get_height()))
        img = pygame.transform.scale(frame, (tw, th))
        if f.facing < 0:
            img = pygame.transform.flip(img, True, False)
        sx = x + (f.w - tw) // 2 + dx  # центрируем по хитбоксу + сдвиг из SPRITE_OFFSET
        sy = y + f.h - th + dy   # низ спрайта + сдвиг Y из SPRITE_OFFSET
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
            hl = ("←→/AD — идти   ↑/W — прыжок  ↓/S — блок   J — кулак   K — нога   "
                  "I — нога сильная   O — перекат   Z — панель   R — заново   "
                  "Ctrl+R — перезапуск   ESC — выход")
        else:
            hl = ("P1: A/D·W·S·J/K/I·O     P2: ←→·↑·↓·N/B/M     Z — панель   R — заново   "
                  "Ctrl+R — перезапуск   ESC — выход")
        if self.pad_info:                 # геймпад подключён — дописываем его раскладку
            hl += f"     |  {self.pad_info}"
        hint = self.font_s.render(hl, True, WHITE)
        self.screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, top + 30))

        # Активные режимы (фон, масштаб, пол, прыжок) — третьей строкой панели, по центру
        if self.par_back_name:
            jump_info = (f"   ПРЫЖОК: {self.jump_name} ({MOVE_ANIM_JUMP_FPS} fps, "
                         f"{JUMP_LEN}px, размер {_scale_txt(SPRITE_SCALE.get('jump'))})") if self.jump_frames else ""
            idle_info = f"   ПОКОЙ: {self.idle_name} ({IDLE_ANIM_FPS} fps)" if self.idle_frames else ""
            sit_info = f"   ПРИСЕД: {self.sit_name} ({SIT_ANIM_FPS} fps)" if self.sit_frames else ""
            punch_info = f"   УДАР: {self.punch_name}" if self.punch_frames else ""
            kik_info = f"   НОГА: {self.kik_name}" if self.kik_frames else ""
            mma_info = f"   НОГА СИЛЬН.: {self.mma_name}" if self.mma_frames else ""
            bn = self.font_s.render(
                f"ФОН: {self.par_back_name} (E)   МАСШТАБ: "
                f"{getattr(self, 'back_eff_scale', self.back_scale):.2f} (+/-)"
                f"   ДВИЖЕНИЕ: {MOVE_ANIM_FPS} fps, {_scale_txt(SPRITE_SCALE.get('run'))}"
                f"   ПОЛ: {self.floor_name} (F){jump_info}{idle_info}{sit_info}{punch_info}"
                f"{kik_info}{mma_info}",
                True, YELLOW)
            self.screen.blit(bn, (WIDTH // 2 - bn.get_width() // 2, top + 52))