import os.path
from PyQt5.QtWidgets import QMessageBox
from misc import validate_all_conditions

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


def get_user_specific_credentials():
    home = os.path.expanduser("~")
    storage_dir = os.path.join(home, ".chandra_limits")
    if not os.path.exists(storage_dir):
        os.makedirs(storage_dir)
    return storage_dir


def get_credentials():
    SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/userinfo.profile",
        "https://www.googleapis.com/auth/userinfo.email",
        "openid"
    ]

    user_dir = get_user_specific_credentials()
    token_path = os.path.join(user_dir, "token.json")
    credentials_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "credentials.json")
    creds = None

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None

        if not creds:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            try:
                creds = flow.run_local_server(
                    port= 0,
                    timeout= 30,
                    prompt="select_account",
                    authorization_prompt_message= "Please complete this login in your browser...")
            except Exception as e:
                raise Exception(f"Authentication failed or timed out: {e}")

        # Save the credentials locally for the next run
        with open(token_path, "w") as token:
            token.write(creds.to_json())

    return creds


def get_oauth2_api_data(self):
    try:
        self.oauth_service= build("oauth2", "v2", credentials= get_credentials())
        user_info= self.oauth_service.userinfo().get().execute()
        return {
            "User ID": user_info.get('id'),
            "Email": user_info.get('email'),
            "Username": user_info.get('name')
        }
    except Exception as e:
        print(f"Error fetching user data: {e}")
        return None


def get_sheets_api_service(self):
    SPREADSHEET_ID= "15rRk5JAMWXBGiKTly4aP0cUuFE1qECZe01tNESSKXBo"
    try:
        sheets_service= build("sheets", "v4", credentials= get_credentials())
        result= sheets_service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID, range="Sheet1!A1:Q").execute()
        sheets_data= result.get("values", [])
        return sheets_service, sheets_data

    except HttpError as e:
        if e.resp.status == 403:
            print(f"\n[!] ACCESS DENIED: {self.oauth2_data['email']} does not have access to this sheet.")
            token_path = os.path.join(get_user_specific_credentials(), "token.json")
            if os.path.exists(token_path):
                os.remove(token_path)
            print("The local token has been cleared. Please restart and pick a different account.")
        else:
            print(f"Sheets API Error: {e}")
        os._exit(1)


def update_gui(self):
    "Update the GUI wtih the current login status information"
    if self.is_logged_in:
        self.btn_login.setEnabled(False)
        self.btn_logout.setEnabled(True)
        self.lbl_auth_status.setText(
            f"CFA Google Account Log Status: 🟢<br>Logged In ({self.oauth_data['Email']})")
        QMessageBox.information(self, "Success",
                                f"Logged in to CFA Google Account ({self.oauth_data['Email']}) Successfully!")
    else:
        self.btn_login.setEnabled(True)
        self.btn_logout.setEnabled(False)
        self.lbl_auth_status.setText("CFA Google Account Log Status: 🔴<br>Logged Out")
        QMessageBox.information(self, "Success", "Logged out of CFA Google Account Successfully!")


def handle_google_login(self):
    """
    Description: Orchestrates the Google OAuth2 login flow. It triggers the 
                    authentication process and, upon success, captures user profile 
                    and spreadsheet data to the GUI instance.
    
    Instance Attributes Updated:
        - self.oauth_data: Dictionary containing 'User ID', 'Email', and 'Username' 
                            retrieved from Google OAuth2 API.
        - self.sheets_data: A list of values (rows) retrieved from the Master 
                            Google Sheet spreadsheet.
        - self.is_logged_in: Boolean flag set to True on success.

    Side Effects:
        - Updates the auth status label with the user's email.
        - Toggles the enabled state of login/logout buttons.
        - Triggers validate_all_conditions() to refresh action button availability.
    """
    try:
        self.oauth_data= get_oauth2_api_data(self)
        self.sheets_service, self.sheets_data= get_sheets_api_service(self)
        self.is_logged_in= True # Declare user logged in
    except Exception as e:
        print(e)
        self.is_logged_in= False # Declare user logged out

    update_gui(self)
    validate_all_conditions(self) # Check if we can enable buttons


def handle_google_logout(self):
    """
    Description: Orchestrates the Google OAuth2 logout flow.
    
    Instance Attributes Updated:
        - self.oauth_data: None
        - self.sheets_data: None
        - self.is_logged_in: Boolean flag set to False.

    Side Effects:
        - Updates the auth status label to "not logged in" format.
        - Toggles the enabled state of login/logout buttons.
        - Triggers validate_all_conditions() to refresh action button availability.
    """
    self.oauth_data= None
    self.sheets_service, self.sheets_data= None, None
    self.is_logged_in= False
    update_gui(self)
    validate_all_conditions(self) # Check if we can enable buttons
