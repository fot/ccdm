import sys
import json
import shutil
import re
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QListWidget,
                             QFileDialog, QTextEdit, QMessageBox, QCheckBox,
                             QLineEdit, QGroupBox)
from PyQt6.QtGui import QAction, QTextCursor
from PyQt6.QtCore import Qt

# Local Imports
from workers import ConsoleStream, SFTPWorker, PipelineWorker, SFTP_CONFIG_PATH
from dialogs import (SFTPConfigDialog, JsonViewerDialog, MaudeDialog, 
                     BinaryExportDialog, ErpSourceDialog, NrtSourceDialog)
from binary_convert import convert_dis_file, convert_dat_file
from reports import (generate_trending_report, generate_correlation_report,
                     get_correlation_report_title, update_html_table)
from plots import generate_residual_plot


class ClockDriftApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Clock Correlation Tool")
        self.resize(950, 750)

        self.erp_file = None
        self.nrt_files = []
        self.maude_range = None
        self.nrt_df = None
        self.base_out_dir = ""
        self.out_dir = ""
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

        action_select_nrt = QAction("Add Telemetry...", self)
        action_select_nrt.triggered.connect(self.open_nrt_dialog)
        file_menu.addAction(action_select_nrt)

        action_select_erp = QAction("Select .erp File...", self)
        action_select_erp.triggered.connect(self.open_erp_dialog)
        file_menu.addAction(action_select_erp)

        file_menu.addSeparator()
        action_exit = QAction("Exit", self)
        action_exit.triggered.connect(self.close)
        file_menu.addAction(action_exit)

        settings_menu = menubar.addMenu("Settings")
        action_sftp_settings = QAction("SFTP Configuration...", self)
        action_sftp_settings.triggered.connect(self.open_sftp_settings)
        settings_menu.addAction(action_sftp_settings)

        view_menu = menubar.addMenu("View")
        for f in ["constants.json", "calibration_data.json", "dsn_data.json"]:
            act = QAction(f, self)
            act.triggered.connect(lambda checked, name=f: self.view_calibration_file(name))
            view_menu.addAction(act)

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(6)

        # INPUT BLOCK 
        input_group_layout = QVBoxLayout()
        input_group_layout.setContentsMargins(0, 0, 0, 0)
        input_group_layout.setSpacing(8)
        input_group_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Active Ephemeris Row
        erp_layout = QHBoxLayout()
        erp_layout.setContentsMargins(0, 0, 0, 0)

        self.lbl_erp_path = QLabel("No ERP file selected.")
        self.lbl_erp_path.setStyleSheet("color: gray; font-style: italic;")

        erp_layout.addWidget(QLabel("<b>Active Ephemeris:</b>"))
        erp_layout.addWidget(self.lbl_erp_path)
        erp_layout.addStretch()
        input_group_layout.addLayout(erp_layout)

        # Active Telemetry Queue Box
        nrt_layout = QVBoxLayout()
        nrt_layout.setContentsMargins(0, 0, 0, 0)
        nrt_layout.setSpacing(2)
        
        nrt_layout.addWidget(QLabel("<b>Active Telemetry Queue (NRT / MAUDE):</b>"))
        
        self.list_nrt_files = QListWidget()
        self.list_nrt_files.setMinimumHeight(160)
        self.list_nrt_files.setMaximumHeight(160)
        nrt_layout.addWidget(self.list_nrt_files)
        input_group_layout.addLayout(nrt_layout)
        
        main_layout.addLayout(input_group_layout)

        # Run Button & Legacy Mode Block
        run_layout = QHBoxLayout()
        run_layout.setContentsMargins(0, 0, 0, 0)
        
        self.chk_legacy = QCheckBox("Legacy Mode")
        self.chk_legacy.stateChanged.connect(self.toggle_legacy_mode)
        run_layout.addWidget(self.chk_legacy, stretch=1)

        self.btn_run = QPushButton("Execute Clock Correlation")
        self.btn_run.setMinimumHeight(40)
        self.btn_run.setEnabled(False)
        self.btn_run.setStyleSheet("font-weight: bold; font-size: 14px; background-color: #8e44ad; color: white;")
        self.btn_run.clicked.connect(self.run_calculation)
        run_layout.addWidget(self.btn_run, stretch=3)
        
        main_layout.addLayout(run_layout)

        # POST-PROCESSING UI BLOCK
        self.output_group = QGroupBox("Output Generation & Post-Processing")
        output_main_layout = QVBoxLayout()

        # Output Directory Row
        out_dir_layout = QHBoxLayout()
        self.txt_out_dir = QLineEdit()
        self.txt_out_dir.setPlaceholderText("Output directory required before generation...")
        self.txt_out_dir.setReadOnly(True)
        self.btn_out_dir = QPushButton("Browse...")
        self.btn_out_dir.clicked.connect(self.select_output_directory)
        
        out_dir_layout.addWidget(QLabel("Output Directory:"))
        out_dir_layout.addWidget(self.txt_out_dir)
        out_dir_layout.addWidget(self.btn_out_dir)
        output_main_layout.addLayout(out_dir_layout)

        # Individual Outputs Row
        output_row1 = QHBoxLayout()
        self.btn_binaries = QPushButton("Export Binary DBs")
        self.btn_binaries.clicked.connect(self.export_binaries)

        self.btn_trend = QPushButton("Trending Report")
        self.btn_trend.clicked.connect(self.generate_trending)

        self.btn_corr = QPushButton("Correlation Report")
        self.btn_corr.clicked.connect(self.generate_correlation)

        self.btn_plot = QPushButton("Residual Plot")
        self.btn_plot.clicked.connect(self.generate_plot)

        self.btn_html_table = QPushButton("HTML Table")
        self.btn_html_table.clicked.connect(self.update_html_record_table)

        self.btn_csv = QPushButton("Export CSV")
        self.btn_csv.clicked.connect(self.export_csv)

        output_row1.addWidget(self.btn_binaries)
        output_row1.addWidget(self.btn_trend)
        output_row1.addWidget(self.btn_corr)
        output_row1.addWidget(self.btn_plot)
        output_row1.addWidget(self.btn_html_table)
        output_row1.addWidget(self.btn_csv)

        # Batch Run Row
        output_row2 = QHBoxLayout()
        self.btn_run_all = QPushButton("Run All Reports (Exclude CSV)")
        self.btn_run_all.setMinimumHeight(30)
        self.btn_run_all.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold;")
        self.btn_run_all.clicked.connect(self.run_all_outputs)
        output_row2.addWidget(self.btn_run_all)

        output_main_layout.addLayout(output_row1)
        output_main_layout.addLayout(output_row2)
        self.output_group.setLayout(output_main_layout)
        
        self.output_buttons = [self.btn_binaries, self.btn_trend, self.btn_corr,
                               self.btn_plot, self.btn_html_table, self.btn_csv,
                               self.btn_run_all, self.btn_out_dir]

        for btn in self.output_buttons:
            btn.setEnabled(False) 

        main_layout.addWidget(self.output_group)

        # Console Block
        main_layout.addWidget(QLabel("<b>Console Output:</b>"))
        self.txt_output = QTextEdit()
        self.txt_output.setReadOnly(True)
        self.txt_output.setStyleSheet("font-family: Consolas, monospace; background-color: #1e1e1e; color: #d4d4d4;")
        
        main_layout.addWidget(self.txt_output, stretch=1)

    def check_ready_state(self):
        has_erp = self.erp_file is not None
        has_data = len(self.nrt_files) > 0 or self.maude_range is not None
        if has_erp and has_data:
            self.btn_run.setEnabled(True)
        else:
            self.btn_run.setEnabled(False)

    def check_output_ready_state(self):
        if self.nrt_df is not None and (self.out_dir == ""):
            self.btn_out_dir.setEnabled(True)
        elif self.nrt_df is not None and (self.out_dir != ""):
            for btn in self.output_buttons:
                btn.setEnabled(True)
        else:
            for btn in self.output_buttons:
                btn.setEnabled(False)

    def toggle_legacy_mode(self):
        self.legacy_mode = self.chk_legacy.isChecked()
        
    def open_sftp_settings(self):
        dialog = SFTPConfigDialog(self)
        dialog.exec()

    def select_output_directory(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if dir_path:
            self.base_out_dir = dir_path
            self.setup_run_output_directory()

    def setup_run_output_directory(self):
        if not self.base_out_dir:
            return

        now = datetime.now(timezone.utc)
        yy_str = now.strftime("%y")
        jday_str = now.strftime("%j")
        start_str = jday_str
        end_str = jday_str

        if self.nrt_df is not None:
            try:
                time_col = None
                for col in ['time', 'UTC', 'DateTime', 'date', 'timestamp']:
                    if col in self.nrt_df.columns:
                        time_col = col
                        break
                if time_col:
                    t_min = pd.to_datetime(self.nrt_df[time_col]).min()
                    t_max = pd.to_datetime(self.nrt_df[time_col]).max()
                elif isinstance(self.nrt_df.index, pd.DatetimeIndex):
                    t_min = self.nrt_df.index.min()
                    t_max = self.nrt_df.index.max()
                else:
                    t_min = pd.to_datetime(self.nrt_df.iloc[:, 0]).min()
                    t_max = pd.to_datetime(self.nrt_df.iloc[:, 0]).max()
                
                yy_str = t_min.strftime("%y")
                start_str = t_min.strftime("%j")
                end_str = t_max.strftime("%j")
            except Exception:
                pass

        sub_dir_name = f"rclkout_{yy_str}_{start_str}_{end_str}"
        sub_path = Path(self.base_out_dir) / sub_dir_name
        sub_path.mkdir(parents=True, exist_ok=True)
        
        self.out_dir = str(sub_path)
        self.txt_out_dir.setText(self.out_dir)
        print(f"[UI] Output Subdirectory created: {self.out_dir}")
        self.check_output_ready_state()

    def open_erp_dialog(self):
        dialog = ErpSourceDialog(self)
        if dialog.exec():
            if dialog.selection == 'local':
                self.select_erp_file_local()
            elif dialog.selection == 'sftp':
                self.pull_erp_sftp()

    def select_erp_file_local(self):
        default_dir = Path("//noodle/fot/engineering/ccdm/Clock_Timing/ERPFiles")
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Ephemeris File", str(default_dir), "ERP Files (*.erp);;All Files (*.*)")
        if file_path:
            self.erp_file = file_path
            self.lbl_erp_path.setText(Path(self.erp_file).name)
            self.lbl_erp_path.setStyleSheet("color: white; font-weight: bold;")
            print(f"[UI] Loaded Local Ephemeris: {self.erp_file}")
            self.check_ready_state()

    def pull_erp_sftp(self):
        if not SFTP_CONFIG_PATH.exists():
            QMessageBox.warning(self, "Error", "SFTP Config not found. Please configure in Settings.")
            return

        with open(SFTP_CONFIG_PATH, 'r') as f:
            cfg = json.load(f)

        # UI label update for loading state
        self.lbl_erp_path.setText("Downloading from Lucky...")
        self.lbl_erp_path.setStyleSheet("color: #f39c12; font-weight: bold; font-style: italic;")

        erp_dest = Path("//noodle/fot/engineering/ccdm/Clock_Timing/ERPFiles")
        self.worker_erp = SFTPWorker(cfg.get('remote_erp_dir', ''), '.erp', dest_dir=erp_dest)

        self.worker_erp.log.connect(self.append_to_console)
        self.worker_erp.finished.connect(self.on_erp_sftp_success)
        self.worker_erp.error.connect(self.on_erp_sftp_error)
        self.worker_erp.start()

    def on_erp_sftp_success(self, local_path):
        self.erp_file = local_path
        self.lbl_erp_path.setText(f"(SFTP) {Path(self.erp_file).name}")
        self.lbl_erp_path.setStyleSheet("color: #2ecc71; font-weight: bold;")
        print(f"[UI] SFTP Loaded Ephemeris: {self.erp_file}")
        self.check_ready_state()

    def on_erp_sftp_error(self, err):
        self.lbl_erp_path.setText("SFTP Download Failed.")
        self.lbl_erp_path.setStyleSheet("color: #e74c3c; font-weight: bold; font-style: italic;")
        QMessageBox.critical(self, "SFTP Error", err)

    def open_nrt_dialog(self):
        dialog = NrtSourceDialog(self)
        if dialog.exec():
            if dialog.selection == 'local':
                self.select_nrt_files()
            elif dialog.selection == 'maude':
                self.open_maude_dialog()

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

        print("[UI] Initializing Clock Correlation in background thread...")
        if self.legacy_mode:
            print("[UI] Execution configured for Legacy Mode overrides.")

        self.worker = PipelineWorker(self.erp_file, self.nrt_files, self.legacy_mode)
        self.worker.finished.connect(self.on_calculation_finished)
        self.worker.error.connect(self.on_calculation_error)
        self.worker.start()

    def on_calculation_finished(self, nrt_df):
        self.nrt_df = nrt_df
        print("\n[UI] Clock Correlation completed successfully.")
        self.btn_run.setEnabled(True)

        self.check_output_ready_state()

        if self.base_out_dir:
            self.setup_run_output_directory()
        else:
            print("[UI] Waiting for Output Directory to be selected to enable generation buttons.")

    def on_calculation_error(self, err_msg):
        print(f"\n[ERROR] Clock Correlation halted due to exception:\n{err_msg}")
        self.btn_run.setEnabled(True)

    def export_binaries(self):
        print("[UI] Prompting for Binary DB base files...")
        dialog = BinaryExportDialog(self)
        if dialog.exec():
            print("[UI] Initiating Binary Database Export...")
            try:
                out_path = Path(self.out_dir)

                def get_incremented_clkhst_name(filepath):
                    p = Path(filepath)
                    match = re.match(r"(CLKHST_)(\d+)", p.stem, re.IGNORECASE)
                    if match:
                        prefix = match.group(1).upper()
                        num = int(match.group(2))
                        return f"{prefix}{num + 1}{p.suffix.upper()}"
                    return f"NEW_{p.name}"

                # Process .DIS file
                if dialog.base_dis:
                    dest_dis = out_path / get_incremented_clkhst_name(dialog.base_dis)
                    shutil.copy(dialog.base_dis, dest_dis)
                    convert_dis_file(self.nrt_df, inputdir=str(dialog.base_dis), outputdir=str(dest_dis))
                    print(f"[UI] Binary DB .DIS successfully exported to {dest_dis}")

                    if ".sftp_cache" in Path(dialog.base_dis).parts:
                        Path(dialog.base_dis).unlink(missing_ok=True)
                        print(f"[UI] Cleaned up temporary SFTP file: {Path(dialog.base_dis).name}")

                # Process .DAT file
                if dialog.base_dat:
                    dest_dat = out_path / get_incremented_clkhst_name(dialog.base_dat)
                    shutil.copy(dialog.base_dat, dest_dat)
                    convert_dat_file(self.nrt_df, inputdir=str(dialog.base_dat), outputdir=str(dest_dat))
                    print(f"[UI] Binary DB .DAT successfully exported to {dest_dat}")

                    if ".sftp_cache" in Path(dialog.base_dat).parts:
                        Path(dialog.base_dat).unlink(missing_ok=True)
                        print(f"[UI] Cleaned up temporary SFTP file: {Path(dialog.base_dat).name}")

            except Exception as e:
                print(f"[ERROR] Binary export failed: {e}")

    def generate_trending(self, autorun=False):
        trend_dir = Path("//noodle/fot/users/rhoover/Clock Tool Development Files")
        # trend_dir = Path("//noodle/fot/engineering/ccdm/Clock_Timing/Clock Rate Trending_files")

        try:
            if autorun:
                file_path = trend_dir / "Clock Rate Trending (Test).xlsx"
                # file_path = trend_dir / "Clock Rate Trending (Data Only).xlsx"
            else:
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
                    file_path, _ = QFileDialog.getOpenFileName(self, "Select Existing Master Excel File",
                                                               str(trend_dir), "Excel Files (*.xlsx)")
                elif clicked_btn == btn_new:
                    file_path, _ = QFileDialog.getSaveFileName(self, "Create New Master Excel File",
                                                               str(Path(trend_dir) / "Master_Trending.xlsx"),
                                                               "Excel Files (*.xlsx)")

            if file_path:
                generate_trending_report(self.nrt_df, Path(file_path))
                print(f"[UI] Trending report successfully processed at {file_path}")
        except Exception as e:
            print(f"[ERROR] Trending report generation failed: {e}")

    def generate_correlation(self, autorun=False):
        try:
            filetitle = get_correlation_report_title(self.nrt_df)

            if autorun:
                file_path = str(Path(self.out_dir) / f"{filetitle}.txt")
            else:
                file_path, _ = QFileDialog.getSaveFileName(self, "Save Correlation Report",
                                                           str(Path(self.out_dir) / f"{filetitle}.txt"),
                                                           "Text Files (*.txt)")

            if file_path:
                generate_correlation_report(self.nrt_df, self.nrt_files, self.erp_file, Path(file_path).parent)
            print(f"[UI] Correlation report successfully generated.")
        except Exception as e:
            print(f"[ERROR] Correlation report generation failed: {e}")

    def generate_plot(self, autorun=False):
        try:
            filetitle = get_correlation_report_title(self.nrt_df)

            if autorun:
                file_path = str(Path(self.out_dir) / f"{filetitle}_residuals.png")
            else:
                file_path, _ = QFileDialog.getSaveFileName(self, "Save Residual Plot",
                                                           str(Path(self.out_dir) / f"{filetitle}_residuals.png"),
                                                           "PNG Images (*.png);;HTML Files (*.html)")

            if file_path:
                generate_residual_plot(self.nrt_df, Path(file_path))
                print(f"[UI] Plot successfully saved to {file_path}")
        except Exception as e:
            print(f"[ERROR] Plot generation failed: {e}")

    def update_html_record_table(self):
        try:
            now = datetime.now(timezone.utc)
            # inputpath = Path("//noodle/vweb/fot_web/eng/subsystems/ccdm/Clock_Rate")
            inputpath = Path("//noodle/fot/users/rhoover/Clock Tool Development Files")
            update_html_table(self.nrt_df, inputpath / f"Clock_Correlation{now.strftime("%Y")}.htm")
            print(f"[UI] HTML Table successfully updated.")
        except Exception as e:
            print(f"[ERROR] HTML table update failed: {e}")

    def run_all_outputs(self):
        try:
            print(f"\n[UI] Executing batch output generation to {Path(self.out_dir)}...\n")

            self.export_binaries() # Run Export Binaries
            self.generate_trending(autorun=True) # Run Trending XLSX Export
            self.generate_correlation(autorun=True) # Run Correlation Report
            self.generate_plot(autorun=True) # Run Residual Plot
            self.update_html_record_table() # Run HTML Table Update

            print("[UI] Batch output generation complete.")
        except Exception as e:
            print(f"[ERROR] Batch output execution failed: {e}")

    def export_csv(self):
        filetitle = get_correlation_report_title(self.nrt_df)
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Raw DataFrame", str(Path(self.out_dir) / f"{filetitle}.csv"), "CSV Files (*.csv)")
        if file_path:
            try:
                self.nrt_df.to_csv(file_path, index=False)
                print(f"[UI] Raw DataFrame exported to {file_path}")
            except Exception as e:
                print(f"[ERROR] CSV Export failed: {e}")

    def closeEvent(self, event):
        sys.stdout = sys.__stdout__
        super().closeEvent(event)
