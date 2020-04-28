import jsonInterpreter
import pytest


def test_Database(tmp_path):
    # Test 1: file not found
    error_path = 'error/path'

    with pytest.raises(ValueError) as excinfo:
        bd = jsonInterpreter.Database(error_path)

    assert 'The path: ' + error_path + \
           ' cannot be resolved to a valid file. Please check the input path.' in str(excinfo.value)

    # Test 2: Correct behaviour

    """
    content = '{"Test\" :{ "test1" : null}}'
    d = tmp_path / "sub"
    d.mkdir()

    test_json = d / "test.json"
    test_json.write_text(content)
    bd = jsonInterpreter.Database(test_json)
    assert bd.labels == 'Test'
    """
