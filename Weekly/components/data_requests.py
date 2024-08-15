"Data request methods for CCDM Weekly"

import urllib.request
import json
from Ska.engarchive import fetch_eng as fetch


def ska_data_request(ts, tp, msid, high_rate = False):
    "Requests a particular MSID for an interval from the ska_eng archive"
    print(f"""   - Requesting data for MSID "{msid}" ({ts} thru {tp})...""")
    ts.format = "yday"
    tp.format = "yday"
    fetch.data_source.set("maude")
    fetch.data_source.set(f"maude allow_subset={not high_rate}")
    data = fetch.MSID(f"{msid}", ts, tp)
    return data


def maude_data_request(ts,tp,msid):
    "Requests a particular MSID for an interval from MAUDE"
    print(f"""   - Requesting MAUDE data for "{msid}" ({ts} thru {tp})...""")
    ts.format = "yday"
    tp.format = "yday"
    base_url = "https://occweb.cfa.harvard.edu/maude/mrest/FLIGHT/msid.json?m="
    url = base_url + msid + "&ts=" +str(ts) + "&tp=" + str(tp)
    response = urllib.request.urlopen(url)
    html = response.read()
    return json.loads(html)
