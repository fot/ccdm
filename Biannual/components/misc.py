"Misc methods used in CCDM Biannaul Report"

import pandas as pd


def write_html_file(user_vars, figure, file_name):
    "Writes a figure into an HTML file"
    print(f"""  - Writing data to "{file_name}" in {user_vars.set_dir}...""")
    figure.write_html(f"{user_vars.set_dir}/Output/{file_name}")


def write_csv_file(user_vars, data, file_name):
    "Writes data to csv file"
    print(f"""  - Writing data to "{file_name}" in {user_vars.set_dir}...""")
    data.to_csv(f"{user_vars.set_dir}/Output/{file_name}")


def write_png_file(user_vars, figure, file_name):
    "Writes a figure to a png file"
    print(f"""  - Writing data to "{file_name}" in {user_vars.set_dir}...""")
    figure.write_image(f"{user_vars.set_dir}/Output/{file_name}")


def parse_csv_file(csv_file,as_dict=False):
    "Read given .csv file and return data"
    print(f"""  - Parsing file "{csv_file}"...""")
    data = pd.read_csv(csv_file)
    if as_dict:
        data.to_dict()
    return data
