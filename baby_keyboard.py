"""
Baby Keyboard — безопасная песочница для малыша.
Полноэкранное приложение: нажатия клавиш показывают символы поверх
анимации пузырьков шампанского. Пузырьки плывут снизу вверх и лопаются
при наведении мыши. Закрытие только по Ctrl+G+Enter.
"""

import array
import ctypes
import ctypes.wintypes as wintypes
import io
import threading
import time
import random
import colorsys
import math
import sys
import wave
from collections import deque

import pygame

# ─── Win32 константы ───────────────────────────────────────────────

WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_SYSKEYDOWN = 0x0104

VK_LWIN   = 0x5B
VK_RWIN   = 0x5C
VK_TAB    = 0x09
VK_ESCAPE = 0x1B
VK_F4     = 0x73
VK_DELETE = 0x2E
VK_RETURN = 0x0D
VK_G      = 0x47

LLKHF_ALTDOWN = 0x20
HWND_TOPMOST  = -1
SWP_NOMOVE    = 0x0002
SWP_NOSIZE    = 0x0001

user32  = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

user32.SetWindowsHookExW.argtypes = [
    ctypes.c_int, ctypes.c_void_p, wintypes.HINSTANCE, wintypes.DWORD,
]
user32.SetWindowsHookExW.restype  = ctypes.c_void_p
user32.CallNextHookEx.argtypes    = [
    ctypes.c_void_p, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM,
]
user32.CallNextHookEx.restype     = ctypes.c_long
user32.UnhookWindowsHookEx.argtypes = [ctypes.c_void_p]
user32.UnhookWindowsHookEx.restype  = wintypes.BOOL
user32.GetAsyncKeyState.argtypes    = [ctypes.c_int]
user32.GetAsyncKeyState.restype     = ctypes.c_short
kernel32.GetModuleHandleW.argtypes  = [wintypes.LPCWSTR]
kernel32.GetModuleHandleW.restype   = wintypes.HMODULE
user32.SystemParametersInfoW.argtypes = [
    wintypes.UINT, wintypes.UINT, ctypes.c_void_p, wintypes.UINT,
]
user32.SystemParametersInfoW.restype  = wintypes.BOOL
user32.SetForegroundWindow.argtypes   = [wintypes.HWND]
user32.SetForegroundWindow.restype    = wintypes.BOOL

