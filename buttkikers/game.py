# -*- coding: utf-8 -*-
"""Класс Game целиком: собирает части класса и запускает игру.

Сам класс разбит на несколько частей (миксинов), чтобы файл не разрастался:
загрузка ресурсов, мир (фон и слои), ход партии (переходы и музыка) и игровой
цикл. Все части — обычные классы без своего состояния: состояние лежит в self
и заполняется __init__ из game_load.py. Порядок в скобках задаёт, в каком
порядке искать метод, если он есть в нескольких частях.
"""

from .settings import *  # noqa: F401,F403
from .anim import *  # noqa: F401,F403

from .audio import GameAudio

from .game_load import GameLoad
from .game_world import GameWorld
from .game_flow import GameFlow
from .game_loop import GameLoop


class Game(GameAudio, GameLoad, GameWorld, GameFlow, GameLoop):
    """Игра: окно, ресурсы, бойцы, уровень и игровой цикл. Запуск — Game().run()."""