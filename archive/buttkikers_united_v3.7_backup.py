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
MMA_DIR = "sprites/char/mma"       # анимированный .png сильного удара ногой (APNG); None/пусто — спрайт бега
KIK_DIR = "sprites/char/kik"       # анимированный .png обычного удара ногой (APNG); None/пусто — спрайт бега
SIT_DIR = "sprites/char/sit"       # анимированный .png приседа (APNG); None/пусто — спрайт бега
SIT_REVERSE = True             # True — развернуть кадры: в sit.png они идут задом наперёд
                               # (сначала стоя, потом приседание), а нужно наоборот
SIT_ANIM_FPS = 30            # скорость анимации приседа, кадров анимации в секунду
SIT_SPEED_MUL = 2.0            # насколько быстрее идёт приседание: 2.0 — вдвое быстрее обычного.
                               # Частота ПРОСМОТРА кадров при этом остаётся прежней (её задаёт
                               # MOVE_ANIM_FPS), ускорение делается пропуском кадров: переход
                               # занимает вдвое меньше кадров игры и показывает вдвое меньше
                               # поз. 1.0 — как было, без ускорения.
IDLE_ANIM_FPS = 30           # скорость анимации простоя, кадров анимации в секунду
GAMEPAD_ON = True            # True — управление с геймпада (гайд/крестовина/стик + кнопки)
# Кнопки-плечи/триггеры для листания задних фонов. Номера кнопок у падов разные,
# поэтому вынесены сюда: если на вашем паде они не те — правьте эти две строки.
# По умолчанию 4 = LB (плечо), 6 = LT (триггер) — как у Xbox-совместимых.
# При срабатывании печатается индекс кнопки — по нему видно, что нажато на самом деле.
PAD_BTN_BG_NEXT = (4, 5)     # LB / RB — следующий задний фон
PAD_BTN_BG_PREV = (7,)       # RT — предыдущий задний фон
PAD_BTN_ISOLATE = (6,)       # LT — изоляция фона (как Q)
PAD_DEADZONE = 0.35          # мёртвая зона стика: 0.35 = отклонение до 35% не считается нажатием
PAD_MENU_REPEAT = 18         # кадров до следующего пункта при удержании стика в меню (0.3 с)
ATTACK_ANIM_FPS = 20         # скорость анимаций ударов (во всех APNG ровно 30 fps)
ATTACK_FRAME_SKIP = 2        # показывать каждый N-й кадр анимации удара: 2 = через один (30 кадров → 15)
CHAR_SPRITE_SCALE = 1.5         # общий масштаб спрайтов бойцов: 1.0 — как есть, 1.5 — в полтора раза
RUN_SPRITE_DX = -10             # сдвиг спрайта бега по X, px (вместе со знаком по направлению взгляда)
MOVE_SRC_FPS = 30               # частота кадров в самих APNG (во всех анимациях ровно 30 fps) —
                               # это исходная скорость, по ней считается длительность цикла
                               # бега и прыжка; правьте только если перезапишете анимации
MOVE_ANIM_FPS = 21             # ОДИН переключатель для всех анимаций движения: сколько кадров
                               # реально показывается в секунду. Работает сразу на бег,
                               # крадущуюся ходьбу, прыжок, присед (в т.ч. подъём) и покой.
                               # Длительность от этого НЕ меняется (цикл бега и прыжок занимают
                               # столько же, сколько при 30): промежуточные кадры пропускаются,
                               # показанный держится дольше — ноги не рассинхронизируются с
                               # ходьбой, анимация просто становится «ступенчатой».
                               # 30 — все кадры (как сейчас). Можно ставить любое число, например
                               # 21 (примерно через один), 15, 12, 10: чем меньше — тем реже
                               # обновляется картинка.
MOVE_ANIM_JUMP_FPS = 26         # отдельный счётчик только для прыжка: сколько его кадров
                               # показывается в секунду. Прыжок — быстрое движение, там
                               # прореживание видно сильнее всего, поэтому его частота задаётся
                               # отдельно от MOVE_ANIM_FPS. Длительность и дальность прыжка от
                               # любого из этих значений НЕ меняются. 30 — все кадры, как было.
JUMP_SPRITE_DX = -20            # сдвиг спрайта прыжка по X, px (вместе со знаком по направлению взгляда)
MMA_SPRITE_DX = -8             # сдвиг спрайта удара ногой по X, px (вместе со знаком по направлению взгляда)
KIK_SPRITE_DX = -8             # сдвиг спрайта обычного удара ногой по X, px
CRWALK_DIR = "sprites/char/crwalk"  # анимированный .png крадущейся ходьбы (APNG)
CRWALK_ANIM_FPS = 30          # скорость анимации крадущейся ходьбы, кадров в секунду.бег (30)
CRWALK_SPEED_MUL = 0.5        # скорость перемещения в крадущейся ходьбе: 0.5 = вдвое
                               # медленнее обычной ходьбы
CRWALK_SPRITE_DX = -10        # сдвиг спрайта крадущейся ходьбы по X, px
# Положение спрайта для каждой анимации: (сдвиг X, сдвиг Y, знак X по направлению взгляда).
# Правьте эти числа — на экране сразу сдвинется нужная анимация. Состояния: idle, run,
# jump, sit, crwalk, punch, kik, mma. Y положительный — вниз.
SPRITE_OFFSET = {
    "idle":   (0, 0, False),
    "run":    (-15, 0, True),
    "jump":   (JUMP_SPRITE_DX, 0, True),
    "sit":    (-30, 0, True),
    "crwalk": (CRWALK_SPRITE_DX, 0, True),
    "punch":  (0, 0, False),
    "kik":    (KIK_SPRITE_DX, 0, True),
    "mma":    (MMA_SPRITE_DX, 0, True),
}
# Масштаб спрайта — свой для каждой анимации, ключи те же, что у SPRITE_OFFSET.
# Значение: одно число на обе оси или пара (X, Y), если нужно растянуть только по одной оси,
# например "jump": (0.7, 1.2) — ниже и выше. Всё это умножается на общий CHAR_SPRITE_SCALE и на
# масштаб самого бойца, так что 1.0 — «как раньше». Отсутствующий ключ — без своего множителя.
SPRITE_SCALE = {
    "idle":   1.0,
    "run":    0.96,
    "jump":   0.98,
    "sit":    0.96,
    "crwalk": 0.96,
    "punch":  1.0,
    "kik":    1.0,
    "mma":    1.0,
}
CHAR_SPRITE_H = 82              # высота спрайта бойца в пикселях (до применения CHAR_SPRITE_SCALE)
FOOTSTEP_TIME = 20             # кадров между шагами (цикл бега 40 кадров → шаг каждые 20)


                                                                                                                        # --- Настройки звука ---
                                                                                        
                                                                                                                                                                                
