from hypnos.geometry_maker import GeometryMaker, make_everything
from hypnos.default_params import PIN
from hypnos.generic_classes import CubismError
from hypnos.assemblies import PinAssembly
from hypnos.components import (
    MultiplierComponent,
    PressureTubeComponent,
    CladdingComponent,
    PinCoolant,
    FilterLidComponent,
    PurgeGasComponent,
    FilterDiskComponent,
    PinBreeder
)

import difflib
import sys
import re
import copy
import pytest
from pathlib import Path

PIN_STP = "pin.stp"
PARSE_FILE = "parse_this.json"
# classes of components in a pin assembly
PIN_COMPS = [
        MultiplierComponent,
        PressureTubeComponent,
        CladdingComponent,
        PinCoolant,
        FilterLidComponent,
        FilterDiskComponent,
        PurgeGasComponent,
        PinBreeder
        ]

# is this bad practice?
raise_cubism = pytest.raises(CubismError)


def fopen(filename: str):
    '''Open a file

    :param filename: Name of file
    :type filename: str
    '''
    try:
        return open(filename)
    except IOError as detail:
        sys.stderr.write(f"Couldn't open file {filename}: {detail}")
        return 0


def compare_stp(filepath1: str, filepath2: str):
    '''Compare if two stp files are identical (excluding metadata)

    :return: whether stp files are identical
    :rtype: bool
    '''
    filename1 = Path(filepath1).resolve()
    filename2 = Path(filepath2).resolve()
    file1 = fopen(filename1)
    file2 = fopen(filename2)
    if not file1 or not file2:
        return False

    text1 = file1.readlines()
    text2 = file2.readlines()

    file1.close()
    file2.close()

    for line in difflib.ndiff(text1, text2):
        if not (line.startswith("  ") or line.startswith("?")):
            header = re.match(r'^[\+\-] FILE_NAME(.*);$', line)
            if isinstance(header, re.Match):
                pass
            else:
                print(line)
                return False
    return True


@pytest.fixture(scope='function')
def maker():
    return GeometryMaker()


@pytest.fixture(scope="function")
def dirpath(pytestconfig):
    return pytestconfig.rootpath / "tests" / "geometry_maker_testing"


@pytest.fixture(scope='function')
def parsed(maker, dirpath):
    parse_file = dirpath / PARSE_FILE
    maker.parse_json(parse_file)
    return maker


@pytest.fixture(scope="function")
def goldpath(pytestconfig):
    return pytestconfig.rootpath / "tests" / "gold"


def test_make_everything():
    # this should make a pin assembly
    geom_list = make_everything(PIN)
    geom = geom_list[0]
    assert len(geom_list) == 1
    assert isinstance(geom, PinAssembly)

    # make sure it contains all the components we want
    comp_classes = [type(comp) for comp in geom.components]
    for pin_comp in PIN_COMPS:
        assert pin_comp in comp_classes

    fake_json_obj = [PIN]
    json_list = make_everything(fake_json_obj)
    assert len(json_list) == 1
    assert isinstance(json_list[0], PinAssembly)

    with pytest.raises(CubismError):
        make_everything(1)


def test_parse_json(parsed):
    assert parsed.design_tree == PIN


def test_change_params(parsed):
    pin_changed = copy.deepcopy(PIN)
    pin_changed["geometry"]["offset"] = "dummy"

    # check if parameter actually changes
    parsed.change_params({"geometry/offset": "dummy"})
    assert parsed.design_tree == pin_changed

    # break if path is bad
    with raise_cubism:
        parsed.change_params({"geometry/not a path": 3})
    with raise_cubism:
        parsed.change_params({1: 1})


def test_change_delimiter(parsed):
    pin_changed = copy.deepcopy(PIN)
    pin_changed["geometry"]["offset"] = "dummy"
    parsed.change_delimiter("...")
    parsed.change_params({"geometry...offset": "dummy"})
    assert parsed.design_tree == pin_changed
    with raise_cubism:
        parsed.change_params({"geometry/offset": "dummy"})


def test_get_param(parsed):
    assert parsed.get_param("geometry/offset") == 60

    with raise_cubism:
        parsed.get_param("haha")


def test_export_stp(goldpath, parsed, tmp_path):
    goldfile = goldpath / PIN_STP
    stp_path = tmp_path / "pin"
    stp_file = tmp_path / "pin.stp"
    parsed.make_tracked_geometry()
    parsed.export("stp", stp_path)

    assert compare_stp(goldfile, stp_file)


@pytest.mark.slow
def test_export_existence(parsed, tmp_path):
    file_path = tmp_path / "pin"
    exodus_filepath = tmp_path / "pin_large_exodus"
    parsed.reset_cubit()
    parsed.make_tracked_geometry()
    parsed.tetmesh()

    parsed.export("cub5", file_path)
    parsed.export("exodus", file_path)
    parsed.export("dagmc", file_path)
    parsed.export_exodus(exodus_filepath, True, True)

    assert file_path.with_suffix(".cub5").is_file()
    assert file_path.with_suffix(".e").is_file()
    assert file_path.with_suffix(".h5m").is_file()
    # would like to be able to check this is done with the right settings
    assert exodus_filepath.with_suffix(".e").is_file()

    with pytest.raises(CubismError):
        parsed.export("not a file type", file_path)
