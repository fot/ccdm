import sys
from pathlib import Path
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QListWidget,
                             QFileDialog, QTextEdit, QMessageBox, QDialog,
                             QDateTimeEdit, QFormLayout, QGroupBox, QCheckBox)
from PyQt6.QtGui import QAction, QTextCursor
from PyQt6.QtCore import QObject, pyqtSignal, QDateTime, QTime, QThread

# Local Imports
from clock_processing import calculate_clock_drift
from binary_convert import convert_dis_file, convert_dat_file
from reports import (generate_trending_report, generate_correlation_report,
                     get_correlation_report_title)
from plots import generate_residual_plot


class ConsoleStream(QObject):
    """Intercepts sys.stdout for real-time GUI console updates."""
    text_written = pyqtSignal(str)

    def write(self, text):
        self.text_written.emit(str(text))

    def flush(self):
        pass


class PipelineWorker(QThread):
    """Runs heavy calculations in a background thread to keep the GUI responsive."""
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, erp_file, nrt_files, legacy_mode=False):
        super().__init__()
        self.erp_file = erp_file
        self.nrt_files = nrt_files
        self.legacy_mode = legacy_mode

    def run(self):
        try:
            nrt_df = calculate_clock_drift(self.erp_file, self.nrt_files, legacy_mode=self.legacy_mode)
            self.finished.emit(nrt_df)
        except Exception as e:
            import traceback
            self.error.emit(f"{str(e)}\n{traceback.format_exc()}")


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


