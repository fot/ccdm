import os
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QHBoxLayout,
                             QLineEdit, QLabel, QMessageBox, QFrame, QMenuBar,
                             QMenu, QAction, QToolButton, QApplication)
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt
from information import how_to_btn_press, about_app_btn_press
from misc import (update_svn_button_style, update_master_button_layout,
                  open_sheets_master, update_merge_button_style)
from load_file import open_file_dialog
from jira_items import check_jira_status
from google_auth import handle_google_login, handle_google_logout
from merge_to_master import merge_to_master

class LimitsGatekeeperlGUI(QWidget):
    def __init__(self):
        super().__init__()
        # init state tracking
        self.is_logged_in= False
        self.is_jira_valid= False
        self.is_file_loaded= False
        self.initUI()
        self.add_top_menu_section()
        self.add_google_auth_section()
        self.add_file_select_section()
        self.add_jira_section()
        self.add_merge_to_master_btn()
        self.add_save_to_svn_btn()
        self.add_sheet_master_btn()
        self.add_exit_btn()

    def initUI(self):
        self.setWindowTitle("The Limits Gatekeeper")
        script_dir= os.path.dirname(os.path.abspath(__file__))
        icon_path= os.path.join(script_dir, "app_icon.ico")
        self.setWindowIcon(QIcon(icon_path))
        width, height= 300, 375
        self.resize(width, height)
        screen= QApplication.primaryScreen().availableGeometry()
        self.move((screen.width() - width) // 2, (screen.height() - height) // 2)
        self.layout= QVBoxLayout(self)
        self.layout.setSpacing(12)

    def add_top_menu_section(self):
        "Add the top menu to the GUI"
        self.nav_bar= QMenuBar()
        self.help_btn= QToolButton()
        self.help_btn.setText("Help")
        self.help_btn.setPopupMode(QToolButton.InstantPopup)
        self.help_btn.setStyleSheet("border: none; padding: 5px;")

        # init the "Help" button in the QMenuBar
        self.help_menu= QMenu(self.help_btn)

        # Add the Documentation dropdown option
        doc_action= QAction("How to Use This Tool", self)
        doc_action.triggered.connect(lambda: how_to_btn_press(self))
        self.help_menu.addAction(doc_action)

        # Add the About App dropdown option
        about_action= QAction("About App", self)
        about_action.triggered.connect(lambda: about_app_btn_press(self))
        self.help_menu.addAction(about_action)

        # Add the Dropdowns to the Help button
        self.help_btn.setMenu(self.help_menu)
        self.nav_bar.setCornerWidget(self.help_btn, Qt.TopRightCorner)

        # Add whole assembly to main layout
        self.layout.setMenuBar(self.nav_bar)

    def add_google_auth_section(self):
        "Add the 'CFA Google Account Auth' section to the GUI"
        self.lbl_auth_status= QLabel("CFA Google Account Log Status: 🔴<br>Logged Out")
        self.layout.addWidget(self.lbl_auth_status)
        login_button_layout= QHBoxLayout()
        self.btn_login= QPushButton("Login")
        self.btn_login.clicked.connect(lambda: handle_google_login(self))
        self.btn_logout= QPushButton("Logout")
        self.btn_logout.setEnabled(False)
        self.btn_logout.clicked.connect(lambda: handle_google_logout(self))
        login_button_layout.addWidget(self.btn_login)
        login_button_layout.addWidget(self.btn_logout)
        self.layout.addLayout(login_button_layout) 
        self.layout.addWidget(self.create_separator())

    def add_file_select_section(self):
        "Add the 'File Selection' section to the GUI"
        self.lbl_file_status = QLabel("File Status: 🔴<br>No file selected")
        self.btn_load_file = QPushButton("Load File (csv, xlsx)")
        self.btn_load_file.clicked.connect(lambda: open_file_dialog(self))
        self.layout.addWidget(self.lbl_file_status)
        self.layout.addWidget(self.btn_load_file)
        self.layout.addWidget(self.create_separator())

    def add_jira_section(self):
        "Add the JIRA section to the GUI"
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
        self.layout.addWidget(self.jira_status)
        self.layout.addLayout(jira_layout)
        self.layout.addWidget(self.create_separator())

    def add_merge_to_master_btn(self):
        "Add the 'Merge to Master' button to the GUI"
        self.btn_merge = QPushButton("Merge to Master")
        self.btn_merge.setEnabled(False) 
        self.btn_merge.clicked.connect(lambda: merge_to_master(self))
        self.layout.addWidget(self.btn_merge)
        update_merge_button_style(self, enabled=False)

    def add_save_to_svn_btn(self):
        "Add the 'Save to SVN' button to the GUI"
        self.btn_svn = QPushButton("Save to SVN")
        self.btn_svn.setEnabled(False)
        self.btn_svn.clicked.connect(self.save_to_svn)
        self.layout.addWidget(self.btn_svn)
        update_svn_button_style(self, enabled=False) # Set initial grey style

    def add_sheet_master_btn(self):
        "Add the 'Open Sheets Master' button to the GUI"
        self.btn_master= QPushButton("Open Sheets Master")
        self.btn_master.setEnabled(True)
        self.btn_master.clicked.connect(lambda: open_sheets_master())
        self.layout.addWidget(self.btn_master)
        update_master_button_layout(self)

    def add_exit_btn(self):
        "Add the exit button to the GUI"
        self.layout.addStretch()
        btn_exit = QPushButton("Exit")
        btn_exit.setStyleSheet("color: #cc0000; font-weight: bold;")
        btn_exit.clicked.connect(self.close)
        self.layout.addWidget(btn_exit)
        self.setLayout(self.layout)

    # --- Utility Methods ---
    def create_separator(self):
        line = QFrame(); line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        return line

    def merge_to_master(self):
        QMessageBox.information(self, "Merge to Google Sheet Master", f"Merging data from ({self.fileName}) to Master Google Sheets File...")

    def save_to_svn(self):
        QMessageBox.information(self, "Save to SVN", "Saving Master Google Sheets file to SVN...")
