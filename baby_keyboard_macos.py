"""
Baby Keyboard (macOS) — безопасная песочница для малыша.
Полноэкранное приложение: нажатия клавиш показывают символы поверх
анимации пузырьков шампанского. Пузырьки плывут снизу вверх и лопаются
при наведении мыши. Закрытие только по Ctrl+Enter.

Требования: pip install pygame pyobjc-framework-Quartz
"""

import threading
import time
import random
import colorsys
import math
import sys

import pygame

# ─── macOS: блокировка системных клавиш через CGEventTap ──────────

try:
    import Quartz
    from Quartz import (
        CGEventTapCreate,
        CGEventTapEnable,
        kCGSessionEventTap,
        kCGHeadInsertEventTap,
        kCGEventKeyDown,
        kCGEventKeyUp,
        kCGEventFlagsChanged,
        CGEventGetIntegerValueField,
        kCGKeyboardEventKeycode,
        CGEventGetFlags,
        kCGEventFlagMaskCommand,
        kCGEventFlagMaskControl,
        kCGEventFlagMaskAlternate,
        CFMachPortCreateRunLoopSource,
        CFRunLoopGetCurrent,
        CFRunLoopAddSource,
        CFRunLoopRun,
        CFRunLoopStop,
        kCFRunLoopCommonModes,
    )
    HAS_QUARTZ = True
except ImportError:
    HAS_QUARTZ = False
    print("WARN: pyobjc-framework-Quartz не установлен, "
          "системные клавиши не будут заблокированы", file=sys.stderr)

# macOS keycodes
KC_TAB    = 48
KC_Q      = 12
KC_W      = 13
KC_H      = 4
KC_M      = 46
KC_SPACE  = 49
KC_F4     = 118
KC_ESCAPE = 53
KC_RETURN = 36

# ─── Глобальное состояние ──────────────────────────────────────────

ctrl_enter_pressed = False
_run_loop_ref = None


def _event_tap_callback(proxy, event_type, event, refcon):
    global ctrl_enter_pressed
    if event_type not in (kCGEventKeyDown, kCGEventKeyUp, kCGEventFlagsChanged):
        return event
    keycode = CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode)
    flags   = CGEventGetFlags(event)
    cmd  = bool(flags & kCGEventFlagMaskCommand)
    ctrl = bool(flags & kCGEventFlagMaskControl)
    alt  = bool(flags & kCGEventFlagMaskAlternate)

    if ctrl and keycode == KC_RETURN and event_type == kCGEventKeyDown:
        ctrl_enter_pressed = True
        return event

    if cmd and keycode in (KC_TAB, KC_Q, KC_W, KC_H, KC_M, KC_SPACE, KC_F4):
        return None
    if cmd and alt and keycode == KC_ESCAPE:
        return None

    return event


def _tap_thread():
    global _run_loop_ref
    if not HAS_QUARTZ:
        return
    event_mask = (
        (1 << kCGEventKeyDown) |
        (1 << kCGEventKeyUp) |
        (1 << kCGEventFlagsChanged)
    )
    tap = CGEventTapCreate(
        kCGSessionEventTap, kCGHeadInsertEventTap, 0,
        event_mask, _event_tap_callback, None,
    )
    if tap is None:
        print("WARN: не удалось создать CGEventTap. "
              "Системные настройки → Конфиденциальность → Универсальный доступ",
              file=sys.stderr)
        return
    source = CFMachPortCreateRunLoopSource(None, tap, 0)
    _run_loop_ref = CFRunLoopGetCurrent()
    CFRunLoopAddSource(_run_loop_ref, source, kCFRunLoopCommonModes)
    CGEventTapEnable(tap, True)
    CFRunLoopRun()


def start_hook():
    t = threading.Thread(target=_tap_thread, daemon=True)
    t.start()
    return t


def stop_hook():
    global _run_loop_ref
    if _run_loop_ref and HAS_QUARTZ:
        CFRunLoopStop(_run_loop_ref)
        _run_loop_ref = None


# ─── Утилиты ───────────────────────────────────────────────────────

def hue_to_rgb(hue):
    r, g, b = colorsys.hsv_to_rgb(hue % 1.0, 1.0, 1.0)
    return (int(r * 255), int(g * 255), int(b * 255))


# ─── Фон ───────────────────────────────────────────────────────────

