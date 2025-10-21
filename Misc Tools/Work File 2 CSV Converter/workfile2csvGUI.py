#!/usr/bin/env python3
"""
workfile2text_gui.py
GUI for converting binary work files (.wrk) to CSV using Tkinter.
"""

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import struct
import datetime
import os


MJD1985 = 46066
MJD1900 = 15020
MJD1970 = 40587


def date_to_mjd(year, month, day):
    return (367 * year
            - int(7 * (year + int((month + 9) / 12)) / 4)
            + int(275 * month / 9)
            + day + (1721013.5 - 2400000.5))


def secref_to_timedata(secref, refmjd):
    sec1970 = secref + (refmjd - MJD1970) * 86400
    base_time = int(sec1970)
    frac = sec1970 - base_time
    utc = datetime.datetime.utcfromtimestamp(base_time)
    doy = utc.timetuple().tm_yday
    sec_of_day = utc.hour * 3600 + utc.minute * 60 + utc.second + frac
    timestring = f"{utc.year}:{doy:03d}:{utc.hour:02d}:{utc.minute:02d}:{sec_of_day % 60:09.6f}"
    mjd = date_to_mjd(utc.year, utc.month, utc.day)
    return {
        "timestring": timestring,
        "mjd": mjd,
        "year": utc.year,
        "doy": doy,
        "sod": sec_of_day,
    }


def unpack_wrk_record(data):
    """Unpack 249-byte record."""
    def d(a, b): return struct.unpack("<d", data[a:b])[0]
    def l(a, b): return struct.unpack("<l", data[a:b])[0]
    w = {}
    w["sclk_adj_data_1"] = d(4, 12)
    w["sclk_adj_data_f"] = d(12, 20)
    w["sclk_ref_cnts"] = d(20, 28)
    w["sclk_ref_gmt"] = d(60, 68)
    w["sclk_rate"] = d(68, 76)
    w["sclk_drift_rate"] = d(76, 84)
    w["sclk_base_ref"] = data[224:245].decode(errors="ignore").strip()
    return w


def convert_file(filepath, log_callback):
    try:
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")

        outfile = os.path.splitext(filepath)[0] + ".csv"
        log_callback(f"Reading {filepath}...\n")

        with open(filepath, "rb") as fin, open(outfile, "w", encoding="utf-8") as fout:
            fout.write("RefTime(UTC),RefVCDU,RefTime(sec),Rate(sec/cnt),Drift(sec/cnt^2),DayofYr,ExcelTime\n")

            recnum = 0
            while True:
                data = fin.read(249)
                if len(data) != 249:
                    break
                w = unpack_wrk_record(data)
                recnum += 1

                t = secref_to_timedata(w["sclk_ref_gmt"], MJD1985)
                mjd, doy, sod = t["mjd"], t["doy"], t["sod"]
                ExcelTime = (mjd - MJD1900 + 2) + sod / 86400
                DayofYr = doy + sod / 86400

                fout.write(f"{t['timestring']}, {w['sclk_ref_cnts']:14.2f}, {w['sclk_ref_gmt']:17.7f}, "
                           f"{w['sclk_rate']:17.14f}, {w['sclk_drift_rate']:14.6e}, "
                           f"{DayofYr:10.6f}, {ExcelTime:13.6f}\n")

        log_callback(f"✅ Done! {recnum} records written to:\n{outfile}\n")
    except Exception as e:
        log_callback(f"❌ Error: {e}\n")
        messagebox.showerror("Conversion Error", str(e))


# ----------------- GUI -----------------
def launch_gui():
    root = tk.Tk()
    root.title("Workfile to CSV Converter")
    root.geometry("600x400")
    root.resizable(False, False)

    selected_file = tk.StringVar()

    def choose_file():
        path = filedialog.askopenfilename(filetypes=[("Work files", "*.wrk"), ("All files", "*.*")])
        if path:
            selected_file.set(path)
            log(f"Selected file: {path}\n")

    def run_conversion():
        if not selected_file.get():
            messagebox.showwarning("No file", "Please select a .wrk file first.")
            return
        log("Starting conversion...\n")
        convert_file(selected_file.get(), log)

    def log(msg):
        output.insert(tk.END, msg)
        output.see(tk.END)
        root.update_idletasks()

    tk.Label(root, text="Select a Work (.wrk) File:", font=("Arial", 12)).pack(pady=10)
    tk.Entry(root, textvariable=selected_file, width=60).pack(pady=5)
    tk.Button(root, text="Browse", command=choose_file, width=15).pack(pady=5)
    tk.Button(root, text="Convert to CSV", command=run_conversion, width=20, bg="#4CAF50", fg="white").pack(pady=10)

    tk.Label(root, text="Output Log:", font=("Arial", 11)).pack(pady=5)
    output = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=70, height=12)
    output.pack(padx=10, pady=5)

    root.mainloop()


if __name__ == "__main__":
    launch_gui()
