from jira import JIRA
from jira.exceptions import JIRAError
from PyQt5.QtWidgets import QMessageBox
from misc import validate_all_conditions


def get_user_key(file_path):
    "Open txt file for user key and return the key as a string"
    with open(file_path, 'r') as file:
        return file.read().strip()


def init_jira_connection():
    "Initializer and return a Jira connection object"
    JIRA_SERVER= "https://occ-cfa.cfa.harvard.edu/"

    jira= JIRA(
        server= JIRA_SERVER,
        token_auth= get_user_key("C:/Users/RHoover/Desktop/jira_api_token.txt"),
        timeout= 60)

    return jira


def handle_jira_error(self, error_type, error_message):
    status, title, reporter= "ERROR", "N/A", "N/A"
    icon, color_code= "🔴", "red"
    self.jira_status.setText(
        f"Jira Status: {icon}<br>Ticket: <b style='color:{color_code};'>{error_type}</b>, "
        f"Status: <b style='color:{color_code};'>{status}</b>"
        f"<br>Title: {title}<br>Reporter: {reporter}")
    QMessageBox.information(self, "JIRA Check Failed", error_message)


def check_jira_status(self):
    try:
        jira_connection= init_jira_connection()
        ticket_obj= jira_connection.issue(self.jira_ticket.text())
        status= str(ticket_obj.fields.status).strip()
        title= str(ticket_obj.fields.summary).strip()
        reporter= str(ticket_obj.fields.reporter.displayName).strip()

        if status.lower() in ["waiting for configuration", "configured"]:
            icon, color_code = "🟢", "green"
            self.is_jira_valid= True
        else:
            icon, color_code= "🔴", "red"
            self.is_jira_valid= False

        self.jira_status.setText(
            f"Jira Status: {icon}<br>Ticket: <b style='color:{color_code};'>{ticket_obj}</b>, "
            f"Status: <b style='color:{color_code};'>{status}</b>"
            f"<br>Title: {title}<br>Reporter: {reporter}")

        validate_all_conditions(self) # Check if we can enable buttons

    except ValueError:
        error_message= ("ERROR! Unable to connect to JIRA server.")
        handle_jira_error(self, "CONNECTION ERROR", error_message)
    except JIRAError:
        error_message= ("ERROR! Invalid JIRA ticket ID. Please input a "
                        "valid JIRA ticket ID (e.g., CRF-12345)")
        handle_jira_error(self, "INVALID TICKET ID", error_message)
