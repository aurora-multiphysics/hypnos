from blobmaker.default_params import FIRST_WALL, PIN, HCPB_BLANKET
from funcs_for_tests import get_union_volumes
import cubit
import pytest

FIRST_WALL_GOLD = "sample_first_wall.cub5"
PIN_GOLD = "sample_pin.cub5"
BLANKET_GOLD = "sample_blanket.cub5"


@pytest.fixture(scope="function")
def goldpath(pytestconfig):
    cubit.reset()
    return pytestconfig.rootpath / "tests" / "gold"


@pytest.mark.slow
def test_first_wall(goldpath):
    first_wall_path = goldpath / FIRST_WALL_GOLD
    gold_vol, maker_vol, net_vol = get_union_volumes(first_wall_path, FIRST_WALL)
    assert gold_vol == maker_vol == net_vol


@pytest.mark.slow
def test_first_wall_diff(goldpath):
    first_wall_path = goldpath / FIRST_WALL_GOLD
    design_tree = FIRST_WALL.copy()
    design_tree["geometry"]["length"] += 1

    gold_vol, maker_vol, net_vol = get_union_volumes(first_wall_path, design_tree)

    assert gold_vol != maker_vol
    assert gold_vol != net_vol
    assert net_vol != maker_vol


@pytest.mark.slow
def test_pin(goldpath):
    pin_path = goldpath / PIN_GOLD
    gold_vol, maker_vol, net_vol = get_union_volumes(pin_path, PIN)
    appx = pytest.approx
    assert gold_vol == appx(maker_vol) == appx(net_vol)


@pytest.mark.slow
def test_blanket(goldpath):
    blanket_path = goldpath / BLANKET_GOLD
    gold_vol, maker_vol, net_vol = get_union_volumes(blanket_path, HCPB_BLANKET)
    appx = pytest.approx
    assert gold_vol == appx(maker_vol) == appx(net_vol)
