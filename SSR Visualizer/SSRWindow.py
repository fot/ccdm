"""
Module to create a GUI for SSR Pointer Visualization.
Handles user inputs, continuous updating, and dynamic image rendering.
"""

import sys
from generate_image import generate_image
from PyQt5 import QtWidgets, QtGui, QtCore


class QTextEditLogger(QtCore.QObject):
    """
    A logger that redirects standard output (stdout/stderr) to a QTextEdit widget.
    """
    def __init__(self, text_edit):
        super().__init__()
        self.text_edit = text_edit

    def write(self, msg):
        """Write a message to the QTextEdit widget and force a GUI update."""
        if msg.strip():
            self.text_edit.append(msg)
            self.text_edit.moveCursor(QtGui.QTextCursor.End)
            QtWidgets.QApplication.processEvents()

    def flush(self):
        """Dummy flush method required by some libraries when replacing sys.stdout"""
        pass


class SSRPointerWindow(QtWidgets.QWidget):
    """
    This class implements a user-interface for a set of tools that generate
    a plot to visualize SSR pointers.

    Usage:
        Instantiate this class and show() it within a QApplication loop.
    """
    def __init__(self, parent=None):
        """
        Initializes the SSR Pointer Tool window, layouts, and all internal widgets.
        """
        super().__init__(parent)

        # --- Window Setup ---
        self.setWindowTitle("SSR Visualizer")
        self.redBackground = "QPushButton { background: red }"
        self.greenBackground = "QPushButton { background: lightgreen }"

        # --- Screen Scaling ---
        screen = QtGui.QGuiApplication.primaryScreen()
        scaling_factor = screen.logicalDotsPerInch() / 96.0
        screen_width = screen.geometry().width()
        screen_height = screen.geometry().height()

        self.setStyleSheet("""
            QWidget { font-size: 11pt; }
            QPushButton { font-size: 12pt; font-weight: bold; }""")

        self.resize(QtCore.QSize(
            int((screen_width / scaling_factor) / 3.8),
            int((screen_height / scaling_factor) / 1.5)))

        # --- Layout Initialization ---
        self.layout = QtWidgets.QGridLayout()
        self.layout.setRowStretch(3, 3)
        self.layout.setRowStretch(4, 1)

        # --- State Variables ---
        self.selectedssr = None
        self.selectedchannel = None
        self.selectedquery = None
        self.plot_rgba = None
        self.display_mode = "pointers"

        # --- Timer ---
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.run_ssr)

        # --- Build GUI Components ---
        self._build_ssr_selection()           
        self._build_channel_selection()       
        self._build_continuous_checkbox()     
        self._build_toggle_display_checkbox() 
        self._build_query_rate()              
        self._build_image_output()            
        self._build_console()                 
        self._build_run_button()              
        self._build_quit_button()             
        self._apply_gui_formatting()


    # ---------------------------------------------------------
    # Event Handlers
    # ---------------------------------------------------------
    def selected_ssr(self, text):
        self.selectedssr = text

    def selected_channel(self, text):
        self.selectedchannel = text

    def selected_query(self, text):
        self.selectedquery = float(text[:-3])

    def run_ssr(self):
        """Handle the Run button click event and timer execution."""
        self.consoleoutput.clear() 
        generate_image(self)
        self._build_image_output()

        if self.plot_rgba is None:
            print(f"  - (Error): Cannot generate plot.\n")

    def toggle_continuous(self, checked):
        if checked:
            self.timer.start(30000) 
            self.run_ssr()          
        else:
            self.timer.stop()
            print("  - Continuous mode DISABLED.\n")

    def toggle_display(self, checked):
        self.display_mode = "time" if checked else "pointers"

    def quit_event(self):
        sys.exit(1)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Use a single-shot timer to wait 100ms after the resize stops
        QtCore.QTimer.singleShot(100, self._build_image_output)

    # ---------------------------------------------------------
    # UI Builder Methods
    # ---------------------------------------------------------
    def _build_ssr_selection(self):
        self.ssrlabel = QtWidgets.QLabel("Select SSR:")
        self.ssrlabel.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignCenter)
        self.ssrlabel.setMinimumHeight(30)
        self.layout.addWidget(self.ssrlabel, 1, 0)
        self.ssrcombobox = QtWidgets.QComboBox()
        self.ssrcombobox.addItems(["A", "B"])
        self.ssrcombobox.setEditable(True)
        self.ssrcombobox.setMinimumHeight(30)
        line_edit = self.ssrcombobox.lineEdit()
        self.line_edit_align(line_edit)
        self.layout.addWidget(self.ssrcombobox, 1, 1)
        self.selectedssr = self.ssrcombobox.currentText()
        self.ssrcombobox.currentTextChanged.connect(self.selected_ssr)

    def _build_channel_selection(self):
        self.channellabel = QtWidgets.QLabel("Channel:")
        self.channellabel.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignCenter)
        self.channellabel.setMinimumHeight(30)
        self.layout.addWidget(self.channellabel, 1, 2)
        self.channelcombobox = QtWidgets.QComboBox()
        self.channelcombobox.addItems(["Flight", "ASVT"])
        self.channelcombobox.setEditable(True)
        self.channelcombobox.setMinimumHeight(30)
        line_edit = self.channelcombobox.lineEdit()
        self.line_edit_align(line_edit)
        self.layout.addWidget(self.channelcombobox, 1, 3)
        self.selectedchannel = self.channelcombobox.currentText()
        self.channelcombobox.currentTextChanged.connect(self.selected_channel)

    def _build_continuous_checkbox(self):
        self.continuous_checkbox = QtWidgets.QCheckBox("Continuous")
        self.continuous_checkbox.setMinimumHeight(30)
        self.layout.addWidget(self.continuous_checkbox, 2, 0,
            alignment = QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.continuous_checkbox.toggled.connect(self.toggle_continuous)

    def _build_toggle_display_checkbox(self):
        self.display_checkbox = QtWidgets.QCheckBox("Pointer/Time")
        self.display_checkbox.setMinimumHeight(30)
        self.layout.addWidget(self.display_checkbox, 2, 1,
            alignment=QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.display_checkbox.toggled.connect(self.toggle_display)

    def _build_query_rate(self):
        self.querylabel = QtWidgets.QLabel("Query Time:")
        self.querylabel.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignCenter)
        self.querylabel.setMinimumHeight(30)
        self.layout.addWidget(self.querylabel, 2, 2)
        self.querycombobox = QtWidgets.QComboBox()
        self.querycombobox.addItems(["18.6 hr", "24 hr", "48 hr"])
        self.querycombobox.setEditable(True)
        self.querycombobox.setMinimumHeight(30)
        line_edit = self.querycombobox.lineEdit()
        self.line_edit_align(line_edit)
        self.layout.addWidget(self.querycombobox, 2, 3)
        self.selectedquery = float(self.querycombobox.currentText()[:-3])
        self.querycombobox.currentTextChanged.connect(self.selected_query)

    def line_edit_align(self, line_edit):
        """Helper to align line edits and make them read-only."""
        line_edit.setAlignment(QtCore.Qt.AlignCenter)
        line_edit.setReadOnly(True)

    def _build_image_output(self):
        """
        Renders the Matplotlib raw RGBA pixel array into the GUI QLabel.
        """
        # Initialize the QLabel if it doesn't exist yet
        if not hasattr(self, 'image_label'):
            self.image_label = QtWidgets.QLabel("Waiting for data...")
            self.image_label.setAlignment(QtCore.Qt.AlignCenter)
            self.image_label.setMinimumSize(100, 100)
            self.image_label.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                           QtWidgets.QSizePolicy.Expanding)
            self.layout.addWidget(self.image_label, 3, 0, 1, 4)

        # Check if we have valid pixel data from Matplotlib
        if hasattr(self, 'plot_rgba') and self.plot_rgba is not None:
            try:
                # Deep Copy the array to ensure stable memory for QImage
                image_data = self.plot_rgba.copy()
                height, width, channels = image_data.shape
                bytes_per_line = channels * width
                qimage = QtGui.QImage(
                    image_data.data, 
                    width, 
                    height, 
                    bytes_per_line, 
                    QtGui.QImage.Format_RGBA8888
                )

                # Force a deep copy into the QImage so it is safe to discard the numpy array
                qimage = qimage.copy()
                pixmap = QtGui.QPixmap.fromImage(qimage)

                # PyQt5 Enum Fix: KeepAspectRatio and SmoothTransformation
                scaled_pixmap = pixmap.scaled(
                    self.image_label.size(), 
                    QtCore.Qt.KeepAspectRatio, 
                    QtCore.Qt.SmoothTransformation
                )
                self.image_label.setPixmap(scaled_pixmap)

            except Exception as e:
                print(f"Error displaying native image: {e}")
                self.image_label.setText(f"Error generating image:\n{e}")
        else:
            # Fallback if no data has been generated yet
            self.image_label.setText("Waiting for data...")

    def _build_console(self):
        self.consoleoutput = QtWidgets.QTextEdit()
        self.consoleoutput.setReadOnly(True)
        self.consoleoutput.setLineWrapMode(QtWidgets.QTextEdit.NoWrap)
        self.consoleoutput.setFont(QtGui.QFont("Courier", 10))
        self.consoleoutput.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Expanding)
        self.layout.addWidget(self.consoleoutput, 4, 0, 1, 4)
        sys.stdout = QTextEditLogger(self.consoleoutput)
        sys.stderr = QTextEditLogger(self.consoleoutput)

    def _build_run_button(self):
        self.runssrbutton = QtWidgets.QPushButton("Run SSR Visualizer")
        self.runssrbutton.setMinimumHeight(40)
        self.runssrbutton.setStyleSheet(self.greenBackground)
        runfont = self.runssrbutton.font()
        runfont.setBold(True)
        self.runssrbutton.setFont(runfont)
        self.layout.addWidget(self.runssrbutton, 5, 0, 1, 3)
        self.runssrbutton.clicked.connect(self.run_ssr)

    def _build_quit_button(self):
        self.quitbutton = QtWidgets.QPushButton("Quit")
        self.quitbutton.setMinimumHeight(40)
        self.quitbutton.setStyleSheet(self.redBackground)
        quitfont = self.quitbutton.font()
        quitfont.setBold(True)
        self.quitbutton.setFont(quitfont)
        self.layout.addWidget(self.quitbutton, 5, 3)
        self.quitbutton.clicked.connect(self.quit_event)

    def _apply_gui_formatting(self):
        self.textdisplay = QtWidgets.QTextEdit()
        self.textdisplay.setReadOnly(True)
        self.textdisplay.setLineWrapMode(QtWidgets.QTextEdit.NoWrap)
        self.textdisplay.moveCursor(QtGui.QTextCursor.End)
        font = QtGui.QFont("Courier", 10, QtGui.QFont.Bold)
        self.textdisplay.setFont(font)
        self.setLayout(self.layout)
