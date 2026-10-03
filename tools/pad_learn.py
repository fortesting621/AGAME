# -*- coding: utf-8 -*-
"""Проверка раскладки геймпада: показывает, какая кнопка/ось нажата прямо сейчас.

Запуск: python pad_learn.py
  ESC или Q — выход
  S        — сохранить отчёт в pad_report.txt (файл читается и переносится в settings.py)
  C        — сбросить счётчики нажатий и пики осей (если случайно нажали лишнее)

Зачем этот инструмент: у пультов индексы кнопок и осей не совпадают с документацией
и у разных моделей разные. Без замера любое «правильное» значение — угадывание:
например у SDL-клонов 4 = Select, 5 = Guide, 9 = LB, 10 = RB, а у Xbox-совместимых
4 = LB, 5 = RB, 6 = Start, 7 = Select. Поэтому игра слушает те индексы, которые
измерены здесь, и для пультов с другой раскладкой их правят в buttkikers/settings.py.

Что показывает экран:
  * кнопки — плитки по индексу: номер, число нажатий, подсветка нажатой, удержание
    отдельным цветом (свечение, пока кнопка зажата). Так видно и залипание кнопки,
    и что индекс не тот, какой ожидался;
  * оси — все оси с текущим значением и полосой от центра, плюс пик модуля за всю
    работу программы: по пику видно диапазон оси (у триггеров покой может быть 0.0,
    а нажатие уходит в +1.0, у клонов наоборот — поэтому в игре триггер ловится
    по модулю отклонения от покоя);
  * лог событий снизу — с временем от запуска: DOWN/UP кнопок, движение оси,
    значение «шапки» (крестовины).
Кнопки на тыльной стороне (плечи LB/RB, триггеры LT/RT, Share/Options) сюда
попадают так же, как все остальные: и как кнопки, и как оси — что именно приходит
от твоего пульта, покажет экран.
"""
import os
import sys
import time

import pygame

HERE = os.path.dirname(os.path.abspath(__file__))
# Шрифты и отчёт ищем в корне проекта (родительская папка), а если скрипт лежит
# рядом с шрифтами — берём свою папку. Так скрипт работает и из корня AGAME,
# и отдельно (например из tools/), не требуя копировать шрифты к нему
ROOTS = [HERE]
_parent = os.path.dirname(HERE)
if os.path.isdir(os.path.join(_parent, "fonts")):
    ROOTS.insert(0, _parent)
BASE_DIR = next((r for r in ROOTS if os.path.isdir(os.path.join(r, "fonts"))), HERE)
REPORT = os.path.join(BASE_DIR, "pad_report.txt")
LOG_LINES = 10          # строк в логе событий
HOLD_WARN = 1.5         # сек удержания кнопки, после чего подсветка меняется на «залипла»

W, H = 1280, 900
CELL_W, CELL_H = 118, 92
COLS = 9
BG = (24, 24, 30)
FG = (230, 230, 235)
DIM = (140, 140, 150)
ACCENT = (255, 214, 92)
HOLD = (255, 120, 90)
CELL = (44, 44, 54)
CELL_HIT = (90, 78, 34)
CELL_HOLD = (92, 44, 40)


def load_font(size):
    """Шрифт с кириллицей из проекта; если не открылся — системный моноширинный."""
    for name in ("Tiny5.ttf", "PressStart2P.ttf"):
        path = os.path.join(BASE_DIR, "fonts", name)
        if os.path.exists(path):
            try:
                return pygame.font.Font(path, size)
            except (pygame.error, OSError):
                break
    return pygame.font.SysFont("consolas", size)


