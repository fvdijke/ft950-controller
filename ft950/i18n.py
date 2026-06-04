"""
FT-950 Controller — internationalisation (i18n)

Usage:
    from .i18n import tr
    label = tr("Verbinden")   # → "Connect" in English, "Verbinden" in Dutch

Language is set once at app start via set_language().
Change language → save to config → restart app.
"""

_LANG: str = "en"   # active language (default English)

# Dutch → English translation table
_EN: dict[str, str] = {
    # ── Menus ────────────────────────────────────────────────────────────────
    "Radio":               "Radio",
    "Geheugen":            "Memory",
    "Weergave":            "View",
    "Help":                "Help",
    "Instellingen…":       "Settings…",
    "Verbinden":           "Connect",
    "Verbreken":           "Disconnect",
    "Afsluiten":           "Exit",
    "Geheugenkanalen…":    "Memory channels…",
    "Frequentie favorieten…": "Frequency favourites…",
    "S-meter kalibratie…": "S-meter calibration…",
    "Weergave instellingen…": "Display settings…",
    "Lettergroottes…":     "Font sizes…",
    "Taal / Language":     "Taal / Language",
    "Nederlands":          "Nederlands",
    "English":             "English",
    "Over FT-950 Controller…": "About FT-950 Controller…",

    # ── Kolom-headers ─────────────────────────────────────────────────────────
    "BEDIENING":           "CONTROLS",
    "DSP FILTER":          "DSP FILTER",
    "DISPLAY":             "DISPLAY",
    "VFO":                 "VFO",
    "ONTVANGER":           "RECEIVER",
    "ZENDER":              "TRANSMITTER",

    # ── Verbinden / status ───────────────────────────────────────────────────
    "⬤  Verbinden":        "⬤  Connect",
    "⬤  Verbreken":        "⬤  Disconnect",
    "⬤  Verbonden":        "⬤  Connected",
    "⬤  Niet verbonden":   "⬤  Not connected",

    # ── Knoppen BEDIENING ─────────────────────────────────────────────────────
    "ANT 1":               "ANT 1",
    "ANT 2":               "ANT 2",
    "MOX":                 "MOX",
    "TUNE":                "TUNE",
    "VOX":                 "VOX",
    "🔇  MUTE":            "🔇  MUTE",
    "🔴  MUTE":            "🔴  MUTE",
    "⚫  MUTE":            "⚫  MUTE",
    "MONI":                "MONI",
    "PROC":                "PROC",
    "SPOT":                "SPOT",
    "BK-IN":               "BK-IN",
    "KEYER":               "KEYER",
    "AGC":                 "AGC",
    "AUTO":                "AUTO",
    "MIC GAIN":            "MIC GAIN",
    "SPEED (WPM)":         "SPEED (WPM)",
    "ALC":                 "ALC",
    "SWR":                 "SWR",

    # ── DSP panel ─────────────────────────────────────────────────────────────
    "IF SHIFT":            "IF SHIFT",
    "IF WIDTH":            "IF WIDTH",
    "CONTOUR positie (1-30)": "CONTOUR position (1-30)",
    "NOTCH frequentie (Hz)":  "NOTCH frequency (Hz)",
    "NAR":                 "NAR",
    "µTUNE":               "µTUNE",
    "CLEAR":               "CLEAR",
    "SHIFT":               "SHIFT",
    "WIDTH":               "WIDTH",
    "CONT":                "CONT",
    "NOTCH":               "NOTCH",

    # ── Ontvanger ─────────────────────────────────────────────────────────────
    "ATT":                 "ATT",
    "ATT OFF":             "ATT OFF",
    "IPO":                 "IPO",
    "AMP1":                "AMP1",
    "R.FLT":               "R.FLT",
    "NB":                  "NB",
    "DNR":                 "DNR",
    "AF GAIN":             "AF GAIN",
    "RF GAIN":             "RF GAIN",
    "SQL":                 "SQL",

    # ── VFO panel ─────────────────────────────────────────────────────────────
    "SPLIT":               "SPLIT",
    "TXW":                 "TXW",
    "FAST":                "FAST",
    "LOCK":                "LOCK",
    "QMB STO":             "QMB STO",
    "QMB RCL":             "QMB RCL",
    "VFO-A TX":            "VFO-A TX",
    "VFO-B TX":            "VFO-B TX",
    "A→B":                 "A→B",
    "A=B":                 "A=B",
    "V/M":                 "V/M",
    "M→A":                 "M→A",
    "A→M":                 "A→M",
    "RX CLAR":             "RX CLAR",
    "TX CLAR":             "TX CLAR",
    "Stap:":               "Step:",
    "AFSTEMSTAP":          "TUNING STEP",

    # ── Zender ────────────────────────────────────────────────────────────────
    "TX POWER":            "TX POWER",
    "TX METERS":           "TX METERS",
    "ON AIR":              "ON AIR",
    "5 W":                 "5 W",
    "100 W":               "100 W",

    # ── Dialogen algemeen ────────────────────────────────────────────────────
    "Opslaan":             "Save",
    "Annuleren":           "Cancel",
    "Sluiten":             "Close",
    "Bewaren":             "Save",
    "Wissen":              "Clear",
    "Laden":               "Load",
    "OK":                  "OK",
    "Toepassen":           "Apply",

    # ── Instellingen dialoog ──────────────────────────────────────────────────
    "CAT Instellingen":    "CAT Settings",
    "Seriële poort:":      "Serial port:",
    "Baudrate:":           "Baud rate:",
    "Databits:":           "Data bits:",
    "Stopbits:":           "Stop bits:",
    "Pariteit:":           "Parity:",
    "Poll interval (ms)":  "Poll interval (ms)",
    "Verbind en test (ID;)": "Connect & test (ID;)",
    "Verbonden":           "Connected",
    "Niet verbonden":      "Not connected",

    # ── Geheugen dialoog ─────────────────────────────────────────────────────
    "Frequentie favorieten": "Frequency favourites",
    "Favorieten":          "Favourites",
    "EIBI":                "EIBI",
    "Naam:":               "Name:",
    "Notities:":           "Notes:",
    "Modus:":              "Mode:",
    "Volume:":             "Volume:",
    "Squelch:":            "Squelch:",
    "Smal filter:":        "Narrow filter:",
    "Breedte:":            "Width:",
    "💾 Bewaren":          "💾 Save",
    "➕ Toevoegen":        "➕ Add",
    "🗑 Verwijderen":      "🗑 Delete",
    "▲ Omhoog":            "▲ Up",
    "▼ Omlaag":            "▼ Down",
    "Instellingen geselecteerde regel": "Selected row settings",
    "Kanaal":              "Channel",
    "Freq (Hz):":          "Freq (Hz):",
    "💾 Opslaan":          "💾 Save",

    # ── EIBI dialoog ─────────────────────────────────────────────────────────
    "📥 Importeer EIBI…":  "📥 Import EIBI…",
    "✕ Alles wissen":      "✕ Clear all",
    "Zoeken:":             "Search:",
    "station, land of frequentie…": "station, country or frequency…",
    "0 records":           "0 records",
    "Importeren…":         "Importing…",

    # ── S-meter kalibratie ───────────────────────────────────────────────────
    "S-meter kalibratie":  "S-meter calibration",
    "S-punt":              "S-point",
    "Actueel":             "Current",
    "← Actueel":           "← Current",
    "Herstel standaard":   "Reset to default",

    # ── Display instellingen ──────────────────────────────────────────────────
    "Lettergrootte band/mode knoppen:": "Band/mode button font size:",
    "Lettergrootte VFD:":  "VFD font size:",

    # ── Diversen ─────────────────────────────────────────────────────────────
    "Verbinden (F5)":         "Connect (F5)",
    "CAT Monitor…":           "CAT Monitor…",
    "Frequentie-favorieten…": "Frequency favourites…",
    "Radio geheugenkanalen…": "Radio memory channels…",
    "Lettergrootte display…": "Display font size…",
    "S-meter kalibreren…":    "S-meter calibration…",
    "AFSTEMSTAP":             "TUNING STEP",
    "Stap:":                  "Step:",
    "Frequentie invoeren":    "Enter frequency",
    "Frequentie favorieten":  "Frequency favourites",
    "CAT Instellingen":       "CAT Settings",
    "Frequentie-poll interval (ms):": "Frequency poll interval (ms):",
    "⬤  Verbinden":           "⬤  Connect",
    "⬤  Verbreken":           "⬤  Disconnect",
    "Geheugen — FT-950":      "Memory — FT-950",
    "Zoeken:":                "Search:",
    "Zoeken (station / freq):" : "Search (station / freq):",
    "Importeren…":            "Importing…",
    "S-meter kalibratie":     "S-meter calibration",

    # ── Status / verbinding ───────────────────────────────────────────────────
    "⬤  Verbonden":            "⬤  Connected",
    "⬤  Niet verbonden":       "⬤  Not connected",
    "Verbinding mislukt":       "Connection failed",
    "Niet verbonden":           "Not connected",
    "Niet verbonden met radio.": "Not connected to radio.",
    "Niet verbonden.":          "Not connected.",
    "Niet verbonden met radio — kanaal NIET naar radio gestuurd.":
        "Not connected to radio — channel NOT sent to radio.",

    # ── Dialoog labels en knoppen ─────────────────────────────────────────────
    "Lettergrootte display":    "Display font sizes",
    "VFO-A  /  Band & mode knoppen": "VFO-A  /  Band & mode buttons",
    "Band/mode knoppen:":       "Band/mode buttons:",
    "Frequentie (VFD):":        "Frequency (VFD):",
    "VFO-B:":                   "VFO-B:",
    "CLAR:":                    "CLAR:",
    "Annuleer":                 "Cancel",
    "Annuleer…":                "Cancel…",
    "Oproepen op radio":        "Recall on radio",
    "💾 Bewaren":               "💾 Save",
    "💾 Opslaan":               "💾 Save",
    "Verbinden en test (ID;)":  "Connect and test (ID;)",
    "Ongeldige frequentie.":    "Invalid frequency.",

    # ── Status berichten ──────────────────────────────────────────────────────
    "Download mislukt  ✗":      "Download failed  ✗",
    "Zoeken naar actueel bestand…": "Searching for current file…",

    # ── Help / Over ───────────────────────────────────────────────────────────
    "FT-950 Controller":   "FT-950 Controller",
    "Versie":              "Version",
    "Yaesu FT-950 CAT controller": "Yaesu FT-950 CAT controller",

    # ── Statusbalk ────────────────────────────────────────────────────────────
    "Taal gewijzigd":      "Language changed",
    "Herstart de applicatie om de taal te wijzigen.":
        "Restart the application to change the language.",
}


def set_language(lang: str) -> None:
    """Set active language: 'nl' or 'en'."""
    global _LANG
    _LANG = lang if lang in ("nl", "en") else "nl"


def get_language() -> str:
    return _LANG


def tr(text: str) -> str:
    """Translate text. Unknown keys are returned unchanged."""
    if _LANG == "en":
        return _EN.get(text, text)
    return text
