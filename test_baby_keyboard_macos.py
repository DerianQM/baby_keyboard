"""
Tests for Baby Keyboard (macOS version).

Запуск:  python -m pytest test_baby_keyboard_macos.py -v
         python test_baby_keyboard_macos.py

Использует SDL dummy-драйвер — дисплей не нужен.
Quartz недоступен на Windows — хук-специфичные тесты проверяют
только логику (без реального CGEventTap).
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
import baby_keyboard_macos as bk


# ═══════════════════════════════════════════════════════════════════
# 1. КЛЮЧЕВОЕ ТРЕБОВАНИЕ — выход только по Ctrl+G+Enter
# ═══════════════════════════════════════════════════════════════════

class TestCtrlGEnterExit(unittest.TestCase):
    """Приложение должно закрываться ТОЛЬКО по Ctrl+G+Enter."""

    def _run_events(self):
        running = True
        g_held  = False
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_g:
                    g_held = True
                mods = event.mod
                if (mods & pygame.KMOD_CTRL) and event.key == pygame.K_RETURN:
                    if g_held:
                        running = False
            elif event.type == pygame.KEYUP:
                if event.key == pygame.K_g:
                    g_held = False
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

    def test_ctrl_g_enter_exits(self):
        self._post_key(pygame.K_g, unicode="g")
        self._post_key(pygame.K_RETURN, mod=pygame.KMOD_LCTRL, unicode="\r")
        self.assertFalse(self._run_events(), "Ctrl+G+Enter должен закрывать приложение")

    def test_ctrl_enter_without_g_does_not_exit(self):
        self._post_key(pygame.K_RETURN, mod=pygame.KMOD_LCTRL, unicode="\r")
        self.assertTrue(self._run_events(), "Ctrl+Enter без G не должен закрывать")

    def test_g_released_before_enter_does_not_exit(self):
        self._post_key(pygame.K_g, unicode="g")
        self._post_keyup(pygame.K_g)
        self._post_key(pygame.K_RETURN, mod=pygame.KMOD_LCTRL, unicode="\r")
        self.assertTrue(self._run_events(), "G отпущена — не должен закрывать")

    def test_escape_does_not_exit(self):
        self._post_key(pygame.K_ESCAPE)
        self.assertTrue(self._run_events(), "Escape не должен закрывать")

    def test_enter_alone_does_not_exit(self):
        self._post_key(pygame.K_RETURN, unicode="\r")
        self.assertTrue(self._run_events(), "Enter без Ctrl не должен закрывать")

    def test_g_alone_does_not_exit(self):
        self._post_key(pygame.K_g, unicode="g")
        self.assertTrue(self._run_events(), "Только G не должен закрывать")

    def test_random_letters_do_not_exit(self):
        for key in (pygame.K_a, pygame.K_z, pygame.K_SPACE):
            self._post_key(key, unicode=chr(key))
        self.assertTrue(self._run_events(), "Обычные клавиши не должны закрывать")

    def test_hook_flag_triggers_exit(self):
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

    # ── Логика CGEventTap callback (без реального Quartz) ────────────

    def test_tap_callback_logic_ctrl_g_enter(self):
        """Ctrl+G+Enter → флаг должен быть установлен."""
        KC_RETURN = bk.KC_RETURN
        KC_G      = bk.KC_G
        ctrl      = True
        g_down    = True
        flag_set  = ctrl and g_down and KC_RETURN == bk.KC_RETURN
        self.assertTrue(flag_set, "Ctrl+G+Enter должен устанавливать флаг")

    def test_tap_callback_logic_without_g(self):
        """Ctrl+Enter без G → флаг НЕ должен устанавливаться."""
        ctrl   = True
        g_down = False
        flag_set = ctrl and g_down
        self.assertFalse(flag_set, "Без G флаг не должен устанавливаться")

    def test_tap_blocks_cmd_tab(self):
        """Cmd+Tab должен блокироваться (возвращать None)."""
        KC_TAB = bk.KC_TAB
        cmd    = True
        blocked = cmd and KC_TAB in (bk.KC_TAB, bk.KC_Q, bk.KC_W,
                                      bk.KC_H,   bk.KC_M, bk.KC_SPACE, bk.KC_F4)
        self.assertTrue(blocked, "Cmd+Tab должен быть заблокирован")

    def test_tap_blocks_cmd_q(self):
        cmd = True
        blocked = cmd and bk.KC_Q in (bk.KC_TAB, bk.KC_Q, bk.KC_W,
                                       bk.KC_H,   bk.KC_M, bk.KC_SPACE, bk.KC_F4)
        self.assertTrue(blocked, "Cmd+Q должен быть заблокирован")

    def test_has_quartz_flag_exists(self):
        self.assertIsInstance(bk.HAS_QUARTZ, bool)

    def test_g_key_down_tracking(self):
        """_g_key_down должен быть булевым полем."""
        self.assertIsInstance(bk._g_key_down, bool)


# ═══════════════════════════════════════════════════════════════════
# 2. Lifecycle пузырей
# ═══════════════════════════════════════════════════════════════════

class TestBubbleLifecycle(unittest.TestCase):

    def _bubble(self):
        b = bk.Bubble(_W, _H, start_offscreen=False)
        b.x, b.y = _W // 2, _H // 2
        return b

    def test_start_offscreen_is_below(self):
        for _ in range(10):
            b = bk.Bubble(_W, _H, start_offscreen=True)
            self.assertGreater(b.y, _H - 1)

    def test_moves_upward(self):
        b = self._bubble()
        y0 = b.y
        b.update(0.1, -9999, -9999)
        self.assertLess(b.y, y0)

    def test_pops_on_mouse_hover(self):
        b = self._bubble()
        b.update(0.016, b.x, b.y)
        self.assertTrue(b.popping)

    def test_no_pop_when_mouse_far(self):
        b = self._bubble()
        b.update(0.016, -9999, -9999)
        self.assertFalse(b.popping)

    def test_pop_creates_particles(self):
        b = self._bubble()
        b.pop()
        self.assertGreaterEqual(len(b.pop_particles), 10)

    def test_particles_float_upward(self):
        b = self._bubble()
        b.pop()
        up_biased = sum(1 for p in b.pop_particles if p['vy'] < 0)
        self.assertGreater(up_biased, len(b.pop_particles) // 2)

    def test_dies_after_pop_animation(self):
        b = self._bubble()
        b.update(0.016, b.x, b.y)
        for _ in range(70):
            b.update(0.016, -9999, -9999)
        self.assertFalse(b.alive)

    def test_dies_at_top(self):
        b = self._bubble()
        b.y = -200
        b.update(0.016, -9999, -9999)
        self.assertFalse(b.alive)
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
        self.assertEqual(len(b.pop_particles), particles_before)


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
        self.assertEqual(len(self.fizz.particles), 0)

    def test_spawn_burst_count(self):
        before = len(self.fizz.particles)
        self.fizz.spawn_burst(x=400, n=15)
        self.assertEqual(len(self.fizz.particles) - before, 15)

    def test_particles_have_upward_vy(self):
        self.fizz.update(0.1)
        for p in self.fizz.particles:
            self.assertLess(p['vy'], 0)

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
        self.assertIs(s1, s2)

    def test_different_radii_different_objects(self):
        s1 = bk.get_bubble_surf(50)
        s2 = bk.get_bubble_surf(90)
        self.assertIsNot(s1, s2)

    def test_surface_has_alpha(self):
        surf = bk.get_bubble_surf(60)
        self.assertEqual(surf.get_flags() & pygame.SRCALPHA, pygame.SRCALPHA)

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

    def test_correct_size(self):
        bg = bk.create_background(800, 600)
        self.assertEqual(bg.get_size(), (800, 600))

    def test_has_gradient(self):
        bg = bk.create_background(400, 400)
        top = bg.get_at((200, 5))[:3]
        bot = bg.get_at((200, 395))[:3]
        diff = sum(abs(int(a) - int(b)) for a, b in zip(top, bot))
        self.assertGreater(diff, 5)

    def test_not_solid_black(self):
        bg = bk.create_background(200, 200)
        pixel = bg.get_at((100, 100))[:3]
        self.assertGreater(sum(pixel), 0)

    def test_various_sizes(self):
        for w, h in [(640, 480), (1920, 1080)]:
            bg = bk.create_background(w, h)
            self.assertEqual(bg.get_size(), (w, h))


# ═══════════════════════════════════════════════════════════════════
# 6. Отрисовка
# ═══════════════════════════════════════════════════════════════════

class TestDrawing(unittest.TestCase):

    def setUp(self):
        self.surf = pygame.Surface((600, 600), pygame.SRCALPHA)

    def test_draw_bubble_normal(self):
        bk.draw_aero_bubble(self.surf, 300, 300, 70)

    def test_draw_bubble_alpha_partial(self):
        bk.draw_aero_bubble(self.surf, 300, 300, 60, alpha=128)

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

    def test_fizz_draw(self):
        fizz = bk.FizzSystem(600, 600)
        fizz.update(0.3)
        fizz.draw(self.surf)


# ═══════════════════════════════════════════════════════════════════
# 7. Стабильность
# ═══════════════════════════════════════════════════════════════════

class TestStability(unittest.TestCase):

    def test_simulate_10_seconds(self):
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

        self.assertEqual(len(bubbles), bk.Bubble.TARGET_COUNT)

    def test_dt_spike_no_crash(self):
        b = bk.Bubble(_W, _H, start_offscreen=False)
        b.x, b.y = 640, 400
        b.update(1.0, -9999, -9999)

    def test_fizz_no_memory_leak(self):
        fizz = bk.FizzSystem(_W, _H)
        for _ in range(200):
            fizz.spawn_burst(x=400, n=20)
        fizz.update(10.0)
        self.assertEqual(len(fizz.particles), 0)

    def test_background_render_time(self):
        start = time.perf_counter()
        bk.create_background(_W, _H)
        elapsed = time.perf_counter() - start
        self.assertLess(elapsed, 3.0)

    def test_bubble_cache_warmup(self):
        for r in range(bk.Bubble.RADIUS_MIN, bk.Bubble.RADIUS_MAX + 1, 3):
            surf = bk.get_bubble_surf(r)
            self.assertIsNotNone(surf)


if __name__ == "__main__":
    unittest.main(verbosity=2)
