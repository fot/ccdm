
from PyQt5.QtWidgets import QHBoxLayout, QPushButton, QMessageBox, QFileDialog, QLabel
from PyQt5.QtCore import Qt
import os
import subprocess
from pathlib import Path
from components.misc import create_separator, validate_all_conditions
from components.sheets_master import sheet_data_to_excel


class SVNCommitBox():
    """
        A confirmation dialog used to authorize an SVN commit action.

        This class serves as a final gateway before the application executes 
        terminal or API commands to commit changes to the SVN repository. 
        It ensures the user is ready to proceed and provides a clear path 
        to abort the operation.

        Attributes:
            svn_commit_box (QMessageBox): The underlying message box widget.
            svn_cont_btn (QPushButton): The 'Continue' button used to trigger 
                the commit logic.
    """
    def __init__(self):
        "Define the SVN Commit Box"
        self.svn_commit_box= QMessageBox()
        self.svn_commit_box.setWindowTitle("SVN Commit")
        self.svn_cont_btn= self.svn_commit_box.addButton("Continue", QMessageBox.ButtonRole.AcceptRole)
        self.svn_commit_box.addButton(QMessageBox.StandardButton.Cancel)

        commit_text= """
            <div style='margin-left: 10px;'>
                Select <b>Continue</b> to proceed with SVN Commit.<br><br>
                Select <b>Cancel</b> to cancel SVN Commit.
            """
        self.svn_commit_box.setInformativeText(commit_text)
        self.svn_commit_box.setTextFormat(Qt.RichText)


def get_svn_bin_path():
    """
        Dynamically locates the 'bin' directory of the bundled portable SVN tools.
    """
    # Locate the svn-tools directory relative to this component file
    component_dir = Path(__file__).resolve().parent

    # Try current folder, then one level up (root)
    svn_bin_dir = component_dir / "svn-tools" / "bin"
    if not svn_bin_dir.exists():
        svn_bin_dir = component_dir.parent / "svn-tools" / "bin"

    svn_exe = svn_bin_dir / "svn.exe"

    # Environment and DLL Handling
    # Adding the bin directory to PATH ensures svn.exe can see libapr-1.dll 
    # even when running from a network share.
    env = os.environ.copy()
    env["PATH"] = str(svn_bin_dir) + os.pathsep + env.get("PATH", "")

    # For Python 3.8+, we must explicitly trust the DLL directory
    dll_handler = None
    if hasattr(os, 'add_dll_directory'):
        dll_handler = os.add_dll_directory(str(svn_bin_dir))
    
    return svn_exe, env, dll_handler


def svn_commit_file(self):
    """
        Commits the 'chandra_limits.xlsx' file to the Subversion repository using 
        bundled portable SVN tools.

        This function handles the specific challenges of running portable binaries 
        from a network share (UNC paths) and managing DLL dependencies in 
        modern Python environments.

        Key Features:
        ----------
        - Dynamic Path Resolution: Locates 'svn-tools' relative to the script 
        location to maintain portability across different user environments.
        - DLL Management: Uses 'os.add_dll_directory' (Python 3.8+) to explicitly 
        trust the bundled bin folder, resolving 'libapr-1.dll not found' errors.
        - Path Priority: Prepend the bin directory to the system PATH environment 
        variable for the duration of the subprocess call.
        - UNC Path Workaround: Sets the 'cwd' (Current Working Directory) to a 
        local disk path (the file's parent directory) to prevent CMD errors 
        when executing binaries from a network share.

        Attributes Required:
        -------------------
        - self.svn_path (str/Path): The local directory of the SVN checkout.
        - self.ticket_obj (str, optional): JIRA ticket number for the commit message.

        Returns:
        -------
        - bool: True if 'add' and 'commit' operations were successful, False otherwise.

        Raises:
        -------
        - subprocess.CalledProcessError: Captured internally; prints STDOUT and 
        STDERR to the console for debugging.
    """
    # Pathing for Excel file
    file_path = Path(self.svn_path) / "chandra_limits.xlsx"
    ticket = getattr(self, "ticket_obj", "No JIRA Ticket")
    commit_message = f"Updated chandra_limits.xlsx ({ticket})"
    svn_exe, env, dll_handler= get_svn_bin_path()

    try:
        subprocess.run(
            [str(svn_exe), "add", str(file_path), "--force"],
            check=True,
            capture_output=True,
            text=True,
            env=env,
            cwd=str(file_path.parent) # Change working directory to local disk
        )

        subprocess.run(
            [str(svn_exe), "commit", str(file_path), "-m", commit_message],
            check=True,
            capture_output=True,
            text=True,
            env=env,
            cwd=str(file_path.parent)
        )
        return True

    except subprocess.CalledProcessError as e:
        print(f"SVN FAILED.\nSTDOUT: {e.stdout}\nSTDERR: {e.stderr}")
        return False

    finally:
        if dll_handler:
            dll_handler.close()


