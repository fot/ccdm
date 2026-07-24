import sys
import tempfile
import threading
from pathlib import Path
import plotly.graph_objs as go
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QLabel,
    QVBoxLayout, QHBoxLayout, QFileDialog, QSizePolicy,
    QTextEdit, QProgressBar
)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import Qt, QUrl, pyqtSignal, QObject, QThread
from PyQt5.QtGui import QMovie
from generate_plot import build_plot


class DataPoint:
    "A blank dataclass used to store data point attributes"

# -------------------------------------------------------
# WORKER SIGNAL WRAPPER
# -------------------------------------------------------
class WorkerSignals(QObject):
    finished = pyqtSignal(object)   # returns figure
    error = pyqtSignal(str)


# -------------------------------------------------------
# WORKER THREAD
# -------------------------------------------------------
class PlotWorker(QThread):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, gui):
        super().__init__()
        self.gui = gui
        self._cancel = False

    def run(self):
        try:
            if self._cancel:
                return
            fig = build_plot(self.gui)
            if self._cancel:
                return
            self.finished.emit(fig)
        except Exception as e:
            self.error.emit(str(e))

    def cancel(self):
        self._cancel = True

# -------------------------------------------------------
# MAIN GUI
# -------------------------------------------------------
class FileLoaderApp(QWidget):

    def __init__(self):
        super().__init__()
        self.selected_file = None
        self.worker = None
        self.signals = WorkerSignals()
        self.signals.finished.connect(self.plot_ready)
        self.signals.error.connect(self.plot_error)

        self.init_ui()

    # ---------------------------------------------------
    # LOGGING (Color-Coded Console)
    # ---------------------------------------------------
    def log(self, msg):
        if msg.startswith("[INFO]"):
            color = "#2ecc71"
        elif msg.startswith("[WARNING]"):
            color = "#f39c12"
        elif msg.startswith("[ERROR]"):
            color = "#e74c3c"
            msg = f"<b>{msg}</b>"
        elif msg.startswith("[SUCCESS]"):
            color = "#1abc9c"
        else:
            color = "white"

        html = f'<span style="color:{color};">{msg}</span>'
        self.console.append(html)

    # ---------------------------------------------------
    # UI SETUP
    # ---------------------------------------------------
    def init_ui(self):
        self.setWindowTitle("X_LIST Data Plotter")

        # Label / Select button
        self.label = QLabel("No file selected", self)
        self.btn_select = QPushButton("Select File")
        self.btn_select.clicked.connect(self.load_file)

        # Spinner (GIF)
        self.spinner = QLabel(self)
        self.spinner_movie = QMovie("loading_icon.gif")
        self.spinner.setMovie(self.spinner_movie)
        self.spinner.setAlignment(Qt.AlignCenter)
        self.spinner.setVisible(False)

        # Web view (Plot)
        self.plot_view = QWebEngineView()
        self.plot_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Console
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setFixedHeight(150)
        self.console.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: white;
                font-family: Consolas, monospace;
                font-size: 13px;
            }
        """)

        # Progress bar
        self.progress = QProgressBar()
        self.progress.setValue(0)

        # Buttons
        self.btn_run = QPushButton("Run")
        self.btn_run.clicked.connect(self.start_plot_thread)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.cancel_worker)

        self.btn_exit = QPushButton("Exit")
        self.btn_exit.clicked.connect(self.close)

        # Button styles
        self.btn_run.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #f1c40f;
                color: black;
                font-weight: bold;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #d4ac0d;
            }
        """)
        self.btn_exit.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
        """)

        # Layouts
        main = QVBoxLayout()
        top = QHBoxLayout()
        buttons = QHBoxLayout()

        top.addWidget(self.label)
        top.addWidget(self.btn_select)

        buttons.addStretch()
        buttons.addWidget(self.btn_run)
        buttons.addWidget(self.btn_cancel)
        buttons.addWidget(self.btn_exit)

        main.addLayout(top)
        main.addWidget(self.spinner)
        main.addWidget(self.plot_view, stretch=1)
        main.addWidget(self.progress)
        main.addWidget(self.console)
        main.addLayout(buttons)

        self.setLayout(main)

    # ---------------------------------------------------
    # File selection
    # ---------------------------------------------------
    def load_file(self):
        file, _ = QFileDialog.getOpenFileName(self, "Select ASVT Data File")
        if file:
            self.selected_file = file
            self.label.setText(f"Loaded: {file}")
            self.log(f"[INFO] File selected: {file}")

    # ---------------------------------------------------
    # START THREAD
    # ---------------------------------------------------
    def start_plot_thread(self):
        if not self.selected_file:
            self.log("[ERROR] No file selected.")
            return

        self.log("[INFO] Starting plot generation...")

        self.spinner.setVisible(True)
        self.spinner_movie.start()
        self.progress.setValue(5)

        # Use QThread-based worker
        self.worker = PlotWorker(self)
        self.worker.finished.connect(self.plot_ready)
        self.worker.error.connect(self.plot_error)
        self.worker.start()

    # ---------------------------------------------------
    # CANCEL THREAD
    # ---------------------------------------------------
    def cancel_worker(self):
        if self.worker:
            self.worker.cancel()
            self.worker.wait()  # ensures the thread stops safely
            self.log("[WARNING] Operation cancelled.")
            self.spinner_movie.stop()
            self.spinner.setVisible(False)
            self.progress.setValue(0)

    # ---------------------------------------------------
    # WORKER FINISHED
    # ---------------------------------------------------
    def plot_ready(self, fig):
        self.log("[SUCCESS] Plot generated.")

        # Delete previous temp file if it exists
        if hasattr(self, 'current_temp_file') and self.current_temp_file:
            try:
                Path(self.current_temp_file).unlink()
            except Exception:
                pass

        # Create a new temp file
        fd, temp_path = tempfile.mkstemp(suffix=".html")
        self.current_temp_file = temp_path  # store reference for cleanup next time

        # Generate full HTML with embedded JS
        html_content = fig.to_html(include_plotlyjs=True, full_html=True)
        html_content = html_content.replace(":focus-visible", ":focus")  # QtWebEngine CSS fix

        # Append auto-resize JS
        html_content += """
        <script>
        window.addEventListener("resize", function() {
            var gd = document.querySelector('.plotly-graph-div');
            if (gd) Plotly.Plots.resize(gd);
        });
        </script>
        """

        # Write to disk
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        # Load into QWebEngineView
        self.plot_view.load(QUrl.fromLocalFile(temp_path))

        self.spinner_movie.stop()
        self.spinner.setVisible(False)
        self.progress.setValue(100)

    # ---------------------------------------------------
    # WORKER ERROR
    # ---------------------------------------------------
    def plot_error(self, msg):
        self.log(f"[ERROR] Failed to generate plot: {msg}")
        self.spinner_movie.stop()
        self.spinner.setVisible(False)
        self.progress.setValue(0)

# -------------------------------------------------------
# MAIN
# -------------------------------------------------------
def main():
    app = QApplication(sys.argv)
    window = FileLoaderApp()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()