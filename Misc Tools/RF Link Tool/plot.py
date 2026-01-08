import numpy as np
from scipy.special import jv
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# TRANSMITTER_POWER_W = 12.0 # High power mode
# TRANSMITTER_POWER_W = 2.0 # Low power mode
TX_ANT_GAIN_DBI = -1.25
# TX_ANT_GAIN_DBI = 3.30
# TX_ANT_GAIN_DBI = 0.00

TX_CABLE_LOSS_DB = 2.75 # Good
FREQ_MHZ = 2250 # Good
L_ATM = 0.19 # Good
L_POL = 0.22 # Good
RX_GT_DB_K = 33.63
K_BOLTZMANN_DBW = -228.599167  # 10*log10(1.380649e-23)
RX_SYSTEM_LOSS_DB = 0.6
CARRIER_LOOP_BW_HZ = 45.0      # 2B0 (Carrier Loop Noise Bandwidth)
DATA_RATE_BPS= (np.array([1024, 512, 256, 128, 64])) * 1000
SYMBOL_RATE_SPS = 1187.84 * 1000 # Specific to 1024 kbps mode
MOD_INDEX_RAD = 1.25           # theta_1 (Data)
RNG_MOD_INDEX = 0.176          # theta_2 (Ranging)
CMD_MOD_INDEX = 0.236          # theta_3 (Command turn-around)
REQUIRED_CARRIER_SNR = 10.0
REQUIRED_EBNO = 2.55
DSN_ANT_GAIN_DBI = 55.93       # DSS27 Ground Gain
DSN_MISC_LOSS_DB = 0.10        # Coupling/Misc loss in Ground Rx


def calculate_margins(altitudes, rate, mode):
    # a. EIRP and Propagation
    eirp = (10 * np.log10(2 if mode == "Low Power" else 12)) - TX_CABLE_LOSS_DB + TX_ANT_GAIN_DBI
    path_loss = 32.45 + (20 * (np.log10(FREQ_MHZ) + np.log10(altitudes)))
    rip_dbw = eirp - path_loss - L_ATM - L_POL

    # Carrier Suppression: Pc/Pt = cos^2(t1) * J0^2(t2) * J0^2(t3)
    sup_c = 10 * (np.log10(np.cos(MOD_INDEX_RAD)**2) + 
                  np.log10(jv(0, RNG_MOD_INDEX)**2) + 
                  np.log10(jv(0, CMD_MOD_INDEX)**2))

    # TLM Suppression: Pd/Pt = sin^2(t1) * J0^2(t2) * J0^2(t3)
    sup_tlm = 10 * (np.log10(np.sin(MOD_INDEX_RAD)**2) +
                    np.log10(jv(0, RNG_MOD_INDEX)**2) +
                    np.log10(jv(0, CMD_MOD_INDEX)**2))

    # Eb/No Margin
    recieved_pr_no= rip_dbw + 34.83 - K_BOLTZMANN_DBW
    playback= 10 * np.log10(rate * 1000)
    pd_no = recieved_pr_no + sup_tlm
    eb_no_net = pd_no - RX_SYSTEM_LOSS_DB - playback
    eb_no_margin = eb_no_net - REQUIRED_EBNO

    # e. Ground AGC (Received Carrier Power in dBm)
    dsn_rcvr_agc_dbm = rip_dbw + 30 + DSN_ANT_GAIN_DBI - DSN_MISC_LOSS_DB + sup_c

    return eb_no_margin, dsn_rcvr_agc_dbm


def add_plot_data(fig, rate, mode):
    "build the RF link margin plot"
    altitudes_km= np.linspace(500, 160000, 5000)
    ref_alt= 140000

    eb_no_margin, dsn_rcvr_agc_dbm=         calculate_margins(altitudes_km, rate, mode)
    eb_no_margin_ref, dsn_rcvr_agc_dbm_ref= calculate_margins(ref_alt, rate, mode)

    # Add Eb/No values
    fig.add_trace(go.Scatter(x=altitudes_km, y=eb_no_margin,
                            name= f'Eb/No Margin (dB) ({rate/1000})', 
                            line=dict(color='green', width=2)))

    fig.add_trace(go.Scatter(x=altitudes_km, y=dsn_rcvr_agc_dbm, name= 'DSN RCVR AGC /w Ranging (dBm)', 
                            line=dict(color='orange', width=2, dash='dash')),
                            secondary_y= True)

    # Vertical Reference Line at 140,000 km
    fig.add_vline(x=ref_alt, line_dash="dash", line_color="red", opacity=0.7)
    
    # Horizontal Reference Lines
    fig.add_hrect(y0= 0, y1=-77, fillcolor= "LightSalmon", layer= "below", opacity=0.3,
                  secondary_y= True, line_width= 0)

    # Annotations for reference point
    fig.add_annotation(x=ref_alt, y=dsn_rcvr_agc_dbm_ref, text=f"{dsn_rcvr_agc_dbm_ref:.2f} dBm",
                       showarrow=True, font= dict(color= "#FFFFFF"), yref="y2")
    fig.add_annotation(x=ref_alt, y=eb_no_margin_ref, text=f"{eb_no_margin_ref:.2f} dB",
                       showarrow=True, font= dict(color= "#FFFFFF"))
    fig.add_annotation(x=80000, y=-70, text="DSN RCVR Hazard Zone",
                       showarrow= False, font= dict(color= "#FFFFFF", size= 40), yref="y2")

    return fig


def format_plot(fig):
    "Final formatting of the plot object after generation"
    fig.update_layout(
        title= dict(text= f"AXAF Link Budget Analysis",
                    font= dict(color= "#FFFFFF")),
        paper_bgcolor= "#202020", plot_bgcolor= "#000000",
        height= 1000, width= 1250,
        showlegend= False, hovermode= "x unified",
        hoverlabel= dict(bgcolor= "#333333", font= dict(color= "#FFFFFF", size= 14)),
        )

    fig.update_xaxes(
        title= dict(text= "Altitude (km)", font= dict(color= "#FFFFFF")),
        color= "#FFFFFF"
    )

    # Y-Axis 1 & 2
    getattr(fig.layout, "yaxis").title.text= "Eb/No Margin (dB)"
    getattr(fig.layout, "yaxis").title.font.color= "#FFFFFF"
    getattr(fig.layout, "yaxis").color= "#FFFFFF"
    getattr(fig.layout, "yaxis").range= [-5, 100]

    getattr(fig.layout, "yaxis2").title.text= "DSN RCVR AGC /w Ranging (dBm)"
    getattr(fig.layout, "yaxis2").title.font.color= "#FFFFFF"
    getattr(fig.layout, "yaxis2").color= "#FFFFFF"
    getattr(fig.layout, "yaxis2").range= [-170, -60]

    # X-Axis
    getattr(fig.layout, "xaxis").title.text= "Altitude (km)"
    getattr(fig.layout, "xaxis").color= "#FFFFFF"
    getattr(fig.layout, "xaxis").title.font.color= "#FFFFFF"

    fig.update_annotations(font_color="#FFFFFF")


def generate_plot(rate, mode):
    # Init plotly object
    fig= make_subplots(rows= 1, cols= 1, shared_xaxes= True,
                        vertical_spacing= 0.04, specs= [[{"secondary_y": True}]])
    add_plot_data(fig, rate, mode)
    format_plot(fig)

    return fig
