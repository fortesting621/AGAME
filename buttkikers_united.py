# -*- coding: utf-8 -*-
"""BEAT-EM-UP «ButtKIkers United» — запуск игры.

Точка входа: этот файл. Вся игра лежит в папке buttkikers рядом:
  buttkikers/settings.py  — все настройки и переключатели (их и правь)
  buttkikers/anim.py      — тайминги анимаций
  buttkikers/audio.py     — звук
  buttkikers/gamepad.py   — геймпад
  buttkikers/entities.py  — бойцы (Fighter / Player / Enemy)
  buttkikers/game_load.py — часть Game: загрузка ресурсов и создание окна
  buttkikers/game_world.py — часть Game: фон, слои параллакса, пол
  buttkikers/game_flow.py — часть Game: рестарт, переходы, заставка, музыка
  buttkikers/game_loop.py — часть Game: игровой цикл, логика кадра, отрисовка
  buttkikers/game.py      — класс Game целиком

Управление:
  P1: A/D — идти, W — прыжок, S — блок, J — кулак, L — нога, X/K — сильная нога
  P2: ←/→, ↑, ↓, N/B/M
  Геймпад: стик/крестовина + кнопки, правый триггер — перекат, левый — изоляция фона
  R — заново, Ctrl+R — перезапуск скрипта, Q — изоляция фона, +/- — масштаб фона,
  E — смена заднего фона, F — смена пола, Z — панель, ESC — выход

Запуск: launch.pyw (pythonw, без окна консоли) или python buttkikers_united.py
"""
from buttkikers.game import Game

if __name__ == "__main__":
    Game().run()