def save_to_svn(self):
    "Open the SVN Directory Select Dialog Box"
    sheet_data_to_excel(self, to_svn= True)
    commit_box= SVNCommitBox()
    commit_box.svn_commit_box.exec_()

    if commit_box.svn_commit_box.clickedButton() == commit_box.svn_cont_btn:
        commit_success= svn_commit_file(self)

        if commit_success:
            QMessageBox.information(self, "File Successfully Commited",
                                    f"Successfully SVN commited chandra_limits.xlsx to repo")
        else:
            QMessageBox.information(self, "File Commit Failed",
                                    f"Thats not a moon, its a Space Station.")


def pull_from_svn(self):
    "Pull the latest version of the chandra_limits.xlsx file from SVN and overwrite local copy"
    # Pathing for Excel file
    file_path = Path(self.svn_path) / "chandra_limits.xlsx"
    svn_exe, env, dll_handler= get_svn_bin_path()

    try:
        subprocess.run(
            [str(svn_exe), "update", str(file_path)],
            check=True,
            capture_output=True,
            text=True,
            env=env,
            cwd=str(file_path.parent) # Change working directory to local disk
        )
        QMessageBox.information(self, "SVN Update Successful!",
                        f"Successfully updated SVN repository {self.svn_path}.")

    except subprocess.CalledProcessError as e:
        print(f"SVN FAILED.\nSTDOUT: {e.stdout}\nSTDERR: {e.stderr}")
        QMessageBox.information(self, "SVN Update Failed!",
                        f"Failed to update SVN repository {self.svn_path}.")

    finally:
        if dll_handler:
            dll_handler.close()


def open_svn_dialog(self):
    "Open a file dialog to select a data file (xlsx)."
    self.svn_path= QFileDialog.getExistingDirectory(self, "Select SVN Directory")

    if self.svn_path:
        self.is_svn_valid= True

    validate_all_conditions(self)


def add_svn_section(self):
    """Add the entire SVN section to the GUI"""
    self.svn_status= QLabel("SVN Status: 🔴<br>Directory: N/A")
    self.svn_select_btn= QPushButton("Select SVN Directory")
    self.svn_select_btn.clicked.connect(lambda: open_svn_dialog(self))

    # Init the "Pull from Master" Button
    self.svn_pull_btn= QPushButton("Pull from SVN")
    self.svn_pull_btn.setEnabled(False)
    self.svn_pull_btn.clicked.connect(lambda: pull_from_svn(self))

    # Init the "Save to SVN" Button
    self.svn_save_btn= QPushButton("Save to SVN")
    self.svn_save_btn.setEnabled(False)
    self.svn_save_btn.clicked.connect(lambda: save_to_svn(self))

    self.svn_layout= QHBoxLayout()
    self.svn_layout.addWidget(self.svn_save_btn)
    self.svn_layout.addWidget(self.svn_pull_btn)
    
    self.layout.addWidget(self.svn_status)
    self.layout.addWidget(self.svn_select_btn)
    self.layout.addLayout(self.svn_layout)
    self.layout.addWidget(create_separator(self))
