"""FT-950 Controller — dialogen.

  CatSettingsDialog  — COM-poort, baudrate, seriële parameters, test
  MemoryDialog       — geheugenkanalen bekijken/bewerken/opslaan
"""

from PySide6.QtCore    import Qt, QTimer, QSortFilterProxyModel
from PySide6.QtGui     import QFont, QColor, QPainter, QFontMetrics
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QComboBox, QSpinBox, QCheckBox, QDoubleSpinBox,
    QPushButton, QFrame, QTableWidget, QTableWidgetItem,
    QHeaderView, QSizePolicy, QWidget, QGroupBox,
    QTabWidget, QScrollArea, QFileDialog, QMessageBox,
    QAbstractItemView, QProgressBar, QAbstractSpinBox
)

from .theme  import (BG_PANEL, BG_SURFACE, BG_ROOT, BG_DISPLAY, BORDER,
                     TEXT_H1, TEXT_DIM, ACCENT, LED_GREEN, LED_RED, LED_OFF,
                     VFD_BRIGHT, VFD_DIM, VFD_AMBER, VFD_OFF)
from .cat    import list_ports, MODE_CODES
from .config import (FreqEntry, load_memories, save_memories,
                     EibiRecord, load_eibi_records, save_eibi_records,
                     load_channels, save_channels)


_QSS_DIALOG = f"""
QDialog, QWidget {{
    background: {BG_PANEL};
}}
QTabWidget::pane {{
    border: 1px solid #555555;
    background: {BG_PANEL};
}}
QTabBar::tab {{
    background: #2E2E2E;
    color: #CCCCCC;
    padding: 6px 18px;
    font-size: 8pt;
    border: 1px solid #555555;
    border-bottom: none;
    border-top-left-radius: 3px;
    border-top-right-radius: 3px;
    margin-right: 2px;
}}
QTabBar::tab:selected {{
    background: #4A4A4A;
    color: #FFFFFF;
    font-weight: bold;
}}
QTabBar::tab:hover:!selected {{
    background: #383838;
    color: #EEEEEE;
}}
QGroupBox {{
    color: {TEXT_DIM};
    font-size: 8pt;
    border: 1px solid {BORDER};
    border-radius: 3px;
    margin-top: 8px;
    padding: 6px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 4px;
}}
QLabel {{
    color: {TEXT_DIM};
    font-size: 8pt;
    background: transparent;
}}
QLineEdit, QComboBox {{
    background: {BG_SURFACE};
    color: {TEXT_H1};
    border: 1px solid {BORDER};
    padding: 3px 5px;
    border-radius: 2px;
    font-size: 8pt;
}}
QLineEdit:focus, QComboBox:focus {{
    border-color: {ACCENT};
}}
QComboBox QAbstractItemView {{
    background: {BG_SURFACE};
    color: {TEXT_H1};
    selection-background-color: {ACCENT};
}}
QCheckBox {{
    color: {TEXT_H1};
    font-size: 8pt;
    spacing: 5px;
}}
QPushButton {{
    background: {BG_SURFACE};
    color: {TEXT_H1};
    border: 1px solid {BORDER};
    padding: 4px 12px;
    border-radius: 2px;
    font-size: 8pt;
}}
QPushButton:hover  {{ background: #32373F; border-color: {ACCENT}; }}
QPushButton#ok     {{ background: {ACCENT}; color: #000; font-weight: bold; }}
QPushButton#ok:hover {{ background: #E0C060; }}
QPushButton#test   {{ background: #1A3A1A; color: {LED_GREEN}; border-color: #2A5A2A; }}
QPushButton#test:hover {{ background: #2A4A2A; }}
QTableWidget {{
    background: {BG_SURFACE};
    color: {TEXT_H1};
    border: 1px solid {BORDER};
    gridline-color: {BORDER};
    font-size: 8pt;
}}
QTableWidget QHeaderView::section {{
    background: {BG_PANEL};
    color: {TEXT_DIM};
    border: none;
    padding: 3px;
    font-size: 7pt;
}}
QTableWidget::item:selected {{
    background: {ACCENT};
    color: #000;
}}
"""


def _spinbox(min_v: int, max_v: int, val: int = 0,
             suffix: str = "") -> QSpinBox:
    """Standaard QSpinBox met de gedeelde dialoog-stijl."""
    s = QSpinBox()
    s.setRange(min_v, max_v)
    s.setValue(val)
    if suffix:
        s.setSuffix(suffix)
    return s


def _dblspinbox(min_v: float, max_v: float, val: float = 0.0,
                decimals: int = 3, suffix: str = "") -> QDoubleSpinBox:
    s = QDoubleSpinBox()
    s.setRange(min_v, max_v)
    s.setDecimals(decimals)
    s.setValue(val)
    if suffix:
        s.setSuffix(suffix)
    return s


# ── CAT instellingen ──────────────────────────────────────────────────────────

class CatSettingsDialog(QDialog):
    """COM-poort, baudrate en seriële parameters instellen + verbindingstest."""

    def __init__(self, cfg, cat, parent=None):
        super().__init__(parent)
        self._cfg = cfg
        self._cat = cat
        self.setWindowTitle("CAT / Seriële poort instellingen")
        self.setMinimumWidth(440)
        self.setStyleSheet(_QSS_DIALOG)
        self._build()
        self._load_from_cfg()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        # ── Verbinding ────────────────────────────────────────────────────────
        grp_conn = QGroupBox("Seriële verbinding")
        gc = QGridLayout(grp_conn)
        gc.setSpacing(6)

        gc.addWidget(QLabel("COM-poort:"), 0, 0)
        self.cmb_port = QComboBox()
        self.cmb_port.setEditable(True)
        btn_scan = QPushButton("⟳")
        btn_scan.setFixedWidth(30)
        btn_scan.clicked.connect(self._scan_ports)
        port_row = QHBoxLayout()
        port_row.addWidget(self.cmb_port, 1)
        port_row.addWidget(btn_scan)
        gc.addLayout(port_row, 0, 1)

        gc.addWidget(QLabel("Baudrate:"), 1, 0)
        self.cmb_baud = QComboBox()
        self.cmb_baud.addItems(["4800", "9600", "19200", "38400"])
        gc.addWidget(self.cmb_baud, 1, 1)

        gc.addWidget(QLabel("Databits:"), 2, 0)
        self.cmb_bits = QComboBox()
        self.cmb_bits.addItems(["8", "7"])
        gc.addWidget(self.cmb_bits, 2, 1)

        gc.addWidget(QLabel("Pariteit:"), 3, 0)
        self.cmb_par = QComboBox()
        self.cmb_par.addItems(["Geen", "Even", "Odd"])
        gc.addWidget(self.cmb_par, 3, 1)

        gc.addWidget(QLabel("Stopbits:"), 4, 0)
        self.cmb_stop = QComboBox()
        self.cmb_stop.addItems(["1", "2"])
        gc.addWidget(self.cmb_stop, 4, 1)

        root.addWidget(grp_conn)

        # ── Handshake ────────────────────────────────────────────────────────
        grp_hs = QGroupBox("Handshake / signaalbeheer")
        gh = QHBoxLayout(grp_hs)
        self.chk_rtscts = QCheckBox("RTS/CTS hardware handshake")
        self.chk_dtr    = QCheckBox("DTR aan bij verbinden")
        self.chk_rts    = QCheckBox("RTS aan bij verbinden")
        gh.addWidget(self.chk_rtscts)
        gh.addWidget(self.chk_dtr)
        gh.addWidget(self.chk_rts)
        root.addWidget(grp_hs)

        # ── Poll-interval ────────────────────────────────────────────────────
        grp_poll = QGroupBox("Polling")
        gp = QHBoxLayout(grp_poll)
        gp.addWidget(QLabel("Frequentie-poll interval (ms):"))
        self.spn_poll = QSpinBox()
        self.spn_poll.setRange(200, 5000)
        self.spn_poll.setSingleStep(100)
        self.spn_poll.setValue(500)
        gp.addWidget(self.spn_poll)
        gp.addStretch()
        root.addWidget(grp_poll)

        # ── Test-status ───────────────────────────────────────────────────────
        self._status_lbl = QLabel("Niet verbonden")
        self._status_lbl.setStyleSheet(f"color:{TEXT_DIM}; font-size:8pt;")
        root.addWidget(self._status_lbl)

        # ── Knoppen ───────────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_test = QPushButton("Verbind en test (ID;)")
        btn_test.setObjectName("test")
        btn_test.clicked.connect(self._do_test)
        btn_ok     = QPushButton("Opslaan")
        btn_ok.setObjectName("ok")
        btn_ok.clicked.connect(self._do_save)
        btn_cancel = QPushButton("Annuleer")
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_test)
        btn_row.addStretch()
        btn_row.addWidget(btn_ok)
        btn_row.addWidget(btn_cancel)
        root.addLayout(btn_row)

        self._scan_ports()

    def _scan_ports(self):
        ports = list_ports()
        current = self.cmb_port.currentText()
        self.cmb_port.clear()
        if ports:
            self.cmb_port.addItems(ports)
            if current in ports:
                self.cmb_port.setCurrentText(current)
        else:
            self.cmb_port.addItem("(geen poorten gevonden)")

    def _load_from_cfg(self):
        cfg = self._cfg
        if cfg.cat_port:
            self.cmb_port.setCurrentText(cfg.cat_port)
        self.cmb_baud.setCurrentText(str(cfg.cat_baud))
        self.cmb_bits.setCurrentText(str(cfg.cat_databits))
        self.cmb_par.setCurrentText(cfg.cat_parity)
        self.cmb_stop.setCurrentText(str(cfg.cat_stopbits))
        self.chk_rtscts.setChecked(cfg.cat_rtscts)
        self.chk_dtr.setChecked(cfg.cat_dtr)
        self.chk_rts.setChecked(cfg.cat_rts)
        self.spn_poll.setValue(getattr(cfg, "cat_poll_ms", 500))

    def _apply_to_cfg(self):
        cfg = self._cfg
        cfg.cat_port     = self.cmb_port.currentText().strip()
        cfg.cat_baud     = int(self.cmb_baud.currentText())
        cfg.cat_databits = int(self.cmb_bits.currentText())
        cfg.cat_parity   = self.cmb_par.currentText()
        cfg.cat_stopbits = self.cmb_stop.currentText()
        cfg.cat_rtscts   = self.chk_rtscts.isChecked()
        cfg.cat_dtr      = self.chk_dtr.isChecked()
        cfg.cat_rts      = self.chk_rts.isChecked()
        cfg.cat_poll_ms  = self.spn_poll.value()

    def _do_test(self):
        self._apply_to_cfg()
        if self._cat.connected:
            self._cat.disconnect()
        ok, msg = self._cat.connect()
        if ok:
            ok2, resp = self._cat.identify()
            if ok2:
                self._status_lbl.setText(f"✔  Verbonden — antwoord: {resp}")
                self._status_lbl.setStyleSheet(f"color:{LED_GREEN}; font-size:8pt;")
            else:
                self._status_lbl.setText(f"✔  Verbonden maar ID mislukt: {resp}")
                self._status_lbl.setStyleSheet(f"color:#FFAA00; font-size:8pt;")
        else:
            self._status_lbl.setText(f"✘  Verbinding mislukt: {msg}")
            self._status_lbl.setStyleSheet(f"color:{LED_RED}; font-size:8pt;")

    def _do_save(self):
        self._apply_to_cfg()
        from .config import save_config
        save_config(self._cfg)
        self.accept()


