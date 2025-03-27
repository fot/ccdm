"""
v1.6 Change Notes:
 - Improves SSR rollover detection
"""

from datetime import datetime,timezone
import urllib.request
from os import system
import warnings
import time
import pandas as pd
from cxotime import CxoTime
from components.obc_error_detection import (
    get_obc_report_dirs, get_obc_error_reports, write_obc_errors)
from components.vcdu_rollover_detection import vcdu_rollover_detection
from components.limit_violation_detection import (
    get_limit_report_dirs, get_limit_reports, write_limit_violations)
from components.eia_sequencer_selftest_detection import sequencer_selftest_detection
from components.scs107_detection import scs107_detection
from components.misc import create_dir,HTML_HEADER,HTML_SCRIPT
from components.ssr import (get_ssr_data, get_ssr_beat_report_data, ssr_rollover_detection,
                            make_ssr_by_submod, make_ssr_by_doy, make_ssr_full, get_wk_list)
from components.receiver import (get_receiver_data, spurious_cmd_lock_detection,
                                 write_spurious_cmd_locks)
warnings.filterwarnings('ignore')


class UserVariables:
    "User defined variables"
    def __init__(self):
        system('clear')
        self.get_start_date()
        self.get_end_date()
        self.get_dir_path()
        self.get_ssr_prime()
        self.get_major_events()
        self.get_cdme_performance_events()
        self.get_rf_performance_events()
        self.get_limit_violation_events()
        self.get_tlm_corruption_events()
        self.get_cdme_misc_comments()

    def get_start_date(self):
        "User input for start date"
        while True:
            user_input= input('Enter the START date YYYY:DOY: ')
            try:
                ts= CxoTime(f"{user_input[:4]}:{user_input[-3:]}:00:00:00.000")
            except ValueError:
                print(f' - Input "{user_input}" was not in the correct format, try again.')
                continue

            if ((2001 <= ts.datetime.year <= datetime.now(timezone.utc).year) and
                (len(user_input) == 8) and (1 <= int(ts.datetime.strftime("%j")) <= 366)):
                break
            print(f' - Input "{user_input}" was not a valid date, try again.')

        self.ts= ts

    def get_end_date(self):
        "User input for end date"
        while True:
            user_input= input('Enter the END date YYYY:DOY: ')
            try:
                tp= CxoTime(f"{user_input[:4]}:{user_input[-3:]}:23:59:59.999")
            except ValueError:
                print(f' - Input "{user_input}" was not in the correct format, try again.')
                continue

            if ((2001 <= self.ts.datetime.year <= tp.datetime.year) and
                (len(user_input) == 8) and (1 <= int(tp.datetime.strftime("%j")) <= 366)):
                break
            print(f' - Input "{user_input}" was invalid, try again.')

        self.tp= tp

    def get_dir_path(self):
        "User input for set directory"
        self.set_dir = "/share/FOT/engineering/ccdm/Tools/Weekly"
        print(f"Set directory is: {self.set_dir}")

    def get_ssr_prime(self):
        "User input for SSR prime"
        self.ssr_prime = ["A","2025:032:03:34:11"]
        print(f"Prime SSR is set at: {self.ssr_prime}")

    def get_major_events(self):
        "User input for Major events this week"
        while True:
            major_events_list = []
            print(
                "\n----Major Events Input----\n"
                "   Enter unexpected events that occured for the reporting week, "
                "(ie, CTU TLM processor resets, ect...)"
                """\n   Enter nothing when completed with Major Event Inputs."""
            )

            while True:
                input_item = input("   - Input: ")
                if input_item in (""):
                    break
                major_events_list.append(input_item)
            self.major_events_list = major_events_list
            valid_input = input("   Major Events Input(s) Accurate? Y/N: ")

            if valid_input in ("y","Y","yes","YES"):
                break

            print("    - Clearing Major Events list...")
            time.sleep(0.5)

    def get_cdme_performance_events(self):
        "User input for CDME Performance Notes for this week."
        while True:
            cdme_performance_list = []
            print(
                "\n----CDME Performance Events Input----\n"
                "   Enter any info about any off-nominal behavior that occured for the "
                "reporting week, (ie, IU resets, CTU CMD processor resets, ect...)"
                """\n   Enter nothing when completed with CDME Performance Note Inputs."""
            )
            while True:
                input_item = input("   - Input: ")
                if input_item in (""):
                    break
                cdme_performance_list.append(input_item)

            self.cdme_performance_list = cdme_performance_list
            valid_input = input("   CDME Perf Input(s) Accurate? Y/N: ")

            if valid_input in ("y","Y","yes","YES"):
                break

            print("    - Clearing CDME Perf list...")
            time.sleep(0.5)

    def get_rf_performance_events(self):
        "User input for RF Performance Notes for this week."
        while True:
            rf_performance_list = []
            print(
                "\n----RF Performance Events Input----\n"
                "   Enter any info about any off-nominal behavior that occured for the reporting "
                "week, (ie, unexpected command lock drops, ect...)"
                """\n   Enter nothing when completed with CDME Performance Note Inputs."""
            )
            while True:
                input_item = input("   - Input: ")
                if input_item in (""):
                    break
                rf_performance_list.append(input_item)

            self.rf_performance_list = rf_performance_list
            valid_input = input("   RF Perf Input(s) Accurate? Y/N: ")

            if valid_input in ("y","Y","yes","YES"):
                break

            print("    - Clearing RF Perf list...")
            time.sleep(0.5)

    def get_limit_violation_events(self):
        "User input for non-automated limit violations"
        while True:
            limit_violations_list = []
            print(
                "\n----Limit Violation (Non-Autogen) Input----\n"
                "   Enter any additional limit violations that aren't handled automatically "
                "(ie, non-CCDM limit violations, ect...)"
                """\n   Enter nothing when completed with CDME Performance Note Inputs."""
            )
            while True:
                input_item = input("   - Input: ")
                if input_item in (""):
                    break
                limit_violations_list.append(input_item)

            self.limit_violations_list = limit_violations_list
            valid_input = input("   Limit Violation Input(s) Accurate? Y/N: ")

            if valid_input in ("y","Y","yes","YES"):
                break

            print("    - Clearing Limit Violations list...")
            time.sleep(0.5)

    def get_tlm_corruption_events(self):
        "User input for Telemetry Corrcution Events for this week."
        while True:
            tlm_corruption_list = []
            print(
                "\n----Telemetry Corruption Input(s)----\n"
                "   Enter info about any telemetry corruption that occured for the reporting week, "
                """\n   Enter nothing when completed with Telemetry Corruption Note Inputs."""
            )
            while True:
                input_item = input("   - Input: ")
                if (input_item in ("")) and (len(tlm_corruption_list) == 0):
                    tlm_corruption_list.append("Nominal.")
                    break
                if input_item in (""):
                    break
                tlm_corruption_list.append(input_item)

            self.tlm_corruption_list = tlm_corruption_list
            valid_input = input("   Telemetry Corruption Input(s) Accurate? Y/N: ")

            if valid_input in ("y","Y","yes","YES"):
                break

            print("    - Clearing Telemetry Corruption list...")
            time.sleep(0.5)

    def get_cdme_misc_comments(self):
        "User input for CDME misc comments for this week."

        while True:
            cdme_misc_comments_list = []
            print(
                "\n----CDME Misc Comment Input(s)----\n"
                "   Enter any additional comments that occured for the reporting week, "
                """\n   Enter nothing when completed with CDME Misc Note Inputs."""
            )
            while True:
                input_item = input("   - Input: ")
                if input_item in (""):
                    break
                cdme_misc_comments_list.append(input_item)
            valid_input = input("   CDME Misc Comment Input(s) Accurate? Y/N: ")

            if valid_input in ("y","Y","yes","YES"):
                break

            print("    - Clearing CDME Misc Comment list...")
            time.sleep(0.5)
        self.cdme_misc_comments_list = cdme_misc_comments_list


