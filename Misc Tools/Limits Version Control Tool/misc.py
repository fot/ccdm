"Misc functions for the limits_tool_gui"

import os.path
from PyQt5.QtWidgets import QPushButton, QFrame
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtCore import QUrl


def get_user_directory(directory):
    home = os.path.expanduser("~")
    storage_dir = os.path.join(home, directory)
    if not os.path.exists(storage_dir):
        os.makedirs(storage_dir)
    return storage_dir


def validate_all_conditions(self):
    """Checks if all criteria are met to enable the final action buttons."""

    if self.is_logged_in:
        self.btn_svn.setEnabled(True)
        update_svn_button_style(self, enabled=True)
    else:
        self.btn_svn.setEnabled(False)
        update_svn_button_style(self, enabled= False)

    if self.is_logged_in and self.is_jira_valid and self.is_file_loaded:
        self.btn_merge.setEnabled(True)
        update_merge_button_style(self, enabled=True)
    else:
        self.btn_merge.setEnabled(False)
        update_merge_button_style(self, enabled= False)


def update_merge_button_style(self, enabled):
    if enabled:
        self.btn_merge.setStyleSheet("background-color: #28a745; color: white; font-size: 18px; "
                                    "font-weight: bold; padding: 15px; border-radius: 5px;")
    else:
        self.btn_merge.setStyleSheet("background-color: #d3d3d3; color: #888888; font-size: 12px; "
                                    "font-weight: bold; padding: 12px; border-radius: 5px;")


def update_svn_button_style(self, enabled):
    if enabled:
        self.btn_svn.setStyleSheet("background-color: #28a745; color: white; font-size: 18px; "
                                   "font-weight: bold; padding: 15px; border-radius: 5px;")
    else:
        self.btn_svn.setStyleSheet("background-color: #d3d3d3; color: #888888; font-size: 12px; "
                                   "font-weight: bold; padding: 12px; border-radius: 5px;")


def update_master_button_layout(self):
    self.btn_master.setStyleSheet("background-color: #28a745; color: white; font-size: 12px; "
                                "font-weight: bold; padding: 10px; border-radius: 5px;")


def open_sheets_master():
    url = QUrl("https://docs.google.com/spreadsheets/d/15rRk5JAMWXBGiKTly4aP0cUuFE1qECZe01tNESSKXBo/edit?usp=sharing")
    QDesktopServices.openUrl(url)


def create_separator(self):
    line= QFrame(); line.setFrameShape(QFrame.HLine)
    line.setFrameShadow(QFrame.Sunken)
    return line


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
    self.btn_exit= QPushButton("Exit")
    self.btn_exit.setStyleSheet("color: #cc0000; font-weight: bold;")
    self.btn_exit.clicked.connect(self.close)
    self.layout.addWidget(self.btn_exit)
    self.setLayout(self.layout)
