#import sys
#sys.path.append('/home/runner/work/Bank-account-parser/Bank-account-parser/src')

import helper
from datetime import datetime, timedelta
import pandas as pd
import random
import pytest
import os

def test_is_valid_csv_file(tmp_path):
    
    d = tmp_path / "sub"
    d.mkdir()
    
    test_txt = d / "hello.txt"
    test_txt.write_text("test")
    
    test_csv = d / "hello.csv"
    test_csv.write_text("test")
    
    test_CSV = d / "hello.CSV"
    test_CSV.write_text("test")


    # Test 1: file not found
    file_not_found_exeption = str(tmp_path)

    with pytest.raises(ValueError) as excinfo:

        helper.is_valid_csv_file(file_not_found_exeption)

    assert  'The path: ' + file_not_found_exeption + \
            ' cannot be resolved to a valid file. Please check the input path.' in str(excinfo.value)

    
    # Test 2: file not a csv
    not_a_csv_file_exeption = str(test_txt)

    with pytest.raises(ValueError) as excinfo:
        
        helper.is_valid_csv_file(not_a_csv_file_exeption)
    
    assert  'The input file does not appear to be a csv file. Please check the file-suffix.' in str(excinfo.value)   

    
    # Test 3: file is csv (lower cases)
    correct_file = str(test_csv)
    
    assert helper.is_valid_csv_file(correct_file) is True
    
    # Test 4: file is csv (upper cases)
    correct_file2 = str(test_CSV)
    
    assert helper.is_valid_csv_file(correct_file2) is True

def test_generate_days():
    # Test 1: start after end
    start1  = pd.Timestamp(datetime.now())
    end1 = pd.Timestamp(start1 - timedelta(days=1))
        
    result1 = helper.generate_days(start1,end1)
    expected_result1 = []

    assert result1 == expected_result1

    # Test 2: contains start and end
    start2 = pd.Timestamp(datetime.now().date())
    end2 = pd.Timestamp(start2 + timedelta(days=1))

    result2 = helper.generate_days(start2, end2)
    expected_result2 = [start2, end2]

    assert result2 == expected_result2

    # Test 3: generating more days than a year has
    random3 = random.randint(400, 500)
    start3 = pd.Timestamp(datetime.now().date())
    runner3 = start3
    end3 = pd.Timestamp(start2 + timedelta(days=random3))

    result3 = helper.generate_days(start3, end3)
    
    expected_result3 = []
    while runner3 <= end3:
        expected_result3.append(runner3)
        runner3 += timedelta(days=1)

    assert result3 == expected_result3
