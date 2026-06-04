"""FT-950 Controller — knop/bedieningspanelen.

Panels (van links naar rechts conform de echte radio):
  LeftPanel      — POWER/ANT/MOX/TUNE/VOX + ALC meter
  ModePanel      — MONI/PROC/SPOT/BK-IN/KEYER/AGC + MIC GAIN/SPEED
  DspPanel       — SHIFT/WIDTH/CONT/NOTCH/µ-TUNE/CLEAR + SELECT
  VfoPanel       — QMB, NAR/SPLIT/TXW, hoofdafstemknop (simulatie), VFO-knoppen
  BandModePanel  — BAND-knoppen + MODE-knoppen
  RightPanel     — ATT/IPO/R.FLT/NB/AF-RF gain + CLAR-knoppen
  PowerPanel     — Zendvermogen schuif + ALC indicator
"""

from PySide6.QtCore    import Qt, Signal, QSize, Qt
from PySide6.QtGui     import QFont, QFontDatabase
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QSlider, QSpinBox, QFrame, QSizePolicy,
    QComboBox, QPushButton
)

from .theme   import (BG_PANEL, BTN_NORMAL, BTN_HOVER, BORDER,
                      TEXT_H1, TEXT_DIM, ACCENT, LED_GREEN, LED_RED,
                      LED_ORANGE, BG_SURFACE, LED_AMBER, GROUP_BORDER,
                      VFD_AMBER)
from .widgets import LedButton, RadioButton, SectionFrame, SMeterBar, TxMeterBar, StatusBadge
from .i18n    import tr


def _sep(vertical: bool = False) -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.VLine if vertical else QFrame.HLine)
    f.setStyleSheet(f"background:{BORDER}; max-{'width' if vertical else 'height'}:1px;")
    return f


def _lbl(text: str, tiny: bool = False) -> QLabel:
    l = QLabel(text)
    fs = "6pt" if tiny else "7pt"
    l.setStyleSheet(f"color:{TEXT_DIM}; font-size:{fs}; background:transparent;")
    return l


# ── Links: POWER / ANT / MOX / TUNE / VOX ─────────────────────────────────────

class LeftPanel(QWidget):
    sig_power  = Signal(bool)    # aan/uit
    sig_mox    = Signal(bool)    # PTT
    sig_tune   = Signal(int)     # 0=off,1=on,2=tune
    sig_vox    = Signal(bool)
    sig_ant    = Signal(int)     # 1 of 2

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(95)
        self._build()

    def _build(self):
        v = QVBoxLayout(self)
        v.setContentsMargins(4, 4, 4, 4)
        v.setSpacing(4)

        # Aan/uit
        self.btn_power = LedButton("ON/OFF", LED_GREEN, checkable=True)
        self.btn_power.setFixedHeight(26)
        self.btn_power.toggled.connect(self.sig_power)
        v.addWidget(self.btn_power)

        v.addWidget(_sep())

        # ANT 1-2
        ant_row = QHBoxLayout()
        ant_row.setSpacing(2)
        self.btn_ant1 = RadioButton("ANT 1", checkable=True, small=True)
        self.btn_ant2 = RadioButton("ANT 2", checkable=True, small=True)
        self.btn_ant1.setChecked(True)
        self.btn_ant1.clicked.connect(lambda: self._set_ant(1))
        self.btn_ant2.clicked.connect(lambda: self._set_ant(2))
        ant_row.addWidget(self.btn_ant1)
        ant_row.addWidget(self.btn_ant2)
        v.addLayout(ant_row)

        # MOX
        self.btn_mox = LedButton("MOX", LED_RED, checkable=True, small=True)
        self.btn_mox.toggled.connect(self.sig_mox)
        v.addWidget(self.btn_mox)

        # TUNE
        tune_row = QHBoxLayout()
        tune_row.setSpacing(2)
        self.btn_tune_on  = RadioButton("TUNE", checkable=True, small=True)
        self.btn_tune_go  = RadioButton("⟳",   checkable=False, small=True)
        self.btn_tune_on.setFixedWidth(46)
        self.btn_tune_go.setFixedWidth(26)
        self.btn_tune_on.toggled.connect(lambda on: self.sig_tune.emit(1 if on else 0))
        self.btn_tune_go.clicked.connect(lambda: self.sig_tune.emit(2))
        tune_row.addWidget(self.btn_tune_on)
        tune_row.addWidget(self.btn_tune_go)
        v.addLayout(tune_row)

        # VOX
        self.btn_vox = LedButton("VOX", LED_ORANGE, checkable=True, small=True)
        self.btn_vox.toggled.connect(self.sig_vox)
        v.addWidget(self.btn_vox)

        v.addWidget(_sep())

        # ALC meter
        v.addWidget(_lbl("ALC", tiny=True))
        self.alc_bar = SMeterBar("ALC")
        v.addWidget(self.alc_bar)

        v.addStretch()

    def _set_ant(self, n: int):
        self.btn_ant1.setChecked(n == 1)
        self.btn_ant2.setChecked(n == 2)
        self.sig_ant.emit(n)

    def set_power(self, on: bool):
        self.btn_power.setChecked(on)

    def set_alc(self, v: int):
        self.alc_bar.set_value(v)


# ── Modus-paneel: MONI/PROC/SPOT/BK-IN/KEYER/AGC + MIC GAIN/SPEED ─────────────

