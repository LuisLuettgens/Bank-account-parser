import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

import pandas as pd


def is_rent(df: pd.DataFrame) -> pd.DataFrame:
    """
        Filter method to classify transactions with the label Rent
    Args:
        df: DataFrame that is queried

    Returns:
        returns all the rows of df where 'Verwendungszweck' equals 'Miet' and 'Buchungstext' is not equal to 'Gutschrift'
        as a DataFrame
    """
    return (df['Verwendungszweck'].str.contains('Miet', case=False, na=False) &
           (df['Buchungstext'].str.contains('Gutschrift', case=False, na=False) is False))


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
    my_file = Path(path)
    if not my_file.is_file():
        raise ValueError('The path: ' + path + ' cannot be resolved to a valid file. Please check the input path.')
    
    # Check if the file is a csv-file
    pattern = r'\.csv$'
    if re.search(pattern, path,re.IGNORECASE) is None:
        raise ValueError('The passed file does not appear to be a csv file. Please check the file-suffix.')
    
    return True
