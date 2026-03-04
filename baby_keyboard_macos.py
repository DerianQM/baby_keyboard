"""
Baby Keyboard (macOS) — безопасная песочница для малыша.
Полноэкранное приложение: нажатия клавиш показывают символы,
движение мыши оставляет радужный шлейф.
Закрытие только по Ctrl+Enter.

Требования: pip install pygame pyobjc-framework-Quartz
"""

import threading
import time
import random
import colorsys
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
KC_TAB = 48
KC_Q = 12
KC_W = 13
KC_H = 4
KC_M = 46
KC_SPACE = 49
KC_F4 = 118
KC_ESCAPE = 53
KC_RETURN = 36

# ─── Глобальное состояние ──────────────────────────────────────────

ctrl_enter_pressed = False
_run_loop_ref = None


def _event_tap_callback(proxy, event_type, event, refcon):
    """CGEventTap callback: блокирует системные комбинации на macOS."""
    global ctrl_enter_pressed

    if event_type not in (kCGEventKeyDown, kCGEventKeyUp, kCGEventFlagsChanged):
        return event

    keycode = CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode)
    flags = CGEventGetFlags(event)

    cmd = bool(flags & kCGEventFlagMaskCommand)
    ctrl = bool(flags & kCGEventFlagMaskControl)
    alt = bool(flags & kCGEventFlagMaskAlternate)

    # Ctrl+Enter — пропускаем (для закрытия)
    if ctrl and keycode == KC_RETURN and event_type == kCGEventKeyDown:
        ctrl_enter_pressed = True
        return event

    # Блокируем Cmd+Tab (переключение приложений)
    if cmd and keycode == KC_TAB:
        return None

    # Блокируем Cmd+Q (выход из приложения)
    if cmd and keycode == KC_Q:
        return None

    # Блокируем Cmd+W (закрытие окна)
    if cmd and keycode == KC_W:
        return None

    # Блокируем Cmd+H (скрыть приложение)
    if cmd and keycode == KC_H:
        return None

    # Блокируем Cmd+M (свернуть)
    if cmd and keycode == KC_M:
        return None

    # Блокируем Cmd+Space (Spotlight)
    if cmd and keycode == KC_SPACE:
        return None

    # Блокируем Cmd+Alt+Esc (Force Quit)
    if cmd and alt and keycode == KC_ESCAPE:
        return None

    # Блокируем Ctrl+стрелки и Mission Control (Ctrl+Up/Down)
    # и Cmd+F4 (закрытие)
    if cmd and keycode == KC_F4:
        return None

    return event


def _tap_thread():
    """Поток для CGEventTap и RunLoop."""
    global _run_loop_ref

    if not HAS_QUARTZ:
        return

    event_mask = (
        (1 << kCGEventKeyDown) |
        (1 << kCGEventKeyUp) |
        (1 << kCGEventFlagsChanged)
    )

    tap = CGEventTapCreate(
        kCGSessionEventTap,
        kCGHeadInsertEventTap,
        0,  # активный тап (не пассивный)
        event_mask,
        _event_tap_callback,
        None,
    )

    if tap is None:
        print("WARN: не удалось создать CGEventTap. "
              "Дайте приложению разрешение в "
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


# ─── Главное приложение ────────────────────────────────────────────


def main():
    global ctrl_enter_pressed

    # Запускаем хук в отдельном потоке
    start_hook()
    time.sleep(0.2)

    # Инициализация Pygame
    pygame.init()
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN | pygame.NOFRAME)
    pygame.display.set_caption("Baby Keyboard")
    W, H = screen.get_size()

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
        ba = random.randint(30, 80)
        bubbles.append((bx, by, br, ba))

    # Состояние символов
    chars = []
    cursor_x = 20
    cursor_y = 20
    line_height = 110

    # Шлейф мыши
    trail = []
    TRAIL_LIFETIME = 2.0
    trail_hue = 0.0

    # Off-screen surfaces с per-pixel alpha
    trail_surface = pygame.Surface((W, H), pygame.SRCALPHA)
    bubble_surface = pygame.Surface((W, H), pygame.SRCALPHA)

    running = True

    while running:
        now = time.time()

        # ─── События ───
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
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
                mx, my = event.pos
                trail_hue += 0.002
                color = hue_to_rgb(trail_hue)
                trail.append((mx, my, color[0], color[1], color[2], now))

        # Проверяем флаг от хука
        if ctrl_enter_pressed:
            running = False

        # Удаляем старые точки шлейфа
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
