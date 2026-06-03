"""
FT-950 Controller — startpunt

Gebruik:
    python ft950_controller.py

Vereiste pakketten:
    pip install PySide6 pyserial
"""

import sys
import os

# Zorg dat de projectmap in het pad staat
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from PySide6.QtGui     import QFont, QPalette, QColor
from PySide6.QtCore    import Qt

from ft950.config     import load_config
from ft950.mainwindow import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("FT-950 Controller")
    app.setOrganizationName("PA3FKV")

    # Uniform donker grijs kleurpalet
    DARK = "#1E1E1E"
    palette = QPalette()
    palette.setColor(QPalette.Window,          QColor(DARK))
    palette.setColor(QPalette.WindowText,      QColor("#DCDCDC"))
    palette.setColor(QPalette.Base,            QColor(DARK))
    palette.setColor(QPalette.AlternateBase,   QColor("#2A2A2A"))
    palette.setColor(QPalette.Text,            QColor("#DCDCDC"))
    palette.setColor(QPalette.Button,          QColor("#2A2A2A"))
    palette.setColor(QPalette.ButtonText,      QColor("#DCDCDC"))
    palette.setColor(QPalette.Highlight,       QColor("#C8A430"))
    palette.setColor(QPalette.HighlightedText, QColor("#000000"))
    app.setPalette(palette)

    # Standaard lettertype
    app.setFont(QFont("Segoe UI", 8))

    cfg = load_config()
    win = MainWindow(cfg)
    win.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
