import tkinter as tk
from tkinterweb import HtmlFrame # For rendering HTML/Plotly
import plotly.graph_objects as go
import plotly.io as pio
from plot import generate_plot

class ScriptRunnerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Script Controller with Plotly")
        self.root.geometry("900x700") # Larger window for the plot

        # --- Variables ---
        self.data_rate_var = tk.StringVar(value="1024")
        self.pa_mode_var = tk.StringVar(value="Low Power")

        # --- UI Layout ---
        self.setup_ui()

    def setup_ui(self):
        # Top Container for Controls
        control_frame = tk.Frame(self.root)
        control_frame.pack(side="top", fill="x", padx=10, pady=10)

        # Dropdowns (Side by side)
        tk.Label(control_frame, text="Data Rate:").pack(side="left", padx=5)
        dr_menu = tk.OptionMenu(control_frame, self.data_rate_var, 1024, 512, 256, 128, 64)
        dr_menu.pack(side="left", padx=5)

        tk.Label(control_frame, text="PA Mode:").pack(side="left", padx=15)
        pa_menu = tk.OptionMenu(control_frame, self.pa_mode_var, "Low Power", "High Power")
        pa_menu.pack(side="left", padx=5)

        # --- The Plot Box ---
        # This frame will hold the Plotly object
        self.plot_container = HtmlFrame(self.root)
        self.plot_container.pack(fill="both", expand=True, padx=10, pady=10)

        # Bottom Buttons
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(side="bottom", fill="x", pady=10)

        tk.Button(btn_frame, text="Run Script", command=self.run_script, bg="#e1f5fe").pack(side="left", padx=20)
        tk.Button(btn_frame, text="Pause", command=lambda: print("Paused")).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Exit", command=self.root.quit).pack(side="right", padx=20)

    def run_script(self):
        # 1. Get parameters
        rate = int(self.data_rate_var.get())
        mode = self.pa_mode_var.get()

        # 2. RUN YOUR SCRIPT (Example Plotly Logic)
        fig= generate_plot(rate, mode)

        # 3. Convert Plotly fig to HTML string
        # 'include_plotlyjs="cdn"' keeps the string small by loading JS from the web
        plot_html = pio.to_html(fig, full_html=True, include_plotlyjs='cdn')

        # 4. Render in the GUI box
        self.plot_container.load_html(plot_html)

if __name__ == "__main__":
    root = tk.Tk()
    app = ScriptRunnerGUI(root)
    root.mainloop()
