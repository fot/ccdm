from PyQt5.QtWidgets import QApplication
import sys
from SSRWindow import SSRPointerWindow

app=    QApplication(sys.argv)
window= SSRPointerWindow()

if len(sys.argv) > 3:
    hostName = sys.argv[1]
    databaseName = sys.argv[2]
    userName = sys.argv[3]
    window.initialize ( hostName, databaseName, userName )

if len(sys.argv) > 4:
    jplDirectory = sys.argv[4]
    window.setJplDirectory ( jplDirectory )

if len(sys.argv) > 5:
    reportDirectory = sys.argv[5]
    window.setReportDirectory ( reportDirectory )

if len(sys.argv) > 6:
    dataDirectory = sys.argv[6]
    window.setDataDirectory ( dataDirectory )

window.show()
app.exec_()
