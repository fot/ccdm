"Functions to initialzie the Top Bar Menu in the main GUI"

from misc import get_user_directory
from PyQt5.QtWidgets import QMessageBox, QMenuBar, QMenu, QAction, QToolButton
from PyQt5.QtCore import Qt


def add_top_menu_section(self):
    """
    Initializes and configures the main navigation bar for the application.
    
    This function creates a QMenuBar and populates it with two custom styled 
    QToolButtons ("File" and "Help") positioned at the top corners of the UI. 
    It suppresses the default dropdown arrow icon for a cleaner look.

    Components:
        - File Menu (Top Left): Contains an action to download/open the Excel template.
        - Help Menu (Top Right): Contains actions for documentation and 'About' info.
        - Styling: Removes borders and hides the 'menu-indicator' (dropdown arrow).

    Note:
        Uses QToolButton.InstantPopup to ensure menus appear immediately upon 
        clicking the button text.
    """

    # init the "File" button and its menu in the QMenuBar
    self.file_btn= QToolButton()
    self.file_btn.setText("File")
    self.file_btn.setPopupMode(QToolButton.InstantPopup)
    self.file_btn.setStyleSheet("""QToolButton { border: none; padding: 5px; }
                                    QToolButton::menu-indicator { image: none; }""")
    self.file_menu= QMenu(self.file_btn)
    self.file_action= QAction("Download Template File (.xlsx)")
    self.file_action.triggered.connect(lambda: print("downloading file..."))
    self.file_menu.addAction(self.file_action)
    self.file_btn.setMenu(self.file_menu)

    # init the "Help" buttton and its menu items
    self.key_action= QAction("How To Setup User Keys", self)
    self.doc_action= QAction("How to Use This Tool", self)
    self.about_action= QAction("About App", self)
    self.key_action.triggered.connect(lambda: setup_btn_press(self))
    self.doc_action.triggered.connect(lambda: how_to_btn_press(self))
    self.about_action.triggered.connect(lambda: about_app_btn_press(self))

    self.help_btn= QToolButton()
    self.help_btn.setText("Help")
    self.help_btn.setPopupMode(QToolButton.InstantPopup)
    self.help_btn.setStyleSheet("""QToolButton { border: none; padding: 5px; }
                                    QToolButton::menu-indicator { image: none; }""")
    self.help_menu= QMenu(self.help_btn)
    self.help_menu.addAction(self.key_action)
    self.help_menu.addAction(self.doc_action)
    self.help_menu.addAction(self.about_action)
    self.help_btn.setMenu(self.help_menu)

    # Assemble the nav_bar
    self.nav_bar= QMenuBar()
    self.nav_bar.setCornerWidget(self.file_btn, Qt.TopLeftCorner)
    self.nav_bar.setCornerWidget(self.help_btn, Qt.TopRightCorner)
    self.layout.setMenuBar(self.nav_bar)

def setup_btn_press(self):
    "Handle pressing of the How To Setup User Keys Button."
    setup_box= QMessageBox()
    setup_box.setWindowTitle("How to Setup User Keys")

    html_text= f"""
        <div style='margin-left: 10px;'>
            <li><b>Setup JIRA Personal Access Token:</b><ol>
            <li>Log on to JIRA through OccWeb.</li><li>Navigate to your profile 
            (user icon at the top right) and navigate to <b>Profile</b>.</li>
            <li>Next navigate to <b>Personal Access Tokens</b>.</li>
            <li>Click the <b>Create Token</b> button.</li>
            <li>Save this access token in a text file (.txt) called <b>jira_token.txt</b> 
            in the directory <b>{get_user_directory(".chandra_limits")}</b>.</li>
            <li>This key allows <b>The Limits Gatekeeper</b> tool to access JIRA ticket status 
            information from the OCC JIRA server. This tool only reads data from the OCC 
            JIRA server.</li>
            </ol></li>
            <li><b>CFA Google Account API Credentials JSON File:</b><ol>
            <li>Contact an administrator for this application in order to recieve the Google 
            API <b>credentials.json</b> file.</li>
            <li>Place the <b>credentials.json</b> file in the directory 
            <b>{get_user_directory(".chandra_limits")}</b>.</li>
            <li>This key allows <b>The Limits Gatekeeper</b> tool to log you into your CFA 
            Google Account. On subsequent runs of this tool, this key is not used. A local 
            copy of the key for <b>your account</b> is saved in 
            <b>{get_user_directory(".chandra_limits")}</b>.</li>
            </ol></li>
            <br>
        </div>
        """
    setup_box.setText("<b>How To Setup User Keys:</b>")
    setup_box.setInformativeText(html_text)
    setup_box.setTextFormat(Qt.RichText)
    setup_box.exec_()


def how_to_btn_press(self):
    "Handle the pressing of the documentation button"
    how_to_box= QMessageBox()
    how_to_box.setWindowTitle("How to Use This Tool")

    html_text= """
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
