"""
Baby Keyboard — безопасная песочница для малыша.
Полноэкранное приложение: нажатия клавиш показывают символы,
движение мыши оставляет радужный шлейф.
Закрытие только по Ctrl+Enter.
"""

import ctypes
import ctypes.wintypes as wintypes
import threading
import time
import random
import colorsys
import sys

import pygame

# ─── Win32 константы ───────────────────────────────────────────────

WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_SYSKEYDOWN = 0x0104

VK_LWIN = 0x5B
VK_RWIN = 0x5C
VK_TAB = 0x09
VK_ESCAPE = 0x1B
VK_F4 = 0x73
VK_DELETE = 0x2E
VK_RETURN = 0x0D
VK_D = 0x44

LLKHF_ALTDOWN = 0x20

HWND_TOPMOST = -1
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# Настраиваем типы Win32 функций
user32.SetWindowsHookExW.argtypes = [
    ctypes.c_int,
    ctypes.c_void_p,
    wintypes.HINSTANCE,
    wintypes.DWORD,
]
user32.SetWindowsHookExW.restype = ctypes.c_void_p

user32.CallNextHookEx.argtypes = [
    ctypes.c_void_p,
    ctypes.c_int,
    wintypes.WPARAM,
    wintypes.LPARAM,
]
user32.CallNextHookEx.restype = ctypes.c_long

user32.UnhookWindowsHookEx.argtypes = [ctypes.c_void_p]
user32.UnhookWindowsHookEx.restype = wintypes.BOOL

user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
user32.GetAsyncKeyState.restype = ctypes.c_short

kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32.GetModuleHandleW.restype = wintypes.HMODULE

# Тип callback для хука
HOOKPROC = ctypes.CFUNCTYPE(
    ctypes.c_long,
    ctypes.c_int,
    wintypes.WPARAM,
    wintypes.LPARAM,
)


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


# ─── Глобальное состояние ──────────────────────────────────────────

hook_id = None
ctrl_enter_pressed = False


def _kb_hook_proc(nCode, wParam, lParam):
    """Low-level keyboard hook: блокирует системные комбинации."""
    global ctrl_enter_pressed

    if nCode >= 0 and wParam in (WM_KEYDOWN, WM_SYSKEYDOWN):
        kb = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
        vk = kb.vkCode
        alt_down = bool(kb.flags & LLKHF_ALTDOWN)
        ctrl_down = bool(user32.GetAsyncKeyState(0xA2) & 0x8000) or bool(
            user32.GetAsyncKeyState(0xA3) & 0x8000
        )

        # Ctrl+Enter — пропускаем (для закрытия)
        if ctrl_down and vk == VK_RETURN:
            ctrl_enter_pressed = True
            return user32.CallNextHookEx(hook_id, nCode, wParam, lParam)

        # Блокируем Win
        if vk in (VK_LWIN, VK_RWIN):
            return 1

        # Блокируем Alt+Tab, Alt+F4, Alt+Esc
        if alt_down and vk in (VK_TAB, VK_F4, VK_ESCAPE):
            return 1

        # Блокируем Ctrl+Esc (меню Пуск)
        if ctrl_down and vk == VK_ESCAPE:
            return 1

        # Блокируем Win+D (показать рабочий стол) — Win уже заблокирован,
        # но на всякий случай
        if ctrl_down and alt_down and vk == VK_DELETE:
            return 1

    return user32.CallNextHookEx(hook_id, nCode, wParam, lParam)


# Prevent garbage collection of the callback
_hook_callback = HOOKPROC(_kb_hook_proc)


def _hook_thread():
    """Поток для установки хука и прокачки сообщений Windows."""
    global hook_id
    hook_id = user32.SetWindowsHookExW(
        WH_KEYBOARD_LL, _hook_callback, kernel32.GetModuleHandleW(None), 0
    )
    if not hook_id:
        err = ctypes.GetLastError()
        print(f"WARN: не удалось установить хук клавиатуры (err={err})", file=sys.stderr)
        return

    msg = wintypes.MSG()
    while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
        user32.TranslateMessage(ctypes.byref(msg))
        user32.DispatchMessageW(ctypes.byref(msg))


def start_hook():
    t = threading.Thread(target=_hook_thread, daemon=True)
    t.start()
    return t


def stop_hook():
    global hook_id
    if hook_id:
        user32.UnhookWindowsHookEx(hook_id)
        hook_id = None


# ─── Утилиты ───────────────────────────────────────────────────────


def random_bright_color():
    """Случайный яркий насыщенный цвет."""
    h = random.random()
    r, g, b = colorsys.hsv_to_rgb(h, 0.9, 1.0)
    return (int(r * 255), int(g * 255), int(b * 255))


