"""
FT-950 Controller — CAT-communicatie (standalone, FT-950 specifiek)

CAT Reference Book pagina-verwijzingen:
  FA<8 digits>;  — VFO-A frequentie instellen/lezen  (p.9)
  FB<8 digits>;  — VFO-B frequentie instellen/lezen  (p.9)
  MD0<code>;     — Modus instellen  (p.11)
  MD<fixed>;     — Modus lezen      (p.11)
  IF;            — Alles-in-één status  (p.10)
  ID;            — Identificatie (antwoord: ID0310;)  (p.9)
  VS<0|1>;       — VFO selectie  (p.17)
  PA0<0|1|2>;    — IPO/Preamp  (p.13)
  RA0<0-3>;      — Attenuator  (p.14)
  RF<0><000-255>; — RF gain  (p.14)
  AG0<000-255>;  — AF gain  (p.4)
  KR<0|1>;       — Keyer aan/uit  (p.10)
  BI<0|1>;       — Break-in  (p.4)
  NB0<0|1|2>;    — Noise blanker  (p.12)
  NR0<0|1>;      — Noise reduction  (p.12)
  NA0<0|1>;      — Narrow filter  (p.12)
  MX<0|1>;       — MOX (PTT)  (p.12)
  PC<005-100>;   — Zendvermogen  (p.13)
  AC00<0|1|2>;   — Antenne-tuner  (p.4)
  MC<000-117>;   — Memory channel  (p.11)
  MR<000-117>;   — Memory channel lezen  (p.11)
  MW<...>;       — Memory channel schrijven  (p.12)
"""

import threading
import time

_serial_available = False
try:
    import serial
    import serial.tools.list_ports
    _serial_available = True
except ImportError:
    pass


# ── Moduscodes conform CAT ref. p.11 ─────────────────────────────────────────
MODE_CODES = {
    "LSB":    "1", "USB":    "2", "CW":     "3",
    "FM":     "4", "AM":     "5", "RTTY":   "6",
    "CW-R":   "7", "PKT-L":  "8", "FSK-R":  "9",
    "PKT-FM": "A", "FM-N":   "B", "PKT-U":  "C",
    "AM-N":   "D",
}
CODE_MODES = {v: k for k, v in MODE_CODES.items()}


def list_ports() -> list[str]:
    """Geef beschikbare seriële poorten terug."""
    if not _serial_available:
        return []
    return [p.device for p in serial.tools.list_ports.comports()]


