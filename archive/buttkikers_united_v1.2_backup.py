import os
import random
import subprocess
import sys

import pygame

WIDTH, HEIGHT = 900, 880
FPS = 30
FLOOR_Y = 620
CHARACTER_FLOOR_Y = 557
LEVEL_LEN = 6000
GRAVITY = 2.0
MOVE = 9.0
JUMP = -32
MAX_HP = 100
NO_ENEMIES = True

SKY = (30, 26, 46)
SKY_D = (22, 20, 38)
BUILD = (60, 52, 66)
BUILD_D = (44, 38, 54)
WINDOW = (95, 90, 70)
WINDOW_L = (210, 200, 120)
ROAD = (90, 88, 84)
ROAD_D = (66, 64, 62)
SIDEWALK = (150, 148, 140)
PLAYER = (70, 200, 90)
PLAYER_D = (40, 130, 60)
PLAYER2 = (90, 150, 235)
PLAYER2_D = (50, 90, 170)
THUG = (190, 90, 90)
BRUISER = (140, 70, 200)
BOSS = (200, 60, 60)
SKIN = (235, 190, 150)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (220, 40, 40)
YELLOW = (255, 225, 60)
GREEN = (70, 200, 90)
GRAY = (150, 150, 150)
BARREL = (178, 120, 50)
BARREL_D = (120, 82, 34)


class Fighter:
    def __init__(self, x, hp, color, name, scale=1.0):
        self.x = x
        self.y = FLOOR_Y - 82 * scale
        self.vel_x = 0
        self.vel_y = 0
        self.hp = hp
        self.max_hp = hp
        self.color = color
        self.name = name
        self.scale = scale
        self.facing = 1
        self.on_ground = True
        self.crouching = False
        self.attack = None
        self.attack_timer = 0
        self.attack_hit = False
        self.cooldown = 0
        self.combo = 0
        self.combo_timeout = 0
        self.flinch = 0
        self.knock = 0
        self.dead = False
        self.dead_timer = 0
        self.dead_fall = 0
        self.ai_timer = 0
        self.bias = random.choice([-1, 1])

    @property
    def w(self):
        return int(44 * self.scale)

    @property
    def h(self):
        return int((50 if self.crouching else 82) * self.scale)

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    def hitbox(self):
        if self.attack is None:
            return None
        r = self.rect
        if self.attack == "punch":
            w, h, oy = 46, int(24 * self.scale), int(30 * self.scale)
        else:
            w, h, oy = 62, int(30 * self.scale), int(36 * self.scale)
        hx = r.right if self.facing > 0 else r.left - w
        return pygame.Rect(hx, r.y + oy, w, h)

    def attack_damage(self):
        if self.attack == "punch":
            base = 12 + self.combo * 3
            return base, "punch"
        return 20 + self.combo * 2, "kick"

    def try_attack(self, kind, now):
        if self.cooldown > 0 or self.attack is not None or self.dead:
            return
        self.attack = kind
        self.attack_timer = 7 if kind == "punch" else 12
        self.attack_hit = False
        self.cooldown = 3 if kind == "punch" else 5
        if now > self.combo_timeout:
            self.combo = 0
        self.combo += 1
        if self.combo > 2:
            self.combo = 2
        self.combo_timeout = now + 30

    def take_hit(self, dmg, dir_side, blocking=False):
        if self.dead:
            return
        if blocking:
            dmg = dmg // 2
        self.hp -= dmg
        self.attack = None
        self.attack_timer = 0
        self.flinch = 7
        self.knock = (dir_side or self.bias) * 6
        if self.hp <= 0:
            self.hp = 0
            self.dead = True
            self.dead_fall = 0

    def update(self, cam, frame):
        now = frame
        if self.dead:
            self.dead_timer += 1
            self.dead_fall += 3.0
            if self.dead_fall > 15:
                self.dead_fall = 15
            return

        if self.flinch > 0:
            self.flinch -= 1
        if self.knock:
            self.x += self.knock
            self.knock *= 0.67
            if abs(self.knock) < 0.4:
                self.knock = 0

        if self.attack is not None:
            self.attack_timer -= 1
            if self.attack_timer <= 0:
                self.attack = None
        if self.cooldown > 0:
            self.cooldown -= 1

        self.vel_y += GRAVITY
        self.y += self.vel_y
        if self.y >= CHARACTER_FLOOR_Y - self.h:
            self.y = CHARACTER_FLOOR_Y - self.h
            self.vel_y = 0
            self.on_ground = True
        else:
            self.on_ground = False

        self.x += self.vel_x
        self.vel_x = 0
        self.x = max(cam, min(self.x, LEVEL_LEN - self.w))

        if self.now_blocking:
            self.now_blocking = False


