"Main Execution for App"

import sys
from pathlib import Path
from SSRWindow import SSRPointerWindow


from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt
QApplication.setAttribute(Qt.ApplicationAttribute.AA_DontCreateNativeWidgetSiblings)


def main():
    app= QApplication(sys.argv + ['--log-level=3'])
    app.setWindowIcon(QIcon(str(Path(__file__).resolve().parent / "ssr_visualizer_icon.ico")))
    window= SSRPointerWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
