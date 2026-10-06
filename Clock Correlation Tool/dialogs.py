import json
from pathlib import Path
from PyQt6.QtGui import QColor, QBrush
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QFileDialog, QTextEdit, QMessageBox,
                             QDateTimeEdit, QFormLayout, QGroupBox, QLineEdit, QWidget,
                             QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView)
from PyQt6.QtCore import QDateTime, QTime, Qt
from workers import SFTPWorker, SFTP_CONFIG_PATH
from reports import update_maude_refdata
from svn import commit_refdata


class SFTPConfigDialog(QDialog):
    """Dialog to configure and save SFTP credentials."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("SFTP Configuration")
        self.resize(400, 250)
        self.config_path = SFTP_CONFIG_PATH

        layout = QFormLayout(self)

        self.txt_host_path = QLineEdit(str(self.config_path))
        self.txt_host_path.setReadOnly(True)
        self.txt_host = QLineEdit()
        self.txt_port = QLineEdit("22")
        self.txt_user = QLineEdit()
        self.txt_pass = QLineEdit()
        self.txt_pass.setEchoMode(QLineEdit.EchoMode.Password)

        self.txt_erp_dir = QLineEdit()
        self.txt_bin_dir = QLineEdit()

        self.load_config()

        layout.addRow("Config File Location:", self.txt_host_path)
        layout.addRow("Host/IP:", self.txt_host)
        layout.addRow("Port:", self.txt_port)
        layout.addRow("Username:", self.txt_user)
        layout.addRow("Password/Key Passphrase:", self.txt_pass)
        layout.addRow("Remote ERP Folder:", self.txt_erp_dir)
        layout.addRow("Remote Binary DB Folder:", self.txt_bin_dir)

        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("Save Settings")
        self.btn_save.setStyleSheet("background-color: #2980b9; color: white; font-weight: bold;")
        self.btn_save.clicked.connect(self.save_config)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_save)

        layout.addRow(btn_layout)

    def load_config(self):
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                cfg = json.load(f)
                self.txt_host.setText(cfg.get('host', ''))
                self.txt_port.setText(str(cfg.get('port', '22')))
                self.txt_user.setText(cfg.get('user', ''))
                self.txt_pass.setText(cfg.get('password', ''))
                self.txt_erp_dir.setText(cfg.get('remote_erp_dir', ''))
                self.txt_bin_dir.setText(cfg.get('remote_bin_dir', ''))

    def save_config(self):
        cfg = {
            'host': self.txt_host.text(),
            'port': int(self.txt_port.text() or 22),
            'user': self.txt_user.text(),
            'password': self.txt_pass.text(),
            'remote_erp_dir': self.txt_erp_dir.text(),
            'remote_bin_dir': self.txt_bin_dir.text()
        }
        with open(self.config_path, 'w') as f:
            json.dump(cfg, f, indent=4)
        self.accept()


class JsonViewerDialog(QDialog):
    """Read-only popup for viewing JSON configuration files with dark mode support."""
    def __init__(self, filepath, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Viewing: {filepath.name}")
        self.resize(500, 600)
        layout = QVBoxLayout(self)
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setStyleSheet("font-family: Consolas, monospace; background-color: #1e1e1e; color: #d4d4d4;")
        try:
            with open(filepath, 'r') as f:
                text_edit.setText(f.read())
        except Exception as e:
            text_edit.setText(f"[ERROR] Could not read {filepath.name}:\n{str(e)}")
        layout.addWidget(text_edit)


class MaudeDialog(QDialog):
    """Dialog for MAUDE database query date ranges with time fixed at 08:00:00."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("MAUDE Data Import")
        self.resize(350, 180)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Select the UTC date range for MAUDE telemetry extraction (Time fixed at 08:00:00):"))
        form_layout = QFormLayout()

        now = QDateTime.currentDateTime()
        default_start_date = now.date().addDays(-7)
        default_end_date = now.date()

        self.start_dt = QDateTimeEdit(self)
        self.start_dt.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.start_dt.setDateTime(QDateTime(default_start_date, QTime(8, 0, 0)))
        self.start_dt.setCalendarPopup(True)
        self.start_dt.dateChanged.connect(lambda d: self.start_dt.setTime(QTime(8, 0, 0)))

        self.end_dt = QDateTimeEdit(self)
        self.end_dt.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.end_dt.setDateTime(QDateTime(default_end_date, QTime(8, 0, 0)))
        self.end_dt.setCalendarPopup(True)
        self.end_dt.dateChanged.connect(lambda d: self.end_dt.setTime(QTime(8, 0, 0)))

        form_layout.addRow("Start Time (UTC):", self.start_dt)
        form_layout.addRow("End Time (UTC):", self.end_dt)
        layout.addLayout(form_layout)

        btn_layout = QHBoxLayout()
        self.btn_fetch = QPushButton("Queue MAUDE Query")
        self.btn_fetch.setStyleSheet("background-color: #2c3e50; color: white; font-weight: bold;")
        self.btn_fetch.clicked.connect(self.accept)
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_fetch)
        layout.addLayout(btn_layout)

    def get_date_range(self):
        return self.start_dt.dateTime(), self.end_dt.dateTime()


