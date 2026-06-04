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


# ── Beschikbare VFD-fonts (instelbaar via weergave-instellingen) ──────────────

VFD_FONTS = [
    "OCR A Extended", "Consolas", "Cascadia Mono", "Inconsolata",
    "Roboto Mono", "Fira Mono", "Ubuntu Mono", "Courier New", "Lucida Console",
]


# ── VFD Display ───────────────────────────────────────────────────────────────

class VfdDisplay(QWidget):
    """
    Interactieve VFD-frequentieweergave met configureerbaar font.

    • Klik / hover op een digit → selecteer die digit (highlight in amber)
    • Scrollwiel → increment/decrement de geselecteerde digit
    • Rechtsklik op mode-label → mode selecteren (alleen VFO-B SmallVfd)
    """

    sig_freq_changed = Signal(int)

    _DIGIT_STEPS = [10_000_000, 1_000_000, None,
                    100_000, 10_000, 1_000, None,
                    100, 10, 1]

    def __init__(self, parent=None, font_size=34, font_name="Consolas"):
        super().__init__(parent)
        self._freq_hz       = 14_195_000
        self._font_sz       = font_size
        self._font_name     = font_name
        self._font_style    = "Bold Italic"
        self._selected_char = 5
        self._hovered       = False
        self._mode          = "USB"

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet(f"background:{BG_DISPLAY}; border-radius:4px;")
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.WheelFocus)
        self.setMouseTracking(True)
        self._update_min_height()

    # ── Publiek ───────────────────────────────────────────────────────────────

    def _update_min_height(self):
        fm = QFontMetrics(QFont(self._font_name, self._font_sz, QFont.Bold))
        self.setMinimumHeight(fm.height() + 32)

    def set_freq(self, hz: int):
        self._freq_hz = max(30_000, min(56_000_000, int(hz)))
        self.update()

    def set_font_name(self, name: str):
        self._font_name = name
        self._update_min_height()
        self.update()

    def set_font_style(self, style: str):
        self._font_style = style
        self.update()

    def get_current_step(self) -> int:
        step = self._DIGIT_STEPS[self._selected_char]
        return step if step is not None else 1_000

    def increment(self, delta: int):
        step   = self.get_current_step()
        new_hz = max(30_000, min(56_000_000, self._freq_hz + delta * step))
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
        idx = self._hit_digit_idx(int(event.position().x()))
        if idx is not None and idx != self._selected_char:
            self._selected_char = idx
            self.update()

    def mousePressEvent(self, event):
        if not self._hovered or event.button() != Qt.LeftButton:
            return
        idx = self._hit_digit_idx(int(event.position().x()))
        if idx is not None:
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

    def _make_freq_font(self) -> QFont:
        bold   = "Bold"   in self._font_style
        italic = "Italic" in self._font_style
        f = QFont(self._font_name, self._font_sz,
                  QFont.Bold if bold else QFont.Normal)
        f.setItalic(italic)
        return f

    def _compute_layout(self) -> dict:
        freq_font = self._make_freq_font()
        freq_fm   = QFontMetrics(freq_font)
        char_w    = freq_fm.horizontalAdvance("0")   # monospace slot

        freq_str     = self._freq_str()
        offsets      = [i * char_w for i in range(len(freq_str))]
        freq_total_w = len(freq_str) * char_w

        aux_sz   = max(9, int(self._font_sz * 0.42))
        aux_font = QFont("Segoe UI", aux_sz, QFont.Bold)
        aux_fm   = QFontMetrics(aux_font)

        mode_text = self._mode
        mode_w    = aux_fm.horizontalAdvance(mode_text) + 10 if mode_text else 0
        kHz_w     = aux_fm.horizontalAdvance("kHz")

        total_w = mode_w + freq_total_w + 8 + kHz_w
        group_x = (self.width() - total_w) // 2
        freq_x  = group_x + mode_w

        tag_fm  = QFontMetrics(QFont("Segoe UI", 7, QFont.Bold))
        c_top   = tag_fm.height() + 2
        c_h     = self.height() - c_top - 4
        y_base  = c_top + (c_h - freq_fm.height()) // 2 + freq_fm.ascent()
        y_base  = max(c_top + freq_fm.ascent(), y_base)

        return dict(freq_font=freq_font, freq_fm=freq_fm,
                    char_w=char_w, freq_str=freq_str, offsets=offsets,
                    freq_x=freq_x, freq_total_w=freq_total_w,
                    mode_text=mode_text, group_x=group_x,
                    kHz_x=freq_x + freq_total_w + 8,
                    aux_font=aux_font, aux_fm=aux_fm,
                    y_base=y_base, c_top=c_top, c_h=c_h)

    def _hit_digit_idx(self, mouse_x: int) -> int | None:
        lo = self._compute_layout()
        for i, x_off in enumerate(lo['offsets']):
            cx = lo['freq_x'] + x_off
            if cx <= mouse_x < cx + lo['char_w']:
                if self._DIGIT_STEPS[i] is not None:
                    return i
        return None

    # ── Tekenen ───────────────────────────────────────────────────────────────

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)

        # Achtergrond + kader
        p.fillRect(self.rect(), QColor(BG_DISPLAY))
        border_col = QColor(ACCENT if self._hovered else VFD_DIM)
        p.setPen(QPen(border_col, 1))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 4, 4)

        # "VFO-A" label linksbovenin
        tag_font = QFont("Segoe UI", 7, QFont.Bold)
        tag_fm   = QFontMetrics(tag_font)
        p.setFont(tag_font)
        p.setPen(border_col)
        p.drawText(6, 4 + tag_fm.ascent(), "VFO-A")

        lo   = self._compute_layout()
        ff   = lo['freq_font'];   fm   = lo['freq_fm']
        cw   = lo['char_w'];      yb   = lo['y_base']
        fstr = lo['freq_str'];    fx   = lo['freq_x']
        ct   = lo['c_top'];       ch   = lo['c_h']

        # Ghost ("8" achter elk digit in VFD_OFF)
        p.setFont(ff)
        for i, x_off in enumerate(lo['offsets']):
            cx = fx + x_off
            p.setPen(QColor(VFD_OFF))
            p.drawText(cx, yb, "8" if fstr[i].isdigit() else fstr[i])

        # Echte digits, per karakter
        for i, (c, x_off) in enumerate(zip(fstr, lo['offsets'])):
            cx = fx + x_off
            selected = self._hovered and i == self._selected_char
            if selected:
                box_y = yb - fm.ascent()
                p.fillRect(cx - 1, box_y, cw + 2, fm.height(), QColor("#1A1400"))
                p.setPen(QPen(QColor(VFD_AMBER), 1))
                p.setBrush(Qt.NoBrush)
                p.drawRect(cx - 1, box_y, cw + 1, fm.height() - 1)
                p.setPen(QColor(VFD_AMBER))
            elif c == '.':
                p.setPen(QColor(VFD_DIM))
            else:
                p.setPen(QColor(VFD_BRIGHT))
            p.setFont(ff)
            p.drawText(cx, yb, c)

        # Mode voor frequentie (amber, Segoe UI)
        af = lo['aux_font'];  afm = lo['aux_fm']
        ay = ct + (ch - afm.height()) // 2 + afm.ascent()
        p.setFont(af)
        if lo['mode_text']:
            p.setPen(QColor(VFD_AMBER))
            p.drawText(lo['group_x'], ay, lo['mode_text'])

        # kHz na frequentie (dim)
        p.setPen(QColor(VFD_DIM))
        p.drawText(lo['kHz_x'], ay, "kHz")

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

    sig_freq_changed  = Signal(int)
    sig_mode_request  = Signal(str)   # emits gekozen mode via rechtsklik-menu

    _DIGIT_STEPS = [10_000_000, 1_000_000, None,
                    100_000, 10_000, 1_000, None,
                    100, 10, 1]

    _MODES = ["LSB", "USB", "CW", "FM", "AM", "RTTY", "CW-R", "PKT-L"]

    def __init__(self, label="VFO-B", interactive: bool = False,
                 font_size: int = 14, font_name: str = "Consolas", parent=None):
        super().__init__(parent)
        self._label       = label
        self._freq_hz     = 0
        self._interactive = interactive
        self._selected    = 5
        self._hovered     = False
        self._font_sz     = font_size
        self._font_name   = font_name
        self._font_style  = "Bold Italic"
        self._mode        = ""
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setStyleSheet(f"background:{BG_DISPLAY};")
        self.setToolTip("Rechtsklik om modulatie VFO-B te wijzigen")
        self._update_height()
        if interactive:
            self.setCursor(Qt.PointingHandCursor)
            self.setFocusPolicy(Qt.WheelFocus)
            self.setMouseTracking(True)

    def _update_height(self):
        fm = QFontMetrics(QFont(self._font_name, self._font_sz, QFont.Bold))
        self.setFixedHeight(max(44, fm.height() + 22))

    def set_freq(self, hz: int, color: str | None = None):
        self._freq_hz = max(0, int(hz))
        self.update()

    def set_font_size(self, pt: int):
        self._font_sz = max(8, min(28, pt))
        self._update_height()
        self.update()

    def set_font_name(self, name: str):
        self._font_name = name
        self._update_height()
        self.update()

    def set_font_style(self, style: str):
        self._font_style = style
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

    def _make_freq_font(self) -> QFont:
        bold   = "Bold"   in self._font_style
        italic = "Italic" in self._font_style
        f = QFont(self._font_name, self._font_sz,
                  QFont.Bold if bold else QFont.Normal)
        f.setItalic(italic)
        return f

    def _compute_layout(self) -> dict:
        freq_font = self._make_freq_font()
        freq_fm   = QFontMetrics(freq_font)
        char_w    = freq_fm.horizontalAdvance("0")

        freq_str     = self._freq_str()
        offsets      = [i * char_w for i in range(len(freq_str))]
        freq_total_w = len(freq_str) * char_w

        aux_sz   = max(6, int(self._font_sz * 0.55))
        aux_font = QFont("Segoe UI", aux_sz, QFont.Bold)
        aux_fm   = QFontMetrics(aux_font)

        mode_text = self._mode
        mode_w    = aux_fm.horizontalAdvance(mode_text) + 8 if mode_text else 0
        kHz_w     = aux_fm.horizontalAdvance("kHz")

        total_w = mode_w + freq_total_w + 6 + kHz_w
        group_x = (self.width() - total_w) // 2
        freq_x  = group_x + mode_w

        tag_fm  = QFontMetrics(QFont("Segoe UI", 6, QFont.Bold))
        c_top   = tag_fm.height() + 1
        c_h     = self.height() - c_top - 3
        y_base  = c_top + (c_h - freq_fm.height()) // 2 + freq_fm.ascent()
        y_base  = max(c_top + freq_fm.ascent(), y_base)

        return dict(freq_font=freq_font, freq_fm=freq_fm,
                    char_w=char_w, freq_str=freq_str, offsets=offsets,
                    freq_x=freq_x, freq_total_w=freq_total_w,
                    mode_text=mode_text, group_x=group_x,
                    kHz_x=freq_x + freq_total_w + 6,
                    aux_font=aux_font, aux_fm=aux_fm,
                    y_base=y_base, c_top=c_top, c_h=c_h)

    def _hit_digit_idx(self, mouse_x: int) -> int | None:
        lo = self._compute_layout()
        for i, x_off in enumerate(lo['offsets']):
            cx = lo['freq_x'] + x_off
            if cx <= mouse_x < cx + lo['char_w']:
                if self._DIGIT_STEPS[i] is not None:
                    return i
        return None

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
        idx = self._hit_digit_idx(int(event.position().x()))
        if idx is not None and idx != self._selected:
            self._selected = idx
            self.update()

    def mousePressEvent(self, event):
        if not self._interactive or not self._hovered or event.button() != Qt.LeftButton:
            return
        idx = self._hit_digit_idx(int(event.position().x()))
        if idx is not None:
            self._selected = idx
            self.update()

    def contextMenuEvent(self, event):
        """Rechtsklik → mode kiezen voor VFO-B."""
        from PySide6.QtWidgets import QMenu
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{ background:#2A2A2A; color:#DCDCDC;
                     border:1px solid #555; font-size:8pt; }}
            QMenu::item:selected {{ background:#C8A430; color:#000; }}
        """)
        for m in self._MODES:
            act = menu.addAction(m)
            if m == self._mode:
                act.setEnabled(False)
        chosen = menu.exec(event.globalPos())
        if chosen:
            self.sig_mode_request.emit(chosen.text())

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
        p.setRenderHint(QPainter.Antialiasing, True)
        p.fillRect(self.rect(), QColor(BG_DISPLAY))

        # Kader
        border_col = QColor(ACCENT if (self._interactive and self._hovered) else VFD_DIM)
        p.setPen(QPen(border_col, 1))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 3, 3)

        # Label linksbovenin
        tag_font = QFont("Segoe UI", 6, QFont.Bold)
        tag_fm   = QFontMetrics(tag_font)
        p.setFont(tag_font)
        p.setPen(border_col)
        p.drawText(5, 3 + tag_fm.ascent(), self._label)

        lo   = self._compute_layout()
        ff   = lo['freq_font'];  fm  = lo['freq_fm']
        cw   = lo['char_w'];     yb  = lo['y_base']
        fstr = lo['freq_str'];   fx  = lo['freq_x']
        ct   = lo['c_top'];      ch  = lo['c_h']

        # Ghost
        p.setFont(ff)
        for i, x_off in enumerate(lo['offsets']):
            cx = fx + x_off
            p.setPen(QColor(VFD_OFF))
            p.drawText(cx, yb, "8" if fstr[i].isdigit() else fstr[i])

        # Echte digits
        hovering = self._interactive and self._hovered and self._freq_hz > 0
        for i, (c, x_off) in enumerate(zip(fstr, lo['offsets'])):
            cx = fx + x_off
            selected = hovering and i == self._selected
            if selected:
                box_y = yb - fm.ascent()
                p.fillRect(cx - 1, box_y, cw + 2, fm.height(), QColor("#1A1400"))
                p.setPen(QPen(QColor(VFD_AMBER), 1))
                p.setBrush(Qt.NoBrush)
                p.drawRect(cx - 1, box_y, cw + 1, fm.height() - 1)
                p.setPen(QColor(VFD_AMBER))
            elif c == '.':
                p.setPen(QColor(VFD_DIM))
            else:
                p.setPen(QColor(VFD_DIM))
            p.setFont(ff)
            p.drawText(cx, yb, c)

        # Mode + kHz
        af  = lo['aux_font'];  afm = lo['aux_fm']
        ay  = ct + (ch - afm.height()) // 2 + afm.ascent()
        p.setFont(af)
        if lo['mode_text']:
            p.setPen(QColor(VFD_AMBER))
            p.drawText(lo['group_x'], ay, lo['mode_text'])
        p.setPen(QColor(VFD_DIM))
        p.drawText(lo['kHz_x'], ay, "kHz")

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
        self._value        = 0
        self._label        = label
        self._raw_cal      = list(self._DEFAULT_RAW)
        self._pointer      = None   # int 0-255 of None
        self._active_block = None   # int 0-7 of None
        self.setFixedHeight(36)     # iets hoger zodat wijzer boven labels past
        self.setMaximumHeight(36)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set_calibration(self, raw_values: list):
        """Pas kalibratie toe: lijst van 8 ruwe waarden voor S1..+60dB."""
        if len(raw_values) == 8:
            self._raw_cal = [max(0, min(255, int(v))) for v in raw_values]
            self.update()

    def get_calibration(self) -> list:
        return list(self._raw_cal)

    def set_pointer(self, raw: int | None):
        """Toon een witte wijzer op positie raw (0-255). None = verbergen."""
        self._pointer = raw
        self.update()

    def set_active_block(self, idx: int | None):
        """Markeer blokje idx als geselecteerd (wit kader). None = geen."""
        self._active_block = idx
        self.update()

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

        N       = 8
        LBL_W   = 14                 # "S" label links
        PTR_H   = 8                  # hoogte voor wijzer bovenaan
        LBL_H   = 10                 # hoogte labels boven blokjes
        GAP     = self._BLOCK_GAP
        blk_w   = max(6, (w - LBL_W - GAP * (N - 1)) // N)
        blk_h   = max(4, (h - PTR_H - LBL_H - 4) // 3)
        lbl_y   = PTR_H              # labels beginnen na wijzerzone
        blk_y   = PTR_H + LBL_H + 2

        total_w = N * blk_w + (N - 1) * GAP
        x0      = LBL_W + max(0, (w - LBL_W - total_w) // 2)

        p.fillRect(0, 0, w, h, QColor("#080808"))

        lbl_font = QFont("Consolas", 6)
        p.setFont(lbl_font)
        lfm = QFontMetrics(lbl_font)
        p.setPen(QColor(VFD_DIM))
        p.drawText(2, lbl_y + lfm.ascent(), self._label)

        marks = self._MARKS

        for i, (raw, lbl, _) in enumerate(marks):
            bx     = x0 + i * (blk_w + GAP)
            active = self._value >= raw
            is_red = i >= 5
            is_sel = (i == self._active_block)

            # Blokkleur: geselecteerd = fel opgelicht ongeacht meter-waarde
            if is_sel:
                col  = QColor(self._BLOCK_ON_RED if is_red else self._BLOCK_ON_AMBER).lighter(160)
                glow = col.lighter(120)
            elif active:
                col  = QColor(self._BLOCK_ON_RED if is_red else self._BLOCK_ON_AMBER)
                glow = col.lighter(130)
            else:
                col  = QColor(self._BLOCK_OFF_RED if is_red else self._BLOCK_OFF)
                glow = col

            p.fillRect(bx, blk_y, blk_w, blk_h, col)

            if active or is_sel:
                p.setPen(QPen(glow, 1))
                p.drawLine(bx + 1, blk_y + 1, bx + blk_w - 2, blk_y + 1)

            # Rand: geselecteerd = wit kader
            if is_sel:
                p.setPen(QPen(QColor("#FFFFFF"), 1))
            else:
                p.setPen(QPen(col.lighter(150) if active else QColor(BORDER), 1))
            p.drawRect(bx, blk_y, blk_w - 1, blk_h - 1)

            # Label
            if is_sel:
                p.setPen(QColor("#FFFFFF"))
            elif active:
                p.setPen(QColor(self._BLOCK_ON_RED if is_red else self._BLOCK_ON_AMBER))
            else:
                p.setPen(QColor(TEXT_DIM))
            lw = lfm.horizontalAdvance(lbl)
            tx = bx + (blk_w - lw) // 2
            p.drawText(tx, lbl_y + lfm.ascent(), lbl)

        # ── Wijzer (downward triangle) bovenaan ──────────────────────────────
        if self._pointer is not None:
            px = x0 + int(max(0, min(255, self._pointer)) / 255 * total_w)
            px = max(x0, min(x0 + total_w, px))
            tip_y  = PTR_H - 1          # punt van de driehoek
            base_y = 1                  # basis bovenaan
            p.setRenderHint(QPainter.Antialiasing, True)
            from PySide6.QtGui import QPolygon as _Poly
            from PySide6.QtCore import QPoint as _Pt
            tri = _Poly([_Pt(px, tip_y), _Pt(px - 4, base_y), _Pt(px + 4, base_y)])
            p.setBrush(QColor("#E8E8E8"))
            p.setPen(QPen(QColor("#AAAAAA"), 1))
            p.drawConvexPolygon(tri)

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
