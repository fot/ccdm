"Functions to merge input excel file data to master"

from PyQt5.QtWidgets import QMessageBox, QPushButton
from google_auth import get_sheets_api_service
from load_file import clear_loaded_file
from misc import update_merge_button_style


SPREADSHEET_ID= "15rRk5JAMWXBGiKTly4aP0cUuFE1qECZe01tNESSKXBo"


def update_google_sheet(self):
    "update the google sheets file via API"

    body= {"values": self.excel_file_data[1:]}

    self.sheets_service.spreadsheets().values().append(
        spreadsheetId= SPREADSHEET_ID,
        range= "Sheet1!A1:P",
        valueInputOption= "USER_ENTERED",
        body= body
        ).execute()


def update_sheet_format(self):
    "Update the sheet's format after updating."
    spreadsheet = self.sheets_service.spreadsheets().get(spreadsheetId= SPREADSHEET_ID).execute()
    sheet_id = next(s['properties']['sheetId'] for s in spreadsheet['sheets'] 
                        if s['properties']['title'] == "Sheet1")
    num_rows= len(self.sheets_data) + len(self.excel_file_data) - 1
    num_cols= 17  # Columns A through Q

    border_style = {
        "style": "SOLID",
        "width": 1,
        "color": {"red": 0, "green": 0, "blue": 0}
    }

    requests = [
        # 1. Header Row (Exactly Row 0, Columns 0-15)
        {
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 0,
                    "endRowIndex": 1,
                    "startColumnIndex": 0,
                    "endColumnIndex": num_cols
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": {"red": 0.85, "green": 0.85, "blue": 0.85},
                        "textFormat": {"bold": True},
                        "horizontalAlignment": "CENTER",
                        "borders": {
                            "top": border_style, "bottom": border_style, 
                            "left": border_style, "right": border_style
                        }
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,borders)"
            }
        },
        # 2. Data Rows (From Row 1 to num_rows, Columns 0-15)
        {
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 1,
                    "endRowIndex": num_rows,
                    "startColumnIndex": 0,
                    "endColumnIndex": num_cols
                },
                "cell": {
                    "userEnteredFormat": {
                        "horizontalAlignment": "CENTER",
                        "borders": {
                            "top": border_style, "bottom": border_style, 
                            "left": border_style, "right": border_style
                        }
                    }
                },
                "fields": "userEnteredFormat(horizontalAlignment,borders)"
            }
        }
    ]

    self.sheets_service.spreadsheets().batchUpdate(spreadsheetId= SPREADSHEET_ID, body={"requests": requests}).execute()


def append_jira_ticket_num(self):
    "Append the jira ticket number to the end of the excel sheet data before push to google sheets"
    for row in self.excel_file_data:
        try:
            row[16] = str(self.ticket_obj)
        except IndexError:
            row.append(str(self.ticket_obj))


def merge_to_master(self):
    "Actions when the 'Merge to Master' button is clicked"
    
    msg = QMessageBox(self)
    msg.setWindowTitle("Merge to Google Sheet Master")
    msg.setText(f"Proceed with merging data from ({self.fileName}) to Master Google Sheets File?")
    msg.setIcon(QMessageBox.Icon.Information)

    # Add buttons and change the text of the "Ok" button
    continue_button = msg.addButton("Continue", QMessageBox.ButtonRole.AcceptRole)
    msg.addButton(QMessageBox.StandardButton.Cancel)
    msg.exec()

    if msg.clickedButton() == continue_button:

        # Refresh the sheets data in the event it was edited externally
        _, self.sheets_data= get_sheets_api_service(self)

        # Update Google Sheets file with excel data
        append_jira_ticket_num(self)
        update_google_sheet(self)
        update_sheet_format(self)
        QMessageBox.information(self, "Success",
                        f"Successfully merged spreadsheet ({self.fileName}) to Google Sheets Master!")
        clear_loaded_file(self)
    else:
        pass


def add_merge_to_master_btn(self):
    "Add the 'Merge to Master' button to the GUI"
    self.btn_merge= QPushButton("Merge to Master")
    self.btn_merge.setEnabled(False) 
    self.btn_merge.clicked.connect(lambda: merge_to_master(self))
    self.layout.addWidget(self.btn_merge)
    update_merge_button_style(self, enabled=False)
