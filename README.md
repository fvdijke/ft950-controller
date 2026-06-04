<img width="1998" height="642" alt="Yaesu FT-950 Controller" src="https://github.com/user-attachments/assets/d98874fd-c5be-43dc-893d-91fc08ad5d18" />

# FT-950 Controller

A Python-based control application for the **Yaesu FT-950** HF/50 MHz transceiver, built with PySide6.

## Description

FT-950 Controller provides a full graphical interface for controlling the radio via the CAT interface (serial port). The layout is inspired by the front panel of the real FT-950.

### Features

- **Frequency tuning** via clickable VFD display — hover over a digit to select it, then use the scroll wheel to tune
- **Mode selection** (LSB, USB, CW, AM, FM, RTTY/PKT)
- **Band selection** with direct frequency entry via GEN button (keypad)
- **VFO-A / VFO-B** management — both tunable via scroll wheel, split operation, FAST/LOCK
- **DSP filters**: IF Shift, IF Width, Contour, Notch (sliders per function)
- **Receiver**: ATT, IPO, R.FLT, NB, DNR, AF Gain, RF Gain, Squelch
- **Transmitter**: TX Power, MOX/PTT, ON AIR button (turns red while transmitting)
- **S-meter** with calibration dialog and scale (S1…S9…+60 dB)
- **TX meters**: SWR, ALC, VDD, ID, COMP — all with scale markings
- **TX detection** from hardware PTT via SWR meter (RM6) — ON AIR button and TX badge reflect actual radio TX state
- **Frequency favourites** (save/load/edit with all radio settings per entry)
- **EIBI shortwave list**: import from local file or directly from eibispace.de; click a row to tune the radio
- **Radio memory channels** (read/write/save to JSON)
- **AGC mode** shown on button, updated from radio
- **CAT monitor** with connection test (ID; command)
- **UTC and CEST clock** in the status bar
- **Status badges** (TX, BUSY, NAR, SPLIT, NB, DNR, FAST, LOCK) in the status bar — TX badge blinks while transmitting
- **S-meter calibration** — configurable raw value per S-point
- **Display settings**: font size for band/mode buttons, VFD, VFO-B and CLAR individually adjustable
- **Language selection**: English (default) and Dutch — switchable via View → Language, persisted across restarts
- All settings are stored in JSON configuration files

## Requirements

- Python 3.10 or higher
- PySide6 >= 6.4
- pyserial >= 3.5

Install:
```bash
pip install PySide6 pyserial
```

## Getting Started

```bash
cd FT950
python ft950_controller.py
```

## CAT Connection Setup

1. Connect the FT-950 via a serial cable to the CAT port (9-pin DB9)
2. Go to **Radio → Settings…**
3. Set the COM port, baud rate (default 4800 bps) and other serial parameters
4. Click **Connect and test (ID;)** — the radio responds with `ID0310;`
5. Click **Save**
6. Press **F5** or click the **⬤ Connect** button to connect

## Project Structure

```
FT950/
├── ft950_controller.py       # entry point
├── requirements.txt
├── ft950_config.json         # settings (created on first run)
├── ft950_memories.json       # frequency favourites
├── ft950_channels.json       # radio memory channels
├── ft950_eibi.json           # EIBI shortwave schedule
└── ft950/
    ├── i18n.py               # internationalisation (NL/EN)
    ├── theme.py              # colour theme
    ├── config.py             # config dataclasses + JSON storage
    ├── cat.py                # CAT communication (FT-950 specific)
    ├── widgets.py            # VFD display, S-meter, LED buttons
    ├── display.py            # frequency display panel
    ├── panels.py             # all control panels
    ├── dialogs.py            # dialogs (CAT, memory, EIBI, calibration)
    └── mainwindow.py         # main window
```

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| F5  | Connect / Disconnect |

## Notes

- TX detection via hardware PTT uses the SWR meter (CAT command `RM6;`). The radio must be connected and transmitting into an antenna for the GUI to reflect TX state.
- The EIBI import auto-detects the current schedule file URL from eibispace.de.
- All favourites, EIBI notes and channel data are stored locally in JSON files.

## License

MIT License — free to use and modify.

## Author

Developed for use with the Yaesu FT-950 HF/50 MHz transceiver.
