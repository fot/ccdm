import sys
import pandas as pd
from pathlib import Path
from PyQt6.QtWidgets import QApplication

# Import your local modules
from clock_app import ClockDriftApp
from reports import generate_correlation_report

def run_tests():
    app = QApplication(sys.argv)

    basepath = Path(r"//noodle/fot/engineering/ccdm/Clock_Timing/Clock Correlation Output/2026/rclkout_26_264_278")
    csvpath = basepath / "rclkout_26_264_278.csv"

    print(f"Loading test dataframe from {csvpath.name}...")

    try:
        df = pd.read_csv(csvpath, parse_dates=['datetime', 'astropy_time'])
    except FileNotFoundError:
        print(f"Could not find CSV at {csvpath}")
        return

    clock_app = ClockDriftApp()
    sys.stdout = sys.__stdout__

    # 5. Inject the mock data and paths
    clock_app.nrt_df = df
    clock_app.out_dir = str(basepath)
    
    # FIX: Inject dummy variables for the binary paths to satisfy draft_email()
    clock_app.base_dis = r"C:\mock\path\CLKHST_2026264_000000.DIS"
    clock_app.base_dat = r"C:\mock\path\CLKHST_2026264_000000.DAT"

    # --- TEST 1: Correlation Report ---
    print("\nTesting generate_correlation_report()...")
    try:
        # FIX: Provide dummy strings for erp_path and sto_path so Path() doesn't crash on None
        generate_correlation_report(
            df, 
            erp_path="mock_ephemeris.erp", 
            sto_path="mock_telemetry.sto", 
            output_path=basepath
        )
        print(f"Success! Correlation report saved to {basepath}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error testing correlation report: {e}")

    # --- TEST 2: Email Draft UI ---
    print("\nTesting draft_email()...")
    try:
        clock_app.draft_email()
        print("Email test sequence completed.")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error testing email draft: {e}")

if __name__ == "__main__":
    run_tests()
