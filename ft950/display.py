"""FT-950 Controller — hoofd display-paneel (verticale layout).

Layout (van boven naar beneden):
  ┌─ Row 1: block-diagram (ANT/ATT/IPO/R.FLT/AGC) + status-badges ─┐
  │  Row 2: S-meter + ALC-meter                                      │
  │  Row 3: BIG VFD frequentie (volledige breedte)                   │
  │  Row 4: Mode-label │ VFO-B display │ CLAR-offset display         │
  │  Row 5: DSP-indicatoren (CONTOUR/NOTCH/WIDTH/SHIFT)              │
  └──────────────────────────────────────────────────────────────────┘
"""

from PySide6.QtCore    import Qt, Signal
from PySide6.QtGui     import QFont, QColor, QPainter, QFontMetrics
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QFrame, QSizePolicy,
    QPushButton
)

from .theme   import (BG_DISPLAY, BG_PANEL, BG_SURFACE, VFD_BRIGHT, VFD_DIM,
                      VFD_AMBER, VFD_OFF, LED_GREEN, LED_RED, LED_ORANGE,
                      TEXT_H1, TEXT_DIM, BORDER, ACCENT)
from .widgets import VfdDisplay, SmallVfd, SMeterBar, StatusBadge


# ── Compacte block-diagram cel (tekst-only) ────────────────────────────────────

class _CompactStatus(QLabel):
    """Één item in de block-diagram balk: 'ATT: OFF'."""

    def __init__(self, name: str, default: str, parent=None):
        super().__init__(parent)
        self._name = name
        self._val  = default
        self._refresh()
        self.setStyleSheet(f"""
            QLabel {{
                background: {BG_SURFACE};
                border: 1px solid {BORDER};
                border-radius: 2px;
                padding: 1px 4px;
                font-family: Consolas;
                font-size: 7pt;
                color: {VFD_BRIGHT};
            }}
        """)

    def set_value(self, val: str):
        self._val = val
        self._refresh()

    def _refresh(self):
        self.setText(f"{self._name}:{self._val}")


# ── DSP grafische balk ────────────────────────────────────────────────────────

