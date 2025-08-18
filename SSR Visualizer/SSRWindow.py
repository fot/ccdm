from PyQt5 import QtWidgets, QtGui, QtCore
from generate_image import generate_image
import sys
from tempfile import NamedTemporaryFile
import os


class QTextEditLogger(QtCore.QObject):
    """A logger that writes to a QTextEdit widget."""
    def __init__(self, text_edit):
        super().__init__()
        self.text_edit = text_edit

    def write(self, msg):
        """Write a message to the QTextEdit widget."""
        if msg.strip():
            self.text_edit.append(msg)
            self.text_edit.moveCursor(QtGui.QTextCursor.End)

    def flush(self):
        """Flush method to comply with file-like interface."""
        pass


class SSRPointerWindow(QtWidgets.QWidget):
    """
    This class implements a user-interface for a set of tools that generate
    a plot to visuallize SSR pointers.

    Usage:
        To Do
    """
    def __init__ ( self, parent=None ):
        """
        Initializes the SSR Pointer Tool window and its widgets.
        Widgets and layout:
            - Run SSR Pointer Tool button (row 0, columns 0-3): Starts the SSR pointer visualization.
            - Image output area (row 1, columns 0-3): Displays generated SSR pointer plots.
            - SSR Selection Combo Box (row 2, columns 0-3): Allows selection between SSR-A and SSR-B pointer sets.
            - Console output area (row 2, columns 0-3): Shows log and console messages.
            - Quit button (row 3, column 3): Closes the interface.
            - Additional read-only text display for formatted output.
        Note:
            The widgets are arranged using a QGridLayout, with most controls spanning all columns for a wide interface.
        """
        QtWidgets.QWidget.__init__(self,parent)
        self.redBackground =  "QPushButton { background: red }"
        self.greenBackground= "QPushButton { background: lightgreen }"
        self.setWindowTitle ("SSR Pointer Tool (Ver 1.0)")
        self.resize(QtCore.QSize(800,1100))
        self.layout= QtWidgets.QGridLayout()
        self.plot= None

#       # Build GUI
        self.build_run_button()    # row 0, columns 0-3
        self.build_ssr_selection() # row 1, columns 0-3
        self.build_image_output()  # row 2, columns 0-3
        self.build_console()       # row 3, columns 0-3
        self.build_quit_button()   # row 4, column 3
        self.gui_formatting()

        # Button clicked actions
        self.runSSRButton.clicked.connect(self.runSSR)
        self.quitButton.clicked.connect(self.quitSlot)

    def build_run_button(self):
        "build the run button"
        self.runSSRButton = QtWidgets.QPushButton("Run SSR Pointer Tool")
        self.runSSRButton.setToolTip("Run the SSR Pointer Tool to generate a plot of SSR pointers")
        self.runSSRButton.setMinimumHeight(40)
        runFont= self.runSSRButton.font()
        runFont.setBold(True)
        runFont.setPointSize(2 * runFont.pointSize())
        self.runSSRButton.setFont(runFont)
        self.runSSRButton.setStyleSheet(self.greenBackground)
        self.layout.addWidget(self.runSSRButton, 0, 0, 1, 4)

    def build_ssr_selection(self):
        "build the SSR selection combo box"
        # Section label
        self.ssrLabel = QtWidgets.QLabel("Select SSR:")
        self.ssrLabel.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.ssrLabel.setMinimumHeight(30)
        self.layout.addWidget(self.ssrLabel, 1, 0, 1, 1)

        # SSR selection combo box
        self.ssrComboBox = QtWidgets.QComboBox()
        self.ssrComboBox.addItems(["A", "B"])
        self.ssrComboBox.setToolTip("Select an SSR pointer set to visualize")
        self.ssrComboBox.setMinimumHeight(30)
        self.layout.addWidget(self.ssrComboBox, 1, 1, 1, 2)
        self.selectedSSR = self.ssrComboBox.currentText()
        self.ssrComboBox.currentTextChanged.connect(self.onSSRChanged)

    def build_image_output(self):
        "build the image output area"
        self.imageOutput = QtWidgets.QLabel()
        self.imageOutput.setAlignment(QtCore.Qt.AlignCenter)
        self.imageOutput.setMinimumHeight(int(self.height() * 0.70))
        self.imageOutput.setStyleSheet("border: 1px solid gray; background: #f0f0f0;")
        if self.plot is not None:
            self.imageOutput.setPixmap(
                QtGui.QPixmap(self.plot_path).scaled(int(self.height() * 0.70),
                                                               int(self.height() * 0.70)))
        self.layout.addWidget(self.imageOutput, 2, 0, 1, 4)

    def build_console(self):
        "build the console output area"
        self.consoleOutput= QtWidgets.QTextEdit()
        self.consoleOutput.setReadOnly(True)
        self.consoleOutput.setLineWrapMode(QtWidgets.QTextEdit.NoWrap)
        self.consoleOutput.setFont(QtGui.QFont("Courier", 10))
        self.consoleOutput.setMinimumHeight(int(self.height() * 0.10))
        self.layout.addWidget(self.consoleOutput, 3, 0, 1, 4)
        sys.stdout= QTextEditLogger(self.consoleOutput)
        sys.stderr= QTextEditLogger(self.consoleOutput)

    def build_quit_button(self):
        "build the quit button"
        self.quitButton = QtWidgets.QPushButton('Quit')
        self.quitButton.setToolTip('Close New Beat Interface')
        self.quitButton.setStyleSheet(self.redBackground)
        self.layout.addWidget(self.quitButton, 4, 3)

    def gui_formatting(self):
        "formatting for the GUI"
        self.textDisplay = QtWidgets.QTextEdit()
        self.textDisplay.setReadOnly ( True )
        self.textDisplay.setLineWrapMode(QtWidgets.QTextEdit.NoWrap)
        self.textDisplay.moveCursor (QtGui.QTextCursor.End)
        font = QtGui.QFont ("Courier", 10, QtGui.QFont.Bold)
        self.textDisplay.setFont (font)
        self.setLayout(self.layout)

    def onSSRChanged(self, text):
        """Handle changes in the SSR selection combo box."""
        self.selectedSSR = text

    def runSSR(self):
        self.plot= generate_image(self)

        if self.plot is not None:
            with NamedTemporaryFile(suffix= ".jpg", delete= False) as tmp_file:
                self.plot_path= tmp_file.name
                self.plot.write_image(self.plot_path, scale=2)
            self.build_image_output()
            os.remove(tmp_file.name)
        else:
            self.build_image_output()
            print(f"  - SSR-{self.selectedSSR} is OFF, cannot generate plot.\n")

    def quitSlot(self):
        """Handle the quit button click event."""
        sys.exit(1)
