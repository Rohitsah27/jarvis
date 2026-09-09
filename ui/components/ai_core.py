"""
Central Holographic AI Core: 3D Holographic Dots Human Face.
Features:
- Genuinely 3D, procedurally-generated particle-cloud face — no static
  image asset. A stylized head/face surface (eyes, nose, cheeks, mouth,
  chin as radius bumps/dips on a front-facing dome) is sampled into ~2500
  small 3D points once at startup, then rotated by a real 3D rotation
  matrix and projected to 2D every frame, so it has genuine depth parallax
  as it sways — not just a flat animated image.
- Holographic vertical scanline sweep and breathing luminescence
- Real-time voice reactive audio amplitude pulsing & expanding sonic shockwaves
- Flanking HUD telemetry columns:
    Left:  LISTENING | THINKING | ANALYZING | EXECUTING
    Right: INTELLIGENCE | ASSISTANCE | AUTOMATION | ALWAYS ON
- Under-face glowing cyber typography: 'JARVIS' and 'HOW CAN I ASSIST YOU?'
- State transitions: IDLE, LISTENING, THINKING, SPEAKING, PROCESSING, OFFLINE
"""
import math
import random
from typing import List, Tuple

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QTimer, QRectF, QPointF
from PySide6.QtGui import (
    QPainter,
    QColor,
    QPen,
    QBrush,
    QFont,
    QRadialGradient,
    QLinearGradient,
    QPainterPath,
)
from ui.styles.theme import theme


def _face_width_profile(pn: float) -> float:
    """
    Narrows the face at the forehead/hairline and jaw/chin, widest at the
    cheekbone/eye line — an actual face taper. Without this, a sphere's
    cross-section is the same width at every height, which is exactly why
    a bumpy sphere reads as a "ball with texture" instead of a face: the
    SILHOUETTE itself needs to taper, not just the surface shading.
    """
    if pn < 0.32:
        return 0.68 + 0.32 * (pn / 0.32)  # forehead tapering up to the hairline
    elif pn < 0.62:
        return 1.0  # cheekbone/eye line — widest part of the face
    else:
        t = (pn - 0.62) / 0.38
        return 1.0 - 0.62 * t  # jaw tapering down to a narrower chin


