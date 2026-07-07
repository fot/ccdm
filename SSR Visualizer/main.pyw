"Main Execution for App"

import sys
import platform
from pathlib import Path
from SSRWindow import SSRPointerWindow


if platform.system() == "Linux":
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QIcon
    from PySide6.QtCore import Qt
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_DontCreateNativeWidgetSiblings)
else:
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtGui import QIcon

def main():
    app= QApplication(sys.argv + ['--log-level=3'])
    app.setWindowIcon(QIcon(str(Path(__file__).resolve().parent / "ssr_visualizer_icon.ico")))
    window= SSRPointerWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