def create_background(W, H):
    bg = pygame.Surface((W, H))

    top    = (168, 213, 245)
    mid    = (185, 224, 248)
    bottom = (205, 235, 252)
    for y in range(H):
        t = y / H
        if t < 0.5:
            f = t * 2
            c = tuple(int(top[i] + (mid[i] - top[i]) * f) for i in range(3))
        else:
            f = (t - 0.5) * 2
            c = tuple(int(mid[i] + (bottom[i] - mid[i]) * f) for i in range(3))
        pygame.draw.line(bg, c, (0, y), (W, y))

    blob_surf = pygame.Surface((W, H), pygame.SRCALPHA)
    blobs = [
        (W * 0.08,  H * 0.12, 260, (140, 190, 230, 28)),
        (W * 0.85,  H * 0.08, 220, (160, 205, 240, 24)),
        (W * 0.55,  H * 0.35, 300, (150, 200, 238, 18)),
        (W * 0.12,  H * 0.65, 240, (130, 185, 225, 22)),
        (W * 0.92,  H * 0.60, 200, (155, 198, 235, 20)),
        (W * 0.40,  H * 0.80, 280, (145, 195, 235, 18)),
        (W * 0.72,  H * 0.88, 190, (165, 210, 242, 22)),
        (W * 0.25,  H * 0.45, 170, (170, 215, 245, 16)),
        (W * 0.65,  H * 0.18, 150, (155, 202, 238, 20)),
    ]
    for bx, by, br, col in blobs:
        for step in range(6, 0, -1):
            t = step / 6
            a = int(col[3] * (1 - t * 0.6))
            r = int(br * t)
            pygame.draw.circle(blob_surf, (col[0], col[1], col[2], a),
                               (int(bx), int(by)), r)
    bg.blit(blob_surf, (0, 0))

    dot_surf = pygame.Surface((W, H), pygame.SRCALPHA)
    for _ in range(220):
        dx = random.randint(0, W)
        dy = random.randint(0, H)
        dr = random.choice([1, 1, 2, 2, 3])
        da = random.randint(18, 55)
        pygame.draw.circle(dot_surf, (255, 255, 255, da), (dx, dy), dr)
    bg.blit(dot_surf, (0, 0))

    return bg


# ─── Пузырь — Aero Glass ───────────────────────────────────────────

_bubble_surf_cache: dict = {}