class Ft950Cat:
    """CAT-interface specifiek voor de Yaesu FT-950."""

    POLL_INTERVAL = 0.5   # seconden

    def __init__(self, cfg=None):
        self._cfg   = cfg
        self._ser   = None
        self._lock  = threading.Lock()

        # Callbacks — alle worden aangeroepen vanuit de poll-thread.
        # Gebruik ALLEEN thread-safe operaties (queue.put, niet direct GUI).
        self.on_freq:       callable = None   # (vfo: str, hz: int)
        self.on_mode:       callable = None   # (mode: str)
        self.on_status:     callable = None   # (connected: bool)
        self.on_log:        callable = None   # (direction: str, data)
        self.on_state:      callable = None   # (state_dict)
        self.on_smeter:     callable = None   # (raw: int)
        self.on_tx_meters:  callable = None   # (dict: swr/alc/vdd/id/comp)
        self.on_tx_state:   callable = None   # (is_tx: bool) — elke cyclus via SWR
        self.on_freq_b:     callable = None   # (hz: int) VFO-B frequentie
        self.on_mode_b:     callable = None   # (mode: str) VFO-B modus
        self.on_agc:        callable = None   # (label: str)
        self.on_af_gain:    callable = None   # (val: int 0-255)
        self.on_rf_gain:    callable = None   # (val: int 0-255)
        self.on_squelch:    callable = None   # (val: int 0-255)
        self.on_busy:       callable = None   # (busy: bool)

        self._polling   = False
        self._poll_thread = None

    # ── Verbinding ────────────────────────────────────────────────────────────

    def connect(self) -> tuple[bool, str]:
        if not _serial_available:
            return False, "pyserial niet geïnstalleerd  →  pip install pyserial"
        cfg = self._cfg
        if not cfg or not getattr(cfg, "cat_port", "").strip():
            return False, "Geen seriële poort ingesteld"
        try:
            with self._lock:
                if self._ser:
                    try: self._ser.close()
                    except Exception: pass
                    self._ser = None

                parity_map  = {"Geen": serial.PARITY_NONE,
                               "Even": serial.PARITY_EVEN,
                               "Odd":  serial.PARITY_ODD}
                stop_map    = {"1": serial.STOPBITS_ONE,
                               "2": serial.STOPBITS_TWO}
                self._ser = serial.Serial(
                    port     = cfg.cat_port,
                    baudrate = int(cfg.cat_baud),
                    bytesize = int(cfg.cat_databits),
                    parity   = parity_map.get(cfg.cat_parity, serial.PARITY_NONE),
                    stopbits = stop_map.get(str(cfg.cat_stopbits), serial.STOPBITS_ONE),
                    timeout  = 0.5,
                    rtscts   = bool(cfg.cat_rtscts),
                    dsrdtr   = False,
                )
                if hasattr(cfg, "cat_dtr"):
                    self._ser.dtr = bool(cfg.cat_dtr)
                if hasattr(cfg, "cat_rts") and not cfg.cat_rtscts:
                    self._ser.rts = bool(cfg.cat_rts)

            self._log("INFO", f"Verbonden: {cfg.cat_port}  {cfg.cat_baud} baud")
            self._notify_status(True)
            self._start_poll()
            return True, ""
        except Exception as e:
            self._ser = None
            self._log("ERR", str(e))
            return False, str(e)

    def disconnect(self):
        self._stop_poll()
        with self._lock:
            if self._ser:
                try: self._ser.close()
                except Exception: pass
                self._ser = None
        self._log("INFO", "Verbinding verbroken")
        self._notify_status(False)

    @property
    def connected(self) -> bool:
        return self._ser is not None and self._ser.is_open

    # ── Poll-lus ──────────────────────────────────────────────────────────────

    def _start_poll(self):
        self._polling = True
        t = threading.Thread(target=self._poll_loop, daemon=True, name="ft950-poll")
        self._poll_thread = t
        t.start()

    def _stop_poll(self):
        self._polling = False

    def _poll_loop(self):
        """
        Achtergrond-poll lus.  Doet ALLE seriële reads; GUI nooit blokkeren.

        Cyclus-schema (bij poll_ms=500):
          Elke ronde:   IF;  → frequentie + modus
          Elke 2e ronde: SM;  → S-meter
          Elke 4e ronde: RM4/6/8/7/3; → TX-meters (SWR/ALC/VDD/ID/COMP)
          Elke 8e ronde: GT;  → AGC-instelling
        """
        fail_count = 0
        cycle      = 0

        while self._polling and self.connected:
            try:
                # ── IF; → frequentie + modus ──────────────────────────────────
                state = self._read_if()
                if state:
                    fail_count = 0
                    if self.on_freq:
                        try: self.on_freq("A", state["freq_hz"])
                        except Exception: pass
                    if self.on_mode:
                        try: self.on_mode(state["mode"])
                        except Exception: pass
                    if self.on_state:
                        try: self.on_state(state)
                        except Exception: pass
                else:
                    fail_count += 1
                    if fail_count >= 5:
                        self._notify_status(False)
                        break

                # ── TX-detectie via SWR (RM6) — elke ronde ─────────────────
                # Tijdens RX is SWR altijd 0; elke waarde > 0 = radio zendt
                swr_tx = self.read_meter(6)
                # SWR raw > 5 ≈ SWR > 1.04 — pakt elk realistisch antennesysteem
                is_tx_now = (swr_tx or 0) > 5
                if self.on_tx_state:
                    try: self.on_tx_state(is_tx_now)
                    except Exception: pass

                # ── SM; → S-meter (elke 2e ronde) ────────────────────────────
                if cycle % 2 == 0:
                    sm = self.read_smeter()
                    if sm is not None and self.on_smeter:
                        try: self.on_smeter(sm)
                        except Exception: pass
                    busy = self.read_busy()
                    if busy is not None and self.on_busy:
                        try: self.on_busy(busy)
                        except Exception: pass

                # ── VFO-B frequentie + modus (elke 3e ronde) ─────────────────
                if cycle % 3 == 0:
                    fb = self.get_freq_b()
                    if fb and self.on_freq_b:
                        try: self.on_freq_b(fb)
                        except Exception: pass
                    oi = self._read_oi()
                    if oi and self.on_mode_b:
                        try: self.on_mode_b(oi["mode"])
                        except Exception: pass

                # ── TX-meters (elke 4e ronde) ─────────────────────────────────
                if cycle % 4 == 0:
                    tx = self.read_all_tx_meters()
                    if self.on_tx_meters:
                        try: self.on_tx_meters(tx)
                        except Exception: pass

                # ── AGC (elke 8e ronde) ───────────────────────────────────────
                if cycle % 8 == 0:
                    agc = self.read_agc()
                    if agc and self.on_agc:
                        try: self.on_agc(agc)
                        except Exception: pass

                # ── AF gain / RF gain / SQL (elke 6e ronde) ──────────────────
                if cycle % 6 == 0:
                    af = self.get_af_gain()
                    if af is not None and self.on_af_gain:
                        try: self.on_af_gain(af)
                        except Exception: pass

                    rf = self.get_rf_gain()
                    if rf is not None and self.on_rf_gain:
                        try: self.on_rf_gain(rf)
                        except Exception: pass

                    sql = self._read_squelch()
                    if sql is not None and self.on_squelch:
                        try: self.on_squelch(sql)
                        except Exception: pass

            except Exception:
                break

            cycle += 1
            interval = getattr(self._cfg, "cat_poll_ms", 500) / 1000.0
            time.sleep(interval)

    # ── Lage-niveau commando's ─────────────────────────────────────────────────

    def _send_recv(self, cmd: str | bytes, timeout: float = 0.6) -> bytes:
        """Stuur commando, lees antwoord tot eerste ';'."""
        if not self.connected:
            return b""
        if isinstance(cmd, str):
            cmd = cmd.encode("ascii")
        with self._lock:
            try:
                self._ser.reset_input_buffer()
                self._ser.write(cmd)
                self._ser.flush()
                time.sleep(0.05)
                buf = b""
                deadline = time.monotonic() + timeout
                while time.monotonic() < deadline:
                    if self._ser.in_waiting:
                        buf += self._ser.read(self._ser.in_waiting)
                        if b";" in buf:
                            break
                    time.sleep(0.02)
                return buf
            except Exception:
                return b""

    def send_raw(self, cmd: str) -> bytes:
        """Stuur een willekeurig CAT-commando en geef het antwoord terug."""
        data = cmd.encode("ascii") if isinstance(cmd, str) else cmd
        self._log("TX", data)
        resp = self._send_recv(data)
        if resp:
            self._log("RX", resp)
        return resp

    # ── IF; status lezen ──────────────────────────────────────────────────────

    def _read_if(self) -> dict | None:
        """
        Parseer IF; antwoord (CAT ref. p.10):
          IF [3-mem][8-freq][+/-][4-clar][rx-clar][tx-clar][mode][vfo][ctcss][2-tone][shift] ;
        Geeft dict terug of None bij fout.
        """
        buf = self._send_recv("IF;", 0.7)
        if not buf:
            return None
        idx = buf.find(b"IF")
        if idx < 0:
            return None
        payload = buf[idx+2:]
        end = payload.find(b";")
        if end < 24:          # IF-payload is exact 24 tekens (CAT ref. p.10)
            return None
        p = payload[:end].decode("ascii", errors="replace")
        try:
            freq_str = p[3:11]
            if not freq_str.isdigit():
                return None
            clar_dir  = p[11]
            clar_off  = int(p[12:16])
            rx_clar   = p[16] == "1"
            tx_clar   = p[17] == "1"
            mode_code = p[18]
            vfo_mem   = p[19]
            ctcss     = p[20]
            shift_code = p[23] if len(p) > 23 else "0"
            return {
                "freq_hz":  int(freq_str),
                "mode":     CODE_MODES.get(mode_code, f"?{mode_code}"),
                "clar_dir": clar_dir,
                "clar_off": clar_off,
                "rx_clar":  rx_clar,
                "tx_clar":  tx_clar,
                "vfo_mem":  vfo_mem,
                "ctcss":    ctcss,
                "shift":    {"0": "S", "1": "+", "2": "-"}.get(shift_code, "S"),
            }
        except (IndexError, ValueError):
            return None

    def _read_oi(self) -> dict | None:
        """
        Parseer OI; (Other VFO info, CAT ref. p.12) — zelfde indeling als IF;.
        Geeft {'freq_hz', 'mode'} terug of None bij fout.
        """
        buf = self._send_recv("OI;", 0.5)
        if not buf:
            return None
        idx = buf.find(b"OI")
        if idx < 0:
            return None
        payload = buf[idx+2:]
        end = payload.find(b";")
        if end < 24:
            return None
        p = payload[:end].decode("ascii", errors="replace")
        try:
            freq_str  = p[3:11]
            mode_code = p[18]
            return {
                "freq_hz": int(freq_str) if freq_str.isdigit() else None,
                "mode":    CODE_MODES.get(mode_code, f"?{mode_code}"),
            }
        except (IndexError, ValueError):
            return None

    # ── Frequentie ────────────────────────────────────────────────────────────

    def get_freq_a(self) -> int | None:
        buf = self._send_recv("FA;")
        idx = buf.find(b"FA")
        if idx < 0: return None
        chunk = buf[idx+2:]
        end = chunk.find(b";")
        if end < 7: return None
        d = chunk[:end]
        return int(d) if d.isdigit() else None

    def get_freq_b(self) -> int | None:
        buf = self._send_recv("FB;")
        idx = buf.find(b"FB")
        if idx < 0: return None
        chunk = buf[idx+2:]
        end = chunk.find(b";")
        if end < 7: return None
        d = chunk[:end]
        return int(d) if d.isdigit() else None

    def set_freq_a(self, hz: int) -> bool:
        cmd = f"FA{hz:08d};"
        self._log("TX", cmd.encode())
        buf = self._send_recv(cmd)
        if buf: self._log("RX", buf)
        return b"?" not in buf

    def set_freq_b(self, hz: int) -> bool:
        cmd = f"FB{hz:08d};"
        self._log("TX", cmd.encode())
        buf = self._send_recv(cmd)
        if buf: self._log("RX", buf)
        return b"?" not in buf

    # ── Modus ─────────────────────────────────────────────────────────────────

    def get_mode(self) -> str | None:
        buf = self._send_recv("MD0;")
        idx = buf.find(b"MD")
        if idx < 0: return None
        chunk = buf[idx+2:]
        end = chunk.find(b";")
        if end < 1: return None
        code = chunk[:end].decode("ascii", errors="replace").lstrip("0")
        return CODE_MODES.get(code)

    def set_mode(self, mode: str) -> bool:
        code = MODE_CODES.get(mode.upper())
        if not code: return False
        cmd = f"MD0{code};"
        self._log("TX", cmd.encode())
        buf = self._send_recv(cmd)
        if buf: self._log("RX", buf)
        return b"?" not in buf

    # ── Vermogen ──────────────────────────────────────────────────────────────

    def get_power(self) -> int | None:
        buf = self._send_recv("PC;")
        idx = buf.find(b"PC")
        if idx < 0: return None
        chunk = buf[idx+2:]
        end = chunk.find(b";")
        if end < 2: return None
        d = chunk[:end]
        return int(d) if d.isdigit() else None

    def set_power(self, pct: int) -> bool:
        pct = max(5, min(100, pct))
        cmd = f"PC{pct:03d};"
        self._log("TX", cmd.encode())
        buf = self._send_recv(cmd)
        return b"?" not in buf

    # ── AF/RF gain ────────────────────────────────────────────────────────────

    def set_af_gain(self, val: int) -> bool:
        cmd = f"AG0{val:03d};"
        buf = self._send_recv(cmd)
        return b"?" not in buf

    def get_af_gain(self) -> int | None:
        buf = self._send_recv("AG0;")
        idx = buf.find(b"AG")
        if idx < 0: return None
        d = buf[idx+3:idx+6]
        return int(d) if d.isdigit() else None

    def set_rf_gain(self, val: int) -> bool:
        cmd = f"RG0{val:03d};"
        buf = self._send_recv(cmd)
        return b"?" not in buf

    def get_rf_gain(self) -> int | None:
        buf = self._send_recv("RG0;")
        idx = buf.find(b"RG")
        if idx < 0: return None
        d = buf[idx+3:idx+6]
        return int(d) if d.isdigit() else None

    def set_squelch(self, val: int) -> bool:
        """Squelch instellen (SQ-commando, CAT ref. p.15), waarde 0-255."""
        cmd = f"SQ0{val:03d};"
        buf = self._send_recv(cmd)
        return b"?" not in buf

    def _read_squelch(self) -> int | None:
        """Squelch-waarde lezen (SQ0;)."""
        buf = self._send_recv("SQ0;", 0.4)
        idx = buf.find(b"SQ")
        if idx < 0: return None
        d = buf[idx+3:idx+6]
        return int(d) if d.isdigit() else None

    # ── Attenuator / Preamp ───────────────────────────────────────────────────

    def set_att(self, level: int) -> bool:
        """level: 0=off, 1=6dB, 2=12dB, 3=18dB"""
        cmd = f"RA0{level};"
        buf = self._send_recv(cmd)
        return b"?" not in buf

    def get_att(self) -> int | None:
        buf = self._send_recv("RA0;")
        idx = buf.find(b"RA")
        if idx < 0: return None
        d = buf[idx+3:idx+4]
        return int(d) if d.isdigit() else None

    def set_ipo(self, mode: int) -> bool:
        """mode: 0=IPO(bypass), 1=AMP1, 2=AMP2"""
        cmd = f"PA0{mode};"
        buf = self._send_recv(cmd)
        return b"?" not in buf

    def get_ipo(self) -> int | None:
        buf = self._send_recv("PA0;")
        idx = buf.find(b"PA")
        if idx < 0: return None
        d = buf[idx+3:idx+4]
        return int(d) if d.isdigit() else None

    # ── Noise blanker / Noise reduction ───────────────────────────────────────

    def set_nb(self, mode: int) -> bool:
        """mode: 0=off, 1=narrow, 2=wide"""
        cmd = f"NB0{mode};"
        buf = self._send_recv(cmd)
        return b"?" not in buf

    def set_nr(self, on: bool) -> bool:
        cmd = f"NR0{1 if on else 0};"
        buf = self._send_recv(cmd)
        return b"?" not in buf

    # ── Narrow filter ─────────────────────────────────────────────────────────

    def set_narrow(self, on: bool) -> bool:
        cmd = f"NA0{1 if on else 0};"
        buf = self._send_recv(cmd)
        return b"?" not in buf

    # ── PTT ───────────────────────────────────────────────────────────────────

    def set_ptt(self, on: bool) -> bool:
        cmd = f"MX{1 if on else 0};"
        buf = self._send_recv(cmd)
        return b"?" not in buf

    # ── Antenne-tuner ─────────────────────────────────────────────────────────

    def set_tuner(self, state: int) -> bool:
        """state: 0=off, 1=on, 2=tune"""
        cmd = f"AC00{state};"
        buf = self._send_recv(cmd)
        return b"?" not in buf

    # ── Clarifier ────────────────────────────────────────────────────────────

    def set_rx_clar(self, on: bool) -> bool:
        cmd = f"RT{1 if on else 0};"
        buf = self._send_recv(cmd)
        return b"?" not in buf

    def set_tx_clar(self, on: bool) -> bool:
        cmd = f"XT{1 if on else 0};"
        buf = self._send_recv(cmd)
        return b"?" not in buf

    def clar_clear(self) -> bool:
        buf = self._send_recv("RC;")
        return b"?" not in buf

    def clar_up(self, hz: int = 100) -> bool:
        cmd = f"RU{hz:04d};"
        buf = self._send_recv(cmd)
        return b"?" not in buf

    def clar_down(self, hz: int = 100) -> bool:
        cmd = f"RD{hz:04d};"
        buf = self._send_recv(cmd)
        return b"?" not in buf

    # ── Split / VFO ───────────────────────────────────────────────────────────

    def set_split(self, on: bool) -> bool:
        # FT-950: FT commando voor TX-VFO selectie
        cmd = f"FT{3 if on else 2};"
        buf = self._send_recv(cmd)
        return b"?" not in buf

    def vfo_a_to_b(self) -> bool:
        buf = self._send_recv("AB;")
        return b"?" not in buf

    def vfo_swap(self) -> bool:
        buf = self._send_recv("SV;")
        return b"?" not in buf

    # ── Memory ───────────────────────────────────────────────────────────────

    def get_memory(self, ch: int) -> dict | None:
        """Lees geheugenkanaal ch (0-99).  Zie CAT ref. p.11."""
        cmd = f"MR{ch:03d};"
        buf = self._send_recv(cmd, 0.8)
        idx = buf.find(b"MR")
        if idx < 0: return None
        payload = buf[idx+2:]
        end = payload.find(b";")
        if end < 24: return None   # MR-payload = 24 tekens (zelfde als IF;, CAT ref. p.11)
        p = payload[:end].decode("ascii", errors="replace")
        try:
            ch_n    = int(p[0:3])
            freq    = int(p[3:11])
            cdir    = p[11]
            coff    = int(p[12:16])
            rxcl    = p[16] == "1"
            txcl    = p[17] == "1"
            mode_c  = p[18]
            ctcss   = p[20]
            tone_n  = int(p[21:23]) if len(p) > 22 else 0
            shift_c = p[23] if len(p) > 23 else "0"
            return {
                "ch":    ch_n,
                "freq":  freq,
                "mode":  CODE_MODES.get(mode_c, f"?{mode_c}"),
                "clar_dir": cdir,
                "clar_off": coff,
                "rx_clar":  rxcl,
                "tx_clar":  txcl,
                "ctcss":    ctcss,
                "tone":     tone_n,
                "shift":    {"0": "S", "1": "+", "2": "-"}.get(shift_c, "S"),
            }
        except (IndexError, ValueError):
            return None

    def set_memory(self, ch: int, freq_hz: int, mode: str,
                   shift: str = "S", ctcss: str = "0", tone: int = 0) -> bool:
        """Schrijf naar geheugenkanaal.  Zie CAT ref. p.12."""
        mode_c = MODE_CODES.get(mode.upper(), "2")
        shift_c = {"S": "0", "+": "1", "-": "2"}.get(shift, "0")
        tone_s  = f"{tone:02d}"
        # MW-formaat (CAT ref. p.12): ch(3) + freq(8) + clar(5) + rx(1) + tx(1)
        #   + mode(1) + vfo(1) + ctcss(1) + tone(2) + shift(1) = 24 tekens
        cmd = (f"MW{ch:03d}{freq_hz:08d}+0000"   # clar = "+0000" = 5 tekens
               f"00{mode_c}0{ctcss}{tone_s}{shift_c};")
        buf = self._send_recv(cmd)
        return b"?" not in buf

    def recall_memory(self, ch: int) -> bool:
        cmd = f"MC{ch:03d};"
        buf = self._send_recv(cmd)
        return b"?" not in buf

    # ── Identificatie ─────────────────────────────────────────────────────────

    def identify(self) -> tuple[bool, str]:
        """Stuur ID; — FT-950 antwoordt ID0310;"""
        if not self.connected:
            ok, err = self.connect()
            if not ok:
                return False, err
        buf = self._send_recv("ID;", 0.8)
        self._log("TX", b"ID;")
        if buf:
            self._log("RX", buf)
        txt = buf.decode("ascii", errors="replace").strip()
        if txt.startswith("ID") and txt.endswith(";"):
            return True, txt[:-1]
        return False, f"Onverwacht antwoord: {txt!r}"

    # ── S-meter lezen ─────────────────────────────────────────────────────────

    def read_smeter(self) -> int | None:
        """Geeft ruwe S-meter waarde (0-255) terug."""
        buf = self._send_recv("SM0;")
        idx = buf.find(b"SM")
        if idx < 0: return None
        chunk = buf[idx+3:]
        end = chunk.find(b";")
        if end < 2: return None
        d = chunk[:end]
        return int(d) if d.isdigit() else None

    def read_busy(self) -> bool | None:
        """
        Lees squelch-open status via BY; commando (CAT ref. p.5).
        Geeft True als BUSY (signaal aanwezig), False als stil, None bij fout.
        """
        buf = self._send_recv("BY;", 0.3)
        idx = buf.find(b"BY")
        if idx < 0: return None
        d = buf[idx+2:idx+3]
        if d == b"1": return True
        if d == b"0": return False
        return None

    def read_meter(self, meter: int) -> int | None:
        """
        Lees één TX-meter via RM-commando (CAT ref. p.14).
          meter: 1=S  3=COMP  4=ALC  5=PO  6=SWR  7=ID  8=VDD
        Geeft ruwe waarde (0-255) of None.
        """
        cmd = f"RM{meter};"
        buf = self._send_recv(cmd, 0.4)
        idx = buf.find(b"RM")
        if idx < 0: return None
        chunk = buf[idx+3:]
        end = chunk.find(b";")
        if end < 2: return None
        d = chunk[:end]
        return int(d) if d.isdigit() else None

    def read_agc(self) -> str | None:
        """
        Lees huidige AGC-instelling (CAT ref. p.9).
        Geeft "OFF"/"FAST"/"MID"/"SLOW"/"AUTO" of None terug.
        """
        buf = self._send_recv("GT0;", 0.4)
        idx = buf.find(b"GT")
        if idx < 0: return None
        d = buf[idx+3:idx+4]
        return {"0":"OFF","1":"FAST","2":"MID","3":"SLOW","4":"AUTO",
                "5":"A-FAST","6":"A-MID","7":"A-SLOW"}.get(
                    d.decode("ascii","replace"), None)

    def set_agc(self, code: int) -> bool:
        """code: 0=off,1=fast,2=mid,3=slow,4=auto"""
        buf = self._send_recv(f"GT0{code};")
        return b"?" not in buf

    # ── IF-shift ─────────────────────────────────────────────────────────────

    def get_if_shift(self) -> int | None:
        """Geeft huidige IF-shift in Hz (-1000..+1000) of None."""
        buf = self._send_recv("IS0;", 0.4)
        idx = buf.find(b"IS")
        if idx < 0: return None
        chunk = buf[idx+3:]
        end = chunk.find(b";")
        if end < 4: return None
        try: return int(chunk[:end])
        except ValueError: return None

    def set_if_shift(self, hz: int) -> bool:
        """IF-shift in Hz (-1000..+1000)."""
        sign = "+" if hz >= 0 else "-"
        cmd  = f"IS0{sign}{abs(hz):04d};"
        buf  = self._send_recv(cmd)
        return b"?" not in buf

    # ── IF-breedte ────────────────────────────────────────────────────────────

    def set_if_width(self, code: int) -> bool:
        """Bandbreedtecode 0-20 (zie CAT ref. p.15-16)."""
        cmd = f"SH0{code:02d};"
        buf = self._send_recv(cmd)
        return b"?" not in buf

    def get_if_width(self) -> int | None:
        buf = self._send_recv("SH0;", 0.4)
        idx = buf.find(b"SH")
        if idx < 0: return None
        d = buf[idx+3:idx+5]
        try: return int(d)
        except ValueError: return None

    # ── Contour ───────────────────────────────────────────────────────────────

    def set_contour(self, on: bool, freq_code: int = 15) -> bool:
        """Contour aan/uit.  freq_code 01-30 = middenpositie."""
        if on:
            self._send_recv(f"CO00001;")         # on/off ON
            self._send_recv(f"CO01{freq_code:02d};")  # level
        else:
            self._send_recv(f"CO00000;")          # on/off OFF
        return True

    def get_contour(self) -> tuple[bool, int]:
        """Geeft (actief, freq_code) terug."""
        buf = self._send_recv("CO00;", 0.4)
        idx = buf.find(b"CO")
        if idx < 0: return False, 15
        chunk = buf[idx+4:]
        end   = chunk.find(b";")
        try:
            code = int(chunk[:end])
            return code > 0, 15
        except ValueError:
            return False, 15

    # ── Handmatig notch ───────────────────────────────────────────────────────

    def set_notch(self, on: bool, freq_hz: int = 1500) -> bool:
        """Handmatig notch-filter aan/uit."""
        if on:
            code = max(1, min(300, freq_hz // 10))
            self._send_recv(f"BP001{code:03d};")
        else:
            self._send_recv(f"BP001000;")
        return True

    def get_notch(self) -> tuple[bool, int]:
        buf = self._send_recv("BP00;", 0.4)
        idx = buf.find(b"BP")
        if idx < 0: return False, 150
        chunk = buf[idx+4:]
        end   = chunk.find(b";")
        try:
            code = int(chunk[:end])
            return code > 0, code * 10
        except ValueError:
            return False, 1500

    def read_all_tx_meters(self) -> dict:
        """
        Lees SWR, ALC, VDD, ID en COMP in één reeks RM-commando's.
        Geeft dict: {swr, alc, vdd, id, comp}  (waarden 0-255 of None).
        """
        return {
            "swr":  self.read_meter(6),
            "alc":  self.read_meter(4),
            "vdd":  self.read_meter(8),
            "id":   self.read_meter(7),
            "comp": self.read_meter(3),
        }

    # ── Hulpfuncties ─────────────────────────────────────────────────────────

    def _log(self, direction: str, data):
        if self.on_log:
            try: self.on_log(direction, data)
            except Exception: pass

    def _notify_status(self, connected: bool):
        if self.on_status:
            try: self.on_status(connected)
            except Exception: pass
