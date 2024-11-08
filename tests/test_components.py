from blobmaker.components import SimpleComponent
from blobmaker.generic_classes import CubitInstance, CubismError
from blobmaker.geometry import create_brick
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


class BrickComponent(SimpleComponent):
    '''This class exists for testing purposes'''
    def __init__(self, json_object):
        super().__init__("brick", json_object)

    def make_geometry(self):
        return create_brick(self.geometry)



@pytest.fixture(scope="function")
def simple_component(geometry_json):
    cubit.reset()
    return BrickComponent(geometry_json)


# tests for SimpleComponent
def test_get_subcomponents(simple_component):
    assert isinstance(simple_component, SimpleComponent)
    assert 1 == simple_component.get_geometries()[0].cid


def test_origin(simple_component: SimpleComponent):
    vol = simple_component.get_geometries()[0].handle
    assert vol.centroid() == (10, 0, 0)


def test_add_to_subcomponents(simple_component: SimpleComponent):
    cubit.brick(1, 1, 1)
    brick = CubitInstance(2, "volume")
    simple_component.add_to_subcomponents(brick)
    vols = [vol.cid for vol in simple_component.get_geometries()]
    assert vols == [1, 2]


def test_as_bodies(simple_component: SimpleComponent):
    simple_component.as_bodies()
    subcmps = simple_component.get_geometries()
    assert [1] == [body.cid for body in subcmps if body.geometry_type == "body"]


def test_as_volumes(simple_component: SimpleComponent):
    simple_component.subcomponents = [CubitInstance(1, "body")]
    simple_component.as_volumes()
    subcmps = simple_component.get_geometries()
    assert [1] == [vol.cid for vol in subcmps if vol.geometry_type == "volume"]


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