class Player(Fighter):
    def __init__(self, pnum=0, mode=1):
        name = "P1" if pnum == 0 else "P2"
        color = PLAYER if pnum == 0 else PLAYER2
        super().__init__(100 * pnum, MAX_HP, color, name)
        self.pnum = pnum
        self.mode = mode
        self.now_blocking = False
        self.moved = 0

    def update(self, cam, frame):
        super().update(cam, frame)
        if self.dead:
            return

        keys = pygame.key.get_pressed()
        if self.pnum == 1:
            left = keys[pygame.K_LEFT]
            right = keys[pygame.K_RIGHT]
            up = keys[pygame.K_UP]
            down = keys[pygame.K_DOWN]
            punch = keys[pygame.K_n]
            kick = keys[pygame.K_m]
        elif self.mode == 1:
            left = keys[pygame.K_a] or keys[pygame.K_LEFT]
            right = keys[pygame.K_d] or keys[pygame.K_RIGHT]
            up = keys[pygame.K_w] or keys[pygame.K_UP]
            down = keys[pygame.K_s] or keys[pygame.K_DOWN]
            punch = keys[pygame.K_z] or keys[pygame.K_j]
            kick = keys[pygame.K_x] or keys[pygame.K_k]
        else:
            left = keys[pygame.K_a]
            right = keys[pygame.K_d]
            up = keys[pygame.K_w]
            down = keys[pygame.K_s]
            punch = keys[pygame.K_j]
            kick = keys[pygame.K_k]

        self.crouching = False
        if self.flinch <= 0:
            if left:
                self.vel_x = -MOVE
                self.facing = -1
                self.moved += 1
            elif right:
                self.vel_x = MOVE
                self.facing = 1
                self.moved += 1
            if up and self.on_ground:
                self.vel_y = JUMP
                self.on_ground = False
            if down:
                self.crouching = True
                self.now_blocking = True
            if punch:
                self.try_attack("punch", frame)
            elif kick:
                self.try_attack("kick", frame)


class Enemy(Fighter):
    def __init__(self, x, kind):
        self.kind = kind
        if kind == "thug":
            super().__init__(x, 45, THUG, "THUG")
            self.speed = 2.2
            self.attack_range = 70
        elif kind == "bruiser":
            super().__init__(x, 80, BRUISER, "BRUTE")
            self.scale = 1.2
            self.speed = 1.5
            self.attack_range = 80
        else:
            super().__init__(x, 180, BOSS, "AXIS")
            self.scale = 1.6
            self.speed = 0.9
            self.attack_range = 110
        self.now_blocking = False
        self.hp = int(self.hp * self.scale)
        self.max_hp = self.hp

    def ai_update(self, player, cam, frame):
        if self.dead or player.dead:
            return
        dx = player.x - self.x
        dist = abs(dx)
        self.facing = 1 if dx > 0 else -1
        self.crouching = False

        if self.flinch > 0:
            return

        if dist > self.attack_range + 20:
            self.vel_x = self.facing * self.speed
        elif dist < self.attack_range:
            self.ai_timer -= 1
            if self.ai_timer <= 0:
                self.ai_timer = random.randint(15, 45)
                if random.random() < 0.55:
                    kind = "punch" if random.random() < 0.6 else "kick"
                    self.try_attack(kind, frame)
                elif random.random() < 0.3 and self.on_ground:
                    self.vel_y = -26
        else:
            self.vel_x = self.facing * min(self.speed, dist * 0.1)


