"""FT-950 Controller — hoofdvenster.

Layout (horizontaal, van links naar rechts):
  LeftPanel | ModePanel | DspPanel | DisplayPanel | VfoPanel | BandModePanel | RightPanel | PowerPanel

Alle panels zijn verbonden via signalen naar de CAT-laag.
De CAT-polling-callback update het display-paneel.
"""

import queue

from PySide6.QtCore    import Qt, QTimer, Signal
from PySide6.QtGui     import QFont, QKeySequence, QShortcut, QColor
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QFrame, QStatusBar, QMenuBar, QMenu,
    QSizePolicy, QMessageBox
)

from .theme   import (BG_BODY, BG_PANEL, BORDER, TEXT_H1, TEXT_DIM,
                      ACCENT, LED_GREEN, LED_RED, LED_ORANGE)
from .config  import Ft950Config, save_config
from .cat     import Ft950Cat
from .display import DisplayPanel
from .panels  import (CombinedLeftPanel, DspPanel, VfoPanel,
                      RightPanel, PowerPanel)
from .dialogs import (CatSettingsDialog, MemoryDialog, FreqKeypadDialog,
                      FreqMemoryDialog, SMeterCalibDialog)
from .config  import FreqEntry
from .i18n    import tr


_APP_QSS = f"""
QMainWindow, QWidget {{
    background: #1E1E1E;
}}
QMenuBar {{
    background: {BG_PANEL};
    color: {TEXT_H1};
    font-size: 8pt;
    border-bottom: 1px solid {BORDER};
}}
QMenuBar::item:selected {{
    background: {ACCENT};
    color: #000;
}}
QMenu {{
    background: {BG_PANEL};
    color: {TEXT_H1};
    border: 1px solid {BORDER};
    font-size: 8pt;
}}
QMenu::item:selected {{
    background: {ACCENT};
    color: #000;
}}
QStatusBar {{
    background: {BG_PANEL};
    color: {TEXT_DIM};
    font-size: 7pt;
    border-top: 1px solid {BORDER};
}}
"""


def _vsep() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.VLine)
    f.setStyleSheet(f"color:{BORDER}; max-width:1px;")
    return f


