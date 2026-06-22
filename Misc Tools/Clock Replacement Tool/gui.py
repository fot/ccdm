import sys
from pathlib import Path
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QListWidget, 
                             QFileDialog, QTextEdit, QMessageBox)
from clock_processing import calculate_clock_drift


class ClockDriftApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Spacecraft Clock Correlation")
        self.resize(700, 550)
        self.erp_file = None
        self.nrt_files = []
        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # ERP Selection
        erp_layout = QHBoxLayout()
        self.btn_select_erp = QPushButton("Select .erp File")
        self.btn_select_erp.clicked.connect(self.select_erp_file)
        self.lbl_erp_path = QLabel("No ERP file selected.")
        self.lbl_erp_path.setStyleSheet("color: gray;")

        erp_layout.addWidget(self.btn_select_erp)
        erp_layout.addWidget(self.lbl_erp_path, stretch=1)
        main_layout.addLayout(erp_layout)

        # NRT Selection
        nrt_layout = QVBoxLayout()
        nrt_btn_layout = QHBoxLayout()
        self.btn_select_nrt = QPushButton("Select .nrt Files")
        self.btn_select_nrt.clicked.connect(self.select_nrt_files)
        self.btn_clear_nrt = QPushButton("Clear List")
        self.btn_clear_nrt.clicked.connect(self.clear_nrt_files)
        
        nrt_btn_layout.addWidget(self.btn_select_nrt)
        nrt_btn_layout.addWidget(self.btn_clear_nrt)
        nrt_btn_layout.addStretch()

        self.list_nrt_files = QListWidget()
        
        nrt_layout.addLayout(nrt_btn_layout)
        nrt_layout.addWidget(QLabel("Selected NRT Telemetry Files:"))
        nrt_layout.addWidget(self.list_nrt_files)
        main_layout.addLayout(nrt_layout)

        # Execution & Output
        self.btn_run = QPushButton("Calculate Clock Drift")
        self.btn_run.setMinimumHeight(40)
        self.btn_run.setStyleSheet("font-weight: bold;")
        self.btn_run.clicked.connect(self.run_calculation)
        main_layout.addWidget(self.btn_run)

        self.txt_output = QTextEdit()
        self.txt_output.setReadOnly(True)
        main_layout.addWidget(QLabel("Processing Output:"))
        main_layout.addWidget(self.txt_output)

    def select_erp_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Ephemeris File", "", "ERP Files (*.erp);;All Files (*.*)"
        )
        if file_path:
            self.erp_file = file_path
            self.lbl_erp_path.setText(Path(self.erp_file).name)
            self.lbl_erp_path.setStyleSheet("color: black;")
            self.log(f"Loaded ERP: {self.erp_file}")

    def select_nrt_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select NRT Telemetry Files", "", "NRT Files (*.nrt);;All Files (*.*)"
        )
        if files:
            for f in files:
                if f not in self.nrt_files:
                    self.nrt_files.append(f)
                    self.list_nrt_files.addItem(Path(f).name)
            self.log(f"Added {len(files)} NRT file(s).")

    def clear_nrt_files(self):
        self.nrt_files.clear()
        self.list_nrt_files.clear()
        self.log("NRT file list cleared.")

    def log(self, message):
        self.txt_output.append(message)
        QApplication.processEvents() # Keeps the GUI responsive during heavy math

    def run_calculation(self):
        if not self.erp_file:
            QMessageBox.warning(self, "Missing Data", "Please select an .erp file.")
            return
        if not self.nrt_files:
            QMessageBox.warning(self, "Missing Data", "Please select at least one .nrt file.")
            return

        try:
            # Run the physics pipeline and pass the UI's log function 
            # so we get live updates in the text box
            calculate_clock_drift(self.erp_file, self.nrt_files)
            self.log("Calculation Complete.")

        except Exception as e:
            self.log(f"Error during processing: {str(e)}")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ClockDriftApp()
    window.show()
    sys.exit(app.exec())