def hue_to_rgb(hue):
    r, g, b = colorsys.hsv_to_rgb(hue % 1.0, 1.0, 1.0)
    return (int(r * 255), int(g * 255), int(b * 255))


# ─── Главное приложение ────────────────────────────────────────────


def main():
    global ctrl_enter_pressed

    # Запускаем хук в отдельном потоке
    start_hook()
    time.sleep(0.1)  # дать хуку время установиться

    # Инициализация Pygame
    pygame.init()
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN | pygame.NOFRAME)
    pygame.display.set_caption("Baby Keyboard")
    W, H = screen.get_size()

    # Делаем окно TOPMOST
    hwnd = pygame.display.get_wm_info()["window"]
    user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)

    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Arial", 96, bold=True)

    # Цвета
    BG_COLOR = (200, 228, 246)  # нежно-голубой фон
    CHAR_COLOR = (60, 60, 80)   # мягкий тёмно-серый для букв

    # Декоративные пузырьки на фоне
    bubbles = []
    for _ in range(30):
        bx = random.randint(0, W)
        by = random.randint(0, H)
        br = random.randint(20, 80)
        ba = random.randint(30, 80)  # прозрачность
        bubbles.append((bx, by, br, ba))

    # Состояние символов
    chars = []  # [(surface, x, y), ...]
    cursor_x = 20
    cursor_y = 20
    line_height = 110

    # Шлейф мыши
    trail = []  # [(x, y, r, g, b, timestamp), ...]
    TRAIL_LIFETIME = 2.0  # секунды
    trail_hue = 0.0

    # Создаём off-screen surface для шлейфа и пузырьков с per-pixel alpha
    trail_surface = pygame.Surface((W, H), pygame.SRCALPHA)
    bubble_surface = pygame.Surface((W, H), pygame.SRCALPHA)

    running = True

    while running:
        now = time.time()
        dt = clock.get_time() / 1000.0

        # ─── События ───
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                # Блокируем стандартное закрытие
                pass

            elif event.type == pygame.KEYDOWN:
                mods = pygame.key.get_mods()
                # Ctrl+Enter — выход
                if (mods & pygame.KMOD_CTRL) and event.key == pygame.K_RETURN:
                    running = False
                    break

                # Печатный символ
                if event.unicode and event.unicode.isprintable():
                    surf = font.render(event.unicode, True, CHAR_COLOR)
                    # Проверяем перенос строки
                    if cursor_x + surf.get_width() > W - 20:
                        cursor_x = 20
                        cursor_y += line_height
                    # Проверяем заполнение экрана
                    if cursor_y + line_height > H:
                        chars.clear()
                        cursor_x = 20
                        cursor_y = 20
                    chars.append((surf, cursor_x, cursor_y))
                    cursor_x += surf.get_width() + 5

            elif event.type == pygame.MOUSEMOTION:
                mx, my = event.pos
                trail_hue += 0.002
                color = hue_to_rgb(trail_hue)
                trail.append((mx, my, color[0], color[1], color[2], now))

        # Проверяем флаг от хука
        if ctrl_enter_pressed:
            running = False

        # ─── Обновление шлейфа ───
        # Удаляем старые точки
        cutoff = now - TRAIL_LIFETIME
        while trail and trail[0][5] < cutoff:
            trail.pop(0)

        # ─── Отрисовка ───
        screen.fill(BG_COLOR)

        # Пузырьки
        bubble_surface.fill((0, 0, 0, 0))
        for bx, by, br, ba in bubbles:
            pygame.draw.circle(bubble_surface, (255, 255, 255, ba), (bx, by), br)
            pygame.draw.circle(bubble_surface, (255, 255, 255, ba + 20), (bx, by), br, 2)
        screen.blit(bubble_surface, (0, 0))

        # Символы
        for surf, x, y in chars:
            screen.blit(surf, (x, y))

        # Шлейф мыши — линия из сегментов
        trail_surface.fill((0, 0, 0, 0))
        for i in range(1, len(trail)):
            x0, y0, r0, g0, b0, ts0 = trail[i - 1]
            x1, y1, r1, g1, b1, ts1 = trail[i]
            age = now - ts1
            alpha = max(0, int(255 * (1.0 - age / TRAIL_LIFETIME)))
            width = max(2, int(8 * (1.0 - age / TRAIL_LIFETIME)))
            if alpha > 0:
                pygame.draw.line(trail_surface, (r1, g1, b1, alpha), (x0, y0), (x1, y1), width)
        screen.blit(trail_surface, (0, 0))

        pygame.display.flip()
        clock.tick(60)

    # ─── Завершение ───
    stop_hook()
    pygame.quit()


if __name__ == "__main__":
    main()