def get_dsn_drs(ts,tp):
    "return a table of DR reports from iFOT"
    url = (
        "https://occweb.cfa.harvard.edu/occweb/web/webapps/ifot/ifot.php?r=home&t=qserver&a=show&"
        "format=list&columns=id,type_desc,tstart,properties&size="
        f"auto&e=DSN_DR.problem&op=properties&tstart={ts}+&tstop={tp}&ul=12"
        )
    with urllib.request.urlopen(url) as response:
        return pd.read_html(response.read())


def build_config_section(user_vars, data):
    "build the CONFIGURATION section of the report"

    config_section = (
        """<div class="output_area">"""
        """<div class="output_markdown rendered_html output_subarea ">"""
        """<p><strong>CONFIGURATION:</strong></p></div></div>"""
        """<div class="output_area">"""
        """<div class="output_markdown rendered_html output_subarea ">"""
    )

    # CDME Section
    config_section += (
        "<div><div><ul><li><strong>CDME:</strong><ul>"
        "<li>All A-side Equipment is in use</li>"
        f"<li>SSR-{user_vars.ssr_prime[0]} selected as "
        f"Prime since {user_vars.ssr_prime[1]}</li>"
    )

    for list_item in user_vars.cdme_misc_comments_list:
        config_section += (
            f"""<li>{list_item}</li>"""
        )

    # CDME Section - SSR Rollover Detection
    config_section += ssr_rollover_detection(user_vars)

    # RF Section
    config_section += (
        "<div><div><ul><li><strong>RF:</strong><ul>"
        f"<li><strong>{data.num_supports}</strong> DSN Supports this week</li>"
        f"<li><strong>{data.tx_a_on}</strong> TX-A/PA-A</li>"
        f"<li><strong>{data.tx_b_on}</strong> TX-B/PA-B</li>"
        )
    config_section += "</li></ul></div></div>"

    # Bad Visibility Days Section
    config_section += (
        "<div><div><ul><li><strong>Bad Visibility Days:</strong><ul>"
        f"<li>Receiver-A: {str(list(data.a_bad.keys()))}</li>"
        f"<li>Receiver-B: {str(list(data.b_bad.keys()))}</li>"
    )
    config_section += "</li></ul></div></div>"

    # DSN DR(s) Section
    config_section += (
        "<div><div><ul><li><strong>DSN DRs this week:</strong><ul>"
    )
    tmp = get_dsn_drs(user_vars.ts,user_vars.tp)
    df = tmp[0]
    result = df.to_html(
        classes="table table-stripped",
        # columns=["Event ID >","< Type Description >","< TStart (GMT) >","< DSN_DR.problem"],
        )
    if len(df) > 1:
        config_section += result
    else:
        config_section += "<li>No DSN DRs this week</li>"
    config_section += "</li></ul></div></div>"

    return config_section


