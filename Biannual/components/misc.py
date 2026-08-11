"Misc methods used in CCDM Biannaul Report"

import pandas as pd


def write_csv_file(user_vars, data, file_name, index= True):
    "Writes data to csv file"
    print(f"""  - Writing data to "{file_name}" in {user_vars.set_dir}...""")
    data.to_csv(f"{user_vars.set_dir}/Output/{file_name}", index= index)


def write_json_file(user_vars, fig, file_name):
    "Writes a figure to a json file"
    print(f"""  - Writing figure to "{file_name}" in {user_vars.set_dir}...""")
    with open(f"{user_vars.set_dir}/Output/{file_name}", "w") as f:
        f.write(fig.to_json())


def parse_csv_file(csv_file,as_dict=False):
    "Read given .csv file and return data"
    print(f"""  - Parsing file "{csv_file}"...""")
    data = pd.read_csv(csv_file)
    if as_dict:
        data.to_dict()
    return data