class ErpSourceDialog(QDialog):
    """Small choice dialog to pick between local ERP file or SFTP fetch."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Ephemeris Source")
        self.resize(360, 150)
        self.selection = None  # 'local' or 'sftp'

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<b>Choose how to acquire the Ephemeris (.erp) file:</b>"))

        self.btn_local = QPushButton("Select Local .erp File")
        self.btn_local.setStyleSheet("background-color: #2980b9; color: white; font-weight: bold; padding: 8px;")
        self.btn_local.clicked.connect(lambda: self.set_selection('local'))

        self.btn_sftp = QPushButton("Pull Latest from Lucky (SFTP)")
        self.btn_sftp.setStyleSheet("background-color: #8e44ad; color: white; font-weight: bold; padding: 8px;")
        self.btn_sftp.clicked.connect(lambda: self.set_selection('sftp'))

        layout.addWidget(self.btn_local)
        layout.addWidget(self.btn_sftp)

    def set_selection(self, mode):
        self.selection = mode
        self.accept()


class NrtSourceDialog(QDialog):
    """Small choice dialog to pick between local NRT files, MAUDE query, or Master STO file extraction."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Telemetry Source")
        self.resize(360, 200)
        self.selection = None  # 'local', 'maude', or 'sto'

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<b>Choose how to add telemetry data:</b>"))

        self.btn_local = QPushButton("Select Local .nrt File(s)")
        self.btn_local.setStyleSheet("background-color: #2980b9; color: white; font-weight: bold; padding: 8px;")
        self.btn_local.clicked.connect(lambda: self.set_selection('local'))

        self.btn_maude = QPushButton("MAUDE Database Query...")
        self.btn_maude.setStyleSheet("background-color: #2c3e50; color: white; font-weight: bold; padding: 8px;")
        self.btn_maude.clicked.connect(lambda: self.set_selection('maude'))

        self.btn_sto = QPushButton("Extract from Master .STO File...")
        self.btn_sto.setStyleSheet("background-color: #16a085; color: white; font-weight: bold; padding: 8px;")
        self.btn_sto.clicked.connect(lambda: self.set_selection('sto'))

        layout.addWidget(self.btn_local)
        layout.addWidget(self.btn_maude)
        layout.addWidget(self.btn_sto)

    def set_selection(self, mode):
        self.selection = mode
        self.accept()


