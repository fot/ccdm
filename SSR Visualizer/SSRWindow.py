"Module to create a GUI for SSR Pointer Visualization"

import sys
from tempfile import NamedTemporaryFile
import os
import tkinter as tk
from PyQt5 import QtWidgets, QtGui, QtCore
from generate_image import generate_image

class QTextEditLogger(QtCore.QObject):
    """A logger that writes to a QTextEdit widget."""
    def __init__(self, text_edit):
        super().__init__()
        self.text_edit= text_edit

    def write(self, msg):
        """Write a message to the QTextEdit widget."""
        if msg.strip():
            self.text_edit.append(msg)
            self.text_edit.moveCursor(QtGui.QTextCursor.End)


class SSRPointerWindow(QtWidgets.QWidget):
    """
    This class implements a user-interface for a set of tools that generate
    a plot to visuallize SSR pointers.

    Usage:
        To Do
    """
    def __init__ (self, parent=None):
        """
        Initializes the SSR Pointer Tool window and its widgets.
        Widgets and layout:
            - Run SSR Pointer Tool button (row 0, columns 0-3): Starts the
              SSR pointer visualization.
            - Image output area (row 1, columns 0-3): Displays generated SSR pointer plots.
            - SSR Selection Combo Box (row 2, columns 0-3): Allows selection between
              SSR-A and SSR-B pointer sets.
            - Console output area (row 2, columns 0-3): Shows log and console messages.
            - Quit button (row 3, column 3): Closes the interface.
            - Additional read-only text display for formatted output.
        Note:
            The widgets are arranged using a QGridLayout, with most controls spanning all
            columns for a wide interface.
        """
        QtWidgets.QWidget.__init__(self,parent)
        self.redBackground=   "QPushButton { background: red }"
        self.greenBackground= "QPushButton { background: lightgreen }"
        self.setWindowTitle ("SSR Visualizer (Ver 1.0)")
        self.resize(QtCore.QSize(
            int((tk.Tk().winfo_screenwidth() / get_screen_scaling()) / 4),
            int((tk.Tk().winfo_screenheight() / get_screen_scaling()) / 1.5)
            ))
        self.layout= QtWidgets.QGridLayout()
        self.selectedssr= None
        self.plot_path= None
        self.plot= None

#       # Build GUI
        build_ssr_selection(self)     # row 1, columns 0-1
        build_channel_selection(self) # row 1, columns 2-3
        build_image_output(self)      # row 2, columns 0-3
        build_console(self)           # row 3, columns 0-3
        build_run_button(self)        # row 4, columns 0-2
        build_quit_button(self)       # row 4, column 3
        gui_formatting(self)

        # Button clicked actions
        self.runssrbutton.clicked.connect(self.run_ssr)
        self.quitbutton.clicked.connect(self.quit_event)

    def selected_ssr(self, text):
        "Handle changes in the SSR selection combo box."
        self.selectedssr= text

    def selected_channel(self, text):
        "Handle changes in the channel selection combo box."
        self.selectedchannel= text

    def run_ssr(self):
        "Handle the Run button click event"
        generate_image(self)

        if self.plot is not None:
            with NamedTemporaryFile(suffix= ".jpg", delete= False) as tmp_file:
                self.plot_path= tmp_file.name
                self.plot.write_image(self.plot_path, scale=2)
            build_image_output(self)
            os.remove(tmp_file.name)
        else:
            build_image_output(self)
            print(f"  - SSR-{self.selectedssr} is OFF, cannot generate plot.\n")

    def quit_event(self):
        "Handle the quit button click event."
        sys.exit(1)


def get_screen_scaling():
    root = tk.Tk()
    pixels_per_inch = root.winfo_fpixels('1i')  # '1i' = 1 inch
    root.destroy()
    scaling_factor = pixels_per_inch / 96  # 96 is the baseline DPI
    return scaling_factor


def build_run_button(self):
    "build the run button"
    self.runssrbutton= QtWidgets.QPushButton("Run SSR Visualizer")
    self.runssrbutton.setToolTip("Run the SSR Visualizer to generate a visual "
                                 "of SSR pointers and data usage status.")
    self.runssrbutton.setMinimumHeight(40)
    runfont= self.runssrbutton.font()
    runfont.setBold(True)
    runfont.setPointSize(2 * runfont.pointSize())
    self.runssrbutton.setFont(runfont)
    self.runssrbutton.setStyleSheet(self.greenBackground)
    self.layout.addWidget(self.runssrbutton, 4, 0, 1, 3)


