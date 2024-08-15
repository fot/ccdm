"EIA Sequencer Self-Test Detection"

from cxotime import CxoTime
from components.data_requests import ska_data_request as ska_data


def sequencer_selftest_detection(user_vars):
    "Auto detect when an EIA sequencer self-test occured"
    print("EIA Sequencer Self-Test Detection...")
    msids = {
        "C2SQATPS":"NPAS","C2SQBTPS":"NPAS","C1SQATPP":"TEST","C1SQPTLX":"SET","C1SQATPS":"NPAS",
        "C1SQRTLX":"SET", "C1SQBTPS":"NPAS","C2SQATPP":"TEST","C2SQPTLX":"SET","C2SQRTLX":"SET",
        "C1SQATI1":"ENAB","C1SQATI2":"ENAB","C2SQATI1":"ENAB","C2SQATI2":"ENAB"}
    relays_position_data, return_string = [], ""

    for msid, expected_value in msids.items():
        raw_msid_data = ska_data(user_vars.ts, user_vars.tp, f"{msid}", True)
        relays_position_data.append(detect_status_change(raw_msid_data,expected_value))

    if all(v is None for v in relays_position_data):
        print("   - No EIA Sequencer self-test detected.")
    elif None in relays_position_data:
        return_string = (
            "<li>An incomplete EIA Sequencer self-test occured on "
            f"""{relays_position_data[0]["C2SQATPS"][0]}.</li>""")
        print(
            "   - An incomplete EIA Sequencer self-test was detected on "
            f"""{relays_position_data[0]["C2SQATPS"][0]}.""")
    elif not None in relays_position_data:
        return_string = (
            "<li>A successful EIA Sequencer self-test occured on "
            f"""{relays_position_data[0]["C2SQATPS"][0]}.</li>""")
        print(
            "   - A successful EIA Sequencer self-test was detected on "
            f"""{relays_position_data[0]["C2SQATPS"][0]}."""
        )
    else:
        return_string = "<li>Error, unable to determine EIA Sequencer self-test condition.</li>"
        print("   - Error! Unable to determine EIA Sequencer self-test condition.")
    return return_string


def detect_status_change(data,expected_value):
    "Return a msid/date_time if the status changed TO the expected state within data set."
    times_found = 0
    return_dict = {}
    for index, (data_point, time_item) in enumerate(zip(data.vals, data.times)):
        # Find first value
        if data_point == expected_value:
            if data.msid in ("C1SQATI1", "C1SQATI2", "C2SQATI1", "C2SQATI2"):
                first_date_time = CxoTime(time_item)
                return_dict.setdefault(f"{data.msid}",[]).append(first_date_time.yday)
            else: times_found += 1

            if times_found == 5: # forces 5 samples before recording value
                first_date_time = CxoTime(data.times[index - 4])
                return_dict.setdefault(f"{data.msid}",[]).append(first_date_time.yday)

        # Find last value
        if data_point != expected_value:
            if data.msid in ("C1SQATI1", "C1SQATI2", "C2SQATI1", "C2SQATI2"):
                continue
            if data.vals[index - 1] == expected_value:
                last_date_time = CxoTime(data.times[index - 1])
                return_dict.setdefault(f"{data.msid}",[]).append(last_date_time.yday)

    return return_dict if return_dict else None