SOUND_ON = True             # главный выключатель: False — глушит всё (музыку и звуки)
MUSIC_ON = True             # True — фоновая музыка, False — без неё
MUSIC_FILE = "start-redused-noise.wav"   # трек фоновой музыки в меню (папка mus)
MUSIC_VOL = 1             # громкость фоновой музыки: трек меню
LEVEL_MUSIC = "sounds/lev1_forest_loop.mp3"   # трек первого уровня (играет только в игре).
                                           # Версия _loop: из оригинала вырезано по 3 с с краёв,
                                           # добавлено нарастание 3 с в начале и затухание 3 с в
                                           # конце — стык при повторе бесшовный.
LEVEL_MUSIC_VOL = 0.6       # громкость фоновой музыки: трек уровня
MUSIC_FADE_STEP = 0.03      # насколько громкость меняется за кадр (0.03 → примерно 0.5 с)
SFX_ON = True                # True — проигрывать звуки нажатий, False — без них
SFX_START = "start nes-sfx29.wav"       # звук нажатия START (папка sounds)
SFX_START_VOL = 0.3         # громкость звука нажатия START
SFX_MENU = "menu.mp3"                  # звук навигации в меню (папка sounds)
SFX_MENU_KEY = "menu"                  # если файла с именем SFX_MENU нет — берём из sounds любой
                                       # звук, у которого слово "menu" есть в имени (любой формат)
SFX_FOOTSTEP = "Footstep__005.wav"      # звук шагов (папка sounds)
SFX_EXT = (".wav", ".mp3", ".ogg", ".flac")   # какие расширения считаются звуковыми файлами
CHAR_SOUND_DIR = "sounds/char"   # папка со звуками персонажа (по одному файлу на анимацию)
# Звук на каждое действие бойца: ключ — действие, значение — имя файла в CHAR_SOUND_DIR
# (по имени анимации: сильная нога — mma.mp3, а не kick). Если файла с точным именем нет,
# ищем в папке любой файл, у которого это слово есть в имени (любой формат из SFX_EXT).
# Пустая строка — действие идёт молча.
CHAR_SFX = {
    "jump": "jump.mp3",         # прыжок
    "punch": "punch.mp3",       # удар кулаком
    "kik": "kik.mp3",           # обычная нога
    "kick": "mma.mp3",          # сильная нога (анимация mma)
}
CHAR_SFX_VOL = 0.45             # общая громкость звуков персонажа (шаги — 0.25, меню — тише)
# Задержка перед звуком удара в миллисекундах — строкой, как просил пользователь.
# "0" — звук сразу в начале анимации. Непустое значение: звук откладывается на указанное
# число миллисекунд (считается от начала удара), чтобы попасть в момент удара по анимации.
# Пересчёт: кадр задержки = миллисекунды / 1000 * FPS.
# У сильной ноги (mma) своя задержка — она дольше замахивается, звук нужен позже.
CHAR_SFX_DELAY_MS = {
    "jump": "0",           # прыжок — сразу
    "punch": "0",          # кулак — сразу
    "kik": "0",            # обычная нога — сразу
    "kick": "180",         # сильная нога (mma) — через 180 мс, на удар
}


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
BACK_SCALE = 0.8            # стартовый масштаб заднего плана: 1.0 — как есть, 0.5 — вдвое меньше.
                            # Фон рисуется как объект уровня: верх прижат к верхней границе
                            # окна, обрезки нет — не влезшее просто уходит за край экрана.
                            # Во время игры масштаб меняется клавишами +/- (см. ниже)
