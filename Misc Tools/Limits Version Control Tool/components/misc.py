"Misc functions for the limits_tool_gui"

import os.path
from PyQt5.QtWidgets import QPushButton, QFrame


def get_user_directory(directory):
    home = os.path.expanduser("~")
    storage_dir = os.path.join(home, directory)
    if not os.path.exists(storage_dir):
        os.makedirs(storage_dir)
    return storage_dir


def validate_all_conditions(self):
    """Checks if all criteria are met to enable the final action buttons."""

    # Handle Google Log Status
    if self.is_logged_in:
        self.btn_login.setEnabled(False)
        self.btn_logout.setEnabled(True)
        self.lbl_auth_status.setText(f"CFA Google Account Log Status: 🟢"
                                     f"<br>Logged In ({self.oauth_data['Email']})")
    else:
        self.btn_login.setEnabled(True)
        self.btn_logout.setEnabled(False)
        self.lbl_auth_status.setText("CFA Google Account Log Status: 🔴<br>Logged Out")

    # Handle File Load Status
    if self.is_file_loaded:
        self.lbl_file_status.setText(f"File Status: 🟢<br>Loaded ({self.fileName.split('/')[-1]})")
    else:
        self.lbl_file_status.setText("File Status: 🔴<br>No file selected")

    # Handle JIRA Status
    try:
        status= str(self.ticket_obj.fields.status).strip()
        title= str(self.ticket_obj.fields.summary).strip()
        reporter= str(self.ticket_obj.fields.reporter.displayName).strip()
        if self.is_jira_valid:
            self.jira_status.setText(
                f"Jira Status: 🟢<br>Ticket: <b style='color:green;'>{self.ticket_obj}</b>, "
                f"Status: <b style='color:green;'>{status}</b>"
                f"<br>Title: {title}<br>Reporter: {reporter}")
        else:
            self.jira_status.setText(
                f"Jira Status: 🔴<br>Ticket: <b style='color:red;'>{self.ticket_obj}</b>, "
                f"Status: <b style='color:red;'>{status}</b>"
                f"<br>Title: {title}<br>Reporter: {reporter}")
    except AttributeError:
        self.jira_status.setText(f"Jira Status: 🔴<br>Ticket: N/A, "
                                 f"Status: N/A<br>Title: N/A<br>Reporter: N/A")

    # Handle SVN Directory Status
    if self.is_svn_valid:
        self.svn_status.setText(f"SVN Status: 🟢<br>Directory: {self.svn_path}")
    else:
        self.svn_status.setText("SVN Status: 🔴<br>Directory: N/A")

    # Enable Buttons
    if self.is_logged_in and self.is_jira_valid and self.is_file_loaded:
        enable_button(self.merge_btn)
    else:
        disable_button(self.merge_btn)

    if self.is_svn_valid:
        enable_button(self.svn_pull_btn)
    else:
        disable_button(self.svn_pull_btn)

    if self.is_logged_in and self.is_jira_valid and self.is_svn_valid:
        enable_button(self.svn_save_btn)
    else:
        disable_button(self.svn_save_btn)
    
    if self.is_logged_in:
        enable_button(self.save_btn)
    else:
        disable_button(self.save_btn)


def enable_button(button):
    button.setEnabled(True)
    button.setStyleSheet("background-color: #28a745; color: white; font-size: 12px; "
                         "font-weight: bold; padding: 12px; border-radius: 5px;")


def disable_button(button):
    button.setEnabled(False)
    button.setStyleSheet("background-color: #d3d3d3; color: #888888; font-size: 12px; "
                         "font-weight: bold; padding: 12px; border-radius: 5px;")


def create_separator(self):
    line= QFrame(); line.setFrameShape(QFrame.HLine)
    line.setFrameShadow(QFrame.Sunken)
    return line


def add_exit_btn(self):
    "Add the exit button to the GUI"
    self.layout.addStretch()
    self.btn_exit= QPushButton("Exit")
    self.btn_exit.setStyleSheet("color: #cc0000; font-weight: bold;")
    self.btn_exit.clicked.connect(self.close)
    self.layout.addWidget(self.btn_exit)
    self.setLayout(self.layout)
