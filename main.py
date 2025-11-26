"""
Final Finger-Tracking Snake Game with Sounds
- Fullscreen
- Camera preview top-right (180 px)
- Score & Timer centered at top
- Food spawns below camera horizontal band with 20 px gap
- Neon snake, small obstacles, particle explosion
- Pages: Main Menu (click start) -> Game -> End (BIG "YOU COLLECTED X POINTS!")
- Controls: Click START or press S to begin. Press R to restart during game or on the end screen. Esc to quit.
- Assets (optional) in ./assets/: main_bg.png, start_btn.png, game_bg.png, end_bg.png, eat.wav, explode.wav, gameover.wav
"""
import os
import sys
import time
import math
import random
import cv2
import pygame
import mediapipe as mp

# ---------------- CONFIG ----------------
ASSETS_DIR = "assets"
CAM_W = 180                # camera preview width
CAM_MARGIN_TOP = 10
CAM_MARGIN_RIGHT = 20
FOOD_GAP_BELOW_CAM = 20
FPS = 30

# Game tuning
SNAKE_SPEED = 6.5
SEG_SPACING = 12
INITIAL_LEN = 7
HEAD_RADIUS = 12
FOOD_RADIUS = 12
TIME_LIMIT = 60

# Obstacles
OBSTACLE_COUNT = 6
OBSTACLE_MIN = 40
OBSTACLE_MAX = 90

# Visuals
NEON_LAYERS = 5
PARTICLE_COUNT = 18
PARTICLE_LIFE = 0.55

# Colors
COLOR_UI = (230, 230, 250)
COLOR_BG = (12, 14, 20)

