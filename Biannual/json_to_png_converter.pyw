import sys
from pathlib import Path
from typing import List, Union

import plotly.io as pio
from PyQt6.QtWidgets import (QApplication, QMainWindow, QTextEdit, 
                             QPushButton, QVBoxLayout, QWidget, QFileDialog)
from PyQt6.QtCore import pyqtSignal, QObject
from PyQt6.QtGui import QFont


class EmittingStream(QObject):
    textWritten = pyqtSignal(str)

    def write(self, text):
        # Emit the signal containing the printed text
        self.textWritten.emit(str(text))

    def flush(self):
        # Required for stream compatibility, but doesn't need to do anything
        pass

# 2. Build the Main GUI Window
class ConverterWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("JSON to PNG Converter")
        self.resize(800, 500)

        # Set up the central layout
        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)

        # Add a trigger button
        self.btn_convert = QPushButton("Select JSON Files & Convert")
        self.btn_convert.clicked.connect(self.run_conversion)
        self.btn_convert.setMinimumHeight(40)
        layout.addWidget(self.btn_convert)

        # Add the console output area
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setFont(QFont("Courier", 10))
        self.console.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4;")
        layout.addWidget(self.console)

        self.setCentralWidget(central_widget)

        # Redirect standard output and errors to our custom stream
        sys.stdout = EmittingStream(textWritten=self.normal_output_written)
        sys.stderr = EmittingStream(textWritten=self.normal_output_written)

    def normal_output_written(self, text):
        # Move cursor to the end, insert text, and keep it scrolled to the bottom
        self.console.moveCursor(self.console.textCursor().MoveOperation.End)
        self.console.insertPlainText(text)
        self.console.moveCursor(self.console.textCursor().MoveOperation.End)

        # Force the UI to refresh immediately so prints aren't batched at the end
        QApplication.processEvents() 

    def run_conversion(self):
        # Open file dialog
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select One or more JSON Files",
            "",
            "JSON (*.json)"
        )

        if not file_paths:
            print("User canceled the selection.\n")
            return

        for path in file_paths: 
            print(f"User selected: {path}")

        output_folder = Path(file_paths[0]).parent / "Output"
        print(f"\nStarting conversion...\nOutput directory: {output_folder}\n")

        # Disable the button while running to prevent double-clicks
        self.btn_convert.setEnabled(False)

        # Execute the conversion
        convert_json_to_png(file_paths, output_dir=output_folder)
        print("\nBatch conversion complete!\n")
        self.btn_convert.setEnabled(True)

    def closeEvent(self, event):
        # Restore standard output to the actual console when the window closes
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        super().closeEvent(event)


# 3. The Conversion Logic
def convert_json_to_png(
    json_paths: List[Union[str, Path]],
    output_dir: Union[str, Path] = None,
    width: int = 1600,
    height: int = 1000
) -> List[Path]:
    """
    Parses Plotly JSON files and saves them natively as PNGs.
    """
    saved_pngs = []

    for path_input in json_paths:
        json_path = Path(path_input).resolve()

        if not json_path.exists():
            print(f"Warning: File not found -> {json_path}")
            continue

        if output_dir:
            out_directory = Path(output_dir)
            out_directory.mkdir(parents=True, exist_ok=True)
            png_path = out_directory / f"{json_path.stem}.png"
        else:
            png_path = json_path.with_suffix(".png")

        try:
            fig = pio.read_json(str(json_path))
            fig.update_layout(width=width, height=height)
            fig.write_image(str(png_path))
            saved_pngs.append(png_path)
            print(f"Converted & Fully Captured: {png_path.name}")

        except Exception as e:
            print(f"Error converting {json_path.name}: {e}")

        # Allow GUI to update during the loop so prints render immediately
        QApplication.processEvents()

    return saved_pngs


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Initialize and display the main window
    window = ConverterWindow()
    window.show()

    sys.exit(app.exec())