class Barrel:
    def __init__(self, x):
        self.x = x
        self.y = FLOOR_Y - 46
        self.hp = 2
        self.dead = False

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), 40, 46)


class Game:
    def __init__(self):
        pygame.init()
        self.audio_ok = False
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("TOADS vs DRAGON — BEAT-EM-UP")
        self.clock = pygame.time.Clock()
        self.font_big = pygame.font.SysFont("arial", 50)
        self.font_m = pygame.font.SysFont("arial", 22)
        self.font_s = pygame.font.SysFont("arial", 15)
        self.pixel_font = pygame.font.Font(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts", "PressStart2P.ttf"), 20)
        self.pixel_font_ru = pygame.font.Font(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts", "Tiny5.ttf"), 32)
        try:
            img = pygame.image.load(os.path.join(os.path.dirname(os.path.abspath(__file__)), "screen", "6fin.png")).convert_alpha()
        except pygame.error:
            img = None
        self.title_img = img
        base = os.path.dirname(os.path.abspath(__file__))
        spr_path = os.path.join(base, "sprites", "choose.png")
        self.choose_img = None
        if os.path.exists(spr_path):
            try:
                self.choose_img = pygame.image.load(spr_path).convert_alpha()
            except pygame.error:
                self.choose_img = None
        self.level_bg = None
        self.level_sel = 0
        lv_path = os.path.join(base, "screen", "1lev_tiled.jpg")
        if os.path.exists(lv_path):
            try:
                raw = pygame.image.load(lv_path).convert()
                lw = raw.get_width()
                lh = FLOOR_Y
                scaled = pygame.transform.smoothscale(raw, (int(lw * lh / raw.get_height()), lh))
                self.level_bg = pygame.Surface((LEVEL_LEN, lh), pygame.SRCALPHA)
                sw, sh = scaled.get_size()
                for tx in range(0, LEVEL_LEN, sw):
                    self.level_bg.blit(scaled, (tx, 0))
            except pygame.error:
                self.level_bg = None
        self.reset()

    def restart_script(self):
        py = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        if not os.path.exists(py):
            py = sys.executable
        subprocess.Popen([py, os.path.abspath(__file__)], cwd=os.path.dirname(os.path.abspath(__file__)))
        pygame.quit()
        sys.exit()

    def reset(self, players=None):
        print(f"[DEBUG] reset called, level_sel={self.level_sel}")
        if players is None:
            players = getattr(self, "num_players", 1)
        self.num_players = players
        self.players = [Player(i, players) for i in range(players)]
        self.frame = 0
        self.cam = 0
        self.state = "title"
        self.score = 0
        self.enemies = []
        # self.barrels = [Barrel(900), Barrel(2100), Barrel(3300), Barrel(4600)]
        self.boss_spawned = False
        self.spawn_points = [(600, "thug"), (950, "thug"), (1500, "bruiser"),
                             (1900, "thug"), (2400, "bruiser"), (2900, "thug"),
                             (3100, "thug"), (3700, "bruiser"), (4200, "thug"),
                             (5000, "bruiser")]
        self.spawn_idx = 0
        self.win_t = 0
        self.lose_t = 0
        self.mode_sel = 0
        self.load_level_bg()

    def load_level_bg(self):
        base = os.path.dirname(os.path.abspath(__file__))
        level_file = "2lev.jpg" if self.level_sel == 1 else "1lev_tiled.jpg"
        print(f"[DEBUG] load_level_bg: level_sel={self.level_sel} -> {level_file}")
        lv_path = os.path.join(base, "screen", level_file)
        self.level_bg = None
        if os.path.exists(lv_path):
            try:
                raw = pygame.image.load(lv_path).convert()
                lw = raw.get_width()
                lh = FLOOR_Y
                scaled = pygame.transform.smoothscale(raw, (int(lw * lh / raw.get_height()), lh))
                self.level_bg = pygame.Surface((LEVEL_LEN, lh), pygame.SRCALPHA)
                sw, sh = scaled.get_size()
                for tx in range(0, LEVEL_LEN, sw):
                    self.level_bg.blit(scaled, (tx, 0))
            except pygame.error:
                self.level_bg = None

    def run(self):
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
                        self.reset()
                    if event.key == pygame.K_r:
                        if event.mod & pygame.KMOD_CTRL:
                            self.restart_script()
                        else:
                            self.reset()
                    if event.key == pygame.K_q:
                        print(f"[DEBUG] Q pressed, level_sel={self.level_sel} -> {(self.level_sel + 1) % 2}")
                        self.level_sel = (self.level_sel + 1) % 2
                        self.load_level_bg()
                    if self.state == "title":
                        if event.key in (pygame.K_UP, pygame.K_w):
                            self.mode_sel = (self.mode_sel - 1) % 2
                        elif event.key in (pygame.K_DOWN, pygame.K_s):
                            self.mode_sel = (self.mode_sel + 1) % 2
                        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE, pygame.K_z):
                            print(f"[DEBUG] ENTER pressed, level_sel={self.level_sel}")
                            self.reset(self.mode_sel + 1)
                            print(f"[DEBUG] After reset, level_bg={'loaded' if self.level_bg else 'None'}")
                            self.state = "play"
                            print(f"[DEBUG] State changed to: {self.state}")
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.state == "title":
                    self.reset(self.mode_sel + 1)
                    self.state = "play"

            self.frame += 1
            self.update()

            if self.audio_ok and not pygame.mixer.music.get_busy():
                pygame.mixer.music.play(-1)

            self.draw()
            pygame.display.flip()
            self.clock.tick(FPS)

    def update(self):
        players = self.players
        alive = [pl for pl in players if not pl.dead]

        if self.state == "title":
            return

        if alive:
            rightmost = max(pl.x for pl in alive)
        else:
            rightmost = players[0].x
        self.cam = int(max(0, min(rightmost - WIDTH // 3, LEVEL_LEN - WIDTH)))

        for pl in players:
            pl.update(self.cam, self.frame)

        if self.state == "play":
            if not alive:
                self.state = "lose"
                self.lose_t = 0
            if alive and any(pl.x > LEVEL_LEN - 60 for pl in alive):
                self.state = "win"
                self.win_t = 0

        # спавн врагов по мере продвижения
        if self.state == "play" and not NO_ENEMIES:
            while self.spawn_idx < len(self.spawn_points):
                sx, kind = self.spawn_points[self.spawn_idx]
                if rightmost + WIDTH >= sx:
                    left = sx < self.cam
                    ex = sx - 200 if left else sx
                    self.enemies.append(Enemy(max(50, ex), kind))
                    self.spawn_idx += 1
                else:
                    break

            if not self.boss_spawned and rightmost > 4800:
                self.boss_spawned = True
                self.enemies.append(Enemy(max(50, 5200), "boss"))

        if not NO_ENEMIES:
            for e in self.enemies[:]:
                if e.dead:
                    e.update(self.cam, self.frame)
                    if e.dead_timer > 60:
                        self.enemies.remove(e)
                    continue
                target = alive[0] if alive else players[0]
                e.ai_update(target, self.cam, self.frame)
                e.update(self.cam, self.frame)
                self.bump_world(e)

        if not NO_ENEMIES:
            # атаки игроков
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
                                self.score += 100
                                pl.attack_hit = True
                                break

            # атаки врагов
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

            # контакты игрок-враг (сбивание)
            for e in self.enemies:
                if e.dead:
                    continue
                for pl in players:
                    if pl.dead:
                        continue
                    if pl.rect.colliderect(e.rect):
                        if pl.vel_y > 0 and pl.on_ground is False:
                            e.take_hit(30, 0)
                            pl.vel_y = -10
                        else:
                            pl.x += -pl.facing * 4
                            if pl.now_blocking:
                                pl.x += -pl.facing * 2

            # враг не может выйти за камеру глубоко влево и вправо за уровень
            for e in self.enemies:
                e.x = max(self.cam, min(e.x, LEVEL_LEN - e.w))

    # def bump_world(self, ent):
#     for b in self.barrels:
#         if not b.dead and ent.rect.colliderect(b.rect):
#             if ent.x < b.x:
#                 ent.x = b.x - ent.w
#             else:
#                 ent.x = b.x + 40

    def draw(self):
        if self.state == "title":
            self.draw_title()
            return
        if self.frame == 1:
            print(f"[DEBUG] draw: state={self.state}, level_bg={self.level_bg.get_size() if self.level_bg else 'None'}")
        self.screen.fill(SKY)
        cam = self.cam

        for i in range(len(self.sky_blocks())):
            pass

        # фон: небо, здания
        if self.level_bg is not None:
            off = cam * 3 // 10
            for k in range(-2, 3):
                self.screen.blit(self.level_bg, (k * LEVEL_LEN - off, 0))
        if self.level_bg is None:
            for k in range(0, WIDTH // 60 + 1):
                wx = k * 60 - (cam % 60)
                h = 170 + ((k * 53 + cam // 60) % 4) * 30
                pygame.draw.rect(self.screen, BUILD, (wx, 60, 60, FLOOR_Y - 40 - 60))
                pygame.draw.rect(self.screen, BUILD_D, (wx, 60, 60, h))
                for wy in range(80, FLOOR_Y - 120, 34):
                    for wx2 in range(4, 56, 14):
                        lit = ((wx2 + wy + k) % 5 == 0)
                        c = WINDOW_L if lit else WINDOW
                        pygame.draw.rect(self.screen, c, (wx + wx2, wy, 8, 13))

        # враги
        if not NO_ENEMIES:
            scale_rank = {"thug": 3, "bruiser": 4, "boss": 5}
            for e in self.enemies:
                self.draw_fighter(e, cam, e.kind, rank=scale_rank[e.kind])

        # игроки
        for pl in self.players:
            if not pl.dead or pl.dead_fall < 15:
                self.draw_fighter(pl, cam, "player", rank=2)

        self.draw_hud()

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

    def sky_blocks(self):
        return []

    def draw_title(self):
        self.screen.fill((0, 0, 0))
        img = self.title_img
        if img is not None:
            th = 660
            tw = int(img.get_width() * th / img.get_height())
            scaled = pygame.transform.smoothscale(img, (tw, th))
            self.screen.blit(scaled, ((WIDTH - tw) // 2, 20))
        else:
            t = self.font_big.render("TOADS vs DRAGON", True, YELLOW)
            self.screen.blit(t, (WIDTH // 2 - t.get_width() // 2, 160))

        sel = self.mode_sel
        for i, label in enumerate(["1 ИГРОК", "2 ИГРОКА"]):
            c = YELLOW if i == sel else (200, 200, 210)
            s = self.pixel_font_ru.render(" " + label, True, c)
            sx = WIDTH // 2 - s.get_width() // 2
            if i == 0:
                sx -= 10
            sy = 656 + i * 36
            self.screen.blit(s, (sx, sy))
            if i == sel and self.choose_img is not None:
                cy = sy + 7
                self.screen.blit(self.choose_img, (WIDTH // 2 - self.choose_img.get_width() - 88, cy))

        if (self.frame // 15) % 2 == 0:
            s = self.pixel_font_ru.render("ENTER — НАЧАТЬ", True, (137, 223, 255))
            self.screen.blit(s, (WIDTH // 2 - s.get_width() // 2, 736))

        hint = self.pixel_font_ru.render(
            "W/S или ↑/↓ — выбор   ESC — выход",
            True, (180, 180, 190))
        self.screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, 816))

    def draw_fighter(self, f, cam, variant, rank):
        x = int(f.x - cam)
        y = int(f.y)
        if y < -20 or x < -100 or x > WIDTH + 100:
            return
        dead = getattr(f, "dead", False)
        if dead:
            y += int(f.dead_fall)
            # лежим на земле
            w2, h2 = f.w, int(f.h * 0.4)
            pygame.draw.rect(self.screen, f.color, (x, FLOOR_Y - 14, w2, 14))
            pygame.draw.rect(self.screen, SKIN, (x + 6, FLOOR_Y - 12, 14, 8))
            return

        col = f.color
        if f.flinch > 0 and (f.flinch // 3) % 2 == 0:
            col = (max(0, col[0] - 70), max(0, col[1] - 70), max(0, col[2] - 70))

        w, h = f.w, f.h
        leg_h = h // 2

        # ноги
        leg_off = 0
        if f.on_ground and f.vel_x:
            leg_off = int(f.vel_x)
        pygame.draw.rect(self.screen, BLACK, (x + 3 + leg_off, y + h - leg_h, 11, leg_h))
        pygame.draw.rect(self.screen, BLACK, (x + w - 3 - 11 + leg_off, y + h - leg_h, 11, leg_h))

        body_h = h - leg_h - 8
        pygame.draw.rect(self.screen, col, (x, y + leg_h, w, body_h))

        head_y = y + 5
        pygame.draw.rect(self.screen, SKIN, (x + 4, head_y, w - 8, 20))
        pygame.draw.rect(self.screen, (40, 40, 50) if variant == "player" else (30, 26, 40),
                         (x + 4, head_y, w - 8, 8))
        ex = x + w - 10 if f.facing > 0 else x + 4
        pygame.draw.rect(self.screen, BLACK, (ex, head_y + 10, 3, 4))

        if f.crouching:
            return

        if f.attack == "punch" and f.attack_timer % 2 == 0:
            px = x + w if f.facing > 0 else x - 40
            pygame.draw.rect(self.screen, (255, 220, 90), (px, y + 32, 40, 14))
        elif f.attack == "kick" and f.attack_timer % 3 < 2:
            kx = x + w if f.facing > 0 else x - 56
            pygame.draw.rect(self.screen, WHITE, (kx, y + h - leg_h + 4, 56, 12))

    def draw_hud(self):
        pygame.draw.rect(self.screen, BLACK, (0, 0, WIDTH, 52))
        xs = [10, 340]
        for i, pl in enumerate(self.players):
            base = xs[i]
            hi = max(0, pl.hp)
            c1 = GREEN if i == 0 else (110, 170, 255)
            pygame.draw.rect(self.screen, GRAY, (base, 8, 200, 12))
            pygame.draw.rect(self.screen, c1, (base, 8, 200 * hi / MAX_HP, 12))
            t = self.font_s.render(f"P{i+1} {int(hi)}/{MAX_HP}", True, WHITE)
            self.screen.blit(t, (base, 2))

        sc = self.font_m.render(f"SCORE {self.score}", True, YELLOW)
        self.screen.blit(sc, (WIDTH // 2 - sc.get_width() // 2, 2))

        prog = self.font_s.render("PROGRESS", True, GRAY)
        self.screen.blit(prog, (WIDTH - 150, 2))
        pygame.draw.rect(self.screen, GRAY, (WIDTH - 90, 8, 80, 10))
        right = max(pl.x for pl in self.players)
        frac = min(1, max(0, (right - 100) / (LEVEL_LEN - WIDTH)))
        pygame.draw.rect(self.screen, YELLOW, (WIDTH - 90, 8, int(80 * frac), 10))

        if self.num_players == 1:
            hl = "←→/AD — идти   ↑/W — прыжок  ↓/S — блок   Z/J — кулак   X/K — нога   R — заново   Ctrl+R — перезапуск   ESC — выход"
        else:
            hl = "P1: A/D·W·S·J/K     P2: ←→·↑·↓·N/M     R — заново   Ctrl+R — перезапуск   ESC — выход"
        hint = self.font_s.render(hl, True, WHITE)
        self.screen.blit(hint, (10, HEIGHT - 20))


if __name__ == "__main__":
    Game().run()