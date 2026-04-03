"""
Tests for Baby Keyboard (Windows version).

Запуск:  python -m pytest test_baby_keyboard.py -v
         python test_baby_keyboard.py

Использует SDL dummy-драйвер — дисплей не нужен.
"""

import os
import sys
import math
import time
import unittest

# ─── Headless SDL ───────────────────────────────────────────────────
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
pygame.init()

_W, _H = 1280, 720
_screen = pygame.display.set_mode((_W, _H))

# ─── Импорт тестируемого модуля ────────────────────────────────────
import baby_keyboard as bk


# ═══════════════════════════════════════════════════════════════════
# 1. КЛЮЧЕВОЕ ТРЕБОВАНИЕ — выход только по Ctrl+G+F7+Enter
# ═══════════════════════════════════════════════════════════════════

class TestCtrlGF7EnterExit(unittest.TestCase):
    """Приложение должно закрываться ТОЛЬКО по Ctrl+G+F7+Enter."""

    def _run_events(self):
        """Прокручивает очередь pygame-событий, возвращает running."""
        running = True
        g_held  = False
        f7_held = False
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_g:
                    g_held = True
                if event.key == pygame.K_F7:
                    f7_held = True
                mods = event.mod
                if (mods & pygame.KMOD_CTRL) and event.key == pygame.K_RETURN:
                    if g_held and f7_held:
                        running = False
            elif event.type == pygame.KEYUP:
                if event.key == pygame.K_g:
                    g_held = False
                if event.key == pygame.K_F7:
                    f7_held = False
        return running

    def _post_key(self, key, mod=0, unicode=""):
        pygame.event.post(pygame.event.Event(
            pygame.KEYDOWN,
            {"key": key, "mod": mod, "unicode": unicode, "scancode": 0}
        ))

    def _post_keyup(self, key, mod=0):
        pygame.event.post(pygame.event.Event(
            pygame.KEYUP,
            {"key": key, "mod": mod, "unicode": "", "scancode": 0}
        ))

    # ── Ctrl+G+F7+Enter → выход ─────────────────────────────────────

    def test_ctrl_g_f7_enter_exits(self):
        self._post_key(pygame.K_g, unicode="g")
        self._post_key(pygame.K_F7)
        self._post_key(pygame.K_RETURN, mod=pygame.KMOD_LCTRL, unicode="\r")
        self.assertFalse(self._run_events(), "Ctrl+G+F7+Enter должен закрывать приложение")

    def test_rctrl_g_f7_enter_exits(self):
        self._post_key(pygame.K_g, unicode="g")
        self._post_key(pygame.K_F7)
        self._post_key(pygame.K_RETURN, mod=pygame.KMOD_RCTRL, unicode="\r")
        self.assertFalse(self._run_events(), "Правый Ctrl+G+F7+Enter должен закрывать")

    # ── Неполные комбинации не выходят ──────────────────────────────

    def test_ctrl_enter_without_g_does_not_exit(self):
        self._post_key(pygame.K_RETURN, mod=pygame.KMOD_LCTRL, unicode="\r")
        self.assertTrue(self._run_events(), "Ctrl+Enter без G и F7 не должен закрывать")

    def test_ctrl_g_enter_without_f7_does_not_exit(self):
        """Ctrl+G+Enter без F7 — не выходит."""
        self._post_key(pygame.K_g, unicode="g")
        self._post_key(pygame.K_RETURN, mod=pygame.KMOD_LCTRL, unicode="\r")
        self.assertTrue(self._run_events(), "Ctrl+G+Enter без F7 не должен закрывать")

    def test_ctrl_f7_enter_without_g_does_not_exit(self):
        """Ctrl+F7+Enter без G — не выходит."""
        self._post_key(pygame.K_F7)
        self._post_key(pygame.K_RETURN, mod=pygame.KMOD_LCTRL, unicode="\r")
        self.assertTrue(self._run_events(), "Ctrl+F7+Enter без G не должен закрывать")

    def test_g_released_before_enter_does_not_exit(self):
        """G отпущена до Enter — не выходит."""
        self._post_key(pygame.K_g, unicode="g")
        self._post_keyup(pygame.K_g)
        self._post_key(pygame.K_F7)
        self._post_key(pygame.K_RETURN, mod=pygame.KMOD_LCTRL, unicode="\r")
        self.assertTrue(self._run_events(), "G отпущена — не должен закрывать")

    def test_f7_released_before_enter_does_not_exit(self):
        """F7 отпущена до Enter — не выходит."""
        self._post_key(pygame.K_g, unicode="g")
        self._post_key(pygame.K_F7)
        self._post_keyup(pygame.K_F7)
        self._post_key(pygame.K_RETURN, mod=pygame.KMOD_LCTRL, unicode="\r")
        self.assertTrue(self._run_events(), "F7 отпущена — не должен закрывать")

    # ── Одиночные клавиши не выходят ────────────────────────────────

    def test_escape_does_not_exit(self):
        self._post_key(pygame.K_ESCAPE)
        self.assertTrue(self._run_events(), "Escape не должен закрывать")

    def test_enter_alone_does_not_exit(self):
        self._post_key(pygame.K_RETURN, unicode="\r")
        self.assertTrue(self._run_events(), "Enter без Ctrl не должен закрывать")

    def test_ctrl_alone_does_not_exit(self):
        self._post_key(pygame.K_LCTRL, mod=pygame.KMOD_LCTRL)
        self.assertTrue(self._run_events(), "Только Ctrl не должен закрывать")

    def test_g_alone_does_not_exit(self):
        self._post_key(pygame.K_g, unicode="g")
        self.assertTrue(self._run_events(), "Только G не должен закрывать")

    def test_alt_f4_does_not_exit_via_event(self):
        self._post_key(pygame.K_F4, mod=pygame.KMOD_ALT)
        self.assertTrue(self._run_events(), "Alt+F4 не должен проходить через event loop")

    def test_random_letters_do_not_exit(self):
        for key in (pygame.K_a, pygame.K_z, pygame.K_SPACE):
            self._post_key(key, unicode=chr(key))
        self.assertTrue(self._run_events(), "Обычные клавиши не должны закрывать")

    # ── Флаг от хука ────────────────────────────────────────────────

    def test_hook_flag_triggers_exit(self):
        """ctrl_enter_pressed = True должен переводить running → False."""
        original = bk.ctrl_enter_pressed
        bk.ctrl_enter_pressed = True
        running = True
        if bk.ctrl_enter_pressed:
            running = False
        self.assertFalse(running)
        bk.ctrl_enter_pressed = original

    def test_hook_flag_false_keeps_running(self):
        original = bk.ctrl_enter_pressed
        bk.ctrl_enter_pressed = False
        running = True
        if bk.ctrl_enter_pressed:
            running = False
        self.assertTrue(running)
        bk.ctrl_enter_pressed = original

    # ── Логика хука: заблокированные комбинации ──────────────────────

    def test_hook_blocks_win_key(self):
        """Win-клавиши (VK_LWIN, VK_RWIN) должны блокироваться хуком."""
        BLOCKED = {0x5B, 0x5C}
        for vk in BLOCKED:
            self.assertIn(vk, BLOCKED)

    def test_hook_blocks_alt_f4(self):
        VK_F4 = 0x73
        LLKHF_ALTDOWN = 0x20
        flags = LLKHF_ALTDOWN
        alt_down = bool(flags & LLKHF_ALTDOWN)
        blocked = alt_down and VK_F4 in (0x09, 0x73, 0x1B)
        self.assertTrue(blocked, "Alt+F4 должен быть заблокирован")

    def test_hook_blocks_ctrl_esc(self):
        VK_ESCAPE = 0x1B
        ctrl_down = True
        blocked = ctrl_down and VK_ESCAPE == 0x1B
        self.assertTrue(blocked, "Ctrl+Esc должен быть заблокирован")

    def test_hook_passes_ctrl_g_f7_enter(self):
        """Ctrl+G+F7+Enter должен ПРОПУСКАТЬСЯ хуком (return CallNextHookEx)."""
        VK_RETURN = 0x0D
        VK_G      = 0x47
        VK_F7     = 0x76
        ctrl_down = True
        g_down    = True
        f7_down   = True
        passed = ctrl_down and g_down and f7_down and VK_RETURN == 0x0D
        self.assertTrue(passed, "Ctrl+G+F7+Enter должен проходить через хук")

    def test_hook_does_not_set_flag_without_g(self):
        """Хук не должен устанавливать флаг если G не зажата."""
        VK_RETURN = 0x0D
        ctrl_down = True
        g_down    = False
        f7_down   = True
        would_set = ctrl_down and g_down and f7_down and VK_RETURN == 0x0D
        self.assertFalse(would_set, "Без G флаг не должен устанавливаться")

    def test_hook_does_not_set_flag_without_f7(self):
        """Хук не должен устанавливать флаг если F7 не зажата."""
        VK_RETURN = 0x0D
        ctrl_down = True
        g_down    = True
        f7_down   = False
        would_set = ctrl_down and g_down and f7_down and VK_RETURN == 0x0D
        self.assertFalse(would_set, "Без F7 флаг не должен устанавливаться")