class StoContactSelectionDialog(QDialog):
    """Interactive table dialog enforcing a 15-contact limit based on exact STO intersection."""
    def __init__(self, supports, history_file, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Support Contacts")
        self.resize(800, 450)

        self.supports = supports
        self.history_file = Path(history_file)

        self.history_dict = {}       # Master dictionary of all known contacts: key=(start, end)
        self.locked_windows = set()  # Set of keys (start, end) for forced historical selections
        self.selected_windows = []   # Final output payload
        self.is_rerun = False        # Determines if we lock 15 or 8

        self.load_history()
        self.init_ui()

    def load_history(self):
        """Reads the JSON ledger. Removes the legacy 'selected' boolean and maps times."""
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r') as f:
                    data = json.load(f)
                    for item in data:
                        # Clean up legacy 'selected' keys if they exist in older files
                        if 'selected' in item:
                            del item['selected']

                        # Use exact start/end strings as the unique identifier key
                        key = (item['support_start'], item['support_end'])
                        self.history_dict[key] = item
            except Exception as e:
                print(f"[WARNING] Could not read contact history: {e}")

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Setup Table
        self.table = QTableWidget(len(self.supports), 5)
        self.table.setHorizontalHeaderLabels([
            "Support Start", 
            "Support End", 
            "Duration (min)", 
            "Extraction Window",
            "Status"
        ])

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        # 1. Intersect STO with History to find valid overlaps
        sto_hist_selected_keys = []
        new_valid_keys = []

        for sup in self.supports:
            key = (sup['start'].strftime('%Y:%j:%H:%M:%S'), sup['end'].strftime('%Y:%j:%H:%M:%S'))

            if key in self.history_dict:
                hist_item = self.history_dict[key]
                # Source of truth: select_start and select_end are not null
                if hist_item.get('select_start') is not None and hist_item.get('select_end') is not None:
                    sto_hist_selected_keys.append(key)
            else:
                if sup['is_valid']:
                    new_valid_keys.append(key)

        # 2. Determine limits: If no new valid supports exist, it's a rerun (lock 15). Otherwise lock 8.
        self.is_rerun = (len(new_valid_keys) == 0)
        lock_target = 15 if self.is_rerun else 8

        # 3. Sort chronologically and lock the targeted amount from the STO overlap
        sto_hist_selected_keys.sort()
        self.locked_windows = set(sto_hist_selected_keys[-lock_target:])

        # 4. Populate Table
        for row, sup in enumerate(self.supports):
            item_start = QTableWidgetItem(sup['start'].strftime('(%b/%d/%Y) %Y:%j:%H:%M:%S'))
            item_end = QTableWidgetItem(sup['end'].strftime('(%b/%d/%Y) %Y:%j:%H:%M:%S'))
            item_dur = QTableWidgetItem(f"{sup['duration_min']:.1f}")

            key = (sup['start'].strftime('%Y:%j:%H:%M:%S'), sup['end'].strftime('%Y:%j:%H:%M:%S'))

            is_valid = sup['is_valid']
            is_locked = key in self.locked_windows
            is_historical = key in self.history_dict

            # Determine Status and Window Text
            if is_locked:
                status_str = "Historical (Locked)"
                window_str = f"{sup['window_start'].strftime('%H:%M')} - {sup['window_end'].strftime('%H:%M')}"
            elif is_historical:
                status_str = "Historical (Ignored)"
                window_str = f"{sup['window_start'].strftime('%H:%M')} - {sup['window_end'].strftime('%H:%M')}" if is_valid else "Insufficient Duration"
            elif is_valid:
                status_str = "New"
                window_str = f"{sup['window_start'].strftime('%H:%M')} - {sup['window_end'].strftime('%H:%M')}"
            else:
                status_str = "Invalid"
                window_str = "Insufficient Duration"

            item_win = QTableWidgetItem(window_str)
            item_status = QTableWidgetItem(status_str)

            # Formatting & Interaction Rules
            if is_locked:
                hist_bg = QBrush(QColor("#2c3e50")) # dark blue-gray
                hist_fg = QBrush(QColor("#ecf0f1")) # light text
                for item in (item_start, item_end, item_dur, item_win, item_status):
                    item.setBackground(hist_bg)
                    item.setForeground(hist_fg)
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            elif not is_valid or (is_historical and not is_locked):
                gray_brush = QBrush(QColor("gray"))
                for item in (item_start, item_end, item_dur, item_win, item_status):
                    item.setForeground(gray_brush)
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable & ~Qt.ItemFlag.ItemIsEnabled)

            self.table.setItem(row, 0, item_start)
            self.table.setItem(row, 1, item_end)
            self.table.setItem(row, 2, item_dur)
            self.table.setItem(row, 3, item_win)
            self.table.setItem(row, 4, item_status)

        layout.addWidget(self.table)
        self.table.itemSelectionChanged.connect(self.check_selection_limit)

        # Setup Select Button
        self.btn_select = QPushButton("Extract Contacts")
        self.btn_select.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; padding: 8px;")
        self.btn_select.clicked.connect(self.on_select)
        layout.addWidget(self.btn_select)

        self.check_selection_limit()

    def check_selection_limit(self):
        selected_rows = set(item.row() for item in self.table.selectedItems())
        new_count = len(selected_rows)

        # Safely count how many locked windows were successfully matched
        locked_count = len(self.locked_windows)
        allowed_new = 15 - locked_count

        if new_count > allowed_new:
            self.btn_select.setEnabled(False)
            self.btn_select.setText(f"Selection Limit Exceeded ({new_count}/{allowed_new} New Contacts)")
            self.btn_select.setStyleSheet("background-color: #e74c3c; color: white; font-weight: bold; padding: 8px;")
        else:
            self.btn_select.setEnabled(True)
            self.btn_select.setText(f"Extract Contacts ({new_count} New, {locked_count} Historical)")
            self.btn_select.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; padding: 8px;")

    def on_select(self):
        # 1. Gather User Selections
        user_selected_rows = set(item.row() for item in self.table.selectedItems())

        # Ensure they have something valid to extract
        if not user_selected_rows and not self.locked_windows:
            QMessageBox.warning(self, "Selection Error", "No contacts are selected for extraction.")
            return

        self.selected_windows = []

        # 2. Iterate STO, build final payload, and update the Master History Dictionary
        for row, sup in enumerate(self.supports):
            sup_start_doy = sup['start'].strftime('%Y:%j:%H:%M:%S')
            sup_end_doy = sup['end'].strftime('%Y:%j:%H:%M:%S')
            key = (sup_start_doy, sup_end_doy)

            is_selected = (key in self.locked_windows) or (row in user_selected_rows)

            if is_selected and sup['is_valid']:
                win_start = sup['window_start']
                win_end = sup['window_end']
                self.selected_windows.append((win_start, win_end))
                sel_start_str = win_start.strftime('%Y:%j:%H:%M:%S')
                sel_end_str = win_end.strftime('%Y:%j:%H:%M:%S')
            else:
                sel_start_str = None
                sel_end_str = None

            # Create or overwrite the entry in the dictionary. 
            # Note: "selected" boolean is completely removed per flow requirement.
            self.history_dict[key] = {
                'support_start': sup_start_doy,
                'support_end': sup_end_doy,
                'select_start': sel_start_str,
                'select_end': sel_end_str
            }

        # 3. Convert dictionary to chronological list and save
        history_list = list(self.history_dict.values())
        history_list.sort(key=lambda x: x['support_start'])

        try:
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.history_file, 'w') as f:
                json.dump(history_list, f, indent=4)
        except Exception as e:
            QMessageBox.warning(self, "Save Error", f"Could not save contact history:\n{e}")

        self.accept()