BACK_SCALE_STEP = 0.05      # шаг изменения масштаба клавишами +/- (5%)
BACK_SCALE_MIN = 0.05       # нижняя граница масштаба (1/20 натуральной величины)
BACK_SCALE_MAX = 10.0       # верхняя граница масштаба (x10)
# Собственный масштаб фона можно задать суффиксом в самом имени — и у файла, и у папки:
#   "1_new river_80"  -> 0.80   "3_night river_50"  -> 0.50   "2_river_125" -> 1.25
# Считывается число ПОСЛЕДНИМ "_NNN" в имени (точку тоже можно: "_0.8").
# Если суффикса нет — берётся BACK_SCALE. Клавиши +/- потом множат это значение.
BACK_SCALE_SUFFIX = True    # True — читать масштаб фона из суффикса имени
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
INTRO_BLACK_TIME = 30        # кадров чистого чёрного экрана перед проявлением картинки уровня
INTRO_FADE_TIME = 45         # кадров на ОДИН цикл: появление и затухание одинаковой длины
INTRO_FADE_STEPS = 6         # тактов (ступеней) за этот цикл: 1 или 0 — плавно, 8 — крупными ступенями
INTRO_SHOW_TIME = 180         # кадров, сколько картинка уровня висит, прежде чем затемняться
INTERSCREEN_DIR = "screen/intersceen"   # папка с заставками уровней (картинка с именем уровня)
LEVEL_INTERSCREEN = "lev1"   # имя заставки: ищется файл <имя>.(jpg|png|...) в INTERSCREEN_DIR/<имя>/
# Слой ПОВЕРХ заставки — отдельная картинка с текстом (<папка заставки>/text.(png|...)).
# Рисуется поверх основной картинки, обе части проявляются/затухают вместе (общая альфа).
# None или "" — слой выключен. Масштабируется по той же схеме, что и заставка.
LEVEL_INTERSCREEN_TEXT = "text"
# Слой текста живёт по своему ритму, отдельно от заставки: ждёт INTRO_TEXT_DELAY кадров,
# потом мягко проявляется (INTRO_TEXT_FADE), держится INTRO_TEXT_SHOW_TIME и гаснет.
INTRO_TEXT_DELAY = 90          # задержка перед появлением текста (1.5 с)
INTRO_TEXT_FADE = 40        # кадров на появление и на затухание текста
INTRO_TEXT_SHOW_TIME = 150   # сколько текст держится на экране (2.5 с)
LEVEL_NUM = "УРОВЕНЬ ПЕРВЫЙ"   # номер уровня на заставке (если картинки-заставки нет)
LEVEL_NAME = "ДОРОГА В РАЙ"    # название уровня на заставке (если картинки-заставки нет)
# Заставка уровня идёт по схеме: чёрный экран (INTRO_BLACK_TIME) -> появление картинки ->
# показ (INTRO_SHOW_TIME) -> затухание в темноту. Один цикл перехода длится INTRO_FADE_TIME
# кадров и разбит на INTRO_FADE_STEPS тактов: каждый такт держит свою альфу, альфа между
# тактами не меняется (дискретный переход). 0 или 1 такт = плавное затухание без ступеней.
INTRO_FADE_FRAMES = max(1, INTRO_FADE_TIME)   # кадров на один цикл появления/затухания
INTRO_FADE_TICK = max(1, INTRO_FADE_FRAMES // max(1, INTRO_FADE_STEPS))   # кадров в одном такте
INTRO_TIME = INTRO_BLACK_TIME + 2 * INTRO_FADE_FRAMES + INTRO_SHOW_TIME
GRAVITY = 2.0               # ускорение свободного падения
MOVE = 12.0                  # скорость ходьбы
# Прыжок. Вертикального перемещения нет: прыжок целиком нарисован в самой анимации
# jump.png, поэтому боец остаётся на линии пола и по вертикали не сдвигается.
# Задаётся только длина прыжка — сколько боец пролетает по горизонтали за время анимации.
# Длительность задаёт сама анимация (JUMP_ANIM_FPS), поэтому скорость зависит от длины:
#   скорость в прыжке = JUMP_LEN / jump_duration()
#   длина под скорость ходьбы = MOVE * jump_duration()  (сейчас 12 * 62 = 744 px)
# Возьмёшь длину меньше — прыжок поедет медленнее ходьбы и будет выглядеть как замедление.
JUMP_LEN = 744               # длина прыжка вперёд/назад, px (0 — прыжок выключен)
JUMP_ANIM_FPS = 30           # скорость проигрывания анимации прыжка, кадров/с (как в самом PNG)
JUMP_COOLDOWN = 1.5          # секунд между прыжками: кулдаун от взлёта до следующего; 0 — без ограничения
ENEMY_JUMP_RATIO = 0.8       # во сколько раз короче прыжок врага
JUMP_COOLDOWN_FRAMES = int(round(JUMP_COOLDOWN * FPS))      # кулдаун в кадрах
JUMP_ANIM_N = 0              # кадров в загруженной анимации прыжка; заполняется при загрузке
RUN_ANIM_N = 0               # кадров в загруженной анимации бега; заполняется при загрузке
SIT_ANIM_N = 0               # кадров в загруженной анимации приседа; заполняется при загрузке
CRWALK_ANIM_N = 0            # кадров в загруженной анимации крадущейся ходьбы; заполняется при загрузке
PUNCH_ANIM_N = 0             # кадров в загруженной анимации удара рукой; 0 — анимации нет
PUNCH_FALLBACK = 7           # длительность удара в кадрах, если анимация не загрузилась
MMA_ANIM_N = 0               # кадров в загруженной анимации сильного удара ногой; 0 — анимации нет
KIK_ANIM_N = 0               # кадров в загруженной анимации обычного удара ногой; 0 — анимации нет
KICK_FALLBACK = 12           # длительность удара ногой в кадрах, если анимация не загрузилась


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


def move_shown(total, fps=0):
    """Сколько кадров анимации реально показывается при заданной частоте (fps = 0 -> MOVE_ANIM_FPS).

    При частоте MOVE_SRC_FPS (30) показываются все кадры — как было раньше. При меньшем значении
    часть кадров пропускается, а длительность анимации (цикла, прыжка, приседа) от этого НЕ
    меняется: показанный кадр просто держится дольше.
    """
    if total <= 0:
        return 0
    rate = float(fps) if fps else float(MOVE_ANIM_FPS)
    return max(1, min(total, int(round(total * rate / float(MOVE_SRC_FPS)))))


def move_frame_index(game_frame, phase, total):
    """Номер кадра ЦИКЛИЧЕСКОЙ анимации движения: бег, крадущаяся ходьба, покой.

    Позиция считается в показах, а не в кадрах анимации: счётчик обновлений идёт со скоростью
    MOVE_ANIM_FPS (при 30 и FPS = 60 — каждый второй игровой кадр, как раньше), а на экран
    выводится только move_shown(total) кадров из total. Цикл поэтому занимает те же
    total / MOVE_SRC_FPS секунд — меняется только частота обновления. phase — сдвиг фазы в
    кадрах исходной анимации (у каждого игрока свой, чтобы не шли в унисон).
    """
    shown = move_shown(total)
    if shown <= 0:
        return 0
    tick = int(game_frame * float(MOVE_ANIM_FPS) / FPS)   # счётчик обновлений анимации
    pos = (tick + phase * shown // total) % shown          # позиция в цикле
    return int(round(pos * total / float(shown))) % total  # кадр анимации для этой позиции


def move_frame_thin(progress, total, fps=0):
    """Номер кадра ОДНОРАЗОВОЙ анимации движения по пройденной части 0..1 — прыжок, присед.

    Первый и последний кадры показываются всегда (поза в начале и в конце важна), между ними —
    только move_shown(total, fps) кадров вместо всех. Длительность задаёт вызывающий код, она не
    меняется: прыжок летит как раньше, присед длится как раньше.
    fps = 0 -> общий MOVE_ANIM_FPS; для прыжка передаётся MOVE_ANIM_JUMP_FPS.
    """
    if total <= 1:
        return 0
    shown = move_shown(total, fps)
    if shown <= 1:
        return 0
    pos = min(shown - 1, int(max(0.0, min(1.0, float(progress))) * shown))
    return min(total - 1, int(round(pos * (total - 1) / float(shown - 1))))


def move_frame_once(elapsed, dur, total, fps=0):
    """Номер кадра одноразовой анимации по прошедшим кадрам игры: elapsed из dur.

    Для прыжка: dur = self.jump_dur (его задаёт jump_duration()), total = self.jump_n,
    fps = MOVE_ANIM_JUMP_FPS (у прыжка своя частота, у остального — общая MOVE_ANIM_FPS).
    """
    return move_frame_thin(elapsed / float(max(1, dur)), total, fps)


def _scale_txt(sc):
    """Подпись множителя масштаба для HUD: число или «X/Y» для пары осей."""
    if isinstance(sc, (tuple, list)):
        return f"{float(sc[0]):.2f}/{float(sc[1]):.2f}"
    return f"{float(sc):.2f}" if sc else "1.00"


def find_sfx(name, keyword="", subdir=""):
    """Путь к звуковому файлу из папки sounds (или sounds/subdir) или None.

    Сначала ищется файл с точным именем name. Если его нет — ищется любой звуковой файл
    (расширения из SFX_EXT), у которого keyword встречается в имени без учёта регистра.
    Благодаря этому звук подхватывается и как "menu.mp3", и как "Menu SFX 23.wav" —
    важен только формат и нужное слово в имени. keyword пустой — ищем только точное имя.
    subdir — вложенная папка (например "char" для звуков персонажа), без неё ищем в sounds.
    Можно указать как "char", так и "sounds/char" — префикс sounds/ не дублируется.
    """
    if not name and not subdir:
        return None
    sub = subdir.replace("/", os.sep).replace("\\", os.sep)
    if sub.lower().startswith("sounds" + os.sep):
        sub = sub[len("sounds") + 1:]          # уже с префиксом sounds — не добавляем второй раз
    sdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sounds", sub)
    exact = os.path.join(sdir, name)
    if os.path.exists(exact):
        return exact
    key = keyword.lower()
    if not key:
        return None
    try:
        found = sorted(n for n in os.listdir(sdir)
                       if n.lower().endswith(SFX_EXT)
                       and key in os.path.splitext(n)[0].lower())
    except OSError:
        return None
    return os.path.join(sdir, found[0]) if found else None


# ---------------------------------------------------------------- геймпад
# Геймпад в Windows через pygame: индекс 0 достаётся первому игроку, индекс 1 — второму.
# Раскладка кнопок стандартная (XInput/DInput): 0=A, 1=B, 2=X, 3=Y, 7=Start, 8=Back.
# На стике работает ось 0 (влево-вправо) и ось 1 (вверх-вниз), плюс крестовина (hat 0).
PADS = []                     # открытые геймпады: [0] -> P1, [1] -> P2


def init_gamepads():
    """Открыть геймпады. Возвращает список подключённых (максимум 2: P1 и P2)."""
    global PADS
    PADS = []
    if not GAMEPAD_ON:
        return PADS
    try:
        pygame.joystick.init()
        count = pygame.joystick.get_count()
    except pygame.error:
        return PADS
    for i in range(min(count, 2)):
        try:
            js = pygame.joystick.Joystick(i)
            js.init()
            PADS.append(js)
        except pygame.error:
            pass
    return PADS


def pad_state(idx):
    """(влево, вправо, вверх, вниз, кулак, обычная нога, сильная нога) с геймпада idx (0 = P1, 1 = P2)."""
    if not GAMEPAD_ON or idx >= len(PADS):
        return (False,) * 7
    js = PADS[idx]
    dz = PAD_DEADZONE

    def ax(i):
        return js.get_axis(i) if i < js.get_numaxes() else 0.0

    def btn(i):
        return bool(js.get_button(i)) if i < js.get_numbuttons() else False

    try:
        hx, hy = js.get_hat(0) if js.get_numhats() else (0, 0)
    except pygame.error:
        hx, hy = 0, 0
    left = ax(0) < -dz or hx < 0
    right = ax(0) > dz or hx > 0
    up = ax(1) < -dz or hy > 0 or btn(0)    # стик, крестовина или кнопка A (A = только прыжок)
    down = ax(1) > dz or hy < 0
    # A (btn 0) намеренно НЕ входит в удар рукой: она уже прыжок, иначе одно
    # нажатие давало прыжок + удар. Удар рукой — только X (btn 2), как J на клавиатуре.
    punch = btn(2)                   # X — удар рукой (как J)
    kik = btn(1)                    # B — обычный удар ноги (как L)
    kick = btn(3)                   # Y — сильный удар ногой (как K)
    return left, right, up, down, punch, kik, kick


def pad_menu(idx):
    """(вверх, вниз, старт) с геймпада — для навигации в главном меню."""
    if not GAMEPAD_ON or idx >= len(PADS):
        return False, False, False
    js = PADS[idx]
    dz = PAD_DEADZONE

    def ax(i):
        return js.get_axis(i) if i < js.get_numaxes() else 0.0

    def btn(i):
        return bool(js.get_button(i)) if i < js.get_numbuttons() else False

    try:
        hx, hy = js.get_hat(0) if js.get_numhats() else (0, 0)
    except pygame.error:
        hx, hy = 0, 0
    up = ax(1) < -dz or hy > 0 or btn(3)
    down = ax(1) > dz or hy < 0 or btn(1)
    start = btn(0) or btn(7)        # A или Start — начать игру
    return up, down, start


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
        self.attack = None             # текущая атака: "punch" / "kik" / "kick" / None
        self.attack_timer = 0          # оставшиеся кадры атаки
        self.attack_hit = False        # уже ли атака попала в цель (один удар за анимацию)
        self.cooldown = 0              # кадры перезарядки между атаками
        self.combo = 0                 # счётчик серии ударов (усиливает урон)
        self.combo_timeout = 0         # кадр, после которого серия обнуляется
        self.flinch = 0                # кадры "отшатывания" от удара (нельзя действовать)
        self.knock = 0                 # сила отталкивания от удара
        self.was_moving = False        # двигался ли боец в этом кадре (для анимации бега)
        self.sit_t = 0                 # кадр анимации приседа: 0 — стоит, SIT_ANIM_N-1 — сел
        self.sit_dir = 0               # 1 — садится, -1 — встаёт, 0 — стоит
        self.sit_acc = 0.0             # накопитель дробного шага таймера приседа (SIT_SPEED_MUL)
        self.game = None                # ссылка на Game (для проигрывания SFX персонажа)
        self.crouch_walking = False    # идёт ли крадущейся ходьбой (анимация crwalk)
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
            return PUNCH_ANIM_N
        if self.attack == "kik":
            return KIK_ANIM_N
        return MMA_ANIM_N

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
        self.jump_n = JUMP_ANIM_N
        self.jump_dur = jump_duration(self.jump_n)
        self.jump_speed = length / self.jump_dur
        self.jump_frame = 0
        self.vel_y = 0
        # Звук прыжка (задержка — из CHAR_SFX_DELAY_MS, сейчас "0")
        if getattr(self, "game", None):
            self.game.play_sfx_delayed("jump")

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
                # был 0-й кадр бега, а не случайный кадр цикла.
                self.run_phase = -(frame // 2) % max(1, RUN_ANIM_N)
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
        gp_l, gp_r, gp_u, gp_d, gp_p, gp_n, gp_k = pad_state(self.pnum)
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
            kik = keys[pygame.K_l] or gp_n        # L — обычный удар ноги
            kick = keys[pygame.K_x] or keys[pygame.K_k] or gp_k
        else:                                    # P1 в кооперативе: только WASD + J/K/L
            left = keys[pygame.K_a] or gp_l
            right = keys[pygame.K_d] or gp_r
            up = keys[pygame.K_w] or gp_u
            down = keys[pygame.K_s] or gp_d
            punch = keys[pygame.K_j] or gp_p
            kik = keys[pygame.K_l] or gp_n
            kick = keys[pygame.K_k] or gp_k

        self.crouching = False
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
        seated_now = down and self.sit_t >= SIT_ANIM_N - 1
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
                # удары только с земли: в прыжке не бьём ни кулаком, ни ногой
                if punch:
                    self.try_attack("punch", frame)
                elif kik:
                    self.try_attack("kik", frame)
                elif kick:
                    self.try_attack("kick", frame)
        # для анимации бега: двигались и стоим на земле (и не заперты в недосиженном приседе)
        self.was_moving = ((left or right) and self.on_ground and self.flinch <= 0
                           and not sit_locked)
        # Крадущаяся ходьба — только когда реально сел и поехал: тогда рисуем crwalk
        # вместо спрайта бега. Пока не досел (sit_locked) — обычный спрайт стоя.
        self.crouch_walking = bool(crouch_walk and self.on_ground)
        # Анимация приседа: садится (кадры вперёд), держит позу, встаёт (кадры назад).
        # Кадры загружены уже развёрнутыми (SIT_REVERSE), так что 0 — стоя, конец — сел.
        n = SIT_ANIM_N
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
        global PUNCH_ANIM_N, MMA_ANIM_N, KIK_ANIM_N, RUN_ANIM_N, JUMP_ANIM_N, SIT_ANIM_N, CRWALK_ANIM_N
        pygame.init()
        self.pad_nav_cd = 0           # кадры до следующего пункта меню при удержании стика
        self.pad_info = ""             # подсказка про геймпад для нижней панели
        pads = init_gamepads()
        if pads:
            for i, js in enumerate(pads):
                print(f"[DEBUG] геймпад P{i + 1}: {js.get_name()}")
            self.pad_info = ("ГЕЙМПАД: стик/крестовина   A — прыжок   X — кулак   "
                             "B — нога   Y — нога сильная   "
                             "LB/RB — фон вперёд   RT — назад   LT — изоляция фона   "
                             "Start — заставка")
        elif GAMEPAD_ON:
            print("[DEBUG] геймпад не найден — играем с клавиатуры")
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
        self.sfx_queue = []            # отложенные звуки персонажа: [кадров_осталось, имя]
        if self.audio_ok and SFX_ON:
            for key, fn, word in (("start", SFX_START, ""),
                                  ("menu", SFX_MENU, SFX_MENU_KEY),
                                  ("step", SFX_FOOTSTEP, "")):
                sfx_path = find_sfx(fn, word)
                if not sfx_path:
                    print(f"[SFX] нет файла: {key} — {fn}")
                    continue
                try:
                    self.sfx[key] = pygame.mixer.Sound(sfx_path)
                    print(f"[SFX] {key}: {os.path.basename(sfx_path)}")
                except pygame.error:
                    print(f"[SFX] не читается: {sfx_path}")
            if "step" in self.sfx:
                self.sfx["step"].set_volume(0.25)      # шаги не должны перебивать игру
            if "start" in self.sfx:
                self.sfx["start"].set_volume(SFX_START_VOL)   # нажатие START — тише
            # Звуки персонажа (sounds/char): прыжок и удары. Ключ в CHAR_SFX — действие,
            # файл ищется по имени анимации (сильная нога -> mma), плюс запасной поиск
            # по слову в имени, чтобы файл можно было переименовать.
            for key, fn in CHAR_SFX.items():
                if not fn:
                    continue
                sfx_path = find_sfx(fn, os.path.splitext(fn)[0], CHAR_SOUND_DIR)
                if not sfx_path:
                    print(f"[SFX] нет звука персонажа: {key} — {fn}")
                    continue
                try:
                    snd = pygame.mixer.Sound(sfx_path)
                    snd.set_volume(CHAR_SFX_VOL)
                    self.sfx[key] = snd
                    print(f"[SFX] {key}: {os.path.basename(sfx_path)} ({CHAR_SOUND_DIR})")
                except pygame.error:
                    print(f"[SFX] не читается: {sfx_path}")
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
        # Заставка уровня из screen/intersceen грузится один раз и масштабируется под окно.
        self.interscreen_img = None
        self.interscreen_loaded = False
        # Слой с текстом поверх заставки (text.png) — тоже грузится один раз
        self.interscreen_text_img = None
        self.interscreen_text_loaded = False
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
        # Анимация приседа: первый анимированный .png из папки SIT_DIR, тем же порядком.
        # В sit.png кадры идут задом наперёд (сначала стоя, потом приседание), поэтому при
        # SIT_REVERSE разворачиваем их: 0 — стоя, последний — сел.
        self.sit_frames = []
        self.sit_name = ""
        if SIT_DIR:
            sdir = os.path.join(base, *SIT_DIR.replace("\\", "/").split("/"))
            if os.path.isdir(sdir):
                sentries = sorted(
                    (self.prefix_order(name), name, os.path.join(sdir, name))
                    for name in os.listdir(sdir) if name.lower().endswith(".png")
                )
                for order, name, full in sentries:
                    frames = self.trim_frames(self.load_apng_frames(full))
                    if frames:
                        self.sit_name, self.sit_frames = name, frames
                        break
        SIT_ANIM_N = len(self.sit_frames)
        if SIT_REVERSE and self.sit_frames:
            self.sit_frames = self.sit_frames[::-1]
        if self.sit_frames:
            print(f"[DEBUG] присед: {self.sit_name} — {SIT_ANIM_N} кадров "
                  f"@ {SIT_ANIM_FPS} fps"
                  + ("  (кадры развёрнуты: sit.png шёл задом наперёд)" if SIT_REVERSE else ""))
        # Анимация крадущейся ходьбы: первый анимированный .png из папки CRWALK_DIR.
        # Показываем ВСЕ кадры (без прореживания, как у ударов) и идём вдвое медленнее,
        # поэтому анимация проходится вдвое быстрее бега — иначе она «зависла» бы.
        self.crwalk_frames = []
        self.crwalk_name = ""
        if CRWALK_DIR:
            cdir = os.path.join(base, *CRWALK_DIR.replace("\\", "/").split("/"))
            if os.path.isdir(cdir):
                centries = sorted(
                    (self.prefix_order(name), name, os.path.join(cdir, name))
                    for name in os.listdir(cdir) if name.lower().endswith(".png")
                )
                for order, name, full in centries:
                    frames = self.trim_frames(self.load_apng_frames(full))
                    if frames:
                        self.crwalk_name, self.crwalk_frames = name, frames
                        break
        CRWALK_ANIM_N = len(self.crwalk_frames)
        if self.crwalk_frames:
            print(f"[DEBUG] крадущаяся ходьба: {self.crwalk_name} — {CRWALK_ANIM_N} кадров "
                  f"@ {CRWALK_ANIM_FPS} fps, скорость x{CRWALK_SPEED_MUL}")
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
                    # ATTACK_FRAME_SKIP выкидывает каждый N-й кадр (2 = каждый второй).
                    # Длительность удара считается по оставшимся кадрам, поэтому прореживание
                    # ровно в ATTACK_FRAME_SKIP раз ускоряет анимацию.
                    src = self.trim_frames(self.load_apng_frames(full))
                    frames = src[::ATTACK_FRAME_SKIP] if ATTACK_FRAME_SKIP > 1 else src
                    if frames:
                        self.punch_name, self.punch_frames = name, frames
                        punch_src = len(src)
                        break
        PUNCH_ANIM_N = len(self.punch_frames)
        if self.punch_frames:
            print(f"[DEBUG] удар рукой: {self.punch_name} — {PUNCH_ANIM_N} кадров "
                  f"из {punch_src} "
                  f"@ {ATTACK_ANIM_FPS} fps, длительность удара "
                  f"{attack_duration(PUNCH_ANIM_N)} кадр "
                  f"({attack_duration(PUNCH_ANIM_N) / FPS:.2f} с)")
        else:
            print("[DEBUG] удар рукой: анимация не найдена, длительность удара "
                  f"{PUNCH_FALLBACK} кадр")
        # Анимация сильного удара ногой: то же самое, но из папки MMA_DIR.
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
                    src = self.trim_frames(self.load_apng_frames(full))
                    frames = src[::ATTACK_FRAME_SKIP] if ATTACK_FRAME_SKIP > 1 else src
                    if frames:
                        self.mma_name, self.mma_frames = name, frames
                        mma_src = len(src)
                        break
        MMA_ANIM_N = len(self.mma_frames)
        if self.mma_frames:
            print(f"[DEBUG] удар ногой (сильный): {self.mma_name} — {MMA_ANIM_N} кадров "
                  f"из {mma_src} "
                  f"@ {ATTACK_ANIM_FPS} fps, длительность удара "
                  f"{attack_duration(MMA_ANIM_N)} кадр "
                  f"({attack_duration(MMA_ANIM_N) / FPS:.2f} с)")
        else:
            print("[DEBUG] удар ногой (сильный): анимация не найдена, длительность удара "
                  f"{KICK_FALLBACK} кадр")
        # Анимация обычного удара ногой: то же самое, но из папки KIK_DIR.
        self.kik_frames = []
        self.kik_name = ""
        if KIK_DIR:
            kdir = os.path.join(base, *KIK_DIR.replace("\\", "/").split("/"))
            if os.path.isdir(kdir):
                kentries = sorted(
                    (self.prefix_order(name), name, os.path.join(kdir, name))
                    for name in os.listdir(kdir) if name.lower().endswith(".png")
                )
                for order, name, full in kentries:
                    src = self.trim_frames(self.load_apng_frames(full))
                    frames = src[::ATTACK_FRAME_SKIP] if ATTACK_FRAME_SKIP > 1 else src
                    if frames:
                        self.kik_name, self.kik_frames = name, frames
                        kik_src = len(src)
                        break
        KIK_ANIM_N = len(self.kik_frames)
        if self.kik_frames:
            print(f"[DEBUG] удар ногой (обычный): {self.kik_name} — {KIK_ANIM_N} кадров "
                  f"из {kik_src} "
                  f"@ {ATTACK_ANIM_FPS} fps, длительность удара "
                  f"{attack_duration(KIK_ANIM_N)} кадр "
                  f"({attack_duration(KIK_ANIM_N) / FPS:.2f} с)")
        else:
            print("[DEBUG] удар ногой (обычный): анимация не найдена, длительность удара "
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
        self.back_scale = 1.0    # относительная подстройка масштаба клавишами +/- (1.0 = как задано именем)
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
                # Собственный масштаб фона из суффикса имени ("..._80" -> 0.8);
                # без суффикса — None, тогда работает общий BACK_SCALE.
                own = self.back_scale_of(fn)
                if kind == "anim":
                    self.par_backs.append((fn, kind, p, own))   # кадры читаем лениво
                    continue
                try:
                    pic = pygame.image.load(p)
                    pic = self.mirror_glue(pic)          # зеркалим и склеиваем для бесшовного тайлинга
                    self.par_backs.append((fn, kind, pic.convert(), own))
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

    def cycle_backdrop(self, step, src=""):
        """Переключение заднего фона на step (+1 вперёд, -1 назад). src — для отладки."""
        if len(self.par_backs) <= 1:
            print(f"[DEBUG] {src} — других задних слоёв нет")
            return
        self.par_back_idx = (self.par_back_idx + step) % len(self.par_backs)
        self.par_back_name = self.par_backs[self.par_back_idx][0]
        # Кэш масштабирования относится к прошлой картинке — сбрасываем, иначе новый фон
        # нарисуется старым размером (back_scaled сверяет исходник в кэше).
        self.back_cache = None
        self.print_backdrop()

    def toggle_isolate(self, src=""):
        """Переключение изоляции фона (Q с клавиатуры, LT на геймпаде).
        В изоляции видны только задний фон, персонажи и пол."""
        self.isolate = not self.isolate
        print(f"[DEBUG] {src} — изоляция фона: "
              f"{'ВКЛ' if self.isolate else 'ВЫКЛ'}")

    def print_backdrop(self):
        """Печать активного фона и его масштаба (суффикс имени задаёт базовый)."""
        own = None
        if self.par_backs:
            entry = self.par_backs[self.par_back_idx]
            own = entry[3] if len(entry) > 3 else None
        base = own if own is not None else BACK_SCALE
        print(f"[DEBUG] задний фон -> {self.par_back_name} | масштаб {base:.2f}")

    @staticmethod
    def back_scale_of(name):
        """Масштаб фона из суффикса имени: "1_new river_80" -> 0.80, "2_river_125" -> 1.25.

        Ищем последнее "_NNN" в имени. Число без точки читается как ПРОЦЕНТЫ:
        "_80" -> 0.80, "_125" -> 1.25. С точкой — как готовое значение: "_0.8" -> 0.8.
        Без суффикса возвращаем None, тогда применяется общий BACK_SCALE.
        Расширение отбрасываем ТОЛЬКО по списку картинок: os.path.splitext резал бы
        и имя с точкой в масштабе ("river_1.25" -> "river_1" + ".25").
        """
        if not BACK_SCALE_SUFFIX:
            return None
        stem = name
        for ext in (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"):
            if stem.lower().endswith(ext):
                stem = stem[: -len(ext)]
                break
        head, sep, tail = stem.rpartition("_")
        if not sep or not tail:
            return None
        try:
            val = float(tail)          # "_80" -> 80.0 -> 0.8; "_1.25" -> 1.25
        except ValueError:
            return None
        if "." not in tail:
            val /= 100.0               # целое число — это проценты
        if not (BACK_SCALE_MIN <= val <= BACK_SCALE_MAX):
            return None                # вне диапазона — считаем, что суффикса нет
        return val
        return val

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
        # Имя для подписи и собственный масштаб из суффикса сохраняем — 4-е поле нужно
        # дальше при отрисовке, без него фон нарисовался бы с общим BACK_SCALE.
        own = self.par_backs[idx][3] if len(self.par_backs[idx]) > 3 else None
        self.par_backs[idx] = (f"{os.path.basename(folder)} ({len(frames)} кадра)",
                               "anim", frames, own)
        if self.par_back_idx == idx:
            self.par_back_name = self.par_backs[idx][0]
        return frames

    def back_scaled(self, im, scale=None):
        """Задний план, умноженный на масштаб scale (по умолчанию — текущий
        self.back_eff_scale, иначе self.back_scale). Общий масштаб на обе оси, без обрезки.
        Результат кэшируем: пересчитываем только когда сменилась картинка или масштаб
        (иначе масштабировали бы огромную картинку каждый кадр)."""
        if scale is None:
            scale = getattr(self, "back_eff_scale", None)
            if scale is None:
                scale = self.back_scale
        w, h = im.get_size()
        dw, dh = max(1, int(w * scale)), max(1, int(h * scale))
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
        """Проигрывает короткий звук по имени (self.sfx)."""
        if not SOUND_ON:
            return
        snd = self.sfx.get(name)
        if snd is not None:
            snd.play()

    def play_sfx_delayed(self, name, ms=None):
        """Проигрывает звук персонажа с задержкой из CHAR_SFX_DELAY_MS.

        ms — строка с количеством миллисекунд (как в CHAR_SFX_DELAY_MS). Если ms не задан,
        берётся значение для name. "0" / пустая строка — звук сразу, без очереди.
        Иначе звук ставится в очередь self.sfx_queue и играет через указанное число кадров
        (update_sfx_queue уменьшает счётчик и проигрывает, когда он дошёл до нуля).
        """
        if not SOUND_ON:
            return
        if name not in self.sfx:
            return
        if ms is None:
            ms = CHAR_SFX_DELAY_MS.get(name, "0")
        try:
            delay_ms = float(str(ms).strip())
        except (TypeError, ValueError):
            print(f"[SFX] неверная задержка для {name}: {ms!r} — играю сразу")
            delay_ms = 0.0
        frames = int(round(delay_ms / 1000.0 * FPS))
        if frames <= 0:
            self.play_sfx(name)
        else:
            self.sfx_queue.append([frames, name])

    def update_sfx_queue(self):
        """Продвигает очередь отложенных звуков: счётчик кадров вниз, на нуле — проигрывание."""
        if not self.sfx_queue:
            return
        left = []
        for item in self.sfx_queue:
            item[0] -= 1
            if item[0] <= 0:
                self.play_sfx(item[1])
            else:
                left.append(item)
        self.sfx_queue = left

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
        for pl in self.players:
            pl.game = self            # ссылка на игру: из Fighter играем SFX персонажа
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
        """Экран погас — показываем заставку уровня: пауза, появление, показ, затухание."""
        self.state = "intro"
        self.intro_t = INTRO_TIME
        self.trans_paused = True
        print(f"[DEBUG] заставка: чёрный {INTRO_BLACK_TIME} + переход {INTRO_FADE_FRAMES} "
              f"({INTRO_FADE_STEPS} такт(ов) по {INTRO_FADE_TICK} кадр) + показ "
              f"{INTRO_SHOW_TIME} + затухание {INTRO_FADE_FRAMES} = {INTRO_TIME} кадров")

    def interscreen_text_image(self):
        """Слой ПОВЕРХ заставки — картинка text.(png|jpg|...) из папки заставки.

        Ищется так же, как основная заставка (сначала прямо в INTERSCREEN_DIR, потом в
        её подпапке с именем уровня), но по имени LEVEL_INTERSCREEN_TEXT. Масштабируется
        и кэшируется так же. Возвращает None, если файла нет — тогда рисуется одна
        заставка без текста поверх.
        """
        if self.interscreen_text_loaded:
            return self.interscreen_text_img
        self.interscreen_text_loaded = True
        name = LEVEL_INTERSCREEN_TEXT
        if not INTERSCREEN_DIR or not name:
            return None
        path = self.find_interscreen_file(name)
        if path is None:
            return None
        try:
            im = self.load_interscreen_img(path)
        except pygame.error as e:
            print(f"[DEBUG] слой текста заставки не читается: {path} ({e})")
            return None
        self.interscreen_text_img = im
        print(f"[DEBUG] слой текста заставки: {os.path.basename(path)} — "
              f"{im.get_width()}x{im.get_height()}")
        return im

    def find_interscreen_file(self, name):
        """Путь к файлу <name>.(jpg|png|bmp|...) в INTERSCREEN_DIR или в его подпапке
        <LEVEL_INTERSCREEN>/<name>. None, если такого файла нет."""
        base = os.path.dirname(os.path.abspath(__file__))
        root = os.path.join(base, *INTERSCREEN_DIR.replace("\\", "/").split("/"))
        for folder in (root, os.path.join(root, LEVEL_INTERSCREEN)):
            if not os.path.isdir(folder):
                continue
            for fn in sorted(os.listdir(folder)):
                stem, ext = os.path.splitext(fn)
                if stem.lower() == name.lower() and ext.lower() in (".jpg", ".jpeg", ".png", ".bmp"):
                    return os.path.join(folder, fn)
        return None

    @staticmethod
    def load_interscreen_img(path):
        """Читает картинку заставки и вписывает её в окно: масштаб по меньшей стороне,
        не увеличивая (коэффициент не больше 1.0). Пропорции сохраняются."""
        im = pygame.image.load(path)
        im = im.convert_alpha() if im.get_flags() & pygame.SRCALPHA else im.convert()
        k = min(WIDTH / im.get_width(), HEIGHT / im.get_height(), 1.0)
        if k < 1.0:
            im = pygame.transform.smoothscale(
                im, (max(1, int(im.get_width() * k)), max(1, int(im.get_height() * k))))
        return im

    def interscreen_image(self):
        """Заставка уровня: картинка с именем уровня из INTERSCREEN_DIR, пропорции сохраняются.

        Ищется файл <LEVEL_INTERSCREEN>.(jpg|png|bmp|...) — сначала прямо в папке
        screen/intersceen, потом в её подпапке с таким же именем. Масштабируется по меньшей
        стороне так, чтобы целиком влезла в окно, и центрируется. Кэшируется: грузим один раз.
        """
        if self.interscreen_loaded:
            return self.interscreen_img
        self.interscreen_loaded = True
        name = LEVEL_INTERSCREEN
        if not INTERSCREEN_DIR or not name:
            return None
        path = self.find_interscreen_file(name)
        if path is None:
            print(f"[DEBUG] заставка уровня «{name}» не найдена в {INTERSCREEN_DIR}")
            return None
        try:
            im = self.load_interscreen_img(path)
        except pygame.error as e:
            print(f"[DEBUG] заставка не читается: {path} ({e})")
            return None
        self.interscreen_img = im
        print(f"[DEBUG] заставка уровня: {os.path.basename(path)} — "
              f"{im.get_width()}x{im.get_height()}")
        return im

    def skip_intro(self, src=""):
        """Пропуск заставки уровня: сразу к затуханию.

        Значение intro_t = INTRO_FADE_FRAMES — это ровно начало фазы затухания, то есть
        пропускаются чёрный экран, появление картинки и её показ. Если затухание уже
        идёт (intro_t <= INTRO_FADE_FRAMES), ничего не трогаем — иначе второй нажим
        назад по времени откатил бы переход на показ картинки.
        """
        if self.intro_t > INTRO_FADE_FRAMES:
            self.intro_t = INTRO_FADE_FRAMES
            print(f"[DEBUG] {src} на заставке — переход к затуханию, intro_t={self.intro_t}")

    def intro_alpha(self):
        """Прозрачность заставки уровня для текущего кадра: 0 — чёрный экран, 255 — картинка."""
        return self.intro_alpha_for(self.intro_t)

    def intro_alpha_for(self, intro_t):
        """Прозрачность по схеме чёрный экран -> появление -> показ -> затухание.

        Считает фазы от intro_t (кадров до конца заставки) тем же способом, что и раньше:
        INTRO_BLACK_TIME чёрного экрана, появление и затухание по INTRO_FADE_FRAMES
        разбиты на INTRO_FADE_STEPS тактов по INTRO_FADE_TICK кадров — внутри такта альфа
        не меняется, поэтому переход дискретный. 0 или 1 такт — плавное затухание.
        """
        elapsed = INTRO_TIME - max(0, intro_t)
        fade = INTRO_FADE_FRAMES
        if elapsed < INTRO_BLACK_TIME:
            return 0
        t = elapsed - INTRO_BLACK_TIME
        if t < fade:                                    # появление
            return min(255, (t + 1) * 255 // fade) if INTRO_FADE_STEPS <= 1 else \
                min(255, (t // INTRO_FADE_TICK + 1) * 255 // INTRO_FADE_STEPS)
        t -= fade
        if t < INTRO_SHOW_TIME:                         # картинка видна целиком
            return 255
        t -= INTRO_SHOW_TIME
        if t < fade:                                    # затухание теми же ступенями
            return max(0, 255 - (t + 1) * 255 // fade) if INTRO_FADE_STEPS <= 1 else \
                max(0, 255 - (t // INTRO_FADE_TICK + 1) * 255 // INTRO_FADE_STEPS)
        return 0

    def intro_text_alpha(self):
        """Прозрачность слоя текста — по СВОЕМУ ритму, отдельно от заставки.

        Текст появляется позже и держится дольше: INTRO_TEXT_DELAY кадров после начала
        появления заставки, затем своё появление, своя пауза и своё затухание.
        Всё считается от фактического числа кадров с начала интро (не от intro_t),
        поэтому текст гарантированно доигрывает свой затухание даже если базовый таймер
        уходит в минус.
        """
        elapsed = INTRO_TIME - self.intro_t   # кадров с начала интро (intro_t может быть < 0)
        if elapsed < INTRO_TEXT_DELAY:                   # текст ещё не начал появляться
            return 0
        t = elapsed - INTRO_TEXT_DELAY
        fade = max(1, INTRO_TEXT_FADE)
        if t < fade:                                     # своё появление
            return min(255, (t + 1) * 255 // fade)
        t -= fade
        if t < INTRO_TEXT_SHOW_TIME:                     # текст держится на экране
            return 255
        t -= INTRO_TEXT_SHOW_TIME
        if t < fade:                                     # своё затухание
            return max(0, 255 - (t + 1) * 255 // fade)
        return 0

    def draw_level_intro(self):
        """Заставка уровня: чёрный экран -> дискретное появление -> показ -> дискретное затухание.

        Сама картинка берётся из screen/intersceen, а если её нет — рисуется чёрный экран
        с названием уровня (такты применяются к нему так же).
        """
        self.screen.fill(BLACK)
        alpha = self.intro_alpha()
        if alpha <= 0:                 # пауза перед показом — просто чёрный экран
            return
        img = self.interscreen_image()
        if img is None:
            # Заставки нет — рисуем чёрный экран с названием уровня (если уже пора)
            if alpha > 0:
                num = self.pixel_font_ru.render(LEVEL_NUM, True, (170, 170, 180))
                name = self.pixel_font_ru.render(LEVEL_NAME, True, YELLOW)
                name = pygame.transform.scale(name, (name.get_width() * 2, name.get_height() * 2))
                num.set_alpha(alpha)
                name.set_alpha(alpha)
                self.screen.blit(num, (WIDTH // 2 - num.get_width() // 2, HEIGHT // 2 - 100))
                self.screen.blit(name, (WIDTH // 2 - name.get_width() // 2, HEIGHT // 2 - 30))
            return
        frame = img
        if alpha < 255:                # проявление/затухание — рисуем копию с альфой
            frame = img.copy()
            frame.set_alpha(alpha)
        self.screen.blit(frame, ((WIDTH - frame.get_width()) // 2,
                                 (HEIGHT - frame.get_height()) // 2))
        # Слой с текстом — ПОВЕРХ заставки и по СВОЕМУ ритму (intro_text_alpha):
        # своя задержка, своё появление, своя пауза и своё затухание. Рисуется всегда,
        # даже если основной картинки нет — слой самодостаточный.
        text_img = self.interscreen_text_image()
        if text_img is not None:
            talpha = self.intro_text_alpha()
            if talpha > 0:
                tframe = text_img
                if talpha < 255:
                    tframe = text_img.copy()
                    tframe.set_alpha(talpha)
                self.screen.blit(tframe, ((WIDTH - tframe.get_width()) // 2,
                                          (HEIGHT - tframe.get_height()) // 2))

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

            self.draw()
            self.draw_transition()
            pygame.display.flip()
            self.clock.tick(FPS)

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
            hl = ("←→/AD — идти   ↑/W — прыжок  ↓/S — блок   J — кулак   L — нога   "
                  "X/K — нога сильная   Z — панель   R — заново   Ctrl+R — перезапуск   ESC — выход")
        else:
            hl = ("P1: A/D·W·S·J/L/K     P2: ←→·↑·↓·N/B/M     Z — панель   R — заново   "
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


if __name__ == "__main__":
    Game().run()