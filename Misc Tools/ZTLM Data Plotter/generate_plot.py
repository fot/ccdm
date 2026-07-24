import plotly.express as px
from binary_convert import decode_telemetry

def build_plot(gui_instance):
    """Build a plotly figure from the binary file using pandas."""
    
    # 1. Update the GUI console to show the parsing has started
    gui_instance.log(f"[INFO] Parsing binary data from: {gui_instance.selected_file}")
    
    # 2. Decode the binary file into a DataFrame
    df = decode_telemetry(gui_instance.selected_file)

    # 3. Requested channels from GUI box
    requested_channels = gui_instance.get_selected_channels()

    # 4. Filter columns if specific channels are requested
    if requested_channels:
        # Find which requested channels actually exist in the DataFrame columns
        valid_channels = [ch for ch in requested_channels if ch in df.columns]
        missing_channels = [ch for ch in requested_channels if ch not in df.columns]

        if missing_channels:
            gui_instance.log(f"[WARNING] Channels not found in data: {', '.join(missing_channels)}")

        if valid_channels:
            gui_instance.log(f"[INFO] Plotting filtered channels: {', '.join(valid_channels)}")
            # Keep index (time/frame) along with the selected valid columns
            plot_df = df[valid_channels]
        else:
            gui_instance.log("[WARNING] None of the requested channels matched. Falling back to all columns.")
            plot_df = df
    else:
        gui_instance.log("[INFO] No specific channels entered. Plotting all available channels.")
        plot_df = df

    # 3. Create a single interactive plot with all channels
    gui_instance.log("[INFO] Building Plotly traces...")
    fig = px.line(
        plot_df, x = df.index, y = df.columns,
        title="Telemetry Channels",
        labels={"value": "Amplitude", "index": "Time", "variable": "Channels"}
    )

    # 4. Apply a dark theme to match the PyQt5 GUI
    fig.update_layout(
        template="plotly_dark",
        hovermode="x unified",
        autosize=True, 
        showlegend=True
    )

    return fig