class PadLearner:
    """Собирает события пульта и рисует их. Один пульт (индекс 0) — этого хватает,
    чтобы узнать раскладку; второй подключённый пульт показывается в шапке."""

    def __init__(self):
        pygame.init()
        pygame.display.set_caption("ПРОВЕРКА ГЕЙМПАДА — ESC выход, S сохранить отчёт")
        self.screen = pygame.display.set_mode((W, H))
        self.f_small = load_font(22)
        self.f_mid = load_font(30)
        self.f_big = load_font(38)

        self.t0 = time.time()
        self.now = lambda: time.time() - self.t0
        self.log = []            # строки лога (время, что произошло)
        self.btn_down = {}       # индекс кнопки -> время нажатия (для «удерживается»)
        self.counts = {}         # индекс кнопки -> число нажатий
        self.axes_val = []       # текущие значения осей
        self.axes_peak = []      # максимум модуля оси за всё время
        self.hat = None          # последнее значение «шапки» (крестовины)
        self.js = None
        self.hint = "НАЖМИ КНОПКИ ПУЛЬТА, ВКЛЮЧАЯ ТЫЛЬНУЮ СТОРОНУ"

        self.pads = []
        self.open_pads()

    def open_pads(self):
        """Открыть пульты и заполнить нули, чтобы отрисовка шла сразу по всем индексам.

        Подсистему джойстиков НЕ перезапускаем (joystick.quit() + init()): в pygame-ce
        повторный init() шлёт событие JOYDEVICEADDED, обработчик которого дёргает
        open_pads() снова — и скрипт забивается в бесконечный цикл событий, а окно
        закрывается. Вместо этого список пополняется по pygame.joystick.get_count():
        появившиеся пульты открываем, исчезнувшие закрываем.
        """
        pygame.joystick.init()
        count = pygame.joystick.get_count()
        while len(self.pads) < count:              # открылись новые пульты
            js = pygame.joystick.Joystick(len(self.pads))
            try:
                js.init()
            except pygame.error:
                pass
            self.pads.append(js)
        while len(self.pads) > count:              # пульты отключились
            js = self.pads.pop()
            try:
                js.quit()
            except pygame.error:
                pass
        self.js = self.pads[0] if self.pads else None

        self.n_btn = self.js.get_numbuttons() if self.js else 0
        self.n_ax = self.js.get_numaxes() if self.js else 0
        self.n_hat = self.js.get_numhats() if self.js else 0
        self.btn_down = {i: t for i, t in self.btn_down.items() if i < self.n_btn}
        self.counts = {i: self.counts.get(i, 0) for i in range(self.n_btn)}
        while len(self.axes_val) < self.n_ax:
            self.axes_val.append(0.0)
            self.axes_peak.append(0.0)
        self.name = self.js.get_name() if self.js else "НЕТ ПУЛЬТА"
        self.count = len(self.pads)
        print(f"[PAD] пульт: {self.name}  кнопок={self.n_btn} осей={self.n_ax} шапок={self.n_hat}")
        if self.count > 1:
            print(f"[PAD] всего пультов: {self.count} (смотрим первый)")
        if not self.pads:
            print("[PAD] ПУЛЬТ НЕ НАЙДЕН — подключи и нажми C или перезапусти скрипт")

    def add_log(self, text):
        self.log.append(f"{self.now():6.2f}s  {text}")
        del self.log[:-LOG_LINES]

    def reopen(self):
        """Перечитать список пультов: USB-пульт может проснуться позже, а засыпающий —
        остаться в списке SDL при мёртвых осях. По C делаем это явно."""
        self.open_pads()
        self.add_log("перечитали список пультов")

    def handle_event(self, e):
        if e.type == pygame.JOYBUTTONDOWN:
            self.counts[e.button] = self.counts.get(e.button, 0) + 1
            self.btn_down[e.button] = self.now()
            self.add_log(f"КНОПКА {e.button}  НАЖАТА  (всего нажатий: {self.counts[e.button]})")
            print(f"[PAD] btn{e.button} DOWN  нажатий: {self.counts[e.button]}")
        elif e.type == pygame.JOYBUTTONUP:
            held = self.now() - self.btn_down.pop(e.button, self.now())
            self.add_log(f"КНОПКА {e.button}  отпущена  (удержали {held:.2f} с)")
            print(f"[PAD] btn{e.button} UP    удержание {held:.2f} с")
        elif e.type == pygame.JOYAXISMOTION:
            if e.axis < len(self.axes_val):
                self.axes_val[e.axis] = e.value
                self.axes_peak[e.axis] = max(self.axes_peak[e.axis], abs(e.value))
            self.add_log(f"ОСЬ {e.axis} = {e.value:+.2f}")
            print(f"[PAD] axis{e.axis} = {e.value:+.3f}")
        elif e.type == pygame.JOYHATMOTION:
            self.hat = e.value
            self.add_log(f"ШАПКА = {e.value}")
            print(f"[PAD] hat{e.hat} = {e.value}")

    def poll_axes(self):
        """Значения осей читаем каждый кадр, а не только по событию: у части пультов
        триггеры приходят молча (события нет) — иначе мы бы их не увидели."""
        if not self.js:
            return
        for i in range(self.n_ax):
            try:
                v = self.js.get_axis(i)
            except pygame.error:
                continue
            self.axes_val[i] = v
            self.axes_peak[i] = max(self.axes_peak[i], abs(v))
        for i in range(self.n_hat):
            try:
                self.hat = self.js.get_hat(i)
            except pygame.error:
                break

    def save_report(self):
        """Записать разбор: что нажато и сколько раз, оси с пиком, шапка."""
        lines = [
            "РАЗБОР ГЕЙМПАДА (сделано pad_learn.py)",
            f"имя пульта : {self.name}",
            f"кнопок     : {self.n_btn}   осей: {self.n_ax}   шапок(крестовина): {self.n_hat}",
            "",
            "КНОПКИ (индекс: сколько нажато подряд за прогон)",
        ]
        for i in range(self.n_btn):
            lines.append(f"  btn{i:<3} нажатий: {self.counts.get(i, 0)}")
        lines += ["", "ОСИ (текущее значение / пик модуля за прогон)"]
        for i in range(self.n_ax):
            lines.append(f"  axis{i:<3} = {self.axes_val[i]:+.2f}   пик {self.axes_peak[i]:.2f}")
        lines += ["", f"ШАПКА (крестовина): {self.hat}"]
        lines += ["", "СОБЫТИЯ"]
        lines += [f"  {s}" for s in self.log]
        with open(REPORT, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        print(f"[PAD] отчёт сохранён: {REPORT}")

    def draw(self):
        self.screen.fill(BG)
        y = 16

        head = f"ГЕЙМПАД: {self.name}   КНОПОК {self.n_btn}   ОСЕЙ {self.n_ax}   КРЕСТОВИНА {self.n_hat}"
        if self.count > 1:
            head += f"   ПОДКЛЮЧЕНО ПУЛЬТОВ: {self.count}"
        self.blit(self.f_big, head, ACCENT, 16, y)
        y += 48

        self.blit(self.f_mid, "КНОПКИ (индекс / нажатий / удерживается)", FG, 16, y)
        y += 40
        for i in range(self.n_btn):
            cx = 16 + (i % COLS) * CELL_W
            cy = y + (i // COLS) * CELL_H
            held_for = self.now() - self.btn_down[i] if i in self.btn_down else None
            if held_for is not None and held_for >= HOLD_WARN:
                col = CELL_HOLD
            elif i in self.btn_down:
                col = CELL_HIT
            else:
                col = CELL
            pygame.draw.rect(self.screen, col, (cx, cy, CELL_W - 8, CELL_H - 8))
            self.blit(self.f_small, f"BTN {i}", FG, cx + 8, cy + 6)
            self.blit(self.f_mid, f"{self.counts.get(i, 0)}", ACCENT, cx + 8, cy + 34)
            if held_for is not None:
                col2 = HOLD if held_for >= HOLD_WARN else ACCENT
                self.blit(self.f_small, f"{held_for:.1f}s", col2, cx + 46, cy + 42)
        rows = max(1, (self.n_btn + COLS - 1) // COLS)
        y += rows * CELL_H + 8

        self.blit(self.f_mid, "ОСИ (полоса от центра = значение, справа пик)", FG, 16, y)
        y += 38
        bar_w = 420
        for i in range(self.n_ax):
            v = self.axes_val[i]
            col = ACCENT if abs(v) > 0.5 else FG
            self.blit(self.f_small, f"AXIS {i}", DIM, 20, y)
            pygame.draw.rect(self.screen, (60, 60, 72), (110, y + 6, bar_w, 20))
            mid = 110 + bar_w // 2
            pygame.draw.rect(self.screen, (110, 110, 125), (mid - 1, y + 2, 2, 28))
            half = int(abs(v) * (bar_w // 2 - 4))
            if half:
                rect = (mid, y + 6, half, 20) if v > 0 else (mid - half, y + 6, half, 20)
                pygame.draw.rect(self.screen, col, rect)
            self.blit(self.f_small, f"{v:+.2f}   пик {self.axes_peak[i]:.2f}", col, 110 + bar_w + 14, y)
            y += 34
        if not self.n_ax:
            self.blit(self.f_small, "осей нет — если это триггеры, они придут как КНОПКИ выше", DIM, 20, y)
            y += 30

        self.blit(self.f_mid, "СОБЫТИЯ", FG, 16, y)
        y += 36
        for i, s in enumerate(self.log):
            self.blit(self.f_small, s, FG if i >= len(self.log) - 2 else DIM, 20, y)
            y += 24

        self.blit(self.f_small,
                  self.hint + "   ||   ESC/Q - выход   S - сохранить отчёт   C - перечитать пульт/сброс",
                  ACCENT, 16, H - 34)
        pygame.display.flip()

    def blit(self, font, text, color, x, y):
        """Мелкий помощник: вывести текст цветом font в точку (x, y)."""
        img = font.render(str(text), True, color)
        self.screen.blit(img, (x, y))
        return img.get_width()

    def reset_counts(self):
        self.counts = {i: 0 for i in range(self.n_btn)}
        self.axes_peak = [0.0] * self.n_ax
        self.add_log("счётчики сброшены (C)")

    def run(self):
        clock = pygame.time.Clock()
        check_t = 0
        while True:
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    print("[PAD] событие QUIT — выход")
                    return
                if e.type == pygame.KEYDOWN:
                    if e.key in (pygame.K_ESCAPE, pygame.K_q):
                        return
                    elif e.key == pygame.K_s:
                        self.save_report()
                        self.hint = f"ОТЧЁТ СОХРАНЁН: {os.path.basename(REPORT)}"
                    elif e.key == pygame.K_c:
                        self.reopen()
                        self.reset_counts()
                    elif e.key == pygame.K_SPACE:
                        self.reopen()
                        self.hint = "ПЕРЕЧИТАЛ СПИСОК ПУЛЬТОВ (пробел)"
                elif e.type in (pygame.JOYDEVICEADDED, pygame.JOYDEVICEREMOVED):
                    self.reopen()
                elif e.type in (pygame.JOYBUTTONDOWN, pygame.JOYBUTTONUP,
                                pygame.JOYAXISMOTION, pygame.JOYHATMOTION):
                    self.handle_event(e)
            # Раз в 2 секунды сверяем список пультов: событие подключения приходит
            # не всегда, а пульт может проснуться уже после запуска скрипта
            check_t += 1
            if check_t >= 120:
                check_t = 0
                if pygame.joystick.get_count() != len(self.pads):
                    self.reopen()
            self.poll_axes()
            self.draw()
            clock.tick(60)


if __name__ == "__main__":
    try:
        PadLearner().run()
    except Exception:
        # Печатаем ошибку ДЛЯ СЕБЯ, а не просто выходим: sys.exit() в finally
        # подменяет исключение, и без этого блока скрипт молча закрывался бы с кодом 0
        import traceback
        traceback.print_exc()
    finally:
        pygame.quit()
        sys.exit()