# ── Memory kanalen ─────────────────────────────────────────────────────────────

class MemoryDialog(QDialog):
    """Bekijk en bewerk de 100 geheugenkanalen van de FT-950."""

    _COLS = ["CH", "Frequentie (Hz)", "Mode", "Shift", "CTCSS", "Opmerking"]

    def __init__(self, cat, parent=None):
        super().__init__(parent)
        self._cat  = cat
        self._data: dict[int, dict] = load_channels()   # laad opgeslagen kanalen
        self.setWindowTitle("FT-950 — Geheugenkanalen")
        self.resize(700, 520)
        self.setStyleSheet(_QSS_DIALOG)
        self._build()
        # Herstel opgeslagen kanalen in de tabel
        for ch, data in self._data.items():
            self._fill_row(ch, data)

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        # Toolbar
        tb = QHBoxLayout()
        tb.setSpacing(6)
        btn_read_all = QPushButton("Alles inlezen van radio")
        btn_read_all.setObjectName("test")
        btn_read_all.clicked.connect(self._read_all)
        btn_write    = QPushButton("Geselecteerde → radio")
        btn_write.clicked.connect(self._write_selected)
        btn_recall   = QPushButton("Oproepen op radio")
        btn_recall.clicked.connect(self._recall_selected)
        self.btn_save = QPushButton("💾 Bewaren")
        self.btn_save.setObjectName("ok")
        self.btn_save.clicked.connect(self._do_save)
        tb.addWidget(btn_read_all)
        tb.addWidget(btn_write)
        tb.addWidget(btn_recall)
        tb.addWidget(self.btn_save)
        tb.addStretch()
        root.addLayout(tb)

        # Status
        self._status_lbl = QLabel("")
        self._status_lbl.setStyleSheet(f"color:{TEXT_DIM}; font-size:7pt;")
        root.addWidget(self._status_lbl)

        # Tabel
        self._tbl = QTableWidget(100, len(self._COLS))
        self._tbl.setHorizontalHeaderLabels(self._COLS)
        self._tbl.setSelectionBehavior(QTableWidget.SelectRows)
        self._tbl.verticalHeader().setVisible(False)
        self._tbl.horizontalHeader().setStretchLastSection(True)
        self._tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self._tbl.setColumnWidth(0, 40)
        self._tbl.setColumnWidth(2, 70)
        self._tbl.setColumnWidth(3, 50)
        self._tbl.setColumnWidth(4, 50)
        # Vul CH-kolom alvast
        for i in range(100):
            item = QTableWidgetItem(str(i))
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            item.setTextAlignment(Qt.AlignCenter)
            self._tbl.setItem(i, 0, item)
        root.addWidget(self._tbl, 1)

        # Bewerk-sectie
        edit_grp = QGroupBox("Nieuw kanaal invoeren / bewerken")
        eg = QGridLayout(edit_grp)
        eg.setSpacing(6)

        eg.addWidget(QLabel("Kanaal (0-99):"), 0, 0)
        self.spn_ch = QSpinBox()
        self.spn_ch.setRange(0, 99)
        eg.addWidget(self.spn_ch, 0, 1)

        eg.addWidget(QLabel("Frequentie (Hz):"), 0, 2)
        self.edt_freq = QLineEdit("14000000")
        eg.addWidget(self.edt_freq, 0, 3)

        eg.addWidget(QLabel("Mode:"), 1, 0)
        self.cmb_mode = QComboBox()
        self.cmb_mode.addItems(list(MODE_CODES.keys()))
        self.cmb_mode.setCurrentText("USB")
        eg.addWidget(self.cmb_mode, 1, 1)

        eg.addWidget(QLabel("Shift:"), 1, 2)
        self.cmb_shift = QComboBox()
        self.cmb_shift.addItems(["S (simplex)", "+ (plus)", "- (minus)"])
        eg.addWidget(self.cmb_shift, 1, 3)

        eg.addWidget(QLabel("Opmerking:"), 2, 0)
        self.edt_note = QLineEdit()
        eg.addWidget(self.edt_note, 2, 1, 1, 3)

        btn_write_one = QPushButton("Dit kanaal naar radio sturen")
        btn_write_one.setObjectName("ok")
        btn_write_one.clicked.connect(self._write_one)
        eg.addWidget(btn_write_one, 3, 0, 1, 4)

        root.addWidget(edit_grp)

        # Sluiten
        btn_close = QPushButton("Sluiten")
        btn_close.clicked.connect(self.accept)
        root.addWidget(btn_close, alignment=Qt.AlignRight)

        # Als een rij geselecteerd wordt, vul de bewerk-sectie
        self._tbl.currentCellChanged.connect(
            lambda row, _col, _prow, _pcol: self._row_selected(row))

    def _set_status(self, msg: str, color: str = TEXT_DIM):
        self._status_lbl.setText(msg)
        self._status_lbl.setStyleSheet(f"color:{color}; font-size:7pt;")

    def _do_save(self):
        """Sla alle ingevulde kanalen op naar ft950_channels.json."""
        save_channels(self._data)
        self._set_status(
            f"{len(self._data)} kanalen opgeslagen in ft950_channels.json",
            LED_GREEN)

    def _read_all(self):
        if not self._cat.connected:
            self._set_status("Niet verbonden met radio.", LED_RED)
            return
        self._set_status("Bezig met inlezen…")
        count = 0
        for ch in range(100):
            data = self._cat.get_memory(ch)
            if data:
                self._data[ch] = data
                self._fill_row(ch, data)
                count += 1
        self._set_status(f"{count} kanalen ingelezen.  Klik '💾 Bewaren' om op te slaan.",
                         LED_GREEN)

    def _fill_row(self, ch: int, data: dict):
        row = ch
        vals = [
            str(ch),
            str(data.get("freq", "")),
            data.get("mode", ""),
            data.get("shift", "S"),
            str(data.get("tone", 0)),
            "",
        ]
        for col, val in enumerate(vals):
            item = QTableWidgetItem(val)
            if col == 0:
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                item.setTextAlignment(Qt.AlignCenter)
            elif col == 5:   # Opmerking → links
                item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            else:
                item.setTextAlignment(Qt.AlignCenter)
            self._tbl.setItem(row, col, item)

    def _write_selected(self):
        rows = sorted({idx.row() for idx in self._tbl.selectedIndexes()})
        if not rows:
            self._set_status("Geen rijen geselecteerd.")
            return
        if not self._cat.connected:
            self._set_status("Niet verbonden.", LED_RED)
            return
        for row in rows:
            freq_item = self._tbl.item(row, 1)
            mode_item = self._tbl.item(row, 2)
            if not freq_item or not freq_item.text().strip():
                continue
            try:
                freq = int(freq_item.text())
            except ValueError:
                continue
            mode  = mode_item.text() if mode_item else "USB"
            shift_item = self._tbl.item(row, 3)
            shift = {"S": "S", "+": "+", "-": "-"}.get(
                (shift_item.text() if shift_item else "S"), "S")
            self._cat.set_memory(row, freq, mode, shift)
        self._set_status(f"{len(rows)} kanaal/kanalen verzonden.", LED_GREEN)

    def _recall_selected(self):
        rows = {idx.row() for idx in self._tbl.selectedIndexes()}
        if not rows:
            return
        ch = min(rows)
        if self._cat.connected:
            self._cat.recall_memory(ch)
            self._set_status(f"Kanaal {ch} opgeroepen.", LED_GREEN)

    def _write_one(self):
        ch = self.spn_ch.value()
        try:
            freq = int(self.edt_freq.text())
        except ValueError:
            self._set_status("Ongeldige frequentie.", LED_RED)
            return
        mode  = self.cmb_mode.currentText()
        shift = {0: "S", 1: "+", 2: "-"}.get(self.cmb_shift.currentIndex(), "S")
        if not self._cat.connected:
            self._set_status("Niet verbonden met radio — kanaal NIET naar radio gestuurd.", LED_RED)
        else:
            ok = self._cat.set_memory(ch, freq, mode, shift)
            if ok:
                self._set_status(f"Kanaal {ch} naar radio geschreven.", LED_GREEN)
            else:
                self._set_status(f"Kanaal {ch}: radio antwoordde met fout (?). "
                                 "Controleer verbinding en frequentiebereik.", LED_RED)
        # Altijd lokaal bijwerken
        data = {"freq": freq, "mode": mode, "shift": shift, "tone": 0}
        self._data[ch] = data
        self._fill_row(ch, data)

    def _row_selected(self, row: int):
        if row < 0 or row >= 100:
            return
        self.spn_ch.setValue(row)
        data = self._data.get(row)
        if not data:
            return
        self.edt_freq.setText(str(data.get("freq", "")))
        mode = data.get("mode", "USB")
        idx = self.cmb_mode.findText(mode)
        if idx >= 0:
            self.cmb_mode.setCurrentIndex(idx)
        shift = data.get("shift", "S")
        self.cmb_shift.setCurrentIndex({"S": 0, "+": 1, "-": 2}.get(shift, 0))
        # Stuur kanaal naar radio zodra er op geklikt wordt
        if self._cat.connected:
            self._cat.recall_memory(row)
            self._set_status(f"Kanaal {row} opgeroepen  ({data.get('freq',0)/1000:.1f} kHz  {mode})",
                             LED_GREEN)


