import jsonInterpreter
import pytest


def test_Database():
    # Test 1: file not found
    error_path = 'error/path'

    with pytest.raises(ValueError) as excinfo:
        bd = jsonInterpreter.Database(error_path)

    assert 'The path: ' + error_path + \
           ' cannot be resolved to a valid file. Please check the input path.' in str(excinfo.value)