def build_perf_health_section(user_vars):
    "Build the Performance and Healtlh Section"
    perf_health_dict = {
        "CDME": user_vars.cdme_performance_list,
        "RF Equipment": user_vars.rf_performance_list,
        "Limit Violations": user_vars.limit_violations_list,
        "Telemtry Corruption": user_vars.tlm_corruption_list
    }
    perf_health_section = (
        """<div class="output_area">"""
        """<div class="output_markdown rendered_html output_subarea ">"""
        """<p><strong>PERFORMANCE & HEALTH:</strong></p></div></div>"""
        """<div class="output_area">"""
        """<div class="output_markdown rendered_html output_subarea ">"""
    )
    tlm_corrup_link = "https://occweb.cfa.harvard.edu/twiki/bin/view/SC_Subsystems/CcdmTlmCorrupt"

    for title, string_list in perf_health_dict.items():
        perf_health_section += (
            f"<div><div><ul><li><strong>{title}:</strong><ul>\n"
                )

        for list_item in string_list: # User Inputted Items
            perf_health_section += (
                f"""<li>{list_item}</li>\n"""
            )

        if "CDME" in title:
            obc_error_files = get_obc_report_dirs(user_vars)
            obc_error_report_data = get_obc_error_reports(obc_error_files)

            if obc_error_report_data:
                perf_health_section += write_obc_errors(obc_error_report_data)
            elif not user_vars.cdme_performance_list:
                perf_health_section += ("<li>Nominal.</li>\n")

        elif "RF Equipment" in title:
            spurious_cmd_locks = spurious_cmd_lock_detection(user_vars)

            if spurious_cmd_locks:
                perf_health_section += write_spurious_cmd_locks(spurious_cmd_locks)
            else:
                perf_health_section += ("<li>Nominal.</li>\n")

        elif "Limit Violations" in title:
            limit_dir_list = get_limit_report_dirs(user_vars)
            limit_data = get_limit_reports(limit_dir_list)

            if limit_data:
                perf_health_section += write_limit_violations(limit_data)
            elif not user_vars.limit_violations_list:
                perf_health_section += ("<li>Nominal.</li>\n")

        elif "Telemtry Corruption" in title:
            perf_health_section += (
                f"""<li><a href="{tlm_corrup_link}">List of Telemetry Corruption Events"""
                "</a></li>\n"
                )

        perf_health_section += "</li></ul></div></div>"

    return perf_health_section


