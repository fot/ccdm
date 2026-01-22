"Informationals"

from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import Qt


def how_to_btn_press(self):
    "Handle the pressing of the documentation button"
    how_to_box= QMessageBox()
    how_to_box.setWindowTitle("How to Use This Tool")

    html_text = """
        <div style='margin-left: 10px;'>
            <li><b>CFA Google Account Log Status: </b>Log into your CFA Google Account using the "login" button
            under the "CFA Google Account Log Status" section. Upon 
            successful authentication with your CFA google account the status 
            will change from 🔴 to 🟢.</li>
            <br>
            <li><b>File Status: </b>Click the "Load File" button to select an input file. 
            Files must be type .csv, or .xlsx. "File Status" will change from 🔴 to 🟢 once the
            file load was successful.</li>
            <br>
            <li><b>Jira Status: </b>Input the JIRA ticket being used to track the current limits change. 
            Click the "Check Status" button once a ticket has been inputted. Jira Status will change from 
            🔴 to 🟢 if the inputted Jira ticket is in the <b>"Waiting for Configuration"</b> state. This is the 
            only state that merging to master is allowed.</li>
            <br>
            <li><b>Merge to Master: </b>This button (once enabled) will merge data from the "selected file" 
            to the "Google Sheets Master" file. This button will become enabled once "CFA Google Account Log Status", 
            "File Status", and "Jira Status" are all 🟢. If any of these three conditions become 🔴, the 
            <b>Merge to Master</b> button will become disabled.</li>
            <br>
            <li><b>Save to SVN: </b>This button (once enabled) pulls the most recent version of the 
            "Google Sheets Master" file, and saves it as an excel spreadsheet document (.xlsx) to the 
            SVN repository (http://svn.occ.harvard.edu/svn/fot/). This button will become enabled once 
            the "CFA Google Account Log Status" becomes 🟢. If the "CFA Google Account Log Status" 
            becomes 🔴 the <b>Save to SVN</b> button will be disabled.</li>
            <br>
            <li><b>Exit: </b>This button exits the Limits Gatekeeper tool.</li>
            <br>
        </div>
        """
    how_to_box.setText("<b>Tool Button / Section Descriptions:</b>")
    how_to_box.setInformativeText(html_text)
    how_to_box.setTextFormat(Qt.RichText)
    how_to_box.exec_()


def about_app_btn_press(self):
    "Handle pressing of the about app button"
    message= ("<b>The Limits Gatekeeper v1.0</b><br><br>The Limits Gatekeeper "
              "is a tool developed to enforce the version control process used to "
              """update the "Chandra Limits Master Google Sheets" file. """
              "<br><br>Developed By: Ryan Hoover")
    QMessageBox.information(self, "About App", message)
