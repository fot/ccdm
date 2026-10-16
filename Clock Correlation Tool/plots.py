"""
This module contains functions for generating plots related to clock replacement analysis.
"""

import numpy as np
import plotly.graph_objects as go

# Local Imports
from misc import log_callback


def generate_residual_plot(results_df, output_path):
    """
    Generates an interactive Plotly graph matching the classic MATLAB figure aesthetic.
    """
    resid_musec= results_df['global_resid_musec'].values
    vcdu= results_df['vcdu'].values
    frames= np.arange(1, len(vcdu) + 1)

    # MATLAB Statistics
    rms_val= np.sqrt(np.mean(resid_musec**2))
    max_val, min_val= np.max(resid_musec), np.min(resid_musec)
    max_abs_resid= max(abs(max_val), abs(min_val))

    # Dynamic Titles
    start_dt, end_dt= results_df['datetime'].iloc[0], results_df['datetime'].iloc[-1]
    year, day1, day2= start_dt.strftime('%Y'), start_dt.strftime('%j'), end_dt.strftime('%j')

    title_line1= f"Chandra Clock Correlation Residuals for {year}:{day1} to {year}:{day2}"
    title_line2= f"RMS = {rms_val:.2f} μsec, max = {max_abs_resid:.2f} μsec"

    plot_min_y, plot_max_y= min(-10, np.floor(min_val)), max(10, np.ceil(max_val))

    fig= go.Figure()

    fig.add_trace(go.Scatter(
        x= frames,
        y= resid_musec,
        mode= 'markers',
        name= 'Raw Residuals',
        marker= dict(color='#0000FF', size=4)
    ))

    fig.update_layout(
        title= {
            'text': f"<b>{title_line1}</b><br><span style='font-size: 14px;'>{title_line2}</span>",
            'x': 0.5, 
            'xanchor': 'center', 
            'font': dict(family="Arial, sans-serif", color="black")
        },
        xaxis_title= 'Telemetry Frame Number (VCDU)',
        yaxis_title= 'Timing Error (μsec)',
        plot_bgcolor= 'white',
        paper_bgcolor= '#f0f0f0',
        showlegend= False,
        margin= dict(l= 60, r= 40, t= 80, b= 60)
    )

    fig.update_xaxes(
        range=[0, len(frames)], showgrid=False, zeroline=False,
        showline=True, linewidth=1.5, linecolor='black', mirror=True,
        ticks='inside', tickwidth=1.5, tickcolor='black', ticklen=6
    )

    fig.update_yaxes(
        range=[plot_min_y, plot_max_y], showgrid=False, zeroline=False,
        showline=True, linewidth=1.5, linecolor='black', mirror=True,
        ticks='inside', tickwidth=1.5, tickcolor='black', ticklen=6
    )

    # Write output based on file extension
    if output_path.suffix.lower() == '.html':
        fig.write_html(output_path, include_plotlyjs='cdn', full_html=True)

    elif output_path.suffix.lower() == '.png':
        fig.write_image(output_path, scale=2)

    else:
        raise ValueError("Unsupported file format. Please use .html or .png.")

    log_callback(f"Residual plot saved to {output_path.name}")
