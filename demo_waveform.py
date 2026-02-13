"""Demo du widget waveform — lance le widget pendant 5 secondes.

Usage:
    python demo_waveform.py

Necessite un serveur X/Wayland (pas headless).
Sur WSL : installer un serveur X comme VcXsrv ou utiliser WSLg.
"""

import sys
import time

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication


def main():
    app = QApplication.instance() or QApplication(sys.argv)

    # Mock capture avec amplitude simulee
    class FakeCapture:
        def __init__(self):
            self._amp = 0.0
            self._t = 0

        @property
        def current_amplitude(self):
            import math
            self._t += 1
            # Simule une amplitude oscillante
            return abs(math.sin(self._t * 0.1)) * 0.3

    from src.gui.waveform_widget import WaveformWidget

    capture = FakeCapture()
    widget = WaveformWidget(capture=capture)

    print("=== Demo Waveform Widget ===")
    print("1. Affichage mode RECORDING (3s)...")
    widget.show_recording()

    def switch_to_processing():
        print("2. Affichage mode PROCESSING (2s)...")
        widget.show_processing()

    def hide_and_quit():
        print("3. Widget cache. Demo terminee !")
        widget.hide_widget()
        app.quit()

    QTimer.singleShot(3000, switch_to_processing)
    QTimer.singleShot(5000, hide_and_quit)

    app.exec()


if __name__ == "__main__":
    main()