class MainWindow(QMainWindow):

    def __init__(self, cfg: Ft950Config):
        super().__init__()
        self._cfg    = cfg
        self._cat    = Ft950Cat(cfg)
        self._freq   = cfg.last_freq_hz
        self._mode   = cfg.last_mode
        self._mode_b = cfg.last_mode   # afzonderlijke VFO-B modus

        self.setWindowTitle("Yaesu FT-950 Controller")
        self.setStyleSheet(_APP_QSS)
        self.setMinimumWidth(1600)

        self._build_menu()
        self._build_ui()
        self._build_statusbar()
        self._wire_signals()
        self._wire_cat()

        # Thread-safe queues: CAT-thread schrijft, drain-timer leest in GUI-thread
        self._state_queue:  queue.Queue = queue.Queue()
        self._status_queue: queue.Queue = queue.Queue()
        self._meter_queue:  queue.Queue = queue.Queue()   # (type, payload)

        self._drain_timer = QTimer(self)
        self._drain_timer.timeout.connect(self._drain_queues)
        self._drain_timer.start(50)   # drain elke 50 ms

        # Restore venstergrootte
        self.resize(cfg.win_w, cfg.win_h)
        if cfg.win_x > 0 and cfg.win_y > 0:
            self.move(cfg.win_x, cfg.win_y)

        # Opgeslagen lettergroottes en font toepassen
        self._display.set_btn_font(cfg.band_btn_font)
        self._display.set_vfd_font(cfg.vfd_font)
        self._display.set_vfd_font_name(cfg.vfd_font_name)

        # Kalibratie S-meter toepassen
        self._display._smeter.set_calibration(cfg.smeter_cal)

        # Initialiseer display
        self._display.set_freq_a(self._freq)
        self._display.set_freq_b(cfg.last_vfob_hz)
        self._display.set_mode(self._mode)
        self._display.set_mode_b(self._mode_b)
        self._display.set_band(cfg.last_band)

        # Koppel display freq-signaal (VFD klik/scroll + knop) aan set_freq
        self._display.sig_freq_changed.connect(self._set_freq)

        # Band/mode vanuit de display-balk
        self._display.sig_band.connect(self._on_band)
        self._display.sig_mode.connect(self._on_mode)
        self._display.sig_mode_b.connect(self._on_mode_b)

        # Herstel alle opgeslagen instellingen
        self._restore_all_settings()

        # Sneltoets: F5 = verbinden/verbreken
        QShortcut(QKeySequence("F5"), self).activated.connect(self._toggle_connect)

    # ── Menu ─────────────────────────────────────────────────────────────────

    def _build_menu(self):
        mb = self.menuBar()

        # Radio
        m_radio = mb.addMenu(tr("Radio"))
        self._act_connect    = m_radio.addAction(tr("Verbinden (F5)"))
        self._act_disconnect = m_radio.addAction(tr("Verbreken"))
        m_radio.addSeparator()
        m_radio.addAction(tr("CAT Monitor…"),     self._open_cat_log)
        m_radio.addAction(tr("Instellingen…"),    self._open_settings)
        m_radio.addSeparator()
        m_radio.addAction(tr("Afsluiten"),        self.close)
        self._act_connect.triggered.connect(self._do_connect)
        self._act_disconnect.triggered.connect(self._do_disconnect)
        self._act_disconnect.setEnabled(False)

        # Geheugen
        m_mem = mb.addMenu(tr("Geheugen"))
        m_mem.addAction(tr("Frequentie-favorieten…"), self._open_freq_memories)
        m_mem.addSeparator()
        m_mem.addAction(tr("Radio geheugenkanalen…"), self._open_memories)

        # Weergave
        m_view = mb.addMenu(tr("Weergave"))
        m_view.addAction(tr("Lettergrootte display…"), self._open_display_fonts)
        m_view.addSeparator()
        m_view.addAction(tr("S-meter kalibreren…"),    self._open_smeter_calib)
        m_view.addSeparator()

        # Taal submenu
        m_lang = m_view.addMenu("Taal / Language")
        act_nl = m_lang.addAction("Nederlands")
        act_en = m_lang.addAction("English")
        act_nl.setCheckable(True)
        act_en.setCheckable(True)
        from .i18n import get_language
        act_nl.setChecked(get_language() == "nl")
        act_en.setChecked(get_language() == "en")
        act_nl.triggered.connect(lambda: self._set_language("nl", act_nl, act_en))
        act_en.triggered.connect(lambda: self._set_language("en", act_nl, act_en))

        # Help
        m_help = mb.addMenu("Help")
        m_help.addAction("Over…", self._show_about)

    # ── UI ───────────────────────────────────────────────────────────────────

    @staticmethod
    def _col(title: str, widget: QWidget, stretch: int = 0) -> QWidget:
        """Wikkel een paneel in een container met een koptekst erboven."""
        container = QWidget()
        v = QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(2)

        lbl = QLabel(title)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setFixedHeight(16)
        lbl.setStyleSheet(f"""
            QLabel {{
                color: {ACCENT};
                font-size: 7pt;
                font-weight: bold;
                font-family: Consolas;
                background: #181818;
                border-bottom: 1px solid #2A2A2A;
                padding-bottom: 1px;
            }}
        """)
        v.addWidget(lbl)
        v.addWidget(widget, 1)
        return container

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main = QHBoxLayout(central)
        main.setContentsMargins(6, 6, 6, 6)
        main.setSpacing(4)

        # 1+2. BEDIENING (CombinedLeftPanel)
        self._left = CombinedLeftPanel()
        self._mode_panel = self._left
        main.addWidget(self._col(tr("BEDIENING"), self._left))
        main.addWidget(_vsep())

        # DSP FILTER
        self._dsp_panel = DspPanel()
        main.addWidget(self._col(tr("DSP FILTER"), self._dsp_panel))
        main.addWidget(_vsep())

        # DISPLAY (strekt)
        self._display = DisplayPanel(
            vfob_font=self._cfg.vfob_font,
            clar_font=self._cfg.clar_font,
        )
        self._display.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        main.addWidget(self._col(tr("DISPLAY"), self._display), 1)
        main.addWidget(_vsep())

        # VFO
        self._vfo = VfoPanel()
        main.addWidget(self._col(tr("VFO"), self._vfo))
        main.addWidget(_vsep())

        # ONTVANGER
        self._right = RightPanel()
        main.addWidget(self._col(tr("ONTVANGER"), self._right))
        main.addWidget(_vsep())

        # ZENDER
        self._power_panel = PowerPanel()
        main.addWidget(self._col(tr("ZENDER"), self._power_panel))

    def _build_statusbar(self):
        sb = self.statusBar()

        # Links: verbindingsstatus + frequentie + modus
        self._sb_conn = QLabel(tr("⬤  Niet verbonden"))
        self._sb_conn.setStyleSheet(f"color:{TEXT_DIM}; font-size:7pt; padding:0 6px;")
        self._sb_freq = QLabel("")
        self._sb_freq.setStyleSheet(
            f"color:{ACCENT}; font-size:7pt; font-family:Consolas; padding:0 6px;")
        self._sb_mode = QLabel("")
        self._sb_mode.setStyleSheet(f"color:{TEXT_H1}; font-size:7pt; padding:0 6px;")
        sb.addWidget(self._sb_conn)
        sb.addWidget(self._sb_freq, 1)   # stretch → duwt badges naar rechts
        sb.addWidget(self._sb_mode)

        # ── Tijdsindicatoren voor statusbadges ────────────────────────────────
        _time_style = (f"color:{TEXT_H1}; font-family:Consolas; font-size:7pt;"
                       f" background:#1A1A1A; border:1px solid #333;"
                       f" border-radius:2px; padding:0 5px;")
        self._sb_utc  = QLabel("UTC --:--:--")
        self._sb_cest = QLabel("CEST --:--:--")
        self._sb_utc.setStyleSheet(_time_style)
        self._sb_cest.setStyleSheet(_time_style)
        sb.addPermanentWidget(self._sb_utc)
        sb.addPermanentWidget(self._sb_cest)

        # Statusbadges helemaal rechts (permanent = rechterzijde van statusbar)
        _badge_style = "padding:0 3px;"
        for badge in (self._display._badge_tx,    self._display._badge_busy,
                      self._display._badge_nar,   self._display._badge_split,
                      self._display._badge_nb,    self._display._badge_nr,
                      self._display._badge_fast,  self._display._badge_lock):
            badge.setStyleSheet(badge.styleSheet() + _badge_style)
            sb.addPermanentWidget(badge)

        # Timer die elk seconde de tijd bijwerkt
        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._update_clock)
        self._clock_timer.start(1000)
        self._update_clock()   # meteen tonen bij start

    def _update_clock(self):
        from datetime import datetime, timezone, timedelta
        now_utc  = datetime.now(timezone.utc)
        # CEST = Central European Summer Time = UTC+2
        # CET  = Central European (Winter) Time = UTC+1
        # Python's astimezone() gebruikt de lokale systeemtijdzone
        now_cest = now_utc.astimezone()   # lokale tijdzone (automatisch CET/CEST)
        self._sb_utc.setText(f"UTC {now_utc.strftime('%H:%M:%S')}")
        self._sb_cest.setText(f"CEST {now_cest.strftime('%H:%M:%S')}")

    # ── Signaalverbindingen ───────────────────────────────────────────────────

    def _wire_signals(self):
        # Left panel
        self._left.sig_power.connect(self._toggle_connect)
        self._left.sig_mox.connect(self._on_mox)
        self._left.sig_tune.connect(self._on_tune)
        self._left.sig_vox.connect(self._on_vox)
        self._left.sig_mute.connect(self._on_mute)
        self._left.sig_ant.connect(self._on_ant)

        # Mode panel
        self._mode_panel.sig_mic.connect(
            lambda v: self._cat.set_af_gain(v) if self._cat.connected else None)

        # DSP panel — knoppen
        self._dsp_panel.sig_narrow.connect(self._on_narrow)
        self._dsp_panel.sig_notch.connect(self._on_notch)
        self._dsp_panel.sig_cont.connect(self._on_contour)
        self._dsp_panel.sig_shift.connect(self._on_shift_toggle)
        self._dsp_panel.sig_width.connect(self._on_width_toggle)
        self._dsp_panel.sig_clear.connect(self._on_dsp_clear)
        # DSP panel — sliders/combos
        self._dsp_panel.sig_shift_hz.connect(self._on_shift_hz)
        self._dsp_panel.sig_cont_pos.connect(self._on_cont_pos)
        self._dsp_panel.sig_notch_hz.connect(self._on_notch_hz)
        self._dsp_panel.sig_width_code.connect(self._on_width_code)

        # Mode panel
        self._mode_panel.sig_agc.connect(self._on_agc)

        # VFO panel
        self._vfo.sig_freq_up.connect(self._step_up)
        self._vfo.sig_freq_dn.connect(self._step_down)
        self._vfo.sig_fast.connect(self._display.set_fast)
        self._vfo.sig_lock.connect(self._display.set_lock)
        self._vfo.sig_split.connect(self._on_split)
        self._vfo.sig_txw.connect(lambda on: None)
        self._vfo.sig_ab.connect(self._on_vfo_ab)
        self._vfo.sig_asb.connect(self._on_vfo_asb)
        self._vfo.sig_vm.connect(self._on_vm)
        self._vfo.sig_qmb_sto.connect(
            lambda: self._cat.send_raw("QI;") if self._cat.connected else None)
        self._vfo.sig_qmb_rcl.connect(
            lambda: self._cat.send_raw("QR;") if self._cat.connected else None)

        # VFO-B afstemming via scrollwiel
        self._display.sig_freq_b_changed.connect(self._on_freq_b_changed)

        # Band/mode
        # Band/mode: alleen vanuit het DisplayPanel (BandModePanel verwijderd)

        # Right panel
        self._right.sig_att.connect(
            lambda v: self._cat.set_att(v) if self._cat.connected else None)
        self._right.sig_ipo.connect(
            lambda v: self._cat.set_ipo(v) if self._cat.connected else None)
        self._right.sig_nb.connect(self._on_nb)
        self._right.sig_nr.connect(self._on_nr)
        self._right.sig_af.connect(
            lambda v: self._cat.set_af_gain(v) if self._cat.connected else None)
        self._right.sig_rf.connect(
            lambda v: self._cat.set_rf_gain(v) if self._cat.connected else None)
        self._right.sig_sql.connect(
            lambda v: self._cat.set_squelch(v) if self._cat.connected else None)
        self._right.sig_rxclar.connect(
            lambda on: self._cat.set_rx_clar(on) if self._cat.connected else None)
        self._right.sig_txclar.connect(
            lambda on: self._cat.set_tx_clar(on) if self._cat.connected else None)
        self._right.sig_clar_clear.connect(
            lambda: self._cat.clar_clear() if self._cat.connected else None)
        self._right.sig_clar_up.connect(
            lambda hz: self._cat.clar_up(hz) if self._cat.connected else None)
        self._right.sig_clar_dn.connect(
            lambda hz: self._cat.clar_down(hz) if self._cat.connected else None)

        # Power panel
        self._power_panel.sig_power.connect(
            lambda v: self._cat.set_power(v) if self._cat.connected else None)
        self._power_panel.sig_ptt.connect(self._on_ptt)

    def _wire_cat(self):
        # Callbacks schrijven ALLEEN naar thread-safe queues — nooit direct GUI!
        self._cat.on_status    = lambda c:     self._status_queue.put(c)
        self._cat.on_state     = lambda s:     self._state_queue.put(s)
        self._cat.on_freq      = lambda v, hz: self._state_queue.put({"freq_hz": hz})
        self._cat.on_mode      = lambda m:     self._state_queue.put({"mode": m})
        self._cat.on_smeter    = lambda v:     self._meter_queue.put(("smeter", v))
        self._cat.on_busy      = lambda b:     self._meter_queue.put(("busy",   b))
        self._cat.on_tx_meters = lambda d:     self._meter_queue.put(("tx", d))
        self._cat.on_tx_state  = lambda b:     self._meter_queue.put(("tx_state", b))
        self._cat.on_freq_b    = lambda hz:    self._state_queue.put({"freq_b": hz})
        self._cat.on_mode_b    = lambda m:     self._state_queue.put({"mode_b": m})
        self._cat.on_agc       = lambda a:     self._meter_queue.put(("agc", a))
        self._cat.on_af_gain   = lambda v:     self._meter_queue.put(("af", v))
        self._cat.on_rf_gain   = lambda v:     self._meter_queue.put(("rf", v))
        self._cat.on_squelch   = lambda v:     self._meter_queue.put(("sql", v))
        self._cat.on_log       = lambda d, x:  None

    # ── Queue drain (GUI-thread, elke 50 ms) ──────────────────────────────────

    def _drain_queues(self):
        try:
            self._drain_queues_impl()
        except Exception:
            pass   # log if needed; nooit GUI-thread laten crashen

    def _drain_queues_impl(self):
        # ── Status-queue ─────────────────────────────────────────────────────
        while not self._status_queue.empty():
            try:
                self._apply_status(self._status_queue.get_nowait())
            except queue.Empty:
                break

        # ── State-queue (IF; frequentie + modus) ─────────────────────────────
        last_state = None
        while not self._state_queue.empty():
            try:
                last_state = self._state_queue.get_nowait()
            except queue.Empty:
                break

        if last_state:
            if "freq_hz" in last_state and "mode" in last_state:
                hz   = last_state["freq_hz"]
                mode = last_state["mode"]
                if hz != self._freq:
                    self._freq = hz
                    self._display.set_freq_a(hz)
                    self._display._vfd_a.set_freq(hz)
                    self._sb_freq.setText(f"{hz / 1_000_000:.6f} MHz")
                self._apply_mode(mode)
                self._display.apply_state(last_state)
            elif "freq_hz" in last_state:
                hz = last_state["freq_hz"]
                if hz != self._freq:
                    self._freq = hz
                    self._display.set_freq_a(hz)
                    self._display._vfd_a.set_freq(hz)
                    self._sb_freq.setText(f"{hz / 1_000_000:.6f} MHz")
            elif "mode" in last_state:
                self._apply_mode(last_state["mode"])
            elif "freq_b" in last_state:
                self._display.set_freq_b(last_state["freq_b"])
            elif "mode_b" in last_state:
                m = last_state["mode_b"]
                if m != self._mode_b:
                    self._mode_b = m
                    self._display.set_mode_b(m)

        # ── Meter-queue (smeter / tx-meters / agc) ────────────────────────────
        while not self._meter_queue.empty():
            try:
                kind, payload = self._meter_queue.get_nowait()
                if kind == "smeter":
                    self._display.set_smeter(payload)
                    self._last_smeter_raw = payload
                elif kind == "busy":
                    self._display.set_busy(payload)
                elif kind == "tx":
                    self._update_tx_meters(payload)
                elif kind == "tx_state":
                    self._set_tx_active(payload, from_meter=True)
                elif kind == "agc":
                    AGC_IDX = {"OFF":0,"FAST":1,"MID":2,"SLOW":3,
                               "AUTO":4,"A-FAST":4,"A-MID":4,"A-SLOW":4}
                    self._mode_panel.set_agc(AGC_IDX.get(payload, 4))
                    self._mode_panel._agc_lbl.setText(payload)
                elif kind == "af":
                    # Blokkeer het signaal zodat de CAT niet teruggetriggerd wordt
                    self._right.sld_af.blockSignals(True)
                    self._right.sld_af.setValue(payload)
                    self._right._af_val.setText(str(payload))
                    self._right.sld_af.blockSignals(False)
                elif kind == "rf":
                    self._right.sld_rf.blockSignals(True)
                    self._right.sld_rf.setValue(payload)
                    self._right._rf_val.setText(str(payload))
                    self._right.sld_rf.blockSignals(False)
                elif kind == "sql":
                    self._right.sld_sql.blockSignals(True)
                    self._right.sld_sql.setValue(payload)
                    self._right._sql_val.setText(str(payload))
                    self._right.sld_sql.blockSignals(False)
            except queue.Empty:
                break

    def _apply_status(self, connected: bool):
        # Verbinden/Verbreken knop linksboven
        self._left.set_power(connected)

        if connected:
            self._sb_conn.setText(tr("⬤  Verbonden"))
            self._sb_conn.setStyleSheet(f"color:{LED_GREEN}; font-size:7pt; padding:0 6px;")
            self._act_connect.setEnabled(False)
            self._act_disconnect.setEnabled(True)
        else:
            self._sb_conn.setText(tr("⬤  Niet verbonden"))
            self._sb_conn.setStyleSheet(f"color:{TEXT_DIM}; font-size:7pt; padding:0 6px;")
            self._act_connect.setEnabled(True)
            self._act_disconnect.setEnabled(False)
            self._display.set_smeter(0)

    def _apply_mode(self, mode: str):
        if mode == self._mode:
            return
        self._mode = mode
        self._display.set_mode(mode)
        self._band_mode.set_mode(mode)
        self._sb_mode.setText(mode)

    # ── Knoppen ───────────────────────────────────────────────────────────────

    def _set_tx_active(self, on: bool, from_meter: bool = False):
        """Centrale TX-schakelaar: badge (knipperend), ON AIR-knop, display.

        from_meter=True: aanroep vanuit TX-meter poll (hardware PTT).
        from_meter=False: aanroep vanuit GUI-knop.
        GUI-initiated TX wordt niet overschreven door meter-detectie.
        """
        if from_meter and getattr(self, "_ptt_from_gui", False):
            return  # GUI heeft prioriteit over meter-detectie

        self._power_panel.set_tx_state(on)
        if on:
            self._display._badge_busy.set_active(False)
            self._tx_blink_state = True
            self._display._badge_tx.set_active(True)
            if not hasattr(self, "_tx_blink_timer"):
                self._tx_blink_timer = QTimer(self)
                self._tx_blink_timer.timeout.connect(self._blink_tx)
            self._tx_blink_timer.start(400)
        else:
            if hasattr(self, "_tx_blink_timer"):
                self._tx_blink_timer.stop()
            self._display._badge_tx.set_active(False)

    def _blink_tx(self):
        self._tx_blink_state = not self._tx_blink_state
        self._display._badge_tx.set_active(self._tx_blink_state)

    @staticmethod
    def _hz_to_mode(hz: int) -> str | None:
        """Geeft de standaard mode terug voor een frequentie (op basis van band)."""
        for lo, hi, mode in (
            (1_800_000,  2_000_000,  "LSB"),   # 160m
            (3_500_000,  4_000_000,  "LSB"),   # 80m
            (7_000_000,  7_300_000,  "LSB"),   # 40m
            (10_100_000, 10_150_000, "CW"),    # 30m
            (14_000_000, 14_350_000, "USB"),   # 20m
            (18_068_000, 18_168_000, "USB"),   # 17m
            (21_000_000, 21_450_000, "USB"),   # 15m
            (24_890_000, 24_990_000, "USB"),   # 12m
            (28_000_000, 29_700_000, "USB"),   # 10m
            (50_000_000, 54_000_000, "FM"),    # 6m
        ):
            if lo <= hz <= hi:
                return mode
        return None

    def _on_freq_b_changed(self, hz: int):
        """VFO-B gewijzigd via scrollwiel → stuur FB; naar radio + auto-mode."""
        if self._cat.connected:
            self._cat.set_freq_b(hz)
        mode = self._hz_to_mode(hz)
        if mode and mode != self._mode_b:
            self._on_mode_b(mode)

    def _on_mox(self, on: bool):
        self._ptt_from_gui = on
        if self._cat.connected:
            self._cat.set_ptt(on)
        self._set_tx_active(on)

    def _on_ptt(self, on: bool):
        self._ptt_from_gui = on
        if self._cat.connected:
            self._cat.set_ptt(on)
        self._set_tx_active(on)
        self._left.btn_mox.blockSignals(True)
        self._left.btn_mox.setChecked(on)
        self._left.btn_mox.blockSignals(False)

    def _on_tune(self, state: int):
        if self._cat.connected:
            self._cat.set_tuner(state)

    def _on_vox(self, on: bool):
        pass   # VOX is radio-intern, geen CAT-commando nodig

    def _on_mute(self, on: bool):
        """Dempen: AF gain → 0 + knipperende indicator; herstellen: vorige waarde."""
        if on:
            self._mute_saved_af = self._right.sld_af.value()
            if self._cat.connected:
                self._cat.set_af_gain(0)
            self._right.sld_af.blockSignals(True)
            self._right.sld_af.setValue(0)
            self._right._af_val.setText("0")
            self._right.sld_af.blockSignals(False)
            # Start knippertimer
            self._mute_blink_state = True
            if not hasattr(self, "_mute_timer"):
                self._mute_timer = QTimer(self)
                self._mute_timer.timeout.connect(self._blink_mute)
            self._mute_timer.start(500)
        else:
            # Stop knippertimer, herstel vaste tekst
            if hasattr(self, "_mute_timer"):
                self._mute_timer.stop()
            self._left.btn_mute.setText("🔇  MUTE")
            restore = getattr(self, "_mute_saved_af", 180)
            if self._cat.connected:
                self._cat.set_af_gain(restore)
            self._right.sld_af.blockSignals(True)
            self._right.sld_af.setValue(restore)
            self._right._af_val.setText(str(restore))
            self._right.sld_af.blockSignals(False)

    def _blink_mute(self):
        """Laat het rode puntje knipperen zolang MUTE actief is."""
        self._mute_blink_state = not self._mute_blink_state
        self._left.btn_mute.setText(
            "🔴  MUTE" if self._mute_blink_state else "⚫  MUTE")

    def _on_ant(self, n: int):
        if self._cat.connected:
            self._cat.send_raw(f"AN0{n};")
        self._display.set_ant(str(n))

    def _on_agc(self, idx: int):
        if self._cat.connected:
            self._cat.set_agc(idx)
        agc_names = ["OFF", "FAST", "MID", "SLOW", "AUTO"]
        self._display.set_agc(agc_names[idx % len(agc_names)])
        self._mode_panel.set_agc(idx)

    # ── DSP filter handlers ────────────────────────────────────────────────────

    def _on_nb(self, mode: int):
        """NB-knop: 0=off, 1=narrow, 2=wide."""
        if self._cat.connected:
            self._cat.set_nb(mode)
        self._display.set_nb(mode > 0)

    def _on_nr(self, on: bool):
        """DNR-knop."""
        if self._cat.connected:
            self._cat.set_nr(on)
        self._display.set_nr(on)

    def _on_narrow(self, on: bool):
        if self._cat.connected:
            self._cat.set_narrow(on)
        self._display.set_nar(on)

    def _on_notch(self, on: bool):
        if self._cat.connected:
            self._cat.set_notch(on)
        self._display.set_dsp_notch(on)

    def _on_contour(self, on: bool):
        if self._cat.connected:
            self._cat.set_contour(on)
        self._display.set_dsp_contour(on)

    def _on_shift_toggle(self, on: bool):
        """IF-shift aan/uit (0 Hz = geen verschuiving)."""
        hz = 0 if not on else 300    # standaard +300 Hz als ingeschakeld
        if self._cat.connected:
            self._cat.set_if_shift(hz)
        self._display.set_dsp_shift(on, 0.5 + hz / 2000.0)

    def _on_width_toggle(self, on: bool):
        """Smalte filter aan/uit (code 0=breed/2.4kHz, 7=smal/500Hz)."""
        code = 7 if on else 13   # 7=500Hz narrow, 13=2400Hz wide
        if self._cat.connected:
            self._cat.set_if_width(code)
        self._display.set_dsp_width(on, 0.3 if on else 0.9)

    def _on_dsp_clear(self):
        """Reset IF-shift naar 0, schakel contour/notch uit."""
        if self._cat.connected:
            self._cat.set_if_shift(0)
            self._cat.set_contour(False)
            self._cat.set_notch(False)
        self._dsp_panel.btn_shift.setChecked(False)
        self._dsp_panel.btn_cont.setChecked(False)
        self._dsp_panel.btn_notch.setChecked(False)
        self._dsp_panel.sld_shift.setValue(0)
        self._display.set_dsp_shift(False)
        self._display.set_dsp_contour(False)
        self._display.set_dsp_notch(False)

    def _on_shift_hz(self, hz: int):
        """IF-shift slider waarde gewijzigd — alleen sturen als knop actief."""
        if self._dsp_panel.btn_shift.isChecked() and self._cat.connected:
            self._cat.set_if_shift(hz)
        pos = 0.5 + hz / 2000.0
        self._display.set_dsp_shift(self._dsp_panel.btn_shift.isChecked(), pos)

    def _on_cont_pos(self, code: int):
        """Contour-schuif waarde gewijzigd."""
        if self._dsp_panel.btn_cont.isChecked() and self._cat.connected:
            self._cat.set_contour(True, code)
        self._display.set_dsp_contour(self._dsp_panel.btn_cont.isChecked(),
                                      code / 30.0)

    def _on_notch_hz(self, hz: int):
        """Notch-schuif waarde gewijzigd."""
        if self._dsp_panel.btn_notch.isChecked() and self._cat.connected:
            self._cat.set_notch(True, hz)
        self._display.set_dsp_notch(self._dsp_panel.btn_notch.isChecked(),
                                    hz / 3000.0)

    def _on_width_code(self, code: int):
        """IF-breedte combobox gewijzigd."""
        if self._dsp_panel.btn_width.isChecked() and self._cat.connected:
            self._cat.set_if_width(code)
        self._display.set_dsp_width(self._dsp_panel.btn_width.isChecked())

    def _on_split(self, on: bool):
        if self._cat.connected:
            self._cat.set_split(on)
        self._display.set_split(on)

    def _on_vfo_ab(self):
        if self._cat.connected:
            self._cat.vfo_a_to_b()

    def _on_vfo_asb(self):
        if self._cat.connected:
            self._cat.vfo_swap()

    def _on_vm(self):
        if self._cat.connected:
            self._cat.send_raw("VM;")

    def _on_band(self, band: str):
        if band == "GEN":
            self._open_freq_keypad()
            return

        BAND_FREQ = {
            "160m": 1_830_000, "80m": 3_600_000, "40m": 7_100_000,
            "30m": 10_120_000, "20m": 14_195_000, "17m": 18_100_000,
            "15m": 21_200_000, "12m": 24_910_000, "10m": 28_500_000,
            "6m":  50_150_000,
        }
        # Standaard mode per band (LSB onder 10 MHz, USB erboven)
        BAND_MODE = {
            "160m": "LSB", "80m": "LSB", "40m": "LSB",
            "30m":  "CW",
            "20m":  "USB", "17m": "USB", "15m": "USB",
            "12m":  "USB", "10m": "USB", "6m":  "FM",
        }
        hz = BAND_FREQ.get(band)
        if hz:
            self._set_freq(hz)
        mode = BAND_MODE.get(band)
        if mode:
            self._on_mode(mode)
        self._display.set_band(band)

    def _open_freq_keypad(self):
        dlg = FreqKeypadDialog(current_hz=0, parent=self)   # 0 = lege invoer
        if dlg.exec():
            hz = dlg.get_freq_hz()
            self._set_freq(hz)
            self._display.set_band("GEN")

    def _on_mode(self, mode: str):
        if self._cat.connected:
            self._cat.set_mode(mode)
        self._display.set_mode(mode)   # update ook de bovenste modusknoppen
        self._sb_mode.setText(mode)
        self._mode = mode

    def _on_mode_b(self, mode: str):
        """Stel VFO-B mode in via VS1; MD0X; VS0; sequentie."""
        self._mode_b = mode
        self._display.set_mode_b(mode)
        if self._cat.connected:
            self._cat.send_raw("VS1;")          # selecteer VFO-B
            self._cat.set_mode(mode)            # stel mode in
            self._cat.send_raw("VS0;")          # terug naar VFO-A

    def _step_up(self, step: int):
        self._set_freq(self._freq + step)

    def _step_down(self, step: int):
        self._set_freq(max(30_000, self._freq - step))

    def _set_freq(self, hz: int):
        hz = max(30_000, min(56_000_000, hz))
        self._freq = hz
        self._display.set_freq_a(hz)
        mhz = hz / 1_000_000
        self._sb_freq.setText(f"{mhz:.6f} MHz")
        if self._cat.connected:
            self._cat.set_freq_a(hz)

    # ── Meter-update (aangeroepen vanuit _drain_queues, GUI-thread) ──────────

    def _update_tx_meters(self, tx: dict):
        """Update alle TX-meteraflezing in de PowerPanel."""
        pp = self._power_panel

        swr_raw = tx.get("swr") or 0
        # SWR-waarde: raw 0-255 → 1.0 – 3.0 (ruwe schaling)
        swr_val = 1.0 + (swr_raw / 255) * 2.0
        swr_txt = f"{swr_val:.1f}" if swr_raw > 0 else "—"
        pp.set_swr(swr_raw, swr_txt)
        # Ook SWR in het bediening-paneel bijwerken
        self._left.set_swr(swr_raw, swr_txt)

        alc_raw = tx.get("alc") or 0
        alc_pct = int(alc_raw / 255 * 100) if alc_raw else 0
        pp.set_alc(alc_raw, f"{alc_pct} %" if alc_raw else "—")
        # ALC ook in BEDIENING-paneel
        self._left.set_alc(alc_raw)

        vdd_raw = tx.get("vdd") or 0
        # VDD: raw 0-255 → 0–16 V  (nominaal 13.8 V ≈ raw ~220)
        vdd_v   = (vdd_raw / 255) * 16.0
        pp.set_vdd(vdd_raw, f"{vdd_v:.1f} V" if vdd_raw else "—")

        id_raw  = tx.get("id") or 0
        # ID: raw 0-255 → 0–30 A
        id_a    = (id_raw / 255) * 30.0
        pp.set_id(id_raw, f"{id_a:.1f} A" if id_raw else "—")

        comp_raw = tx.get("comp") or 0
        # COMP: raw 0-255 → 0–30 dB
        comp_db  = int((comp_raw / 255) * 30)
        pp.set_comp(comp_raw, f"{comp_db} dB" if comp_raw else "—")

    # ── Verbinden/verbreken ───────────────────────────────────────────────────

    def _toggle_connect(self):
        if self._cat.connected:
            self._do_disconnect()
        else:
            self._do_connect()

    def _do_connect(self):
        ok, msg = self._cat.connect()
        if not ok:
            QMessageBox.warning(self, tr("Verbinding mislukt"),
                                f"Cannot connect:\n{msg}\n\n"
                                "Check CAT settings (Radio → Settings…)")

    def _do_disconnect(self):
        self._cat.disconnect()

    # ── Dialogen ─────────────────────────────────────────────────────────────

    def _open_settings(self):
        dlg = CatSettingsDialog(self._cfg, self._cat, parent=self)
        dlg.exec()

    def _open_memories(self):
        dlg = MemoryDialog(self._cat, parent=self)
        dlg.exec()

    def _open_freq_memories(self):
        dlg = FreqMemoryDialog(
            cat           = self._cat,
            apply_eibi_fn = self._apply_eibi_record,
            apply_fav_fn  = self._recall_freq_entry,   # klik → radio instellen
            parent        = self,
        )
        dlg.set_current_entry(self._make_freq_entry())
        if dlg.exec():
            entry = dlg.get_selected()
            if entry:
                self._recall_freq_entry(entry)
            # Bewaar eventuele EIBI-wijzigingen
            from .config import save_eibi_records
            save_eibi_records(dlg._eibi_tab.get_records())

    def _apply_eibi_record(self, rec):
        """Stuur een EIBI-record naar radio en display (wordt bij rijklik aangeroepen)."""
        from .config import EibiRecord
        if not isinstance(rec, EibiRecord):
            return
        # Frequentie + modus
        hz = rec.freq_hz
        self._set_freq(hz)
        self._on_mode(rec.mode)
        # Volume, squelch, filter
        if self._cat.connected:
            self._cat.set_af_gain(rec.af_gain)
            self._cat.set_squelch(rec.sql)
            self._cat.set_narrow(rec.dsp_nar)
        # Schuiven bijwerken
        self._right.sld_af.blockSignals(True)
        self._right.sld_af.setValue(rec.af_gain)
        self._right._af_val.setText(str(rec.af_gain))
        self._right.sld_af.blockSignals(False)
        self._right.sld_sql.blockSignals(True)
        self._right.sld_sql.setValue(rec.sql)
        self._right._sql_val.setText(str(rec.sql))
        self._right.sld_sql.blockSignals(False)

    def _make_freq_entry(self) -> FreqEntry:
        """Maak een FreqEntry van de huidige radio-/UI-staat."""
        d = self._dsp_panel
        r = self._right
        e = FreqEntry(
            name         = f"{self._mode} {self._freq / 1_000_000:.3f} MHz",
            freq_hz      = self._freq,
            mode         = self._mode,
            band         = self._cfg.last_band,
            # DSP
            dsp_shift_on = d.btn_shift.isChecked(),
            dsp_shift_hz = d.sld_shift.value(),
            dsp_width_on = d.btn_width.isChecked(),
            dsp_width_idx= d.cmb_width.currentIndex(),
            dsp_cont_on  = d.btn_cont.isChecked(),
            dsp_cont_pos = d.sld_cont.value(),
            dsp_notch_on = d.btn_notch.isChecked(),
            dsp_notch_hz = d.sld_notch.value() * 10,
            dsp_nar      = d.btn_nar.isChecked(),
            # Ontvanger
            att_idx      = r._att_idx,
            ipo_idx      = r._ipo_idx,
            rflt_idx     = r._rflt_idx,
            nb_idx       = r._nb_idx,
            nr_on        = r.btn_nr.isChecked(),
            af_gain      = r.sld_af.value(),
            rf_gain      = r.sld_rf.value(),
            agc_idx      = self._mode_panel._agc_idx,
            # Zender
            tx_power     = self._power_panel.sld_power.value(),
        )
        return e

    def _recall_freq_entry(self, e: FreqEntry):
        """Pas alle instellingen van een FreqEntry toe op radio + UI."""
        # Frequentie en modus
        self._set_freq(e.freq_hz)
        self._on_mode(e.mode)
        self._display.set_band(e.band)

        # DSP
        d = self._dsp_panel
        d.btn_shift.setChecked(e.dsp_shift_on);  d.sld_shift.setValue(e.dsp_shift_hz)
        d.btn_width.setChecked(e.dsp_width_on);  d.cmb_width.setCurrentIndex(e.dsp_width_idx)
        d.btn_cont.setChecked(e.dsp_cont_on);    d.sld_cont.setValue(e.dsp_cont_pos)
        d.btn_notch.setChecked(e.dsp_notch_on);  d.sld_notch.setValue(e.dsp_notch_hz // 10)
        d.btn_nar.setChecked(e.dsp_nar)

        # Ontvanger
        r = self._right
        r.set_att(e.att_idx);  r.set_ipo(e.ipo_idx)
        r.sld_af.setValue(e.af_gain)
        r.sld_rf.setValue(e.rf_gain)
        r.btn_nr.setChecked(e.nr_on)
        self._mode_panel.set_agc(e.agc_idx)

        # Zender
        self._power_panel.set_power(e.tx_power)

        # Stuur alles naar de radio
        if self._cat.connected:
            self._cat.set_mode(e.mode)
            self._cat.set_att(e.att_idx)
            self._cat.set_ipo(e.ipo_idx)
            self._cat.set_narrow(e.dsp_nar)
            self._cat.set_if_shift(e.dsp_shift_hz if e.dsp_shift_on else 0)
            if e.dsp_notch_on:
                self._cat.set_notch(True, e.dsp_notch_hz)
            if e.dsp_cont_on:
                self._cat.set_contour(True, e.dsp_cont_pos)
            self._cat.set_power(e.tx_power)

    def _open_display_fonts(self):
        from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout,
                                       QLabel, QSpinBox, QPushButton,
                                       QGroupBox, QComboBox, QWidget)
        from PySide6.QtGui import QFontDatabase, QPainter, QFont, QFontMetrics, QColor
        from PySide6.QtCore import Qt
        from .theme import BG_DISPLAY, VFD_BRIGHT, VFD_OFF, VFD_DIM, VFD_AMBER
        from .widgets import VFD_FONTS

        dlg = QDialog(self)
        dlg.setWindowTitle(tr("Lettergrootte & font display"))
        dlg.setMinimumWidth(420)
        from .dialogs import _QSS_DIALOG
        dlg.setStyleSheet(_QSS_DIALOG)

        root = QVBoxLayout(dlg)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        _grp = ("QGroupBox{color:#787878;font-size:7pt;border:1px solid #363636;"
                "border-radius:3px;margin-top:6px;padding:6px;}")
        from .dialogs import _spinbox as _spn

        # ── Lettergroottes ─────────────────────────────────────────────────────
        grp1 = QGroupBox("Lettergrootte"); grp1.setStyleSheet(_grp)
        gl1  = QHBoxLayout(grp1); gl1.setSpacing(18)

        for lbl, attr, lo, hi, sig in [
            ("Band/mode knoppen:", "band_btn_font", 5, 14,
                lambda v: self._display.set_btn_font(v)),
            ("VFO-A frequentie:", "vfd_font", 18, 60,
                lambda v: (self._display.set_vfd_font(v), preview.update())),
            ("VFO-B frequentie:", "vfob_font", 8, 28,
                lambda v: (self._display._vfd_b.set_font_size(v), preview.update())),
        ]:
            col = QVBoxLayout()
            col.addWidget(QLabel(lbl))
            spn = _spn(lo, hi, getattr(self._cfg, attr), " pt")
            spn.valueChanged.connect(sig)
            col.addWidget(spn)
            gl1.addLayout(col)
            if   lbl.startswith("Band"):  spn_btn  = spn
            elif lbl.startswith("VFO-A"): spn_vfd  = spn
            else:                          spn_vfob = spn

        root.addWidget(grp1)

        # ── Fontfamilie ────────────────────────────────────────────────────────
        grp2 = QGroupBox("Frequentie font"); grp2.setStyleSheet(_grp)
        gl2  = QVBoxLayout(grp2)

        db       = QFontDatabase()
        families = db.families()
        avail    = [f for f in VFD_FONTS if f in families] or ["Consolas"]

        font_row = QHBoxLayout()
        font_row.addWidget(QLabel("Font:"))
        cmb_font = QComboBox()
        cmb_font.addItems(avail)
        cur_name = self._cfg.vfd_font_name
        if cur_name in avail:
            cmb_font.setCurrentText(cur_name)
        cmb_font.setMinimumWidth(180)
        font_row.addWidget(cmb_font)
        font_row.addStretch()
        gl2.addLayout(font_row)

        # ── Live preview ───────────────────────────────────────────────────────
        class _Preview(QWidget):
            def __init__(self_p, parent=None):
                super().__init__(parent)
                self_p.setFixedHeight(70)
                self_p.setStyleSheet(f"background:{BG_DISPLAY}; border-radius:4px;")

            def paintEvent(self_p, event):
                name = cmb_font.currentText()
                sz   = spn_vfd.value()
                p = QPainter(self_p)
                p.setRenderHint(QPainter.Antialiasing)
                p.fillRect(self_p.rect(), QColor(BG_DISPLAY))
                freq_font = QFont(name, sz, QFont.Bold)
                freq_font.setItalic(True)
                fm = QFontMetrics(freq_font)
                text  = "14.195.000"
                ghost = "88.888.888"
                cw = fm.horizontalAdvance("0")
                # mode label
                lf = QFont("Segoe UI", max(8, sz // 4), QFont.Bold)
                lfm = QFontMetrics(lf)
                mode_w = lfm.horizontalAdvance("USB") + 10
                khz_w  = lfm.horizontalAdvance("kHz") + 8
                total  = mode_w + len(text) * cw + khz_w
                gx = (self_p.width() - total) // 2
                fx = gx + mode_w
                yb = (self_p.height() - fm.height()) // 2 + fm.ascent() + 4
                p.setFont(freq_font)
                for i, c in enumerate(ghost):
                    p.setPen(QColor(VFD_OFF))
                    p.drawText(fx + i * cw, yb, "8" if c.isdigit() else c)
                for i, c in enumerate(text):
                    p.setPen(QColor(VFD_BRIGHT) if c != '.' else QColor(VFD_DIM))
                    p.drawText(fx + i * cw, yb, c)
                p.setFont(lf)
                ay = (self_p.height() - lfm.height()) // 2 + lfm.ascent() + 4
                p.setPen(QColor(VFD_AMBER)); p.drawText(gx, ay, "USB")
                p.setPen(QColor(VFD_DIM));   p.drawText(fx + len(text)*cw + 6, ay, "kHz")
                p.end()

        preview = _Preview()
        gl2.addWidget(preview)
        cmb_font.currentTextChanged.connect(
            lambda n: (self._display.set_vfd_font_name(n), preview.update()))

        root.addWidget(grp2)

        # ── Knoppen ───────────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_ok  = QPushButton(tr("Opslaan"))
        btn_ok.setStyleSheet("background:#C8A430;color:#000;font-weight:bold;"
                             "border-radius:2px;padding:4px 12px;")
        btn_can = QPushButton(tr("Annuleren"))
        btn_can.setStyleSheet("background:#2A2A2A;color:#DCDCDC;"
                              "border:1px solid #363636;border-radius:2px;padding:4px 12px;")

        def _save():
            self._cfg.band_btn_font = spn_btn.value()
            self._cfg.vfd_font      = spn_vfd.value()
            self._cfg.vfob_font     = spn_vfob.value()
            self._cfg.vfd_font_name = cmb_font.currentText()
            save_config(self._cfg)
            dlg.accept()

        def _cancel():
            self._display.set_btn_font(self._cfg.band_btn_font)
            self._display.set_vfd_font(self._cfg.vfd_font)
            self._display._vfd_b.set_font_size(self._cfg.vfob_font)
            self._display.set_vfd_font_name(self._cfg.vfd_font_name)
            dlg.reject()

        btn_ok.clicked.connect(_save)
        btn_can.clicked.connect(_cancel)
        btn_row.addStretch()
        btn_row.addWidget(btn_ok); btn_row.addWidget(btn_can)
        root.addLayout(btn_row)

        dlg.exec()

    def _open_smeter_calib(self):
        current_cal = self._cfg.smeter_cal
        dlg = SMeterCalibDialog(
            smeter_widget = self._display._smeter,
            current_cal   = current_cal,
            parent        = self,
        )
        # Geef een directe callable mee — altijd de versste waarde bij elke aanroep
        dlg.set_live_source(lambda: getattr(self, "_last_smeter_raw", 0))

        if dlg.exec():
            new_cal = dlg.get_calibration()
            self._cfg.smeter_cal = new_cal
            self._display._smeter.set_calibration(new_cal)
            save_config(self._cfg)

    def _open_cat_log(self):
        # Simpele info: CAT-log venster is in development
        QMessageBox.information(
            self, "CAT Monitor",
            "CAT-log: gebruik de terminal in de Instellingen-dialoog\n"
            "(Radio → Instellingen… → knop 'Verbind en test')"
        )

    def _set_language(self, lang: str, act_nl, act_en):
        from .i18n import set_language
        from .config import save_config
        set_language(lang)
        self._cfg.ui_language = lang
        save_config(self._cfg)
        act_nl.setChecked(lang == "nl")
        act_en.setChecked(lang == "en")
        QMessageBox.information(
            self,
            "Taal / Language",
            "Herstart de applicatie om de taal te wijzigen.\n\n"
            "Restart the application to change the language."
        )

    def _show_about(self):
        QMessageBox.about(
            self, "About FT-950 Controller",
            "<b>Yaesu FT-950 Controller</b><br>"
            "Version 1.1<br><br>"
            "CAT control via serial port per<br>"
            "<i>FT-950 CAT Operation Reference Book</i><br><br>"
            "Built with Python + PySide6"
        )

    # ── Venster sluiten ───────────────────────────────────────────────────────

    def closeEvent(self, event):
        self._save_all_settings()
        if self._cat.connected:
            self._cat.disconnect()
        super().closeEvent(event)

    def _save_all_settings(self):
        """Sla alle UI-instellingen op in de configuratie."""
        cfg = self._cfg

        # Venster
        cfg.win_x = self.x();  cfg.win_y = self.y()
        cfg.win_w = self.width(); cfg.win_h = self.height()

        # Frequentie / modus
        cfg.last_freq_hz  = self._freq
        cfg.last_mode     = self._mode
        cfg.last_vfob_hz  = self._display._vfd_b._freq_hz

        # DSP
        d = self._dsp_panel
        cfg.dsp_shift_on  = d.btn_shift.isChecked()
        cfg.dsp_shift_hz  = d.sld_shift.value()
        cfg.dsp_width_on  = d.btn_width.isChecked()
        cfg.dsp_width_idx = d.cmb_width.currentIndex()
        cfg.dsp_cont_on   = d.btn_cont.isChecked()
        cfg.dsp_cont_pos  = d.sld_cont.value()
        cfg.dsp_notch_on  = d.btn_notch.isChecked()
        cfg.dsp_notch_hz  = d.sld_notch.value() * 10
        cfg.dsp_nar       = d.btn_nar.isChecked()

        # Ontvanger
        r = self._right
        cfg.att_idx  = r._att_idx
        cfg.ipo_idx  = r._ipo_idx
        cfg.rflt_idx = r._rflt_idx
        cfg.nb_idx   = r._nb_idx
        cfg.nr_on    = r.btn_nr.isChecked()
        cfg.af_gain  = r.sld_af.value()
        cfg.rf_gain  = r.sld_rf.value()
        cfg.agc_idx  = self._mode_panel._agc_idx

        # Zender
        cfg.tx_power = self._power_panel.sld_power.value()
        cfg.mic_gain = self._mode_panel.sld_mic.value()
        cfg.cw_speed = self._mode_panel.sld_speed.value()

        # VFO
        cfg.vfd_step_char = self._display._vfd_a._selected_char
        cfg.split_on      = self._vfo.btn_split.isChecked()
        cfg.fast_on       = self._vfo.btn_fast.isChecked()
        cfg.ant_sel       = 2 if self._left.btn_ant2.isChecked() else 1

        save_config(cfg)

    def _restore_all_settings(self):
        """Herstel UI-instellingen vanuit de configuratie."""
        cfg = self._cfg

        # DSP
        d = self._dsp_panel
        d.btn_shift.setChecked(cfg.dsp_shift_on)
        d.sld_shift.setValue(cfg.dsp_shift_hz)
        d.btn_width.setChecked(cfg.dsp_width_on)
        d.cmb_width.setCurrentIndex(cfg.dsp_width_idx)
        d.btn_cont.setChecked(cfg.dsp_cont_on)
        d.sld_cont.setValue(cfg.dsp_cont_pos)
        d.btn_notch.setChecked(cfg.dsp_notch_on)
        d.sld_notch.setValue(cfg.dsp_notch_hz // 10)
        d.btn_nar.setChecked(cfg.dsp_nar)

        # Ontvanger
        r = self._right
        r.set_att(cfg.att_idx)
        r.set_ipo(cfg.ipo_idx)
        r.sld_af.setValue(cfg.af_gain)
        r.sld_rf.setValue(cfg.rf_gain)
        r.btn_nr.setChecked(cfg.nr_on)

        # Zender
        self._power_panel.set_power(cfg.tx_power)
        self._mode_panel.sld_mic.setValue(cfg.mic_gain)
        self._mode_panel.sld_speed.setValue(cfg.cw_speed)
        self._mode_panel.set_agc(cfg.agc_idx)

        # VFO / display
        self._display._vfd_a._selected_char = cfg.vfd_step_char
        self._display._vfd_a.update()
        self._vfo.btn_split.setChecked(cfg.split_on)
        self._vfo.btn_fast.setChecked(cfg.fast_on)
        self._left._set_ant(cfg.ant_sel)