HOOKPROC = ctypes.CFUNCTYPE(
    ctypes.c_long, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM,
)


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode",      wintypes.DWORD),
        ("scanCode",    wintypes.DWORD),
        ("flags",       wintypes.DWORD),
        ("time",        wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


# ─── Специальные возможности Windows ──────────────────────────────
# 5×Shift → StickyKeys, Shift ×8с → FilterKeys, NumLock ×5с → ToggleKeys
# Отключаем их горячие клавиши на время работы и восстанавливаем при выходе.

SPI_GETSTICKYKEYS = 0x003A
SPI_SETSTICKYKEYS = 0x003B
SPI_GETFILTERKEYS = 0x0032
SPI_SETFILTERKEYS = 0x0033
SPI_GETTOGGLEKEYS = 0x0034
SPI_SETTOGGLEKEYS = 0x0035


class STICKYKEYS(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("dwFlags", wintypes.DWORD)]


class FILTERKEYS(ctypes.Structure):
    _fields_ = [
        ("cbSize",      wintypes.DWORD),
        ("dwFlags",     wintypes.DWORD),
        ("iWaitMSec",   wintypes.DWORD),
        ("iDelayMSec",  wintypes.DWORD),
        ("iRepeatMSec", wintypes.DWORD),
        ("iBounceMSec", wintypes.DWORD),
    ]


class TOGGLEKEYS(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("dwFlags", wintypes.DWORD)]


_saved_sk = STICKYKEYS(cbSize=ctypes.sizeof(STICKYKEYS), dwFlags=0)
_saved_fk = FILTERKEYS(cbSize=ctypes.sizeof(FILTERKEYS), dwFlags=0)
_saved_tk = TOGGLEKEYS(cbSize=ctypes.sizeof(TOGGLEKEYS), dwFlags=0)


def disable_accessibility_shortcuts():
    """Сохраняет и отключает горячие клавиши StickyKeys/FilterKeys/ToggleKeys."""
    global _saved_sk, _saved_fk, _saved_tk
    _saved_sk = STICKYKEYS(cbSize=ctypes.sizeof(STICKYKEYS), dwFlags=0)
    user32.SystemParametersInfoW(SPI_GETSTICKYKEYS,
                                 ctypes.sizeof(STICKYKEYS), ctypes.byref(_saved_sk), 0)
    _saved_fk = FILTERKEYS(cbSize=ctypes.sizeof(FILTERKEYS), dwFlags=0)
    user32.SystemParametersInfoW(SPI_GETFILTERKEYS,
                                 ctypes.sizeof(FILTERKEYS), ctypes.byref(_saved_fk), 0)
    _saved_tk = TOGGLEKEYS(cbSize=ctypes.sizeof(TOGGLEKEYS), dwFlags=0)
    user32.SystemParametersInfoW(SPI_GETTOGGLEKEYS,
                                 ctypes.sizeof(TOGGLEKEYS), ctypes.byref(_saved_tk), 0)

    user32.SystemParametersInfoW(SPI_SETSTICKYKEYS, ctypes.sizeof(STICKYKEYS),
                                 ctypes.byref(STICKYKEYS(cbSize=ctypes.sizeof(STICKYKEYS), dwFlags=0)), 0)
    user32.SystemParametersInfoW(SPI_SETFILTERKEYS, ctypes.sizeof(FILTERKEYS),
                                 ctypes.byref(FILTERKEYS(cbSize=ctypes.sizeof(FILTERKEYS), dwFlags=0)), 0)
    user32.SystemParametersInfoW(SPI_SETTOGGLEKEYS, ctypes.sizeof(TOGGLEKEYS),
                                 ctypes.byref(TOGGLEKEYS(cbSize=ctypes.sizeof(TOGGLEKEYS), dwFlags=0)), 0)


def restore_accessibility_shortcuts():
    """Восстанавливает исходные настройки специальных возможностей."""
    user32.SystemParametersInfoW(SPI_SETSTICKYKEYS,
                                 ctypes.sizeof(STICKYKEYS), ctypes.byref(_saved_sk), 0)
    user32.SystemParametersInfoW(SPI_SETFILTERKEYS,
                                 ctypes.sizeof(FILTERKEYS), ctypes.byref(_saved_fk), 0)
    user32.SystemParametersInfoW(SPI_SETTOGGLEKEYS,
                                 ctypes.sizeof(TOGGLEKEYS), ctypes.byref(_saved_tk), 0)


# ─── Глобальное состояние ──────────────────────────────────────────

hook_id            = None
ctrl_enter_pressed = False
_hook_ready        = threading.Event()


def _kb_hook_proc(nCode, wParam, lParam):
    global ctrl_enter_pressed
    if nCode >= 0 and wParam in (WM_KEYDOWN, WM_SYSKEYDOWN):
        kb = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
        vk = kb.vkCode
        alt_down  = bool(kb.flags & LLKHF_ALTDOWN)
        ctrl_down = bool(user32.GetAsyncKeyState(0xA2) & 0x8000) or bool(
            user32.GetAsyncKeyState(0xA3) & 0x8000
        )
        if ctrl_down and vk == VK_RETURN:
            g_down = bool(user32.GetAsyncKeyState(VK_G) & 0x8000)
            if g_down:
                ctrl_enter_pressed = True
            return user32.CallNextHookEx(hook_id, nCode, wParam, lParam)
        if vk in (VK_LWIN, VK_RWIN):
            return 1
        if alt_down and vk in (VK_TAB, VK_F4, VK_ESCAPE):
            return 1
        if ctrl_down and vk == VK_ESCAPE:
            return 1
        if ctrl_down and alt_down and vk == VK_DELETE:
            return 1
    return user32.CallNextHookEx(hook_id, nCode, wParam, lParam)


_hook_callback = HOOKPROC(_kb_hook_proc)


def _hook_thread():
    global hook_id
    hook_id = user32.SetWindowsHookExW(
        WH_KEYBOARD_LL, _hook_callback, kernel32.GetModuleHandleW(None), 0
    )
    if not hook_id:
        err = ctypes.GetLastError()
        print(f"WARN: хук не установлен (err={err})", file=sys.stderr)
        _hook_ready.set()  # разблокируем даже при ошибке
        return
    _hook_ready.set()
    msg = wintypes.MSG()
    while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
        user32.TranslateMessage(ctypes.byref(msg))
        user32.DispatchMessageW(ctypes.byref(msg))


def start_hook():
    _hook_ready.clear()
    t = threading.Thread(target=_hook_thread, daemon=True)
    t.start()
    _hook_ready.wait(timeout=1.0)
    return t


def stop_hook():
    global hook_id
    if hook_id:
        user32.UnhookWindowsHookEx(hook_id)
        hook_id = None


# ─── Фон ───────────────────────────────────────────────────────────

def create_background(W, H):
    """
    Рисует фон в стиле Telegram: мягкий градиент + цветные
    акварельные пятна + лёгкая текстура из точек.
    """
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
    """
    Рисует один пузырь в стиле Windows Aero:
    почти прозрачное тело + стеклянный блик + яркая окантовка + блик-точка.
    """
    size = (r + 6) * 2
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    cx = cy = r + 6

    for ring in range(r, 0, -max(1, r // 8)):
        t = ring / r
        a = int(8 + 22 * (t ** 1.5))
        pygame.draw.circle(s, (190, 225, 255, a), (cx, cy), ring)

    pygame.draw.circle(s, (220, 240, 255, 55), (cx, cy), max(1, r - 4), 1)
    pygame.draw.circle(s, (255, 255, 255, 210), (cx, cy), r, 3)

    shine_w  = int(r * 1.35)
    shine_h  = int(r * 0.60)
    shine_y0 = cy - r + 5
    steps = 8
    for i in range(steps, 0, -1):
        t  = i / steps
        ew = int(shine_w * math.sqrt(t))
        eh = int(shine_h * t)
        a  = int(165 * math.sin(t * math.pi))
        if ew > 1 and eh > 1:
            pygame.draw.ellipse(
                s, (255, 255, 255, a),
                (cx - ew // 2, shine_y0, ew, eh)
            )

    hx = cx - r // 3
    hy = cy - int(r * 0.52)
    hr = max(2, r // 7)
    pygame.draw.circle(s, (255, 255, 255, 245), (hx, hy), hr)
    pygame.draw.circle(s, (255, 255, 255, 255), (hx, hy), max(1, hr // 2))

    ref_w = int(r * 0.85)
    ref_h = int(r * 0.28)
    pygame.draw.ellipse(
        s, (210, 235, 255, 45),
        (cx - ref_w // 2, cy + int(r * 0.52), ref_w, ref_h)
    )

    return s


def get_bubble_surf(r: int) -> pygame.Surface:
    r = max(4, int(r))
    if r not in _bubble_surf_cache:
        _bubble_surf_cache[r] = _build_bubble_surf(r)
    return _bubble_surf_cache[r]


def draw_aero_bubble(surface, x, y, radius, alpha=255):
    """Рисует Aero-пузырь. alpha=255 — полностью, 0 — прозрачный."""
    surf = get_bubble_surf(int(radius))
    if alpha < 255:
        surf = surf.copy()
        surf.set_alpha(alpha)
    cx = int(x)
    cy = int(y)
    r  = int(radius) + 6
    surface.blit(surf, (cx - r, cy - r))


# ─── Класс большого пузырька ───────────────────────────────────────

class Bubble:
    TARGET_COUNT = 18
    SPEED_MIN    = 40
    SPEED_MAX    = 70
    RADIUS_MIN   = 52
    RADIUS_MAX   = 95

    def __init__(self, W, H, start_offscreen=True):
        self.W = W
        self.H = H
        self._respawn(start_offscreen)

    def _respawn(self, start_offscreen=True):
        self.radius       = random.uniform(self.RADIUS_MIN, self.RADIUS_MAX)
        pad               = self.radius + 15
        self.x            = random.uniform(pad, self.W - pad)
        if start_offscreen:
            self.y = self.H + self.radius + random.uniform(10, 200)
        else:
            self.y = random.uniform(self.H * 0.3, self.H - pad)
        self.speed        = random.uniform(self.SPEED_MIN, self.SPEED_MAX)
        self.wobble_phase = random.uniform(0, math.pi * 2)
        self.wobble_amp   = random.uniform(10, 25)
        self.wobble_speed = random.uniform(0.6, 1.2)
        self.alive        = True
        self.popping      = False
        self.pop_alpha    = 255
        self.pop_particles = []
        self.pop_timer    = 0.0
        self.reached_top  = False
        self.has_fish     = random.random() < 0.35
        if self.has_fish:
            count = random.randint(3, 5)
            self.inner_fish = [_make_inner_fish(self.radius) for _ in range(count)]
        else:
            self.inner_fish = []

    def update(self, dt, mx, my):
        if self.popping:
            self.pop_timer += dt
            self.pop_alpha  = max(0, int(255 * (1.0 - self.pop_timer / 0.5)))
            for p in self.pop_particles:
                p['x']    += p['vx'] * dt
                p['y']    += p['vy'] * dt
                p['vy']   -= 80 * dt
                p['vx']   *= 0.96
                p['life'] -= dt
            self.pop_particles = [p for p in self.pop_particles if p['life'] > 0]
            if self.pop_timer > 0.9:
                self.alive = False
            return

        self.y            -= self.speed * dt
        self.wobble_phase += self.wobble_speed * dt
        self.x            += math.sin(self.wobble_phase) * self.wobble_amp * dt
        self.x             = max(self.radius + 10, min(self.W - self.radius - 10, self.x))

        # Мальки плавают внутри пузыря
        for f in self.inner_fish:
            f['wiggle'] += f['wiggle_speed'] * dt
            f['angle']  += math.sin(f['wiggle'] * 1.3) * 0.4 * dt
            spd = math.hypot(f['vx'], f['vy'])
            if spd > 1:
                tx = math.cos(f['angle']) * spd
                ty = math.sin(f['angle']) * spd
                f['vx'] += (tx - f['vx']) * 3.5 * dt
                f['vy'] += (ty - f['vy']) * 3.5 * dt
            f['rx'] += f['vx'] * dt
            f['ry'] += f['vy'] * dt
            # Отражение от стенки пузыря
            dist = math.hypot(f['rx'], f['ry'])
            max_r = self.radius * 0.68
            if dist > max_r:
                nx = f['rx'] / dist
                ny = f['ry'] / dist
                dot = f['vx'] * nx + f['vy'] * ny
                f['vx'] -= 2 * dot * nx
                f['vy'] -= 2 * dot * ny
                f['rx']  = nx * max_r * 0.95
                f['ry']  = ny * max_r * 0.95
                f['angle'] = math.atan2(f['vy'], f['vx'])

        if math.hypot(mx - self.x, my - self.y) < self.radius + 8:
            self.pop()

        if self.y + self.radius < -10:
            self.reached_top = True
            self.alive       = False

    def pop(self):
        self.popping = True
        n = random.randint(12, 20)
        for _ in range(n):
            angle  = random.uniform(0, math.pi * 2)
            spd    = random.uniform(80, 220)
            life   = random.uniform(0.3, 0.75)
            r_part = random.uniform(4, self.radius * 0.28)
            self.pop_particles.append({
                'x':        self.x + random.uniform(-self.radius * 0.4, self.radius * 0.4),
                'y':        self.y + random.uniform(-self.radius * 0.4, self.radius * 0.4),
                'vx':       math.cos(angle) * spd,
                'vy':       math.sin(angle) * spd - 140,
                'r':        r_part,
                'life':     life,
                'max_life': life,
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
        if self.inner_fish:
            fry_len = self.radius * 0.46
            for f in self.inner_fish:
                disp_angle = f['angle'] + math.sin(f['wiggle']) * 0.22
                draw_fish(surface,
                          self.x + f['rx'], self.y + f['ry'],
                          fry_len, disp_angle, f['color'], 162)


# ─── Шипение шампанского (верхняя зона) ───────────────────────────

class FizzSystem:
    ZONE_H     = 90
    SPAWN_RATE = 0.022

    def __init__(self, W, H):
        self.W          = W
        self.H          = H
        self.particles  = []
        self._timer     = 0.0

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
            p['x']    += p['vx'] * dt
            p['y']    += p['vy'] * dt
            p['life'] -= dt
        self.particles = [p for p in self.particles if p['life'] > 0]

    def draw(self, surface):
        for p in self.particles:
            a = int(210 * (p['life'] / p['max_life']))
            draw_aero_bubble(surface, p['x'], p['y'], max(2, int(p['r'])), a)



# ─── Мальки ────────────────────────────────────────────────────────

_FISH_COLORS = [
    (255, 120,  40),   # оранжевый
    ( 45, 150, 255),   # синий
    ( 50, 200,  90),   # зелёный
    (255,  55,  90),   # красный
    (255, 200,  30),   # жёлтый
    (155,  75, 255),   # фиолетовый
    ( 35, 200, 195),   # бирюзовый
    (255, 140, 200),   # розовый
]


def draw_fish(surface, x, y, length, angle, color, alpha):
    """
    Взрослая рыба: веретенообразное тело, спинной плавник,
    грудной плавник, раздвоенный хвост, жабры, глаз с зрачком.
    Смотрит ВПРАВО — angle=0 соответствует движению вправо.
    """
    bw   = max(12, int(length))
    bh   = max(6,  int(length * 0.40))
    ts   = max(5,  int(length * 0.52))
    pad  = ts + 6
    w    = bw + pad * 2
    h    = (bh + ts + pad) * 2
    tmp  = pygame.Surface((w, h), pygame.SRCALPHA)
    cx   = w // 2
    cy   = h // 2
    dark = tuple(max(0, c - 70) for c in color)

    # Тело — веретено (6-угольник): нос вправо, хвост влево
    body_pts = [
        (cx + bw // 2,     cy),
        (cx + bw // 4,     cy - bh // 2),
        (cx - bw // 4,     cy - bh // 2),
        (cx - bw // 2,     cy),
        (cx - bw // 4,     cy + bh // 2),
        (cx + bw // 4,     cy + bh // 2),
    ]
    pygame.draw.polygon(tmp, (*color, alpha), body_pts)
    pygame.draw.polygon(tmp, (*dark,  max(0, alpha - 55)), body_pts, 1)

    # Раздвоенный хвост (слева — сзади)
    tx = cx - bw // 2
    tail_pts = [
        (tx,           cy),
        (tx - ts,      cy - ts * 3 // 4),
        (tx - ts // 2, cy),
        (tx - ts,      cy + ts * 3 // 4),
    ]
    pygame.draw.polygon(tmp, (*color, max(0, alpha - 25)), tail_pts)
    pygame.draw.polygon(tmp, (*dark,  max(0, alpha - 75)), tail_pts, 1)

    # Спинной плавник
    dh = int(bh * 0.90)
    dfin_pts = [
        (cx + bw // 8,  cy - bh // 2),
        (cx,            cy - bh // 2 - dh),
        (cx - bw // 5,  cy - bh // 2),
    ]
    pygame.draw.polygon(tmp, (*color, max(0, alpha - 35)), dfin_pts)
    pygame.draw.polygon(tmp, (*dark,  max(0, alpha - 80)), dfin_pts, 1)

    # Брюшной плавник (снизу, симметрично)
    vfin_pts = [
        (cx,           cy + bh // 2),
        (cx + bw // 8, cy + bh // 2),
        (cx - bw // 8, cy + bh // 2 + int(bh * 0.55)),
    ]
    pygame.draw.polygon(tmp, (*color, max(0, alpha - 45)), vfin_pts)

    # Грудной плавник — маленький эллипс
    pfx = cx + bw // 6
    pfy = cy + bh // 5
    pfw = max(3, int(bw * 0.20))
    pfh = max(3, int(bh * 0.50))
    pygame.draw.ellipse(tmp, (*color, max(0, alpha - 45)),
                        (pfx - pfw // 2, pfy - pfh // 2, pfw, pfh))

    # Жаберная дуга
    gx  = cx + bw // 4
    gar = int(bh * 0.62)
    pygame.draw.arc(tmp, (*dark, max(0, alpha - 30)),
                    (gx - gar, cy - gar, gar * 2, gar * 2),
                    math.radians(20), math.radians(160), max(1, bh // 7))

    # Глаз (голова — справа)
    ex = cx + bw // 2 - max(3, int(length * 0.19))
    er = max(3, int(bh * 0.36))
    pygame.draw.circle(tmp, (255, 255, 220, min(255, alpha + 20)), (ex, cy), er)
    pygame.draw.circle(tmp, (*dark, alpha),                        (ex, cy), max(2, er - 1))
    pygame.draw.circle(tmp, (255, 255, 255, alpha),                (ex - er // 3, cy - er // 3), max(1, er // 3))

    deg     = math.degrees(-angle)
    rotated = pygame.transform.rotate(tmp, deg)
    surface.blit(rotated,
                 (int(x) - rotated.get_width()  // 2,
                  int(y) - rotated.get_height() // 2))


def _make_inner_fish(bubble_r):
    """Создаёт словарь одного малька для жизни внутри пузыря."""
    angle = random.uniform(0, math.pi * 2)
    speed = random.uniform(22, 50)
    return {
        'rx':          random.uniform(-bubble_r * 0.38, bubble_r * 0.38),
        'ry':          random.uniform(-bubble_r * 0.38, bubble_r * 0.38),
        'vx':          math.cos(angle) * speed,
        'vy':          math.sin(angle) * speed,
        'angle':       angle,
        'wiggle':      random.uniform(0, math.pi * 2),
        'wiggle_speed': random.uniform(5, 10),
        'color':       random.choice(_FISH_COLORS),
    }


class FishSystem:
    """Мальки, уплывающие из лопнувшего пузыря."""

    def __init__(self):
        self.fishes = []

    def spawn_from_bubble(self, bx, by, bubble_r, inner_fish):
        for f in inner_fish:
            x = bx + f['rx']
            y = by + f['ry']
            dist = math.hypot(f['rx'], f['ry'])
            out_angle = math.atan2(f['ry'], f['rx']) if dist > 1 else f['angle']
            swim_angle = out_angle + random.uniform(-0.7, 0.7)
            speed = random.uniform(80, 170)
            life  = random.uniform(2.2, 3.8)
            self.fishes.append({
                'x':           x,
                'y':           y,
                'vx':          math.cos(swim_angle) * speed,
                'vy':          math.sin(swim_angle) * speed,
                'angle':       swim_angle,
                'wiggle':      f['wiggle'],
                'wiggle_speed': f['wiggle_speed'],
                'life':        life,
                'max_life':    life,
                'length':      bubble_r * random.uniform(0.40, 0.54),
                'color':       f['color'],   # наследует цвет от внутренней рыбки
            })

    def update(self, dt):
        for f in self.fishes:
            f['wiggle'] += f['wiggle_speed'] * dt
            # Плавное виляние: угол чуть меняется синусоидально
            f['angle'] += math.sin(f['wiggle'] * 1.4) * 0.35 * dt
            spd = math.hypot(f['vx'], f['vy'])
            if spd > 2:
                # Плавно поворачиваем скорость к новому углу
                tx = math.cos(f['angle']) * spd
                ty = math.sin(f['angle']) * spd
                f['vx'] += (tx - f['vx']) * 4.0 * dt
                f['vy'] += (ty - f['vy']) * 4.0 * dt
            # Постепенное замедление
            f['vx'] *= 0.988
            f['vy'] *= 0.988
            f['x']  += f['vx'] * dt
            f['y']  += f['vy'] * dt
            f['life'] -= dt
        self.fishes = [f for f in self.fishes if f['life'] > 0]

    def draw(self, surface):
        for f in self.fishes:
            t     = f['life'] / f['max_life']
            alpha = int(215 * t)
            # Визуальное виляние тела при отрисовке
            disp_angle = f['angle'] + math.sin(f['wiggle'] * 2.0) * 0.20
            draw_fish(surface, f['x'], f['y'], f['length'], disp_angle, f['color'], alpha)


# ─── Краска — брызги при лопании ───────────────────────────────────

_PAINT_COLORS = [
    (255,  80,  60),
    (255, 165,   0),
    ( 80, 200,  80),
    ( 60, 120, 255),
    (220,  50, 220),
    (255, 220,   0),
    ( 40, 200, 200),
    (255, 120, 180),
]


class PaintSystem:
    """Брызги краски при лопании пузыря без рыбок."""

    def __init__(self):
        self.blobs = []

    def spawn(self, x, y, bubble_r):
        for _ in range(random.randint(5, 9)):
            angle = random.uniform(0, math.pi * 2)
            spd   = random.uniform(40, 120)
            life  = random.uniform(0.6, 1.2)
            r0    = random.uniform(2, 6)
            r_max = r0 + random.uniform(bubble_r * 0.15, bubble_r * 0.35)
            self.blobs.append({
                'x':        x + random.uniform(-bubble_r * 0.3, bubble_r * 0.3),
                'y':        y + random.uniform(-bubble_r * 0.3, bubble_r * 0.3),
                'vx':       math.cos(angle) * spd,
                'vy':       math.sin(angle) * spd,
                'r0':       r0,
                'r_max':    r_max,
                'life':     life,
                'max_life': life,
                'color':    random.choice(_PAINT_COLORS),
            })

    def update(self, dt):
        for b in self.blobs:
            b['x']    += b['vx'] * dt
            b['y']    += b['vy'] * dt
            b['vx']   *= 0.92
            b['vy']   *= 0.92
            b['life'] -= dt
        self.blobs = [b for b in self.blobs if b['life'] > 0]

    def draw(self, surface):
        for b in self.blobs:
            t = b['life'] / b['max_life']
            r = int(b['r0'] + (b['r_max'] - b['r0']) * (1.0 - t))
            a = int(200 * t)
            if r > 0 and a > 0:
                pygame.draw.circle(surface, (*b['color'], a),
                                   (int(b['x']), int(b['y'])), r)


# ─── Дно аквариума ─────────────────────────────────────────────────

SAND_H_FRAC = 0.10   # высота полосы дна (доля от высоты экрана)


def _draw_shell_on(surf, x, base_y, size, color, dark, rng):
    """Ракушка-гребешок: веер рёбер + заливка."""
    fan_pts = []
    for i in range(21):
        angle = math.radians(i * 9)          # 0° → 180° (раскрытие вверх)
        fx = x + int(math.cos(angle) * size)
        fy = base_y - int(math.sin(angle) * size)
        fan_pts.append((fx, fy))
    fan_pts.append((x, base_y))
    pygame.draw.polygon(surf, (*color, 210), fan_pts)
    # Рёбра
    n_ribs = 7
    for i in range(n_ribs):
        a = math.radians(i * 180 // (n_ribs - 1))
        ex = x + int(math.cos(a) * size)
        ey = base_y - int(math.sin(a) * size)
        pygame.draw.line(surf, (*dark, 140), (x, base_y), (ex, ey), 1)
    # Контур
    pygame.draw.lines(surf, (*dark, 170), False, fan_pts[:-1], 2)
    # Блик
    light = tuple(min(255, c + 40) for c in color)
    pygame.draw.line(surf, (*light, 110),
                     (x - size // 5, base_y - size * 3 // 4),
                     (x + size // 5, base_y - size * 3 // 4), 2)


def create_seabed(W, H):
    """
    Рисует дно аквариума: песчаный градиент + рябь + крупные камни + ракушки.
    Возвращает статичный Surface (перерисовывается один раз).
    """
    sand_h = int(H * SAND_H_FRAC)
    surf   = pygame.Surface((W, H), pygame.SRCALPHA)
    y0     = H - sand_h

    # Песчаный градиент (жёлто-песочный как на картинке)
    top_col    = (210, 190, 130)
    bottom_col = (168, 145,  90)
    for dy in range(sand_h):
        t = dy / max(1, sand_h - 1)
        c = tuple(int(top_col[i] + (bottom_col[i] - top_col[i]) * t) for i in range(3))
        pygame.draw.line(surf, (*c, 240), (0, y0 + dy), (W, y0 + dy))

    # Плавная граница вода/песок
    for dy in range(10):
        a = int(200 * (dy / 10))
        pygame.draw.line(surf, (*top_col, a), (0, y0 + dy), (W, y0 + dy))

    rng = random.Random(7)

    # Рябь
    for _ in range(18):
        rx = rng.randint(0, W)
        ry = y0 + rng.randint(12, sand_h - 8)
        rw = rng.randint(60, 180)
        rh = rng.randint(4, 9)
        pygame.draw.arc(surf, (178, 158, 108, 70),
                        (rx - rw // 2, ry - rh, rw, rh * 2), 0, math.pi, 1)

    # Крупные камни (оранжево-коричневые, как на картинке)
    stone_colors = [
        (185, 125, 75), (170, 112, 62),
        (195, 138, 85), (160, 105, 58),
    ]
    for _ in range(18):
        px  = rng.randint(0, W)
        py  = y0 + rng.randint(8, sand_h - 8)
        prx = rng.randint(14, 34)
        pry = rng.randint(10, 22)
        col = rng.choice(stone_colors)
        drk = tuple(max(0, c - 30) for c in col)
        lgt = tuple(min(255, c + 30) for c in col)
        tmp = pygame.Surface((prx * 2 + 6, pry * 2 + 6), pygame.SRCALPHA)
        pygame.draw.ellipse(tmp, (*col, 225), (1, 1, prx * 2, pry * 2))
        pygame.draw.ellipse(tmp, (*drk, 100), (1, 1, prx * 2, pry * 2), 2)
        pygame.draw.ellipse(tmp, (*lgt, 70),
                            (prx // 2, pry // 3, prx, pry // 2))
        angle = rng.uniform(-25, 25)
        rot   = pygame.transform.rotate(tmp, angle)
        surf.blit(rot, (px - rot.get_width() // 2, py - rot.get_height() // 2))

    # Мелкий гравий
    for _ in range(45):
        px  = rng.randint(0, W)
        py  = y0 + rng.randint(5, sand_h - 4)
        pr  = rng.randint(3, 7)
        col = rng.choice(stone_colors)
        pygame.draw.circle(surf, (*col, 190), (px, py), pr)

    # Ракушки-гребешки
    shell_col  = (210, 192, 152)
    shell_dark = (165, 145, 108)
    shell_data = [
        (int(W * 0.22), y0 + 4, 28),
        (int(W * 0.58), y0 + 3, 22),
        (int(W * 0.85), y0 + 5, 26),
    ]
    for sx, sy, sz in shell_data:
        _draw_shell_on(surf, sx, sy, sz, shell_col, shell_dark, rng)

    return surf


# ─── Кораллы и водоросли ───────────────────────────────────────────

class SeabedDecor:
    """Водоросли, ветвистые, шаровые и веерные кораллы на дне аквариума."""

    def __init__(self, W, H):
        self.W      = W
        self.H      = H
        self.sand_y = H - int(H * SAND_H_FRAC)
        rng = random.Random(17)

        # ── Водоросли: 3 шт, 2 типа — пушистые (hornwort) и ленточные ──
        self.seaweeds = [
            {'x': int(W * 0.55), 'kind': 'feathery', 'color': (58, 178, 72),
             'phase': rng.uniform(0, math.pi * 2), 'height': rng.randint(170, 230)},
            {'x': int(W * 0.68), 'kind': 'ribbon',   'color': (38, 138, 105),
             'phase': rng.uniform(0, math.pi * 2), 'height': rng.randint(190, 255)},
            {'x': int(W * 0.82), 'kind': 'feathery', 'color': (48, 162, 62),
             'phase': rng.uniform(0, math.pi * 2), 'height': rng.randint(170, 225)},
        ]

        # ── 5 видов кораллов, разложены по экрану ──

        # 1. Ветвистый (красный) — крайний левый
        self.coral_branch = [
            {'x': int(W * 0.07) + rng.randint(-10, 10),
             'height': rng.randint(190, 260), 'color': (222, 58, 58),
             'seed': rng.randint(0, 99999)},
            {'x': int(W * 0.88) + rng.randint(-15, 15),
             'height': rng.randint(185, 250), 'color': (205, 80, 38),
             'seed': rng.randint(0, 99999)},
        ]

        # 2. Мозговой — чуть левее центра
        self.coral_brain = [
            {'x': int(W * 0.62) + rng.randint(-15, 15),
             'r': rng.randint(62, 88), 'color': (192, 165, 38)},
        ]

        # 3. Веерный (фиолетовый) — правее центра
        self.coral_fan = [
            {'x': int(W * 0.74) + rng.randint(-15, 15),
             'height': rng.randint(195, 260), 'color': (148, 55, 205),
             'seed': rng.randint(0, 99999)},
        ]

        # 4. Оленерогий (staghorn) — бежево-розовый
        self.coral_staghorn = [
            {'x': int(W * 0.85) + rng.randint(-15, 15),
             'height': rng.randint(160, 215), 'color': (225, 155, 120),
             'seed': rng.randint(0, 99999)},
        ]

        # 5. Трубчатый (tube) — жёлто-зелёный
        self.coral_tube = [
            {'x': int(W * 0.53) + rng.randint(-15, 15),
             'height': rng.randint(130, 185), 'color': (88, 185, 148),
             'seed': rng.randint(0, 99999)},
        ]

    def draw(self, surface, t):
        sy = self.sand_y
        for c in self.coral_branch:
            self._draw_branch(surface, c['x'], sy, c['height'], c['color'], c['seed'])
        for c in self.coral_brain:
            self._draw_brain(surface, c['x'], sy, c['r'], c['color'])
        for c in self.coral_fan:
            self._draw_fan(surface, c['x'], sy, c['height'], c['color'], c['seed'])
        for c in self.coral_staghorn:
            self._draw_staghorn(surface, c['x'], sy, c['height'], c['color'], c['seed'])
        for c in self.coral_tube:
            self._draw_tube(surface, c['x'], sy, c['height'], c['color'], c['seed'])
        for sw in self.seaweeds:
            if sw['kind'] == 'feathery':
                self._draw_feathery(surface, sw['x'], sy,
                                    sw['height'], sw['color'], sw['phase'], t)
            else:
                self._draw_ribbon(surface, sw['x'], sy,
                                  sw['height'], sw['color'], sw['phase'], t)

    # ── Пушистая водоросль (hornwort) ──
    def _draw_feathery(self, surface, x, base_y, height, color, phase, t):
        """Вертикальный стебель с мелкими ветками по бокам — как хорнворт."""
        n   = 20
        pts = []
        for i in range(n):
            p  = i / (n - 1)
            sy = base_y - int(height * p)
            sx = x + int(math.sin(t * 1.0 + phase + p * 2.4) * p * 14)
            pts.append((sx, sy))
        # Стебель
        for i in range(len(pts) - 1):
            w = max(1, int(3 - (i / n) * 2))
            pygame.draw.line(surface, (*color, 210), pts[i], pts[i + 1], w)
        # Мелкие ветки
        light = tuple(min(255, c + 40) for c in color)
        for i in range(1, len(pts) - 1):
            lx, ly = pts[i]
            dx = pts[i][0] - pts[i - 1][0]
            dy = pts[i][1] - pts[i - 1][1]
            norm = math.hypot(dx, dy) or 1
            px_n, py_n = -dy / norm, dx / norm
            blen = max(6, int(16 - (i / n) * 8))
            for side in (-1, 1):
                for sub in range(2):
                    angle_off = side * (0.7 + sub * 0.5)
                    base_a = math.atan2(py_n, px_n)
                    bx = lx + int(math.cos(base_a + angle_off) * blen)
                    by = ly + int(math.sin(base_a + angle_off) * blen)
                    pygame.draw.line(surface, (*light, 175), (lx, ly), (bx, by), 1)

    # ── Ленточная водоросль ──
    def _draw_ribbon(self, surface, x, base_y, height, color, phase, t):
        """Широкие извивающиеся ленты — как на образце."""
        light = tuple(min(255, c + 35) for c in color)
        for ribbon_i, (x_off, amp, freq_off) in enumerate([(-10, 1.0, 0.0),
                                                             (  0, 1.2, 0.7),
                                                             ( 10, 0.9, 1.4)]):
            n   = 22
            pts = []
            for i in range(n):
                p  = i / (n - 1)
                sy = base_y - int(height * p)
                sx = x + x_off + int(math.sin(t * 0.85 + phase + freq_off + p * 3.0) * p * 24 * amp)
                pts.append((sx, sy))
            if len(pts) >= 2:
                w = 5 - ribbon_i
                pygame.draw.lines(surface, (*color, 195), False, pts, max(2, w))
        # Верхушки — маленькие листики
        n   = 10
        pts = []
        for i in range(n):
            p  = i / (n - 1)
            sy = base_y - int(height * p)
            sx = x + int(math.sin(t * 0.85 + phase + p * 3.0) * p * 24)
            pts.append((sx, sy))
        for i in range(2, len(pts) - 1, 2):
            lx, ly = pts[i]
            pygame.draw.circle(surface, (*light, 160), (lx, ly), 5)

    # ── 1. Ветвистый коралл ──
    def _draw_branch(self, surface, x, base_y, height, color, seed):
        rng   = random.Random(seed)
        dark  = tuple(max(0, c - 35) for c in color)

        def _branch(sx, sy, angle, length, depth):
            if depth == 0 or length < 6:
                pygame.draw.circle(surface, (*color, 220), (int(sx), int(sy)), max(3, depth + 2))
                return
            ex = sx + math.cos(angle) * length
            ey = sy - abs(math.sin(angle)) * length
            w  = max(1, depth // 2 + 2)
            pygame.draw.line(surface, (*color, 232), (int(sx), int(sy)), (int(ex), int(ey)), w)
            spread = rng.uniform(0.28, 0.48)
            factor = rng.uniform(0.58, 0.72)
            _branch(ex, ey, angle - spread, length * factor, depth - 1)
            _branch(ex, ey, angle + spread, length * factor, depth - 1)
            # Изредка тройное ветвление
            if depth > 3 and rng.random() < 0.35:
                _branch(ex, ey, angle, length * factor * 0.8, depth - 2)

        trunk_h = int(height * 0.20)
        for tw in range(7, 0, -2):
            pygame.draw.line(surface, (*dark, 200),
                             (x, base_y), (x, base_y - trunk_h), tw)
        _branch(x, base_y - trunk_h, math.pi / 2, height * 0.44, 7)

    # ── 2. Мозговой коралл (brain coral) ──
    def _draw_brain(self, surface, x, base_y, r, color):
        dark  = tuple(max(0, c - 50) for c in color)
        light = tuple(min(255, c + 55) for c in color)
        cy    = base_y - int(r * 0.58)
        # Тело
        pygame.draw.circle(surface, (*color, 228), (x, cy), r)
        # Лабиринтные борозды — горизонтальные волнистые линии
        for dy in range(-r + 10, r - 10, 14):
            dist = abs(dy) / r
            chord = int(r * math.sqrt(max(0, 1 - dist * dist))) - 4
            if chord < 8:
                continue
            pts = []
            for xi in range(x - chord, x + chord + 1, 5):
                wy = cy + dy + int(5 * math.sin((xi - x) * 0.35))
                pts.append((xi, wy))
            if len(pts) >= 2:
                pygame.draw.lines(surface, (*dark, 115), False, pts, 2)
        # Вертикальные борозды
        for dx in range(-r + 10, r - 10, 18):
            dist = abs(dx) / r
            chord = int(r * math.sqrt(max(0, 1 - dist * dist))) - 4
            if chord < 8:
                continue
            pts = []
            for yi in range(cy - chord, cy + chord + 1, 5):
                wx = x + dx + int(4 * math.sin((yi - cy) * 0.38))
                pts.append((wx, yi))
            if len(pts) >= 2:
                pygame.draw.lines(surface, (*dark, 80), False, pts, 1)
        # Контур и блик
        pygame.draw.circle(surface, (*dark, 90), (x, cy), r, 2)
        pygame.draw.circle(surface, (*light, 70), (x - r // 3, cy - r // 3), r // 4)

    # ── 3. Веерный коралл ──
    def _draw_fan(self, surface, x, base_y, height, color, seed):
        rng   = random.Random(seed)
        light = tuple(min(255, c + 55) for c in color)
        dark  = tuple(max(0, c - 30) for c in color)
        n     = 18
        trunk_h = int(height * 0.16)
        pygame.draw.line(surface, (*dark, 230), (x, base_y), (x, base_y - trunk_h), 5)
        # Первичные ветви
        base_pts = []
        for i in range(n):
            frac   = i / (n - 1)
            angle  = math.radians(-70 + frac * 140) + math.pi / 2
            br_len = height * rng.uniform(0.78, 1.02)
            bx = x + math.cos(angle) * br_len
            by = base_y - trunk_h - abs(math.sin(angle)) * br_len
            pygame.draw.line(surface, (*color, 215),
                             (x, base_y - trunk_h), (int(bx), int(by)), 2)
            base_pts.append((bx, by))
        # Сетка перемычек
        for level_frac in [0.25, 0.42, 0.58, 0.72, 0.86]:
            grid = []
            for i in range(n):
                frac  = i / (n - 1)
                angle = math.radians(-70 + frac * 140) + math.pi / 2
                gx = x + math.cos(angle) * height * level_frac
                gy = base_y - trunk_h - abs(math.sin(angle)) * height * level_frac
                grid.append((int(gx), int(gy)))
            if len(grid) >= 2:
                pygame.draw.lines(surface, (*light, 140), False, grid, 1)
        # Вторичная сетка (смещённая)
        for level_frac in [0.33, 0.50, 0.65, 0.79]:
            grid = []
            for i in range(n):
                frac  = i / (n - 1)
                angle = math.radians(-70 + frac * 140) + math.pi / 2
                gx = x + math.cos(angle) * height * level_frac
                gy = base_y - trunk_h - abs(math.sin(angle)) * height * level_frac
                grid.append((int(gx), int(gy)))
            if len(grid) >= 2:
                pygame.draw.lines(surface, (*color, 100), False, grid, 1)

    # ── 4. Оленерогий коралл (staghorn) ──
    def _draw_staghorn(self, surface, x, base_y, height, color, seed):
        rng  = random.Random(seed)
        dark = tuple(max(0, c - 40) for c in color)
        tip  = tuple(min(255, c + 30) for c in color)

        def _arm(sx, sy, angle, length, depth):
            if depth == 0 or length < 8:
                pygame.draw.circle(surface, (*tip, 220), (int(sx), int(sy)), max(3, int(length // 3) + 2))
                return
            ex = sx + math.cos(angle) * length
            ey = sy - abs(math.sin(angle)) * length
            pygame.draw.line(surface, (*color, 225),
                             (int(sx), int(sy)), (int(ex), int(ey)),
                             max(2, depth + 1))
            # Отводы сбоку (не рекурсивные, короткие)
            n_sprigs = rng.randint(2, 4)
            for j in range(n_sprigs):
                spr_frac = (j + 1) / (n_sprigs + 1)
                sp_x = sx + math.cos(angle) * length * spr_frac
                sp_y = sy - abs(math.sin(angle)) * length * spr_frac
                side  = rng.choice([-1, 1])
                sp_a  = angle + side * rng.uniform(0.5, 1.0)
                sp_l  = length * rng.uniform(0.28, 0.45)
                sp_ex = sp_x + math.cos(sp_a) * sp_l
                sp_ey = sp_y - abs(math.sin(sp_a)) * sp_l
                pygame.draw.line(surface, (*color, 215),
                                 (int(sp_x), int(sp_y)), (int(sp_ex), int(sp_ey)), 2)
                pygame.draw.circle(surface, (*tip, 215), (int(sp_ex), int(sp_ey)), 3)
            spread = rng.uniform(0.32, 0.55)
            factor = rng.uniform(0.55, 0.70)
            _arm(ex, ey, angle - spread, length * factor, depth - 1)
            _arm(ex, ey, angle + spread, length * factor, depth - 1)

        trunk_h = int(height * 0.18)
        pygame.draw.line(surface, (*dark, 220), (x, base_y), (x, base_y - trunk_h), 6)
        _arm(x, base_y - trunk_h, math.pi / 2, height * 0.40, 4)

    # ── 5. Трубчатый коралл ──
    def _draw_tube(self, surface, x, base_y, height, color, seed):
        rng   = random.Random(seed)
        dark  = tuple(max(0, c - 45) for c in color)
        light = tuple(min(255, c + 50) for c in color)
        inner = tuple(max(0, c - 70) for c in color)
        n_tubes = rng.randint(8, 13)
        for i in range(n_tubes):
            tx = x + rng.randint(-int(height * 0.38), int(height * 0.38))
            th = int(height * rng.uniform(0.55, 1.0))
            tr = rng.randint(7, 16)
            # Тело трубки
            pygame.draw.rect(surface, (*color, 220),
                             (tx - tr, base_y - th, tr * 2, th),
                             border_radius=tr)
            # Тёмная боковая линия (объём)
            pygame.draw.line(surface, (*dark, 130),
                             (tx + tr - 3, base_y),
                             (tx + tr - 3, base_y - th), 2)
            # Блик слева
            pygame.draw.line(surface, (*light, 90),
                             (tx - tr + 3, base_y),
                             (tx - tr + 3, base_y - th), 2)
            # Устье трубки (эллипс сверху)
            pygame.draw.ellipse(surface, (*inner, 210),
                                (tx - tr, base_y - th - tr // 2, tr * 2, tr))
            pygame.draw.ellipse(surface, (*dark, 160),
                                (tx - tr, base_y - th - tr // 2, tr * 2, tr), 2)



# ─── Двустворчатый моллюск ─────────────────────────────────────────

_CS_IDLE_CLOSED   = 'idle_closed'
_CS_OPENING       = 'opening'
_CS_IDLE_OPEN     = 'idle_open'
_CS_CLOSING       = 'closing'
_CS_HIDING        = 'hiding'
_CS_HAPPY_OPENING = 'happy_opening'
_CS_HAPPY         = 'happy'
_CS_HAPPY_CLOSING = 'happy_closing'


class Clam:
    # Геометрия
    RX            = 300   # горизонтальный радиус
    BOT_H         = 85    # высота нижней створки (вниз от шва)
    TOP_H         = 210   # высота верхней створки (вверх при закрытой)
    MAX_ANGLE_DEG = 75    # максимальный угол открытия шарнира (градусы)
    HOVER_R       = 320

    OPEN_IDLE          = 0.42   # idle: ~31 градус → gap ~108px
    OPEN_HAPPY         = 1.0    # happy: 75 градусов → gap ~203px
    SPEED_IDLE_OPEN    = 0.38
    SPEED_IDLE_CLOSE   = 0.52
    SPEED_HAPPY_OPEN   = 2.20
    SPEED_HAPPY_CLOSE  = 1.30
    SPEED_HIDING_CLOSE = 2.80
    _N = 60

    def __init__(self, cx, sand_y, seed=0):
        self.cx     = cx
        self.sand_y = sand_y
        self.open   = 0.0
        self._sound = None
        rng = random.Random(seed)
        self.state       = _CS_IDLE_CLOSED
        self.idle_timer  = rng.uniform(3.0, 6.0)
        self.hold_timer  = 0.0
        self.happy_timer = 0.0
        self.wave_phase  = 0.0
        self.wave_angle  = 0.0

    def _approach(self, target, speed, dt):
        diff = target - self.open
        step = speed * dt
        self.open = target if abs(diff) <= step else self.open + math.copysign(step, diff)

    def update(self, dt, mx, my, events):
        seam_y = self.sand_y - self.BOT_H
        near = math.hypot(mx - self.cx, my - seam_y) < self.HOVER_R
        clicked = any(
            e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and
            math.hypot(e.pos[0] - self.cx, e.pos[1] - seam_y) < self.HOVER_R
            for e in events
        )
        if clicked and self.state not in (_CS_HAPPY_OPENING, _CS_HAPPY, _CS_HAPPY_CLOSING):
            self.state      = _CS_HAPPY_OPENING
            self.wave_phase = 0.0
            if self._sound:
                self._sound.play()
        elif self.state == _CS_IDLE_CLOSED:
            if near:
                self.state = _CS_HIDING
            else:
                self.idle_timer -= dt
                if self.idle_timer <= 0:
                    self.state = _CS_OPENING
        elif self.state == _CS_OPENING:
            if near:
                self.state = _CS_HIDING
            else:
                self._approach(self.OPEN_IDLE, self.SPEED_IDLE_OPEN, dt)
                if abs(self.open - self.OPEN_IDLE) < 0.008:
                    self.open       = self.OPEN_IDLE
                    self.state      = _CS_IDLE_OPEN
                    self.hold_timer = random.uniform(1.5, 3.0)
        elif self.state == _CS_IDLE_OPEN:
            if near:
                self.state = _CS_HIDING
            else:
                self.hold_timer -= dt
                if self.hold_timer <= 0:
                    self.state = _CS_CLOSING
        elif self.state == _CS_CLOSING:
            if near:
                self.state = _CS_HIDING
            else:
                self._approach(0.0, self.SPEED_IDLE_CLOSE, dt)
                if self.open < 0.008:
                    self.open       = 0.0
                    self.state      = _CS_IDLE_CLOSED
                    self.idle_timer = random.uniform(4.0, 7.0)
        elif self.state == _CS_HIDING:
            self._approach(0.0, self.SPEED_HIDING_CLOSE, dt)
            if not near:
                self.state      = _CS_IDLE_CLOSED
                self.idle_timer = random.uniform(2.0, 4.5)
        elif self.state == _CS_HAPPY_OPENING:
            self._approach(self.OPEN_HAPPY, self.SPEED_HAPPY_OPEN, dt)
            if abs(self.open - self.OPEN_HAPPY) < 0.008:
                self.open        = self.OPEN_HAPPY
                self.state       = _CS_HAPPY
                self.happy_timer = random.uniform(2.5, 3.5)
        elif self.state == _CS_HAPPY:
            self.happy_timer -= dt
            self.wave_phase  += dt * 5.0
            self.wave_angle   = math.degrees(math.sin(self.wave_phase) * 0.80)
            if self.happy_timer <= 0:
                self.state = _CS_HAPPY_CLOSING
        elif self.state == _CS_HAPPY_CLOSING:
            self._approach(0.0, self.SPEED_HAPPY_CLOSE, dt)
            if self.open < 0.008:
                self.open       = 0.0
                self.state      = _CS_IDLE_CLOSED
                self.idle_timer = random.uniform(4.0, 7.0)

    def draw(self, surface):
        cx    = self.cx
        seam_y = self.sand_y - self.BOT_H
        N      = self._N

        # ── Шарнирная механика ──────────────────────────────────────
        # Верхняя створка вращается вокруг заднего шарнира.
        # В проекции спереди:
        #   gap    = TOP_H * sin(angle)  — насколько поднялась передняя кромка
        #   app_ry = TOP_H * cos(angle)  — видимая высота купола (перспективное сжатие)
        angle_rad = math.radians(self.open * self.MAX_ANGLE_DEG)
        gap    = int(self.TOP_H * math.sin(angle_rad))
        app_ry = max(4, int(self.TOP_H * math.cos(angle_rad)))
        top_pivot = seam_y - gap   # где видна нижняя кромка верхней створки

        # 1. Тёмная полость (за розовым телом)
        if gap > 6:
            cpts = []
            crx  = self.RX - 8
            for i in range(N + 1):
                a = math.pi * i / N
                cpts.append((int(cx + crx * math.cos(a)),
                             int(seam_y - gap * math.sin(a))))
            pygame.draw.polygon(surface, (28, 12, 18, 238), cpts)

        # 2. Розовый моллюск (тело между створками)
        if gap > 16:
            brx = max(1, int(self.RX * 0.72))
            bry = max(1, int(gap * 0.70))
            bcy = seam_y - gap // 2
            pygame.draw.ellipse(surface, (210, 80, 76, 245),
                                pygame.Rect(cx - brx, bcy - bry, brx * 2, bry * 2))
            hlrx = max(1, int(brx * 0.50))
            hlry = max(1, int(bry * 0.34))
            pygame.draw.ellipse(surface, (248, 146, 130, 115),
                                pygame.Rect(cx - hlrx, bcy - bry + 10, hlrx * 2, hlry * 2))

        # 3. Нижняя створка — статична, купол вниз
        self._draw_shell_half(surface, cx, seam_y, self.RX, self.BOT_H, +1, N)

        # 4. Верхняя створка — шарнирно поднята, перспективно сжата
        self._draw_shell_half(surface, cx, top_pivot, self.RX, app_ry, -1, N)

        # 5. Глаза + улыбка — при любом открытии (idle и happy)
        if gap > 28:
            self._draw_face(surface, cx, seam_y, gap)

        # 6. Машущая лапка — только в happy
        if self.state == _CS_HAPPY and self.open > 0.40:
            self._draw_arm(surface, cx, seam_y, gap)

    def _draw_shell_half(self, surface, cx, pivot_y, rx, ry, sign, N):
        """sign=+1: купол вниз (нижняя), sign=-1: купол вверх (верхняя)."""
        col_o = (210, 180, 122)
        col_i = (240, 210, 162)
        dark  = (148, 108, 52)
        lite  = (252, 226, 166)
        irx, iry = rx - 16, max(4, ry - 16)
        pi_over_N = math.pi / N
        pts  = []
        ipts = []
        for i in range(N + 1):
            a   = pi_over_N * i
            ca  = math.cos(a)
            sa  = math.sin(a)
            sy  = sign * sa
            pts.append((int(cx + rx * ca),
                        int(pivot_y + ry * sy)))
            ipts.append((int(cx + irx * ca),
                         int(pivot_y + iry * sy)))
        pygame.draw.polygon(surface, (*col_o, 250), pts)
        pygame.draw.polygon(surface, (*col_i, 215), ipts)
        rx96 = rx * 0.96
        ry96 = ry * 0.96
        for i in range(13):
            a = math.pi * i / 12
            pygame.draw.line(surface, (*dark, 78),
                             (cx, pivot_y),
                             (int(cx + rx96 * math.cos(a)),
                              int(pivot_y + sign * ry96 * math.sin(a))), 2)
        pygame.draw.polygon(surface, (*dark, 195), pts, 3)
        if ry > 16:
            rx68 = rx * 0.68
            ry68 = ry * 0.68
            blik = []
            for i in range(14):
                a = math.pi * (0.11 + 0.78 * i / 13)
                blik.append((int(cx + rx68 * math.cos(a)),
                             int(pivot_y + sign * ry68 * math.sin(a))))
            if len(blik) >= 2:
                pygame.draw.lines(surface, (*lite, 100), False, blik, 5)

    def _draw_face(self, surface, cx, seam_y, gap):
        face_y = seam_y - gap // 2
        eye_r  = min(max(10, int(self.RX * 0.058)), max(1, gap // 2 - 2))
        eye_dx = int(self.RX * 0.20)
        for side in (-1, 1):
            ex, ey = cx + side * eye_dx, face_y - eye_r // 3
            pygame.draw.circle(surface, (255, 248, 230, 250), (ex, ey), eye_r)
            pygame.draw.circle(surface, (35, 18, 10, 250), (ex, ey), int(eye_r * 0.62))
            pygame.draw.circle(surface, (255, 255, 255, 235),
                               (ex + int(eye_r * 0.30), ey - int(eye_r * 0.32)),
                               max(2, int(eye_r * 0.28)))
        # Улыбка — только в happy
        if self.state in (_CS_HAPPY, _CS_HAPPY_OPENING, _CS_HAPPY_CLOSING):
            sw = max(1, int(self.RX * 0.30))
            sh = max(1, int(sw * 0.48))
            pygame.draw.arc(surface, (185, 52, 52, 240),
                            pygame.Rect(cx - sw // 2, face_y + 4, sw, sh),
                            math.pi, math.pi * 2, max(3, int(self.RX * 0.013)))

    def _draw_arm(self, surface, cx, seam_y, gap):
        bx      = cx + self.RX - 8
        by      = seam_y - gap // 3
        arm_len = max(1, int(self.RX * 0.23))
        flen    = max(1, int(arm_len * 0.55))
        dir_rad = math.radians(-66 + self.wave_angle)
        tip_x   = bx + int(math.cos(dir_rad) * arm_len)
        tip_y   = by + int(math.sin(dir_rad) * arm_len)
        aw = max(5, int(self.RX * 0.026))
        kr = max(7, int(self.RX * 0.042))
        fw = max(3, int(self.RX * 0.018))
        fr = max(4, int(self.RX * 0.026))
        col = (215, 162, 98, 238)
        pygame.draw.line(surface, col, (bx, by), (tip_x, tip_y), aw)
        pygame.draw.circle(surface, col, (tip_x, tip_y), kr)
        for i in range(3):
            fa  = dir_rad + math.radians(-26 + i * 26)
            fx2 = tip_x + int(math.cos(fa) * flen)
            fy2 = tip_y + int(math.sin(fa) * flen)
            pygame.draw.line(surface, col, (tip_x, tip_y), (fx2, fy2), fw)
            pygame.draw.circle(surface, col, (fx2, fy2), fr)



# ─── Звуки ─────────────────────────────────────────────────────────

def _make_pop_sound():
    """Мягкое тихое лопание водяного пузыря — лёгкий «чмок»."""
    try:
        sr  = 44100
        n   = int(sr * 0.10)
        buf = array.array('h')
        for i in range(n):
            t    = i / sr
            env  = math.exp(-t * 60)
            # мягкий низкий удар
            tone = math.sin(2 * math.pi * 130 * t) * 0.35
            # быстро затухающий средний тон
            mid  = math.sin(2 * math.pi * 380 * math.exp(-t * 25) * t) * 0.25
            # чуть шума воды
            noise = random.uniform(-1.0, 1.0) * 0.12
            val  = (tone + mid + noise) * env
            s    = int(32767 * 0.28 * val)
            buf.append(s)
            buf.append(s)
        return pygame.mixer.Sound(buffer=buf)
    except Exception:
        return None


def _make_music_wav():
    """
    Генерирует ~6-секундный WAV-цикл: мягкий пентатонический дрон
    с плавной мелодией — лёгкая фоновая музыкальная шкатулка.
    Возвращает BytesIO, пригодный для pygame.mixer.music.load().
    """
    sr       = 44100
    duration = 6.0
    n        = int(sr * duration)

    # Мелодия: ноты C4→E4→G4→A4→G4→E4 (по 1 секунде каждая)
    melody = [261.63, 329.63, 392.00, 440.00, 392.00, 329.63]
    nd     = duration / len(melody)

    buf = array.array('h')
    for i in range(n):
        t = i / sr

        # Дрон: C3-G3-C4 (очень тихо)
        val = (0.022 * math.sin(2 * math.pi * 130.81 * t) +
               0.018 * math.sin(2 * math.pi * 196.00 * t) +
               0.014 * math.sin(2 * math.pi * 261.63 * t) +
               0.010 * math.sin(2 * math.pi * 392.00 * t))

        # Медленное покачивание (тремоло ~0.25 Гц)
        val *= 0.85 + 0.15 * math.sin(2 * math.pi * 0.25 * t)

        # Мелодия
        mi  = min(int(t / nd), len(melody) - 1)
        mt  = t - mi * nd
        mf  = melody[mi]
        env = min(mt / 0.08, 1.0) * math.exp(-mt * 2.2)
        val += 0.065 * env * math.sin(2 * math.pi * mf * t)
        val += 0.020 * env * math.sin(4 * math.pi * mf * t)   # октава

        # Плавное начало/конец для бесшовного цикла
        fade = min(1.0, t / 0.4) * min(1.0, (n - i - 1) / (sr * 0.4))
        val *= fade

        s = max(-32767, min(32767, int(32767 * val)))
        buf.append(s)
        buf.append(s)

    wav_io = io.BytesIO()
    with wave.open(wav_io, 'wb') as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(buf.tobytes())
    wav_io.seek(0)
    return wav_io


def _make_clam_sound():
    """Мягкий щелчок раковины при открытии по клику."""
    try:
        sr  = 44100
        n   = int(sr * 0.09)
        buf = array.array('h')
        for i in range(n):
            t   = i / sr
            env = math.exp(-t * 75)
            val = (math.sin(2 * math.pi * 180 * t) * 0.38 +
                   math.sin(2 * math.pi * 420 * t) * 0.18 +
                   random.uniform(-0.06, 0.06)) * env
            s   = int(32767 * 0.32 * val)
            buf.append(s)
            buf.append(s)
        return pygame.mixer.Sound(buffer=buf)
    except Exception:
        return None


# ─── Главное приложение ────────────────────────────────────────────

def hue_to_rgb(hue):
    r, g, b = colorsys.hsv_to_rgb(hue % 1.0, 1.0, 1.0)
    return (int(r * 255), int(g * 255), int(b * 255))


def main():
    global ctrl_enter_pressed

    disable_accessibility_shortcuts()
    start_hook()  # блокируется до готовности хука (threading.Event)

    pygame.mixer.pre_init(44100, -16, 2, 512)
    pygame.init()
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN | pygame.NOFRAME)
    pygame.display.set_caption("Baby Keyboard")
    W, H = screen.get_size()

    hwnd = pygame.display.get_wm_info()["window"]
    user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)

    # ── Звуки и фоновая музыка ──
    pop_sound  = _make_pop_sound()
    clam_sound = _make_clam_sound()
    try:
        pygame.mixer.music.load(_make_music_wav())
        pygame.mixer.music.set_volume(0.18)
        pygame.mixer.music.play(-1)
    except Exception as e:
        print(f"WARN: музыка недоступна ({e})", file=sys.stderr)

    clock = pygame.time.Clock()
    font  = pygame.font.SysFont("Arial", 96, bold=True)

    background = create_background(W, H)
    seabed     = create_seabed(W, H)
    decor      = SeabedDecor(W, H)
    sand_y       = H - int(H * SAND_H_FRAC)
    clams        = [Clam(max(Clam.RX + 20, int(W * 0.24)), sand_y)]
    clams[0]._sound = clam_sound

    for r in range(Bubble.RADIUS_MIN, Bubble.RADIUS_MAX + 1, 4):
        get_bubble_surf(r)

    dyn_surf   = pygame.Surface((W, H), pygame.SRCALPHA)
    trail_surf = pygame.Surface((W, H), pygame.SRCALPHA)

    trail          = deque()
    TRAIL_LIFETIME = 1.5
    trail_hue      = 0.0

    bubbles = [Bubble(W, H, start_offscreen=False) for _ in range(Bubble.TARGET_COUNT)]
    for b in bubbles:
        b.y = random.uniform(b.radius + 10, H - b.radius - 10)

    fizz   = FizzSystem(W, H)
    fishes = FishSystem()
    paint  = PaintSystem()

    chars       = []
    cursor_x    = 20
    cursor_y    = 20
    line_height = 115
    g_held      = False  # отслеживаем, зажата ли клавиша G
    running     = True

    while running:
        now      = time.time()
        dt       = min(clock.get_time() / 1000.0, 0.05)
        mx, my   = pygame.mouse.get_pos()

        # ─── События ───
        raw_events = pygame.event.get()
        for event in raw_events:
            if event.type == pygame.QUIT:
                pass
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_g:
                    g_held = True
                mods = pygame.key.get_mods()
                if (mods & pygame.KMOD_CTRL) and event.key == pygame.K_RETURN:
                    if g_held:
                        running = False
                        break
                if event.unicode and event.unicode.isprintable():
                    surf = font.render(event.unicode, True, (35, 45, 80))
                    if cursor_x + surf.get_width() > W - 20:
                        cursor_x  = 20
                        cursor_y += line_height
                    if cursor_y + line_height > H:
                        chars.clear()
                        cursor_x = 20
                        cursor_y = 20
                    chars.append((surf, cursor_x, cursor_y))
                    cursor_x += surf.get_width() + 5
            elif event.type == pygame.KEYUP:
                if event.key == pygame.K_g:
                    g_held = False
            elif event.type == pygame.MOUSEMOTION:
                trail_hue += 0.002
                trail.append((event.pos[0], event.pos[1], hue_to_rgb(trail_hue), now))
            elif event.type == pygame.ACTIVEEVENT:
                # Если окно потеряло фокус — вернуть на передний план
                if hasattr(event, 'gain') and not event.gain:
                    user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                                        SWP_NOMOVE | SWP_NOSIZE)
                    user32.SetForegroundWindow(hwnd)

        if ctrl_enter_pressed:
            running = False

        # ─── Обновление ───
        popping_before = {id(b) for b in bubbles if b.popping}

        for b in bubbles:
            b.update(dt, mx, my)

        # Реакция на новые лопания: мальки вырываются наружу + звук
        for b in bubbles:
            if b.popping and id(b) not in popping_before:
                if b.has_fish:
                    fishes.spawn_from_bubble(b.x, b.y, b.radius, b.inner_fish)
                else:
                    paint.spawn(b.x, b.y, b.radius)
                if pop_sound:
                    pop_sound.play()

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
        fishes.update(dt)
        paint.update(dt)
        for clam in clams:
            clam.update(dt, mx, my, raw_events)

        cutoff = now - TRAIL_LIFETIME
        while trail and trail[0][3] < cutoff:
            trail.popleft()

        # ─── Отрисовка ───

        screen.blit(background, (0, 0))
        screen.blit(seabed,     (0, 0))

        dyn_surf.fill((0, 0, 0, 0))
        decor.draw(dyn_surf, now)   # кораллы и водоросли (за пузырями)
        for clam in clams:
            clam.draw(dyn_surf)     # моллюски на дне
        fishes.draw(dyn_surf)       # уплывающие рыбки
        paint.draw(dyn_surf)        # брызги краски
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

    restore_accessibility_shortcuts()
    stop_hook()
    pygame.quit()


if __name__ == "__main__":
    main()
