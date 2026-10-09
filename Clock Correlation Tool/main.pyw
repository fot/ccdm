import sys
import ctypes
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from clock_app import ClockDriftApp
from misc import get_bundled_path

if __name__ == '__main__':

    if sys.platform == 'win32':
        myappid = 'clockcorrelationtool'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid) 

    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(str(get_bundled_path("app_icon.ico"))))
    window = ClockDriftApp()
    window.show()
    sys.exit(app.exec())
