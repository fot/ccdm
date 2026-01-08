from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, 
                             QDoubleSpinBox, QSpinBox, QPushButton, QGroupBox, QScrollArea, QWidget)

class ParametersGUI(QDialog):
    def __init__(self, parent=None, initialize= False):
        super().__init__(parent)
        self.setWindowTitle("Edit RF Link Parameters")
        self.setMinimumWidth(400)
        
        # This dictionary will store our actual numeric values
        self.values = {}

        # Main Layout
        self.layout = QVBoxLayout(self)

        # Create a scroll area in case the list gets long
        scroll = QScrollArea()
        scroll_content = QWidget()
        self.form_layout = QFormLayout(scroll_content)

        # --- Define Parameters ---
        # Format: (Key, Label, Default Value, Decimals, Step)
        params= [
            ("TX_GAIN", "TX Ant Gain (dBi)", -1.25, 2, 0.05),
            ("TX_LOSS", "TX Cable Loss (dB)", 2.75, 2, 0.1),
            ("FREQ", "Frequency (MHz)", 2250.0, 1, 10.0),
            ("L_ATM", "Atmospheric Loss (dB)", 0.19, 2, 0.01),
            ("L_POL", "Polarization Loss (dB)", 0.22, 2, 0.01),
            ("RX_GT", "Rx G/T (dB/K)", 33.63, 2, 0.1),
            ("K_BOLTZMANN", "K_Boltzmann (dBW)", -228.599167, 2, 0.01),
            ("RX_SYSTEM_LOSS", "Rx System Loss (dB)", 0.6, 2, 0.1),
            ("BW_CARRIER", "Carrier Loop BW (Hz)", 45.0, 1, 1.0),
            ("MOD_DATA", "Data Mod Index (rad)", 1.25, 3, 0.01),
            ("MOD_RNG", "Ranging Mod Index", 0.176, 3, 0.01),
            ("MOD_CMD", "Command Mod Index", 0.236, 3, 0.01),
            ("REQ_SNR", "Required Carrier SNR (dB)", 10.0, 1, 0.5),
            ("REQ_EBNO", "Required Eb/No (dB)", 2.55, 2, 0.1),
            ("DSN_ANT_GAIN", "DSN Ant Gain (dBi)", 55.93, 2, 0.1),
            ("DSN_MISC_LOSS", "DSN Misc Loss (dB)", 0.10, 2, 0.01),
            ("BWG_ANT_GAIN", "BWG Ant Gain (dBi)", 56.8, 2, 0.1),
        ]

        self.inputs = {}
        for key, label, default, dec, step in params:
            spin = QDoubleSpinBox()
            spin.setRange(-1000.0, 1000000.0) # Broad range
            spin.setDecimals(dec)
            spin.setSingleStep(step)
            spin.setValue(default)

            if key not in ["TX_GAIN", "TX_LOSS", "DSN_ANT_GAIN"]:
                            spin.setReadOnly(True)
                            # Optional: Change the background color to a "darkened" grey
                            spin.setStyleSheet("background-color: #e0e0e0; color: #505050;")

            self.inputs[key] = spin
            self.form_layout.addRow(label, spin)

        scroll.setWidget(scroll_content)
        scroll.setWidgetResizable(True)
        self.layout.addWidget(scroll)

        # --- Buttons ---
        button_layout= QHBoxLayout()
        
        # Save Button
        self.save_btn = QPushButton("Accept and Launch Tool" if initialize else "Save")
        self.save_btn.setStyleSheet("background-color: #2E7D32; color: white; font-weight: bold;")
        self.save_btn.clicked.connect(self.save_and_close)
        button_layout.addWidget(self.save_btn)

        # Cancel Button
        if not initialize:
            self.cancel_btn = QPushButton("Cancel")
            self.cancel_btn.clicked.connect(self.reject)
            button_layout.addWidget(self.cancel_btn)

        self.layout.addLayout(button_layout)

    def save_and_close(self):
        # Update the values dictionary with current spinbox values
        for key, spinbox in self.inputs.items():
            self.values[key] = spinbox.value()
        self.accept() # Closes the dialog and returns "Accepted" status
