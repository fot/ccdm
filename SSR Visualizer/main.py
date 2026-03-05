"Main Execution for App"

import sys
import os

os.environ["PYTHONWARNINGS"] = "ignore"
os.environ["QTWEBENGINE_DISABLE_SANDBOX"] = "1"
os.environ["QT_LOGGING_RULES"] = "qt.webenginecontext.debug=false"

from PyQt6.QtWidgets import QApplication
from SSRWindow import SSRPointerWindow

app= QApplication(sys.argv + ['--log-level=3'])
window= SSRPointerWindow()
window.show()
app.exec()
