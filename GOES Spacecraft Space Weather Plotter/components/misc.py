"Misc Methods for Space Weather Plotter Tool"

import os


def create_dir(input_dir):
    """
    Description: Create the given directory path
    Input: <str>
    Output: None
    """
    try:
        os.mkdir(input_dir)
    except FileExistsError:
        pass
