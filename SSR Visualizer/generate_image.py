"""
Tool to display SSR Pointers.
Handles MAUDE data requests, data parsing, and Plotly polar plot generation.
"""

import json
import urllib.request
import traceback
import warnings
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import plotly.graph_objects as go

warnings.filterwarnings("ignore")


def data_request(self, msids: list) -> pd.DataFrame:
    """
    Synchronous fetching with urllib, vectorized Pandas processing.

    Args:
        self: The main application instance containing state variables (start_date, end_date).
        msids (list): A list of MAUDE MSID strings to query.

    Returns:
        pd.DataFrame: A single concatenated Pandas DataFrame containing 'times', 'values', 
                      and 'msid' columns for all requested data.
    """

    def maude_data_request(ts, tp, msid):
        """Helper to request a particular MSID for an interval from MAUDE using urllib."""
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

        # Collect Data
        while True:
            raw_data = maude_data_request(ts + shift_time, tp, msid)

            chunk_times = raw_data.get('data-fmt-1', {}).get('times', [])
            chunk_values = raw_data.get('data-fmt-1', {}).get('values', [])

            if not chunk_times:
                break

            raw_times_accum.extend(chunk_times)
            raw_values_accum.extend(chunk_values)

            # Parse ONLY the last timestamp to manage the loop logic
            last_time_str = str(chunk_times[-1])
            last_time_dt = datetime.strptime(last_time_str, "%Y%j%H%M%S%f").replace(tzinfo=timezone.utc)
            new_shift_time = last_time_dt - ts

            if last_time_dt >= tp or new_shift_time <= shift_time:
                break

            shift_time = new_shift_time

        # Handle edge case where no data was returned for the entire MSID
        if not raw_times_accum:
            empty_df = pd.DataFrame(columns=['times', 'values'])
            empty_df['msid'] = msid
            all_dfs.append(empty_df)
            continue

        # --- PANDAS VECTORIZATION ---
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
    """
    Retrieves the playback and record pointers for a specified SSR 
    within the configured date range using vectorized Pandas operations.

    Extracts the most recent record pointer, its exact timestamp, and 
    both current and previous playback pointers. Saves these to `self`.
    """
    print("  - Getting Playback/Record Pointers...")
    pb_pointers = []
    ssr_max_val = 134217728

    # --- Find Current and Previous Playback Pointers ---
    pb_df = data_request(self, [f"COS{self.selectedssr.upper()}PBPT"])

    if pb_df.empty:
        raise ValueError(f"No Playback Pointer data returned for SSR-{self.selectedssr}.")

    # Reverse values and cast to integer via Pandas
    pb_series = pb_df['values'].astype(int)[::-1].reset_index(drop=True)
    current_pb = pb_series.iloc[0]
    pb_pointers.append(current_pb)

    # Vectorized search for the first value that differs from the current playback pointer
    changed_pb = pb_series[pb_series != current_pb]
    if not changed_pb.empty:
        pb_pointers.append(changed_pb.iloc[0])
    else:
        pb_pointers.append(None)

    # Extract data into values and times lists
    rc_data = data_request(self, f"COS{self.selectedssr.upper()}RCPT")
    rc_values = rc_data['data-fmt-1']['values']
    rc_times = rc_data['data-fmt-1']['times']

    # Newest data points
    rc_pointer = int(rc_values[-1])
    rc_time_str = str(rc_times[-1])
    rc_timestamp = datetime.strptime(rc_time_str[:13], "%Y%j%H%M%S").replace(tzinfo=timezone.utc)

    # Oldest point in the queried dataset
    old_rc_time_str = str(rc_times[0])
    old_rc_timestamp = datetime.strptime(old_rc_time_str[:13], "%Y%j%H%M%S").replace(tzinfo=timezone.utc)

    # Calculate elapsed time in hours
    delta_hours = (rc_timestamp - old_rc_timestamp).total_seconds() / 3600.0

    # Calculate total pointers moved (step-by-step to catch wrap-arounds)
    total_pointers_moved = 0
    for i in range(1, len(rc_values)):
        prev_val = int(rc_values[i-1])
        curr_val = int(rc_values[i])
        total_pointers_moved += (curr_val - prev_val) % ssr_max_val

    # Calculate dynamic rate (Pointers per Hour)
    if delta_hours > 0 and total_pointers_moved > 0:
        self.rc_rate = total_pointers_moved / delta_hours
    else:
        # Safe fallback to nominal 18.6 hr fill rate if data is missing/corrupted
        self.rc_rate = ssr_max_val / 18.6

    # Apply to instance
    self.pb_pointers = pb_pointers
    self.rc_pointer = rc_pointer
    self.rc_timestamp = rc_timestamp