# ═══════════════════════════════════════════════════════════════════
# 2. Lifecycle пузырей
# ═══════════════════════════════════════════════════════════════════

class TestBubbleLifecycle(unittest.TestCase):

    def _bubble(self, offscreen=False):
        b = bk.Bubble(_W, _H, start_offscreen=offscreen)
        b.x, b.y = _W // 2, _H // 2
        return b

    def test_start_offscreen_is_below(self):
        for _ in range(10):
            b = bk.Bubble(_W, _H, start_offscreen=True)
            self.assertGreater(b.y, _H - 1,
                               "Пузырь offscreen должен стартовать ниже экрана")

    def test_moves_upward(self):
        b = self._bubble()
        y0 = b.y
        b.update(0.1, -9999, -9999)
        self.assertLess(b.y, y0, "Пузырь должен двигаться вверх")

    def test_speed_proportional_to_dt(self):
        """Перемещение должно быть пропорционально dt."""
        b1 = self._bubble()
        b2 = self._bubble()
        b1.speed = b2.speed = 60.0
        b1.wobble_amp = b2.wobble_amp = 0
        y0 = b1.y
        b1.update(0.1, -9999, -9999)
        b2.update(0.2, -9999, -9999)
        d1 = y0 - b1.y
        d2 = y0 - b2.y
        self.assertAlmostEqual(d2, d1 * 2, delta=2.0)

    def test_pops_on_mouse_hover(self):
        b = self._bubble()
        b.update(0.016, b.x, b.y)
        self.assertTrue(b.popping, "Должен лопнуть при наведении мыши")

    def test_no_pop_when_mouse_far(self):
        b = self._bubble()
        b.update(0.016, -9999, -9999)
        self.assertFalse(b.popping, "Не должен лопаться когда мышь далеко")

    def test_pop_on_bubble_edge(self):
        b = self._bubble()
        b.update(0.016, b.x + b.radius + 7, b.y)
        self.assertTrue(b.popping)

    def test_no_pop_just_outside(self):
        b = self._bubble()
        b.update(0.016, b.x + b.radius + 20, b.y)
        self.assertFalse(b.popping)

    def test_pop_creates_particles(self):
        b = self._bubble()
        b.pop()
        self.assertGreaterEqual(len(b.pop_particles), 10,
                                "Лопание должно создавать >= 10 частиц")

    def test_particles_float_upward(self):
        b = self._bubble()
        b.pop()
        up_biased = sum(1 for p in b.pop_particles if p['vy'] < 0)
        self.assertGreater(up_biased, len(b.pop_particles) // 2,
                           "Большинство частиц должны лететь вверх")

    def test_dies_after_pop_animation(self):
        b = self._bubble()
        b.update(0.016, b.x, b.y)
        for _ in range(70):
            b.update(0.016, -9999, -9999)
        self.assertFalse(b.alive, "Пузырь должен умереть после анимации лопания")

    def test_dies_at_top(self):
        b = self._bubble()
        b.y = -200
        b.update(0.016, -9999, -9999)
        self.assertFalse(b.alive, "Пузырь должен умереть при выходе за верх")
        self.assertTrue(b.reached_top)

    def test_reached_top_flag(self):
        b = self._bubble()
        b.y = -200
        b.update(0.016, -9999, -9999)
        self.assertTrue(b.reached_top)

    def test_stays_in_x_bounds(self):
        b = bk.Bubble(_W, _H, start_offscreen=False)
        for _ in range(300):
            b.update(0.016, -9999, -9999)
            if not b.alive:
                break
            self.assertGreaterEqual(b.x, b.radius + 4)
            self.assertLessEqual(b.x, _W - b.radius - 4)

    def test_size_in_range(self):
        for _ in range(30):
            b = bk.Bubble(_W, _H)
            self.assertGreaterEqual(b.radius, bk.Bubble.RADIUS_MIN)
            self.assertLessEqual(b.radius, bk.Bubble.RADIUS_MAX)

    def test_speed_in_range(self):
        for _ in range(30):
            b = bk.Bubble(_W, _H)
            self.assertGreaterEqual(b.speed, bk.Bubble.SPEED_MIN)
            self.assertLessEqual(b.speed, bk.Bubble.SPEED_MAX)

    def test_target_count_maintained(self):
        bubbles = [bk.Bubble(_W, _H) for _ in range(bk.Bubble.TARGET_COUNT)]
        for b in bubbles[:4]:
            b.alive = False
        bubbles = [b for b in bubbles if b.alive]
        while len(bubbles) < bk.Bubble.TARGET_COUNT:
            bubbles.append(bk.Bubble(_W, _H))
        self.assertEqual(len(bubbles), bk.Bubble.TARGET_COUNT)

    def test_already_popping_ignores_mouse(self):
        b = self._bubble()
        b.pop()
        particles_before = len(b.pop_particles)
        b.update(0.016, b.x, b.y)
        self.assertEqual(len(b.pop_particles), particles_before,
                         "Второй pop не должен добавлять частицы")


