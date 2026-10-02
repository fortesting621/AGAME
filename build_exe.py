# -*- coding: utf-8 -*-
"""Сборка игры в exe для запуска на другом компьютере.

Запуск:  python build_exe.py

Что делает:
  1. Проверяет, что PyInstaller установлен (если нет — ставит).
  2. Собирает в build/ButtKIkersUnited/ готовую игру: ButtKIkersUnited.exe
     + папка _internal с ресурсами (sprites, screen, sounds, fonts, mus)
     и кодом игры (папка buttkikers с модулями).
  3. Папку build/ButtKIkersUnited целиком копируют на любой компьютер с Windows
     и запускают ButtKIkersUnited.exe — Python там не нужен.

Почему папка, а не один файл: ресурсов 130 МБ, и в однофайловом виде они
распаковываются во временную папку при каждом запуске — старт занимает секунды.
С папкой запуск мгновенный.

Сборка идёт от buttkikers_united.py — это точка входа, она только импортирует
buttkikers.game; сам код игры PyInstaller подтянет сам по этим импортам.

Путь к ресурсам игра берёт из sys._MEIPASS (см. BASE_DIR в buttkikers/settings.py) —
поэтому игру можно запускать откуда угодно, exe не обязан лежать в папке AGAME.
"""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GAME = os.path.join(HERE, "buttkikers_united.py")
PKG = os.path.join(HERE, "buttkikers")
BUILD_DIR = os.path.join(HERE, "build")
OUT_NAME = "ButtKIkersUnited"
# Папки с ресурсами, которые кладём рядом с exe.
DATA_DIRS = ["sprites", "screen", "sounds", "fonts", "mus"]
# launch.pyw в exe не нужен, архив бэкапов — тоже.
EXCLUDE_DIRS = ["archive", "__pycache__", "build"]


def ensure_pyinstaller():
    """Ставит PyInstaller, если его нет."""
    try:
        import PyInstaller  # noqa: F401
        print("PyInstaller уже установлен")
    except ImportError:
        print("PyInstaller не найден, ставлю...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("PyInstaller установлен")


def main():
    if not os.path.exists(GAME):
        print(f"НЕ НАЙДЕН ИГРА: {GAME}")
        return 1
    if not os.path.isdir(PKG):
        print(f"НЕ НАЙДЕН ПАКЕТ С КОДОМ ИГРЫ: {PKG}")
        return 1

    ensure_pyinstaller()

    # Чистим прошлую сборку, чтобы в новую не попали удалённые файлы.
    if os.path.isdir(BUILD_DIR):
        print(f"Удаляю прошлую сборку: {BUILD_DIR}")
        shutil.rmtree(BUILD_DIR, ignore_errors=True)

    args = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",                    # без окна консоли
        "--name", OUT_NAME,
        "--onedir",                     # exe + папка _internal с ресурсами рядом
        "--distpath", BUILD_DIR,     # onedir сам создаст build/OUT_NAME/
        "--workpath", os.path.join(BUILD_DIR, "_work"),
        "--specpath", BUILD_DIR,
        "--paths", HERE,              # чтобы пакет buttkikers нашёлся рядом с точкой входа
    ]
    for d in DATA_DIRS:
        src = os.path.join(HERE, d)
        if os.path.isdir(src):
            # Данные кладутся внутрь exe (месту _MEIPASS), игра найдёт их через BASE_DIR.
            args += ["--add-data", f"{src}{os.pathsep}{d}"]
        else:
            print(f"ПРЕДУПРЕЖДЕНИЕ: нет папки {d} — пропускаю")

    args.append(GAME)

    print("\nСобираю... (это занимает минуту-две)\n")
    code = subprocess.call(args, cwd=HERE)
    if code != 0:
        print(f"\nСборка не удалась, код {code}")
        return code

    out_dir = os.path.join(BUILD_DIR, OUT_NAME)
    exe = os.path.join(out_dir, OUT_NAME + ".exe")
    if not os.path.exists(exe):
        print(f"\nГотовый exe не найден: {exe}")
        return 1

    size = 0
    for root, _, files in os.walk(out_dir):
        for fn in files:
            size += os.path.getsize(os.path.join(root, fn))
    print("\n" + "=" * 60)
    print(f"Готово: {exe}")
    print(f"Вся папка: {size / (1024 * 1024):.1f} МБ")
    print(f"Скопируй папку {OUT_NAME} на другой компьютер и запусти {OUT_NAME}.exe")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())