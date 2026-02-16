"Module to detect CMD Processor Resets in the CTU"

from datetime import timedelta
from dataclasses import dataclass
from cxotime import CxoTime
from components.tlm_request import data_request


@dataclass
class CommandProcessorReset:
    """
    Class to track the reset datetimes for command processors A and B.
    Attributes:
        reset_a_datetime: The datetime when command processor A was reset.
        reset_b_datetime: The datetime when command processor B was reset.
    """
    reset_a_datetime: None
    reset_b_datetime: None


def cmd_processor_reset_detection(user_vars,file):
    """
    Detects command processor resets and writes a summary to the provided file.
    Args:
        user_vars (dict): A dictionary containing user-specific variables required for detection.
        file (file-like object): An open file or file-like object to which the reset detection
                                 results will be written.
    Behavior:
        - Calls `detect_cmd_processor_reset` with `user_vars` to obtain a list of reset events.
        - For each detected reset, writes a message to the file indicating the CTU (A or B)
          and the reset datetime.
        - If no resets are detected, write default message.
    """
    print(" - Command Processor Reset Detection...")
    cmd_processor_resets= detect_cmd_processor_reset(user_vars)

    if cmd_processor_resets:
        for cmd_processor_reset in cmd_processor_resets:
            if cmd_processor_reset.reset_a_datetime is not None:
                response= (f"A Command Processor reset was found on CTU-A "
                           f"at {cmd_processor_reset.reset_a_datetime}.")
                print(f"   - {response}")
                file.write(f"  - {response}\n")
            elif cmd_processor_reset.reset_a_datetime is not None:
                response= (f"A Command Processor reset was found on CTU-B "
                           f"at {cmd_processor_reset.reset_b_datetime}.")
                print(f"   - {response}")
                file.write(f"  - {response}\n")
    else:
        response= "No Command Processor resets found."
        print(f"   - {response}")
        file.write(f"  - {response}\n")


def detect_cmd_processor_reset(user_vars):
    """
    Detects command processor resets by analyzing telemetry data for specific reset signatures.
    This function examines the "CULACC" telemetry channel for reset events, identified by a value
    drop to 0 that is not caused by a rollover (i.e., previous value is not 65535), and then checks
    for corresponding resets in the "CMRJCNTA" and "CMRJCNTB" channels within a 1-second window
    around the detected reset time. It ensures that these resets are not due to rollover (previous
    value is not 255).
    Args:
        user_vars: An object containing user-specified variables, including time start (`ts`) and
            time stop (`tp`).
    Returns:
        list: A list of CommandProcessorReset objects, each containing the datetime of detected
        resets for CMRJCNTA and CMRJCNTB channels.
    """
    data_accept= data_request(user_vars.ts, user_vars.tp, "SKA High Rate", "CULACC")
    data_point, data_points= CommandProcessorReset(None,None), []

    for i, (value_accept, time_accept) in enumerate(zip(data_accept.vals, data_accept.times)):
        try:
            if ((value_accept == 0) and
                (data_accept.vals[i-1] != 65535) and
                (value_accept < data_accept.vals[i-1])):
                reset_time= CxoTime(time_accept)
                data_reject_a= data_request(
                    reset_time - timedelta(minutes= 0.5), reset_time + timedelta(minutes= 0.5),
                    "SKA High Rate", "CMRJCNTA")
                data_reject_b= data_request(
                    reset_time - timedelta(minutes= 0.5), reset_time + timedelta(minutes= 0.5),
                    "SKA High Rate", "CMRJCNTB")

                # Check if CMRJCNTA reset to 0, previous value was not 255 (rollover value),
                # and within time window.
                for i, (time_a, value_a) in enumerate(zip(data_reject_a.times, data_reject_a.vals)):
                    if (value_a == 0 and (data_reject_a.vals[i-1] != 255) and
                        (CxoTime(time_a)-timedelta(seconds=1) <= reset_time <=
                         CxoTime(time_a)+timedelta(seconds=1))):
                        data_point.reset_a_datetime= CxoTime(time_a).yday
                        break

                # Check if CMRJCNTB reset to 0, previous value was not 255 (rollover value),
                # and within time window.
                for i, (time_b, value_b) in enumerate(zip(data_reject_b.times, data_reject_b.vals)):
                    if ((value_b == 0) and (data_reject_b.vals[i-1] != 255) and
                        (CxoTime(time_b)-timedelta(seconds=1) <= reset_time <=
                         CxoTime(time_b)+timedelta(seconds=1))):
                        data_point.reset_b_datetime= CxoTime(time_b).yday
                        break

                # Append data_points list if data_point fills up
                if ((data_point.reset_a_datetime is not None) and
                    (data_point.reset_b_datetime is not None)):
                    data_points.append(data_point)
                    data_point = CommandProcessorReset(None, None)

        except IndexError:
            pass

    # If a data_point was partially filled, append it to the list
    if ((data_point.reset_a_datetime is not None) or
        (data_point.reset_b_datetime is not None)):
        data_points.append(data_point)

    return data_points