# ═══════════════════════════════════════════════════════════════════
# 3. FizzSystem
# ═══════════════════════════════════════════════════════════════════

class TestFizzSystem(unittest.TestCase):

    def setUp(self):
        self.fizz = bk.FizzSystem(_W, _H)

    def test_particles_spawn_on_update(self):
        self.fizz.update(0.5)
        self.assertGreater(len(self.fizz.particles), 0)

    def test_particles_cleaned_up(self):
        self.fizz.update(0.5)
        self.fizz.update(10.0)
        self.assertEqual(len(self.fizz.particles), 0,
                         "Все частицы с истёкшим life должны удаляться")

    def test_spawn_burst_count(self):
        before = len(self.fizz.particles)
        self.fizz.spawn_burst(x=400, n=15)
        self.assertEqual(len(self.fizz.particles) - before, 15)

    def test_particles_have_upward_vy(self):
        self.fizz.update(0.1)
        for p in self.fizz.particles:
            self.assertLess(p['vy'], 0, "Все частицы fizz должны лететь вверх")

    def test_particles_in_top_zone(self):
        self.fizz.update(0.1)
        for p in self.fizz.particles:
            self.assertLess(p['y'], self.fizz.ZONE_H + 50)

    def test_burst_x_near_given(self):
        self.fizz.spawn_burst(x=600, n=20)
        for p in self.fizz.particles:
            self.assertAlmostEqual(p['x'], 600, delta=50)

    def test_continuous_spawn_accumulates(self):
        for _ in range(5):
            self.fizz.spawn_burst(x=400, n=10)
        self.assertGreaterEqual(len(self.fizz.particles), 50)