def _build_bubble_surf(r: int) -> pygame.Surface:
    size = (r + 6) * 2
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    cx = cy = r + 6

    for ring in range(r, 0, -max(1, r // 8)):
        t = ring / r
        a = int(8 + 22 * (t ** 1.5))
        pygame.draw.circle(s, (190, 225, 255, a), (cx, cy), ring)

    pygame.draw.circle(s, (220, 240, 255, 55), (cx, cy), max(1, r - 4), 1)
    pygame.draw.circle(s, (255, 255, 255, 210), (cx, cy), r, 3)

    shine_w = int(r * 1.35)
    shine_h = int(r * 0.60)
    shine_y0 = cy - r + 5
    for i in range(8, 0, -1):
        t = i / 8
        ew = int(shine_w * math.sqrt(t))
        eh = int(shine_h * t)
        a = int(165 * math.sin(t * math.pi))
        if ew > 1 and eh > 1:
            pygame.draw.ellipse(s, (255, 255, 255, a),
                                (cx - ew // 2, shine_y0, ew, eh))

    hx = cx - r // 3
    hy = cy - int(r * 0.52)
    hr = max(2, r // 7)
    pygame.draw.circle(s, (255, 255, 255, 245), (hx, hy), hr)
    pygame.draw.circle(s, (255, 255, 255, 255), (hx, hy), max(1, hr // 2))

    ref_w = int(r * 0.85)
    ref_h = int(r * 0.28)
    pygame.draw.ellipse(s, (210, 235, 255, 45),
                        (cx - ref_w // 2, cy + int(r * 0.52), ref_w, ref_h))
    return s


def get_bubble_surf(r: int) -> pygame.Surface:
    r = max(4, int(r))
    if r not in _bubble_surf_cache:
        _bubble_surf_cache[r] = _build_bubble_surf(r)
    return _bubble_surf_cache[r]


def draw_aero_bubble(surface, x, y, radius, alpha=255):
    surf = get_bubble_surf(int(radius))
    if alpha < 255:
        surf = surf.copy()
        surf.set_alpha(alpha)
    r = int(radius) + 6
    surface.blit(surf, (int(x) - r, int(y) - r))


# ─── Класс большого пузырька ───────────────────────────────────────

class Bubble:
    TARGET_COUNT = 18
    SPEED_MIN = 40
    SPEED_MAX = 70
    RADIUS_MIN = 52
    RADIUS_MAX = 95

    def __init__(self, W, H, start_offscreen=True):
        self.W = W
        self.H = H
        self._respawn(start_offscreen)

    def _respawn(self, start_offscreen=True):
        self.radius = random.uniform(self.RADIUS_MIN, self.RADIUS_MAX)
        pad = self.radius + 15
        self.x = random.uniform(pad, self.W - pad)
        if start_offscreen:
            self.y = self.H + self.radius + random.uniform(10, 200)
        else:
            self.y = random.uniform(self.H * 0.3, self.H - pad)
        self.speed = random.uniform(self.SPEED_MIN, self.SPEED_MAX)
        self.wobble_phase = random.uniform(0, math.pi * 2)
        self.wobble_amp   = random.uniform(10, 25)
        self.wobble_speed = random.uniform(0.6, 1.2)
        self.alive = True
        self.popping = False
        self.pop_alpha = 255
        self.pop_particles = []
        self.pop_timer = 0.0
        self.reached_top = False

    def update(self, dt, mx, my):
        if self.popping:
            self.pop_timer += dt
            self.pop_alpha = max(0, int(255 * (1.0 - self.pop_timer / 0.5)))
            for p in self.pop_particles:
                p['x']  += p['vx'] * dt
                p['y']  += p['vy'] * dt
                p['vy'] -= 80 * dt
                p['vx'] *= 0.96
                p['life'] -= dt
            self.pop_particles = [p for p in self.pop_particles if p['life'] > 0]
            if self.pop_timer > 0.9:
                self.alive = False
            return

        self.y -= self.speed * dt
        self.wobble_phase += self.wobble_speed * dt
        self.x += math.sin(self.wobble_phase) * self.wobble_amp * dt
        self.x = max(self.radius + 10, min(self.W - self.radius - 10, self.x))

        if math.hypot(mx - self.x, my - self.y) < self.radius + 8:
            self.pop()

        if self.y + self.radius < -10:
            self.reached_top = True
            self.alive = False

    def pop(self):
        self.popping = True
        for _ in range(random.randint(12, 20)):
            angle = random.uniform(0, math.pi * 2)
            spd   = random.uniform(80, 220)
            life  = random.uniform(0.3, 0.75)
            self.pop_particles.append({
                'x': self.x + random.uniform(-self.radius * 0.4, self.radius * 0.4),
                'y': self.y + random.uniform(-self.radius * 0.4, self.radius * 0.4),
                'vx': math.cos(angle) * spd,
                'vy': math.sin(angle) * spd - 140,
                'r': random.uniform(4, self.radius * 0.28),
                'life': life, 'max_life': life,
            })

    def draw(self, surface):
        if self.popping:
            if self.pop_alpha > 0:
                draw_aero_bubble(surface, self.x, self.y, self.radius, self.pop_alpha)
            for p in self.pop_particles:
                a = int(230 * (p['life'] / p['max_life']))
                draw_aero_bubble(surface, p['x'], p['y'], max(3, p['r']), a)
            return
        draw_aero_bubble(surface, self.x, self.y, self.radius)


# ─── Шипение шампанского ───────────────────────────────────────────

class FizzSystem:
    ZONE_H     = 90
    SPAWN_RATE = 0.022

    def __init__(self, W, H):
        self.W = W
        self.H = H
        self.particles = []
        self._timer = 0.0

    def spawn_burst(self, x, n=14):
        for _ in range(n):
            self.particles.append(self._make(
                x=x + random.uniform(-40, 40),
                y=random.uniform(0, self.ZONE_H),
            ))

    def _make(self, x=None, y=None):
        if x is None:
            x = random.uniform(0, self.W)
        if y is None:
            y = random.uniform(0, self.ZONE_H)
        life = random.uniform(0.5, 1.4)
        return {
            'x': x, 'y': y,
            'vx': random.uniform(-10, 10),
            'vy': random.uniform(-30, -8),
            'r':  random.uniform(2, 6),
            'life': life, 'max_life': life,
        }

    def update(self, dt):
        self._timer += dt
        while self._timer >= self.SPAWN_RATE:
            self._timer -= self.SPAWN_RATE
            for _ in range(random.randint(2, 4)):
                self.particles.append(self._make())
        for p in self.particles:
            p['x'] += p['vx'] * dt
            p['y'] += p['vy'] * dt
            p['life'] -= dt
        self.particles = [p for p in self.particles if p['life'] > 0]

    def draw(self, surface):
        for p in self.particles:
            a = int(210 * (p['life'] / p['max_life']))
            draw_aero_bubble(surface, p['x'], p['y'], max(2, int(p['r'])), a)


# ─── Главное приложение ────────────────────────────────────────────

def main():
    global ctrl_enter_pressed

    start_hook()
    time.sleep(0.2)

    pygame.init()
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN | pygame.NOFRAME)
    pygame.display.set_caption("Baby Keyboard")
    W, H = screen.get_size()

    clock = pygame.time.Clock()
    font  = pygame.font.SysFont("Arial", 96, bold=True)

    background = create_background(W, H)

    for r in range(Bubble.RADIUS_MIN, Bubble.RADIUS_MAX + 1, 4):
        get_bubble_surf(r)

    dyn_surf   = pygame.Surface((W, H), pygame.SRCALPHA)
    trail_surf = pygame.Surface((W, H), pygame.SRCALPHA)

    trail = []
    TRAIL_LIFETIME = 2.0
    trail_hue = 0.0

    bubbles = [Bubble(W, H, start_offscreen=False) for _ in range(Bubble.TARGET_COUNT)]
    for b in bubbles:
        b.y = random.uniform(b.radius + 10, H - b.radius - 10)

    fizz = FizzSystem(W, H)

    chars = []
    cursor_x, cursor_y = 20, 20
    line_height = 115

    running = True

    while running:
        now = time.time()
        dt  = min(clock.get_time() / 1000.0, 0.05)
        mx, my = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pass
            elif event.type == pygame.KEYDOWN:
                mods = pygame.key.get_mods()
                if (mods & pygame.KMOD_CTRL) and event.key == pygame.K_RETURN:
                    running = False
                    break
                if event.unicode and event.unicode.isprintable():
                    surf = font.render(event.unicode, True, (35, 45, 80))
                    if cursor_x + surf.get_width() > W - 20:
                        cursor_x = 20
                        cursor_y += line_height
                    if cursor_y + line_height > H:
                        chars.clear()
                        cursor_x = 20
                        cursor_y = 20
                    chars.append((surf, cursor_x, cursor_y))
                    cursor_x += surf.get_width() + 5
            elif event.type == pygame.MOUSEMOTION:
                trail_hue += 0.002
                trail.append((event.pos[0], event.pos[1], hue_to_rgb(trail_hue), now))

        if ctrl_enter_pressed:
            running = False

        for b in bubbles:
            b.update(dt, mx, my)

        alive_next = []
        for b in bubbles:
            if b.reached_top:
                fizz.spawn_burst(b.x)
            if b.alive:
                alive_next.append(b)
        bubbles = alive_next

        while len(bubbles) < Bubble.TARGET_COUNT:
            bubbles.append(Bubble(W, H, start_offscreen=True))

        fizz.update(dt)

        cutoff = now - TRAIL_LIFETIME
        while trail and trail[0][3] < cutoff:
            trail.pop(0)

        screen.blit(background, (0, 0))

        dyn_surf.fill((0, 0, 0, 0))
        for b in bubbles:
            b.draw(dyn_surf)
        fizz.draw(dyn_surf)
        screen.blit(dyn_surf, (0, 0))

        trail_surf.fill((0, 0, 0, 0))
        for i in range(1, len(trail)):
            x0, y0, c0, ts0 = trail[i - 1]
            x1, y1, c1, ts1 = trail[i]
            age   = now - ts1
            alpha = max(0, int(255 * (1.0 - age / TRAIL_LIFETIME)))
            width = max(2, int(10 * (1.0 - age / TRAIL_LIFETIME)))
            if alpha > 0:
                pygame.draw.line(trail_surf, (*c1, alpha), (x0, y0), (x1, y1), width)
        screen.blit(trail_surf, (0, 0))

        for surf, x, y in chars:
            screen.blit(surf, (x, y))

        pygame.display.flip()
        clock.tick(60)

    stop_hook()
    pygame.quit()


if __name__ == "__main__":
    main()
