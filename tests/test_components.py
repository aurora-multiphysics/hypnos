from blobmaker.components import SimpleComponent
from blobmaker.generic_classes import CubitInstance, CubismError
import cubit
import pytest


@pytest.fixture(scope="module")
def geometry_json():
    return {
        "material": "Steel",
        "geometry": {
            "dimensions": 5
        },
        "origin": [10, 0, 0]
    }


@pytest.fixture(scope="function")
def simple_component(geometry_json):
    cubit.reset()
    return SimpleComponent("air", geometry_json)


# tests for SimpleComponent
def test_get_subcomponents(simple_component):
    assert isinstance(simple_component, SimpleComponent)
    assert 1 == simple_component.get_subcomponents()[0].cid


def test_origin(simple_component: SimpleComponent):
    vol = simple_component.get_subcomponents()[0].handle
    assert vol.centroid() == (10, 0, 0)


def test_add_to_subcomponents(simple_component: SimpleComponent):
    cubit.brick(1, 1, 1)
    brick = CubitInstance(2, "volume")
    simple_component.add_to_subcomponents(brick)
    vols = [vol.cid for vol in simple_component.get_subcomponents()]
    assert vols == [1, 2]


def test_as_bodies(simple_component: SimpleComponent):
    simple_component.as_bodies()
    subcmps = simple_component.get_subcomponents()
    assert [1] == [body.cid for body in subcmps if body.geometry_type == "body"]


def test_as_volumes(simple_component: SimpleComponent):
    simple_component.subcomponents = [CubitInstance(1, "body")]
    simple_component.as_volumes()
    subcmps = simple_component.get_subcomponents()
    assert [1] == [vol.cid for vol in subcmps if vol.geometry_type == "volume"]


def test_get_parameters(simple_component: SimpleComponent):
    assert simple_component.get_parameters(["dimensions"])[0] == 5
    with pytest.raises(KeyError):
        simple_component.get_parameters(["parameter not real"])


def test_extract_parameters(simple_component: SimpleComponent):
    extract = simple_component.extract_parameters
    assert extract(["dimensions"])["dimensions"] == 5
    assert extract({"dimensions": "a"})["a"] == 5

    with pytest.raises(CubismError):
        extract(1)
    with pytest.raises(KeyError):
        extract(["parameter not real"])


def test_vol_id_string(simple_component: SimpleComponent):
    assert simple_component.volume_id_string() == "1"