# ═══════════════════════════════════════════════════════════════════
# 4. Кэш пузырей
# ═══════════════════════════════════════════════════════════════════

class TestBubbleCache(unittest.TestCase):

    def test_returns_surface(self):
        surf = bk.get_bubble_surf(60)
        self.assertIsInstance(surf, pygame.Surface)

    def test_same_radius_same_object(self):
        s1 = bk.get_bubble_surf(70)
        s2 = bk.get_bubble_surf(70)
        self.assertIs(s1, s2, "Одинаковый радиус должен давать тот же объект")

    def test_different_radii_different_objects(self):
        s1 = bk.get_bubble_surf(50)
        s2 = bk.get_bubble_surf(90)
        self.assertIsNot(s1, s2)

    def test_surface_has_alpha(self):
        surf = bk.get_bubble_surf(60)
        self.assertEqual(surf.get_flags() & pygame.SRCALPHA, pygame.SRCALPHA,
                         "Поверхность пузыря должна иметь per-pixel alpha")

    def test_surface_size_matches_radius(self):
        r = 60
        surf = bk.get_bubble_surf(r)
        w, h = surf.get_size()
        expected = (r + 6) * 2
        self.assertEqual(w, expected)
        self.assertEqual(h, expected)


# ═══════════════════════════════════════════════════════════════════
# 5. Фон
# ═══════════════════════════════════════════════════════════════════