class BinaryExportDialog(QDialog):
    """Dialog configuring local binary exports."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Export Binary Databases")
        self.resize(450, 300)
        self.base_dis = None
        self.base_dat = None
        layout = QVBoxLayout(self)

        file_group = QGroupBox("Base Legacy Databases (To Append)")
        file_layout = QFormLayout()
        
        self.btn_dis = QPushButton("Select Base .DIS")
        self.btn_dis.clicked.connect(self.select_dis)
        self.lbl_dis = QLabel("None")
        
        self.btn_dat = QPushButton("Select Base .DAT")
        self.btn_dat.clicked.connect(self.select_dat)
        self.lbl_dat = QLabel("None")

        file_layout.addRow(self.btn_dis, self.lbl_dis)
        file_layout.addRow(self.btn_dat, self.lbl_dat)
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)

        btn_layout = QHBoxLayout()
        self.btn_export = QPushButton("Run Export")
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


class ClockDriftApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Clock Correlation Tool")
        self.resize(900, 700)

        self.erp_file = None
        self.nrt_files = []
        self.maude_range = None
        self.nrt_df = None
        self.output_buttons = []
        self.legacy_mode = False

        self.console_stream = ConsoleStream()
        self.console_stream.text_written.connect(self.append_to_console)
        sys.stdout = self.console_stream

        self.init_menu()
        self.init_ui()

    def init_menu(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")

        action_select_erp = QAction("Select .erp File", self)
        action_select_erp.triggered.connect(self.select_erp_file)
        file_menu.addAction(action_select_erp)

        action_select_nrt = QAction("Select .nrt Files", self)
        action_select_nrt.triggered.connect(self.select_nrt_files)
        file_menu.addAction(action_select_nrt)

        action_maude = QAction("MAUDE Data Import...", self)
        action_maude.triggered.connect(self.open_maude_dialog)
        file_menu.addAction(action_maude)

        file_menu.addSeparator()
        action_exit = QAction("Exit", self)
        action_exit.triggered.connect(self.close)
        file_menu.addAction(action_exit)

        view_menu = menubar.addMenu("View")
        for f in ["constants.json", "calibration_data.json", "dsn_data.json"]:
            act = QAction(f, self)
            act.triggered.connect(lambda checked, name=f: self.view_calibration_file(name))
            view_menu.addAction(act)

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Tighten main layout margins and spacing to remove dead space
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(4)

        # Active Ephemeris UI Block
        erp_layout = QHBoxLayout()
        erp_layout.setContentsMargins(0, 0, 0, 0)
        self.lbl_erp_path = QLabel("No ERP file selected.")
        self.lbl_erp_path.setStyleSheet("color: gray; font-style: italic;")
        erp_layout.addWidget(QLabel("<b>Active Ephemeris:</b>"))
        erp_layout.addWidget(self.lbl_erp_path)
        erp_layout.addStretch()
        main_layout.addLayout(erp_layout)

        # Active Telemetry Queue UI Block
        nrt_layout = QVBoxLayout()
        nrt_layout.setContentsMargins(0, 0, 0, 0)
        nrt_layout.setSpacing(2)
        nrt_layout.addWidget(QLabel("<b>Active Telemetry Queue (NRT / MAUDE):</b>"))
        self.list_nrt_files = QListWidget()
        self.list_nrt_files.setMaximumHeight(80)
        nrt_layout.addWidget(self.list_nrt_files)
        main_layout.addLayout(nrt_layout)

        # Run Button & Legacy Mode Block
        run_layout = QHBoxLayout()
        run_layout.setContentsMargins(0, 0, 0, 0)
        
        self.chk_legacy = QCheckBox("Legacy Mode")
        self.chk_legacy.stateChanged.connect(self.toggle_legacy_mode)
        run_layout.addWidget(self.chk_legacy, stretch=1)

        self.btn_run = QPushButton("Execute Clock Correlation Pipeline")
        self.btn_run.setMinimumHeight(40)
        self.btn_run.setEnabled(False)
        self.btn_run.setStyleSheet("font-weight: bold; font-size: 14px; background-color: #8e44ad; color: white;")
        self.btn_run.clicked.connect(self.run_calculation)
        run_layout.addWidget(self.btn_run, stretch=3)
        
        main_layout.addLayout(run_layout)

        # Post-Processing UI Block
        self.output_group = QGroupBox("Output Generation & Post-Processing")
        output_layout = QHBoxLayout()

        self.btn_binaries = QPushButton("Export Binary DBs")
        self.btn_binaries.clicked.connect(self.export_binaries)

        self.btn_trend = QPushButton("Trending Report")
        self.btn_trend.clicked.connect(self.generate_trending)

        self.btn_corr = QPushButton("Correlation Report")
        self.btn_corr.clicked.connect(self.generate_correlation)

        self.btn_plot = QPushButton("Residual Plot")
        self.btn_plot.clicked.connect(self.generate_plot)

        self.btn_csv = QPushButton("Export CSV")
        self.btn_csv.clicked.connect(self.export_csv)

        self.output_buttons = [self.btn_binaries, self.btn_trend, self.btn_corr, self.btn_plot, self.btn_csv]
        for btn in self.output_buttons:
            btn.setEnabled(False) 
            output_layout.addWidget(btn)

        self.output_group.setLayout(output_layout)
        main_layout.addWidget(self.output_group)

        # Console Block
        main_layout.addWidget(QLabel("<b>Console Output:</b>"))
        self.txt_output = QTextEdit()
        self.txt_output.setReadOnly(True)
        self.txt_output.setStyleSheet("font-family: Consolas, monospace; background-color: #1e1e1e; color: #d4d4d4;")
        main_layout.addWidget(self.txt_output)

    def check_ready_state(self):
        has_erp = self.erp_file is not None
        has_data = len(self.nrt_files) > 0 or self.maude_range is not None
        
        if has_erp and has_data:
            self.btn_run.setEnabled(True)
        else:
            self.btn_run.setEnabled(False)

    def toggle_legacy_mode(self):
        self.legacy_mode = self.chk_legacy.isChecked()

    def select_erp_file(self):
        default_dir = Path("//noodle/fot/engineering/ccdm/Clock_Timing/ERPFiles")
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Ephemeris File", str(default_dir), "ERP Files (*.erp);;All Files (*.*)")
        if file_path:
            self.erp_file = file_path
            self.lbl_erp_path.setText(Path(self.erp_file).name)
            self.lbl_erp_path.setStyleSheet("color: white; font-weight: bold;")
            print(f"[UI] Loaded Ephemeris: {self.erp_file}")
            self.check_ready_state()

    def select_nrt_files(self):
        default_dir = Path("//noodle/fot/engineering/ccdm/Clock_Timing/NRTFiles")
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select NRT Telemetry Files", str(default_dir), "NRT Files (*.nrt);;All Files (*.*)")
        if files:
            for f in files:
                if f not in self.nrt_files:
                    self.nrt_files.append(f)
                    self.list_nrt_files.addItem(f"Local File: {f}")
            print(f"[UI] Appended {len(files)} telemetry file(s) to the queue.")
            self.check_ready_state()

    def open_maude_dialog(self):
        dialog = MaudeDialog(self)
        if dialog.exec():
            start_dt, end_dt = dialog.get_date_range()
            if start_dt >= end_dt:
                QMessageBox.warning(self, "Invalid Range", "Start time must be before End time.")
                return
            self.maude_range = (start_dt, end_dt)
            maude_str = f"MAUDE Query: {start_dt.toString('yyyy-MM-dd HH:mm:ss')} to {end_dt.toString('yyyy-MM-dd HH:mm:ss')}"
            self.list_nrt_files.addItem(maude_str)
            print(f"[UI] {maude_str} queued for extraction.")
            self.check_ready_state()

    def view_calibration_file(self, filename):
        target_path = Path(__file__).parent.resolve() / filename
        if not target_path.exists():
            QMessageBox.warning(self, "File Not Found", f"Could not locate {filename}.")
            return
        viewer = JsonViewerDialog(target_path, self)
        viewer.exec()

    def append_to_console(self, text):
        cursor = self.txt_output.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(text)
        self.txt_output.setTextCursor(cursor)
        self.txt_output.ensureCursorVisible()

    def run_calculation(self):
        self.btn_run.setEnabled(False)
        self.txt_output.clear()
        
        for btn in self.output_buttons:
            btn.setEnabled(False)

        print("[UI] Initializing Clock Correlation Pipeline in background thread...")
        if self.legacy_mode:
            print("[UI] Pipeline execution configured for Legacy Mode overrides.")
            
        self.worker = PipelineWorker(self.erp_file, self.nrt_files)
        self.worker.finished.connect(self.on_calculation_finished)
        self.worker.error.connect(self.on_calculation_error)
        self.worker.start()

    def on_calculation_finished(self, nrt_df):
        self.nrt_df = nrt_df
        print("\n[UI] Pipeline execution completed successfully. Output options enabled.")
        for btn in self.output_buttons:
            btn.setEnabled(True)
        self.btn_run.setEnabled(True)

    def on_calculation_error(self, err_msg):
        print(f"\n[ERROR] Pipeline halted due to exception:\n{err_msg}")
        self.btn_run.setEnabled(True)

    def export_binaries(self):
        dialog = BinaryExportDialog(self)
        if dialog.exec():
            print("[UI] Initiating Binary Database Export...")
            try:
                if dialog.base_dis:
                    convert_dis_file(self.nrt_df, dialog.base_dis)
                if dialog.base_dat:
                    convert_dat_file(self.nrt_df, dialog.base_dat)
            except Exception as e:
                print(f"[ERROR] Binary export failed: {e}")

    def generate_trending(self):
        try:
            box = QMessageBox(self)
            box.setWindowTitle("Trending Report Destination")
            box.setText("Would you like to append to an existing master trending spreadsheet or create a new one?")
            btn_append = box.addButton("Append to Existing", QMessageBox.ButtonRole.AcceptRole)
            btn_new = box.addButton("Create New File", QMessageBox.ButtonRole.ActionRole)
            box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
            box.exec()

            clicked_btn = box.clickedButton()
            file_path = None

            if clicked_btn == btn_append:
                file_path, _ = QFileDialog.getOpenFileName(self, "Select Existing Master Excel File", "", "Excel Files (*.xlsx)")
            elif clicked_btn == btn_new:
                file_path, _ = QFileDialog.getSaveFileName(self, "Create New Master Excel File", "Master_Trending.xlsx", "Excel Files (*.xlsx)")

            if file_path:
                generate_trending_report(self.nrt_df, Path(file_path))
                print(f"[UI] Trending report successfully processed at {file_path}")
        except Exception as e:
            print(f"[ERROR] Trending report generation failed: {e}")

    def generate_correlation(self):
        try:
            filetitle = get_correlation_report_title(self.nrt_df)
            file_path, _ = QFileDialog.getSaveFileName(self, "Save Correlation Report", f"{filetitle}.txt", "Text Files (*.txt)")
            if file_path:
                generate_correlation_report(self.nrt_df, self.nrt_files, self.erp_file, Path(file_path).parent)
        except Exception as e:
            print(f"[ERROR] Correlation report generation failed: {e}")

    def generate_plot(self):
        try:
            file_path, _ = QFileDialog.getSaveFileName(self, "Save Residual Plot", "Residuals.html", "HTML Files (*.html);;PNG Images (*.png)")
            if file_path:
                generate_residual_plot(self.nrt_df, Path(file_path))
                print(f"[UI] Plot successfully saved to {file_path}")
        except Exception as e:
            print(f"[ERROR] Plot generation failed: {e}")

    def export_csv(self):
        filetitle = get_correlation_report_title(self.nrt_df)
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Raw DataFrame", f"{filetitle}.csv", "CSV Files (*.csv)")
        if file_path:
            try:
                self.nrt_df.to_csv(file_path, index=False)
                print(f"[UI] Raw DataFrame exported to {file_path}")
            except Exception as e:
                print(f"[ERROR] CSV Export failed: {e}")

    def closeEvent(self, event):
        sys.stdout = sys.__stdout__
        super().closeEvent(event)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ClockDriftApp()
    window.show()
    sys.exit(app.exec())
