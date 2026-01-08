import tempfile
from plot import generate_plot
from parameters_gui import ParametersGUI
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QSpinBox,
                             QHBoxLayout, QComboBox, QPushButton, QLabel, QFrame)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl


class RFLinkToolGui(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RF Link Tool")
        self.setMinimumSize(1200, 800)

        # Main Widget and Layout
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.main_layout = QHBoxLayout(self.main_widget)

        # --- Left Control Panel (Sidebar) ---
        self.controls_wrapper = QVBoxLayout()

        # Data Rate Dropdown
        self.controls_wrapper.addWidget(QLabel("<b>Data Rate (bps):</b>"))
        self.data_rate_combo = QComboBox()
        self.data_rate_combo.addItems(["1024", "512", "256", "128", "64"])
        self.controls_wrapper.addWidget(self.data_rate_combo)

        # PA Mode Dropdown
        self.controls_wrapper.addWidget(QLabel("<b>PA Mode:</b>"))
        self.pa_mode_combo = QComboBox()
        self.pa_mode_combo.addItems(["High Power", "Low Power"])
        self.controls_wrapper.addWidget(self.pa_mode_combo)

        # Reference Altitude Numerical Input
        self.controls_wrapper.addWidget(QLabel("<b>Reference Line (km):</b>"))
        self.ref_alt= QSpinBox()
        self.ref_alt.setRange(500, 160000)
        self.ref_alt.setValue(140000)
        self.controls_wrapper.addWidget(self.ref_alt)

        # Spacer to push buttons to the bottom
        self.controls_wrapper.addStretch()

        # Control Buttons
        self.run_btn = QPushButton("Run Link Budget")
        self.run_btn.setMinimumHeight(40)
        self.run_btn.setStyleSheet("background-color: #2E7D32; color: black; font-weight: bold; font-size: 12pt;")
        self.run_btn.clicked.connect(self.run_script)
        self.run_btn.setToolTip("Execute the RF Link Budget Calculation with the selected parameters.")
        self.controls_wrapper.addWidget(self.run_btn)

        self.pause_btn = QPushButton("Pause Execution")
        self.pause_btn.setMinimumHeight(30)
        self.pause_btn.setStyleSheet("background-color: #ffff66; color: black; font-weight: bold; font-size: 12pt;")
        self.pause_btn.clicked.connect(lambda: print("Script Paused"))
        self.pause_btn.setToolTip("Pause the execution of the RF Link Budget Calculation.")
        self.controls_wrapper.addWidget(self.pause_btn)

        # Button to open the Parameters GUI
        self.params_btn= QPushButton("Edit RF Parameters")
        self.params_btn.setStyleSheet("background-color: #ffffff; color: black; font-weight: bold; font-size: 12pt;")
        self.params_btn.clicked.connect(self.open_parameters_gui)
        self.params_btn.setToolTip("Open the RF Parameters Configuration Window.")
        self.controls_wrapper.addWidget(self.params_btn)

        self.exit_btn = QPushButton("Exit Tool")
        self.exit_btn.setMinimumHeight(30)
        self.exit_btn.setStyleSheet("background-color: #ff0000; color: black; font-weight: bold; font-size: 12pt;")
        self.exit_btn.clicked.connect(self.close)
        self.exit_btn.setToolTip("Close the RF Link Tool application.")
        self.controls_wrapper.addWidget(self.exit_btn)

        # --- Right Display Area (The Plot Box) ---
        self.display_layout = QVBoxLayout()

        # The Browser Widget
        self.browser = QWebEngineView()

        # Optional: Add a visual border using a Container Frame
        self.plot_container = QFrame()
        self.plot_container.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        self.plot_container.setLineWidth(2)
        container_layout = QVBoxLayout(self.plot_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.addWidget(self.browser)

        self.display_layout.addWidget(self.plot_container)
        self.display_layout.setContentsMargins(0,0,0,0)
        self.display_layout.setSpacing(0)

        # Combine Sidebar and Display
        self.main_layout.addLayout(self.controls_wrapper, 1)
        self.main_layout.addLayout(self.display_layout, 10)
        self.main_layout.setContentsMargins(5,5,5,5)

        # Initialize default parameters
        self.open_parameters_gui(True)


    def open_parameters_gui(self, initialize= False):
        dialog= ParametersGUI(self, initialize)
        if dialog.exec_():  # This waits until the user clicks Save or Cancel
            # The user clicked Save
            self.saved_params = dialog.values


    def run_script(self):
            try:
                fig= generate_plot(self)

                style_fix = """
                    <style>
                        html, body { 
                            margin: 0; 
                            padding: 0; 
                            height: 100vh; 
                            width: 100vw; 
                            overflow: hidden; /* This kills the scrollbars */
                        }
                        .plotly-graph-div { 
                            height: 100vh !important; 
                            width: 100vw !important; 
                        }
                    </style>"""
                html_content= fig.to_html(include_plotlyjs=True, full_html=True, config={'responsive': True})
                html_content = html_content.replace(":focus-visible", ":focus")  # QtWebEngine CSS fix
                html_content = html_content.replace("<head>", f"<head>{style_fix}")
                html_content += """
                    <script>
                    window.addEventListener("resize", function() {
                        var gd = document.querySelector('.plotly-graph-div');
                        if (gd) Plotly.Plots.resize(gd);
                    });
                    </script>"""

                td, temp_path = tempfile.mkstemp(suffix=".html")

                with open(temp_path, "w", encoding="utf-8") as f:
                    f.write(html_content)

                self.browser.load(QUrl.fromLocalFile(temp_path))

            except Exception as e:
                print(f"Error: {e}")