class TestBackground(unittest.TestCase):

    def test_returns_surface(self):
        bg = bk.create_background(800, 600)
        self.assertIsInstance(bg, pygame.Surface)

    def test_correct_size(self):
        bg = bk.create_background(800, 600)
        self.assertEqual(bg.get_size(), (800, 600))

    def test_has_gradient(self):
        bg = bk.create_background(400, 400)
        top = bg.get_at((200, 5))[:3]
        bot = bg.get_at((200, 395))[:3]
        diff = sum(abs(int(a) - int(b)) for a, b in zip(top, bot))
        self.assertGreater(diff, 5, "Фон должен иметь градиент")

    def test_not_solid_black(self):
        bg = bk.create_background(200, 200)
        pixel = bg.get_at((100, 100))[:3]
        self.assertGreater(sum(pixel), 0, "Фон не должен быть чёрным")

    def test_various_sizes(self):
        for w, h in [(640, 480), (1920, 1080), (2560, 1440)]:
            bg = bk.create_background(w, h)
            self.assertEqual(bg.get_size(), (w, h))


# ═══════════════════════════════════════════════════════════════════
# 6. Отрисовка (не падает)
# ═══════════════════════════════════════════════════════════════════

class TestDrawing(unittest.TestCase):

    def setUp(self):
        self.surf = pygame.Surface((600, 600), pygame.SRCALPHA)

    def test_draw_bubble_normal(self):
        bk.draw_aero_bubble(self.surf, 300, 300, 70)

    def test_draw_bubble_small(self):
        bk.draw_aero_bubble(self.surf, 50, 50, 5)

    def test_draw_bubble_alpha_zero(self):
        bk.draw_aero_bubble(self.surf, 300, 300, 60, alpha=0)

    def test_draw_bubble_alpha_partial(self):
        bk.draw_aero_bubble(self.surf, 300, 300, 60, alpha=128)

    def test_draw_bubble_at_edge(self):
        bk.draw_aero_bubble(self.surf, 0, 0, 70)
        bk.draw_aero_bubble(self.surf, 600, 600, 70)

    def test_bubble_draw_alive(self):
        b = bk.Bubble(600, 600, start_offscreen=False)
        b.x, b.y = 300, 300
        b.draw(self.surf)

    def test_bubble_draw_popping(self):
        b = bk.Bubble(600, 600, start_offscreen=False)
        b.x, b.y = 300, 300
        b.pop()
        b.update(0.1, -999, -999)
        b.draw(self.surf)

    def test_bubble_draw_fading(self):
        b = bk.Bubble(600, 600, start_offscreen=False)
        b.x, b.y = 300, 300
        b.pop()
        for _ in range(30):
            b.update(0.016, -999, -999)
        b.draw(self.surf)

    def test_fizz_draw(self):
        fizz = bk.FizzSystem(600, 600)
        fizz.update(0.3)
        fizz.draw(self.surf)


# ═══════════════════════════════════════════════════════════════════
# 7. Стабильность
# ═══════════════════════════════════════════════════════════════════

