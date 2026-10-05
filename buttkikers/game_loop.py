# -*- coding: utf-8 -*-
"""Часть Game: игровой цикл, логика кадра и отрисовка."""

import sys

import pygame

from .settings import *  # noqa: F401,F403
from .anim import _scale_txt, enemy_dead_time, move_frame_index, move_frame_thin
from .entities import Enemy
from .gamepad import current_pad_count, init_gamepads, pad_menu, pad_trigger_left, reopen_gamepads


def pack_lines(items, font, max_w):
    """Упаковывает список подсказок в строки шириной не больше max_w.

    Одна длинная строка с управлением не влезала за экран, особенно когда
    дописывалась раскладка геймпада. Поэтому подсказки идут списком, а строки
    собираются по фактической ширине текста: шрифт и разрешение можно менять,
    раскладка пересоберётся сама. Пункт шире max_w остаётся в строке один —
    обрезать подсказку нельзя.
    """
    lines, cur = [], ""
    for item in items:
        probe = f"{cur}   {item}" if cur else item
        if not cur or font.size(probe)[0] <= max_w:
            cur = probe
        else:
            lines.append(cur)
            cur = item
    if cur:
        lines.append(cur)
    return lines


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
                    self.pad_connected = bool(pads)   # панель переключится на управление геймпадом
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
                elif (event.type == pygame.JOYBUTTONDOWN and self.state == "title"
                      and not self.trans_active and event.button in (0, 7, PAD_BTN_START[0])):
                    # A / Select / Start — начать игру с геймпада. Кнопки тыльной стороны
                    # корпуса (8, 9, 10) в список не входят и игровых действий не имеют
                    self.play_sfx("start")
                    self.start_transition(self.mode_sel + 1)
                elif event.type == pygame.JOYBUTTONDOWN and self.state == "play":
                    # Start (кнопка 6) — рестарт партии, так же, как R на клавиатуре.
                    # Проверяем первым остальных: это единственное действие, которое
                    # начинается с нуля, поэтому список кнопок с ним не должен совпадать.
                    # Select (кнопка 7) — панель информации, так же, как Z на клавиатуре.
                    # LB — предыдущий фон, RB — следующий фон, LT — панорама (Q).
                    # Срабатывает только при нажатии (JOYBUTTONDOWN), а не по удержанию,
                    # иначе фон перелистывался бы сам, пока кнопка зажата.
                    # Порядок важен: изоляцию проверяем первее листания — LT раньше
                    # числился в PAD_BTN_BG_PREV, и его нельзя оставлять в обоих списках.
                    if event.button in PAD_BTN_START:
                        print(f"[DEBUG] геймпад btn{event.button} (Start) — рестарт")
                        self.reset()
                    elif event.button in PAD_BTN_PANEL:
                        self.hud_on = not self.hud_on
                        print(f"[DEBUG] геймпад btn{event.button} (Select) — панель: "
                              f"{'ВКЛ' if self.hud_on else 'ВЫХКЛ'}")
                    elif event.button in PAD_BTN_ISOLATE:
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
            self.update_pad_connection()   # перепроверка списка геймпадов раз в PAD_CHECK_FRAMES
            self.update_hud_anim()         # панель информации выезжает снизу вверх

            self.draw()
            self.draw_transition()
            pygame.display.flip()
            self.clock.tick(FPS)


    def update_pad_connection(self):
        """Раз в PAD_CHECK_FRAMES кадров перечитывает список геймпадов.

        Зачем: список открывается на старте игры и по событию JOYDEVICEADDED, но
        событие приходит не всегда — пульт, подключённый или разбуженный уже после
        старта, может его не дать. Тогда игра остаётся в режиме «клавиатура»,
        и панель показывает клавиатурные подсказки, хотя пульт подключён (и наоборот).
        Перепроверка раз в секунду стоит одного get_count() и чинит это само.

        Две тонкости, из-за которых написано именно так:
        - если список не изменился, ничего НЕ переоткрываем: get_numaxes() дёргает
          драйвер, а пересоздание джойстика каждую секунду сбрасывает состояние
          устройства (кнопки теряются, пульт заново «просыпается»);
        - пульт засыпает по USB-энергосбережению и на пару секунд пропадает из
          списка. Если переключать панель сразу, подсказки будут мигать
          «клавиатура ↔ геймпад» прямо во время игры. Поэтому на исчезновение
          ждём PAD_LOST_CHECKS неудачных проверок подряд, а появление считаем
          сразу.
        """
        self.pad_check_t += 1
        if self.pad_check_t < PAD_CHECK_FRAMES:
            return
        self.pad_check_t = 0
        count = pygame.joystick.get_count()
        if count == current_pad_count():
            self.pad_missed = 0
            return
        if count == 0:
            self.pad_missed += 1
            if self.pad_missed < PAD_LOST_CHECKS:
                return
        else:
            self.pad_missed = 0
        was = self.pad_connected
        pads = init_gamepads()
        self.pad_connected = bool(pads)
        if self.pad_connected == was:
            return
        if self.pad_connected:
            for i, js in enumerate(pads):
                print(f"[DEBUG] геймпад P{i + 1} появился: {js.get_name()}")
        else:
            print("[DEBUG] геймпад отключился — панель покажет клавиатуру")


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
                sx = self.spawn_points[self.spawn_idx]
                if rightmost + WIDTH >= sx:
                    left = sx < self.cam
                    ex = sx - 200 if left else sx        # если точка позади камеры — отодвигаем вперёд
                    self.enemies.append(Enemy(max(50, ex)))
                    self.spawn_idx += 1
                else:
                    break

        # Поведение врагов + удаление трупов
        if not NO_ENEMIES:
            for e in self.enemies[:]:
                if e.dead:
                    e.update(self.cam, self.frame)
                    if e.dead_timer > enemy_dead_time():
                        self.enemies.remove(e)           # труп убран после проигрывания анимации
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

        # Враги (в изоляции скрыты). Видов нет — у всех один ранг отрисовки.
        if not NO_ENEMIES and not self.isolate:
            for e in self.enemies:
                self.draw_fighter(e, cam, e.kind, rank=3)

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
            # Панорамный режим: чистый вид (фон + персонаж + пол), вместо HUD —
            # панель с названием режима. Панель выезжает так же, как обычная.
            # Условие — только анимация (hud_anim > 0), а не hud_on: иначе при выключении
            # панель исчезала бы мгновенно вместо того, чтобы уехать вниз
            if self.hud_anim > 0.0:
                slide = self.hud_slide(HUD_H)
                top = HEIGHT - HUD_H + slide
                self.panel_band(HUD_H, top)
                step = self.font_panel.get_linesize()
                y = top + (HUD_H - step * 2) // 2
                t = self.font_panel.render("ПАНОРАМНЫЙ РЕЖИМ", True, YELLOW)
                self.screen.blit(t, (WIDTH // 2 - t.get_width() // 2, y))
                # Подсказка выхода — по тому, чем игра запущена: с геймпада LT,
                # с клавиатуры Q (иначе с подключённым пультом писало бы Q - не туда)
                q = self.font_panel.render(
                    PANORAMA_EXIT_PAD if self.pad_connected else PANORAMA_EXIT_KEY, True, WHITE)
                self.screen.blit(q, (WIDTH // 2 - q.get_width() // 2, y + step))
        else:
            # Панель рисуется всегда: скрытие отдано анимации (hud_anim → 0), поэтому
            # при выключении она уезжает вниз, а не пропадает на месте
            self.draw_hud()

        # Экран победы/поражения
        if self.state == "win":
            self.win_t += 1
            t = self.font_big.render("LEVEL CLEAR!", True, YELLOW)
            self.screen.blit(t, (WIDTH // 2 - t.get_width() // 2, 180))
            if self.win_t > 20:
                h = self.font_panel.render("R - ЗАНОВО   CTRL+R - ПЕРЕЗАПУСК", True, WHITE)
                self.screen.blit(h, (WIDTH // 2 - h.get_width() // 2, 240))
        elif self.state == "lose":
            self.lose_t += 1
            t = self.font_big.render("GAME OVER", True, RED)
            self.screen.blit(t, (WIDTH // 2 - t.get_width() // 2, 180))
            if self.lose_t > 20:
                h = self.font_panel.render("R - ЗАНОВО   CTRL+R - ПЕРЕЗАПУСК", True, WHITE)
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

        # Мигающая подсказка запуска. С геймпадом игру начинает кнопка Start, поэтому
        # пишем «НАЖМИТЕ СТАРТ», с клавиатуры — «НАЖМИТЕ ENTER» (иначе геймпадный игрок
        # не видит, чем начать игру, а клавиатурный — не видит своей клавиши)
        if (self.frame // 15) % 2 == 0:
            start_hint = "НАЖМИТЕ СТАРТ" if self.pad_connected else "НАЖМИТЕ ENTER"
            s = self.pixel_font_ru.render(start_hint, True, (137, 223, 255))
            self.screen.blit(s, (WIDTH // 2 - s.get_width() // 2, 736))

        # Подсказка по навигации
        hint = self.pixel_font_ru.render(
            "W/S ИЛИ ↑/↓ - ВЫБОР   ESC - ВЫХОД",
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
        # Враг рисуется ТОЛЬКО своими спрайтами из ENEMY_WALK_DIR (sprites/enemies) —
        # спрайты игрока ему не подставляются никогда. Состояние выбирается как обычно,
        # но кадр берётся из enemy_frames; если своего файла для состояния нет, показывается
        # первый кадр ходьбы (поза покоя), а не спрайт игрока.
        is_enemy = (variant != "player")
        ef = (getattr(self, "enemy_frames", None) or {}) if is_enemy else {}
        if is_enemy:
            return self.draw_enemy(f, x, y, variant, rank, ef)
        if getattr(f, "dead", False) or not self.run_frames:
            return                     # мёртвых игроков и без спрайтов не рисуем
        frames_punch = self.punch_frames
        frames_kik = self.kik_frames
        frames_mma = self.mma_frames
        if f.attack == "punch" and frames_punch:
            # Удар рукой: кадр анимации по прогрессу атаки. Номер кадра считает Fighter
            # через attack_progress, чтобы не тянуть лишние счётчики.
            idx = int(f.attack_progress * len(frames_punch))
            frame = frames_punch[min(max(0, idx), len(frames_punch) - 1)]
            state = "punch"
        elif f.attack == "kik" and frames_kik:
            # Обычный удар ногой: своя анимация kik.png, кадр так же по прогрессу атаки.
            idx = int(f.attack_progress * len(frames_kik))
            frame = frames_kik[min(max(0, idx), len(frames_kik) - 1)]
            state = "kik"
        elif f.attack == "kick" and frames_mma:
            # Удар ногой: своя анимация, кадр так же по прогрессу атаки.
            idx = int(f.attack_progress * len(frames_mma))
            frame = frames_mma[min(max(0, idx), len(frames_mma) - 1)]
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
        self.blit_fighter(f, x, y, frame, state, is_player=True)


    def draw_enemy(self, f, x, y, variant, rank, ef):
        """Отрисовка ВРАГА — только спрайтами из папки sprites/enemies.

        Спрайты игрока врагу не подставляются. Состояние (удар, прыжок, перекат...) берётся
        из логики Fighter, но кадр ищется только в ef — словаре своих анимаций врага. Если
        для состояния своего файла нет, рисуется первый кадр ходьбы (поза покоя), чтобы
        враг не исчезал и не показывал чужой спрайт.
        """
        if not ef:
            return                         # папка врагов пуста/не загрузилась — нечего рисовать
        stand = ef.get("erun") or next(iter(ef.values()))
        if f.dead:
            # Смерть: спрайт падения проигрывается по времени, пока труп не уберут
            # (Fighter.update ведёт dead_timer). Без своего файла смерти враг исчезает.
            frames = ef.get("death")
            if not frames:
                return
            # Кадр считается от dead_timer — времени С МОМЕНТА СМЕРТИ этого врага, а не от
            # общего self.frame: по self.frame анимация начиналась бы со случайного места
            # (зависела от того, в какой кадр игры враг умер) и выглядела бы неправильно.
            # move_frame_index здесь не годится — он ЦИКЛИЧЕСКИЙ и прореживает кадры под
            # MOVE_SRC_FPS, а смерть одноразовая и должна показывать каждый кадр.
            # После последнего кадра держим последний (труп лежит), а не начинаем заново.
            tick = int(getattr(f, "dead_timer", 0) * ENEMY_DEATH_ANIM_FPS / FPS)
            idx = min(tick, len(frames) - 1)
            self.blit_fighter(f, x, y, frames[max(0, idx)], "death", is_player=False)
            return
        state = None
        frame = None
        if f.attack in ("punch", "kik", "kick"):
            # Удар: у каждого вида удара своё состояние. Кадр — по прогрессу атаки, который
            # считает Fighter через attack_progress (без лишних счётчиков).
            state = {"kick": "mma"}.get(f.attack, f.attack)
            frames = ef.get(state)
            if frames:
                idx = int(f.attack_progress * len(frames))
                frame = frames[min(max(0, idx), len(frames) - 1)]
        if frame is None and getattr(f, "rolling", False) and ef.get("roll"):
            frame = ef["roll"][min(max(0, getattr(f, "roll_frame", 0)), len(ef["roll"]) - 1)]
            state = "roll"
        if frame is None and f.jumping and ef.get("jump"):
            frame = ef["jump"][min(max(0, getattr(f, "jump_frame", 0)), len(ef["jump"]) - 1)]
            state = "jump"
        if frame is None and getattr(f, "crouch_walking", False) and ef.get("crwalk"):
            frames = ef["crwalk"]
            frame = frames[move_frame_index(self.frame, f.run_phase, len(frames))]
            state = "crwalk"
        if frame is None and (f.crouching or getattr(f, "sit_dir", 0) != 0) and ef.get("sit"):
            frames = ef["sit"]
            sit_n = len(frames)
            sit_t = max(0, getattr(f, "sit_t", 0))
            sit_fps = float(MOVE_ANIM_FPS) / max(0.1, float(SIT_SPEED_MUL))
            frame = frames[move_frame_thin(sit_t / float(max(1, sit_n - 1)), sit_n, sit_fps)]
            state = "sit"
        if frame is None:
            # Ходьба врага: в движении — цикл со своим сдвигом фазы (f.run_phase), чтобы
            # враги не шли в унисон; стоя — первый кадр (поза покоя).
            state = "erun"
            frames = ef.get("erun") or stand
            if f.was_moving:
                fps = ENEMY_ANIM_FPS.get("erun", ENEMY_WALK_ANIM_FPS)
                frame = frames[move_frame_index(self.frame, f.run_phase, len(frames), fps)]
            else:
                frame = frames[0]
        self.blit_fighter(f, x, y, frame, state, is_player=False)


    def blit_fighter(self, f, x, y, frame, state, is_player):
        """Масштабирует и рисует кадр бойца. is_player выбирает таблицу настроек.

        Смещение и масштаб — свои у игрока (SPRITE_OFFSET / SPRITE_SCALE) и свои у врага
        (ENEMY_SPRITE_OFFSET / ENEMY_SPRITE_SCALE): правка врага не задевает игрока.
        """
        if frame is None:
            return
        off_tbl = SPRITE_OFFSET if is_player else ENEMY_SPRITE_OFFSET
        sc_tbl = SPRITE_SCALE if is_player else ENEMY_SPRITE_SCALE
        # Сдвиг X симметричный — всегда отсчитывается по направлению взгляда: при повороте
        # влево смещение меняет знак, и боец со спрайтом остаются на одном расстоянии.
        ox, oy = off_tbl.get(state, (0, 0))
        dx = ox * f.facing
        dy = oy
        # Число — множитель на обе оси, пара (X, Y) — по одной каждой.
        sc = sc_tbl.get(state, 1.0)
        sx_mul, sy_mul = sc if isinstance(sc, (tuple, list)) else (sc, sc)
        base_h = CHAR_SPRITE_H * f.scale * CHAR_SPRITE_SCALE   # базовая высота бойца на экране
        # Размер считается по СОДЕРЖИМОМУ кадра, а не по кадру целиком: у спрайтов вокруг
        # бойца пустые прозрачные поля (у walk.png кадр шире бойца почти вдвое), поэтому
        # при масштабировании по кадре боец выходил бы на экране меньше своего спрайта,
        # и переход «иду -> бью» скакал бы по высоте. Множитель ENEMY_STATE_FIT приводит
        # каждое состояние врага к высоте его ходьбы; у игрока он равен 1.0 — его спрайты
        # отмасштабированы так, как заведено (SPRITE_SCALE).
        fit = 1.0 if is_player else ENEMY_STATE_FIT.get(state, 1.0)
        # Итоговый множитель по каждой оси: своя настройка состояния × подгонка по
        # содержимому. Их порядок не важен — оба множителя входят произведением.
        mul_x, mul_y = sx_mul * fit, sy_mul * fit
        th = max(1, int(base_h * mul_y))                      # высота спрайта на экране
        # Ширина идёт от пропорций кадра: спрайт не должен искажаться, поэтому своя
        # настройка по X множит ту же высоту, а не задаёт ширину напрямую.
        tw = max(1, int(frame.get_width() * base_h * mul_x / frame.get_height()))
        img = pygame.transform.scale(frame, (tw, th))
        if f.facing < 0:
            img = pygame.transform.flip(img, True, False)
        sx = x + (f.w - tw) // 2 + dx  # центрируем по хитбоксу + сдвиг из настроек
        sy = y + f.h - th + dy   # низ спрайта + сдвиг Y из настроек
        self.screen.blit(img, (sx, sy))


    def panel_band(self, height, y=None):
        """Рисует чёрную полосу панели высотой height с прозрачностью PANEL_ALPHA.

        Полоса полупрозрачная, поэтому сквозь неё видно игру — это же она делает
        в панорамном режиме и в панели подсказок по Z. Поверхности кэшируются по
        высоте: иначе на каждом кадре создавался бы новый Surface с альфой.
        y — верх полосы; по умолчанию полоса прижата к низу кадра. Своё y нужно при
        анимации появления, когда панель выезжает снизу вверх (см. update_hud_anim).
        """
        band = self.panel_bands.get(height)
        if band is None:
            band = pygame.Surface((WIDTH, height), pygame.SRCALPHA)
            band.fill((0, 0, 0, PANEL_ALPHA))
            self.panel_bands[height] = band
        self.screen.blit(band, (0, HEIGHT - height if y is None else y))


    def hud_slide(self, height):
        """На сколько пикселей поднять панель при текущем состоянии анимации.

        0 — панель у нижнего края (не видна за кадром, если сдвиг = height),
        height — панель полностью на месте. Сдвиг считается от self.hud_anim (0..1),
        который двигает update_hud_anim.
        """
        return int(round((1.0 - self.hud_anim) * height))

    def update_hud_anim(self):
        """Плавно выдвигает панель информации снизу вверх и убирает её вниз.

        Состояние берётся из self.hud_on, поэтому переключатели (Z, Select, старт
        уровня) менять ничего не должны — достаточно переключить hud_on. Скорость
        задана в настройках: HUD_ANIM_FRAMES кадров на весь ход (больше — быстрее).
        Пока панель полностью уехала (hud_anim == 0), она вообще не рисуется.
        """
        target = 1.0 if self.hud_on else 0.0
        step = 1.0 / max(1, HUD_ANIM_FRAMES)
        if self.hud_anim < target:
            self.hud_anim = min(target, self.hud_anim + step)
        elif self.hud_anim > target:
            self.hud_anim = max(target, self.hud_anim - step)

    def draw_hud(self):
        """Панель информации: подсказка по управлению и текущий фон.

        Панель выезжает снизу вверх (см. update_hud_anim): текст и полоса рисуются
        с одним и тем же сдвигом, поэтому при появлении они едут вместе. Пока панель
        не выехала хотя бы на кадр — не рисуем ничего, иначе внизу кадра на миг
        мелькала бы пустая полоса.

        Больше ничего: здоровье, счёт, прогресс и отладочные режимы (масштаб,
        пол, анимации) убраны — на панели осталось только то, что нужно при
        настройке игры: как управлять и какой фон сейчас на экране.

        Текст — пиксельным шрифтом font_panel (Tiny5, кегль из настроек),
        капсом: строки собираются по ширине панели функцией pack_lines, одна
        длинная строка не влезала за края кадра.
        """
        if self.hud_anim <= 0.0:
            return
        if self.pad_connected:
            # Запустились с геймпада — на панели только геймпад. Служебные клавиши
            # (KEY_SYS) сюда НЕ добавляются: они описывают то, чего на геймпаде нет,
            # и в геймпадной подсказке выглядели как обрывок клавиатурной
            items = ["УПРАВЛЕНИЕ", *PAD_HELP]
            bg_hint = "LB/RB"
        else:
            # Запустились с клавиатуры. Блока в игре нет (анимации блока пока нет),
            # поэтому ↓/S в подсказку не вносим. Служебные клавиши — свои, геймпадных
            # кнопок для них здесь нет
            items = ["УПРАВЛЕНИЕ", *(KEY_HELP_1P if self.num_players == 1 else KEY_HELP_2P),
                     *KEY_SYS]
            bg_hint = "E"
        font = self.font_panel
        lines = pack_lines(items, font, WIDTH - 2 * PANEL_PAD)
        if self.par_back_name:            # текущий фон — последней строкой, жёлтым
            lines.append(f"ФОН: {self.par_back_name} ({bg_hint})")

        # Панель растёт под содержимое: HUD_H — минимальная высота, а если строк
        # больше (длинное имя фона, геймпадная раскладка) — берём по факту,
        # иначе нижние строки уезжали бы за край экрана
        step = font.get_linesize()
        self.hud_h = max(HUD_H, len(lines) * step + 8)
        slide = self.hud_slide(self.hud_h)
        if slide >= self.hud_h:
            return                       # панель ещё целиком за нижним краем кадра
        top = HEIGHT - self.hud_h + slide
        self.panel_band(self.hud_h, top)
        y = top + max(4, (self.hud_h - step * len(lines)) // 2)
        for line in lines:
            color = YELLOW if line.startswith("ФОН:") else WHITE
            t = font.render(line, True, color)
            self.screen.blit(t, (WIDTH // 2 - t.get_width() // 2, y))
            y += step