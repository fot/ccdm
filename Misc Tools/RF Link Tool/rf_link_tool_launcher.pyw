import sys
from main_gui import RFLinkToolGui
from PyQt5.QtWidgets import QApplication

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = RFLinkToolGui()
    window.show()
    sys.exit(app.exec_())
