import sys
sys.path.insert(0,'../')
import unittest
import helper
from datetime import datetime, timedelta
import pandas as pd
import random

class TestHelper(unittest.TestCase):
    
    def test_is_valid_csv_file(self):
        
        # Test 1: file not found
        file_not_found_exeption = 'test_files/this/is/an/invalid/path.csv'

        with self.assertRaisesRegex(expected_exception=ValueError,
                                    expected_regex='The path: ' + file_not_found_exeption + 
                                                    ' cannot be resolved to a valid file. Please check the input path.'):
            helper.is_valid_csv_file(file_not_found_exeption)

        # Test 2: file not a csv
        not_a_csv_file_exeption = 'test_files/not_a_csv_file.txt'

        with self.assertRaisesRegex(expected_exception=ValueError,
                                    expected_regex='The passed file does not appear to be a csv file. Please check the file-suffix.'):
            helper.is_valid_csv_file(not_a_csv_file_exeption)

        # Test 3: file is csv (lower cases)
        correct_file = 'test_files/correct.csv'
        self.assertTrue(helper.is_valid_csv_file(correct_file))
        
        # Test 4: file is csv (upper cases)
        correct_file2 = 'test_files/correct.CSV'
        self.assertTrue(helper.is_valid_csv_file(correct_file2))

    def test_generate_days(self):
        # Test 1: start after end
        start1  = pd.Timestamp(datetime.now())
        end1 = pd.Timestamp(start1 - timedelta(days=1))
        
        result1 = helper.generate_days(start1,end1)
        expected_result1 = []
        
        self.assertEqual(result1, expected_result1)

        # Test 2: contains start and end
        start2  = pd.Timestamp(datetime.now().date())
        end2 = pd.Timestamp(start2 + timedelta(days=1))

        result2 = helper.generate_days(start2,end2)
        expected_result2 = [start2,end2]

        self.assertEqual(result2, expected_result2)

        # Test 3: generating more days than a year has
        random3 = random.randint(400,500)
        start3  = pd.Timestamp(datetime.now().date())
        runner3 = start3
        end3 = pd.Timestamp(start2 + timedelta(days=random3))

        result3 = helper.generate_days(start3,end3)

        expected_result3 = []

        while runner3 <= end3:
            expected_result3.append(runner3)
            runner3 += timedelta(days=1)
        
        self.assertEqual(result3, expected_result3)

    def test_is_rent(self):
        # TODO: implement
        pass
    
if __name__ == '__main__':
    unittest.main()