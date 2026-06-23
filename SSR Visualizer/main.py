"Main Execution for App"

import sys
import os
from pathlib import Path

os.environ["PYTHONWARNINGS"]= "ignore"
os.environ["QTWEBENGINE_DISABLE_SANDBOX"]= "1"
os.environ["QT_LOGGING_RULES"]= "qt.webenginecontext.debug=false"

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from SSRWindow import SSRPointerWindow

app= QApplication(sys.argv + ['--log-level=3'])
app.setWindowIcon(QIcon(str(Path(__file__).resolve().parent / "ssr_visualizer_icon.ico")))

window= SSRPointerWindow()
window.show()

sys.exit(app.exec())