# ---------------- Helper: resource path for PyInstaller ----------------
def resource_path(relative_path):
    """ Get absolute path for PyInstaller or normal run """
    # If running as a PyInstaller bundle, _MEIPASS is set to the temp folder
    _meipass = getattr(sys, "_MEIPASS", None)
    if _meipass:
        return os.path.join(_meipass, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# ---------------- Pygame init (fullscreen) ----------------
pygame.init()
# init mixer for sounds (catch failures)
try:
    pygame.mixer.init()
except Exception as e:
    print("Warning: pygame.mixer.init() failed:", e)

# fullscreen
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
WIN_W, WIN_H = screen.get_size()
pygame.display.set_caption("Finger Snake - Final")
clock = pygame.time.Clock()
font = pygame.font.SysFont("Arial", 26)
bigfont = pygame.font.SysFont("Arial", 44)

# ---------------- Assets loader ----------------
def load_image(name, scale_to=None):
    path = resource_path(os.path.join(ASSETS_DIR, name))
    if os.path.isfile(path):
        try:
            img = pygame.image.load(path).convert_alpha()
            if scale_to:
                img = pygame.transform.smoothscale(img, scale_to)
            return img
        except Exception as e:
            print(f"Failed to load {path}: {e}")
    return None

def load_sound(name):
    path = resource_path(os.path.join(ASSETS_DIR, name))
    if os.path.isfile(path):
        try:
            return pygame.mixer.Sound(path)
        except Exception as e:
            print(f"Failed to load sound {path}: {e}")
    return None

# load images (optional)
main_bg_img = load_image("main_bg.png", scale_to=(WIN_W, WIN_H))
start_btn_img = load_image("start_btn.png")
game_bg_img = load_image("game_bg.png", scale_to=(WIN_W, WIN_H))
end_bg_img = load_image("end_bg.png", scale_to=(WIN_W, WIN_H))

# create fallback start button if missing
START_BTN_SIZE = (int(WIN_W * 0.32), int(WIN_H * 0.12))
if start_btn_img is None:
    s = pygame.Surface(START_BTN_SIZE, pygame.SRCALPHA)
    pygame.draw.rect(s, (30,140,220), (0,0,START_BTN_SIZE[0], START_BTN_SIZE[1]), border_radius=18)
    txt = bigfont.render("START", True, (255,255,255))
    s.blit(txt, (START_BTN_SIZE[0]//2 - txt.get_width()//2, START_BTN_SIZE[1]//2 - txt.get_height()//2))
    start_btn_img = s

start_btn_rect = start_btn_img.get_rect(center=(WIN_W//2, WIN_H//2 + 80))

# ---------------- Mediapipe + Camera ----------------
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Camera not found. Exiting.")
    pygame.quit(); sys.exit(1)

# warm frame to compute CAM_H
ret, warm_frame = cap.read()
if not ret:
    print("Unable to read from camera on startup.")
    cap.release(); hands.close(); pygame.quit(); sys.exit(1)
warm_frame = cv2.flip(warm_frame, 1)
CAM_H = int(CAM_W * warm_frame.shape[0] / warm_frame.shape[1])
CAM_X = WIN_W - CAM_W - CAM_MARGIN_RIGHT
CAM_Y = CAM_MARGIN_TOP

# ---------------- Sounds loader & fallback synthesis ----------------
eat_sound = load_sound("eat.wav")
explode_sound = load_sound("explode.wav")
gameover_sound = load_sound("gameover.wav")

# if sounds missing, try to synth a simple beep using numpy & pygame.sndarray
def try_synth_beep(freq=600, duration=0.12, volume=0.4):
    try:
        import numpy as np
        sample_rate = 44100
        t = np.linspace(0, duration, int(sample_rate*duration), False)
        wave = 0.5 * np.sign(np.sin(2 * np.pi * freq * t))  # square-ish
        audio = np.int16(wave * 32767 * volume)
        # stereo
        sound = pygame.sndarray.make_sound(np.stack([audio, audio], axis=-1))
        return sound
    except Exception:
        return None

if eat_sound is None:
    eat_sound = try_synth_beep(freq=880, duration=0.09, volume=0.4)
if explode_sound is None:
    explode_sound = try_synth_beep(freq=520, duration=0.18, volume=0.5)
if gameover_sound is None:
    gameover_sound = try_synth_beep(freq=260, duration=0.35, volume=0.6)

# ---------------- Game state ----------------
PAGE_MAIN, PAGE_GAME, PAGE_END = 0, 1, 2
page = PAGE_MAIN

score = 0
start_time = None
game_over = False

snake = [(WIN_W//2 - i * SEG_SPACING, WIN_H//2) for i in range(INITIAL_LEN)]
target_pos = (WIN_W//2, WIN_H//2)

# obstacles
def generate_obstacles(count):
    rects = []
    tries = 0
    while len(rects) < count and tries < 400:
        w = random.randint(OBSTACLE_MIN, OBSTACLE_MAX)
        h = random.randint(OBSTACLE_MIN, OBSTACLE_MAX)
        x = random.randint(30, WIN_W - w - 30)
        y = random.randint(120, WIN_H - h - 30)
        r = pygame.Rect(x, y, w, h)
        ok = True
        for ex in rects:
            if r.colliderect(ex.inflate(60,60)):
                ok = False; break
        if ok:
            rects.append(r)
        tries += 1
    return rects

obstacles = generate_obstacles(OBSTACLE_COUNT)

# spawn food ensuring below camera band + gap
def spawn_food(obstacles, snake):
    tries = 0
    min_y = CAM_Y + CAM_H + FOOD_GAP_BELOW_CAM
    if min_y < 120:
        min_y = 120
    while tries < 800:
        fx = random.randint(60, WIN_W - 60)
        fy = random.randint(int(min_y), WIN_H - 60)
        pt = (fx, fy)
        ok = True
        for r in obstacles:
            if r.collidepoint(pt):
                ok = False; break
        if ok and math.hypot(fx - snake[0][0], fy - snake[0][1]) < 120:
            ok = False
        if ok:
            return pt
        tries += 1
    return (WIN_W//2 + random.randint(-120,120), max(int(min_y), WIN_H//2))

food = spawn_food(obstacles, snake)

# particle explosion
particles = []
def spawn_explosion(x, y):
    now = time.time()
    for _ in range(PARTICLE_COUNT):
        ang = random.random() * 2 * math.pi
        spd = random.uniform(120, 420)
        vx = math.cos(ang) * spd
        vy = math.sin(ang) * spd
        sz = random.randint(3,7)
        col = (255, random.randint(120,220), random.randint(0,90))
        particles.append({"pos":[x,y], "vel":[vx,vy], "born":now, "life":PARTICLE_LIFE, "size":sz, "color":col})

# neon helper
def draw_neon_circle(surf, center, base_color, radius):
    cx, cy = int(center[0]), int(center[1])
    for i in range(NEON_LAYERS, 0, -1):
        r = int(radius * (1 + i*0.16))
        alpha = max(8, int(45 * (i / NEON_LAYERS)))
        glow = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*base_color, alpha), (r, r), r)
        surf.blit(glow, (cx - r, cy - r), special_flags=0)

# collision helpers
def clamp(v, a, b): return max(a, min(b, v))
def head_hits_rect(head, rect):
    hx, hy = head
    cx = clamp(hx, rect.left, rect.right)
    cy = clamp(hy, rect.top, rect.bottom)
    return math.hypot(hx - cx, hy - cy) < (HEAD_RADIUS + 2)

# start/restart
def start_game():
    global page, score, start_time, game_over, snake, target_pos, obstacles, food, particles
    page = PAGE_GAME
    score = 0
    start_time = time.time()
    game_over = False
    snake = [(WIN_W//2 - i * SEG_SPACING, WIN_H//2) for i in range(INITIAL_LEN)]
    target_pos = (WIN_W//2, WIN_H//2)
    obstacles = generate_obstacles(OBSTACLE_COUNT)
    food = spawn_food(obstacles, snake)
    particles = []

# finger coords for camera preview overlay
finger_x = 0; finger_y = 0

print("Controls: Click START or press S to play. Press R to restart during game or on end screen. Esc to quit.")
running = True
while running:
    for ev in pygame.event.get():
        if ev.type == pygame.QUIT:
            running = False
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_ESCAPE:
                running = False
            if ev.key == pygame.K_s and page == PAGE_MAIN:
                start_game()
            if ev.key == pygame.K_r:
                # allow restart both in-game and on end screen
                start_game()
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            mx, my = ev.pos
            if page == PAGE_MAIN:
                if start_btn_rect.collidepoint(mx, my):
                    start_game()
            # no clickable restart on end page; R key used

    # PAGE MAIN
    if page == PAGE_MAIN:
        if main_bg_img:
            screen.blit(main_bg_img, (0,0))
        else:
            screen.fill(COLOR_BG)
            title = bigfont.render("Finger Snake", True, COLOR_UI)
            screen.blit(title, (WIN_W//2 - title.get_width()//2, 120))
        screen.blit(start_btn_img, start_btn_rect.topleft)
        info = font.render("Click START or press S to begin", True, (200,200,230))
        screen.blit(info, (WIN_W//2 - info.get_width()//2, start_btn_rect.bottom + 18))
        pygame.display.flip()
        clock.tick(FPS)
        continue

    # PAGE GAME
    if page == PAGE_GAME:
        elapsed = time.time() - start_time
        time_left = max(0, int(TIME_LIMIT - elapsed))
        if time_left <= 0:
            game_over = True

        # camera read
        ret, frame = cap.read()
        if not ret:
            print("Camera frame missing.")
            running = False
            break
        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb)

        if results.multi_hand_landmarks:
            lm = results.multi_hand_landmarks[0].landmark[8]
            finger_x = int(lm.x * frame.shape[1])
            finger_y = int(lm.y * frame.shape[0])
            target_pos = (int(lm.x * WIN_W), int(lm.y * WIN_H))
            cv2.circle(frame, (finger_x, finger_y), 7, (0,255,255), -1)
        else:
            tx, ty = target_pos
            # gentle drift when no hand
            target_pos = (int(tx*0.92 + WIN_W*0.08*0.5), int(ty*0.92 + WIN_H*0.08*0.5))

        # move snake
        hx, hy = snake[0]
        tx, ty = target_pos
        dx, dy = tx - hx, ty - hy
        dist = math.hypot(dx, dy)
        if dist > 1:
            nx = hx + (dx/dist)*SNAKE_SPEED
            ny = hy + (dy/dist)*SNAKE_SPEED
        else:
            nx, ny = hx, hy

        snake.insert(0, (nx, ny))
        desired_len = INITIAL_LEN + score
        if len(snake) > desired_len:
            snake.pop()

        # eat check with sound + explosion
        if math.hypot(nx - food[0], ny - food[1]) < (FOOD_RADIUS + HEAD_RADIUS):
            score += 1
            if eat_sound:
                try: eat_sound.play()
                except Exception: pass
            if explode_sound:
                try: explode_sound.play()
                except Exception: pass
            spawn_explosion(food[0], food[1])
            food = spawn_food(obstacles, snake)

        # collisions: walls
        if nx < 6 or ny < 6 or nx > WIN_W - 6 or ny > WIN_H - 6:
            game_over = True

        # obstacles
        for rect in obstacles:
            if head_hits_rect((nx, ny), rect.inflate(-16, -16)):
                game_over = True
                break

        # self-collision
        for i in range(9, len(snake)):
            if math.hypot(nx - snake[i][0], ny - snake[i][1]) < (HEAD_RADIUS - 6):
                game_over = True
                break

        # update particles
        now = time.time()
        alive = []
        for p in particles:
            age = now - p["born"]
            if age < p["life"]:
                dt = 1.0 / FPS
                p["pos"][0] += p["vel"][0] * dt
                p["pos"][1] += p["vel"][1] * dt
                p["vel"][0] *= 0.99
                p["vel"][1] *= 0.99
                alive.append(p)
        particles = alive

        # draw background
        if game_bg_img:
            screen.blit(game_bg_img, (0,0))
        else:
            screen.fill((14,16,22))

        # draw obstacles
        for rect in obstacles:
            glow = pygame.Surface((rect.width+12, rect.height+12), pygame.SRCALPHA)
            pygame.draw.rect(glow, (30,70,90,36), (0,0,rect.width+12, rect.height+12), border_radius=8)
            screen.blit(glow, (rect.left-6, rect.top-6))
            pygame.draw.rect(screen, (40,40,56), rect, border_radius=6)
            pygame.draw.rect(screen, (90,140,170), rect, width=2, border_radius=6)

        # draw food
        fx, fy = food
        draw_neon_circle(screen, (fx, fy), (255,110,90), FOOD_RADIUS+6)
        pygame.draw.circle(screen, (255,90,90), (fx, fy), FOOD_RADIUS)
        pygame.draw.circle(screen, (255,220,180), (fx, fy), max(3, FOOD_RADIUS//3))

        # draw snake neon
        for idx, (x,y) in enumerate(reversed(snake)):
            real_idx = len(snake) - 1 - idx
            t = real_idx / max(1, len(snake)-1)
            base_color = (int(60 + (1-t)*160), int(200 - (1-t)*60), int(200 - t*100))
            rad = HEAD_RADIUS if real_idx==0 else max(8, HEAD_RADIUS - int(t*4))
            glow_r = rad + (6 if real_idx==0 else 3)
            draw_neon_circle(screen, (x,y), base_color, glow_r)
            pygame.draw.circle(screen, base_color, (int(x), int(y)), rad)
            if real_idx == 0:
                pygame.draw.circle(screen, (255,255,220), (int(x), int(y)), max(3, rad//2))

        # draw particles
        for p in particles:
            age = now - p["born"]
            life_frac = max(0, 1 - age / p["life"])
            alpha = int(255 * life_frac)
            col = p["color"]
            surf = pygame.Surface((p["size"]*4, p["size"]*4), pygame.SRCALPHA)
            pygame.draw.circle(surf, (*col, alpha), (p["size"]*2, p["size"]*2), p["size"])
            screen.blit(surf, (p["pos"][0] - p["size"]*2, p["pos"][1] - p["size"]*2))

        # UI: centered score & timer at top
        score_surf = font.render(f"Score: {score}", True, COLOR_UI)
        timer_surf = font.render(f"Time Left: {time_left}", True, (255,220,140))
        score_x = WIN_W // 2 - score_surf.get_width() // 2
        timer_x = WIN_W // 2 - timer_surf.get_width() // 2
        screen.blit(score_surf, (score_x, 10))
        screen.blit(timer_surf, (timer_x, 44))

        # camera preview top-right (small)
        cam_frame_h = int(CAM_W * frame.shape[0] / frame.shape[1])
        cam_frame = cv2.resize(frame, (CAM_W, cam_frame_h))
        cam_rgb = cv2.cvtColor(cam_frame, cv2.COLOR_BGR2RGB)
        try:
            cam_surface = pygame.surfarray.make_surface(cam_rgb.swapaxes(0,1))
        except Exception:
            # fallback: convert with pygame.image.frombuffer
            cam_surface = pygame.image.frombuffer(cam_rgb.tobytes(), (CAM_W, cam_frame_h), "RGB")
        cam_x = WIN_W - CAM_W - CAM_MARGIN_RIGHT
        cam_y = CAM_MARGIN_TOP
        # border and blit
        border = pygame.Surface((CAM_W+8, cam_frame_h+8), pygame.SRCALPHA)
        pygame.draw.rect(border, (40,70,90,200), (0,0, CAM_W+8, cam_frame_h+8), border_radius=10)
        screen.blit(border, (cam_x-4, cam_y-4))
        screen.blit(cam_surface, (cam_x, cam_y))

        # dot overlay for finger
        px = cam_x + int((finger_x / frame.shape[1]) * CAM_W) if frame.shape[1] != 0 else cam_x + CAM_W//2
        py = cam_y + int((finger_y / frame.shape[0]) * cam_frame_h) if frame.shape[0] != 0 else cam_y + cam_frame_h//2
        pygame.draw.circle(screen, (255,240,80), (px, py), 6)
        pygame.draw.circle(screen, (255,255,200), (px, py), 10, width=2)

        pygame.display.flip()
        clock.tick(FPS)

        # handle game over
        if game_over:
            # play gameover sound once
            if gameover_sound:
                try: gameover_sound.play()
                except Exception: pass
            page = PAGE_END
            # tiny delay to allow sound to start
            time.sleep(0.08)
        continue

    # PAGE END
    if page == PAGE_END:
        if end_bg_img:
            screen.blit(end_bg_img, (0,0))
        else:
            screen.fill((8,8,12))
            txt = bigfont.render("CONGRATULATIONS!", True, (240,220,220))
            screen.blit(txt, (WIN_W//2 - txt.get_width()//2, 140))

        # BIG bold score text centered
        bigbold = pygame.font.SysFont("Arial", 64, bold=True)
        score_txt = bigbold.render(f"YOU COLLECTED {score} POINTS!", True, (255, 255, 255))
        screen.blit(score_txt, (WIN_W//2 - score_txt.get_width()//2, WIN_H//2 - 40))

        # show small hint that R restarts (optional subtle)
        hint = font.render("Press R to play again or Esc to quit", True, (200,200,230))
        screen.blit(hint, (WIN_W//2 - hint.get_width()//2, WIN_H//2 + 60))

        pygame.display.flip()
        clock.tick(FPS)
        continue

# cleanup
cap.release()
hands.close()
pygame.quit()
print("Exited cleanly.")
