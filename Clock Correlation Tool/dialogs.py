import json
from pathlib import Path
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QFileDialog, QTextEdit, QMessageBox, 
                             QDateTimeEdit, QFormLayout, QGroupBox, QLineEdit, QWidget)
from PyQt6.QtCore import QDateTime, QTime
from workers import SFTPWorker, SFTP_CONFIG_PATH


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
    """Small choice dialog to pick between local NRT files or MAUDE query."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Telemetry Source")
        self.resize(360, 150)
        self.selection = None  # 'local' or 'maude'
        
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<b>Choose how to add telemetry data:</b>"))
        
        self.btn_local = QPushButton("Select Local .nrt File(s)")
        self.btn_local.setStyleSheet("background-color: #2980b9; color: white; font-weight: bold; padding: 8px;")
        self.btn_local.clicked.connect(lambda: self.set_selection('local'))
        
        self.btn_maude = QPushButton("MAUDE Database Query...")
        self.btn_maude.setStyleSheet("background-color: #2c3e50; color: white; font-weight: bold; padding: 8px;")
        self.btn_maude.clicked.connect(lambda: self.set_selection('maude'))
        
        layout.addWidget(self.btn_local)
        layout.addWidget(self.btn_maude)

    def set_selection(self, mode):
        self.selection = mode
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
        
        self.worker_dis = SFTPWorker(cfg.get('remote_bin_dir', ''), '.DIS')
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
        
        self.worker_dat = SFTPWorker(cfg.get('remote_bin_dir', ''), '.DAT')
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
