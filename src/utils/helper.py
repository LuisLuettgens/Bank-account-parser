import re
from datetime import datetime, timedelta
from typing import List
import os
import pandas as pd


def generate_days(first: datetime, last: datetime) -> List[datetime]:
    """
        Generates a list of all days from first to last inclusively
    Args:
        first: start date
        last:  end date

    Returns:
        List of datetime
    """
    step = timedelta(days=1)
    last += timedelta(days=1)
    result = []
    while first < last:
        result.append(pd.Timestamp(first.strftime('%Y-%m-%d')))
        first += step
    return result


def is_valid_csv_file(path: str) -> bool:
    """
    checks if path can be resolved into a csv file.
    Args:
        path: location that is checked

    Returns:
        True if path can be resolved to a csv-file, False otherwise
    """

    # Check if path destination can be resolved into a file
    if not os.path.isfile(path):
        raise ValueError('The path: ' + path + ' cannot be resolved to a valid file. Please check the input path.')

    # Check if the file is a csv-file
    pattern = r'\.csv$'
    if re.search(pattern, path, re.IGNORECASE) is None:
        raise ValueError('The input file does not appear to be a csv file. Please check the file-suffix.')

    return True


# TODO: check whether code is redundant
def is_valid_json_file(path: str) -> bool:
    """
    checks if path can be resolved into a csv file.
    Args:
        path: location that is checked

    Returns:
        True if path can be resolved to a csv-file, False otherwise
    """

    # Check if path destination can be resolved into a file
    if not os.path.isfile(path):
        raise ValueError('The path: ' + path + ' cannot be resolved to a valid file. Please check the input path.')

    # Check if the file is a csv-file
    pattern = r'\.json$'
    if re.search(pattern, path, re.IGNORECASE) is None:
        raise ValueError('The input file does not appear to be a json file. Please check the file-suffix.')

    return True