def _generate_face_point_cloud(n_theta: int = 64, n_phi: int = 40) -> List[List[Tuple[float, float, float]]]:
    """
    Procedurally builds a stylized 3D head+neck+shoulders bust as a POINT
    GRID (rows of same-height points), entirely from math — no mesh file or
    image asset. The head is sampled on a front-facing hemisphere (a dome)
    using standard spherical coordinates; the neck and shoulders below it
    are separate, simpler cross-section rows appended to the same grid so
    the caller can draw wireframe contour lines within each row (connecting
    neighboring points at the same height) for that "topology scan" mesh
    look, with particle dots at each vertex on top — matching a reference
    HUD bust portrait rather than a floating disembodied head.

    Two things make the head read as an actual FACE rather than a textured
    ball: (1) _face_width_profile tapers the silhouette itself (narrow
    forehead, wide cheekbones, narrow jaw) instead of a uniform circular
    cross-section, and (2) the base radius is locally perturbed by Gaussian
    bump/dip terms carving out eye sockets (indent), a nose ridge and tip
    (protrude), a mouth line (indent), cheekbones and chin (protrude).

    Returned as a list of rows (each row a list of (x, y, z)) in a
    normalized coordinate space (x=left/right, y=up/down, z=depth toward
    the viewer) — an oval aspect ratio and further scaling are applied at
    draw time.
    """
    rows: List[List[Tuple[float, float, float]]] = []
    phi_min, phi_max = math.pi * 0.08, math.pi * 0.94  # top-of-head .. below chin

    def jittered(x, y, z, amount=0.009):
        return (
            x + random.uniform(-amount, amount),
            y + random.uniform(-amount, amount),
            z + random.uniform(-amount, amount),
        )

    # ---- Head (spherical dome) ----
    for j in range(n_phi):
        phi = phi_min + (phi_max - phi_min) * (j / (n_phi - 1))
        pn = (phi - phi_min) / (phi_max - phi_min)  # normalized 0..1 (top..chin)
        row: List[Tuple[float, float, float]] = []
        for i in range(n_theta):
            theta = -math.pi / 2 + math.pi * (i / (n_theta - 1))
            tn = theta / (math.pi / 2)  # normalized -1..1 (left..right)

            bump = 0.0
            # Eye sockets (indent) — deep and sharply localized so they
            # read unmistakably as eyes, not shading noise.
            for ex in (-0.36, 0.36):
                d2 = ((tn - ex) / 0.115) ** 2 + ((pn - 0.40) / 0.075) ** 2
                bump -= 0.38 * math.exp(-d2)
            # Nose ridge (protrude)
            d2 = (tn / 0.07) ** 2 + ((pn - 0.52) / 0.18) ** 2
            bump += 0.32 * math.exp(-d2)
            # Nose tip (extra protrude)
            d2 = (tn / 0.05) ** 2 + ((pn - 0.63) / 0.045) ** 2
            bump += 0.22 * math.exp(-d2)
            # Mouth line (indent)
            d2 = (tn / 0.18) ** 2 + ((pn - 0.81) / 0.028) ** 2
            bump -= 0.15 * math.exp(-d2)
            # Cheekbones (protrude)
            for cx in (-0.46, 0.46):
                d2 = ((tn - cx) / 0.16) ** 2 + ((pn - 0.56) / 0.12) ** 2
                bump += 0.11 * math.exp(-d2)
            # Chin (protrude)
            d2 = (tn / 0.13) ** 2 + ((pn - 0.95) / 0.045) ** 2
            bump += 0.12 * math.exp(-d2)

            r = 1.0 + bump
            width = _face_width_profile(pn)
            x = r * math.sin(phi) * math.sin(theta) * width
            y = -r * math.cos(phi)  # negative so phi=0 (top of head) is up on screen
            z = r * math.sin(phi) * math.cos(theta)  # max at theta=0 (facing viewer)
            row.append(jittered(x, y, z))
        rows.append(row)

    head_bottom_y = rows[-1][n_theta // 2][1]  # chin y, front-center point

    # ---- Neck (narrow, roughly cylindrical) ----
    n_neck_rows = 4
    neck_y0, neck_y1 = head_bottom_y, head_bottom_y + 0.10
    neck_width = 0.30
    for k in range(n_neck_rows):
        t = k / (n_neck_rows - 1)
        yn = neck_y0 + (neck_y1 - neck_y0) * t
        row = []
        for i in range(n_theta):
            theta = -math.pi / 2 + math.pi * (i / (n_theta - 1))
            x = neck_width * math.sin(theta)
            z = neck_width * math.cos(theta) * 0.75
            row.append(jittered(x, yn, z))
        rows.append(row)

    # ---- Shoulders (widening, flattening flare) ----
    n_shoulder_rows = 8
    sh_y0, sh_y1 = neck_y1, neck_y1 + 0.30
    for k in range(n_shoulder_rows):
        t = k / (n_shoulder_rows - 1)
        ys = sh_y0 + (sh_y1 - sh_y0) * t
        shoulder_width = neck_width + 1.35 * (t ** 1.15)
        depth_scale = 0.55 * (1.0 - 0.4 * t)
        row = []
        for i in range(n_theta):
            theta = -math.pi / 2 + math.pi * (i / (n_theta - 1))
            x = shoulder_width * math.sin(theta)
            z = shoulder_width * math.cos(theta) * depth_scale
            row.append(jittered(x, ys, z))
        rows.append(row)

    return rows


class AICoreState:
    IDLE = "IDLE"
    LISTENING = "LISTENING"
    THINKING = "THINKING"
    SPEAKING = "SPEAKING"
    PROCESSING = "PROCESSING"
    OFFLINE = "OFFLINE"


class ShockwaveRing:
    """Dynamic expanding shockwave circle line that pops outward on voice detection."""

    def __init__(self, start_r: float, max_r: float, speed: float, color: QColor, width: float = 2.0):
        self.radius = start_r
        self.start_r = start_r
        self.max_r = max_r
        self.speed = speed
        self.color = color
        self.width = width
        self.alpha = 255
        self.alive = True

    def update(self):
        self.radius += self.speed
        if self.radius >= self.max_r:
            self.alive = False
            self.alpha = 0
        else:
            progress = (self.radius - self.start_r) / max(1.0, (self.max_r - self.start_r))
            self.alpha = max(0, int(255 * ((1.0 - progress) ** 1.35)))


class FloatingParticle:
    """Ambient floating cyber node point drifting around the holographic face."""

    def __init__(self, bounds_w: float, bounds_h: float):
        self.x = random.uniform(bounds_w * 0.25, bounds_w * 0.75)
        self.y = random.uniform(bounds_h * 0.15, bounds_h * 0.85)
        self.vx = random.uniform(-0.4, 0.4)
        self.vy = random.uniform(-0.5, -0.1)
        self.size = random.uniform(1.2, 2.8)
        self.alpha = random.uniform(80, 220)
        self.phase = random.uniform(0, math.pi * 2)

    def update(self, bounds_w: float, bounds_h: float):
        self.x += self.vx
        self.y += self.vy
        self.phase += 0.05
        # Wrap around bounds
        if self.y < bounds_h * 0.08:
            self.y = bounds_h * 0.88
            self.x = random.uniform(bounds_w * 0.25, bounds_w * 0.75)
        if self.x < bounds_w * 0.20 or self.x > bounds_w * 0.80:
            self.vx *= -1


class JarvisAICore(QWidget):
    """
    Futuristic Holographic 3D Dots Human Face AI Core.
    Replaces circular orb with high-tech biometric particle countenance.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(320, 260)
        self.state = AICoreState.IDLE

        # Animation states
        self._pulse_phase = 0.0
        self._scanline_phase = 0.0
        self._audio_amplitude = 0.0
        self._smoothed_amp = 0.0
        # Concentric HUD targeting rings rotating in opposite directions
        # (classic sci-fi "locked on" look) — independent phases so they
        # visibly counter-rotate rather than moving together.
        self._ring_rotation_outer = 0.0
        self._ring_rotation_inner = 0.0
        self._orbit_phase = 0.0

        # Dynamic expanding pop-up circle lines
        self._shockwave_rings: List[ShockwaveRing] = []
        self._ring_spawn_cooldown = 0

        # Ambient cyber particles
        self._particles: List[FloatingParticle] = [
            FloatingParticle(500, 300) for _ in range(24)
        ]

        # Procedural 3D point-grid bust (head+neck+shoulders, see
        # _generate_face_point_cloud) — generated once here, rotated +
        # projected + wireframe-connected fresh every frame. Density traded
        # down slightly from the face-only version since drawing wireframe
        # lines between points roughly doubles the per-frame primitive
        # count versus dots alone.
        self._face_points_3d = _generate_face_point_cloud(n_theta=36, n_phi=22)
        # How far down the bust actually extends (chin -> neck -> shoulder
        # bottom), read directly from the generated geometry rather than
        # hardcoding the neck/shoulder proportions a second time — used to
        # keep the "JARVIS" title/subtitle text clear of the shoulders
        # instead of overlapping them.
        self._bust_max_y = max(p[1] for row in self._face_points_3d for p in row)
        self._face_rotation_phase = 0.0  # drives a gentle turntable sway
        self._face_rotation_speed = 1.0

        # Animation timer (~30 FPS)
        self._timer = QTimer(self)
        self._timer.setInterval(33)
        self._timer.timeout.connect(self._animation_tick)
        self._timer.start()

    def set_state(self, state: str):
        if self.state != state:
            self.state = state
            self.update()

    def set_audio_amplitude(self, amp: float):
        """Called by voice engine when speaking or listening to voice input."""
        self._audio_amplitude = max(0.0, min(1.0, amp))

    def _animation_tick(self):
        # Audio smoothing filter (fast attack, smooth decay)
        if self._audio_amplitude > self._smoothed_amp:
            self._smoothed_amp = self._audio_amplitude
        else:
            self._smoothed_amp = max(0.0, self._smoothed_amp * 0.82 - 0.01)

        # Pulse and scanline speeds based on state
        boost = 1.0 + self._smoothed_amp * 1.5
        if self.state == AICoreState.IDLE:
            self._pulse_phase += 0.045
            self._scanline_phase = (self._scanline_phase + 0.008) % 1.0
        elif self.state == AICoreState.LISTENING:
            self._pulse_phase += 0.08 * boost
            self._scanline_phase = (self._scanline_phase + 0.016 * boost) % 1.0
        elif self.state == AICoreState.THINKING:
            self._pulse_phase += 0.16
            self._scanline_phase = (self._scanline_phase + 0.024) % 1.0
        elif self.state == AICoreState.SPEAKING:
            self._pulse_phase += 0.09 * boost
            self._scanline_phase = (self._scanline_phase + 0.014 * boost) % 1.0
        elif self.state == AICoreState.PROCESSING:
            self._pulse_phase += 0.14
            self._scanline_phase = (self._scanline_phase + 0.020) % 1.0
        else:  # OFFLINE
            self._pulse_phase += 0.01

        # HUD ring rotation: faster and more "alert" while actively
        # thinking/processing, slow ambient drift otherwise — counter-
        # rotating so they read as two independent locked-on rings rather
        # than one rigid frame.
        ring_speed = 1.0
        if self.state in (AICoreState.THINKING, AICoreState.PROCESSING):
            ring_speed = 2.4
        elif self.state in (AICoreState.LISTENING, AICoreState.SPEAKING):
            ring_speed = 1.5 * boost
        elif self.state == AICoreState.OFFLINE:
            ring_speed = 0.15
        self._ring_rotation_outer = (self._ring_rotation_outer + 0.35 * ring_speed) % 360.0
        self._ring_rotation_inner = (self._ring_rotation_inner - 0.55 * ring_speed) % 360.0
        self._orbit_phase = (self._orbit_phase + 0.022 * ring_speed) % (math.pi * 2)
        # Slow turntable sway for the 3D face — a full spin would expose
        # that only the front hemisphere was ever generated (no back-of-
        # head data), so this stays a gentle back-and-forth like a bust
        # rotating on a pedestal rather than a full rotation.
        self._face_rotation_phase = (self._face_rotation_phase + 0.010 * ring_speed) % (math.pi * 2)

        # Update shockwave rings
        for ring in self._shockwave_rings:
            ring.update()
        self._shockwave_rings = [r for r in self._shockwave_rings if r.alive]

        # Trigger pop-up acoustic shockwave on speech volume peaks
        self._ring_spawn_cooldown = max(0, self._ring_spawn_cooldown - 1)
        w = max(200, self.width())
        h = max(200, self.height())
        face_size = min(w * 0.45, h * 0.72)

        if self._smoothed_amp > 0.22 and self._ring_spawn_cooldown == 0 and self.state in (AICoreState.LISTENING, AICoreState.SPEAKING):
            color = QColor(0, 255, 235) if self.state == AICoreState.LISTENING else QColor(0, 210, 255)
            self._shockwave_rings.append(
                ShockwaveRing(
                    start_r=face_size * 0.42,
                    max_r=face_size * 0.82,
                    speed=3.5 + 4.0 * self._smoothed_amp,
                    color=color,
                    width=2.0,
                )
            )
            self._ring_spawn_cooldown = 7

        # Update floating particles
        for p in self._particles:
            p.update(w, h)

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        w = float(self.width())
        h = float(self.height())
        center_x = w / 2.0
        center_y = h * 0.44

        pulse = (math.sin(self._pulse_phase) + 1.0) / 2.0

        # Colors based on state
        if self.state == AICoreState.IDLE:
            primary_color = QColor(0, 210, 255)
            glow_mult = 0.7 + 0.3 * pulse + self._smoothed_amp * 0.5
        elif self.state == AICoreState.LISTENING:
            primary_color = QColor(0, 255, 235)
            glow_mult = 0.9 + 0.25 * pulse + self._smoothed_amp * 0.7
        elif self.state == AICoreState.THINKING:
            primary_color = QColor(190, 95, 255)
            glow_mult = 0.85 + 0.3 * pulse
        elif self.state == AICoreState.SPEAKING:
            primary_color = QColor(0, 230, 255)
            glow_mult = 0.8 + self._smoothed_amp * 0.75
        elif self.state == AICoreState.PROCESSING:
            primary_color = QColor(0, 245, 255)
            glow_mult = 0.95
        else:  # OFFLINE
            primary_color = QColor(90, 110, 130)
            glow_mult = 0.2

        # -------------------------------------------------------------
        # 1. Background Cyber Aura Glow
        # -------------------------------------------------------------
        glow_rad = min(w, h) * (0.50 + 0.15 * self._smoothed_amp)
        glow_grad = QRadialGradient(QPointF(center_x, center_y), glow_rad)
        glow_grad.setColorAt(0.0, QColor(primary_color.red(), primary_color.green(), primary_color.blue(), int(48 * glow_mult)))
        glow_grad.setColorAt(0.55, QColor(0, 120, 255, int(18 * glow_mult)))
        glow_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(glow_grad))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QPointF(center_x, center_y), glow_rad, glow_rad)

        # -------------------------------------------------------------
        # 1.5 Rotating HUD Targeting Rings ("locked on" sci-fi look) —
        # a segmented dashed ring and a tick-marked ring counter-rotating
        # around the face, plus two small nodes orbiting like electrons.
        # -------------------------------------------------------------
        ring_base = min(h * 0.72, w * 0.44) / 2.0  # matches face_h/2 below
        outer_r = ring_base * 1.28
        inner_r = ring_base * 1.08

        painter.save()
        painter.translate(center_x, center_y)
        painter.rotate(self._ring_rotation_outer)
        painter.setPen(QPen(QColor(primary_color.red(), primary_color.green(), primary_color.blue(), int(120 * glow_mult)), 1.6))
        painter.setBrush(Qt.NoBrush)
        outer_rect = QRectF(-outer_r, -outer_r, outer_r * 2, outer_r * 2)
        segment_span = 22 * 16
        gap_span = 14 * 16
        angle = 0
        while angle < 360 * 16:
            painter.drawArc(outer_rect, angle, segment_span)
            angle += segment_span + gap_span
        painter.restore()

        painter.save()
        painter.translate(center_x, center_y)
        painter.rotate(self._ring_rotation_inner)
        painter.setPen(QPen(QColor(primary_color.red(), primary_color.green(), primary_color.blue(), int(80 * glow_mult)), 1.0))
        painter.drawEllipse(QRectF(-inner_r, -inner_r, inner_r * 2, inner_r * 2))
        tick_count = 24
        for i in range(tick_count):
            a = math.radians(i * (360.0 / tick_count))
            is_major = (i % 6 == 0)
            tick_len = 7.0 if is_major else 3.5
            tick_alpha = 200 if is_major else 90
            x1, y1 = inner_r * math.cos(a), inner_r * math.sin(a)
            x2, y2 = (inner_r + tick_len) * math.cos(a), (inner_r + tick_len) * math.sin(a)
            painter.setPen(QPen(
                QColor(primary_color.red(), primary_color.green(), primary_color.blue(), int(tick_alpha * glow_mult)),
                1.2 if is_major else 0.8,
            ))
            painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))
        painter.restore()

        for offset in (0.0, math.pi):
            ox = center_x + outer_r * math.cos(self._orbit_phase + offset)
            oy = center_y + outer_r * math.sin(self._orbit_phase + offset)
            node_glow = QRadialGradient(QPointF(ox, oy), 9.0)
            node_glow.setColorAt(0.0, QColor(primary_color.red(), primary_color.green(), primary_color.blue(), int(140 * glow_mult)))
            node_glow.setColorAt(1.0, QColor(0, 0, 0, 0))
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(node_glow))
            painter.drawEllipse(QPointF(ox, oy), 9.0, 9.0)
            painter.setBrush(QBrush(QColor(primary_color.red(), primary_color.green(), primary_color.blue(), int(230 * glow_mult))))
            painter.drawEllipse(QPointF(ox, oy), 3.2, 3.2)

        # -------------------------------------------------------------
        # 2. Dynamic Expanding Shockwave Rings
        # -------------------------------------------------------------
        for ring in self._shockwave_rings:
            if ring.alpha <= 0:
                continue
            r_pen = QPen(
                QColor(ring.color.red(), ring.color.green(), ring.color.blue(), int(ring.alpha * 0.75)),
                ring.width,
            )
            painter.setPen(r_pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(QPointF(center_x, center_y), ring.radius, ring.radius)

        # -------------------------------------------------------------
        # 3. Ambient Cyber Constellation Particles
        # -------------------------------------------------------------
        for p in self._particles:
            p_alpha = int(min(255, p.alpha * (0.6 + 0.4 * math.sin(p.phase))))
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor(primary_color.red(), primary_color.green(), primary_color.blue(), p_alpha)))
            painter.drawEllipse(QPointF(p.x, p.y), p.size, p.size)

        # -------------------------------------------------------------
        # 4. Central 3D Holographic Dots Human Face
        # -------------------------------------------------------------
        face_h = min(h * 0.72, w * 0.58)
        face_w = face_h  # square aspect

        # Dynamic breathing scale
        scale_mod = 1.0 + 0.018 * math.sin(self._pulse_phase) + 0.04 * self._smoothed_amp
        cur_w = face_w * scale_mod
        cur_h = face_h * scale_mod
        face_rect = QRectF(center_x - cur_w / 2.0, center_y - cur_h / 2.0, cur_w, cur_h)

        # Rotate the procedural 3D point cloud by a gentle turntable sway
        # and project to 2D — a real 3D object with genuine depth parallax
        # as it sways, not a flat animated image. Each point is a small
        # dot shaded by its post-rotation depth (closer to the viewer =
        # brighter/bigger), which is what actually reads as "3D" rather
        # than a flat sprite.
        face_opacity = min(1.0, 0.88 + 0.12 * pulse + self._smoothed_amp * 0.25)
        rot = 0.35 * math.sin(self._face_rotation_phase)
        cos_r, sin_r = math.cos(rot), math.sin(rot)
        radius_px = cur_h / 2.0
        base_size = max(0.7, radius_px / 130.0)
        # A face is taller than it is wide — an equal x/y scale is exactly
        # what made this look like a round ball instead of a face. Combined
        # with _face_width_profile's silhouette taper, this is what actually
        # gives it a face-shaped outline. bust_scale additionally shrinks
        # the WHOLE bust proportionally: face_h below was originally sized
        # assuming just a head (max_y ~= 1.0), but the bust now extends
        # down through the neck and shoulders to self._bust_max_y (~1.4) —
        # without this, the shoulders run past the widget's bottom edge and
        # collide with the "JARVIS" title text under it.
        bust_scale = 1.0 / self._bust_max_y
        width_scale = radius_px * 0.80 * bust_scale
        height_scale = radius_px * 1.10 * bust_scale

        # Project every row first (need all positions before drawing the
        # wireframe mesh lines that connect them).
        projected_rows = []
        for row in self._face_points_3d:
            proj_row = []
            for x, y, z in row:
                xr = x * cos_r + z * sin_r
                zr = -x * sin_r + z * cos_r
                depth = max(0.0, min(1.0, (zr + 1.0) / 2.0))
                proj_row.append((center_x + xr * width_scale, center_y + y * height_scale, depth))
            projected_rows.append(proj_row)

        # Wireframe contour lines — horizontal (within each row) and sparse
        # vertical (between rows) connections, dimmer than the dots and
        # drawn first so the particles sit on top of the mesh, matching a
        # topology-scan HUD look instead of a pure disconnected point cloud.
        for proj_row in projected_rows:
            for idx in range(len(proj_row) - 1):
                px1, py1, d1 = proj_row[idx]
                px2, py2, d2 = proj_row[idx + 1]
                avg_depth = (d1 + d2) / 2.0
                line_alpha = int(70 * (0.25 + 0.75 * avg_depth) * face_opacity)
                if line_alpha <= 2:
                    continue
                painter.setPen(QPen(QColor(primary_color.red(), primary_color.green(), primary_color.blue(), line_alpha), 0.6))
                painter.drawLine(QPointF(px1, py1), QPointF(px2, py2))

        vert_stride = 6
        for row_idx in range(len(projected_rows) - 1):
            row_a, row_b = projected_rows[row_idx], projected_rows[row_idx + 1]
            for i in range(0, min(len(row_a), len(row_b)), vert_stride):
                pxa, pya, da = row_a[i]
                pxb, pyb, db = row_b[i]
                avg_depth = (da + db) / 2.0
                line_alpha = int(55 * (0.25 + 0.75 * avg_depth) * face_opacity)
                if line_alpha <= 2:
                    continue
                painter.setPen(QPen(QColor(primary_color.red(), primary_color.green(), primary_color.blue(), line_alpha), 0.6))
                painter.drawLine(QPointF(pxa, pya), QPointF(pxb, pyb))

        # Particle dots at every vertex, drawn on top of the wireframe.
        painter.setPen(Qt.NoPen)
        for proj_row in projected_rows:
            for px, py, depth in proj_row:
                brightness = 0.16 + 0.84 * depth
                dot_size = base_size * (0.45 + 0.9 * depth)
                alpha = int(255 * brightness * face_opacity)
                painter.setBrush(QBrush(QColor(
                    min(255, primary_color.red() + int(40 * depth)),
                    min(255, primary_color.green() + int(20 * depth)),
                    primary_color.blue(),
                    alpha,
                )))
                painter.drawEllipse(QPointF(px, py), dot_size, dot_size)

        # -------------------------------------------------------------
        # 5. Holographic Vertical Scanline Beam
        # -------------------------------------------------------------
        scan_y = face_rect.top() + (face_rect.height() * self._scanline_phase)
        scan_grad = QLinearGradient(face_rect.left(), scan_y, face_rect.right(), scan_y)
        scan_grad.setColorAt(0.0, QColor(0, 0, 0, 0))
        scan_grad.setColorAt(0.2, QColor(primary_color.red(), primary_color.green(), primary_color.blue(), int(90 * glow_mult)))
        scan_grad.setColorAt(0.5, QColor(255, 255, 255, int(180 * glow_mult)))
        scan_grad.setColorAt(0.8, QColor(primary_color.red(), primary_color.green(), primary_color.blue(), int(90 * glow_mult)))
        scan_grad.setColorAt(1.0, QColor(0, 0, 0, 0))

        scan_pen = QPen(QBrush(scan_grad), 1.5)
        painter.setPen(scan_pen)
        painter.drawLine(QPointF(face_rect.left() + 15, scan_y), QPointF(face_rect.right() - 15, scan_y))

        # -------------------------------------------------------------
        # 6. Central Holographic Typography (Below Face)
        # -------------------------------------------------------------
        # Anchored off the bust's actual lowest point (shoulders), not just
        # the face/chin — otherwise the shoulders visibly overlap this text.
        text_y = center_y + self._bust_max_y * height_scale + 6

        # Title: 'JARVIS'
        font_jarvis = QFont(theme.FONT_DISPLAY, 14, QFont.Bold)
        font_jarvis.setLetterSpacing(QFont.AbsoluteSpacing, 4.0)
        painter.setFont(font_jarvis)

        # Glow shadow
        painter.setPen(QPen(QColor(primary_color.red(), primary_color.green(), primary_color.blue(), int(160 * glow_mult))))
        title_rect = QRectF(center_x - 140, text_y, 280, 24)
        painter.drawText(title_rect.adjusted(0, 1, 0, 1), Qt.AlignCenter, "JARVIS")

        # Foreground crisp white text
        painter.setPen(QPen(QColor("#ffffff")))
        painter.drawText(title_rect, Qt.AlignCenter, "JARVIS")

        # Subtitle: 'HOW CAN I ASSIST YOU?'
        font_sub = QFont(theme.FONT_FAMILY, 7, QFont.Bold)
        font_sub.setLetterSpacing(QFont.AbsoluteSpacing, 2.0)
        painter.setFont(font_sub)
        sub_color = QColor(primary_color.red(), primary_color.green(), primary_color.blue(), int(210 * min(1.0, glow_mult)))
        painter.setPen(QPen(sub_color))
        sub_rect = QRectF(center_x - 160, text_y + 24, 320, 16)
        painter.drawText(sub_rect, Qt.AlignCenter, "HOW CAN I ASSIST YOU?")

        # -------------------------------------------------------------
        # 7. Left Flanking HUD Telemetry
        # -------------------------------------------------------------
        left_items = ["LISTENING", "THINKING", "ANALYZING", "EXECUTING"]
        left_x = max(16.0, face_rect.left() - 125)
        left_y_start = center_y - 46

        font_hud = QFont(theme.FONT_DISPLAY, 7, QFont.Bold)
        font_hud.setLetterSpacing(QFont.AbsoluteSpacing, 1.2)
        painter.setFont(font_hud)

        for i, item in enumerate(left_items):
            iy = left_y_start + i * 22
            is_active = (
                (item == "LISTENING" and self.state == AICoreState.LISTENING) or
                (item == "THINKING" and self.state == AICoreState.THINKING) or
                (item in ("ANALYZING", "EXECUTING") and self.state == AICoreState.PROCESSING)
            )

            # Active glowing indicator
            if is_active:
                color = primary_color
                painter.setPen(QPen(color))
                # Active cyan pill marker
                painter.setBrush(QBrush(color))
                painter.drawEllipse(QPointF(left_x + 92, iy + 6), 2.5, 2.5)
            else:
                color = QColor(100, 125, 155, 170)
                painter.setPen(QPen(color))
                # Subtle inactive dash
                painter.setPen(QPen(QColor(60, 85, 115, 120), 1.0))
                painter.drawLine(QPointF(left_x + 88, iy + 6), QPointF(left_x + 94, iy + 6))
                painter.setPen(QPen(color))

            painter.drawText(QRectF(left_x, iy, 85, 16), Qt.AlignRight | Qt.AlignVCenter, item)

        # -------------------------------------------------------------
        # 8. Right Flanking HUD Telemetry
        # -------------------------------------------------------------
        right_items = ["INTELLIGENCE", "ASSISTANCE", "AUTOMATION", "ALWAYS ON"]
        right_x = min(w - 120.0, face_rect.right() + 35)
        right_y_start = center_y - 46

        for i, item in enumerate(right_items):
            iy = right_y_start + i * 22
            is_active = (
                (item in ("INTELLIGENCE", "ASSISTANCE") and self.state == AICoreState.SPEAKING) or
                (item == "ALWAYS ON" and self.state != AICoreState.OFFLINE)
            )

            if is_active:
                color = QColor(0, 255, 157) if item == "ALWAYS ON" else primary_color
                painter.setPen(QPen(color))
                # Active glowing marker
                painter.setBrush(QBrush(color))
                painter.drawEllipse(QPointF(right_x - 8, iy + 6), 2.5, 2.5)
            else:
                color = QColor(100, 125, 155, 170)
                painter.setPen(QPen(color))
                # Subtle inactive dash
                painter.setPen(QPen(QColor(60, 85, 115, 120), 1.0))
                painter.drawLine(QPointF(right_x - 10, iy + 6), QPointF(right_x - 4, iy + 6))
                painter.setPen(QPen(color))

            painter.drawText(QRectF(right_x, iy, 110, 16), Qt.AlignLeft | Qt.AlignVCenter, item)

        # -------------------------------------------------------------
        # 9. Corner HUD Targeting Brackets — frames the whole widget like a
        # sci-fi "locked on" viewport, echoing the rings around the face.
        # -------------------------------------------------------------
        margin = 10.0
        arm = 22.0
        bracket_color = QColor(primary_color.red(), primary_color.green(), primary_color.blue(), int(150 * glow_mult))
        bracket_pen = QPen(bracket_color, 2.0)
        bracket_pen.setCapStyle(Qt.FlatCap)
        painter.setPen(bracket_pen)
        corners = [
            (margin, margin, 1, 1),               # top-left
            (w - margin, margin, -1, 1),           # top-right
            (margin, h - margin, 1, -1),           # bottom-left
            (w - margin, h - margin, -1, -1),      # bottom-right
        ]
        for cx, cy, dx, dy in corners:
            painter.drawLine(QPointF(cx, cy), QPointF(cx + arm * dx, cy))
            painter.drawLine(QPointF(cx, cy), QPointF(cx, cy + arm * dy))
