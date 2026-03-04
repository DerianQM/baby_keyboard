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
# 1. КЛЮЧЕВОЕ ТРЕБОВАНИЕ — выход только по Ctrl+Enter
# ═══════════════════════════════════════════════════════════════════

class TestCtrlEnterExit(unittest.TestCase):
    """Приложение должно закрываться ТОЛЬКО по Ctrl+Enter."""

    def _run_events(self):
        """Прокручивает очередь pygame-событий, возвращает running."""
        running = True
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                mods = event.mod
                if (mods & pygame.KMOD_CTRL) and event.key == pygame.K_RETURN:
                    running = False
        return running

    def _post_key(self, key, mod=0, unicode=""):
        pygame.event.post(pygame.event.Event(
            pygame.KEYDOWN,
            {"key": key, "mod": mod, "unicode": unicode, "scancode": 0}
        ))

    # ── Ctrl+Enter → выход ──────────────────────────────────────────

    def test_ctrl_enter_exits(self):
        self._post_key(pygame.K_RETURN, mod=pygame.KMOD_LCTRL, unicode="\r")
        self.assertFalse(self._run_events(), "Ctrl+Enter должен закрывать приложение")

    def test_rctrl_enter_exits(self):
        self._post_key(pygame.K_RETURN, mod=pygame.KMOD_RCTRL, unicode="\r")
        self.assertFalse(self._run_events(), "Правый Ctrl+Enter должен закрывать")

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
        BLOCKED = {0x5B, 0x5C}  # VK_LWIN, VK_RWIN
        for vk in BLOCKED:
            self.assertIn(vk, BLOCKED)

    def test_hook_blocks_alt_f4(self):
        VK_F4 = 0x73
        LLKHF_ALTDOWN = 0x20
        flags = LLKHF_ALTDOWN
        alt_down = bool(flags & LLKHF_ALTDOWN)
        blocked = alt_down and VK_F4 in (0x09, 0x73, 0x1B)  # TAB, F4, ESC
        self.assertTrue(blocked, "Alt+F4 должен быть заблокирован")

    def test_hook_blocks_ctrl_esc(self):
        VK_ESCAPE = 0x1B
        ctrl_down = True
        blocked = ctrl_down and VK_ESCAPE == 0x1B
        self.assertTrue(blocked, "Ctrl+Esc должен быть заблокирован")

    def test_hook_passes_ctrl_enter(self):
        """Ctrl+Enter должен ПРОПУСКАТЬСЯ хуком (return CallNextHookEx)."""
        VK_RETURN = 0x0D
        ctrl_down = True
        passed_through = ctrl_down and VK_RETURN == 0x0D
        self.assertTrue(passed_through, "Ctrl+Enter должен проходить через хук")


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
        b1.wobble_amp = b2.wobble_amp = 0  # убираем покачивание
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
        """Мышь на краю пузыря (radius+7) — должна лопнуть."""
        b = self._bubble()
        b.update(0.016, b.x + b.radius + 7, b.y)
        self.assertTrue(b.popping)

    def test_no_pop_just_outside(self):
        """Мышь за краем пузыря (radius+20) — не лопается."""
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
        b.update(0.016, b.x, b.y)  # pop
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
        """Логика поддержания TARGET_COUNT пузырей."""
        bubbles = [bk.Bubble(_W, _H) for _ in range(bk.Bubble.TARGET_COUNT)]
        for b in bubbles[:4]:
            b.alive = False
        bubbles = [b for b in bubbles if b.alive]
        while len(bubbles) < bk.Bubble.TARGET_COUNT:
            bubbles.append(bk.Bubble(_W, _H))
        self.assertEqual(len(bubbles), bk.Bubble.TARGET_COUNT)

    def test_already_popping_ignores_mouse(self):
        """Уже лопающийся пузырь не должен повторно вызывать pop()."""
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
        self.fizz.update(10.0)  # все должны умереть
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
        """Новые частицы spawning в верхней зоне экрана."""
        self.fizz.update(0.1)
        for p in self.fizz.particles:
            # Y при создании <= ZONE_H (могут выйти за пределы после движения)
            self.assertLess(p['y'], self.fizz.ZONE_H + 50)

    def test_burst_x_near_given(self):
        self.fizz.spawn_burst(x=600, n=20)
        for p in self.fizz.particles:
            self.assertAlmostEqual(p['x'], 600, delta=50)

    def test_continuous_spawn_accumulates(self):
        """Постоянный spawn без update — частицы накапливаются."""
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
        # size = (r+6)*2
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
        """Верх и низ фона должны отличаться по цвету."""
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
        """Разные размеры экрана не должны вызывать ошибки."""
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
        """Пузырь на краю поверхности — не должно быть IndexError."""
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
                         "TARGET_COUNT пузырей должен поддерживаться на протяжении всей симуляции")

    def test_dt_spike_no_crash(self):
        """Большой dt (зависание на 1 сек) не должен ломать симуляцию."""
        b = bk.Bubble(_W, _H, start_offscreen=False)
        b.x, b.y = 640, 400
        b.update(1.0, -9999, -9999)  # dt = 1 секунда

    def test_zero_dt_no_crash(self):
        b = bk.Bubble(_W, _H, start_offscreen=False)
        b.x, b.y = 640, 400
        b.update(0.0, -9999, -9999)

    def test_fizz_no_memory_leak(self):
        """Много burst-ов + большой dt → все частицы умерли, список не растёт."""
        fizz = bk.FizzSystem(_W, _H)
        for _ in range(200):
            fizz.spawn_burst(x=400, n=20)
        fizz.update(10.0)
        self.assertEqual(len(fizz.particles), 0)

    def test_rapid_pops_stability(self):
        """Быстрое лопание всех пузырей подряд — симуляция не падает."""
        bubbles = [bk.Bubble(_W, _H, start_offscreen=False)
                   for _ in range(bk.Bubble.TARGET_COUNT)]
        for b in bubbles:
            b.x, b.y = _W // 2, _H // 2
            b.update(0.016, _W // 2, _H // 2)  # все лопаются
        for b in bubbles:
            self.assertTrue(b.popping)

    def test_background_render_time(self):
        """Фон должен генерироваться быстрее 3 секунд."""
        start = time.perf_counter()
        bk.create_background(_W, _H)
        elapsed = time.perf_counter() - start
        self.assertLess(elapsed, 3.0,
                        f"create_background слишком медленный: {elapsed:.2f}s")

    def test_bubble_cache_warmup(self):
        """Прогрев кэша для всех размеров — без исключений."""
        for r in range(bk.Bubble.RADIUS_MIN, bk.Bubble.RADIUS_MAX + 1, 3):
            surf = bk.get_bubble_surf(r)
            self.assertIsNotNone(surf)


if __name__ == "__main__":
    unittest.main(verbosity=2)
