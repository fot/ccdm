
from PyQt5.QtWidgets import QPushButton, QMessageBox
from misc import update_svn_button_style


def add_save_to_svn_btn(self):
    "Add the 'Save to SVN' button to the GUI"
    self.btn_svn = QPushButton("Save to SVN")
    self.btn_svn.setEnabled(False)
    self.btn_svn.clicked.connect(lambda: save_to_svn(self))
    self.layout.addWidget(self.btn_svn)
    update_svn_button_style(self, enabled=False) # Set initial grey style


def save_to_svn(self):
    QMessageBox.information(self, "Save to SVN", "Saving Master Google Sheets file to SVN...")