# ── Frequentie-favorieten ─────────────────────────────────────────────────────

_WIDTH_LABELS_LIST = ["3.0k","2.9k","2.8k","2.7k","2.6k","2.5k","2.4k",
                      "2.1k","1.8k","1.5k","1.2k","1.0k","800","500","400","300","200"]


# ── EIBI-tabblad ─────────────────────────────────────────────────────────────

_EIBI_COLS = ["Freq (kHz)", "Station", "Land", "Start", "Stop",
              "Taal", "Doel", "Mode", "Volume", "SQL", "Notitie"]


class _NumericItem(QTableWidgetItem):
    """QTableWidgetItem dat numeriek sorteert (voor de frequentiekolom)."""
    def __lt__(self, other):
        try:
            return float(self.text()) < float(other.text())
        except ValueError:
            return super().__lt__(other)


class _EibiTab(QWidget):
    """EIBI-lijst tabblad: import, tabel met verschuifbare kolommen, rijklik → radio."""

    def __init__(self, cat, apply_fn, lazy: bool = False, parent=None):
        super().__init__(parent)
        self._cat       = cat
        self._apply_fn  = apply_fn
        self._lazy      = lazy      # True = vul tabel pas bij ensure_loaded()
        self._loaded    = False
        self._records: list[EibiRecord] = load_eibi_records()
        self._selected  = -1
        self._build()
        if not lazy:
            self._fill_table(self._records)

    def ensure_loaded(self):
        """Vul de tabel als dat nog niet is gedaan (lazy loading)."""
        if not self._loaded:
            self._fill_table(self._records)
            self._loaded = True

    # ── Opbouw ─────────────────────────────────────────────────────────────

    def _build(self):
        v = QVBoxLayout(self)
        v.setContentsMargins(6, 6, 6, 6)
        v.setSpacing(5)

        # Toolbar
        tb = QHBoxLayout(); tb.setSpacing(5)
        btn_import = QPushButton("📥 Importeer EIBI…"); btn_import.setObjectName("test")
        btn_apply  = QPushButton("▶ Laden → radio");   btn_apply.setObjectName("ok")
        btn_save   = QPushButton("💾 Bewaren")
        btn_clear  = QPushButton("✕ Alles wissen")
        btn_import.clicked.connect(self._do_import)
        btn_apply.clicked.connect(self._do_apply_selected)
        btn_save.clicked.connect(self._do_save)
        btn_clear.clicked.connect(self._do_clear)
        for w in (btn_import, btn_apply, btn_save, btn_clear):
            tb.addWidget(w)
        tb.addStretch()
        v.addLayout(tb)

        # Zoekbalk
        sr = QHBoxLayout(); sr.setSpacing(4)
        sr.addWidget(QLabel("Zoeken:"))
        self._search = QLineEdit()
        self._search.setPlaceholderText("station, land of frequentie…")
        self._search.textChanged.connect(self._filter)
        sr.addWidget(self._search, 1)
        self._cnt_lbl = QLabel("0 records")
        self._cnt_lbl.setStyleSheet(f"color:{TEXT_DIM}; font-size:7pt;")
        sr.addWidget(self._cnt_lbl)
        v.addLayout(sr)

        # Tabel — kolommen zijn versleepbaar en instelbaar van breedte
        self._tbl = QTableWidget(0, len(_EIBI_COLS))
        self._tbl.setHorizontalHeaderLabels(_EIBI_COLS)
        self._tbl.horizontalHeader().setSectionsMovable(True)
        self._tbl.horizontalHeader().setSortIndicatorShown(True)
        self._tbl.setSortingEnabled(True)
        self._tbl.setSelectionBehavior(QTableWidget.SelectRows)
        self._tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        self._tbl.verticalHeader().setVisible(False)
        self._tbl.horizontalHeader().setStretchLastSection(True)
        self._tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self._tbl.setColumnWidth(0, 90);  self._tbl.setColumnWidth(2, 50)
        self._tbl.setColumnWidth(3, 50);  self._tbl.setColumnWidth(4, 50)
        self._tbl.setColumnWidth(5, 50);  self._tbl.setColumnWidth(6, 50)
        self._tbl.setColumnWidth(7, 55);  self._tbl.setColumnWidth(8, 55)
        self._tbl.setColumnWidth(9, 45);  self._tbl.setColumnWidth(10, 120)
        self._tbl.currentCellChanged.connect(
            lambda row, _c, _pr, _pc: self._row_selected(row))
        self._tbl.doubleClicked.connect(lambda _: self._do_apply_selected())
        v.addWidget(self._tbl, 1)

        # Bewerk-strip (instellingen per record)
        edit_grp = QGroupBox("Instellingen geselecteerde regel")
        eg = QHBoxLayout(edit_grp); eg.setSpacing(12)

        eg.addWidget(QLabel("Mode:"))
        self._cmb_mode = QComboBox()
        self._cmb_mode.addItems(["AM","USB","LSB","CW","FM","RTTY"])
        self._cmb_mode.setFixedWidth(70)
        eg.addWidget(self._cmb_mode)

        eg.addWidget(QLabel("Volume:"))
        self._spn_vol = _spinbox(0, 255, 60)
        self._spn_vol.setFixedWidth(65)
        eg.addWidget(self._spn_vol)

        eg.addWidget(QLabel("SQL:"))
        self._spn_sql = _spinbox(0, 255, 0)
        self._spn_sql.setFixedWidth(65)
        eg.addWidget(self._spn_sql)

        self._chk_nar = QCheckBox("NAR")
        eg.addWidget(self._chk_nar)

        eg.addWidget(QLabel("Breedte:"))
        self._cmb_width = QComboBox()
        self._cmb_width.addItems(["3.0k","2.9k","2.8k","2.7k","2.6k","2.5k","2.4k",
                                   "2.1k","1.8k","1.5k","1.2k","1.0k","800","500",
                                   "400","300","200"])
        self._cmb_width.setCurrentIndex(6)
        self._cmb_width.setFixedWidth(70)
        eg.addWidget(self._cmb_width)

        eg.addWidget(QLabel("Notitie:"))
        self._edt_note = QLineEdit()
        eg.addWidget(self._edt_note, 1)

        btn_apply_edit = QPushButton("Opslaan")
        btn_apply_edit.setObjectName("ok")
        btn_apply_edit.clicked.connect(self._save_edit)
        eg.addWidget(btn_apply_edit)

        v.addWidget(edit_grp)

    # ── Tabel vullen ───────────────────────────────────────────────────────

    def _fill_table(self, records):
        """Vul de tabel bulk-gewijs: updates en sortering uitgeschakeld."""
        self._tbl.setUpdatesEnabled(False)
        self._tbl.setSortingEnabled(False)
        self._tbl.setRowCount(0)
        self._tbl.setRowCount(len(records))
        for row, r in enumerate(records):
            vals = [
                f"{r.freq_hz / 1000:.1f}",
                r.station, r.country, r.start, r.stop,
                r.language, r.target, r.mode,
                f"{r.af_gain:03d}", f"{r.sql:03d}", r.notes,
            ]
            # Kolom 1 (station) en 10 (notitie) links uitlijnen
            _LEFT = {1, 10}
            for col, val in enumerate(vals):
                item = _NumericItem(val) if col == 0 else QTableWidgetItem(val)
                item.setTextAlignment(
                    Qt.AlignLeft | Qt.AlignVCenter if col in _LEFT
                    else Qt.AlignCenter)
                item.setData(Qt.UserRole, r)
                self._tbl.setItem(row, col, item)
        self._tbl.setSortingEnabled(True)
        self._tbl.sortItems(0, Qt.AscendingOrder)
        self._tbl.setUpdatesEnabled(True)
        self._cnt_lbl.setText(f"{len(records)} records")

    def _append_row(self, r: EibiRecord):
        """Voeg één rij toe; sortering wordt tijdelijk uitgeschakeld."""
        self._tbl.setSortingEnabled(False)
        row = self._tbl.rowCount()
        self._tbl.insertRow(row)
        vals = [
            f"{r.freq_hz / 1000:.1f}",
            r.station, r.country, r.start, r.stop,
            r.language, r.target, r.mode,
            f"{r.af_gain:03d}", f"{r.sql:03d}", r.notes,
        ]
        _LEFT = {1, 10}
        for col, val in enumerate(vals):
            item = _NumericItem(val) if col == 0 else QTableWidgetItem(val)
            item.setTextAlignment(
                Qt.AlignLeft | Qt.AlignVCenter if col in _LEFT
                else Qt.AlignCenter)
            item.setData(Qt.UserRole, r)
            self._tbl.setItem(row, col, item)
        self._tbl.setSortingEnabled(True)

    def _filter(self, text: str):
        term = text.strip().lower()
        filtered = [r for r in self._records if
                    not term or term in r.station.lower()
                    or term in r.country.lower()
                    or term in str(r.freq_hz // 1000)]
        self._fill_table(filtered)

    # ── Rijselectie ────────────────────────────────────────────────────────

    def _row_selected(self, row: int):
        self._selected = row
        if row < 0: return
        item = self._tbl.item(row, 0)
        if not item: return
        r = item.data(Qt.UserRole)
        if not isinstance(r, EibiRecord): return
        # Vul bewerk-strip
        idx = self._cmb_mode.findText(r.mode)
        if idx >= 0: self._cmb_mode.setCurrentIndex(idx)
        self._spn_vol.setValue(r.af_gain)
        self._spn_sql.setValue(r.sql)
        self._chk_nar.setChecked(r.dsp_nar)
        self._cmb_width.setCurrentIndex(r.dsp_width_idx)
        self._edt_note.setText(r.notes)
        # Stuur meteen naar radio (bij enkelvoudige klik)
        if self._apply_fn:
            try: self._apply_fn(r)
            except Exception: pass

    # ── Acties ─────────────────────────────────────────────────────────────

    def _do_apply_selected(self):
        """Dubbelklik of knop: stuur geselecteerde regel naar radio."""
        row = self._selected
        if row < 0: return
        item = self._tbl.item(row, 0)
        if item:
            r = item.data(Qt.UserRole)
            if isinstance(r, EibiRecord) and self._apply_fn:
                self._apply_fn(r)

    def _save_edit(self):
        """Sla bewerk-strip op in het geselecteerde record."""
        row = self._selected
        if row < 0: return
        item = self._tbl.item(row, 0)
        if not item: return
        r = item.data(Qt.UserRole)
        if not isinstance(r, EibiRecord): return
        r.mode          = self._cmb_mode.currentText()
        r.af_gain       = self._spn_vol.value()
        r.sql           = self._spn_sql.value()
        r.dsp_nar       = self._chk_nar.isChecked()
        r.dsp_width_idx = self._cmb_width.currentIndex()
        r.notes         = self._edt_note.text().strip()
        # Tabel bijwerken
        updates = {7: r.mode, 8: f"{r.af_gain:03d}", 9: f"{r.sql:03d}", 10: r.notes}
        for col, val in updates.items():
            if self._tbl.item(row, col):
                self._tbl.item(row, col).setText(val)
        # Automatisch opslaan na elke aanpassing
        save_eibi_records(self._records)

    def _do_import(self):
        dlg = EIBIImportDialog(parent=self)
        if dlg.exec():
            new_entries = dlg.get_entries()   # geeft nu EibiRecord objecten
            if new_entries:
                for rec in new_entries:
                    if isinstance(rec, EibiRecord):
                        self._records.append(rec)
                        self._append_row(rec)
                self._cnt_lbl.setText(f"{len(self._records)} records")
                self._loaded = True   # tabel is nu gevuld

    def _do_save(self):
        save_eibi_records(self._records)
        self._cnt_lbl.setText(f"{len(self._records)} records  (opgeslagen)")

    def _do_clear(self):
        self._records.clear()
        self._tbl.setRowCount(0)
        self._cnt_lbl.setText("0 records")

    def get_records(self) -> list:
        return self._records


# ── Favorieten-dialoog met tabbladen ──────────────────────────────────────────

class FreqMemoryDialog(QDialog):
    """Frequentie-favorieten: meerdere tabbladen (Favorieten + EIBI)."""

    def __init__(self, cat=None, apply_eibi_fn=None, apply_fav_fn=None, parent=None):
        super().__init__(parent)
        self._entries: list[FreqEntry] = load_memories()
        self._selected: int = -1
        self._cat          = cat
        self._apply_eibi   = apply_eibi_fn
        self._apply_fav    = apply_fav_fn   # callable(FreqEntry) → radio instellen
        self.setWindowTitle("Frequentie-favorieten")
        self.resize(1000, 620)
        self.setStyleSheet(_QSS_DIALOG)
        self._build()
        self._fill_table()

    # ── Opbouw ─────────────────────────────────────────────────────────────

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(0)

        # ── Hoofd QTabWidget ──────────────────────────────────────────────
        self._tabs = QTabWidget()
        # Tab-stijl zit in _QSS_DIALOG (op dialogniveau), geen override nodig

        # ── Tab 1: Favorieten ─────────────────────────────────────────────
        fav_widget = QWidget()
        fav_layout = QVBoxLayout(fav_widget)
        fav_layout.setContentsMargins(8, 8, 8, 8)
        fav_layout.setSpacing(6)

        # Toolbar favorieten
        tb = QHBoxLayout(); tb.setSpacing(5)
        self.btn_save   = QPushButton("⊕ Bewaar huidig");  self.btn_save.setObjectName("ok")
        self.btn_delete = QPushButton("✕ Verwijder")
        self.btn_up     = QPushButton("▲"); self.btn_up.setFixedWidth(28)
        self.btn_dn     = QPushButton("▼"); self.btn_dn.setFixedWidth(28)
        self.btn_save.clicked.connect(self._do_save_current)
        self.btn_delete.clicked.connect(self._do_delete)
        self.btn_up.clicked.connect(lambda: self._move(-1))
        self.btn_dn.clicked.connect(lambda: self._move(+1))
        for w in (self.btn_save, self.btn_delete, self.btn_up, self.btn_dn):
            tb.addWidget(w)
        tb.addStretch()
        fav_layout.addLayout(tb)

        self._status = QLabel("")
        self._status.setStyleSheet(f"color:{TEXT_DIM}; font-size:7pt;")
        fav_layout.addWidget(self._status)

        # Splitter: tabel links + bewerkpaneel rechts
        split = QHBoxLayout(); split.setSpacing(8)

        # ── Tabel ──────────────────────────────────────────────────────────
        cols = ["Naam", "Frequentie (MHz)", "Mode", "Band", "Notitie"]
        self._tbl = QTableWidget(0, len(cols))
        self._tbl.setHorizontalHeaderLabels(cols)
        self._tbl.setSelectionBehavior(QTableWidget.SelectRows)
        self._tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        self._tbl.verticalHeader().setVisible(False)
        self._tbl.horizontalHeader().setStretchLastSection(True)
        self._tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self._tbl.setColumnWidth(1, 120)
        self._tbl.setColumnWidth(2, 60)
        self._tbl.setColumnWidth(3, 60)
        self._tbl.currentCellChanged.connect(
            lambda row, _c, _pr, _pc: self._row_selected(row))
        split.addWidget(self._tbl, 3)

        # ── Bewerkpaneel rechts ────────────────────────────────────────────
        edit_widget = QWidget()
        ev = QVBoxLayout(edit_widget); ev.setContentsMargins(0, 0, 0, 0); ev.setSpacing(4)

        tabs = QTabWidget()
        tabs.setStyleSheet(f"QTabBar::tab {{ padding:4px 10px; font-size:7pt; }}")

        # Tab 1: Basis
        t1 = QWidget(); g1 = QGridLayout(t1); g1.setSpacing(5)
        self.edt_name = QLineEdit(); self.edt_freq = QDoubleSpinBox()
        self.edt_freq.setDecimals(6); self.edt_freq.setRange(0.03, 56.0)
        self.edt_freq.setSuffix(" MHz")
        self.cmb_mode = QComboBox(); self.cmb_mode.addItems(list(MODE_CODES.keys()))
        self.edt_band = QLineEdit()
        self.edt_note = QLineEdit()
        for r, (lbl, w) in enumerate([
            ("Naam:", self.edt_name), ("Frequentie:", self.edt_freq),
            ("Mode:", self.cmb_mode), ("Band:", self.edt_band),
            ("Notitie:", self.edt_note),
        ]):
            g1.addWidget(QLabel(lbl), r, 0)
            g1.addWidget(w, r, 1)
        tabs.addTab(t1, "Basis")

        # Tab 2: DSP
        t2 = QWidget(); g2 = QGridLayout(t2); g2.setSpacing(5)
        self.chk_shift = QCheckBox("SHIFT aan"); self.spn_shift = QSpinBox()
        self.spn_shift.setRange(-1000, 1000); self.spn_shift.setSuffix(" Hz")
        self.chk_width = QCheckBox("WIDTH aan"); self.cmb_width = QComboBox()
        self.cmb_width.addItems(_WIDTH_LABELS_LIST)
        self.chk_cont  = QCheckBox("CONTOUR aan"); self.spn_cont = QSpinBox()
        self.spn_cont.setRange(1, 30)
        self.chk_notch = QCheckBox("NOTCH aan"); self.spn_notch = QSpinBox()
        self.spn_notch.setRange(100, 3000); self.spn_notch.setSuffix(" Hz")
        self.chk_nar   = QCheckBox("NAR (smal filter)")
        for r, (c1, c2) in enumerate([
            (self.chk_shift, self.spn_shift), (self.chk_width, self.cmb_width),
            (self.chk_cont, self.spn_cont),   (self.chk_notch, self.spn_notch),
        ]):
            g2.addWidget(c1, r, 0); g2.addWidget(c2, r, 1)
        g2.addWidget(self.chk_nar, 4, 0, 1, 2)
        tabs.addTab(t2, "DSP")

        # Tab 3: Ontvanger
        t3 = QWidget(); g3 = QGridLayout(t3); g3.setSpacing(5)
        self.cmb_att = QComboBox(); self.cmb_att.addItems(["OFF","-6dB","-12dB","-18dB"])
        self.cmb_ipo = QComboBox(); self.cmb_ipo.addItems(["IPO ON","AMP1","AMP2"])
        self.cmb_ipo.setCurrentIndex(1)
        self.cmb_rflt= QComboBox(); self.cmb_rflt.addItems(["AUTO","3kHz","6kHz","15kHz"])
        self.cmb_nb  = QComboBox(); self.cmb_nb.addItems(["OFF","Narrow","Wide"])
        self.chk_nr  = QCheckBox("DNR (digitale ruisonderdrukking)")
        self.spn_af  = QSpinBox(); self.spn_af.setRange(0, 255); self.spn_af.setValue(180)
        self.spn_rf  = QSpinBox(); self.spn_rf.setRange(0, 255); self.spn_rf.setValue(255)
        self.cmb_agc = QComboBox(); self.cmb_agc.addItems(["OFF","FAST","MID","SLOW","AUTO"])
        self.cmb_agc.setCurrentIndex(4)
        for r, (lbl, w) in enumerate([
            ("ATT:", self.cmb_att), ("IPO:", self.cmb_ipo),
            ("R.FLT:", self.cmb_rflt), ("NB:", self.cmb_nb),
            ("AF gain:", self.spn_af), ("RF gain:", self.spn_rf),
            ("AGC:", self.cmb_agc),
        ]):
            g3.addWidget(QLabel(lbl), r, 0); g3.addWidget(w, r, 1)
        g3.addWidget(self.chk_nr, len([0]*7), 0, 1, 2)
        tabs.addTab(t3, "Ontvanger")

        # Tab 4: Zender
        t4 = QWidget(); g4 = QGridLayout(t4); g4.setSpacing(5)
        self.spn_pwr = QSpinBox(); self.spn_pwr.setRange(5, 100)
        self.spn_pwr.setValue(100); self.spn_pwr.setSuffix(" W")
        g4.addWidget(QLabel("TX Vermogen:"), 0, 0); g4.addWidget(self.spn_pwr, 0, 1)
        g4.setRowStretch(1, 1)
        tabs.addTab(t4, "Zender")

        ev.addWidget(tabs, 1)

        btn_apply = QPushButton("Wijzigingen opslaan"); btn_apply.setObjectName("ok")
        btn_apply.clicked.connect(self._do_apply_edit)
        ev.addWidget(btn_apply)

        split.addWidget(edit_widget, 2)
        fav_layout.addLayout(split, 1)

        self._tabs.addTab(fav_widget, "Favorieten")

        # ── Tab 2: EIBI — lazy geladen (pas bij eerste klik) ─────────────────
        self._eibi_tab = _EibiTab(
            cat      = self._cat,
            apply_fn = self._apply_eibi,
            lazy     = True,        # vul tabel pas wanneer tab zichtbaar wordt
        )
        self._tabs.addTab(self._eibi_tab, "EIBI")
        self._tabs.currentChanged.connect(self._on_tab_changed)

        root.addWidget(self._tabs, 1)

        btn_close = QPushButton("Sluiten")
        btn_close.clicked.connect(self.accept)
        root.addWidget(btn_close, alignment=Qt.AlignRight)

    # ── Tabel ──────────────────────────────────────────────────────────────

    def _fill_table(self):
        self._tbl.setRowCount(0)
        for e in self._entries:
            self._append_row(e)

    def _append_row(self, e: FreqEntry):
        row = self._tbl.rowCount()
        self._tbl.insertRow(row)
        _LEFT_FAV = {0, 4}   # naam en notitie
        for col, val in enumerate([
            e.name,
            f"{e.freq_hz / 1_000_000:.6f}",
            e.mode, e.band, e.notes,
        ]):
            item = QTableWidgetItem(val)
            item.setTextAlignment(
                Qt.AlignLeft | Qt.AlignVCenter if col in _LEFT_FAV
                else Qt.AlignCenter)
            self._tbl.setItem(row, col, item)

    def _row_selected(self, row: int):
        self._selected = row
        if 0 <= row < len(self._entries):
            e = self._entries[row]
            self._load_entry_to_form(e)
            # Stuur meteen naar radio (zelfde gedrag als EIBI-tab)
            if self._apply_fav:
                try: self._apply_fav(e)
                except Exception: pass

    def _load_entry_to_form(self, e: FreqEntry):
        self.edt_name.setText(e.name)
        self.edt_freq.setValue(e.freq_hz / 1_000_000)
        idx = self.cmb_mode.findText(e.mode)
        if idx >= 0: self.cmb_mode.setCurrentIndex(idx)
        self.edt_band.setText(e.band)
        self.edt_note.setText(e.notes)
        # DSP
        self.chk_shift.setChecked(e.dsp_shift_on); self.spn_shift.setValue(e.dsp_shift_hz)
        self.chk_width.setChecked(e.dsp_width_on); self.cmb_width.setCurrentIndex(e.dsp_width_idx)
        self.chk_cont.setChecked(e.dsp_cont_on);   self.spn_cont.setValue(e.dsp_cont_pos)
        self.chk_notch.setChecked(e.dsp_notch_on); self.spn_notch.setValue(e.dsp_notch_hz)
        self.chk_nar.setChecked(e.dsp_nar)
        # Ontvanger
        self.cmb_att.setCurrentIndex(e.att_idx)
        self.cmb_ipo.setCurrentIndex(e.ipo_idx)
        self.cmb_rflt.setCurrentIndex(e.rflt_idx)
        self.cmb_nb.setCurrentIndex(e.nb_idx)
        self.chk_nr.setChecked(e.nr_on)
        self.spn_af.setValue(e.af_gain); self.spn_rf.setValue(e.rf_gain)
        self.cmb_agc.setCurrentIndex(e.agc_idx)
        # Zender
        self.spn_pwr.setValue(e.tx_power)

    def _form_to_entry(self, e: FreqEntry):
        e.name         = self.edt_name.text().strip() or e.name
        e.freq_hz      = int(round(self.edt_freq.value() * 1_000_000))
        e.mode         = self.cmb_mode.currentText()
        e.band         = self.edt_band.text().strip()
        e.notes        = self.edt_note.text().strip()
        e.dsp_shift_on = self.chk_shift.isChecked(); e.dsp_shift_hz = self.spn_shift.value()
        e.dsp_width_on = self.chk_width.isChecked(); e.dsp_width_idx= self.cmb_width.currentIndex()
        e.dsp_cont_on  = self.chk_cont.isChecked();  e.dsp_cont_pos = self.spn_cont.value()
        e.dsp_notch_on = self.chk_notch.isChecked(); e.dsp_notch_hz = self.spn_notch.value()
        e.dsp_nar      = self.chk_nar.isChecked()
        e.att_idx      = self.cmb_att.currentIndex()
        e.ipo_idx      = self.cmb_ipo.currentIndex()
        e.rflt_idx     = self.cmb_rflt.currentIndex()
        e.nb_idx       = self.cmb_nb.currentIndex()
        e.nr_on        = self.chk_nr.isChecked()
        e.af_gain      = self.spn_af.value(); e.rf_gain = self.spn_rf.value()
        e.agc_idx      = self.cmb_agc.currentIndex()
        e.tx_power     = self.spn_pwr.value()

    # ── Acties ─────────────────────────────────────────────────────────────

    def set_current_entry(self, entry: FreqEntry):
        self._pending = entry

    def _do_save_current(self):
        e = getattr(self, "_pending", None)
        if e is None:
            self._status.setText("Geen huidig beschikbaar – open opnieuw vanuit het hoofdvenster.")
            return
        from datetime import datetime
        e.created = datetime.now().strftime("%Y-%m-%d %H:%M")
        self._entries.append(e)
        self._append_row(e)
        save_memories(self._entries)
        self._tbl.scrollToBottom()
        self._tbl.selectRow(len(self._entries) - 1)
        self._status.setText(f"'{e.name}' bewaard")

    def _do_load(self):
        if self._selected < 0 or self._selected >= len(self._entries):
            return
        self.selected_entry = self._entries[self._selected]
        self.accept()

    def _do_delete(self):
        row = self._selected
        if row < 0 or row >= len(self._entries):
            return
        name = self._entries[row].name
        self._entries.pop(row); self._tbl.removeRow(row)
        save_memories(self._entries)
        self._selected = -1
        self._status.setText(f"'{name}' verwijderd")

    def _do_apply_edit(self):
        row = self._selected
        if row < 0 or row >= len(self._entries):
            self._status.setText("Selecteer eerst een rij in de tabel.")
            return
        e = self._entries[row]
        self._form_to_entry(e)
        save_memories(self._entries)
        # Tabel bijwerken
        for col, val in enumerate([e.name, f"{e.freq_hz/1e6:.6f}",
                                    e.mode, e.band, e.notes]):
            if self._tbl.item(row, col):
                self._tbl.item(row, col).setText(val)
        self._status.setText("Wijzigingen opgeslagen")

    def _move(self, direction: int):
        row = self._selected; new_row = row + direction
        if new_row < 0 or new_row >= len(self._entries): return
        self._entries[row], self._entries[new_row] = \
            self._entries[new_row], self._entries[row]
        save_memories(self._entries)
        self._fill_table(); self._tbl.selectRow(new_row)

    def _do_eibi_import(self):
        dlg = EIBIImportDialog(parent=self)
        if dlg.exec():
            new_entries = dlg.get_entries()
            for e in new_entries:
                self._entries.append(e)
                self._append_row(e)
            if new_entries:
                save_memories(self._entries)
                self._status.setText(f"{len(new_entries)} EIBI-vermeldingen geïmporteerd")

    def get_selected(self) -> FreqEntry | None:
        return getattr(self, "selected_entry", None)

    def _on_tab_changed(self, index: int):
        """Laad EIBI-tabel pas wanneer het tabblad voor het eerst getoond wordt."""
        if index == 1:   # EIBI-tab
            self._eibi_tab.ensure_loaded()


# ── EIBI-import ───────────────────────────────────────────────────────────────

class EIBIImportDialog(QDialog):
    """
    Importeer frequenties uit een EIBI-schedulebestand.

    EIBI-formaat (sked_a.csv of sked_b.csv van eibispace.de):
      kHz;start;stop;dag;land;station;target;taal;...
    of comma-gescheiden.
    """

    def __init__(self, parent=None):
        import queue as _q
        super().__init__(parent)
        self._raw_entries: list[dict] = []
        self._selected_entries: list[FreqEntry] = []
        # Thread-safe queue: achtergrond-thread schrijft, drain-timer leest
        self._dl_queue = _q.Queue()
        self._drain_timer = QTimer(self)
        self._drain_timer.timeout.connect(self._drain)
        self._drain_timer.start(40)   # drain elke 40 ms → vloeiende voortgang
        self.setWindowTitle("EIBI-frequenties importeren")
        self.resize(880, 540)
        self.setStyleSheet(_QSS_DIALOG)
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(6)

        # Bestandsselectie — lokaal of internet
        file_row = QHBoxLayout()
        file_row.addWidget(QLabel("EIBI-bestand:"))
        self._file_lbl = QLabel("(geen bestand geselecteerd)")
        self._file_lbl.setStyleSheet(f"color:{TEXT_DIM}; font-style:italic;")
        btn_open = QPushButton("📂 Bladeren…"); btn_open.setObjectName("test")
        btn_open.clicked.connect(self._open_file)
        file_row.addWidget(self._file_lbl, 1)
        file_row.addWidget(btn_open)
        root.addLayout(file_row)

        # Download van internet
        dl_row = QHBoxLayout()
        dl_row.addWidget(QLabel("Of download direct van eibispace.de:"))
        self._cmb_season = QComboBox()
        self._cmb_season.addItems(["Seizoen A (jan–jun)", "Seizoen B (jul–dec)"])
        self._cmb_season.setFixedWidth(160)
        self._btn_dl = QPushButton("🌐 Download"); self._btn_dl.setObjectName("ok")
        self._btn_dl.clicked.connect(self._do_download)
        dl_row.addWidget(self._cmb_season)
        dl_row.addWidget(self._btn_dl)
        dl_row.addStretch()
        root.addLayout(dl_row)

        # Voortgangsbalk (verborgen totdat een download start)
        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setFixedHeight(18)
        self._progress.setTextVisible(True)
        self._progress.setStyleSheet(f"""
            QProgressBar {{
                background: #1A1A1A;
                border: 1px solid {BORDER};
                border-radius: 3px;
                color: {TEXT_H1};
                font-size: 7pt;
                text-align: center;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1A5A1A, stop:0.5 {ACCENT}, stop:1 #4CAF50);
                border-radius: 2px;
            }}
        """)
        self._progress.setVisible(False)
        root.addWidget(self._progress)

        # Zoekfilter
        filt_row = QHBoxLayout()
        filt_row.addWidget(QLabel("Zoeken (station / freq):"))
        self._search = QLineEdit(); self._search.setPlaceholderText("bijv. BBC of 6005")
        self._search.textChanged.connect(self._apply_filter)
        filt_row.addWidget(self._search, 1)
        root.addLayout(filt_row)

        self._status = QLabel("Laad een EIBI-bestand om te beginnen")
        self._status.setStyleSheet(f"color:{TEXT_DIM}; font-size:7pt;")
        root.addWidget(self._status)

        # Tabel
        cols = ["Frequentie (kHz)", "Station", "Start", "Stop", "Land", "Taal", "Doel"]
        self._tbl = QTableWidget(0, len(cols))
        self._tbl.setHorizontalHeaderLabels(cols)
        self._tbl.setSelectionBehavior(QTableWidget.SelectRows)
        self._tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        self._tbl.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self._tbl.verticalHeader().setVisible(False)
        self._tbl.horizontalHeader().setStretchLastSection(True)
        self._tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self._tbl.setColumnWidth(0, 110)
        self._tbl.setColumnWidth(2, 55); self._tbl.setColumnWidth(3, 55)
        self._tbl.setColumnWidth(4, 55); self._tbl.setColumnWidth(5, 55)
        self._tbl.setColumnWidth(6, 55)
        root.addWidget(self._tbl, 1)

        # Knoppen
        btn_row = QHBoxLayout()
        lbl_sel = QLabel("Selecteer rijen (Ctrl+klik voor meerdere)")
        lbl_sel.setStyleSheet(f"color:{TEXT_DIM}; font-size:7pt;")
        btn_import = QPushButton("✓ Geselecteerde importeren"); btn_import.setObjectName("ok")
        btn_cancel = QPushButton("Annuleer")
        btn_import.clicked.connect(self._do_import)
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(lbl_sel); btn_row.addStretch()
        btn_row.addWidget(btn_import); btn_row.addWidget(btn_cancel)
        root.addLayout(btn_row)

    def _open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "EIBI-bestand openen", "",
            "EIBI bestanden (*.csv *.txt);;Alle bestanden (*.*)")
        if not path:
            return
        self._file_lbl.setText(path)
        self._parse_file(path)

    # ── Internet-download ─────────────────────────────────────────────────

    _EIBI_BASE  = "https://www.eibispace.de"
    _EIBI_HOME  = "https://www.eibispace.de/"

    def _do_download(self):
        import threading
        season_hint = "a" if self._cmb_season.currentIndex() == 0 else "b"
        self._progress.setValue(0)
        self._progress.setRange(0, 0)          # onbepaald terwijl we zoeken
        self._progress.setFormat("Zoeken naar actueel bestand…")
        self._progress.setVisible(True)
        self._btn_dl.setEnabled(False)
        self._status.setText("Ophalen bestandslijst van eibispace.de…")
        threading.Thread(target=self._detect_and_download,
                         args=(season_hint,), daemon=True).start()

    # ── Drain-timer: verwerkt queue-berichten in de GUI-thread ───────────

    def _drain(self):
        import queue as _q
        while True:
            try:
                msg = self._dl_queue.get_nowait()
            except _q.Empty:
                break
            kind = msg[0]
            if kind == "status":
                self._status.setText(msg[1])
            elif kind == "file_lbl":
                self._file_lbl.setText(msg[1])
            elif kind == "progress_range":
                self._progress.setRange(0, msg[1])
            elif kind == "progress_value":
                self._progress.setValue(msg[1])
            elif kind == "progress_fmt":
                self._progress.setFormat(msg[1])
            elif kind == "done":
                self._download_done(msg[1], msg[2])
            elif kind == "fail":
                self._download_failed(msg[1])

    # ── Stap 1: detecteer het actuele bestandspad ─────────────────────────

    def _detect_and_download(self, season_hint: str):
        import urllib.request, re, ssl
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode    = ssl.CERT_NONE
        opener = urllib.request.build_opener(
            urllib.request.HTTPSHandler(context=ctx))
        HEADERS = {"User-Agent": "Mozilla/5.0 FT950-Controller"}

        try:
            req  = urllib.request.Request(self._EIBI_HOME, headers=HEADERS)
            html = opener.open(req, timeout=10).read().decode("utf-8", errors="replace")

            raw_hrefs = re.findall(r'href=[^\s>]*sked-[^"\'> ]*\.csv',
                                   html, re.IGNORECASE)
            found = [h.split('="')[-1].strip('"\'') for h in raw_hrefs]
            matches = [f for f in found if f"-{season_hint}" in f.lower()]
            if not matches:
                matches = found

            if not matches:
                self._dl_queue.put(("fail",
                    "Geen sked-*.csv gevonden op eibispace.de. "
                    "Gebruik 'Bladeren' om een lokaal bestand te laden."))
                return

            path = matches[0]
            url  = path if path.startswith("http") else self._EIBI_BASE + "/" + path
            fn   = url.split("/")[-1]
            self._dl_queue.put(("file_lbl",    url))
            self._dl_queue.put(("status",      f"Gevonden: {fn}  —  bezig met downloaden…"))
            self._dl_queue.put(("progress_fmt", f"Downloaden {fn}…"))

            self._download_thread(url, opener)

        except Exception as ex:
            self._dl_queue.put(("fail", f"Kan eibispace.de niet bereiken: {ex}"))

    # ── Stap 2: download het bestand in chunks ────────────────────────────

    def _download_thread(self, url: str, opener=None):
        """
        Chunk-gewijze download; alle GUI-updates via self._dl_queue (thread-safe).
        """
        import urllib.request, ssl
        CHUNK = 8192
        if opener is None:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode    = ssl.CERT_NONE
            opener = urllib.request.build_opener(
                urllib.request.HTTPSHandler(context=ctx))
        HEADERS = {"User-Agent": "Mozilla/5.0 FT950-Controller"}
        try:
            req   = urllib.request.Request(url, headers=HEADERS)
            resp  = opener.open(req, timeout=20)
            total = int(resp.headers.get("Content-Length", 0))

            if total > 0:
                self._dl_queue.put(("progress_range", total))
                self._dl_queue.put(("progress_fmt",
                    f"Downloaden… 0 / {total//1024} kB"))
            else:
                self._dl_queue.put(("progress_range", 0))   # bouncer
                self._dl_queue.put(("progress_fmt", "Downloaden…"))

            chunks = []; downloaded = 0
            while True:
                chunk = resp.read(CHUNK)
                if not chunk:
                    break
                chunks.append(chunk)
                downloaded += len(chunk)
                if total > 0:
                    pct = int(downloaded / total * 100)
                    self._dl_queue.put(("progress_value", downloaded))
                    self._dl_queue.put(("progress_fmt",
                        f"{downloaded//1024} / {total//1024} kB  ({pct}%)"))
                else:
                    self._dl_queue.put(("progress_fmt",
                        f"{downloaded//1024} kB ontvangen…"))

            raw   = b"".join(chunks).decode("utf-8", errors="replace")
            lines = raw.splitlines()
            self._dl_queue.put(("done", lines, url))

        except Exception as ex:
            self._dl_queue.put(("fail", str(ex)))

    def _download_done(self, lines: list, url: str):
        """Wordt aangeroepen in GUI-thread na succesvolle download."""
        self._progress.setRange(0, 100)
        self._progress.setValue(100)
        self._progress.setFormat("Download voltooid  ✓")
        self._btn_dl.setEnabled(True)
        self._parse_lines(lines, url)
        # Balk na 3 s automatisch verbergen
        QTimer.singleShot(3000, lambda: self._progress.setVisible(False))

    def _download_failed(self, msg: str):
        """Wordt aangeroepen in GUI-thread bij downloadfout."""
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setFormat("Download mislukt  ✗")
        self._progress.setStyleSheet(self._progress.styleSheet().replace(
            "#4CAF50", "#EF5350").replace("#1A5A1A", "#5A1010"))
        self._btn_dl.setEnabled(True)
        self._status.setText(f"Download mislukt: {msg}")

    def _parse_lines(self, lines: list[str], source: str = ""):
        """Verwerk een lijst van regels (string) als EIBI-data."""
        self._raw_entries.clear()
        count = 0
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            sep = ";" if ";" in line else ","
            parts = [p.strip() for p in line.split(sep)]
            if len(parts) < 2:
                continue
            try:
                freq_khz = float(parts[0])
                if freq_khz < 100 or freq_khz > 100_000:
                    continue
            except ValueError:
                continue
            # Werkelijk EIBI sked-a.csv formaat (bevestigd uit bestand):
            # parts[0] = kHz
            # parts[1] = Time(UTC)  bijv. "0000-2400"  (start-stop gecombineerd)
            # parts[2] = Days
            # parts[3] = ITU landcode  bijv. "IND"
            # parts[4] = Stationsnaam  bijv. "VTX1 Indian Navy"
            # parts[5] = Taalcode      bijv. "RUS"  of  ""
            # parts[6] = Doelgebied    bijv. "SAs"
            # parts[7] = Opmerkingen
            time_f = parts[1] if len(parts) > 1 else ""
            # Splits "0000-2400" → start="0000", stop="2400"
            if len(time_f) >= 9 and time_f[4] == "-":
                start, stop = time_f[:4], time_f[5:9]
            else:
                start = time_f; stop = ""
            self._raw_entries.append({
                "freq_khz": freq_khz,
                "start":    start,
                "stop":     stop,
                "day":      parts[2] if len(parts) > 2 else "",
                "country":  parts[3] if len(parts) > 3 else "",   # ITU
                "station":  parts[4] if len(parts) > 4 else "",   # naam
                "language": parts[5] if len(parts) > 5 else "",   # taal
                "target":   parts[6] if len(parts) > 6 else "",   # doel
            })
            count += 1
        src = source.split("/")[-1] if source else "data"
        self._status.setText(f"{count} vermeldingen geladen uit {src}")
        self._apply_filter()

    def _parse_file(self, path: str):
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
        except Exception as ex:
            self._status.setText(f"Fout bij lezen: {ex}")
            return
        self._parse_lines(lines, path)

    def _apply_filter(self):
        term = self._search.text().strip().lower()
        self._tbl.setRowCount(0)
        for d in self._raw_entries:
            if term and term not in d["station"].lower() \
                     and term not in str(d["freq_khz"]):
                continue
            row = self._tbl.rowCount()
            self._tbl.insertRow(row)
            for col, val in enumerate([
                f"{d['freq_khz']:.1f}",
                d["station"], d["start"], d["stop"],
                d["country"], d["language"], d["target"],
            ]):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignCenter)
                item.setData(Qt.UserRole, d)
                self._tbl.setItem(row, col, item)

    def _do_import(self):
        rows = sorted({idx.row() for idx in self._tbl.selectedIndexes()})
        if not rows:
            return
        self._selected_entries.clear()
        for row in rows:
            item = self._tbl.item(row, 0)
            if not item: continue
            d = item.data(Qt.UserRole)
            if not d: continue
            freq_hz = int(d["freq_khz"] * 1000)
            # Maak direct een EibiRecord aan — geen FreqEntry-tussenstap
            rec = EibiRecord(
                freq_hz  = freq_hz,
                station  = d.get("station", "") or f"{d['freq_khz']:.1f} kHz",
                country  = d.get("country",  ""),
                start    = d.get("start",    ""),
                stop     = d.get("stop",     ""),
                language = d.get("language", ""),
                target   = d.get("target",   ""),
                mode     = "AM",
                af_gain  = 60,
            )
            self._selected_entries.append(rec)
        self.accept()

    def get_entries(self) -> list:
        """Geeft lijst van EibiRecord objecten terug."""
        return self._selected_entries


