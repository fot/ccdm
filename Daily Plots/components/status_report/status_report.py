"Generate the Status Report"

from datetime import datetime
from components.misc import make_output_dir, format_doy
from components.status_report.components.spurious_cmd_lock_detection import (
    spurious_cmd_lock_detection)
from components.status_report.components.vcdu_rollover_detection import vcdu_rollover_detection
from components.status_report.components.ssr_rollover_detection import ssr_rollover_detection
from components.status_report.components.sequencer_selftest_detection import (
    sequencer_selftest_detection)
from components.status_report.components.scs107_detection import scs107_detection
from components.status_report.components.tlm_corruption_detection import tlm_corruption_detection
from components.status_report.components.obc_error_detection import obc_error_detection
from components.status_report.components.limit_detection import limit_violation_detection
from components.status_report.components.dbe_detection import dbe_detection
from components.status_report.components.cmd_processor_reset_detection import cmd_processor_reset_detection
from components.status_report.components.weeks_without_paul import weeks_without_paul


def generate_status_report(user_vars, auto_gen= False):
    "write the status report file"
    print(" - Generating CCDM status report .txt file...")
    set_dir= make_output_dir(user_vars, auto_gen)

    if auto_gen:
        file_title= "CCDM Status Report (Auto-Gen 14-Day Lookback)"
    else:
        file_title= (
            f"CCDM Status Report ({user_vars.year_start}{user_vars.doy_start}_"
            f"{user_vars.year_end}{user_vars.doy_end})"
        )

    with open(f"{set_dir}/{file_title}.txt", "w+", encoding= "utf-8") as file:
        file.write(f"{file_title}\n(Generated on "
                   f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC)\n"
                   f"{'-'*145}\n{'-'*145}\n")
        tlm_corruption_detection(user_vars, file)
        obc_error_detection(user_vars, file)
        limit_violation_detection(user_vars, file)
        dbe_detection(user_vars, file)
        misc_detection(user_vars, file)
        file.close()

    print(f"""\nDone! Data written to "{file_title}.txt" in "{set_dir}".""")


def misc_detection(user_vars, file):
    "Add misc detection items to report file"
    print("\nMisc Detection Items...")
    file.write(
        f"Misc Detected Items for {user_vars.year_start}:{format_doy(user_vars.doy_start)} "
        f"thru {user_vars.year_end}:{format_doy(user_vars.doy_end)}\n\n" + "-"*87 + "\n")

    vcdu_rollover_detection(user_vars,file)
    spurious_cmd_lock_detection(user_vars,file)
    ssr_rollover_detection(user_vars,file)
    sequencer_selftest_detection(user_vars,file)
    scs107_detection(user_vars,file)
    cmd_processor_reset_detection(user_vars,file)
    weeks_without_paul(file)

    file.write("\n  ----------END OF MISC DETECTION----------")
    file.write("\n" + "-"*149 + "\n" + "-"*149 + "\n")
    print(" - Done! Data written to Misc section.")
