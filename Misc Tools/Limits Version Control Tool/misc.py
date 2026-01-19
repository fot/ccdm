"Misc functions for the limits_tool_gui"

from PyQt5.QtWidgets import QFileDialog

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

def open_file_dialog(self):
    "Open a file dialog to select a data file (csv or xlsx)."
    self.fileName, _ = QFileDialog.getOpenFileName(self, "Select Data File", "", "Data Files (*.csv *.xlsx)")
    if self.fileName:
        self.lbl_file_status.setText(f"File Status: 🟢<br>Loaded ({self.fileName.split('/')[-1]})")
        self.is_file_loaded = True
        validate_all_conditions(self) # Check if we can enable buttons

def update_merge_button_style(self, enabled):
    if enabled:
        self.btn_merge.setStyleSheet("background-color: #28a745; color: white; font-size: 18px; "
                                        "font-weight: bold; padding: 15px; border-radius: 5px;")
    else:
        self.btn_merge.setStyleSheet("background-color: #d3d3d3; color: #888888; font-size: 18px; "
                                        "font-weight: bold; padding: 15px; border-radius: 5px;")

def update_svn_button_style(self, enabled):
    if enabled:
        self.btn_svn.setStyleSheet("background-color: #28a745; color: white; font-size: 18px; "
                            "font-weight: bold; padding: 15px; border-radius: 5px;")
    else:
        self.btn_svn.setStyleSheet("background-color: #d3d3d3; color: #888888; font-size: 18px; "
                            "font-weight: bold; padding: 15px; border-radius: 5px;")