# ── S-meter kalibratie ────────────────────────────────────────────────────────

class SMeterCalibDialog(QDialog):
    """
    S-meter kalibratie.

    Voor elk S-punt stel je de bijbehorende ruwe waarde (0-255) in.
    Je kunt de radio afstemmen op een bekend signaal en op 'Gebruik actueel'
    klikken om de huidige meterstand op te slaan als dat S-punt.

    Standaard FT-950 schaling per S-unit ≈ 6 dB:
      S1=18  S3=54  S5=90  S7=126  S9=162  +20=189  +40=216  +60=243
    """

    _LABELS   = ["S 1", "S 3", "S 5", "S 7", "S 9", "+20 dB", "+40 dB", "+60 dB"]
    _DEFAULTS = [18, 54, 90, 126, 162, 189, 216, 243]

    def __init__(self, smeter_widget, current_cal: list, parent=None):
        super().__init__(parent)
        self._smeter      = smeter_widget   # SMeterBar widget (live preview)
        self._current_raw = 0               # live ruwe waarde van radio
        self.setWindowTitle("S-meter kalibratie")
        self.setFixedWidth(460)
        self.setStyleSheet(_QSS_DIALOG)
        self._build(current_cal)

        # Live update timer
        self._live_timer = QTimer(self)
        self._live_timer.timeout.connect(self._refresh_live)
        self._live_timer.start(300)

    # ── Opbouw ─────────────────────────────────────────────────────────────

    def _build(self, cal: list):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        # Live S-meter preview
        grp_live = QGroupBox("Live S-meter (preview)")
        lv = QVBoxLayout(grp_live); lv.setSpacing(4)
        from .widgets import SMeterBar
        self._preview = SMeterBar("S")
        self._preview.set_calibration(cal)
        self._live_lbl = QLabel("Ruwe waarde: —")
        self._live_lbl.setStyleSheet(f"color:{TEXT_H1}; font-family:Consolas; font-size:9pt;")
        lv.addWidget(self._preview)
        lv.addWidget(self._live_lbl)
        root.addWidget(grp_live)

        # Kalibratie-tabel
        grp_cal = QGroupBox("S-punt kalibratie  (ruwe waarde 0–255)")
        gv = QVBoxLayout(grp_cal); gv.setSpacing(4)

        self._spins: list[QSpinBox] = []
        for i, (lbl, val) in enumerate(zip(self._LABELS, cal)):
            row = QHBoxLayout(); row.setSpacing(6)
            lbl_w = QLabel(lbl)
            lbl_w.setFixedWidth(56)
            lbl_w.setStyleSheet(f"color:{TEXT_H1}; font-family:Consolas; font-size:8pt;")

            spn = _spinbox(0, 255, val)
            spn.valueChanged.connect(self._on_spin_change)
            self._spins.append(spn)

            btn_use = QPushButton("← Actueel"); btn_use.setFixedWidth(80)
            btn_use.setObjectName("test")
            btn_use.clicked.connect(lambda _, idx=i: self._use_current(idx))
            btn_use.setToolTip("Sla de huidige live S-meter waarde op als dit S-punt")

            row.addWidget(lbl_w)
            row.addWidget(spn, 1)
            row.addWidget(btn_use)
            gv.addLayout(row)

        root.addWidget(grp_cal)

        # Knoppen
        btn_row = QHBoxLayout(); btn_row.setSpacing(8)
        btn_def  = QPushButton("Standaard herstellen")
        btn_ok   = QPushButton("Opslaan"); btn_ok.setObjectName("ok")
        btn_can  = QPushButton("Annuleer")
        btn_def.clicked.connect(self._reset_defaults)
        btn_ok.clicked.connect(self.accept)
        btn_can.clicked.connect(self.reject)
        btn_row.addWidget(btn_def); btn_row.addStretch()
        btn_row.addWidget(btn_ok); btn_row.addWidget(btn_can)
        root.addLayout(btn_row)

    # ── Logica ─────────────────────────────────────────────────────────────

    def set_live_source(self, fn):
        """
        Stel een callable in die de actuele ruwe S-meter waarde teruggeeft.
        Wordt bij elke klik op '← Actueel' én bij elke refresh-timer
        direct aangeroepen — altijd verse waarde.
        """
        self._live_source = fn

    # compat: oud mainwindow-API
    def set_live_value(self, raw: int):
        self._current_raw = raw

    def _get_live(self) -> int:
        if hasattr(self, "_live_source"):
            return self._live_source()
        return self._current_raw

    def _refresh_live(self):
        raw = self._get_live()
        self._current_raw = raw
        self._preview.set_value(raw)
        # Bepaal welk S-punt dit ongeveer is
        cal = self.get_calibration()
        labels = ["S1","S3","S5","S7","S9","+20","+40","+60"]
        level = "< S1"
        for i, r in enumerate(cal):
            if raw >= r:
                level = labels[i]
        self._live_lbl.setText(f"Ruwe waarde: {raw}   ≈ {level}")

    def _on_spin_change(self):
        self._preview.set_calibration(self.get_calibration())

    def _use_current(self, idx: int):
        """Sla de ACTUELE live waarde op als dit S-punt (directe call)."""
        self._spins[idx].setValue(self._get_live())

    def _reset_defaults(self):
        for spn, val in zip(self._spins, self._DEFAULTS):
            spn.setValue(val)

    def get_calibration(self) -> list:
        return [spn.value() for spn in self._spins]


