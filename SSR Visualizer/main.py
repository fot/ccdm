"Main Execution for App"

import sys
from PyQt5.QtWidgets import QApplication
from SSRWindow import SSRPointerWindow

app=    QApplication(sys.argv)
window= SSRPointerWindow()
window.show()
app.exec_()