class ModePanel(QWidget):
    sig_moni   = Signal(bool)
    sig_proc   = Signal(bool)
    sig_spot   = Signal(bool)
    sig_bkin   = Signal(bool)
    sig_keyer  = Signal(bool)
    sig_agc    = Signal(int)    # 0=off,1=fast,2=mid,3=slow,4=auto
    sig_mic    = Signal(int)    # 0-255
    sig_speed  = Signal(int)    # 4-60 WPM

    _AGC_LABELS = ["OFF", "FAST", "MID", "SLOW", "AUTO"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(120)
        self._agc_idx = 4   # AUTO
        self._build()

    def _build(self):
        v = QVBoxLayout(self)
        v.setContentsMargins(4, 4, 4, 4)
        v.setSpacing(3)

        # Bovenste rij knoppen
        row1 = QHBoxLayout(); row1.setSpacing(2)
        self.btn_moni  = LedButton("MONI",  LED_GREEN,  small=True)
        self.btn_proc  = LedButton("PROC",  LED_ORANGE, small=True)
        self.btn_spot  = LedButton("SPOT",  LED_ORANGE, small=True)
        for btn, sig in [(self.btn_moni, self.sig_moni),
                         (self.btn_proc, self.sig_proc),
                         (self.btn_spot, self.sig_spot)]:
            btn.toggled.connect(sig)
            row1.addWidget(btn)
        v.addLayout(row1)

        row2 = QHBoxLayout(); row2.setSpacing(2)
        self.btn_bkin  = LedButton("BK-IN",  LED_GREEN,  small=True)
        self.btn_keyer = LedButton("KEYER",  LED_ORANGE, small=True)
        self.btn_agc   = RadioButton("AGC",  checkable=False, small=True)
        self.btn_bkin.toggled.connect(self.sig_bkin)
        self.btn_keyer.toggled.connect(self.sig_keyer)
        self.btn_agc.clicked.connect(self._cycle_agc)
        self._agc_lbl = _lbl("AUTO", tiny=True)
        row2.addWidget(self.btn_bkin)
        row2.addWidget(self.btn_keyer)
        row2.addWidget(self.btn_agc)
        v.addLayout(row2)
        agc_row = QHBoxLayout()
        agc_row.addStretch()
        agc_row.addWidget(self._agc_lbl)
        v.addLayout(agc_row)

        v.addWidget(_sep())

        # MIC GAIN knop-slider
        v.addWidget(_lbl("MIC GAIN", tiny=True))
        self.sld_mic = QSlider(Qt.Horizontal)
        self.sld_mic.setRange(0, 255)
        self.sld_mic.setValue(128)
        self.sld_mic.setFixedHeight(18)
        self.sld_mic.valueChanged.connect(self.sig_mic)
        self.sld_mic.setStyleSheet(_slider_qss())
        v.addWidget(self.sld_mic)

        # SPEED (CW)
        v.addWidget(_lbl("SPEED (WPM)", tiny=True))
        self.sld_speed = QSlider(Qt.Horizontal)
        self.sld_speed.setRange(4, 60)
        self.sld_speed.setValue(20)
        self.sld_speed.setFixedHeight(18)
        self.sld_speed.valueChanged.connect(self.sig_speed)
        self.sld_speed.setStyleSheet(_slider_qss())
        v.addWidget(self.sld_speed)

        v.addStretch()

    def _cycle_agc(self):
        self._agc_idx = (self._agc_idx + 1) % len(self._AGC_LABELS)
        self._agc_lbl.setText(self._AGC_LABELS[self._agc_idx])
        self.sig_agc.emit(self._agc_idx)

    def set_agc(self, idx: int):
        self._agc_idx = idx % len(self._AGC_LABELS)
        self._agc_lbl.setText(self._AGC_LABELS[self._agc_idx])


# ── Gecombineerd links paneel (LeftPanel + ModePanel in één kolom) ─────────────

class CombinedLeftPanel(QWidget):
    """
    Alle knoppen van LeftPanel + ModePanel verticaal in één kolom, volle breedte.

    Signalen zijn identiek aan LeftPanel + ModePanel zodat mainwindow.py
    ongewijzigd blijft.
    """

    # ─ LeftPanel-signalen
    sig_power  = Signal()
    sig_mox    = Signal(bool)
    sig_tune   = Signal(int)
    sig_vox    = Signal(bool)
    sig_mute   = Signal(bool)   # geluid dempen
    sig_ant    = Signal(int)

    # ─ ModePanel-signalen
    sig_moni   = Signal(bool)
    sig_proc   = Signal(bool)
    sig_spot   = Signal(bool)
    sig_bkin   = Signal(bool)
    sig_keyer  = Signal(bool)
    sig_agc    = Signal(int)
    sig_mic    = Signal(int)
    sig_speed  = Signal(int)

    _AGC_LABELS = ["OFF", "FAST", "MID", "SLOW", "AUTO"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(215)
        self._agc_idx = 4
        self._build()

    def _build(self):
        v = QVBoxLayout(self)
        v.setContentsMargins(6, 6, 6, 6)
        v.setSpacing(5)

        # ── VERBINDEN / VERBREKEN ─────────────────────────────────────────────
        self.btn_power = QPushButton(tr("⬤  Verbinden"))
        self.btn_power.setFixedHeight(34)
        self.btn_power.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self.btn_power.clicked.connect(self.sig_power)   # mainwindow koppelt toggle
        self._set_conn_style(False)
        v.addWidget(self.btn_power)

        v.addWidget(_sep())

        # ── ANTENNE ──────────────────────────────────────────────────────────
        ant_row = QHBoxLayout(); ant_row.setSpacing(4)
        self.btn_ant1 = RadioButton("ANT 1", checkable=True)
        self.btn_ant2 = RadioButton("ANT 2", checkable=True)
        self.btn_ant1.setChecked(True)
        self.btn_ant1.clicked.connect(lambda: self._set_ant(1))
        self.btn_ant2.clicked.connect(lambda: self._set_ant(2))
        ant_row.addWidget(self.btn_ant1)
        ant_row.addWidget(self.btn_ant2)
        v.addLayout(ant_row)

        # ── MOX / TUNE ───────────────────────────────────────────────────────
        mt_row = QHBoxLayout(); mt_row.setSpacing(4)
        self.btn_mox      = LedButton("MOX",  LED_RED,    checkable=True)
        self.btn_tune_on  = RadioButton("TUNE", checkable=True)
        self.btn_tune_go  = RadioButton("⟳",   checkable=False)
        self.btn_tune_go.setFixedWidth(32)
        self.btn_mox.toggled.connect(self.sig_mox)
        self.btn_tune_on.toggled.connect(lambda on: self.sig_tune.emit(1 if on else 0))
        self.btn_tune_go.clicked.connect(lambda: self.sig_tune.emit(2))
        mt_row.addWidget(self.btn_mox, 2)
        mt_row.addWidget(self.btn_tune_on, 2)
        mt_row.addWidget(self.btn_tune_go, 1)
        v.addLayout(mt_row)

        # ── VOX ──────────────────────────────────────────────────────────────
        self.btn_vox = LedButton("VOX", LED_ORANGE, checkable=True)
        self.btn_vox.toggled.connect(self.sig_vox)
        v.addWidget(self.btn_vox)

        # ── MUTE — gewone knop zonder LED-cirkel ─────────────────────────────
        self.btn_mute = QPushButton("🔇  MUTE")
        self.btn_mute.setCheckable(True)
        self.btn_mute.setFixedHeight(32)
        self.btn_mute.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self.btn_mute.setStyleSheet(f"""
            QPushButton {{
                background: #1A1A1A;
                color: {TEXT_DIM};
                border: 1px solid {BORDER};
                border-radius: 3px;
                padding: 4px;
                text-align: center;
            }}
            QPushButton:hover  {{ border-color: {LED_RED}; }}
            QPushButton:checked {{
                background: #3A0A0A;
                color: #EF5350;
                border: 2px solid #EF5350;
                font-weight: bold;
            }}
        """)
        self.btn_mute.toggled.connect(self.sig_mute)
        v.addWidget(self.btn_mute)

        v.addWidget(_sep())

        # ── MONI / PROC / SPOT ───────────────────────────────────────────────
        row1 = QHBoxLayout(); row1.setSpacing(4)
        self.btn_moni = LedButton("MONI",  LED_GREEN,  small=True)
        self.btn_proc = LedButton("PROC",  LED_ORANGE, small=True)
        self.btn_spot = LedButton("SPOT",  LED_ORANGE, small=True)
        for btn, sig in [(self.btn_moni, self.sig_moni),
                         (self.btn_proc, self.sig_proc),
                         (self.btn_spot, self.sig_spot)]:
            btn.toggled.connect(sig)
            row1.addWidget(btn)
        v.addLayout(row1)

        # ── BK-IN / KEYER / AGC ──────────────────────────────────────────────
        row2 = QHBoxLayout(); row2.setSpacing(4)
        self.btn_bkin  = LedButton("BK-IN",  LED_GREEN,  small=True)
        self.btn_keyer = LedButton("KEYER",  LED_ORANGE, small=True)
        self.btn_agc   = RadioButton("AGC",  checkable=False, small=True)
        self._agc_lbl  = _lbl("AUTO", tiny=True)
        self.btn_bkin.toggled.connect(self.sig_bkin)
        self.btn_keyer.toggled.connect(self.sig_keyer)
        self.btn_agc.clicked.connect(self._cycle_agc)
        row2.addWidget(self.btn_bkin)
        row2.addWidget(self.btn_keyer)
        row2.addWidget(self.btn_agc)
        row2.addWidget(self._agc_lbl)
        v.addLayout(row2)

        v.addWidget(_sep())

        # ── MIC GAIN ─────────────────────────────────────────────────────────
        mic_row = QHBoxLayout()
        mic_row.addWidget(_lbl("MIC GAIN", tiny=True))
        self._mic_val = _lbl("128", tiny=True)
        mic_row.addStretch(); mic_row.addWidget(self._mic_val)
        v.addLayout(mic_row)
        self.sld_mic = QSlider(Qt.Horizontal)
        self.sld_mic.setRange(0, 255); self.sld_mic.setValue(128)
        self.sld_mic.setFixedHeight(18)
        self.sld_mic.setStyleSheet(_slider_qss())
        self.sld_mic.valueChanged.connect(lambda val: [
            self._mic_val.setText(str(val)), self.sig_mic.emit(val)])
        v.addWidget(self.sld_mic)

        # ── SPEED ─────────────────────────────────────────────────────────────
        spd_row = QHBoxLayout()
        spd_row.addWidget(_lbl("SPEED (WPM)", tiny=True))
        self._spd_val = _lbl("20", tiny=True)
        spd_row.addStretch(); spd_row.addWidget(self._spd_val)
        v.addLayout(spd_row)
        self.sld_speed = QSlider(Qt.Horizontal)
        self.sld_speed.setRange(4, 60); self.sld_speed.setValue(20)
        self.sld_speed.setFixedHeight(18)
        self.sld_speed.setStyleSheet(_slider_qss())
        self.sld_speed.valueChanged.connect(lambda val: [
            self._spd_val.setText(str(val)), self.sig_speed.emit(val)])
        v.addWidget(self.sld_speed)

        v.addWidget(_sep())

        # ── ALC METER ────────────────────────────────────────────────────────
        v.addWidget(_lbl("ALC", tiny=True))
        self.alc_bar = SMeterBar("ALC")
        v.addWidget(self.alc_bar)

        # ── SWR METER ────────────────────────────────────────────────────────
        v.addWidget(_lbl("SWR", tiny=True))
        from .widgets import TxMeterBar
        _SWR = [( 43, "1.3", "#00AAFF"),
                ( 85, "1.5", "#00BB44"),
                (128, "2.0", "#FFAA00"),
                (191, "2.5", "#FF6600"),
                (232, "3.0", "#FF2020")]
        self.swr_bar = TxMeterBar("SWR", _SWR)
        v.addWidget(self.swr_bar)

        v.addStretch()

    # ── Hulpfuncties ──────────────────────────────────────────────────────────

    def _set_ant(self, n: int):
        self.btn_ant1.setChecked(n == 1)
        self.btn_ant2.setChecked(n == 2)
        self.sig_ant.emit(n)

    def _cycle_agc(self):
        self._agc_idx = (self._agc_idx + 1) % len(self._AGC_LABELS)
        self._agc_lbl.setText(self._AGC_LABELS[self._agc_idx])
        self.sig_agc.emit(self._agc_idx)

    # ── Publieke setters ──────────────────────────────────────────────────────

    def _set_conn_style(self, connected: bool):
        if connected:
            self.btn_power.setText(tr("⬤  Verbreken"))
            self.btn_power.setStyleSheet(f"""
                QPushButton {{
                    background: #3A0A0A;
                    color: #EF5350;
                    border: 2px solid #EF5350;
                    border-radius: 4px;
                    padding: 4px;
                    font-weight: bold;
                }}
                QPushButton:hover {{ background: #5A1010; }}
                QPushButton:pressed {{ background: #220000; }}
            """)
        else:
            self.btn_power.setText(tr("⬤  Verbinden"))
            self.btn_power.setStyleSheet(f"""
                QPushButton {{
                    background: #0A2A0A;
                    color: #4CAF50;
                    border: 2px solid #4CAF50;
                    border-radius: 4px;
                    padding: 4px;
                    font-weight: bold;
                }}
                QPushButton:hover {{ background: #1A4A1A; }}
                QPushButton:pressed {{ background: #002200; }}
            """)

    def set_power(self, on: bool):        self._set_conn_style(on)
    def set_alc(self, v: int):            self.alc_bar.set_value(v)
    def set_swr(self, raw: int, text: str = ""):
        self.swr_bar.set_value(raw, text)
    def set_agc(self, idx: int):
        self._agc_idx = idx % len(self._AGC_LABELS)
        self._agc_lbl.setText(self._AGC_LABELS[self._agc_idx])


# ── DSP paneel: SHIFT/WIDTH/CONT/NOTCH/µ-TUNE/CLEAR ─────────────────────────

class DspPanel(QWidget):
    """
    DSP-filterbesturing: elke functie heeft zijn eigen knop + aanpasbare waarde.

    Lay-out:
      SHIFT knop  ◄──── schuif -1000..+1000 Hz ────► ±xxx
      WIDTH knop  [ combobox: 3.0k … 200 Hz ]
      CONT  knop  ◄──── schuif positie 1..30 ────────► xx
      NOTCH knop  ◄──── schuif freq 100..3000 Hz ────► xxxx
      ─────────────────────────────────────────────────────
      [NAR]  [µ-TUNE]  [CLEAR]
    """

    sig_shift      = Signal(bool)   # button toggle
    sig_shift_hz   = Signal(int)    # slider: -1000..+1000 Hz
    sig_width      = Signal(bool)
    sig_width_code = Signal(int)    # combobox index → bandwidth code
    sig_cont       = Signal(bool)
    sig_cont_pos   = Signal(int)    # slider: 1..30
    sig_notch      = Signal(bool)
    sig_notch_hz   = Signal(int)    # slider: 100..3000 Hz
    sig_utune      = Signal(bool)
    sig_clear      = Signal()
    sig_narrow     = Signal(bool)

    # Bandbreedtecodes (conform CAT ref. p.15-16) per combobox-index
    # SSB-wide: index 0-12 → code 9-20; NAR: aparte set
    _WIDTH_LABELS = ["3.0k", "2.9k", "2.8k", "2.7k", "2.6k",
                     "2.5k", "2.4k", "2.1k", "1.8k", "1.5k",
                     "1.2k", "1.0k",  "800",  "500",  "400", "300", "200"]
    _WIDTH_CODES  = [20, 19, 18, 17, 16, 15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(200)
        self._build()

    def _build(self):
        v = QVBoxLayout(self)
        v.setContentsMargins(4, 4, 4, 4)
        v.setSpacing(4)

        # ── IF SHIFT ──────────────────────────────────────────────────────────
        v.addWidget(_lbl("IF SHIFT", tiny=True))
        self.btn_shift = LedButton("SHIFT", LED_ORANGE, small=True)
        self.btn_shift.setFixedWidth(56)
        self.sld_shift = QSlider(Qt.Horizontal)
        self.sld_shift.setRange(-1000, 1000)
        self.sld_shift.setValue(0)
        self.sld_shift.setFixedHeight(18)
        self.sld_shift.setStyleSheet(_slider_qss())
        self._lbl_shift = _lbl("  0 Hz", tiny=True)
        self._lbl_shift.setFixedWidth(36)
        self.btn_shift.toggled.connect(self.sig_shift)
        self.sld_shift.valueChanged.connect(self._on_shift_val)
        r = QHBoxLayout(); r.setSpacing(3)
        r.addWidget(self.btn_shift); r.addWidget(self.sld_shift)
        r.addWidget(self._lbl_shift)
        v.addLayout(r)

        # ── IF WIDTH ──────────────────────────────────────────────────────────
        v.addWidget(_lbl("IF WIDTH", tiny=True))
        self.btn_width = LedButton("WIDTH", LED_ORANGE, small=True)
        self.btn_width.setFixedWidth(56)
        self.cmb_width = QComboBox()
        self.cmb_width.addItems(self._WIDTH_LABELS)
        self.cmb_width.setCurrentIndex(6)   # 2.4k = standaard
        self.cmb_width.setFixedHeight(20)
        self.cmb_width.setStyleSheet(_combobox_qss())
        self.btn_width.toggled.connect(self.sig_width)
        self.cmb_width.currentIndexChanged.connect(
            lambda i: self.sig_width_code.emit(self._WIDTH_CODES[i]))
        r2 = QHBoxLayout(); r2.setSpacing(3)
        r2.addWidget(self.btn_width); r2.addWidget(self.cmb_width)
        v.addLayout(r2)

        # ── CONTOUR ───────────────────────────────────────────────────────────
        v.addWidget(_lbl("CONTOUR positie (1-30)", tiny=True))
        self.btn_cont = LedButton("CONT", LED_ORANGE, small=True)
        self.btn_cont.setFixedWidth(56)
        self.sld_cont = QSlider(Qt.Horizontal)
        self.sld_cont.setRange(1, 30)
        self.sld_cont.setValue(15)
        self.sld_cont.setFixedHeight(18)
        self.sld_cont.setStyleSheet(_slider_qss())
        self._lbl_cont = _lbl("15", tiny=True)
        self._lbl_cont.setFixedWidth(20)
        self.btn_cont.toggled.connect(self.sig_cont)
        self.sld_cont.valueChanged.connect(self._on_cont_val)
        r3 = QHBoxLayout(); r3.setSpacing(3)
        r3.addWidget(self.btn_cont); r3.addWidget(self.sld_cont)
        r3.addWidget(self._lbl_cont)
        v.addLayout(r3)

        # ── NOTCH ─────────────────────────────────────────────────────────────
        v.addWidget(_lbl("NOTCH frequentie (Hz)", tiny=True))
        self.btn_notch = LedButton("NOTCH", LED_ORANGE, small=True)
        self.btn_notch.setFixedWidth(56)
        self.sld_notch = QSlider(Qt.Horizontal)
        self.sld_notch.setRange(10, 300)    # ×10 Hz → 100..3000 Hz
        self.sld_notch.setValue(150)         # 1500 Hz standaard
        self.sld_notch.setFixedHeight(18)
        self.sld_notch.setStyleSheet(_slider_qss())
        self._lbl_notch = _lbl("1500", tiny=True)
        self._lbl_notch.setFixedWidth(28)
        self.btn_notch.toggled.connect(self.sig_notch)
        self.sld_notch.valueChanged.connect(self._on_notch_val)
        r4 = QHBoxLayout(); r4.setSpacing(3)
        r4.addWidget(self.btn_notch); r4.addWidget(self.sld_notch)
        r4.addWidget(self._lbl_notch)
        v.addLayout(r4)

        v.addWidget(_sep())

        # ── Overige knoppen ───────────────────────────────────────────────────
        other = QHBoxLayout(); other.setSpacing(2)
        self.btn_utune = LedButton("µ-TUNE", LED_GREEN, small=True)
        self.btn_nar   = LedButton("NAR",    LED_ORANGE, checkable=True, small=True)
        self.btn_clear = RadioButton("CLEAR", checkable=False, small=True)
        self.btn_utune.toggled.connect(self.sig_utune)
        self.btn_nar.toggled.connect(self.sig_narrow)
        self.btn_clear.clicked.connect(self.sig_clear)
        for b in (self.btn_utune, self.btn_nar, self.btn_clear):
            other.addWidget(b)
        v.addLayout(other)

        v.addStretch()

    # ── Waarde-handlers ───────────────────────────────────────────────────────

    def _on_shift_val(self, val: int):
        sign = "+" if val >= 0 else ""
        self._lbl_shift.setText(f"{sign}{val}")
        self.sig_shift_hz.emit(val)

    def _on_cont_val(self, val: int):
        self._lbl_cont.setText(str(val))
        self.sig_cont_pos.emit(val)

    def _on_notch_val(self, val: int):
        hz = val * 10
        self._lbl_notch.setText(str(hz))
        self.sig_notch_hz.emit(hz)

    def get_width_code(self) -> int:
        return self._WIDTH_CODES[self.cmb_width.currentIndex()]


# ── VFO paneel ─────────────────────────────────────────────────────────────────

class VfoPanel(QWidget):
    """VFO-bedieningsknoppen: QMB, SPLIT, memorie-knoppen, frequency-invoer."""

    sig_qmb_sto  = Signal()
    sig_qmb_rcl  = Signal()
    sig_split    = Signal(bool)
    sig_txw      = Signal(bool)
    sig_ab       = Signal()
    sig_asb      = Signal()
    sig_vm       = Signal()
    sig_ma       = Signal()
    sig_am       = Signal()
    sig_freq_up  = Signal(int)    # stap in Hz
    sig_freq_dn  = Signal(int)
    sig_fast     = Signal(bool)
    sig_lock     = Signal(bool)
    sig_vfoa_tx  = Signal()
    sig_vfob_tx  = Signal()

    _STEPS = [10, 100, 1_000, 5_000, 10_000]
    _STEP_LABELS = ["10 Hz", "100 Hz", "1 kHz", "5 kHz", "10 kHz"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(165)
        self._step_idx = 2
        self._build()

    def _build(self):
        v = QVBoxLayout(self)
        v.setContentsMargins(4, 4, 4, 4)
        v.setSpacing(3)

        # QMB
        qmb_row = QHBoxLayout(); qmb_row.setSpacing(2)
        btn_qmb_sto = RadioButton("QMB STO", small=True)
        btn_qmb_rcl = RadioButton("QMB RCL", small=True)
        btn_qmb_sto.clicked.connect(self.sig_qmb_sto)
        btn_qmb_rcl.clicked.connect(self.sig_qmb_rcl)
        qmb_row.addWidget(btn_qmb_sto)
        qmb_row.addWidget(btn_qmb_rcl)
        v.addLayout(qmb_row)

        v.addWidget(_sep())

        # SPLIT / TXW
        split_row = QHBoxLayout(); split_row.setSpacing(2)
        self.btn_split = LedButton("SPLIT", LED_ORANGE, checkable=True, small=True)
        self.btn_txw   = LedButton("TXW",   LED_RED,    checkable=True, small=True)
        self.btn_split.toggled.connect(self.sig_split)
        self.btn_txw.toggled.connect(self.sig_txw)
        split_row.addWidget(self.btn_split)
        split_row.addWidget(self.btn_txw)
        v.addLayout(split_row)

        # TX indicator knoppen VFO-A / VFO-B
        vfo_tx_row = QHBoxLayout(); vfo_tx_row.setSpacing(2)
        self.btn_vfoa_tx = LedButton("VFO-A TX", LED_RED, checkable=True, small=True)
        self.btn_vfob_tx = LedButton("VFO-B TX", LED_RED, checkable=True, small=True)
        self.btn_vfoa_tx.setChecked(True)
        self.btn_vfoa_tx.clicked.connect(self._set_vfoa_tx)
        self.btn_vfob_tx.clicked.connect(self._set_vfob_tx)
        vfo_tx_row.addWidget(self.btn_vfoa_tx)
        vfo_tx_row.addWidget(self.btn_vfob_tx)
        v.addLayout(vfo_tx_row)

        v.addWidget(_sep())

        # FAST / LOCK
        fl_row = QHBoxLayout(); fl_row.setSpacing(2)
        self.btn_fast = LedButton("FAST", LED_ORANGE, checkable=True, small=True)
        self.btn_lock = LedButton("LOCK", LED_ORANGE, checkable=True, small=True)
        self.btn_fast.toggled.connect(self.sig_fast)
        self.btn_lock.toggled.connect(self.sig_lock)
        fl_row.addWidget(self.btn_fast)
        fl_row.addWidget(self.btn_lock)
        v.addLayout(fl_row)

        v.addWidget(_sep())

        # Afstem-knoppen (simulatie draaiknop met + / -)
        v.addWidget(_lbl(tr("AFSTEMSTAP"), tiny=True))
        step_row = QHBoxLayout(); step_row.setSpacing(2)
        btn_dn = RadioButton("◀", small=True)
        btn_dn.setFixedWidth(26)
        self._step_lbl = _lbl(self._STEP_LABELS[self._step_idx])
        btn_up = RadioButton("▶", small=True)
        btn_up.setFixedWidth(26)
        btn_dn.clicked.connect(self._freq_down)
        btn_up.clicked.connect(self._freq_up)
        step_row.addWidget(btn_dn)
        step_row.addWidget(self._step_lbl, 1)
        step_row.addWidget(btn_up)
        v.addLayout(step_row)

        # Stap selectie
        step_sel = QHBoxLayout(); step_sel.setSpacing(2)
        step_sel.addWidget(_lbl(tr("Stap:"), tiny=True))
        self.cmb_step = QComboBox()
        self.cmb_step.addItems(self._STEP_LABELS)
        self.cmb_step.setCurrentIndex(self._step_idx)
        self.cmb_step.currentIndexChanged.connect(self._change_step)
        self.cmb_step.setFixedHeight(20)
        self.cmb_step.setStyleSheet(f"""
            QComboBox {{
                background:{BTN_NORMAL}; color:{TEXT_H1};
                border:1px solid {BORDER}; padding:1px 4px;
                font-size:7pt; border-radius:2px;
            }}
            QComboBox QAbstractItemView {{
                background:{BG_PANEL}; color:{TEXT_H1};
                selection-background-color:{ACCENT};
            }}
        """)
        step_sel.addWidget(self.cmb_step, 1)
        v.addLayout(step_sel)

        v.addWidget(_sep())

        # VFO-swap knoppen
        swap_row = QHBoxLayout(); swap_row.setSpacing(2)
        for label, sig in [("A→B", self.sig_ab), ("A≈B", self.sig_asb),
                            ("V/M", self.sig_vm)]:
            b = RadioButton(label, small=True)
            b.clicked.connect(sig)
            swap_row.addWidget(b)
        v.addLayout(swap_row)

        mem_row = QHBoxLayout(); mem_row.setSpacing(2)
        for label, sig in [("M→A", self.sig_ma), ("A→M", self.sig_am)]:
            b = RadioButton(label, small=True)
            b.clicked.connect(sig)
            mem_row.addWidget(b)
        v.addLayout(mem_row)

        v.addStretch()

    def _set_vfoa_tx(self):
        self.btn_vfoa_tx.setChecked(True)
        self.btn_vfob_tx.setChecked(False)
        self.sig_vfoa_tx.emit()

    def _set_vfob_tx(self):
        self.btn_vfoa_tx.setChecked(False)
        self.btn_vfob_tx.setChecked(True)
        self.sig_vfob_tx.emit()

    def _change_step(self, idx: int):
        self._step_idx = idx
        self._step_lbl.setText(self._STEP_LABELS[idx])

    def _freq_up(self):
        self.sig_freq_up.emit(self._STEPS[self._step_idx])

    def _freq_down(self):
        self.sig_freq_dn.emit(self._STEPS[self._step_idx])


# ── Band + Mode paneel ────────────────────────────────────────────────────────

class BandModePanel(QWidget):
    sig_band = Signal(str)   # "160m", "80m", …
    sig_mode = Signal(str)   # "LSB", "USB", "CW", …

    _BANDS = [
        ("1.8", "160m"), ("3.5", "80m"),  ("7", "40m"),
        ("10",  "30m"),  ("14",  "20m"),  ("18", "17m"),
        ("21",  "15m"),  ("24.5","12m"),  ("28/29","10m"),
        ("GEN", "GEN"),  ("50",  "6m"),   ("ENT", "ENT"),
    ]
    _MODES = [
        ("SSB",    ["LSB", "USB"]),
        ("AM/FM",  ["AM",  "FM"]),
        ("CW",     ["CW",  "CW-R"]),
        ("RTTY/PKT",["RTTY","PKT-L"]),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(150)
        self._mode_idx = {"SSB": 0, "AM/FM": 0, "CW": 0, "RTTY/PKT": 0}
        self._build()

    def _build(self):
        v = QVBoxLayout(self)
        v.setContentsMargins(4, 4, 4, 4)
        v.setSpacing(2)

        v.addWidget(_lbl("BAND", tiny=True))
        grid = QGridLayout()
        grid.setSpacing(2)
        self._band_btns: dict[str, QPushButton] = {}
        row, col = 0, 0
        for label, band in self._BANDS:
            b = RadioButton(label, small=True)
            b.clicked.connect(lambda _, bnd=band: self._on_band(bnd))
            grid.addWidget(b, row, col)
            self._band_btns[band] = b
            col += 1
            if col == 4:
                col = 0; row += 1
        v.addLayout(grid)

        v.addWidget(_sep())
        v.addWidget(_lbl("MODE", tiny=True))

        self._mode_btns: dict[str, QPushButton] = {}
        for group_label, variants in self._MODES:
            b = RadioButton(group_label, checkable=True, small=True)
            b.clicked.connect(lambda _, gl=group_label, vs=variants: self._on_mode(gl, vs))
            self._mode_btns[group_label] = b
            v.addWidget(b)

        v.addStretch()

    def _on_band(self, band: str):
        # Deselecteer alle andere bandknoppen
        for bnd, btn in self._band_btns.items():
            btn.setChecked(bnd == band)
        self.sig_band.emit(band)

    def _on_mode(self, group: str, variants: list[str]):
        # Deselecteer andere groepen
        for gl, btn in self._mode_btns.items():
            btn.setChecked(gl == group)
        # Toggle binnen de groep
        idx = self._mode_idx[group]
        self._mode_idx[group] = (idx + 1) % len(variants)
        self.sig_mode.emit(variants[idx])

    def set_band(self, band: str):
        for bnd, btn in self._band_btns.items():
            btn.setChecked(bnd == band)

    def set_mode(self, mode: str):
        mode_upper = mode.upper()
        for gl, variants in self._MODES:
            if any(v.upper() == mode_upper for v in variants):
                for g2, btn in self._mode_btns.items():
                    btn.setChecked(g2 == gl)
                return


# ── Rechts: ATT/IPO/R.FLT/NB + gain + CLAR ───────────────────────────────────

class RightPanel(QWidget):
    sig_att    = Signal(int)    # 0-3
    sig_ipo    = Signal(int)    # 0-2
    sig_rflt   = Signal(str)
    sig_nb     = Signal(int)    # 0-2
    sig_nr     = Signal(bool)
    sig_af     = Signal(int)
    sig_rf     = Signal(int)
    sig_sql    = Signal(int)   # squelch 0-255
    sig_rxclar = Signal(bool)
    sig_txclar = Signal(bool)
    sig_clar_clear = Signal()
    sig_clar_up    = Signal(int)
    sig_clar_dn    = Signal(int)

    _ATT_LABELS  = ["ATT OFF", "-6dB",  "-12dB",  "-18dB"]
    _IPO_LABELS  = ["IPO ON",  "AMP1",  "AMP2"]
    _RFLT_LABELS = ["AUTO",    "3kHz",  "6kHz",   "15kHz"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(130)
        self._att_idx  = 0
        self._ipo_idx  = 1
        self._rflt_idx = 0
        self._nb_idx   = 0
        self._build()

    def _build(self):
        v = QVBoxLayout(self)
        v.setContentsMargins(4, 4, 4, 4)
        v.setSpacing(3)

        # ATT
        row1 = QHBoxLayout(); row1.setSpacing(2)
        self.btn_att = RadioButton("ATT", small=True)
        self._att_lbl = _lbl(self._ATT_LABELS[0], tiny=True)
        self.btn_att.clicked.connect(self._cycle_att)
        row1.addWidget(self.btn_att)
        row1.addWidget(self._att_lbl, 1)
        v.addLayout(row1)

        # IPO
        row2 = QHBoxLayout(); row2.setSpacing(2)
        self.btn_ipo = RadioButton("IPO", small=True)
        self._ipo_lbl = _lbl(self._IPO_LABELS[1], tiny=True)
        self.btn_ipo.clicked.connect(self._cycle_ipo)
        row2.addWidget(self.btn_ipo)
        row2.addWidget(self._ipo_lbl, 1)
        v.addLayout(row2)

        # R.FLT
        row3 = QHBoxLayout(); row3.setSpacing(2)
        self.btn_rflt = RadioButton("R.FLT", small=True)
        self._rflt_lbl = _lbl(self._RFLT_LABELS[0], tiny=True)
        self.btn_rflt.clicked.connect(self._cycle_rflt)
        row3.addWidget(self.btn_rflt)
        row3.addWidget(self._rflt_lbl, 1)
        v.addLayout(row3)

        # NB
        row4 = QHBoxLayout(); row4.setSpacing(2)
        self.btn_nb = RadioButton("NB", small=True)
        self._nb_lbl = _lbl("OFF", tiny=True)
        self.btn_nb.clicked.connect(self._cycle_nb)
        row4.addWidget(self.btn_nb)
        row4.addWidget(self._nb_lbl, 1)
        v.addLayout(row4)

        # DNR
        self.btn_nr = LedButton("DNR", LED_ORANGE, checkable=True, small=True)
        self.btn_nr.toggled.connect(self.sig_nr)
        v.addWidget(self.btn_nr)

        v.addWidget(_sep())

        # AF GAIN
        af_row = QHBoxLayout(); af_row.addWidget(_lbl("AF GAIN", tiny=True))
        af_row.addStretch()
        self._af_val = _lbl("180", tiny=True); af_row.addWidget(self._af_val)
        v.addLayout(af_row)
        self.sld_af = QSlider(Qt.Horizontal)
        self.sld_af.setRange(0, 255); self.sld_af.setValue(180)
        self.sld_af.setFixedHeight(18); self.sld_af.setStyleSheet(_slider_qss())
        self.sld_af.valueChanged.connect(lambda val: [
            self._af_val.setText(str(val)), self.sig_af.emit(val)])
        v.addWidget(self.sld_af)

        # RF GAIN
        rf_row = QHBoxLayout(); rf_row.addWidget(_lbl("RF GAIN", tiny=True))
        rf_row.addStretch()
        self._rf_val = _lbl("255", tiny=True); rf_row.addWidget(self._rf_val)
        v.addLayout(rf_row)
        self.sld_rf = QSlider(Qt.Horizontal)
        self.sld_rf.setRange(0, 255); self.sld_rf.setValue(255)
        self.sld_rf.setFixedHeight(18); self.sld_rf.setStyleSheet(_slider_qss())
        self.sld_rf.valueChanged.connect(lambda val: [
            self._rf_val.setText(str(val)), self.sig_rf.emit(val)])
        v.addWidget(self.sld_rf)

        # SQUELCH
        sql_row = QHBoxLayout(); sql_row.addWidget(_lbl("SQL", tiny=True))
        sql_row.addStretch()
        self._sql_val = _lbl("0", tiny=True); sql_row.addWidget(self._sql_val)
        v.addLayout(sql_row)
        self.sld_sql = QSlider(Qt.Horizontal)
        self.sld_sql.setRange(0, 255); self.sld_sql.setValue(0)
        self.sld_sql.setFixedHeight(18); self.sld_sql.setStyleSheet(_slider_qss())
        self.sld_sql.valueChanged.connect(lambda val: [
            self._sql_val.setText(str(val)), self.sig_sql.emit(val)])
        v.addWidget(self.sld_sql)

        v.addWidget(_sep())

        # CLAR
        self.btn_rxclar = LedButton("RX CLAR", LED_GREEN,  checkable=True, small=True)
        self.btn_txclar = LedButton("TX CLAR", LED_ORANGE, checkable=True, small=True)
        self.btn_rxclar.toggled.connect(self.sig_rxclar)
        self.btn_txclar.toggled.connect(self.sig_txclar)
        v.addWidget(self.btn_rxclar)
        v.addWidget(self.btn_txclar)

        clar_btns = QHBoxLayout(); clar_btns.setSpacing(2)
        btn_cup   = RadioButton("▲", small=True)
        btn_cclr  = RadioButton("CLR", small=True)
        btn_cdn   = RadioButton("▼", small=True)
        btn_cup.clicked.connect(lambda: self.sig_clar_up.emit(100))
        btn_cclr.clicked.connect(self.sig_clar_clear)
        btn_cdn.clicked.connect(lambda: self.sig_clar_dn.emit(100))
        for b in (btn_cup, btn_cclr, btn_cdn):
            clar_btns.addWidget(b)
        v.addLayout(clar_btns)

        v.addStretch()

    # ── Statuskleur: dim = standaard, oranje = actief ─────────────────────────

    _DEFAULT_IDX = {"att": 0, "ipo": 1, "rflt": 0, "nb": 0}

    @staticmethod
    def _apply_status(label, text: str, is_active: bool):
        """Zet tekst + kleur op een statuslabel (oranje als actief, dim als standaard)."""
        label.setText(text)
        color = LED_ORANGE if is_active else TEXT_DIM
        label.setStyleSheet(
            f"color:{color}; font-size:6pt; background:transparent; font-weight:{'bold' if is_active else 'normal'};")

    def _cycle_att(self):
        self._att_idx = (self._att_idx + 1) % len(self._ATT_LABELS)
        self._apply_status(self._att_lbl, self._ATT_LABELS[self._att_idx],
                           self._att_idx != 0)
        self.sig_att.emit(self._att_idx)

    def _cycle_ipo(self):
        self._ipo_idx = (self._ipo_idx + 1) % len(self._IPO_LABELS)
        # IPO ON (idx=0) = bypass = 'actief' afwijkend; AMP1 (idx=1) = standaard
        self._apply_status(self._ipo_lbl, self._IPO_LABELS[self._ipo_idx],
                           self._ipo_idx != 1)
        self.sig_ipo.emit(self._ipo_idx)

    def _cycle_rflt(self):
        self._rflt_idx = (self._rflt_idx + 1) % len(self._RFLT_LABELS)
        self._apply_status(self._rflt_lbl, self._RFLT_LABELS[self._rflt_idx],
                           self._rflt_idx != 0)
        self.sig_rflt.emit(self._RFLT_LABELS[self._rflt_idx])

    def _cycle_nb(self):
        NB_LABELS = ["OFF", "NARROW", "WIDE"]
        self._nb_idx = (self._nb_idx + 1) % 3
        self._apply_status(self._nb_lbl, NB_LABELS[self._nb_idx],
                           self._nb_idx != 0)
        self.sig_nb.emit(self._nb_idx)

    def set_att(self, idx: int):
        self._att_idx = idx % len(self._ATT_LABELS)
        self._apply_status(self._att_lbl, self._ATT_LABELS[self._att_idx],
                           self._att_idx != 0)

    def set_ipo(self, idx: int):
        self._ipo_idx = idx % len(self._IPO_LABELS)
        self._apply_status(self._ipo_lbl, self._IPO_LABELS[self._ipo_idx],
                           self._ipo_idx != 1)


# ── Zendvermogen paneel ───────────────────────────────────────────────────────

class PowerPanel(QWidget):
    """
    TX-vermogen + alle TX-meters.

    Lay-out (van boven naar beneden):
      TX POWER label + VFD-getal
      Horizontale slider (5-100 W)
      Grote PTT-knop
      ─────────────
      VDD  ████░░░░  13.8 V
      ID   ████░░░░  8.5 A
      COMP ████░░░░  0 dB
    """

    sig_power = Signal(int)    # 5–100 W
    sig_ptt   = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(160)
        self._build()

    def _build(self):
        v = QVBoxLayout(self)
        v.setContentsMargins(4, 6, 4, 6)
        v.setSpacing(5)

        # ── TX POWER ──────────────────────────────────────────────────────────
        v.addWidget(_lbl("TX POWER", tiny=True))

        self._pwr_display = QLabel("100 W")
        self._pwr_display.setAlignment(Qt.AlignCenter)
        self._pwr_display.setStyleSheet(f"""
            QLabel {{
                background: {BG_PANEL};
                color: {VFD_AMBER};
                font-family: Consolas;
                font-size: 18pt;
                font-weight: bold;
                border: 1px solid {BORDER};
                border-radius: 2px;
                padding: 2px;
            }}
        """)
        self._pwr_display.setFixedHeight(44)
        v.addWidget(self._pwr_display)

        self.sld_power = QSlider(Qt.Horizontal)
        self.sld_power.setRange(5, 100)
        self.sld_power.setValue(100)
        self.sld_power.setFixedHeight(20)
        self.sld_power.setStyleSheet(_slider_qss())
        self.sld_power.valueChanged.connect(self._on_power)
        v.addWidget(self.sld_power)

        mm = QHBoxLayout()
        mm.addWidget(_lbl("5 W", tiny=True))
        mm.addStretch()
        mm.addWidget(_lbl("100 W", tiny=True))
        v.addLayout(mm)

        v.addWidget(_sep())

        # ── PTT ──────────────────────────────────────────────────────────────
        self.btn_ptt = QPushButton("ON AIR")
        self.btn_ptt.setCheckable(True)
        self.btn_ptt.setFixedHeight(42)
        self.btn_ptt.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.btn_ptt.toggled.connect(self.sig_ptt)
        self._ptt_style_normal()
        v.addWidget(self.btn_ptt)

        v.addWidget(_sep())

        # ── TX-meters (VDD, ID, COMP) — SWR en ALC staan in BEDIENING-paneel ──
        v.addWidget(_lbl("TX METERS", tiny=True))

        _VDD = [(128, "10V",   "#00BB44"),
                (178, "12V",   "#44CC44"),
                (222, "13.8",  "#88FF44"),
                (242, "15V",   "#FFCC00")]

        _ID  = [( 43, " 5A", "#00BB44"),
                ( 85, "10A", "#88CC00"),
                (128, "15A", "#FFAA00"),
                (170, "20A", "#FF6600"),
                (213, "25A", "#FF2020")]

        _CMP = [( 43, " 5",  "#FFCC00"),
                ( 85, "10",  "#FFAA00"),
                (128, "15",  "#FF8800"),
                (170, "20",  "#FF5500"),
                (213, "25",  "#FF2020"),
                (243, "30",  "#DD0000")]

        # Dummy-attributen zodat mainwindow.py set_swr/set_alc kan aanroepen
        # zonder AttributeError — waarden gaan nu alleen naar BEDIENING-paneel
        self.m_swr  = None
        self.m_alc  = None
        self.m_vdd  = TxMeterBar("VDD",  _VDD)
        self.m_id   = TxMeterBar("ID",   _ID)
        self.m_comp = TxMeterBar("COMP", _CMP)

        for meter in (self.m_vdd, self.m_id, self.m_comp):
            v.addWidget(meter)

        v.addStretch()

    # ── Publieke setters ──────────────────────────────────────────────────────

    def _on_power(self, val: int):
        self._pwr_display.setText(f"{val} W")
        self.sig_power.emit(val)

    def set_power(self, pct: int):
        self.sld_power.setValue(max(5, min(100, pct)))

    def _ptt_style_normal(self):
        from .theme import BTN_NORMAL, BTN_HOVER, BORDER
        self.btn_ptt.setStyleSheet(f"""
            QPushButton {{
                background: {BTN_NORMAL};
                color: #888888;
                border: 1px solid {BORDER};
                border-radius: 3px;
                font-size: 11pt;
                font-weight: bold;
                text-align: center;
            }}
            QPushButton:hover {{ background: {BTN_HOVER}; color: #AAAAAA; }}
            QPushButton:pressed {{ background: #111; }}
        """)

    def set_tx_state(self, on: bool):
        """Verander PTT-knop achtergrond: rood bij TX, normaal bij RX."""
        btn = self.btn_ptt
        btn.blockSignals(True)
        btn.setChecked(on)
        btn.blockSignals(False)
        if on:
            btn.setStyleSheet("""
                QPushButton {
                    background: #7A0000;
                    color: #FF4444;
                    border: 2px solid #FF2020;
                    border-radius: 3px;
                    font-size: 11pt;
                    font-weight: bold;
                    text-align: center;
                }
                QPushButton:hover { background: #9A0000; }
            """)
        else:
            self._ptt_style_normal()

    def set_swr(self, raw: int, text: str = ""):
        pass   # SWR staat in BEDIENING-paneel

    def set_alc(self, raw: int, text: str = ""):
        pass   # ALC staat in BEDIENING-paneel

    def set_vdd(self, raw: int, text: str = ""):
        self.m_vdd.set_value(raw, text)

    def set_id(self, raw: int, text: str = ""):
        self.m_id.set_value(raw, text)

    def set_comp(self, raw: int, text: str = ""):
        self.m_comp.set_value(raw, text)


# ── Gedeelde stijlen ─────────────────────────────────────────────────────────

def _combobox_qss() -> str:
    return f"""
        QComboBox {{
            background:{BG_SURFACE}; color:{TEXT_H1};
            border:1px solid {BORDER}; padding:1px 4px;
            font-size:7pt; border-radius:2px;
        }}
        QComboBox::drop-down {{ border:none; width:14px; }}
        QComboBox QAbstractItemView {{
            background:{BG_SURFACE}; color:{TEXT_H1};
            selection-background-color:{ACCENT};
            font-size:7pt;
        }}
    """


def _slider_qss(vertical: bool = False) -> str:
    handle_w = "6px" if vertical else "10px"
    handle_h = "10px" if vertical else "6px"
    return f"""
        QSlider::groove:{'vertical' if vertical else 'horizontal'} {{
            background: #1A1A1A;
            border: 1px solid {BORDER};
            {'width' if vertical else 'height'}: 4px;
            border-radius: 2px;
        }}
        QSlider::handle:{'vertical' if vertical else 'horizontal'} {{
            background: {ACCENT};
            border: 1px solid {BORDER};
            width: {handle_w};
            height: {handle_h};
            border-radius: 2px;
        }}
        QSlider::sub-page:horizontal {{
            background: {ACCENT};
            border-radius: 2px;
        }}
        QSlider::add-page:vertical {{
            background: {ACCENT};
            border-radius: 2px;
        }}
    """