def build_ssr_selection(self):
    "build the SSR selection combo box"
    # Section label
    self.ssrlabel= QtWidgets.QLabel("Select SSR:")
    self.ssrlabel.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignCenter)
    self.ssrlabel.setMinimumHeight(30)
    ssrfont= self.ssrlabel.font()
    ssrfont.setPointSize(2 * ssrfont.pointSize())
    self.ssrlabel.setFont(ssrfont)
    self.layout.addWidget(self.ssrlabel, 1, 0)

    # SSR selection combo box
    self.ssrcombobox= QtWidgets.QComboBox()
    self.ssrcombobox.addItems(["A", "B"])
    self.ssrcombobox.setEditable(True)
    self.ssrcombobox.setToolTip("Select which SSR to visualize")
    line_edit= self.ssrcombobox.lineEdit() # Move selectable items to center of box
    line_edit.setAlignment(QtCore.Qt.AlignCenter)
    line_edit.setReadOnly(True)
    self.ssrcombobox.setMinimumHeight(30)
    ssrcombofont= self.ssrcombobox.font()
    ssrcombofont.setPointSize(2 * ssrcombofont.pointSize())
    self.ssrcombobox.setFont(ssrcombofont)
    self.layout.addWidget(self.ssrcombobox, 1, 1)
    self.selectedssr= self.ssrcombobox.currentText()
    self.ssrcombobox.currentTextChanged.connect(self.selected_ssr)


def build_channel_selection(self):
    "build the channel selection combo box"
    # Section label
    self.channellabel= QtWidgets.QLabel("Channel:")
    self.channellabel.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignCenter)
    self.channellabel.setMinimumHeight(30)
    channelfont= self.channellabel.font()
    channelfont.setPointSize(2 * channelfont.pointSize())
    self.channellabel.setFont(channelfont)
    self.layout.addWidget(self.channellabel, 1, 2)

    # Channel selection combo box
    self.channelcombobox= QtWidgets.QComboBox()
    self.channelcombobox.addItems(["Flight", "ASVT"])
    self.channelcombobox.setEditable(True)
    self.channelcombobox.setToolTip("Select which data channel to query data from.")
    line_edit= self.channelcombobox.lineEdit() # Move selectable items to center of box
    line_edit.setAlignment(QtCore.Qt.AlignCenter)
    line_edit.setReadOnly(True)
    self.channelcombobox.setMinimumHeight(30)
    ssrcombofont= self.channelcombobox.font()
    ssrcombofont.setPointSize(2 * ssrcombofont.pointSize())
    self.channelcombobox.setFont(ssrcombofont)
    self.layout.addWidget(self.channelcombobox, 1, 3)
    self.selectedchannel= self.channelcombobox.currentText()
    self.channelcombobox.currentTextChanged.connect(self.selected_channel)


def build_image_output(self):
    "build the image output area"
    self.imageoutput= QtWidgets.QLabel()
    self.imageoutput.setAlignment(QtCore.Qt.AlignCenter)
    self.imageoutput.setMinimumHeight(int(self.height() * 0.70))
    self.imageoutput.setStyleSheet("border: 1px solid gray; background: #f0f0f0;")
    if self.plot is not None:
        self.imageoutput.setPixmap(
            QtGui.QPixmap(self.plot_path).scaled(int(self.height() * 0.72),
                                                    int(self.height() * 0.72)))
    self.layout.addWidget(self.imageoutput, 2, 0, 1, 4)


def build_console(self):
    "build the console output area"
    self.consolequtput= QtWidgets.QTextEdit()
    self.consolequtput.setReadOnly(True)
    self.consolequtput.setLineWrapMode(QtWidgets.QTextEdit.NoWrap)
    self.consolequtput.setFont(QtGui.QFont("Courier", 10))
    self.consolequtput.setMinimumHeight(int(self.height() * 0.08))
    self.layout.addWidget(self.consolequtput, 3, 0, 1, 4)
    sys.stdout= QTextEditLogger(self.consolequtput)
    sys.stderr= QTextEditLogger(self.consolequtput)


def build_quit_button(self):
    "build the quit button"
    self.quitbutton= QtWidgets.QPushButton("Quit")
    self.quitbutton.setToolTip("Close Tool")
    self.quitbutton.setMinimumHeight(40)
    quitfont= self.quitbutton.font()
    quitfont.setBold(True)
    quitfont.setPointSize(2 * quitfont.pointSize())
    self.quitbutton.setFont(quitfont)
    self.quitbutton.setStyleSheet(self.redBackground)
    self.layout.addWidget(self.quitbutton, 4, 3)


def gui_formatting(self):
    "formatting for the GUI"
    self.textdisplay= QtWidgets.QTextEdit()
    self.textdisplay.setReadOnly ( True )
    self.textdisplay.setLineWrapMode(QtWidgets.QTextEdit.NoWrap)
    self.textdisplay.moveCursor (QtGui.QTextCursor.End)
    font= QtGui.QFont("Courier", 10, QtGui.QFont.Bold)
    self.textdisplay.setFont (font)
    self.setLayout(self.layout)