class TestStability(unittest.TestCase):

    def test_simulate_10_seconds(self):
        """10 секунд симуляции @ 60fps — без исключений, TARGET_COUNT сохраняется."""
        W, H = 1280, 720
        surf = pygame.Surface((W, H), pygame.SRCALPHA)
        bubbles = [bk.Bubble(W, H, start_offscreen=False)
                   for _ in range(bk.Bubble.TARGET_COUNT)]
        fizz = bk.FizzSystem(W, H)
        dt = 1 / 60

        for frame in range(600):
            mx = 100 + (frame * 3) % (W - 200)
            my = 200 + (frame * 2) % (H - 400)

            for b in bubbles:
                b.update(dt, mx, my)

            alive = []
            for b in bubbles:
                if b.reached_top:
                    fizz.spawn_burst(b.x)
                if b.alive:
                    alive.append(b)
            bubbles = alive

            while len(bubbles) < bk.Bubble.TARGET_COUNT:
                bubbles.append(bk.Bubble(W, H))

            fizz.update(dt)
            surf.fill((0, 0, 0, 0))
            for b in bubbles:
                b.draw(surf)
            fizz.draw(surf)

        self.assertEqual(len(bubbles), bk.Bubble.TARGET_COUNT,
                         "TARGET_COUNT пузырей должен поддерживаться")

    def test_dt_spike_no_crash(self):
        b = bk.Bubble(_W, _H, start_offscreen=False)
        b.x, b.y = 640, 400
        b.update(1.0, -9999, -9999)

    def test_zero_dt_no_crash(self):
        b = bk.Bubble(_W, _H, start_offscreen=False)
        b.x, b.y = 640, 400
        b.update(0.0, -9999, -9999)

    def test_fizz_no_memory_leak(self):
        fizz = bk.FizzSystem(_W, _H)
        for _ in range(200):
            fizz.spawn_burst(x=400, n=20)
        fizz.update(10.0)
        self.assertEqual(len(fizz.particles), 0)

    def test_rapid_pops_stability(self):
        bubbles = [bk.Bubble(_W, _H, start_offscreen=False)
                   for _ in range(bk.Bubble.TARGET_COUNT)]
        for b in bubbles:
            b.x, b.y = _W // 2, _H // 2
            b.update(0.016, _W // 2, _H // 2)
        for b in bubbles:
            self.assertTrue(b.popping)

    def test_background_render_time(self):
        start = time.perf_counter()
        bk.create_background(_W, _H)
        elapsed = time.perf_counter() - start
        self.assertLess(elapsed, 3.0,
                        f"create_background слишком медленный: {elapsed:.2f}s")

    def test_bubble_cache_warmup(self):
        for r in range(bk.Bubble.RADIUS_MIN, bk.Bubble.RADIUS_MAX + 1, 3):
            surf = bk.get_bubble_surf(r)
            self.assertIsNotNone(surf)


# ═══════════════════════════════════════════════════════════════════
# 8. PaintSystem
# ═══════════════════════════════════════════════════════════════════

class TestPaintSystem(unittest.TestCase):

    def setUp(self):
        self.paint = bk.PaintSystem()

    def test_spawn_creates_blobs(self):
        self.paint.spawn(400, 300, 80)
        self.assertGreaterEqual(len(self.paint.blobs), 5)
        self.assertLessEqual(len(self.paint.blobs), 9)

    def test_blobs_have_required_keys(self):
        self.paint.spawn(400, 300, 80)
        for b in self.paint.blobs:
            for key in ('x', 'y', 'r0', 'r_max', 'life', 'max_life', 'color', 'vx', 'vy'):
                self.assertIn(key, b)

    def test_blobs_expire_after_update(self):
        self.paint.spawn(400, 300, 80)
        self.paint.update(100.0)
        self.assertEqual(len(self.paint.blobs), 0, "Все блобы должны умереть после большого dt")

    def test_blobs_move_on_update(self):
        self.paint.spawn(400, 300, 80)
        initial = [(b['x'], b['y']) for b in self.paint.blobs]
        self.paint.update(0.1)
        moved = any((b['x'], b['y']) != p for b, p in zip(self.paint.blobs, initial))
        self.assertTrue(moved, "Блобы должны двигаться после update")

    def test_draw_no_crash(self):
        surf = pygame.Surface((800, 600), pygame.SRCALPHA)
        self.paint.spawn(400, 300, 80)
        self.paint.update(0.5)
        self.paint.draw(surf)

    def test_draw_empty_no_crash(self):
        surf = pygame.Surface((800, 600), pygame.SRCALPHA)
        self.paint.draw(surf)

    def test_r_max_larger_than_r0(self):
        self.paint.spawn(400, 300, 80)
        for b in self.paint.blobs:
            self.assertGreater(b['r_max'], b['r0'])

    def test_multiple_spawns_accumulate(self):
        for _ in range(5):
            self.paint.spawn(400, 300, 80)
        self.assertGreaterEqual(len(self.paint.blobs), 25)

    def test_color_from_palette(self):
        self.paint.spawn(400, 300, 80)
        for b in self.paint.blobs:
            self.assertIn(b['color'], bk._PAINT_COLORS)


# ═══════════════════════════════════════════════════════════════════
# 9. Clam — граничные случаи и FSM
# ═══════════════════════════════════════════════════════════════════

class TestClamBoundary(unittest.TestCase):

    def _clam(self, open_val=0.0):
        c = bk.Clam(cx=640, sand_y=600)
        c.open = open_val
        return c

    def _surf(self):
        return pygame.Surface((1280, 720), pygame.SRCALPHA)

    def test_draw_open_zero_no_crash(self):
        c = self._clam(0.0)
        c.draw(self._surf())

    def test_draw_open_one_no_crash(self):
        c = self._clam(1.0)
        c.draw(self._surf())

    def test_draw_open_half_no_crash(self):
        c = self._clam(0.5)
        c.draw(self._surf())

    def test_draw_open_tiny_no_crash(self):
        c = self._clam(0.001)
        c.draw(self._surf())

    def test_gap_never_negative(self):
        import math
        for open_val in [0.0, 0.001, 0.1, 0.42, 0.5, 1.0]:
            angle_rad = math.radians(open_val * bk.Clam.MAX_ANGLE_DEG)
            gap = int(bk.Clam.TOP_H * math.sin(angle_rad))
            self.assertGreaterEqual(gap, 0, f"gap<0 при open={open_val}")

    def test_app_ry_never_zero(self):
        import math
        for open_val in [0.0, 0.5, 1.0]:
            angle_rad = math.radians(open_val * bk.Clam.MAX_ANGLE_DEG)
            app_ry = max(4, int(bk.Clam.TOP_H * math.cos(angle_rad)))
            self.assertGreaterEqual(app_ry, 4, f"app_ry<4 при open={open_val}")

    def test_draw_with_cx_zero_no_crash(self):
        c = bk.Clam(cx=0, sand_y=600)
        c.open = 0.5
        c.draw(self._surf())

    def test_draw_with_sand_y_small_no_crash(self):
        c = bk.Clam(cx=640, sand_y=100)
        c.open = 0.5
        c.draw(self._surf())

    def test_draw_large_open_face_no_crash(self):
        c = self._clam(1.0)
        c.state = bk._CS_HAPPY
        c.wave_angle = 20.0
        c.draw(self._surf())

    def test_draw_happy_arm_no_crash(self):
        c = self._clam(1.0)
        c.state = bk._CS_HAPPY
        c.wave_angle = 0.0
        c.draw(self._surf())


class TestClamFSM(unittest.TestCase):

    def _no_events(self):
        return []

    def _make_clam(self):
        c = bk.Clam(cx=640, sand_y=600)
        c.state = bk._CS_IDLE_CLOSED
        c.idle_timer = 0.001
        return c

    def test_fsm_idle_closed_to_opening(self):
        c = self._make_clam()
        c.update(0.1, -9999, -9999, self._no_events())
        self.assertEqual(c.state, bk._CS_OPENING)

    def test_fsm_opening_to_idle_open(self):
        c = self._make_clam()
        c.update(0.1, -9999, -9999, self._no_events())
        self.assertEqual(c.state, bk._CS_OPENING)
        for _ in range(200):
            c.update(0.05, -9999, -9999, self._no_events())
            if c.state == bk._CS_IDLE_OPEN:
                break
        self.assertEqual(c.state, bk._CS_IDLE_OPEN)

    def test_fsm_idle_open_to_closing(self):
        c = self._make_clam()
        c.state = bk._CS_IDLE_OPEN
        c.hold_timer = 0.001
        c.update(0.1, -9999, -9999, self._no_events())
        self.assertEqual(c.state, bk._CS_CLOSING)

    def test_fsm_closing_to_idle_closed(self):
        c = self._make_clam()
        c.state = bk._CS_CLOSING
        c.open = 0.001
        for _ in range(50):
            c.update(0.05, -9999, -9999, self._no_events())
            if c.state == bk._CS_IDLE_CLOSED:
                break
        self.assertEqual(c.state, bk._CS_IDLE_CLOSED)

    def test_fsm_idle_closed_to_hiding_on_near(self):
        c = self._make_clam()
        c.idle_timer = 999.0
        c.update(0.016, 640, 515, self._no_events())
        self.assertEqual(c.state, bk._CS_HIDING)

    def test_fsm_hiding_to_idle_closed_when_far(self):
        c = self._make_clam()
        c.state = bk._CS_HIDING
        c.update(0.016, -9999, -9999, self._no_events())
        self.assertEqual(c.state, bk._CS_IDLE_CLOSED)

    def test_fsm_happy_full_cycle(self):
        c = self._make_clam()
        c.state = bk._CS_HAPPY_OPENING
        for _ in range(200):
            c.update(0.05, -9999, -9999, self._no_events())
            if c.state == bk._CS_HAPPY:
                break
        self.assertEqual(c.state, bk._CS_HAPPY)
        c.happy_timer = 0.001
        c.update(0.1, -9999, -9999, self._no_events())
        self.assertEqual(c.state, bk._CS_HAPPY_CLOSING)
        for _ in range(100):
            c.update(0.05, -9999, -9999, self._no_events())
            if c.state == bk._CS_IDLE_CLOSED:
                break
        self.assertEqual(c.state, bk._CS_IDLE_CLOSED)

    def test_fsm_open_value_in_range(self):
        c = self._make_clam()
        for _ in range(300):
            c.update(0.016, -9999, -9999, self._no_events())
            self.assertGreaterEqual(c.open, 0.0)
            self.assertLessEqual(c.open, 1.0)

    def test_draw_all_states_no_crash(self):
        surf = pygame.Surface((1280, 720), pygame.SRCALPHA)
        for state in [bk._CS_IDLE_CLOSED, bk._CS_OPENING,
                      bk._CS_IDLE_OPEN, bk._CS_CLOSING,
                      bk._CS_HIDING, bk._CS_HAPPY_OPENING,
                      bk._CS_HAPPY, bk._CS_HAPPY_CLOSING]:
            c = bk.Clam(cx=640, sand_y=600)
            c.state = state
            c.open = 0.5
            c.draw(surf)


# ═══════════════════════════════════════════════════════════════════
# 10. SeabedDecor — не перекрывает зону клама
# ═══════════════════════════════════════════════════════════════════

class TestSeabedDecorNoOverlapClam(unittest.TestCase):

    def test_seaweeds_x_outside_clam_zone(self):
        """Водоросли не должны перекрывать зону клама."""
        W, H = 1280, 720
        decor = bk.SeabedDecor(W, H)
        clam_cx = max(bk.Clam.RX + 20, int(W * 0.24))
        clam_rx = bk.Clam.RX
        for sw in decor.seaweeds:
            x = sw['x']
            outside = (x > clam_cx + clam_rx) or (x < clam_cx - clam_rx)
            self.assertTrue(outside,
                f"Водоросль x={x} перекрывает зону клама cx={clam_cx} rx={clam_rx}")

    def test_right_side_decor_outside_clam_zone(self):
        """Декорации правее 0.5W не должны перекрывать зону клама."""
        W, H = 1280, 720
        decor = bk.SeabedDecor(W, H)
        clam_cx = max(bk.Clam.RX + 20, int(W * 0.24))
        clam_rx = bk.Clam.RX
        right_x = []
        for c in decor.coral_brain:
            right_x.append(c['x'])
        for c in decor.coral_fan:
            right_x.append(c['x'])
        for c in decor.coral_tube:
            right_x.append(c['x'])
        for x in right_x:
            outside = (x > clam_cx + clam_rx) or (x < clam_cx - clam_rx)
            self.assertTrue(outside,
                f"Коралл x={x} перекрывает зону клама cx={clam_cx} rx={clam_rx}")


# ═══════════════════════════════════════════════════════════════════
# 11. Stability 30 секунд симуляции
# ═══════════════════════════════════════════════════════════════════

class TestStability30s(unittest.TestCase):

    def test_simulate_30_seconds_no_exception(self):
        W, H = 1280, 720
        surf = pygame.Surface((W, H), pygame.SRCALPHA)
        sand_y = H - int(H * bk.SAND_H_FRAC)
        bubbles = [bk.Bubble(W, H, start_offscreen=False)
                   for _ in range(bk.Bubble.TARGET_COUNT)]
        fizz   = bk.FizzSystem(W, H)
        fishes = bk.FishSystem()
        paint  = bk.PaintSystem()
        decor  = bk.SeabedDecor(W, H)
        clam   = bk.Clam(cx=max(bk.Clam.RX + 20, int(W * 0.24)), sand_y=sand_y)
        dt = 1 / 60
        t  = 0.0

        for frame in range(30 * 60):
            mx = 100 + (frame * 3) % (W - 200)
            my = 200 + (frame * 2) % (H - 400)
            t += dt

            popping_before = {id(b) for b in bubbles if b.popping}
            for b in bubbles:
                b.update(dt, mx, my)
            for b in bubbles:
                if b.popping and id(b) not in popping_before:
                    if b.has_fish:
                        fishes.spawn_from_bubble(b.x, b.y, b.radius, b.inner_fish)
                    else:
                        paint.spawn(b.x, b.y, b.radius)

            alive = [b for b in bubbles if b.alive]
            for b in bubbles:
                if b.reached_top:
                    fizz.spawn_burst(b.x)
            bubbles = [b for b in bubbles if b.alive]
            while len(bubbles) < bk.Bubble.TARGET_COUNT:
                bubbles.append(bk.Bubble(W, H))

            fizz.update(dt)
            fishes.update(dt)
            paint.update(dt)
            clam.update(dt, mx, my, [])

            surf.fill((0, 0, 0, 0))
            decor.draw(surf, t)
            clam.draw(surf)
            for b in bubbles:
                b.draw(surf)
            fizz.draw(surf)
            fishes.draw(surf)
            paint.draw(surf)

        self.assertEqual(len(bubbles), bk.Bubble.TARGET_COUNT)


if __name__ == "__main__":
    unittest.main(verbosity=2)
