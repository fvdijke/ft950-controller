"""FT-950 Controller — herbruikbare widgets.

Bevat:
  • VfdDisplay      — VFD-stijl frequentie/tekst display
  • LedButton       — drukknop met ingebouwde LED-indicator
  • RadioKnob       — draaiknop (klik = increment/decrement)
  • SmeterBar       — horizontale S-meter balk
  • SectionFrame    — gelabeld kader voor een groep knoppen
"""

import math

from PySide6.QtCore    import Qt, Signal, QSize
from PySide6.QtGui     import (QPainter, QColor, QFont, QPen,
                               QLinearGradient, QFontMetrics)
from PySide6.QtWidgets import (QWidget, QLabel, QFrame, QVBoxLayout,
                               QHBoxLayout, QSizePolicy, QPushButton)

from .theme import (BG_DISPLAY, VFD_BRIGHT, VFD_DIM, VFD_AMBER, VFD_OFF,
                    LED_GREEN, LED_RED, LED_ORANGE, LED_OFF,
                    BTN_NORMAL, BTN_HOVER, BG_SURFACE, BORDER,
                    TEXT_H1, TEXT_DIM, GROUP_BORDER, ACCENT)


# ── VFD Display ───────────────────────────────────────────────────────────────

class VfdDisplay(QWidget):
    """
    Interactieve VFD-frequentieweergave.

    • Klik op een digit → selecteer die digit (highlight in amber)
    • Scroll met muiswiel → increment/decrement de geselecteerde digit
    • sig_freq_changed wordt geëmit bij elke frequentiewijziging

    Formaat: "14.195.000" (10 tekens: 2 MHz . 3 kHz . 3 Hz)
    """

    sig_freq_changed = Signal(int)   # nieuwe frequentie in Hz

    # Stap in Hz per karakter-index in "14.195.000"
    _DIGIT_STEPS = [10_000_000, 1_000_000, None,
                    100_000, 10_000, 1_000, None,
                    100, 10, 1]

    _STEP_LABELS = {
        10_000_000: "10 MHz", 1_000_000: "1 MHz",
        100_000: "100 kHz", 10_000: "10 kHz", 1_000: "1 kHz",
        100: "100 Hz", 10: "10 Hz", 1: "1 Hz",
    }

    def __init__(self, parent=None, font_size=44):
        super().__init__(parent)
        self._freq_hz       = 14_195_000
        self._font_sz       = font_size
        self._selected_char = 5          # default: 1 kHz digit
        self._hovered       = False      # muis zweeft erover
        self._mode          = "USB"

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet(f"background:{BG_DISPLAY}; border-radius:4px;")
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.WheelFocus)
        self.setMouseTracking(True)

        fm = QFontMetrics(QFont("Consolas", font_size, QFont.Bold))
        self.setMinimumHeight(fm.height() + 32)

    # ── Publiek ───────────────────────────────────────────────────────────────

    def set_freq(self, hz: int):
        self._freq_hz = max(30_000, min(56_000_000, int(hz)))
        self.update()

    def get_current_step(self) -> int:
        step = self._DIGIT_STEPS[self._selected_char]
        return step if step is not None else 1_000

    def increment(self, delta: int):
        """Verhoog/verlaag frequentie met delta × huidige stap."""
        step    = self.get_current_step()
        new_hz  = max(30_000, min(56_000_000, self._freq_hz + delta * step))
        self._freq_hz = new_hz
        self.update()
        self.sig_freq_changed.emit(new_hz)

    def set_mode(self, mode: str):
        self._mode = mode
        self.update()

    # ── Muis-events ───────────────────────────────────────────────────────────

    def enterEvent(self, event):
        self._hovered = True
        self.update()

    def leaveEvent(self, event):
        self._hovered = False
        self.update()

    def mouseMoveEvent(self, event):
        if not self._hovered:
            return
        x_start, char_w = self._string_start_and_charwidth()
        rel = event.position().x() - x_start
        if rel >= 0:
            idx = int(rel // char_w)
            if 0 <= idx < len(self._DIGIT_STEPS) and self._DIGIT_STEPS[idx] is not None:
                if idx != self._selected_char:
                    self._selected_char = idx
                    self.update()

    def mousePressEvent(self, event):
        if not self._hovered:
            return
        if event.button() == Qt.LeftButton:
            x = event.position().x()
            x_start, char_w = self._string_start_and_charwidth()
            rel   = x - x_start
            if rel >= 0:
                idx = int(rel // char_w)
                if 0 <= idx < len(self._DIGIT_STEPS):
                    if self._DIGIT_STEPS[idx] is not None:
                        self._selected_char = idx
                        self.update()

    def wheelEvent(self, event):
        if not self._hovered:
            event.ignore()
            return
        delta = 1 if event.angleDelta().y() > 0 else -1
        self.increment(delta)
        event.accept()

    # ── Hulp-methoden ─────────────────────────────────────────────────────────

    def _freq_str(self) -> str:
        hz   = self._freq_hz
        mhz  = hz // 1_000_000
        khz  = (hz % 1_000_000) // 1_000
        hz_r = hz % 1_000
        return f"{mhz:2d}.{khz:03d}.{hz_r:03d}"

    def _string_start_and_charwidth(self) -> tuple[int, int]:
        freq_font = QFont("Consolas", self._font_sz, QFont.Bold)
        freq_fm   = QFontMetrics(freq_font)
        freq_w    = freq_fm.horizontalAdvance(self._freq_str())
        char_w    = freq_fm.horizontalAdvance("0")
        aux_font  = QFont("Consolas", max(9, int(self._font_sz * 0.4)), QFont.Bold)
        aux_fm    = QFontMetrics(aux_font)
        mode_w    = aux_fm.horizontalAdvance(self._mode) + 12 if self._mode else 0
        kHz_w     = aux_fm.horizontalAdvance("kHz") + 8
        total_w   = mode_w + freq_w + kHz_w
        freq_x    = (self.width() - total_w) // 2 + mode_w
        return freq_x, char_w

    # ── Tekenen ───────────────────────────────────────────────────────────────

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        # ── Achtergrond ───────────────────────────────────────────────────────
        p.fillRect(self.rect(), QColor(BG_DISPLAY))

        # ── Kader ─────────────────────────────────────────────────────────────
        border_col = QColor(ACCENT if self._hovered else VFD_DIM)
        p.setPen(QPen(border_col, 1))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 4, 4)

        # ── "VFO-A" linksbovenin, snijdt het kader door ───────────────────────
        tag_font = QFont("Segoe UI", 7, QFont.Bold)
        tag_fm   = QFontMetrics(tag_font)
        tag_text = "VFO-A"
        tag_w    = tag_fm.horizontalAdvance(tag_text) + 6
        tag_h    = tag_fm.height()
        p.fillRect(8, 0, tag_w, tag_h, QColor(BG_DISPLAY))
        p.setFont(tag_font)
        p.setPen(border_col)
        p.drawText(10, tag_fm.ascent(), tag_text)

        # ── Metriek ───────────────────────────────────────────────────────────
        freq_font = QFont("Consolas", self._font_sz, QFont.Bold)
        freq_fm   = QFontMetrics(freq_font)
        freq_str  = self._freq_str()
        freq_w    = freq_fm.horizontalAdvance(freq_str)
        char_w    = freq_fm.horizontalAdvance("0")

        aux_sz    = max(9, int(self._font_sz * 0.4))
        aux_font  = QFont("Consolas", aux_sz, QFont.Bold)
        aux_fm    = QFontMetrics(aux_font)

        mode_text = self._mode
        mode_w    = aux_fm.horizontalAdvance(mode_text) + 12 if mode_text else 0
        kHz_w     = aux_fm.horizontalAdvance("kHz")
        kHz_gap   = 8

        total_w  = mode_w + freq_w + kHz_gap + kHz_w
        group_x  = (self.width() - total_w) // 2
        freq_x   = group_x + mode_w
        kHz_x    = freq_x + freq_w + kHz_gap

        content_top = tag_h + 2
        content_h   = self.height() - content_top - 4
        y_base = content_top + (content_h - freq_fm.height()) // 2 + freq_fm.ascent()
        y_base = max(content_top + freq_fm.ascent(), y_base)

        # ── Ghost ─────────────────────────────────────────────────────────────
        p.setFont(freq_font)
        for i, gc in enumerate("88.888.888"):
            p.setPen(QColor(VFD_OFF))
            p.drawText(int(freq_x + i * char_w), y_base, gc)

        # ── Frequentie-digits ─────────────────────────────────────────────────
        for i, c in enumerate(freq_str):
            x = int(freq_x + i * char_w)
            if self._hovered and i == self._selected_char:
                box_top = y_base - freq_fm.ascent()
                p.fillRect(x - 1, box_top, char_w + 2, freq_fm.height(), QColor("#1A1400"))
                p.setPen(QPen(QColor(VFD_AMBER), 1))
                p.drawRect(x - 1, box_top, char_w + 1, freq_fm.height() - 1)
                p.setPen(QColor(VFD_AMBER))
            elif c == '.':
                p.setPen(QColor(VFD_DIM))
            else:
                p.setPen(QColor(VFD_BRIGHT))
            p.drawText(x, y_base, c)

        # ── Mode voor frequentie (amber) ──────────────────────────────────────
        if mode_text:
            p.setFont(aux_font)
            p.setPen(QColor(VFD_AMBER))
            aux_y = content_top + (content_h - aux_fm.height()) // 2 + aux_fm.ascent()
            p.drawText(group_x, aux_y, mode_text)

        # ── kHz na frequentie (dim) ───────────────────────────────────────────
        p.setFont(aux_font)
        p.setPen(QColor(VFD_DIM))
        aux_y = content_top + (content_h - aux_fm.height()) // 2 + aux_fm.ascent()
        p.drawText(kHz_x, aux_y, "kHz")

        p.end()


# ── Afstemknop (round tuning knob) ───────────────────────────────────────────

class TuningKnob(QWidget):
    """
    Ronde afstemknop (nabootsing van de grote draaiknop op de FT-950).

    • Muiswiel draaien → emit sig_turned(+1 of -1)
    • Klik+sleep omhoog/omlaag → idem
    • Verbind met VfdDisplay.increment: knob.sig_turned.connect(vfd.increment)
    """

    sig_turned = Signal(int)   # +1 (omhoog) of -1 (omlaag)

    def __init__(self, size: int = 96, parent=None):
        super().__init__(parent)
        self._sz     = size
        self._angle  = 120.0       # beginpositie wijzer (graden)
        self._drag_y = 0.0
        self.setFixedSize(size, size)
        self.setCursor(Qt.SizeVerCursor)
        self.setToolTip("Scroll of sleep om frequentie af te stemmen\n"
                        "(stap = geselecteerde digit in het display)")

    # ── Events ────────────────────────────────────────────────────────────────

    def wheelEvent(self, event):
        delta = 1 if event.angleDelta().y() > 0 else -1
        self._turn(delta)
        event.accept()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_y = event.position().y()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            dy = self._drag_y - event.position().y()
            self._drag_y = event.position().y()
            steps = int(dy / 3)
            if steps != 0:
                self._turn(steps)

    def _turn(self, steps: int):
        self._angle = (self._angle + steps * 11.25) % 360   # 32 stappen per omwenteling
        self.update()
        self.sig_turned.emit(steps)

    # ── Tekenen ───────────────────────────────────────────────────────────────

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        sz = self._sz
        cx, cy = sz // 2, sz // 2
        r  = sz // 2 - 3

        # ── Schaalticks langs de rand ─────────────────────────────────────────
        for i in range(32):
            a    = math.radians(i * 360 / 32 - 90)
            major = (i % 4 == 0)
            r_out = r
            r_in  = r - (6 if major else 3)
            x1 = int(cx + r_out * math.cos(a))
            y1 = int(cy + r_out * math.sin(a))
            x2 = int(cx + r_in  * math.cos(a))
            y2 = int(cy + r_in  * math.sin(a))
            pen_col = QColor(ACCENT if major else "#484848")
            p.setPen(QPen(pen_col, 2 if major else 1))
            p.drawLine(x1, y1, x2, y2)

        # ── Buitenring ────────────────────────────────────────────────────────
        grad = QLinearGradient(0, 0, sz, sz)
        grad.setColorAt(0.0, QColor("#3C3C3C"))
        grad.setColorAt(1.0, QColor("#181818"))
        p.setBrush(grad)
        p.setPen(QPen(QColor("#555555"), 2))
        p.drawEllipse(cx - r, cy - r, r * 2, r * 2)

        # ── Binnenknop ────────────────────────────────────────────────────────
        r2 = r - 9
        grad2 = QLinearGradient(cx - r2, cy - r2, cx + r2, cy + r2)
        grad2.setColorAt(0.0, QColor("#303030"))
        grad2.setColorAt(0.4, QColor("#212121"))
        grad2.setColorAt(1.0, QColor("#101010"))
        p.setBrush(grad2)
        p.setPen(QPen(QColor(BORDER), 1))
        p.drawEllipse(cx - r2, cy - r2, r2 * 2, r2 * 2)

        # ── Glans-effect (kleine ellips linksboven) ────────────────────────────
        p.setBrush(QColor(255, 255, 255, 18))
        p.setPen(Qt.NoPen)
        p.drawEllipse(cx - r2 + 4, cy - r2 + 3, r2 - 4, (r2 - 4) // 2)

        # ── Pointer (lijn + stip) ─────────────────────────────────────────────
        a   = math.radians(self._angle - 90)
        r_p = r2 - 5
        px  = cx + r_p * math.cos(a)
        py  = cy + r_p * math.sin(a)

        p.setPen(QPen(QColor(VFD_BRIGHT), 2))
        p.drawLine(cx, cy, int(px), int(py))

        p.setBrush(QColor(VFD_BRIGHT))
        p.setPen(Qt.NoPen)
        p.drawEllipse(int(px) - 4, int(py) - 4, 8, 8)

        p.end()


# ── Small VFD (voor VFO-B / clarifier) ───────────────────────────────────────

class SmallVfd(QWidget):
    """
    Compacte interactieve frequentieweergave voor VFO-B.

    • Klik op een digit → selecteer (amber onderstreept)
    • Scrollwiel → afstemmen op geselecteerde stap
    • sig_freq_changed wordt geëmit bij elke wijziging (alleen als interactive=True)
    """

    sig_freq_changed = Signal(int)

    _DIGIT_STEPS = [10_000_000, 1_000_000, None,
                    100_000, 10_000, 1_000, None,
                    100, 10, 1]

    def __init__(self, label="VFO-B", interactive: bool = False,
                 font_size: int = 14, parent=None):
        super().__init__(parent)
        self._label       = label
        self._freq_hz     = 0
        self._color       = VFD_DIM
        self._interactive = interactive
        self._selected    = 5        # standaard 1 kHz digit
        self._hovered     = False
        self._font_sz     = font_size
        self._mode        = ""
        h = max(44, font_size * 2 + 22)
        self.setFixedHeight(h)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setStyleSheet(f"background:{BG_DISPLAY};")
        if interactive:
            self.setCursor(Qt.PointingHandCursor)
            self.setFocusPolicy(Qt.WheelFocus)
            self.setMouseTracking(True)

    def set_freq(self, hz: int, color: str | None = None):
        self._freq_hz = max(0, int(hz))
        if color:
            self._color = color
        self.update()

    def set_font_size(self, pt: int):
        self._font_sz = max(8, min(28, pt))
        h = max(44, self._font_sz * 2 + 22)
        self.setFixedHeight(h)
        self.update()

    def set_mode(self, mode: str):
        self._mode = mode
        self.update()

    def _freq_str(self) -> str:
        hz = self._freq_hz
        if hz == 0:
            return "--.--.---"
        mhz = hz // 1_000_000
        khz = (hz % 1_000_000) // 1_000
        hzr = hz % 1_000
        return f"{mhz:2d}.{khz:03d}.{hzr:03d}"

    def _char_metrics(self):
        freq_font = QFont("Consolas", self._font_sz, QFont.Bold)
        freq_fm   = QFontMetrics(freq_font)
        freq_w    = freq_fm.horizontalAdvance(self._freq_str())
        cw        = freq_fm.horizontalAdvance("0")
        aux_sz    = max(6, int(self._font_sz * 0.6))
        aux_fm    = QFontMetrics(QFont("Consolas", aux_sz, QFont.Bold))
        mode_w    = aux_fm.horizontalAdvance(self._mode) + 8 if self._mode else 0
        kHz_w     = aux_fm.horizontalAdvance("kHz") + 6
        total_w   = mode_w + freq_w + kHz_w
        freq_x    = (self.width() - total_w) // 2 + mode_w
        return freq_font, freq_fm, freq_x, cw

    def enterEvent(self, event):
        if self._interactive:
            self._hovered = True
            self.update()

    def leaveEvent(self, event):
        if self._interactive:
            self._hovered = False
            self.update()

    def mouseMoveEvent(self, event):
        if not self._interactive or not self._hovered:
            return
        _, _, x0, cw = self._char_metrics()
        rel = event.position().x() - x0
        if rel >= 0:
            idx = int(rel // cw)
            if 0 <= idx < len(self._DIGIT_STEPS) and self._DIGIT_STEPS[idx] is not None:
                if idx != self._selected:
                    self._selected = idx
                    self.update()

    def mousePressEvent(self, event):
        if not self._interactive or not self._hovered:
            return
        if event.button() != Qt.LeftButton:
            return
        _, _, x0, cw = self._char_metrics()
        rel = event.position().x() - x0
        if rel >= 0:
            idx = int(rel // cw)
            if 0 <= idx < len(self._DIGIT_STEPS) and self._DIGIT_STEPS[idx] is not None:
                self._selected = idx
                self.update()

    def wheelEvent(self, event):
        if not self._interactive or not self._hovered or self._freq_hz == 0:
            event.ignore()
            return
        step  = self._DIGIT_STEPS[self._selected] or 1_000
        delta = 1 if event.angleDelta().y() > 0 else -1
        new   = max(30_000, min(56_000_000, self._freq_hz + delta * step))
        self._freq_hz = new
        self.update()
        self.sig_freq_changed.emit(new)
        event.accept()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor(BG_DISPLAY))

        # ── Kader ─────────────────────────────────────────────────────────────
        border_col = QColor(ACCENT if (self._interactive and self._hovered) else VFD_DIM)
        p.setPen(QPen(border_col, 1))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 3, 3)

        # ── Label linksbovenin, snijdt het kader door ────────────────────────
        tag_font = QFont("Segoe UI", 6, QFont.Bold)
        tag_fm   = QFontMetrics(tag_font)
        tag_w    = tag_fm.horizontalAdvance(self._label) + 6
        tag_h    = tag_fm.height()
        p.fillRect(6, 0, tag_w, tag_h, QColor(BG_DISPLAY))
        p.setFont(tag_font)
        p.setPen(border_col)
        p.drawText(8, tag_fm.ascent(), self._label)

        # ── Metriek ───────────────────────────────────────────────────────────
        freq_font, freq_fm, freq_x, cw = self._char_metrics()
        freq_str  = self._freq_str()
        freq_w    = freq_fm.horizontalAdvance(freq_str)

        aux_sz    = max(6, int(self._font_sz * 0.6))
        aux_font  = QFont("Consolas", aux_sz, QFont.Bold)
        aux_fm    = QFontMetrics(aux_font)

        mode_text = self._mode
        mode_w    = aux_fm.horizontalAdvance(mode_text) + 8 if mode_text else 0
        kHz_gap   = 6
        kHz_x     = freq_x + freq_w + kHz_gap
        group_x   = freq_x - mode_w

        content_top = tag_h + 1
        content_h   = self.height() - content_top - 3
        y_base = content_top + (content_h - freq_fm.height()) // 2 + freq_fm.ascent()
        y_base = max(content_top + freq_fm.ascent(), y_base)

        # ── Ghost ─────────────────────────────────────────────────────────────
        p.setFont(freq_font)
        for i, gc in enumerate("88.888.888"):
            p.setPen(QColor(VFD_OFF))
            p.drawText(int(freq_x + i * cw), y_base, gc)

        # ── Frequentie-digits ─────────────────────────────────────────────────
        hovering = self._interactive and self._hovered and self._freq_hz > 0
        for i, c in enumerate(freq_str):
            x = int(freq_x + i * cw)
            if hovering and i == self._selected:
                box_top = y_base - freq_fm.ascent()
                p.fillRect(x, box_top, int(cw), freq_fm.height(), QColor(ACCENT + "33"))
                p.setPen(QColor(ACCENT))
            elif c == '.':
                p.setPen(QColor(VFD_OFF))
            else:
                p.setPen(QColor(VFD_DIM))
            p.drawText(x, y_base, c)

        # ── Mode voor frequentie (amber) ──────────────────────────────────────
        if mode_text:
            p.setFont(aux_font)
            p.setPen(QColor(VFD_AMBER))
            aux_y = content_top + (content_h - aux_fm.height()) // 2 + aux_fm.ascent()
            p.drawText(group_x, aux_y, mode_text)

        # ── kHz na frequentie (dim) ───────────────────────────────────────────
        p.setFont(aux_font)
        p.setPen(QColor(VFD_DIM))
        aux_y = content_top + (content_h - aux_fm.height()) // 2 + aux_fm.ascent()
        p.drawText(kHz_x, aux_y, "kHz")

        p.end()


# ── LED-drukknop ─────────────────────────────────────────────────────────────

class LedButton(QPushButton):
    """
    Drukknop met een kleine LED-indicator (links van de tekst).

    led_color  : kleur als actief (standaard LED_GREEN)
    checkable  : True = toggle-knop; False = momentary
    """

    def __init__(self, text: str, led_color: str = LED_GREEN,
                 checkable: bool = True, small: bool = False, parent=None):
        super().__init__(parent)
        self._led_color = led_color
        self._small     = small
        self.setCheckable(checkable)
        self.setText(text)

        fs   = 7 if small else 8
        pad  = "2px 6px" if small else "3px 8px"
        self.setStyleSheet(f"""
            QPushButton {{
                background: {BTN_NORMAL};
                color: {TEXT_H1};
                border: 1px solid {BORDER};
                border-radius: 2px;
                padding: {pad};
                font-size: {fs}pt;
                text-align: left;
                padding-left: 14px;
            }}
            QPushButton:hover {{
                background: {BTN_HOVER};
                border-color: {ACCENT};
            }}
            QPushButton:checked {{
                background: #1A2A1A;
                border-color: {led_color};
            }}
            QPushButton:pressed {{
                background: #111;
            }}
        """)

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = 5 if not self._small else 4
        x = 5
        y = (self.height() - r * 2) // 2

        if self.isChecked():
            p.setBrush(QColor(self._led_color))
            p.setPen(QPen(QColor(self._led_color).darker(150), 1))
        else:
            p.setBrush(QColor(LED_OFF))
            p.setPen(QPen(QColor(BORDER), 1))

        p.drawEllipse(x, y, r * 2, r * 2)
        p.end()


# ── Knop zonder LED ───────────────────────────────────────────────────────────

class RadioButton(QPushButton):
    """Gewone drukknop in radiostijl, optioneel checkable."""

    def __init__(self, text: str, checkable: bool = False,
                 small: bool = False, parent=None):
        super().__init__(text, parent)
        self.setCheckable(checkable)
        fs  = 7 if small else 8
        pad = "2px 6px" if small else "3px 8px"
        self.setStyleSheet(f"""
            QPushButton {{
                background: {BTN_NORMAL};
                color: {TEXT_H1};
                border: 1px solid {BORDER};
                border-radius: 2px;
                padding: {pad};
                font-size: {fs}pt;
            }}
            QPushButton:hover  {{ background: {BTN_HOVER}; border-color: {ACCENT}; }}
            QPushButton:checked {{ background: #1A2A1A; border-color: {LED_GREEN}; color: #7FFF7F; }}
            QPushButton:pressed {{ background: #111; }}
        """)


# ── S-meter balk met schaalverdeling ─────────────────────────────────────────

class SMeterBar(QWidget):
    """
    Horizontale S-meter met schaalverdeling (S1 S3 S5 S7 S9 +20 +40 +60 dB).

    Conform de FT-950 display (manual p.24):
      "S  1  3  5  7  9 +20 +40 +60dB"

    Ruwe waarde 0-255:
      S1≈18  S3≈54  S5≈90  S7≈126  S9≈162
      +20dB≈189  +40dB≈216  +60dB≈243
    (6 dB per S-unit, +20/+40/+60 boven S9)
    """

    # Standaard marks — labels en kleuren (vast); raw-waarden instelbaar
    _MARK_LABELS = ["1", "3", "5", "7", "9", "+20", "+40", "+60"]
    _MARK_COLORS = ["#00BB44","#00BB44","#66CC00","#AACC00",
                    "#FFCC00","#FF8800","#FF4400","#FF2020"]
    _DEFAULT_RAW  = [18, 54, 90, 126, 162, 189, 216, 243]

    def __init__(self, label="S", parent=None):
        super().__init__(parent)
        self._value     = 0
        self._label     = label
        self._raw_cal   = list(self._DEFAULT_RAW)   # kalibreerbare waarden
        self.setFixedHeight(28)
        self.setMaximumHeight(28)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set_calibration(self, raw_values: list):
        """Pas kalibratie toe: lijst van 8 ruwe waarden voor S1..+60dB."""
        if len(raw_values) == 8:
            self._raw_cal = [max(0, min(255, int(v))) for v in raw_values]
            self.update()

    def get_calibration(self) -> list:
        return list(self._raw_cal)

    @property
    def _MARKS(self):
        return [(self._raw_cal[i], self._MARK_LABELS[i], self._MARK_COLORS[i])
                for i in range(8)]

    # Blokstijl: eerste 5 = amber (S1-S9), laatste 3 = rood (+20/+40/+60)
    _BLOCK_ON_AMBER  = "#FFAA00"
    _BLOCK_ON_RED    = "#FF2020"
    _BLOCK_OFF       = "#1A1008"    # donker amber-uit voor S-blokjes
    _BLOCK_OFF_RED   = "#1A0808"    # donker rood-uit voor +dB-blokjes
    _BLOCK_GAP       = 2            # pixels tussen blokjes

    def set_value(self, v: int):
        self._value = max(0, min(255, v))
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, False)
        w, h = self.width(), self.height()

        N       = 8                  # aantal blokjes = aantal kalibratiepunten
        LBL_W   = 14                 # "S" label links
        LBL_H   = 10                 # hoogte labels boven blokjes
        GAP     = self._BLOCK_GAP
        blk_w   = max(6, (w - LBL_W - GAP * (N - 1)) // N)
        blk_h   = max(4, (h - LBL_H - 4) // 3)
        blk_y   = LBL_H + 2

        # Totale breedte van alle blokjes + gaten
        total_w = N * blk_w + (N - 1) * GAP
        x0      = LBL_W + max(0, (w - LBL_W - total_w) // 2)

        p.fillRect(0, 0, w, h, QColor("#080808"))

        # "S" label links
        lbl_font = QFont("Consolas", 6)
        p.setFont(lbl_font)
        lfm = QFontMetrics(lbl_font)
        p.setPen(QColor(VFD_DIM))
        p.drawText(2, lfm.ascent(), self._label)

        marks = self._MARKS   # [(raw, label, color), ...]

        for i, (raw, lbl, _) in enumerate(marks):
            bx = x0 + i * (blk_w + GAP)

            # Is dit blokje actief?
            active = self._value >= raw
            is_red = i >= 5    # +20/+40/+60

            # Kies kleur
            if active:
                col = QColor(self._BLOCK_ON_RED if is_red else self._BLOCK_ON_AMBER)
                # Glans: lichtere bovenrand
                glow = col.lighter(130)
            else:
                col  = QColor(self._BLOCK_OFF_RED if is_red else self._BLOCK_OFF)
                glow = col

            # Vul blokje
            p.fillRect(bx, blk_y, blk_w, blk_h, col)

            # Glansstreepje bovenaan
            if active:
                p.setPen(QPen(glow, 1))
                p.drawLine(bx + 1, blk_y + 1, bx + blk_w - 2, blk_y + 1)

            # Rand
            border_col = col.lighter(150) if active else QColor(BORDER)
            p.setPen(QPen(border_col, 1))
            p.drawRect(bx, blk_y, blk_w - 1, blk_h - 1)

            # Label boven blokje (gecentreerd)
            p.setPen(QColor(self._BLOCK_ON_RED if is_red else self._BLOCK_ON_AMBER)
                     if active else QColor(TEXT_DIM))
            lw = lfm.horizontalAdvance(lbl)
            tx = bx + (blk_w - lw) // 2
            p.drawText(tx, lfm.ascent(), lbl)

        p.end()


# ── TX-meter balk (SMeterBar-stijl met schaalverdeling) ──────────────────────

class TxMeterBar(QWidget):
    """
    TX-meter met schaalverdeling, identiek van stijl aan SMeterBar.

    Layout (van boven naar beneden):
      label  tik  tik  tik  tik   ← schaalmarkeringen + ticks
      ████████████████░░░░░░░░░   ← gradient balk
      waarde-tekst rechts

    marks: lijst van (raw_0-255, label_str, kleur_str)
    """

    def __init__(self, label: str,
                 marks: list[tuple[int, str, str]],
                 parent=None):
        super().__init__(parent)
        self._label    = label
        self._marks    = marks    # [(raw, lbl, color), ...]
        self._raw      = 0
        self._val_text = "—"
        self.setFixedHeight(38)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set_value(self, raw: int, text: str = ""):
        self._raw      = max(0, min(255, int(raw)))
        self._val_text = text if text else ("—" if raw == 0 else str(raw))
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, False)
        w, h = self.width(), self.height()

        LBL_W  = 38    # label links
        VAL_W  = 50    # waarde rechts
        bar_x  = LBL_W
        bar_w  = w - LBL_W - VAL_W
        TICK_H = 4
        LBL_H  = 10    # hoogte boven de balk voor scale-labels
        BAR_H  = 14    # balk-hoogte
        bar_y  = LBL_H + TICK_H + 2
        # Zorg dat alles past
        if bar_y + BAR_H > h - 4:
            bar_y = h - BAR_H - 4

        p.fillRect(0, 0, w, h, QColor("#080808"))

        # ── Schaalmarkeringen ────────────────────────────────────────────────
        scale_font = QFont("Consolas", 6)
        p.setFont(scale_font)
        sfm = QFontMetrics(scale_font)

        for raw, lbl, col in self._marks:
            x = bar_x + int(bar_w * raw / 255)
            p.setPen(QColor(col))
            # tick
            p.drawLine(x, LBL_H + 1, x, LBL_H + TICK_H)
            # label (gecentreerd boven tick)
            lw = sfm.horizontalAdvance(lbl)
            p.drawText(x - lw // 2, sfm.ascent(), lbl)

        # ── Label links ──────────────────────────────────────────────────────
        p.setPen(QColor(TEXT_DIM))
        p.setFont(QFont("Consolas", 7, QFont.Bold))
        llfm = QFontMetrics(p.font())
        p.drawText(2, bar_y + (BAR_H + llfm.ascent()) // 2, self._label)

        # ── Balk ─────────────────────────────────────────────────────────────
        p.fillRect(bar_x, bar_y, bar_w, BAR_H, QColor("#101010"))
        p.setPen(QColor(BORDER))
        p.drawRect(bar_x, bar_y, bar_w - 1, BAR_H - 1)

        if self._raw > 0:
            fill_w = max(2, int(bar_w * self._raw / 255))
            # Kleurverloop bepaald door de markeringen
            grad = QLinearGradient(bar_x, 0, bar_x + bar_w, 0)
            if self._marks:
                for raw_m, _, col_m in self._marks:
                    pos = raw_m / 255.0
                    grad.setColorAt(min(1.0, pos), QColor(col_m))
            else:
                grad.setColorAt(0.0, QColor("#00BB44"))
                grad.setColorAt(1.0, QColor("#FF2020"))
            p.fillRect(bar_x + 1, bar_y + 1, fill_w - 1, BAR_H - 2, grad)

            # Witte naald
            p.setPen(QPen(QColor("#FFFFFF"), 1))
            nx = bar_x + fill_w
            p.drawLine(nx, bar_y + 1, nx, bar_y + BAR_H - 2)

        # ── Waarde rechts ────────────────────────────────────────────────────
        val_font = QFont("Consolas", 7)
        p.setFont(val_font)
        vfm = QFontMetrics(val_font)
        p.setPen(QColor(VFD_BRIGHT if self._raw > 0 else TEXT_DIM))
        vx = w - VAL_W + (VAL_W - vfm.horizontalAdvance(self._val_text)) // 2
        p.drawText(vx, bar_y + (BAR_H + vfm.ascent()) // 2, self._val_text)

        p.setPen(QColor(BORDER))
        p.drawRect(0, 0, w - 1, h - 1)
        p.end()


# ── Sectie-kader ─────────────────────────────────────────────────────────────

class SectionFrame(QFrame):
    """Gelabeld kader voor een groep knoppen (zoals op de echte radio)."""

    def __init__(self, title: str = "", parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Box)
        self.setStyleSheet(f"""
            QFrame {{
                border: 1px solid {GROUP_BORDER};
                border-radius: 3px;
                background: transparent;
                margin-top: 6px;
            }}
        """)
        self._title = title
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(6, 8, 6, 6)
        self._layout.setSpacing(4)

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self._title:
            return
        p = QPainter(self)
        font = QFont("Segoe UI", 6)
        p.setFont(font)
        p.setPen(QColor(TEXT_DIM))
        fm = QFontMetrics(font)
        tw = fm.horizontalAdvance(self._title)
        p.fillRect(8, 0, tw + 4, fm.height(), QColor("#1C1C1C"))
        p.drawText(10, fm.ascent(), self._title)
        p.end()

    def body(self) -> QVBoxLayout:
        return self._layout


# ── Mode-indicator label ──────────────────────────────────────────────────────

class ModeLabel(QLabel):
    """Grote modus-indicator (LSB, USB, CW, enz.) in VFD-stijl."""

    def __init__(self, parent=None):
        super().__init__("USB", parent)
        self.setStyleSheet(f"""
            QLabel {{
                background: {BG_DISPLAY};
                color: {VFD_AMBER};
                font-family: Consolas;
                font-size: 16pt;
                font-weight: bold;
                padding: 2px 6px;
                border-radius: 2px;
            }}
        """)
        self.setAlignment(Qt.AlignCenter)
        self.setFixedWidth(80)


# ── Kleine status-badge ───────────────────────────────────────────────────────

class StatusBadge(QLabel):
    """Klein statusbadge (TX/RX/SPLIT/NAR enz.)."""

    def __init__(self, text: str, active_color: str = LED_GREEN, parent=None):
        super().__init__(text, parent)
        self._active_color = active_color
        self._active = False
        self._update_style()
        self.setAlignment(Qt.AlignCenter)
        font = QFont("Consolas", 7, QFont.Bold)
        self.setFont(font)
        self.setFixedSize(34, 15)

    def set_active(self, on: bool):
        self._active = on
        self._update_style()

    def _update_style(self):
        if self._active:
            self.setStyleSheet(f"""
                QLabel {{
                    background: {self._active_color};
                    color: #000;
                    border-radius: 2px;
                    font-size: 7pt;
                    font-weight: bold;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QLabel {{
                    background: {LED_OFF};
                    color: {TEXT_DIM};
                    border-radius: 2px;
                    font-size: 7pt;
                }}
            """)