def build_ssr_dropdown(user_vars, all_beat_report_data):
    "Build the SSR stats dropdown menus"
    plot_title_dict= {
        "A": ["SSR-A Current Week Time Strip","SSR-A Year-to-Date By Submodule",
              "SSR-A Year-To-Date By Day-of-Year","SSR-A Year-to-Date Full Time Strip"],
        "B": ["SSR-B Current Week Time Strip","SSR-B Year-to-Date By Submodule",
              "SSR-B Year-To-Date By Day-of-Year","SSR-B Year-to-Date Full Time Strip"],
    }
    plot_loc= ("https://occweb.cfa.harvard.edu/occweb/FOT/engineering/ccdm/Current_CCDM_Files"
                f"/Weekly_Reports/SSR_Weekly_Charts/{user_vars.ts.datetime.year}")
    dropdown_string, url= "",""
    output_width, output_height= 1074, 710

    for ssr, plot_titles in plot_title_dict.items():
        dropdown_string += (
            """</div>"""
            """<p></p>"""
            f"""<button type="button" class="collapsible">SSR-{ssr} Plots</button>"""
            """<div class="content">\n""")

        for plot_title in plot_titles:
            if "Current Week Time Strip" in plot_title:
                make_ssr_full(ssr,user_vars,all_beat_report_data,"Cur_TimeStrip")
                url=  (f"{plot_loc}/SSR_{ssr}_{user_vars.ts.datetime.year}_"
                       f"{user_vars.ts.datetime.strftime("%j").zfill(3)}_Cur_TimeStrip.html")
            elif "Year-to-Date By Submodule" in plot_title:
                make_ssr_by_submod(ssr,user_vars,all_beat_report_data,"YTD_by_SubMod")
                url=  (f"{plot_loc}/SSR_{ssr}_{user_vars.ts.datetime.year}_"
                       f"{user_vars.ts.datetime.strftime('%j').zfill(3)}_YTD_by_SubMod.html")
            elif "Year-To-Date By Day-of-Year" in plot_title:
                make_ssr_by_doy(ssr,user_vars,all_beat_report_data,"YTD_by_DoY")
                url= (f"{plot_loc}/SSR_{ssr}_{user_vars.ts.datetime.year}_"
                      f"{user_vars.ts.datetime.strftime('%j').zfill(3)}_YTD_by_DoY.html")
            elif "Year-to-Date Full Time Strip" in plot_title:
                make_ssr_full(ssr,user_vars,all_beat_report_data,"YTD_Timestrip",True)
                url= (f"{plot_loc}/SSR_{ssr}_{user_vars.ts.datetime.year}_"
                      f"{user_vars.ts.datetime.strftime('%j').zfill(3)}_YTD_Timestrip.html")
            dropdown_string += (
                f"""<button type="button" class="collapsible">{plot_title}</button>"""
                """<div class="content">"""
                f"""<p><iframe src={url} width=\"{output_width}\" height=\"{output_height}\">"""
                """</iframe></p></div>\n""")
    dropdown_string += "</body></li></ul></div></div>"

    return dropdown_string


