import sys
from PyQt6.QtWidgets import QApplication
from clock_app import ClockDriftApp

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ClockDriftApp()
    window.show()
    sys.exit(app.exec())
