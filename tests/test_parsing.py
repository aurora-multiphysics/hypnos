from blobmaker.parsing import (
    extract_data,
    extract_if_string,
    delve,
    ParameterFiller
)
from blobmaker.default_params import HCPB_BLANKET
import pytest, pathlib

@pytest.fixture(autouse=True)
def filename(request):
    module_path = pathlib.Path(request.node.fspath)
    file = module_path.with_name("sample_test.json").as_posix()
    return file

def check(obj: dict):
    return "class" in obj.keys()

def test_extract_data(filename):
    data = extract_data(filename)
    assert check(data)

def test_extract_if_string(filename):
    data = extract_if_string(filename)
    assert check(data)

def test_delve(filename):
    test_str = filename
    test_list = [test_str]
    test_dict = {"a": test_str}

    str_delve = delve(test_str)
    list_delve = delve(test_list)
    dict_delve = delve(test_dict)

    assert check(str_delve)
    assert check(*list_delve)
    assert check(dict_delve["a"])

class TestParameterFiller:
    p_filler = ParameterFiller()
    def test_add_log(self):
        self.p_filler.add_log("test message")
        assert "test message" in self.p_filler.log
    
    def test_process_design_tree(self, filename):
        design_tree = extract_data(filename)
        self.p_filler.process_design_tree(design_tree)
        assert self.p_filler.design_tree == HCPB_BLANKET