class BinaryExportDialog(QDialog):
    """Dialog configuring local binary exports with SFTP integrations."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Export Binary Databases")
        self.resize(500, 300)
        self.base_dis = None
        self.base_dat = None
        layout = QVBoxLayout(self)

        file_group = QGroupBox("Base Legacy Databases (To Append)")
        file_layout = QFormLayout()

        # DIS Row
        dis_widget = QWidget()
        dis_layout = QHBoxLayout(dis_widget)
        dis_layout.setContentsMargins(0, 0, 0, 0)
        self.btn_dis = QPushButton("Select Local .DIS")
        self.btn_dis.clicked.connect(self.select_dis)
        self.btn_sftp_dis = QPushButton("Pull Latest DIS File (SFTP)")
        self.btn_sftp_dis.clicked.connect(self.pull_sftp_dis)
        dis_layout.addWidget(self.btn_dis)
        dis_layout.addWidget(self.btn_sftp_dis)
        self.lbl_dis = QLabel("None")

        # DAT Row
        dat_widget = QWidget()
        dat_layout = QHBoxLayout(dat_widget)
        dat_layout.setContentsMargins(0, 0, 0, 0)
        self.btn_dat = QPushButton("Select Local .DAT")
        self.btn_dat.clicked.connect(self.select_dat)
        self.btn_sftp_dat = QPushButton("Pull Latest DAT File (SFTP)")
        self.btn_sftp_dat.clicked.connect(self.pull_sftp_dat)
        dat_layout.addWidget(self.btn_dat)
        dat_layout.addWidget(self.btn_sftp_dat)
        self.lbl_dat = QLabel("None")

        file_layout.addRow(dis_widget, self.lbl_dis)
        file_layout.addRow(dat_widget, self.lbl_dat)
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)

        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("color: #f39c12; font-style: italic;")
        layout.addWidget(self.lbl_status)

        btn_layout = QHBoxLayout()
        self.btn_export = QPushButton("Confirm")
        self.btn_export.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold;")
        self.btn_export.clicked.connect(self.accept)
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_export)
        layout.addLayout(btn_layout)

    def select_dis(self):
        f, _ = QFileDialog.getOpenFileName(self, "Select Base .DIS", "", "DIS Files (*.DIS *.dis)")
        if f:
            self.base_dis = f
            self.lbl_dis.setText(Path(f).name)

    def select_dat(self):
        f, _ = QFileDialog.getOpenFileName(self, "Select Base .DAT", "", "DAT Files (*.DAT *.dat)")
        if f:
            self.base_dat = f
            self.lbl_dat.setText(Path(f).name)

    def _get_sftp_config(self):
        if not SFTP_CONFIG_PATH.exists():
            QMessageBox.warning(self, "Error", "SFTP Config not found. Set it in Settings.")
            return None
        with open(SFTP_CONFIG_PATH, 'r') as f:
            return json.load(f)

    def pull_sftp_dis(self):
        cfg = self._get_sftp_config()
        if not cfg: return
        self.btn_sftp_dis.setEnabled(False)
        self.btn_sftp_dis.setText("Downloading...")
        self.lbl_status.setText("Connecting to SFTP for .DIS...")
        
        self.worker_dis = SFTPWorker(cfg.get('remote_bin_dir', ''), '.DIS', file_prefix='CLKHST_')
        self.worker_dis.finished.connect(self.on_sftp_dis_success)
        self.worker_dis.error.connect(self.on_sftp_dis_error)
        self.worker_dis.start()

    def on_sftp_dis_success(self, local_path):
        self.base_dis = local_path
        self.lbl_dis.setText(f"(SFTP) {Path(local_path).name}")
        self.btn_sftp_dis.setText("Pull Latest (SFTP)")
        self.btn_sftp_dis.setEnabled(True)
        self.lbl_status.setText("Successfully pulled .DIS file.")

    def on_sftp_dis_error(self, err):
        self.lbl_status.setText(f"Error: {err}")
        self.btn_sftp_dis.setText("Pull Latest (SFTP)")
        self.btn_sftp_dis.setEnabled(True)

    def pull_sftp_dat(self):
        cfg = self._get_sftp_config()
        if not cfg: return
        self.btn_sftp_dat.setEnabled(False)
        self.btn_sftp_dat.setText("Downloading...")
        self.lbl_status.setText("Connecting to SFTP for .DAT...")

        self.worker_dat = SFTPWorker(cfg.get('remote_bin_dir', ''), '.DAT', file_prefix='CLKHST_')
        self.worker_dat.finished.connect(self.on_sftp_dat_success)
        self.worker_dat.error.connect(self.on_sftp_dat_error)
        self.worker_dat.start()

    def on_sftp_dat_success(self, local_path):
        self.base_dat = local_path
        self.lbl_dat.setText(f"(SFTP) {Path(local_path).name}")
        self.btn_sftp_dat.setText("Pull Latest (SFTP)")
        self.btn_sftp_dat.setEnabled(True)
        self.lbl_status.setText("Successfully pulled .DAT file.")

    def on_sftp_dat_error(self, err):
        self.lbl_status.setText(f"Error: {err}")
        self.btn_sftp_dat.setText("Pull Latest (SFTP)")
        self.btn_sftp_dat.setEnabled(True)


class EmailPreviewDialog(QDialog):
    """Dialog to preview and save a draft email with plot attachments."""
    def __init__(self, subject, body, attachment_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Email Draft Preview")
        self.resize(600, 500)

        # Address Variables
        self.sender_email = "rhoover@ipa.cfa.harvard.edu"
        self.recipient_email = "chandra_clock@head.cfa.harvard.edu"

        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.txt_from = QLineEdit(self.sender_email)
        self.txt_to = QLineEdit(self.recipient_email)
        self.txt_subject = QLineEdit(subject)

        self.txt_attach = QLineEdit(str(attachment_path) if attachment_path else "None Found")
        self.txt_attach.setReadOnly(True)
        if not attachment_path:
            self.txt_attach.setStyleSheet("color: #e74c3c; font-style: italic;")

        form_layout.addRow("From:", self.txt_from)
        form_layout.addRow("To:", self.txt_to)
        form_layout.addRow("Subject:", self.txt_subject)
        form_layout.addRow("Attachment:", self.txt_attach)
        layout.addLayout(form_layout)

        self.txt_body = QTextEdit()
        self.txt_body.setPlainText(body)
        layout.addWidget(QLabel("<b>Body:</b>"))
        layout.addWidget(self.txt_body)

        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("Save Draft (Send Later)")
        self.btn_save.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold;")
        self.btn_save.clicked.connect(self.accept)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_save)
        layout.addLayout(btn_layout)

    def get_email_data(self):
        return {
            "from": self.txt_from.text(),
            "to": self.txt_to.text(),
            "subject": self.txt_subject.text(),
            "body": self.txt_body.toPlainText(),
            "attachment": self.txt_attach.text()
        }


class MaudeRefdataDialog(QDialog):
    def __init__(self, dest_dis_path=None, nrt_df=None, parent=None):
        super().__init__(parent)
        self.dest_dis_path = dest_dis_path
        self.nrt_df = nrt_df

        self.setWindowTitle("Update MAUDE Refdata & SVN Commit")
        self.resize(450, 300)
        self.setup_ui()
        self.check_auto_populate()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Input for the CLKHST filename
        input_layout = QHBoxLayout()
        self.file_label = QLabel("Source CLKHST File:")
        self.file_input = QLineEdit()
        self.file_input.setPlaceholderText("e.g., CLKHST_nnnn.dis")
        input_layout.addWidget(self.file_label)
        input_layout.addWidget(self.file_input)
        layout.addLayout(input_layout)

        # Status log
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        layout.addWidget(self.log_output)

        # Buttons
        button_layout = QHBoxLayout()
        self.btn_update = QPushButton("Update refdata.txt")
        self.btn_commit = QPushButton("SVN Commit")
        self.btn_cancel = QPushButton("Close")

        self.btn_update.clicked.connect(self.update_refdata)
        self.btn_commit.clicked.connect(self.svn_commit)
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_commit.setEnabled(False)

        button_layout.addWidget(self.btn_update)
        button_layout.addWidget(self.btn_commit)
        button_layout.addWidget(self.btn_cancel)
        layout.addLayout(button_layout)

    def check_auto_populate(self):
        """Evaluate the provided binary path and update the UI accordingly."""
        if self.dest_dis_path and Path(self.dest_dis_path).name:
            # Extract filename without the .dis extension
            filename = Path(self.dest_dis_path).stem 
            self.file_input.setText(filename)
            self.log_message(f"Auto-detected CLKHST filename: {filename}\n")
        else:
            self.log_message("No recent binary export detected.\n"
                             "Please manually enter the CLKHST filename for the SVN commit message.\n")

    def log_message(self, message):
        """Append messages to the status text area."""
        self.log_output.append(message)

    def update_refdata(self):
        try:
            self.make_commit = update_maude_refdata(self.nrt_df)

            if self.make_commit:
                self.btn_commit.setEnabled(True)
                self.log_message("refdata.txt updated successfully. Ready for SVN commit.")
            else:
                self.log_message("No new data to update in refdata.txt. SVN commit is disabled.")

        except Exception as e:
            self.log_message(f"Error updating refdata: {str(e)}")
            self.make_commit = False
            self.btn_commit.setEnabled(False)

    def svn_commit(self):
        clkhst_name = self.file_input.text().strip()

        if not clkhst_name:
            QMessageBox.warning(self, "Input Error", "Please enter the CLKHST filename.")
            return

        try:
            self.log_message(f"Updating MAUDE refdata from {clkhst_name}...")

            if self.make_commit:
                self.log_message("Committing refdata.txt to SVN...")
                commit_message = f"Added data from {clkhst_name}.dis"
                self.log_message(f"Commit message: {commit_message}")
                commit_refdata(commit_message)

                self.log_message("Success: File updated and committed to SVN.")
            else:
                self.log_message("No new data to commit. refdata.txt remains unchanged.")

        except Exception as e:
            self.log_message(f"Error during process: {str(e)}")
