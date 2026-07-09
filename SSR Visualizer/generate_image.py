"""
Tool to display SSR Pointers.
Handles MAUDE data requests, data parsing, and native Matplotlib polar plot generation.
"""

import json
import urllib.request
import traceback
import warnings
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg

warnings.filterwarnings("ignore")


def data_request(self, msids: list) -> pd.DataFrame:
    """Synchronous fetching with urllib, vectorized Pandas processing."""
    def maude_data_request(ts, tp, msid):
        url = ("http://telemetry.cfa.harvard.edu/maude/mrest/"
               f"FLIGHT/msid.json?m={msid}&ts={ts.strftime('%Y%j%H%M%S')}"
               f"&tp={tp.strftime('%Y%j%H%M%S')}&ap=t")
        response = urllib.request.urlopen(url)
        return json.loads(response.read())

    all_dfs = []
    ts = self.start_date
    tp = self.end_date

    for msid in msids:
        raw_times_accum = []
        raw_values_accum = []
        shift_time = timedelta(0)

        while True:
            raw_data = maude_data_request(ts + shift_time, tp, msid)
            chunk_times = raw_data.get('data-fmt-1', {}).get('times', [])
            chunk_values = raw_data.get('data-fmt-1', {}).get('values', [])

            if not chunk_times:
                break

            raw_times_accum.extend(chunk_times)
            raw_values_accum.extend(chunk_values)

            last_time_str = str(chunk_times[-1])
            last_time_dt = datetime.strptime(last_time_str, "%Y%j%H%M%S%f").replace(tzinfo=timezone.utc)
            new_shift_time = last_time_dt - ts

            if last_time_dt >= tp or new_shift_time <= shift_time:
                break
            shift_time = new_shift_time

        if not raw_times_accum:
            empty_df = pd.DataFrame(columns=['times', 'values'])
            empty_df['msid'] = msid
            all_dfs.append(empty_df)
            continue

        df = pd.DataFrame({'times': raw_times_accum, 'values': raw_values_accum})
        df.drop_duplicates(subset=['times'], inplace=True)
        df['times'] = pd.to_datetime(df['times'].astype(str), format='%Y%j%H%M%S%f')
        df['values'] = pd.to_numeric(df['values'])

        df.sort_values(by='times', inplace=True)
        df.reset_index(drop=True, inplace=True)
        df['msid'] = msid
        all_dfs.append(df)

    if not all_dfs:
        return pd.DataFrame(columns=['times', 'values', 'msid'])

    return pd.concat(all_dfs, ignore_index=True)


def get_pointers(self):
    """Retrieves the playback and record pointers using vectorized Pandas operations."""
    print("  - Getting Playback/Record Pointers...")
    pb_pointers = []
    ssr_max_val = 134217728

    pb_df = data_request(self, [f"COS{self.selectedssr.upper()}PBPT"])

    if pb_df.empty:
        raise ValueError(f"No Playback Pointer data returned for SSR-{self.selectedssr}.")

    pb_series = pb_df['values'].astype(int)[::-1].reset_index(drop=True)
    current_pb = pb_series.iloc[0]
    pb_pointers.append(current_pb)

    changed_pb = pb_series[pb_series != current_pb]

    if not changed_pb.empty:
        pb_pointers.append(changed_pb.iloc[0])
    else:
        pb_pointers.append(None)

    rc_df = data_request(self, [f"COS{self.selectedssr.upper()}RCPT"])

    if rc_df.empty:
        raise ValueError(f"No Record Pointer data returned for SSR-{self.selectedssr}.")

    rc_series = rc_df['values'].astype(int)
    rc_pointer = rc_series.iloc[-1]
    rc_timestamp = rc_df['times'].iloc[-1].replace(tzinfo=timezone.utc)
    old_rc_timestamp = rc_df['times'].iloc[0].replace(tzinfo=timezone.utc)

    delta_hours = (rc_timestamp - old_rc_timestamp).total_seconds() / 3600.0
    total_pointers_moved = rc_series.diff().dropna().mod(ssr_max_val).sum()

    if delta_hours > 0 and total_pointers_moved > 0:
        self.rc_rate = total_pointers_moved / delta_hours
    else:
        self.rc_rate = ssr_max_val / 18.6

    self.pb_pointers =  pb_pointers
    self.rc_pointer =   rc_pointer
    self.rc_timestamp = rc_timestamp


