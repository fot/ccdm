import os
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QApplication
from PyQt5.QtGui import QIcon
from components.top_menu_setup import add_top_menu_section
from components.misc import add_exit_btn, validate_all_conditions
from components.load_file import add_file_select_section
from components.jira_items import add_jira_section
from components.google_auth import add_google_auth_section
from components.sheets_master import add_sheet_master_btns
from components.svn_items import add_svn_section


class LimitsGatekeeperlGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.is_logged_in=   False
        self.is_jira_valid=  False
        self.is_file_loaded= False
        self.is_svn_valid=   False
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
        add_sheet_master_btns(self)        
        add_jira_section(self)
        add_svn_section(self)
        add_exit_btn(self)
        validate_all_conditions(self)
