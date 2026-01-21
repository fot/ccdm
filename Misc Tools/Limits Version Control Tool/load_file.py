import openpyxl
from typing import List, Any
from PyQt5.QtWidgets import QFileDialog

from misc import validate_all_conditions


def load_excel_raw(self) -> List[List[Any]]:
    """
    Opens an Excel file and returns a list of lists using only openpyxl.
    """
    sheet_name= "Sheet1"
    try:
        # Load the workbook (data_only=True ensures you get values, not formulas)
        workbook = openpyxl.load_workbook(self.fileName, data_only=True)

        # Select the active sheet or a specific one by name
        if sheet_name:
            sheet = workbook[sheet_name]
        else:
            sheet = workbook.active

        data = []
        # Iterate through rows and convert to a list of lists
        for row in sheet.iter_rows(values_only=True):
            # values_only=True returns a tuple of the cell values
            data.append(list(row))

        return data

    except FileNotFoundError:
        print(f"Error: The file {self.fileName} was not found.")
        return []
    except Exception as e:
        print(f"An error occurred: {e}")
        return []


def open_file_dialog(self):
    "Open a file dialog to select a data file (csv or xlsx)."
    self.fileName, _ = QFileDialog.getOpenFileName(self, "Select Data File", "", "Data Files (*.csv *.xlsx)")
    if self.fileName:
        self.lbl_file_status.setText(f"File Status: 🟢<br>Loaded ({self.fileName.split('/')[-1]})")
        self.excel_file_data= load_excel_raw(self)
        self.is_file_loaded = True
        validate_all_conditions(self) # Check if we can enable buttons


def clear_loaded_file(self):
    "Clear the loaded file"
    self.lbl_file_status.setText("File Status: 🔴<br>No file selected")
    self.excel_file_data= None
    self.is_file_loaded= False
    validate_all_conditions(self) # Check if we can enable buttons