def generate_polar_plot(self):
    """Generates a custom polar plot using Matplotlib styled to match Plotly."""
    ssr_min, ssr_max = 0, 134217728

    fig = Figure(figsize=(9, 8), dpi=100, facecolor='white')
    ax = fig.add_subplot(111, polar=True)

    ax.set_theta_direction(-1)
    ax.set_theta_offset(np.pi / 2)

    ax.set_facecolor('#E5ECF6')
    ax.grid(False)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.spines['polar'].set_visible(False)
    ax.set_ylim(0, 1.2)

    # --- Data Traces ---
    rc_angle = (self.rc_pointer / (ssr_max - ssr_min)) * 2 * np.pi
    ax.plot([rc_angle, rc_angle], [0, 1.2], color='blue', linewidth=3,
            label=f"Record Pointer: {self.rc_pointer:,}")

    pb_angle = (self.pb_pointers[0] / (ssr_max - ssr_min)) * 2 * np.pi
    ax.plot([pb_angle, pb_angle], [0, 1.2], color='red', linewidth=3,
            label=f"Current Playback: {self.pb_pointers[0]:,}")

    if self.pb_pointers[-1] is not None:
        prev_pb_angle = (self.pb_pointers[-1] / (ssr_max - ssr_min)) * 2 * np.pi
        ax.plot([prev_pb_angle, prev_pb_angle], [0, 1.2], color='red', linewidth=3,
                linestyle='--', label=f"Previous Playback: {self.pb_pointers[-1]:,}")

    # Shading
    if self.pb_pointers[0] != self.rc_pointer:
        theta0 = pb_angle % (2 * np.pi)
        theta1 = rc_angle % (2 * np.pi)
        if theta1 <= theta0:
            theta1 += 2 * np.pi
        theta_fill = np.linspace(theta0, theta1, 200)
        ax.fill_between(theta_fill, 0, 1.2, color='red', alpha=0.2)

    # Labels and Grid Lines
    angles_rad = np.linspace(0, 2 * np.pi, 8, endpoint=False)
    current_mode = getattr(self, 'display_mode', 'pointers')
    for i, angle in enumerate(angles_rad):
        # Draw Plotly-style dashed grid lines
        ax.plot([angle, angle], [0, 1.2], color='black', alpha=0.1, linewidth=2, linestyle='--')

        # Labels
        if current_mode == "time":
            tick_pointer = i * ((ssr_max - ssr_min) / 8)
            pointers_to_go = (tick_pointer - self.rc_pointer) % ssr_max
            hours_to_go = pointers_to_go / self.rc_rate
            future_time = self.rc_timestamp + timedelta(hours=hours_to_go)
            label_text = future_time.strftime('%Y:%j\n%H:%M:%S')
        else:
            val = int(ssr_min + i * ((ssr_max - ssr_min) / 8))
            label_text = f"{val:,}"
            if i == 0: label_text = f"{ssr_max:,}\n{label_text}"

        ax.text(angle, 1.28, label_text, ha='center', va='center', fontsize=14, color='black')

    # Status Alert
    playback_active = data_request(self, [f"COS{self.selectedssr}PBEN"])
    print(f"  - Checking if SSR-{self.selectedssr} has an active playback...")
    if not playback_active.empty and str(playback_active['values'].iloc[-1]) == "1":
        fig.text(0.95, 0.95, "PLAYBACK ACTIVE", color="black", fontsize=14,
                 ha="right", va="top", bbox=dict(facecolor='red',
                                                 edgecolor='black', boxstyle='square,pad=0.3'))

    # --- UI Layout Formatting ---
    fig.subplots_adjust(left=0.05, right=0.95, top=0.90, bottom=0.15)

    # Legend: Docked securely at the bottom left
    fig.legend(loc='lower left', bbox_to_anchor=(0.02, 0.02), 
               frameon=True, facecolor='white', framealpha=1.0, edgecolor='black', fontsize=12)

    # Timestamp: Docked securely at the bottom right
    current_time_str = datetime.now(timezone.utc).strftime('%m/%d/%Y (%Y:%j) %H:%M:%S UTC')
    fig.text(0.95, 0.05, current_time_str, ha='right', va='bottom', fontsize=12, color='black')

    # Render
    canvas = FigureCanvasAgg(fig)
    canvas.draw()
    self.plot_rgba = np.asarray(canvas.buffer_rgba())
    print(f"  - Plot generated for SSR-{self.selectedssr}...")


def generate_image(self):
    """Executes the main orchestration logic."""
    self.start_date = datetime.now(timezone.utc) - timedelta(hours=self.selectedquery)
    self.end_date = datetime.now(timezone.utc) - timedelta(seconds=5)

    print(f"Checking if SSR-{self.selectedssr} is ON...")
    ssr_power = data_request(self, [f"COSSR{self.selectedssr}X"])

    try:
        if ssr_power.empty:
            print(f"  - (Error): No power data retrieved.")
            self.plot_rgba = None
            return

        if int(ssr_power['values'].iloc[-1]) == 1:
            print(f"  - SSR-{self.selectedssr} is ON...")
            get_pointers(self)
            generate_polar_plot(self)
        else:
            self.plot_rgba = None
    except Exception as error:
        print(f"  - (Error) \"{error}\": Failed to generate plot.")
        traceback.print_exc()
        self.plot_rgba = None

    if hasattr(self, 'continuous_checkbox') and self.continuous_checkbox.isChecked():
        print("  - Continuous mode ENABLED.")
