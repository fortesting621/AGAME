"""Разделение кнопок геймпада, которые pygame отдаёт одинаковыми (idx5 = RB и задняя).

Зачем: SDL/pygame отдают и RB, и заднюю правую кнопку как btn5 — по индексу их
не различить, поэтому листание фона нельзя повесить на RB, не задев заднюю.
Но Windowsjoy.drv (winmm) отдаёт по одному биту на физическую кнопку: там
у кнопок свои номера. Этот скрипт их и покажет.

Запуск:  python tools/joy_probe.py
Нажимай по одной кнопке — в консоли появятся номера.
"""

import ctypes
from ctypes import wintypes

MAXPNTSLOT = 4
MAX_AXIS = 8

JOYERR_PARMS = 0x00000010

class JOYCAPSW(ctypes.Structure):
    _fields_ = [
        ("wMid", wintypes.WORD),
        ("wPid", wintypes.WORD),
        ("szPname", wintypes.WCHAR * 32),
        ("wXmin", wintypes.UINT),
        ("wXmax", wintypes.UINT),
        ("wYmin", wintypes.UINT),
        ("wYmax", wintypes.UINT),
        ("wZmin", wintypes.UINT),
        ("wZmax", wintypes.UINT),
        ("wNumButtons", wintypes.UINT),
        ("wPeriodMin", wintypes.UINT),
        ("wPeriodMax", wintypes.UINT),
        ("wRmin", wintypes.UINT),
        ("wRmax", wintypes.UINT),
        ("wUmin", wintypes.UINT),
        ("wUmax", wintypes.UINT),
        ("wVmin", wintypes.UINT),
        ("wVmax", wintypes.UINT),
        ("wCaps", wintypes.UINT),
        ("wMaxAxes", wintypes.UINT),
        ("wNumAxes", wintypes.UINT),
        ("wMaxButtons", wintypes.UINT),
        ("szRegKey", wintypes.WCHAR * 32),
        ("szOEMVxD", wintypes.WCHAR * 32),
    ]


class JOYINFOEX(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("dwXpos", wintypes.DWORD),
        ("dwYpos", wintypes.DWORD),
        ("dwZpos", wintypes.DWORD),
        ("dwRpos", wintypes.DWORD),
        ("dwUpos", wintypes.DWORD),
        ("dwVpos", wintypes.DWORD),
        ("dwButtons", wintypes.DWORD),
        ("dwButtonNumber", wintypes.DWORD),
        ("dwPOV", wintypes.DWORD),
        ("dwReserved1", wintypes.DWORD),
        ("dwReserved2", wintypes.DWORD),
    ]


winmm = ctypes.WinDLL("winmm")
winmm.joyGetNumDevs.restype = wintypes.UINT
winmm.joyGetDevCapsW.argtypes = [wintypes.UINT, ctypes.POINTER(JOYCAPSW), wintypes.WORD]
winmm.joyGetDevCapsW.restype = ctypes.c_uint
winmm.joyGetPosEx.argtypes = [wintypes.UINT, ctypes.POINTER(JOYINFOEX), wintypes.DWORD]
winmm.joyGetPosEx.restype = ctypes.c_uint

# Кнопки, которые чаще всего сзади/сбоку — подписываем заранее, если угадаем
GUESS = {
    0: "A (крест вниз)",
    1: "B (круг)",
    2: "X (квадрат)",
    3: "Y (треугольник)",
    4: "LB (левое плечо)",
    5: "RB (правое плечо)  <-- pygame тоже даёт idx5 на заднюю кнопку",
    6: "BACK / Share",
    7: "START",
    8: "L3 (клик левого стика)",
    9: "R3 (клик правого стика)",
    10: "GUIDE (центральная)",
    11: "доп. 1",
    12: "доп. 2",
    13: "доп. 3",
    14: "доп. 4",
    15: "доп. 5",
}


def main():
    devs = winmm.joyGetNumDevs()
    print(f"[JOY] устройств: {devs}")
    if not devs:
        print("Джойстик не найден — проверь, подключён ли пульт.")
        return

    uid = None
    caps = JOYCAPSW()
    for i in range(devs):
        if winmm.joyGetDevCapsW(i, ctypes.byref(caps), ctypes.sizeof(caps)) == 0:
            print(f"[JOY] #{i}: '{caps.szPname}' кнопок={caps.wNumButtons} "
                  f"осей={caps.wNumAxes} VID={caps.wPid:04X} PID={caps.wMid:04X}")
            if uid is None:
                uid = i

    if uid is None:
        print("Ни одно устройство не открылось.")
        return

    info = JOYINFOEX()
    info.dwSize = ctypes.sizeof(JOYINFOEX)
    info.dwFlags = JOYERR_PARMS
    counts = {}
    prev = 0

    print("\nНажимай по ОДНОЙ кнопке (в том числе задние). Выход — Ctrl+C.\n")
    try:
        import time
        while True:
            if winmm.joyGetPosEx(uid, ctypes.byref(info), JOYERR_PARMS) != 0:
                time.sleep(0.05)
                continue
            mask = info.dwButtons
            changed = mask ^ prev
            if changed:
                for bit in range(32):
                    if changed & (1 << bit):
                        on = bool(mask & (1 << bit))
                        word = "DOWN" if on else "UP"
                        if on:
                            counts[bit] = counts.get(bit, 0) + 1
                        print(f"  кнопка {bit:2d} {word:5s} "
                              f"{GUESS.get(bit, ''):<52s} всего: {counts.get(bit, 0)}")
                prev = mask
            time.sleep(0.01)
    except KeyboardInterrupt:
        print("\n[JOY] остановлено")


if __name__ == "__main__":
    main()
