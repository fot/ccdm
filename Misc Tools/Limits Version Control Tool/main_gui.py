import os
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QHBoxLayout,
                             QLineEdit, QLabel, QMessageBox, QFrame, QMenuBar,
                             QMenu, QAction, QToolButton, QApplication)
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt
from top_menu_setup import add_top_menu_section
from misc import add_sheet_master_btn, add_exit_btn
from load_file import add_file_select_section
from jira_items import add_jira_section
from google_auth import add_google_auth_section
from merge_to_master import add_merge_to_master_btn
from save_to_svn import add_save_to_svn_btn

class LimitsGatekeeperlGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.is_logged_in= False
        self.is_jira_valid= False
        self.is_file_loaded= False
        self.initUI()

    def initUI(self):
        width, height= 300, 375
        script_dir= os.path.dirname(os.path.abspath(__file__))
        icon_path= os.path.join(script_dir, "app_icon.ico")
        screen= QApplication.primaryScreen().availableGeometry()
        self.setWindowTitle("The Limits Gatekeeper")
        self.setWindowIcon(QIcon(icon_path))
        self.resize(width, height)
        self.move((screen.width() - width) // 2, (screen.height() - height) // 2)
        self.layout= QVBoxLayout(self)
        self.layout.setSpacing(12)

        # Add all GUI elements
        add_top_menu_section(self)
        add_google_auth_section(self)
        add_file_select_section(self)
        add_jira_section(self)
        add_merge_to_master_btn(self)
        add_save_to_svn_btn(self)
        add_sheet_master_btn(self)
        add_exit_btn(self)
