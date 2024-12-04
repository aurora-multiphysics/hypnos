from hypnos.parsing import (
    extract_data,
    extract_if_string,
    delve,
    ParameterFiller,
    get_format_extension
)
from hypnos.default_params import HCPB_BLANKET
from hypnos.generic_classes import CubismError
import pytest
import pathlib

cubism_err = pytest.raises(CubismError)
type_err = pytest.raises(TypeError)
key_err = pytest.raises(KeyError)


@pytest.fixture
def filename(request):
    module_path = pathlib.Path(request.node.fspath)
    file = module_path.with_name("sample_test.json").as_posix()
    return file


@pytest.fixture
def p_filler():
    return ParameterFiller()


def check(obj: dict):
    return "class" in obj.keys()


def test_extract_data(filename):
    data = extract_data(filename)
    assert check(data)


def test_extract_if_string(filename):
    data = extract_if_string(filename)
    assert check(data)
    assert extract_if_string({}) == {}


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
    with type_err:
        delve(1)


# ParameterFiller tests
def test_add_log(p_filler):
    p_filler.add_log("test message")
    assert "test message" in p_filler.log


def test_process_design_tree(filename, p_filler):
    design_tree = extract_data(filename)
    p_filler.process_design_tree(design_tree)
    assert p_filler.design_tree == HCPB_BLANKET


def test_print_log(p_filler, capsys):
    p_filler.log = []
    p_filler.add_log("test message")
    p_filler.print_log()
    captured = capsys.readouterr()
    assert captured.out == "test message\n"


def test_prereq_fail(p_filler):
    with cubism_err:
        p_filler.process_design_tree({"not class": "pin"})
    with cubism_err:
        p_filler.process_design_tree({"class": 1})


def test_unfilled_params(p_filler):
    non_existent = {"class": "this will never be a class name"}
    assert p_filler.process_design_tree(non_existent) == non_existent
    nodef_log = f"Default configuration not found for: {non_existent['class']}"
    assert nodef_log in p_filler.log


def test_get_format_extension():
    assert get_format_extension("Cubit") == ".cub5"
    assert get_format_extension("exodus") == ".e"
    assert get_format_extension("DAGMC") == ".h5m"
    assert get_format_extension("stp") == ".stp"
    with cubism_err:
        get_format_extension("this is not a format extension")