# ── Frequentie keypad ─────────────────────────────────────────────────────────

_KP_BTN = f"""
    QPushButton {{
        background: #252525;
        color: {VFD_BRIGHT};
        border: 1px solid #3A3A3A;
        border-radius: 4px;
        font-family: Consolas;
        font-size: 14pt;
        font-weight: bold;
        padding: 6px;
        min-width: 52px;
        min-height: 44px;
    }}
    QPushButton:hover   {{ background: #333; border-color: {VFD_AMBER}; }}
    QPushButton:pressed {{ background: #1A1A1A; }}
    QPushButton#ok      {{ background: #1A3A1A; color: {VFD_BRIGHT};
                           border-color: {VFD_BRIGHT}; font-size: 12pt; }}
    QPushButton#ok:hover {{ background: #2A5A2A; }}
    QPushButton#cancel  {{ background: #3A1818; color: #EF5350;
                           border-color: #8B1A1A; font-size: 10pt; }}
    QPushButton#bsp     {{ color: {VFD_AMBER}; font-size: 12pt; }}
    QPushButton#clr     {{ color: #EF5350;     font-size: 11pt; }}
"""


class _FreqDisplay(QWidget):
    """VFD-weergave van de ingevoerde frequentie met auto-opmaak."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._digits: list = []
        self.setFixedHeight(64)
        self.setStyleSheet(f"background:{BG_DISPLAY}; border-radius:4px;")

    def set_digits(self, digits: list):
        self._digits = digits[:]
        self.update()

    def formatted(self) -> str:
        d = self._digits
        n = len(d)
        if n == 0:  return ""
        if n <= 2:  return "".join(d)
        if n <= 5:  return "".join(d[:2]) + "." + "".join(d[2:])
        return "".join(d[:2]) + "." + "".join(d[2:5]) + "." + "".join(d[5:])

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor(BG_DISPLAY))
        ghost = "88.888.888"
        font = QFont("Consolas", 26, QFont.Bold)
        p.setFont(font)
        fm = QFontMetrics(font)
        y = (self.height() - fm.height()) // 2 + fm.ascent()
        x0 = (self.width() - fm.horizontalAdvance(ghost)) // 2
        p.setPen(QColor(VFD_OFF));    p.drawText(x0, y, ghost)
        s = self.formatted()
        if s:
            xr = (self.width() - fm.horizontalAdvance(s)) // 2
            p.setPen(QColor(VFD_BRIGHT)); p.drawText(xr, y, s)
        lf = QFont("Consolas", 9)
        p.setFont(lf); p.setPen(QColor(VFD_DIM))
        lfm = QFontMetrics(lf)
        p.drawText(self.width() - lfm.horizontalAdvance("kHz") - 4,
                   self.height() - 4, "kHz")
        p.end()


class FreqKeypadDialog(QDialog):
    """
    Frequentie-keypad voor handmatige invoer (bij GEN-knop).

    Digit-buffer (zoals de echte FT-950, max 8 cijfers):
      1 4 1 9 5 0 0 0  →  14.195.000  =  14.195.000 Hz
      1 4              →  14.000.000  =  14 MHz  (rechts opvullen met 0)
    """

    def __init__(self, current_hz: int = 14_000_000, parent=None):
        super().__init__(parent)
        self._digits: list = []
        self._result_hz = current_hz
        self.setWindowTitle("Frequentie invoeren")
        self.setStyleSheet(f"QDialog, QWidget {{ background:{BG_PANEL}; }}" + _KP_BTN)
        self.setFixedSize(340, 430)
        self._build()
        self._load_current(current_hz)

    # ── Opbouw ────────────────────────────────────────────────────────────

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # VFD display
        self._disp = _FreqDisplay()
        root.addWidget(self._disp)

        # Hint
        hint = QLabel("Typ de frequentie in Hz  (bijv. 1 4 1 9 5 0 0 0 = 14.195 MHz)")
        hint.setStyleSheet(f"color:{TEXT_DIM}; font-size:7pt;")
        hint.setWordWrap(True)
        root.addWidget(hint)

        # Keypad grid
        grid = QGridLayout()
        grid.setSpacing(6)

        for lbl, row, col in [
            ("7", 0, 0), ("8", 0, 1), ("9", 0, 2),
            ("4", 1, 0), ("5", 1, 1), ("6", 1, 2),
            ("1", 2, 0), ("2", 2, 1), ("3", 2, 2),
            ("0", 3, 1),
        ]:
            b = QPushButton(lbl)
            b.clicked.connect(lambda _, d=lbl: self._digit(d))
            grid.addWidget(b, row, col)

        b_clr = QPushButton("CLR");  b_clr.setObjectName("clr")
        b_bsp = QPushButton("◀ DEL"); b_bsp.setObjectName("bsp")
        b_ok  = QPushButton("OK ↵"); b_ok.setObjectName("ok")

        b_clr.clicked.connect(self._clear)
        b_bsp.clicked.connect(self._backspace)
        b_ok.clicked.connect(self._confirm)

        grid.addWidget(b_clr, 0, 3)
        grid.addWidget(b_bsp, 1, 3)
        grid.addWidget(b_ok,  2, 3, 2, 1)   # 2 rijen hoog

        root.addLayout(grid)

        b_cancel = QPushButton("Annuleer")
        b_cancel.setObjectName("cancel")
        b_cancel.clicked.connect(self.reject)
        root.addWidget(b_cancel)

    def _load_current(self, hz: int):
        s = f"{hz:08d}".lstrip("0") or "0"
        self._digits = list(s)
        self._refresh()

    # ── Logica ────────────────────────────────────────────────────────────

    def _digit(self, d: str):
        if len(self._digits) < 8:
            self._digits.append(d)
        self._refresh()

    def _backspace(self):
        if self._digits:
            self._digits.pop()
        self._refresh()

    def _clear(self):
        self._digits.clear()
        self._refresh()

    def _refresh(self):
        self._disp.set_digits(self._digits)

    def _confirm(self):
        padded = (self._digits + ["0"] * 8)[:8]
        hz = int("".join(padded))
        self._result_hz = max(30_000, min(56_000_000, hz))
        self.accept()

    def get_freq_hz(self) -> int:
        return self._result_hz

    # ── Toetsenbordinvoer ────────────────────────────────────────────────

    def keyPressEvent(self, event):
        key = event.key()
        if Qt.Key_0 <= key <= Qt.Key_9:
            self._digit(str(key - Qt.Key_0))
        elif key in (Qt.Key_Backspace, Qt.Key_Delete):
            self._backspace()
        elif key == Qt.Key_Escape:
            self.reject()
        elif key in (Qt.Key_Return, Qt.Key_Enter):
            self._confirm()
        else:
            super().keyPressEvent(event)