class _DspBar(QWidget):
    """Horizontale DSP-balk (CONTOUR, NOTCH, WIDTH, SHIFT)."""

    def __init__(self, label: str, color: str = VFD_BRIGHT, parent=None):
        super().__init__(parent)
        self._label  = label
        self._color  = color
        self._value  = 0.5
        self._active = False
        self.setFixedHeight(14)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set_active(self, on: bool):
        self._active = on
        self.update()

    def set_value(self, v: float):
        self._value = max(0.0, min(1.0, v))
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, QColor("#080808"))

        # Track
        track_x = 36
        p.setPen(QColor(self._color if self._active else "#1A2A1A"))
        p.drawLine(track_x, h // 2, w - 4, h // 2)

        # Marker
        if self._active:
            mx = int(track_x + (w - track_x - 4) * self._value)
            p.setPen(QColor(self._color))
            p.drawLine(mx, 2, mx, h - 2)

        # Label
        p.setFont(QFont("Segoe UI", 6))
        p.setPen(QColor(self._color if self._active else TEXT_DIM))
        p.drawText(2, h - 2, self._label)
        p.end()


# ── Hoofd display-paneel ──────────────────────────────────────────────────────

def _btn_style(font_size: int = 7) -> str:
    return f"""
        QPushButton {{
            background: #141414;
            color: #666666;
            border: 1px solid #2A2A2A;
            border-radius: 2px;
            padding: 1px 1px;
            font-family: Consolas;
            font-size: {font_size}pt;
            min-width: 0px;
        }}
        QPushButton:hover {{
            border-color: {VFD_AMBER};
            color: #AAAAAA;
        }}
        QPushButton:checked {{
            background: #2A1800;
            color: {VFD_AMBER};
            border: 1px solid {VFD_AMBER};
            font-weight: bold;
        }}
    """

_BTN_NORM = _btn_style(7)   # standaard bij import


class DisplayPanel(QWidget):
    """Het complete VFD-display van de FT-950 nagebouwd (verticale layout)."""

    sig_freq_changed   = Signal(int)
    sig_freq_b_changed = Signal(int)   # VFO-B afstemming via scrollwiel
    sig_band           = Signal(str)
    sig_mode           = Signal(str)

    _BANDS = [
        ("1.8",  "160m"), ("3.5", "80m"),  ("7",   "40m"),
        ("10",   "30m"),  ("14",  "20m"),  ("18",  "17m"),
        ("21",   "15m"),  ("24.5","12m"),  ("28",  "10m"),
        ("50",   "6m"),   ("GEN", "GEN"),
    ]
    _MODES = [
        ("LSB", "LSB"), ("USB", "USB"), ("CW", "CW"),
        ("AM",  "AM"),  ("FM",  "FM"),  ("RTTY","RTTY"),
    ]

    def __init__(self, vfob_font: int = 14, clar_font: int = 14, parent=None):
        super().__init__(parent)
        self._vfob_font = vfob_font
        self._clar_font = clar_font
        self.setStyleSheet(f"background:{BG_DISPLAY}; border-radius:4px;")
        self.setMinimumWidth(330)
        self._band_btns: dict[str, QPushButton] = {}
        self._mode_btns: dict[str, QPushButton] = {}
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 5, 6, 5)
        root.setSpacing(4)

        # ── Rij 0: Banden + Modes selecteerbaar, geselecteerde = amber ────────
        top = QVBoxLayout()
        top.setSpacing(2)

        # Band-rij — knoppen rekken gelijk uit over de volledige breedte
        band_row = QHBoxLayout()
        band_row.setSpacing(2)
        for label, band in self._BANDS:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setStyleSheet(_BTN_NORM)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.setFixedHeight(16)
            btn.clicked.connect(lambda _, b=band: self._on_band_click(b))
            band_row.addWidget(btn, 1)   # stretch=1 → gelijke verdeling
            self._band_btns[band] = btn
        top.addLayout(band_row)

        # Mode-rij — knoppen rekken uit, rest is leeg
        mode_row = QHBoxLayout()
        mode_row.setSpacing(2)
        for label, mode in self._MODES:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setStyleSheet(_BTN_NORM)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.setFixedHeight(16)
            btn.clicked.connect(lambda _, m=mode: self._on_mode_click(m))
            mode_row.addWidget(btn, 1)
            self._mode_btns[mode] = btn
        mode_row.addStretch(2)   # lege ruimte rechts (modes zijn minder dan banden)
        top.addLayout(mode_row)

        root.addLayout(top)

        # Blok-diagram: alleen intern bijhouden, niet zichtbaar in display
        self._bd_values = {"ANT":"1", "ATT":"OFF", "IPO":"AMP1",
                           "RFLT":"AUTO", "AGC":"AUTO"}

        # Badges: intern bijhouden voor statusbar
        self._badge_tx    = StatusBadge("TX",    LED_RED)
        self._badge_busy  = StatusBadge("BUSY",  LED_GREEN)
        self._badge_nar   = StatusBadge("NAR",   LED_ORANGE)
        self._badge_split = StatusBadge("SPLIT", LED_ORANGE)
        self._badge_nb    = StatusBadge("NB",    LED_ORANGE)
        self._badge_nr    = StatusBadge("DNR",   LED_ORANGE)
        self._badge_fast  = StatusBadge("FAST",  LED_ORANGE)
        self._badge_lock  = StatusBadge("LOCK",  LED_ORANGE)

        # ── Rij 1: VFO-A (mode + freq + kHz in eigen kader) ─────────────────
        self._vfd_a = VfdDisplay(font_size=34)
        self._vfd_a.sig_freq_changed.connect(self.sig_freq_changed)
        root.addWidget(self._vfd_a, 1)   # stretch=1 → neemt resterende hoogte

        # ── Rij 2: S-meter — ONDER de frequentie, niet volledige breedte ─────
        meter_row = QHBoxLayout()
        meter_row.setSpacing(0)
        self._smeter = SMeterBar("S")
        self._smeter.setMaximumWidth(300)
        meter_row.addWidget(self._smeter)
        meter_row.addStretch()
        root.addLayout(meter_row)

        # ── Rij 3: VFO-B ─────────────────────────────────────────────────────
        self._vfd_b = SmallVfd("VFO-B", interactive=True, font_size=self._vfob_font)
        self._vfd_b.sig_freq_changed.connect(self.sig_freq_b_changed)
        root.addWidget(self._vfd_b)

    # ── Publieke update-methoden ──────────────────────────────────────────────

    def set_freq_a(self, hz: int):
        self._vfd_a.set_freq(hz)

    def set_freq_b(self, hz: int):
        self._vfd_b.set_freq(hz)

    def set_clar_offset(self, hz: int):
        pass  # CLAR-display verwijderd

    def set_mode(self, mode: str):
        self._vfd_a.set_mode(mode)
        self._vfd_b.set_mode(mode)
        # Update ook de mode-knoppen in de bovenste balk
        mode_upper = mode.upper().split("-")[0]   # "CW-R" → "CW", "FM-N" → "FM"
        for m, btn in self._mode_btns.items():
            btn.setChecked(m == mode_upper or m == mode)

    def set_band(self, band: str):
        """Markeer de actieve band in de bovenste balk."""
        for b, btn in self._band_btns.items():
            btn.setChecked(b == band)

    def _on_band_click(self, band: str):
        for b, btn in self._band_btns.items():
            btn.setChecked(b == band)
        self.sig_band.emit(band)

    def _on_mode_click(self, mode: str):
        for m, btn in self._mode_btns.items():
            btn.setChecked(m == mode)
        self.sig_mode.emit(mode)

    def set_tx(self, on: bool):
        pass  # TX-badge wordt nu beheerd via mainwindow._set_tx_active (knipperend)

    def set_busy(self, on: bool):
        self._badge_busy.set_active(on)

    def set_fast(self, on: bool):
        self._badge_fast.set_active(on)

    def set_lock(self, on: bool):
        self._badge_lock.set_active(on)

    def set_nar(self, on: bool):
        self._badge_nar.set_active(on)

    def set_split(self, on: bool):
        self._badge_split.set_active(on)

    def set_nb(self, on: bool):
        self._badge_nb.set_active(on)

    def set_nr(self, on: bool):
        self._badge_nr.set_active(on)

    def set_smeter(self, val: int):
        self._smeter.set_value(val)

    # ── Lettergrootte aanpassen op runtime ────────────────────────────────────

    def set_btn_font(self, size: int):
        """Pas de lettergrootte van alle band/mode knoppen direct aan."""
        style = _btn_style(size)
        for btn in self._band_btns.values():
            btn.setStyleSheet(style)
        for btn in self._mode_btns.values():
            btn.setStyleSheet(style)

    def set_vfd_font(self, size: int):
        """Pas de lettergrootte van het frequentie-display direct aan."""
        self._vfd_a._font_sz = size
        self._vfd_a.repaint()   # directe hertekening, geen layout-herberekening

    # Block-diagram: alleen intern bijhouden (blok-diagram niet meer zichtbaar)
    def _refresh_bd(self):
        pass

    def set_ant(self, n: str):  self._bd_values["ANT"]  = str(n); self._refresh_bd()
    def set_att(self, v: str):  self._bd_values["ATT"]  = v;      self._refresh_bd()
    def set_ipo(self, v: str):  self._bd_values["IPO"]  = v;      self._refresh_bd()
    def set_rflt(self, v: str): self._bd_values["RFLT"] = v;      self._refresh_bd()
    def set_agc(self, v: str):  self._bd_values["AGC"]  = v;      self._refresh_bd()

    # DSP-indicatoren zijn verwijderd uit het display; setters zijn no-ops
    def set_dsp_contour(self, active: bool, pos: float = 0.5): pass
    def set_dsp_notch(self,   active: bool, pos: float = 0.5): pass
    def set_dsp_width(self,   active: bool, pos: float = 0.5): pass
    def set_dsp_shift(self,   active: bool, pos: float = 0.5): pass

    def apply_state(self, state: dict):
        """Verwerk een IF; state-dict (van Ft950Cat._read_if)."""
        if not state:
            return
        self.set_freq_a(state.get("freq_hz", 0))
        self.set_mode(state.get("mode", "?"))
        rx_clar = state.get("rx_clar", False)
        tx_clar = state.get("tx_clar", False)
        off     = state.get("clar_off", 0)
        if state.get("clar_dir", "+") == "-":
            off = -off
        self.set_clar_offset(off if (rx_clar or tx_clar) else 0)
        self.set_split(tx_clar)
