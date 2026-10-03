"""Проба индексов кнопок геймпада напрямую через XInput (без pygame/SDL).

Зачем: pygame/SDL отдаёт на этом пульте и RB, и заднюю правую кнопку как btn5 —
различить их нельзя. XInput (драйвер Windows для Xbox-совместимых пультов) индексы
не смешивает: 0=A, 1=B, 2=X, 3=Y, 4=LB, 5=RB, 6=BACK(Share), 7=START, 8=L3,
9=R3, 10=LS, 11=RS, а «центральная» кнопка Guide — 12 или вообще не отдаётся.
Нужен именно этот расклад, чтобы назначить LB/RB листание фона и не задевать задние
кнопки.

Запуск:  python tools/xinput_probe.py
Правило: нажимай по ОДНОЙ кнопке, одну секунду жди, потом следующую. В окне
появляется номер нажатой кнопки и её накопленные нажатия.
"""

import ctypes
from ctypes import wintypes

# --- структуры XInput --------------------------------------------------------

class XINPUT_GAMEPAD(ctypes.Structure):
    _fields_ = [
        ("wButtons", wintypes.WORD),
        ("bLeftTrigger", ctypes.c_ubyte),
        ("bRightTrigger", ctypes.c_ubyte),
        ("sThumbLX", ctypes.c_short),
        ("sThumbLY", ctypes.c_short),
        ("sThumbRX", ctypes.c_short),
        ("sThumbRY", ctypes.c_short),
    ]


class XINPUT_STATE(ctypes.Structure):
    _fields_ = [
        ("dwPacketNumber", wintypes.DWORD),
        ("gGamepad", XINPUT_GAMEPAD),
    ]


class XINPUT_CAPABILITIES(ctypes.Structure):
    class _Sub(ctypes.Structure):
        _fields_ = [
            ("wButtons", wintypes.WORD),
            ("bLeftTrigger", ctypes.c_ubyte),
            ("bRightTrigger", ctypes.c_ubyte),
            ("sThumbLX", ctypes.c_short),
            ("sThumbLY", ctypes.c_short),
            ("sThumbRX", ctypes.c_short),
            ("sThumbRY", ctypes.c_short),
        ]

    _fields_ = [
        ("Type", wintypes.DWORD),
        ("SubType", wintypes.DWORD),
        ("Flags", wintypes.DWORD),
        ("Gamepad", _Sub),
        ("Vibration", XINPUT_GAMEPAD),
    ]


XINPUT_GAMEPAD_TYPE = 1

# Подписи индексов (нумерация XInput, она совпадает с pygame для кнопок 0..11)
NAMES = {
    0: "A (крест вниз)",
    1: "B (круг)",
    2: "X (квадрат)",
    3: "Y (треугольник)",
    4: "LB (левое плечо)",
    5: "RB (правое плечо)",
    6: "BACK / Share",
    7: "START / Menu",
    8: "L3 (левый клик стика)",
    9: "R3 (правый клик стика)",
    10: "LS (клик левого триггера?)",
    11: "RS (клик правого триггера?)",
    12: "GUIDE (центральная)",
    13: "режим/подключение",
    14: "режим/подключение",
    15: "режим/подключение",
}


def _norm(v):
    """Приводит значение оси к -1.0..1.0 (raw -32767..32767)."""
    return max(-1.0, min(1.0, v / 32767.0))


def main():
    xinput = ctypes.WinDLL("xinput1_4")          # XInput для Xbox-совместимых пультов
    state = XINPUT_STATE()
    caps = XINPUT_CAPABILITIES()
    counts = {}
    prev = {}
    which = None

    for i in range(4):
        if xinput.XInputGetCapabilities(i, ctypes.byref(caps)) == 0:
            which = i
            break

    if which is None:
        print("ПУЛЬТ НЕ НАЙДЕН через XInput (xinput1_4)")
        print("Если пульт не Xbox-совместимый — XInput его не увидит, нужен другой путь.")
        return

    name = ctypes.create_string_buffer(260)
    xinput.XInputGetCapabilities(which, ctypes.byref(caps))

    print(f"[XINPUT] порт {which}, SubType={caps.SubType}, кнопок: {caps.Gamepad.wButtons:016b}")

    print("Нажимай по ОДНОЙ кнопке с паузой ~1 с. Закрыть окно — Alt+F4 или Ctrl+C.\n")
    try:
        while True:
            if xinput.XInputGetState(which, ctypes.byref(state)) != 0:
                xinput.XInputGetState = xinput.XInputGetState  # бездействие
                print("[XINPUT] пульт недоступен — переподключи")
                break

            g = state.gGamepad
            for bit in range(16):
                mask = 1 << bit
                down = bool(g.wButtons & mask)
                was = prev.get(bit, False)
                if down and not was:
                    counts[bit] = counts.get(bit, 0) + 1
                    print(f"  нажата idx{bit:2d}  {NAMES.get(bit, '?')}"
                          f"   всего нажатий: {counts[bit]}")
                prev[bit] = down

            # триггеры и стики — смотрим, если вдруг кнопка окажется осью
            lt, rt = g.bLeftTrigger / 255.0, g.bRightTrigger / 255.0
            if lt > 0.5:
                print(f"  левый триггер {lt:.2f}")
            if rt > 0.5:
                print(f"  правый триггер {rt:.2f}")

            import time
            time.sleep(0.01)
    except KeyboardInterrupt:
        print("\n[XINPUT] остановлено")


if __name__ == "__main__":
    main()
