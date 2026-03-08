NEW_CLAM = r'''
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
            brx = int(self.RX * 0.72)
            bry = int(gap * 0.70)
            bcy = seam_y - gap // 2
            pygame.draw.ellipse(surface, (210, 80, 76, 245),
                                pygame.Rect(cx - brx, bcy - bry, brx * 2, bry * 2))
            hlrx = int(brx * 0.50)
            hlry = int(bry * 0.34)
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
        pts = []
        for i in range(N + 1):
            a = math.pi * i / N
            pts.append((int(cx + rx * math.cos(a)),
                        int(pivot_y + sign * ry * math.sin(a))))
        pygame.draw.polygon(surface, (*col_o, 250), pts)
        irx, iry = rx - 16, max(4, ry - 16)
        ipts = []
        for i in range(N + 1):
            a = math.pi * i / N
            ipts.append((int(cx + irx * math.cos(a)),
                         int(pivot_y + sign * iry * math.sin(a))))
        pygame.draw.polygon(surface, (*col_i, 215), ipts)
        for i in range(13):
            a = math.pi * i / 12
            pygame.draw.line(surface, (*dark, 78),
                             (cx, pivot_y),
                             (int(cx + rx * 0.96 * math.cos(a)),
                              int(pivot_y + sign * ry * 0.96 * math.sin(a))), 2)
        pygame.draw.polygon(surface, (*dark, 195), pts, 3)
        if ry > 16:
            blik = []
            for i in range(14):
                a = math.pi * (0.11 + 0.78 * i / 13)
                blik.append((int(cx + rx * 0.68 * math.cos(a)),
                             int(pivot_y + sign * ry * 0.68 * math.sin(a))))
            if len(blik) >= 2:
                pygame.draw.lines(surface, (*lite, 100), False, blik, 5)

    def _draw_face(self, surface, cx, seam_y, gap):
        face_y = seam_y - gap // 2
        eye_r  = max(10, int(self.RX * 0.058))
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
            sw = int(self.RX * 0.30)
            sh = int(sw * 0.48)
            pygame.draw.arc(surface, (185, 52, 52, 240),
                            pygame.Rect(cx - sw // 2, face_y + 4, sw, sh),
                            math.pi, math.pi * 2, max(3, int(self.RX * 0.013)))

    def _draw_arm(self, surface, cx, seam_y, gap):
        bx      = cx + self.RX - 8
        by      = seam_y - gap // 3
        arm_len = int(self.RX * 0.23)
        flen    = int(arm_len * 0.55)
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
'''

import re

for filepath in [
    'C:/Projects/baby_keyboard/baby_keyboard.py',
    'C:/Projects/baby_keyboard/baby_keyboard_macos.py',
]:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    start = content.index('\nclass Clam:')
    m = re.search(r'\n\n\n?# [─\-]', content[start + 10:])
    if not m:
        raise RuntimeError('end marker not found in ' + filepath)
    end = start + 10 + m.start()

    new_content = content[:start] + NEW_CLAM + content[end:]
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f'patched {filepath}')
