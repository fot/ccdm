import os
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QHBoxLayout,
                             QLineEdit, QLabel, QMessageBox, QFrame)
from PyQt5.QtGui import QIcon
from misc import open_file_dialog, update_merge_button_style
from jira_items import check_jira_status
from google_auth import handle_google_login, handle_google_logout

class LimitsRevControlGUI(QWidget):
    def __init__(self):
        super().__init__()
        # init state tracking
        self.is_logged_in= False
        self.is_jira_valid= False
        self.is_file_loaded= False
        self.initUI()

    def initUI(self):
        self.setWindowTitle("I want this to be a funny name.")
        script_dir= os.path.dirname(os.path.abspath(__file__))
        icon_path= os.path.join(script_dir, "app_icon.ico")
        self.setWindowIcon(QIcon(icon_path))
        self.setGeometry(300, 300, 600, 750)
        layout = QVBoxLayout()
        layout.setSpacing(12)

        # Google Login Section
        self.lbl_auth_status= QLabel("CFA Google Account Log Status: 🔴<br>Logged Out")
        layout.addWidget(self.lbl_auth_status)
        login_button_layout= QHBoxLayout()
        self.btn_login= QPushButton("Login")
        self.btn_login.clicked.connect(lambda: handle_google_login(self))
        self.btn_logout= QPushButton("Logout")
        self.btn_logout.setEnabled(False)
        self.btn_logout.clicked.connect(lambda: handle_google_logout(self))
        login_button_layout.addWidget(self.btn_login)
        login_button_layout.addWidget(self.btn_logout)
        layout.addLayout(login_button_layout) 
        layout.addWidget(self.create_separator())

        # File Selection Section
        self.lbl_file_status = QLabel("File Status: 🔴<br>No file selected")
        self.btn_load_file = QPushButton("Load File (csv, xlsx)")
        self.btn_load_file.clicked.connect(lambda: open_file_dialog(self))
        layout.addWidget(self.lbl_file_status)
        layout.addWidget(self.btn_load_file)
        layout.addWidget(self.create_separator())

        # JIRA Section (1 x 2 for input ticket and status button)
        self.jira_status = QLabel(
            "Jira Status: 🔴<br>Ticket: N/A, Status: N/A<br>Title: N/A<br>Reporter: N/A")
        jira_layout= QHBoxLayout()
        self.jira_ticket = QLineEdit()
        self.jira_ticket.setPlaceholderText("i.e.: CRF-12345")
        self.jira_ticket.setFixedWidth(200)
        self.btn_check_jira = QPushButton("Check Status")
        self.btn_check_jira.clicked.connect(lambda: check_jira_status(self))
        jira_layout.addWidget(self.jira_ticket)
        jira_layout.addWidget(self.btn_check_jira)
        layout.addWidget(self.jira_status)
        layout.addLayout(jira_layout)
        layout.addWidget(self.create_separator())

        # Merge to Master Button
        self.btn_merge = QPushButton("Merge to Master")
        self.btn_merge.setEnabled(False) 
        self.btn_merge.clicked.connect(self.merge_to_master)
        layout.addWidget(self.btn_merge)

        # Save to SVN Button
        self.btn_svn = QPushButton("Save to SVN")
        self.btn_svn.setEnabled(False)
        self.btn_svn.clicked.connect(self.save_to_svn)
        layout.addWidget(self.btn_svn)
        update_merge_button_style(self, enabled=False) # Set initial grey style
        layout.addStretch()

        # Exit Button
        btn_exit = QPushButton("Exit")
        btn_exit.setStyleSheet("color: #cc0000; font-weight: bold;")
        btn_exit.clicked.connect(self.close)
        layout.addWidget(btn_exit)
        self.setLayout(layout)

    # --- Utility Methods ---
    def create_separator(self):
        line = QFrame(); line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        return line

    def merge_to_master(self):
        QMessageBox.information(self, "Merge to Google Sheet Master", f"Merging data from ({self.fileName}) to Master Google Sheets File...")

    def save_to_svn(self):
        QMessageBox.information(self, "Save to SVN", "Saving Master Google Sheets file to SVN...")