def build_ssr_playback_section(user_vars, ssr_data, all_beat_report_data):
    "Build the SSR playback section of the report"

    plot_loc = ("https://occweb.cfa.harvard.edu/occweb/FOT/engineering/ccdm/"
                "Current_CCDM_Files/Weekly_Reports/SSR_Weekly_Charts/")

    plot_explainer_pptx = ("https://occweb.cfa.harvard.edu/occweb/FOT/engineering/ccdm/"
                           "Current_CCDM_Files/Weekly_Reports/SSR_Weekly_Charts/"
                           "SSR_Timestrip_Chart_Explainer.pptx")

    ssr_playback_section = (
        """<div class="output_area">"""
        """<div class="output_markdown rendered_html output_subarea ">"""
        """<p><strong>SSR Playback Analysis:</strong></p></div></div>"""
        """<div class="output_area">"""
        """<div class="output_markdown rendered_html output_subarea ">"""
        f"""<li><strong>{ssr_data.ssra_good}</strong> SSR-A Playbacks were successful """
        f"""(<strong>{ssr_data.ssra_bad}</strong> required re-dump)</li>"""
        f"""<li><strong>{ssr_data.ssrb_good}</strong> SSR-B Playbacks were successful """
        f"""(<strong>{ssr_data.ssrb_bad}</strong> required re-dump)</li>"""
        f"""<li><strong>{get_wk_list(user_vars,all_beat_report_data)}</strong> submodules """
        f"""with DBEs were detected in <strong>{ssr_data.ssra_good + ssr_data.ssrb_good}"""
        """</strong> playbacks</li>""")

    ssr_playback_section += (
        """<div class="output_area">"""
        """<div class="output_markdown rendered_html output_subarea ">"""
        """<p><strong>SSR DBE Plot Links:</strong></p></div></div>"""
        """<div class="output_area">"""
        """<div class="output_markdown rendered_html output_subarea ">"""
        f"""<li><a href="{plot_loc}">SSR DBE Plot Archive</a> | """
        f"""<a href="{plot_explainer_pptx}">SSR DBE Plot Archive</a></li>""")

    if user_vars.ts.datetime.year == user_vars.tp.datetime.year:
        ssr_playback_section += build_ssr_dropdown(user_vars, all_beat_report_data)
    else:
        ssr_playback_section += ("<p><li>SSR Plots are unavaliable for a date "
                                 "range spanning a new year.</p></li></div>")
    ssr_playback_section += "</body></li></ul></div></div>"

    return ssr_playback_section


def build_clock_correlation_section(user_vars):
    "Build the Clock Correlation Data section of the report"

    clock_corr_section = (
        """<div class="output_area">"""
        """<div class="output_markdown rendered_html output_subarea ">"""
        """<p><strong>Clock Correlation Data:</strong></p></div></div>"""
        """<div class="output_area">"""
        """<div class="output_markdown rendered_html output_subarea ">""")
    clock_correlation_link = (
        "https://occweb.cfa.harvard.edu/occweb/web/fot_web/eng/subsystems/ccdm/"
        f"Clock_Rate/Clock_Correlation{user_vars.ts.datetime.year}.htm")
    daily_clock_rate_link = (
        "https://occweb.cfa.harvard.edu/occweb/web/fot_web/eng/subsystems/ccdm/"
        f"Clock_Rate/images/{user_vars.ts.datetime.year}_Daily_Clock_Rate.png")
    uso_stability_link = (
        "https://occweb.cfa.harvard.edu/occweb/web/fot_web/eng/subsystems/ccdm/"
        "Clock_Rate/Clock_Rateindex.htm")
    clock_link_dict = {
        f"Clock Correlation Table {user_vars.ts.datetime.year}":
            f"""<iframe src={clock_correlation_link} width=\"800\" height=\"700\"></iframe>""",
        f"Daily Clock Rate {user_vars.ts.datetime.year}":
            f"""<img src={daily_clock_rate_link} width=\'1000\' height=\"700\"></img>""",}

    clock_corr_section += HTML_HEADER

    for plot_title, plot_link in clock_link_dict.items():
        clock_corr_section += (f"""
            <button type="button" class="collapsible">{plot_title}</button>
            <div class="content"><p>{plot_link}</p></div><p></p>\n""")

    clock_corr_section += HTML_SCRIPT

    clock_corr_section += (
        f"""<ul><li><a href="{uso_stability_link}">Link to USO Stability"""
        " - Clock Correlation Data</a></li></ul>\n")

    clock_corr_section += "</body></li></ul></div></div>"

    return clock_corr_section