def generate_polar_plot(self):
    """
    Generates a custom polar plot visualizing record and playback pointers on a circular scale.

    The plot dynamically adjusts labels based on the user's selected view mode (pointers vs. time)
    and highlights the active region between record and playback pointers.

    Returns:
        None: Stores the resulting plotly.graph_objs.Figure in `self.plot`.
    """
    ssr_max = 134217728
    ssr_min = 0
    angles_deg = np.linspace(0, 360, 8, endpoint=False)

    def _draw_grid_and_labels(plot, labels):
        """Helper to draw the text labels and dashed background grid lines."""
        for i, label in enumerate(labels):
            plot.add_trace(go.Scatterpolar(
                r=[1.2], theta=[angles_deg[i]], mode="text", text=[label],
                textfont={"size": 18, "color": "black"}, hoverinfo="skip", showlegend=False
            ))
            plot.add_trace(go.Scatterpolar(
                r=[0, 1.3], theta=[angles_deg[i], angles_deg[i]],
                mode="lines", line={"color": "rgba(0,0,0,0.1)", "width": 3, "dash": "dash"},
                hoverinfo="skip", showlegend=False
            ))

    def build_and_add_pointer_labels(plot):
        """Define labels based off SSR min/max raw pointer values."""
        labels = [f"{int(ssr_min + i * ((ssr_max - ssr_min) / 8)):,}" for i in range(8)]
        labels[0] = f"{labels[0]}<br>{labels[0]}" # Top dead center wrap-around label
        _draw_grid_and_labels(plot, labels)

    def build_and_add_time_labels(plot):
        """Define labels based off SSR time duration and the record pointer's timestamp."""
        labels = []

        for i in range(8):
            tick_pointer = i * ((ssr_max - ssr_min) / 8)

            # The modulo perfectly calculates wrap-around distance
            pointers_to_go = (tick_pointer - self.rc_pointer) % ssr_max
            hours_to_go = pointers_to_go / self.rc_rate

            # Add future duration to the timestamp of the last queried data point
            future_time = self.rc_timestamp + timedelta(hours=hours_to_go)
            labels.append(future_time.strftime('%Y:%j<br>%H:%M:%S'))
        _draw_grid_and_labels(plot, labels)

    def add_record_pointer(plot):
        """Add the record pointer trace (blue)."""
        rc_angle = (self.rc_pointer / (ssr_max - ssr_min)) * 360
        plot.add_trace(go.Scatterpolar(
            r=[0, 1.2], theta=[rc_angle, rc_angle], name=f"Record Pointer: {self.rc_pointer:,}",
            mode="lines", line={"color": "blue", "width": 4}, hoverinfo="skip", showlegend=True
        ))

    def add_current_playback_pointer(plot):
        """Add the current playback pointer trace (solid red)."""
        pb_angle = (self.pb_pointers[0] / (ssr_max - ssr_min)) * 360
        plot.add_trace(go.Scatterpolar(
            r=[0, 1.2], theta=[pb_angle, pb_angle], name=f"Current Playback Pointer: {self.pb_pointers[0]:,}",
            mode="lines", line={"color": "red", "width": 4}, hoverinfo="skip", showlegend=True
        ))

    def add_previous_playback_pointer(plot):
        """Add the previous playback pointer trace (dashed red)."""
        if self.pb_pointers[-1] is not None:
            prev_pb_angle = (self.pb_pointers[-1] / (ssr_max - ssr_min)) * 360
            plot.add_trace(go.Scatterpolar(
                r=[0, 1.2], theta=[prev_pb_angle, prev_pb_angle],
                name=f"Previous Playback Pointer: {self.pb_pointers[-1]:,}",
                mode="lines", line={"color": "red", "width": 4, "dash": "dash"},
                hoverinfo="skip", showlegend=True
            ))

    def add_highlighted_region(plot):
        """Add the shaded region between record and current playback pointer values."""
        if self.pb_pointers[0] != self.rc_pointer:
            theta0 = (self.pb_pointers[0] / (ssr_max - ssr_min)) * 360 % 360
            theta1 = (self.rc_pointer / (ssr_max - ssr_min)) * 360 % 360

            if theta1 <= theta0:
                theta1 += 360

            theta_fill = np.linspace(theta0, theta1, 200)
            r_fill = np.ones_like(theta_fill) * 1.2

            plot.add_trace(go.Scatterpolar(
                r=np.concatenate([[0], r_fill, [0]]),
                theta=np.concatenate([[theta_fill[0]], theta_fill, [theta_fill[-1]]]),
                mode="lines", fill="toself", fillcolor="rgba(255,0,0,0.2)",
                line={"color": "rgba(255,0,0,0)"}, hoverinfo="skip", showlegend=False
            ))

    def add_datetime_annotations(plot):
        """Add UI annotation detailing the execution timestamp."""
        current_time_str = datetime.now(timezone.utc).strftime('%m/%d/%Y (%Y:%j) %H:%M:%S')
        plot.add_annotation(
            text=f"{current_time_str} UTC", xref="paper", yref="paper",
            x=1.10, y=-0.10, showarrow=False, font={"size": 12, "color": "black"}, 
            align="right", borderpad=4, bgcolor="rgba(0,0,0,0)"
        )

    def add_playback_active_annotation(plot):
        """Query and display an alert if playback is actively occurring."""
        print(f"  - Checking if SSR-{self.selectedssr} has an active playback...")
        playback_active = data_request(self, [f"COS{self.selectedssr}PBEN"])

        # Ensure data exists before indexing
        if not playback_active.empty and str(playback_active['values'].iloc[-1]) == "1":
            plot.add_annotation(
                text="PLAYBACK ACTIVE", xref="paper", yref="paper",
                x=1.00, y=1.00, showarrow=False, font={"size": 14, "color": "black"}, 
                align="right", borderpad=4, bordercolor="black", bgcolor="red"
            )

    def format_plot(plot):
        """Apply final layout formatting to hide axes and style the legend."""
        plot.update_layout(
            polar={
                "angularaxis": {"rotation": 90, "direction": "clockwise", "visible": False},
                "radialaxis": {"visible": False, "range": [0, 1.3]}
            },
            showlegend=True, margin=dict(l=100, r=100, t=50, b=100),
            width=750, height=750, font={"size": 14, "color": "black"},
            paper_bgcolor="white",
            legend={
                "yanchor": "bottom", "y": -0.15, "xanchor": "left", "x": 0.00,
                "borderwidth": 2, "bordercolor": "black"
            }
        )

    # ---- Assemble Plot ----
    plot = go.Figure()
    current_mode = getattr(self, 'display_mode', getattr(self, 'display_toggle', 'pointers'))

    if current_mode == "time":
        build_and_add_time_labels(plot)
    else:
        build_and_add_pointer_labels(plot)

    add_record_pointer(plot)
    add_current_playback_pointer(plot)
    add_previous_playback_pointer(plot)
    add_highlighted_region(plot)
    add_datetime_annotations(plot)
    add_playback_active_annotation(plot)
    format_plot(plot)
    print(f"  - Plot generated for SSR-{self.selectedssr}...\n")
    self.plot = plot


