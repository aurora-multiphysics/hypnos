from blobmaker.components import SimpleComponent
from blobmaker.generic_classes import CubitInstance
import cubit, pytest

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

class TestSimpleComponent:
    def test_get_subcomponents(self, simple_component):
        assert isinstance(simple_component, SimpleComponent)
        assert 1 == simple_component.get_subcomponents()[0].cid
    
    def test_origin(self, simple_component: SimpleComponent):
        vol = simple_component.get_subcomponents()[0].handle
        assert vol.centroid() == (10, 0, 0)

    def test_add_to_subcomponents(self, simple_component: SimpleComponent):
        cubit.brick(1, 1, 1)
        brick = CubitInstance(2, "volume")
        simple_component.add_to_subcomponents(brick)
        vols = [vol.cid for vol in simple_component.get_subcomponents()]
        assert 2 in vols

    def test_as_bodies(self, simple_component: SimpleComponent):
        simple_component.as_bodies()
        assert 1 in [body.cid for body in simple_component.get_subcomponents() if body.geometry_type == "body"]

    def test_as_volumes(self, simple_component: SimpleComponent):
        simple_component.subcomponents = [CubitInstance(1, "body")]
        simple_component.as_volumes()
        assert 1 in [vol.cid for vol in simple_component.get_subcomponents() if vol.geometry_type == "volume"]
    
    def test_get_parameters(self, simple_component: SimpleComponent):
        assert simple_component.get_parameters(["dimensions"])[0] == 5
    
    def test_extract_parameters(self, simple_component: SimpleComponent):
        assert simple_component.extract_parameters(["dimensions"])["dimensions"] == 5
        assert simple_component.extract_parameters({"dimensions": "a"})["a"] == 5
    
    def test_vol_id_string(self, simple_component: SimpleComponent):
        assert simple_component.volume_id_string() == "1"
