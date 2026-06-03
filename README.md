# FT-950 Controller

Een Python-gebaseerde besturingsapplicatie voor de **Yaesu FT-950** HF/50 MHz transceiver, gebouwd met PySide6.

## Beschrijving

FT-950 Controller biedt een volledig grafische interface waarmee de radio via de CAT-interface (seriële poort) bestuurd kan worden. De lay-out is geïnspireerd op het frontpaneel van de echte FT-950.

### Mogelijkheden

- **Frequentie-afstemming** via klikbaar VFD-display (klik op een digit → selecteer stap, scrollwiel → afstemmen)
- **Modus-selectie** (LSB, USB, CW, AM, FM, RTTY/PKT)
- **Band-selectie** met directe frequentie-invoer via GEN-knop (keypad)
- **VFO-A / VFO-B** beheer, split-operatie, FAST/LOCK
- **DSP-filters**: IF Shift, IF Width, Contour, Notch (met sliders per functie)
- **Ontvanger**: ATT, IPO, R.FLT, NB, DNR, AF Gain, RF Gain, Squelch
- **Zender**: TX Power, MOX/PTT, MUTE met knipperend indicatie-lampje
- **S-meter** met kalibratie-dialoog en schaalverdeling (S1…S9…+60 dB)
- **TX-meters**: SWR, ALC, VDD, ID, COMP — allen met schaalverdeling
- **Frequentie-favorieten** (opslaan/laden/bewerken met alle radio-instellingen)
- **EIBI-kortegolflijst**: importeren vanuit lokaal bestand of direct van eibispace.de; klikken op een regel stelt de radio in
- **Radio-geheugenkanalen** (lezen/schrijven/opslaan naar JSON)
- **AGC-modus** zichtbaar op de knop, bijgewerkt vanuit de radio
- **CAT-monitor** met verbindingstest (ID;-commando)
- **UTC en EST-klok** in de statusbalk
- **Statusbadges** (TX, BUSY, NAR, SPLIT, NB, DNR, FAST, LOCK) in de statusbalk
- **S-meter kalibratie** per S-punt instelbaar
- **Weergave-instellingen**: lettergrootte band/mode-knoppen en VFD instelbaar
- Alle instellingen worden bewaard in JSON-configuratiebestanden

## Vereisten

- Python 3.10 of hoger
- PySide6 >= 6.4
- pyserial >= 3.5

Installeren:
```bash
pip install PySide6 pyserial
```

## Starten

```bash
cd FT950
python ft950_controller.py
```

## CAT-verbinding instellen

1. Sluit de FT-950 aan via een seriële kabel op de CAT-ingang (9-pin DB9)
2. Ga naar **Radio → Instellingen…**
3. Stel COM-poort, baudrate (standaard 4800 bps) en overige seriële parameters in
4. Klik **Verbind en test (ID;)** — de radio antwoordt met `ID0310;`
5. Klik **Opslaan**
6. Druk **F5** of klik de **⬤ Verbinden**-knop om te verbinden

## Projectstructuur

```
FT950/
├── ft950_controller.py       # startpunt
├── requirements.txt
├── ft950_config.json         # instellingen (aangemaakt bij eerste start)
├── ft950_memories.json       # frequentie-favorieten
├── ft950_channels.json       # radio-geheugenkanalen
├── ft950_eibi.json           # EIBI-kortegolflijst
└── ft950/
    ├── theme.py              # kleurthema
    ├── config.py             # configuratie-dataklassen + JSON-opslag
    ├── cat.py                # CAT-communicatie (FT-950 specifiek)
    ├── widgets.py            # VFD-display, S-meter, LED-knoppen, knob
    ├── display.py            # frequentie-display paneel
    ├── panels.py             # alle bedieningspanelen
    ├── dialogs.py            # dialogen (CAT, geheugen, EIBI, kalibratie)
    └── mainwindow.py         # hoofdvenster
```

## Licentie

MIT License — vrij te gebruiken en aan te passen.

## Auteur

Ontwikkeld voor gebruik met de Yaesu FT-950 HF/50 MHz transceiver.
