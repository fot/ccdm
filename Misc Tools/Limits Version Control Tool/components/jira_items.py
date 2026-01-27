import os.path
from jira import JIRA
from jira.exceptions import JIRAError
from PyQt5.QtWidgets import QMessageBox, QLabel, QHBoxLayout, QLineEdit, QPushButton
from components.misc import validate_all_conditions, get_user_directory, create_separator


def get_user_key(file_path):
    "Open txt file for user key and return the key as a string"
    with open(file_path, 'r') as file:
        return file.read().strip()


def init_jira_connection():
    "Initializer and return a Jira connection object"
    JIRA_SERVER= "https://occ-cfa.cfa.harvard.edu/"
    key_dir= os.path.join(get_user_directory(".chandra_limits"), "jira_token.txt")

    jira= JIRA(
        server= JIRA_SERVER,
        token_auth= get_user_key(key_dir),
        timeout= 60)

    return jira


def handle_jira_error(self, error_type, error_message):
    status, title, reporter= "ERROR", "N/A", "N/A"
    icon, color_code= "🔴", "red"
    self.is_jira_valid= False
    self.jira_status.setText(
        f"Jira Status: {icon}<br>Ticket: <b style='color:{color_code};'>{error_type}</b>, "
        f"Status: <b style='color:{color_code};'>{status}</b>"
        f"<br>Title: {title}<br>Reporter: {reporter}")
    QMessageBox.information(self, "JIRA Check Failed", error_message)


def check_jira_status(self):
    try:
        jira_connection= init_jira_connection()
        self.ticket_obj= jira_connection.issue(self.jira_ticket.text())
        status= str(self.ticket_obj.fields.status).strip()
        title= str(self.ticket_obj.fields.summary).strip()
        reporter= str(self.ticket_obj.fields.reporter.displayName).strip()

        if status.lower() in ["waiting for configuration", "configured"]:
            icon, color_code = "🟢", "green"
            self.is_jira_valid= True
        else:
            icon, color_code= "🔴", "red"
            # self.is_jira_valid= False

        self.jira_status.setText(
            f"Jira Status: {icon}<br>Ticket: <b style='color:{color_code};'>{self.ticket_obj}</b>, "
            f"Status: <b style='color:{color_code};'>{status}</b>"
            f"<br>Title: {title}<br>Reporter: {reporter}")

    except ValueError:
        error_message= ("ERROR! Unable to connect to JIRA server.")
        handle_jira_error(self, "CONNECTION ERROR", error_message)
    except JIRAError:
        error_message= ("ERROR! Invalid JIRA ticket ID. Please input a "
                        "valid JIRA ticket ID (e.g., CRF-12345)")
        handle_jira_error(self, "INVALID TICKET ID", error_message)

    validate_all_conditions(self) # Check if we can enable buttons


def add_jira_section(self):
    "Add the JIRA section to the GUI"
    self.jira_status= QLabel(
        "Jira Status: 🔴<br>Ticket: N/A, Status: N/A<br>Title: N/A<br>Reporter: N/A")
    self.jira_layout= QHBoxLayout()
    self.jira_ticket= QLineEdit()
    self.jira_ticket.setPlaceholderText("i.e.: CRF-12345")
    self.jira_ticket.setFixedWidth(200)
    self.btn_check_jira= QPushButton("Check Status")
    self.btn_check_jira.clicked.connect(lambda: check_jira_status(self))
    self.jira_layout.addWidget(self.jira_ticket)
    self.jira_layout.addWidget(self.btn_check_jira)
    self.layout.addWidget(self.jira_status)
    self.layout.addLayout(self.jira_layout)
    self.layout.addWidget(create_separator(self))
