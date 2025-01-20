"Sequencer Selftest Detection for use in status_report.py"

import dataclasses
from cxotime import CxoTime
from components.tlm_request import data_request


@dataclasses.dataclass
class EIADataPoint:
    "Sequencer selftest data point"
    msid:       None
    start_time: None
    end_time:   None


def sequencer_selftest_detection(user_vars, file):
    "Auto detect when an EIA sequencer self-test occured"
    print(" - EIA Sequencer Self-Test Detection...")
    msids = {"C1SQATPS":"NPAS","C2SQATPS":"NPAS","C1SQBTPS":"NPAS","C2SQBTPS":"NPAS",
             "C1SQPTLX":"SET","C2SQPTLX":"SET","C1SQRTLX":"SET","C2SQRTLX":"SET",
             "C1SQATPP":"TEST","C2SQATPP":"TEST"}
    relay_data_points, start_times, end_times = ([] for i in range(3))

    for msid, expected_value in msids.items():
        raw_msid_data = data_request(user_vars.ts,user_vars.tp,"SKA Abreviated",f"{msid}")
        relay_data_points.append(detect_status_change(raw_msid_data,expected_value))

    for data_point in relay_data_points:
        if data_point.start_time is not None:
            start_times.append(data_point.start_time)
        if data_point.end_time is not None:
            end_times.append(data_point.end_time)

    # Good Test detected in time range
    if len(start_times) == 10 and len(end_times) == 10:
        response = ("A successful EIA-A Sequencer self-test occured on "
                    f"{relay_data_points[0].start_time}.")

    # Bad test detected
    elif (10 > len(start_times) > 0) or (10 > len(end_times) > 0):
        response = ("An incomplete EIA-A Sequencer self-test occured on "
                    f"{relay_data_points[0].start_time}.")

    # No test detected in time range
    elif all(v is None for v in start_times) and all(v is None for v in end_times):
        response = "No EIA Sequencer self-test detected."

    # Error if nothing found.
    else:
        response = "Unable to determine EIA Sequencer self-test status."

    print(f"   - {response}")
    file.write(f"  - {response}\n")


def detect_status_change(data, expected_value):
    "Return a list of data points when state changes."
    data_point = EIADataPoint(None,None,None)

    for index, (loop_data, loop_time) in enumerate(zip(data.vals, data.times)):
        # Record MSID
        if not data_point.msid:
            data_point.msid = data.msid

        try:
            # Find First Value
            if ((loop_data == expected_value) and
                (data.vals[index - 1] != expected_value)
                ):
                data_point.start_time = CxoTime(loop_time).yday

            # Find Last Value
            if ((loop_data != expected_value) and
                (data.vals[index - 1] == expected_value)
                ):
                data_point.end_time = CxoTime(data.times[index - 1]).yday
        except IndexError:
            pass

    return data_point
