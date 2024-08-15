"Misc Methods for Space Weather Plotter Tool"

import os


def create_dir(input_dir):
    """
    Description: Create the given directory path
    Input: <str>
    Output: None
    """
    try:
        os.makedirs(input_dir)
    except FileExistsError:
        pass
