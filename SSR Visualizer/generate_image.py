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
import plotly.graph_objects as go

warnings.filterwarnings("ignore")


def data_request(self, msid, skip=False):
    """
    Data request for a general timeframe and MSID.
    
    Args:
        self: The main application instance containing state variables.
        msid (str): The specific MAUDE MSID to query.
        skip (bool): If True, skips printing the console log for this request.
        
    Returns:
        dict: The parsed JSON response from the MAUDE API.
    """
    start = self.start_date
    stop = self.end_date

    if not skip:
        print(f"    - Requesting data for MSID: {msid} "
              f"({start.strftime('%Y:%j:%H:%M:%S')}-{stop.strftime('%Y:%j:%H:%M:%S')})...")
              
    url = (f"https://occweb.cfa.harvard.edu/maude/mrest/{self.selectedchannel.upper()}"
           f"/msid.json?m={msid}&ts={start.strftime('%Y%j.%H%M%S')}"
           f"&tp={stop.strftime('%Y%j.%H%M%S')}")
           
    with urllib.request.urlopen(url) as response:
        return json.loads(response.read())


def get_pointers(self):
    """
    Retrieves the playback and record pointers for a specified SSR 
    within the configured date range.
    
    Extracts the most recent record pointer, its exact timestamp, and 
    both current and previous playback pointers. Saves these to `self`.

    Raises:
        KeyError: If expected keys are missing in the data response.
        IndexError: If pointer values are not found in the response.
        ValueError: If pointer values cannot be converted to integers.
    """
    print("  - Getting Playback/Record Pointers...")
    pb_pointers = []
    ssr_max_val = 134217728

    # --- Find Current and Previous Playback Pointers ---
    pb_data = data_request(self, f"COS{self.selectedssr.upper()}PBPT")
    pb_data['data-fmt-1']['values'].reverse()
    pb_pointers.append(int(pb_data['data-fmt-1']['values'][0]))

    for i, val in enumerate(pb_data['data-fmt-1']['values']):
        try:
            next_val = pb_data['data-fmt-1']['values'][i+1]
            if next_val != val:
                pb_pointers.append(int(next_val))
                break
        except IndexError:
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
        plotly.graph_objs.Figure: Stores the resulting figure in `self.plot`.
    """
    # Configuration Constants
    ssr_max = 134217728
    ssr_min = 0
    angles_deg = np.linspace(0, 360, 8, endpoint=False)

    # ---------------------------------------------------------
    # Label Generation Helpers
    # ---------------------------------------------------------
    def _draw_grid_and_labels(plot, labels):
        """Helper to draw the text labels and dashed background grid lines."""
        for i, label in enumerate(labels):
            # Add text label
            plot.add_trace(go.Scatterpolar(
                r=[1.2], theta=[angles_deg[i]],
                mode="text", text=[label],
                textfont={"size": 18, "color": "black"},
                hoverinfo="skip", showlegend=False
            ))
            # Add dashed grid line
            plot.add_trace(go.Scatterpolar(
                r=[0, 1.3], theta=[angles_deg[i], angles_deg[i]],
                mode="lines", line={"color": "rgba(0,0,0,0.1)", "width": 3, "dash": "dash"},
                hoverinfo="skip", showlegend=False
            ))

    def build_and_add_pointer_labels(plot):
        """Define labels based off SSR min/max raw pointer values."""
        labels = []
        label_sum = ssr_min
        for i in range(8):
            labels.append(f"{int(label_sum):,}")
            label_sum += ((ssr_max - ssr_min) / 8)
        
        labels[0] = f"{int(label_sum):,}<br>{labels[0]}"
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
            formatted_time = future_time.strftime('%Y:%j<br>%H:%M:%S')
            labels.append(formatted_time)

        _draw_grid_and_labels(plot, labels)

    # ---------------------------------------------------------
    # Pointer Traces & Formatting
    # ---------------------------------------------------------
    def add_record_pointer(plot):
        """Add the record pointer trace (blue)."""
        rc_angle = (self.rc_pointer / (ssr_max - ssr_min)) * 360
        plot.add_trace(go.Scatterpolar(
            r=[0, 1.2], theta=[rc_angle, rc_angle],
            name=f"Record Pointer: {self.rc_pointer:,}",
            mode="lines", line={"color": "blue", "width": 4},
            hoverinfo="skip", showlegend=True
        ))

    def add_current_playback_pointer(plot):
        """Add the current playback pointer trace (solid red)."""
        pb_angle = (self.pb_pointers[0] / (ssr_max - ssr_min)) * 360
        plot.add_trace(go.Scatterpolar(
            r=[0, 1.2], theta=[pb_angle, pb_angle],
            name=f"Current Playback Pointer: {self.pb_pointers[0]:,}",
            mode="lines", line={"color": "red", "width": 4},
            hoverinfo="skip", showlegend=True
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
                line={"color": "rgba(255,0,0,0)"},
                hoverinfo="skip", showlegend=False
            ))

    def add_datetime_annotations(plot):
        """Add UI annotation detailing the execution timestamp."""
        current_time_str = datetime.now(timezone.utc).strftime('%m/%d/%Y (%Y:%j) %H:%M:%S')
        plot.add_annotation(
            text=f"{current_time_str} UTC",
            xref="paper", yref="paper",
            x=1.10, y=-0.10, showarrow=False,
            font={"size": 12, "color": "black"}, align="right",
            borderpad=4, bgcolor="rgba(0,0,0,0)"
        )

    def add_playback_active_annotation(plot):
        """Query and display an alert if playback is actively occurring."""
        print(f"  - Checking if SSR-{self.selectedssr} has an active playback...")
        playback_active = data_request(self, f"COS{self.selectedssr}PBEN")

        if playback_active['data-fmt-1']['values'][-1] == "1":
            plot.add_annotation(
                text="PLAYBACK ACTIVE", xref="paper", yref="paper",
                x=1.00, y=1.00, showarrow=False,
                font={"size": 14, "color": "black"}, align="right",
                borderpad=4, bordercolor="black", bgcolor="red"
            )

    def format_plot(plot):
        """Apply final layout formatting to hide axes and style the legend."""
        plot.update_layout(
            polar={
                "angularaxis": {"rotation": 90, "direction": "clockwise", "visible": False},
                "radialaxis": {"visible": False, "range": [0, 1.3]}
            },
            showlegend=True, 
            margin=dict(l=100, r=100, t=50, b=100),
            width=750, height=750, 
            font={"size": 14, "color": "black"},
            paper_bgcolor="white",
            legend={
                "yanchor": "bottom", "y": -0.15, 
                "xanchor": "left", "x": 0.00,
                "borderwidth": 2, "bordercolor": "black"
            }
        )

    # ---- Assemble Plot ----
    plot = go.Figure()

    # Determine display mode with a safe fallback to 'pointers'
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
    ssr_power = data_request(self, f"COSSR{self.selectedssr}X")

    try:
        # Only generate plot if SSR is powered ON (status == 1)
        if int(ssr_power['data-fmt-1']['values'][-1]) == 1:
            print(f"  - SSR-{self.selectedssr} is ON...")
            get_pointers(self)
            generate_polar_plot(self)
        else:
            self.plot = None

    except IndexError as error:
        print(f" - (Error) \"{error}\": Unable to retrieve SSR-{self.selectedssr} power data.")
        traceback.print_exc()
        self.plot = None