def build_major_events_section(user_vars):
    "Build the Major Events section of the report."

    uso_link = "https://occweb.cfa.harvard.edu/twiki/bin/view/SC_Subsystems/EiaSelfTests"

    major_event_section = (
        """<div class="output_area">"""
        """<div class="output_markdown rendered_html output_subarea ">"""
        """<p><strong>Major Events:</strong></p></div></div>"""
        """<div class="output_area">"""
        """<div class="output_markdown rendered_html output_subarea ">""")

    for list_item in user_vars.major_events_list:
        major_event_section += f"<li>{list_item}</li>"

    # VCDU rollover detection
    vcdu_rollover_string = vcdu_rollover_detection(user_vars)
    if vcdu_rollover_string:
        major_event_section += vcdu_rollover_string

    # EIA Sequencer Self-Test Detection
    eia_sequencer_selftest_string = sequencer_selftest_detection(user_vars)
    if eia_sequencer_selftest_string:
        major_event_section += eia_sequencer_selftest_string

    # SCS107 Detection
    scs107_string = scs107_detection(user_vars)
    if scs107_string:
        major_event_section += scs107_string

    major_event_section += (
        f"""<li><a href="{uso_link}">List of EIA Sequencer Self Tests</a></li>"""
    )
    major_event_section += "</li></ul></div></div>"

    return major_event_section


def build_report(user_vars, ssr_data, all_beat_report_data, receiver_data):
    "Build the report using all queried data."
    print("Assembling the report...")

    file_title= ("""<div class="output_area"><div class="output_markdown """
                  f"""rendered_html output_subarea "><p><strong>CCDM Weekly Report from """
                  f"""{user_vars.ts.datetime.year}:{user_vars.tp.datetime.strftime("%j")} """
                  f"""through {user_vars.tp.datetime.year}:{user_vars.ts.datetime.strftime("%j")}"""
                  """</strong></p></div></div>""")
    horizontal_line= ("""<div class="output_area">"""
                       """<div class="output_markdown rendered_html output_subarea">"""
                       """<hr></div></div>""")

    config_section= build_config_section(user_vars, receiver_data)
    perf_health_section= build_perf_health_section(user_vars)
    ssr_playback_section= build_ssr_playback_section(user_vars, ssr_data, all_beat_report_data)
    clock_correlation_section= build_clock_correlation_section(user_vars)
    major_event_section= build_major_events_section(user_vars)

    html_output= (
        file_title + horizontal_line + config_section + horizontal_line + perf_health_section +
        horizontal_line + ssr_playback_section + horizontal_line + clock_correlation_section +
        horizontal_line + major_event_section + horizontal_line
    )

    file_name = (f"CCDM_Weekly_{user_vars.ts.datetime.strftime("%Y%j")}"
                 f"_{user_vars.tp.datetime.strftime("%Y%j")}.html")

    create_dir(f"{user_vars.set_dir}/{user_vars.ts.datetime.year}")

    with open(f"{user_vars.set_dir}/{user_vars.ts.datetime.year}/{file_name}",
              "w",encoding="utf-8") as file:
        file.write(html_output)
        file.close()


def main():
    "Main execution"
    user_vars = UserVariables()
    ssr_data= get_ssr_data(user_vars)
    all_beat_report_data= get_ssr_beat_report_data(user_vars)
    receiver_data= get_receiver_data(user_vars)
    build_report(user_vars, ssr_data, all_beat_report_data, receiver_data)


main()
