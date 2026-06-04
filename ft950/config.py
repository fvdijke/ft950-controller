"""FT-950 Controller — configuratie (ft950_config.json) + frequentie-favorieten."""

import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime

import sys as _sys

# When running as a frozen onefile exe, user data must live next to sys.executable
_DATA_DIR = (os.path.dirname(_sys.executable)
             if getattr(_sys, "frozen", False)
             else os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

_CONFIG_FILE   = os.path.join(_DATA_DIR, "ft950_config.json")
_MEMORIES_FILE = os.path.join(_DATA_DIR, "ft950_memories.json")
_EIBI_FILE     = os.path.join(_DATA_DIR, "ft950_eibi.json")
_CHANNELS_FILE = os.path.join(_DATA_DIR, "ft950_channels.json")


@dataclass
class EibiRecord:
    """Eén EIBI-uitzendschema-record, aangevuld met radio-instellingen."""
    freq_hz:       int   = 7_000_000
    station:       str   = ""
    country:       str   = ""
    start:         str   = ""
    stop:          str   = ""
    language:      str   = ""
    target:        str   = ""
    # Radio-instellingen (bewaard per record)
    mode:          str   = "AM"
    af_gain:       int   = 60       # standaard volume 60
    sql:           int   = 0
    dsp_nar:       bool  = False
    dsp_width_idx: int   = 6        # 2.4 kHz
    notes:         str   = ""


def load_eibi_records() -> list:
    path = os.path.normpath(_EIBI_FILE)
    if not os.path.exists(path):
        return []
    try:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
        result = []
        for item in raw:
            e = EibiRecord()
            for k, v in item.items():
                if hasattr(e, k):
                    try:
                        setattr(e, k, type(getattr(e, k))(v))
                    except (TypeError, ValueError):
                        setattr(e, k, v)
            result.append(e)
        return result
    except Exception:
        return []


def save_eibi_records(records: list):
    path = os.path.normpath(_EIBI_FILE)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump([asdict(r) for r in records], f,
                      ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"EIBI opslaan mislukt: {e}")


@dataclass
class FreqEntry:
    """Eén opgeslagen frequentie-instelling met alle parameters."""

    name:           str   = "Nieuw"
    freq_hz:        int   = 14_000_000
    mode:           str   = "USB"
    band:           str   = "20m"
    notes:          str   = ""
    created:        str   = ""   # ISO-tijdstempel

    # ─ DSP-instellingen
    dsp_shift_on:   bool  = False
    dsp_shift_hz:   int   = 0
    dsp_width_on:   bool  = False
    dsp_width_idx:  int   = 6
    dsp_cont_on:    bool  = False
    dsp_cont_pos:   int   = 15
    dsp_notch_on:   bool  = False
    dsp_notch_hz:   int   = 1500
    dsp_nar:        bool  = False

    # ─ Ontvangerinstellingen
    att_idx:        int   = 0
    ipo_idx:        int   = 1
    rflt_idx:       int   = 0
    nb_idx:         int   = 0
    nr_on:          bool  = False
    af_gain:        int   = 180
    rf_gain:        int   = 255
    agc_idx:        int   = 4

    # ─ Zender
    tx_power:       int   = 100


def load_memories() -> list[FreqEntry]:
    """Laad frequentie-favorieten uit ft950_memories.json."""
    path = os.path.normpath(_MEMORIES_FILE)
    if not os.path.exists(path):
        return []
    try:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
        result = []
        for item in raw:
            e = FreqEntry()
            for k, v in item.items():
                if hasattr(e, k):
                    try:
                        setattr(e, k, type(getattr(e, k))(v))
                    except (TypeError, ValueError):
                        setattr(e, k, v)
            result.append(e)
        return result
    except Exception:
        return []


def load_channels() -> dict:
    """Laad opgeslagen radio-geheugenkanalen {ch_nr: {freq, mode, shift, tone}}."""
    path = os.path.normpath(_CHANNELS_FILE)
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
        return {int(k): v for k, v in raw.items()}
    except Exception:
        return {}


def save_channels(channels: dict):
    """Sla radio-geheugenkanalen op naar ft950_channels.json."""
    path = os.path.normpath(_CHANNELS_FILE)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({str(k): v for k, v in channels.items()},
                      f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Kanalen opslaan mislukt: {e}")


def save_memories(entries: list[FreqEntry]):
    """Sla frequentie-favorieten op naar ft950_memories.json."""
    path = os.path.normpath(_MEMORIES_FILE)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump([asdict(e) for e in entries], f,
                      ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Favorieten opslaan mislukt: {e}")


@dataclass
class Ft950Config:
    # ── CAT / serieel ─────────────────────────────────────────────────────────
    cat_port:       str  = ""
    cat_baud:       int  = 4800
    cat_databits:   int  = 8
    cat_parity:     str  = "Geen"
    cat_stopbits:   str  = "1"
    cat_rtscts:     bool = False
    cat_dtr:        bool = False
    cat_rts:        bool = False
    cat_poll_ms:    int  = 500     # poll-interval frequentie (ms)

    # ── Laatste status (herinnerd bij opnieuw openen) ─────────────────────────
    last_freq_hz:   int  = 14_000_000
    last_mode:      str  = "USB"
    last_vfob_hz:   int  = 14_100_000
    last_band:      str  = "20m"

    # ── Venstergrootte ────────────────────────────────────────────────────────
    win_x:  int = 100
    win_y:  int = 100
    win_w:  int = 1680
    win_h:  int = 540

    # ── DSP-instellingen ─────────────────────────────────────────────────────
    dsp_shift_on:   bool = False
    dsp_shift_hz:   int  = 0
    dsp_width_on:   bool = False
    dsp_width_idx:  int  = 6        # 2.4 kHz default
    dsp_cont_on:    bool = False
    dsp_cont_pos:   int  = 15
    dsp_notch_on:   bool = False
    dsp_notch_hz:   int  = 1500
    dsp_nar:        bool = False

    # ── Ontvangersinstellingen ────────────────────────────────────────────────
    att_idx:        int  = 0        # 0=off, 1=−6dB, 2=−12dB, 3=−18dB
    ipo_idx:        int  = 1        # 0=IPO ON, 1=AMP1, 2=AMP2
    rflt_idx:       int  = 0        # 0=AUTO, 1=3kHz, 2=6kHz, 3=15kHz
    nb_idx:         int  = 0        # 0=off, 1=narrow, 2=wide
    nr_on:          bool = False
    af_gain:        int  = 180
    rf_gain:        int  = 255
    agc_idx:        int  = 4        # 4=AUTO

    # ── Zender ───────────────────────────────────────────────────────────────
    tx_power:       int  = 100
    mic_gain:       int  = 128
    cw_speed:       int  = 20

    # ── VFO / afstemmen ───────────────────────────────────────────────────────
    vfd_step_char:  int  = 5        # geselecteerde digit (5 = 1 kHz)
    split_on:       bool = False
    fast_on:        bool = False
    ant_sel:        int  = 1        # 1 of 2

    # ── S-meter kalibratie ────────────────────────────────────────────────────
    # 15 ruwe waarden (0-255): S1-S9 + +10/+20/+30/+40/+50/+60 dB
    smeter_cal: list = field(default_factory=lambda: [
        18, 36, 54, 72, 90, 108, 126, 144, 162,   # S1-S9
        175, 189, 202, 216, 229, 243               # +10/+20/+30/+40/+50/+60
    ])

    # ── Weergave-lettergroottes ───────────────────────────────────────────────────
    band_btn_font:  int  = 7        # pt  band/mode knoppen in het display
    vfd_font:       int  = 34       # pt  grote frequentie-aanduiding
    vfob_font:      int  = 14       # pt  VFO-B display
    clar_font:      int  = 14       # pt  CLAR display
    vfd_font_name:  str  = "Seven Segment"  # font-familie voor VFD-frequentieweergave
    vfd_font_style: str  = "Bold"          # "Normal" | "Bold" | "Italic" | "Bold Italic"

    # ── Taal ─────────────────────────────────────────────────────────────────
    ui_language:    str  = "en"  # "nl" of "en"


def load_config() -> Ft950Config:
    cfg = Ft950Config()
    try:
        path = os.path.normpath(_CONFIG_FILE)
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            for k, v in data.items():
                if hasattr(cfg, k):
                    try:
                        setattr(cfg, k, type(getattr(cfg, k))(v))
                    except (TypeError, ValueError):
                        setattr(cfg, k, v)
    except Exception:
        pass

    # Migratie: 8-punts kalibratie (oud) → 15-punts via interpolatie
    if len(cfg.smeter_cal) == 8:
        o = cfg.smeter_cal
        cfg.smeter_cal = [
            o[0], (o[0]+o[1])//2, o[1], (o[1]+o[2])//2, o[2],   # S1-S5
            (o[2]+o[3])//2, o[3], (o[3]+o[4])//2, o[4],          # S6-S9
            (o[4]+o[5])//2, o[5], (o[5]+o[6])//2,                 # +10/+20/+30
            o[6], (o[6]+o[7])//2, o[7],                           # +40/+50/+60
        ]
    elif len(cfg.smeter_cal) != 15:
        cfg.smeter_cal = Ft950Config.__dataclass_fields__['smeter_cal'].default_factory()

    return cfg


def save_config(cfg: Ft950Config):
    try:
        path = os.path.normpath(_CONFIG_FILE)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(cfg), f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Config opslaan mislukt: {e}")
