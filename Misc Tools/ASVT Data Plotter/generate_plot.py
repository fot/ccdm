"Module to build plotly object from ASVT data txt file"

from datetime import datetime
from itertools import islice
import plotly.graph_objects as go
from plotly.subplots import make_subplots

class DataPoint:
    "A blank dataclass used to store data point attributes"

def build_plot(self):
    "build a ploty figure from the ASVT data txt file"
    data_list= []

    with open(self.selected_file, "r") as f:
        # Read header
        msids= f.readline().split()[1:]

        while True:
            lines = list(islice(f, 10000))
            if not lines:
                break

            for line in lines:
                data_line= line.split()
                data_point= DataPoint()
                data_point.datetime= datetime.strptime(data_line[0], "%Y%j.%H%M%S%f")

                for msid, num in zip(msids, range(1, len(msids)*2, 2)):
                    try:
                        setattr(data_point, msid, float(data_line[num]))
                    except ValueError:
                        setattr(data_point, msid, data_line[num])

                data_list.append(data_point)

    # Access data from data_list and plot
    fig= make_subplots(rows= len(msids), cols= 1, shared_xaxes= True, subplot_titles= msids)

    for i, (msid) in enumerate(msids):
        x, y= ([] for i in range(2))
        for data_point in data_list:
            x.append(getattr(data_point, "datetime"))
            y.append(getattr(data_point, msid))

        fig.add_trace(go.Scatter(x= x, y= y, mode='lines', name= msid), row= i + 1, col=1)

    fig.update_layout(autosize= True, showlegend= True)

    return fig
