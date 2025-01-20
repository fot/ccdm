"Telemetry Request Methods for Daily Plots Tools"

import json
import urllib
from Ska.engarchive import fetch_eng as fetch


def data_request(ts,tp,data_source,msid):
    """
    Description: Request ska_eng archive for telemetry
    Input: User defined variables, MSID
    Output: dict or JSON of data
    """
    data, html = None, None
    ts.format = "yday"
    tp.format = "yday"
    base_url = "https://occweb.cfa.harvard.edu/maude/mrest/FLIGHT/msid.json?m="

    if data_source in ("SKA High Rate", "SKA Abreviated"):
        fetch.data_source.set("maude")
        if data_source == "SKA High Rate":
            fetch.data_source.set("maude allow_subset=False")
        else:
            fetch.data_source.set("maude allow_subset=True")
        data = fetch.MSID(f"{msid}",ts,tp)
    else:
        url = base_url + msid + "&ts=" +str(ts.value) + "&tp=" + str(tp.value)
        response = urllib.request.urlopen(url)
        html = response.read()

    return data if not data_source in ("MAUDE Web") else json.loads(html)