def generate_image(self):
    """
    Executes the main orchestration logic to generate a polar plot image.

    Workflow:
      1. Determines the time window for data retrieval.
      2. Checks the power status of the selected SSR.
      3. If ON, retrieves pointer data and constructs the polar plot.
      4. Handles errors if SSR data is unavailable or parsing fails.

    Returns:
        None: The generated plot object is attached directly to `self.plot`.
    """
    self.start_date = datetime.now(timezone.utc) - timedelta(hours=self.selectedquery)
    self.end_date = datetime.now(timezone.utc) - timedelta(seconds=5)
    print(f"Checking if SSR-{self.selectedssr} is ON...")
    ssr_power = data_request(self, [f"COSSR{self.selectedssr}X"])

    try:
        # Check if the dataframe returned empty
        if ssr_power.empty:
            print(f" - (Error): No power data retrieved for SSR-{self.selectedssr}.")
            self.plot = None
            return

        # Only generate plot if SSR is powered ON (status == 1)
        if int(ssr_power['values'].iloc[-1]) == 1:
            print(f"  - SSR-{self.selectedssr} is ON...")
            get_pointers(self)
            generate_polar_plot(self)
        else:
            self.plot = None

    except Exception as error:
        print(f" - (Error) \"{error}\": Failed to generate plot for SSR-{self.selectedssr}.")
        traceback.print_exc()
        self.plot = None

    if hasattr(self, 'continuous_checkbox') and self.continuous_checkbox.isChecked():
        print("  - Continuous mode ENABLED.")
