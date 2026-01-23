import os
import sys
import ctypes
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt
from main_gui import LimitsGatekeeperlGUI

try:
    myappid = u'mycompany.limitsgatekeeper.v1'
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except Exception:
    pass

if __name__ == "__main__":
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
    app = QApplication(sys.argv)

    base_path = os.path.dirname(os.path.abspath(__file__))
    icon_path = os.path.join(base_path, "app_icon.ico")

    app_icon = QIcon(icon_path)
    app.setWindowIcon(app_icon)

    window = LimitsGatekeeperlGUI()
    window.show()
    sys.exit(app.exec_())
