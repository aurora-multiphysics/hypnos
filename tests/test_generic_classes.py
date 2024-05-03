import cubit
import pytest
from blobmaker.generic_classes import (
    CubitInstance,
    get_cubit_geometry
)

@pytest.fixture()
def brick():
    cubit.brick(1, 1, 1)
    return CubitInstance(1, "body")


class TestCubitInstance:
    
    def test_stringify(self, brick):
        assert str(brick) == "body 1"
    
    def test_copy(self, brick):
        # am i allowed to use union here smiley face
        brick_vol = cubit.get_volume_volume(brick.cid)
        brick2 = brick.copy()
        brick2_vol = cubit.get_volume_volume(brick2.cid)

        assert brick_vol == brick2_vol
    
    def test_delete(self, brick):
        brick.destroy_cubit_instance()
        assert cubit.get_entities("volume") == ()
    
    def test_move(self, brick):
        brick.move([1, 1, 1])
        brick_vol = cubit.volume(1)
        assert brick_vol.centroid() == (1, 1, 1)

    def test_update_reference(self, brick):
        brick.move([1, 0, 0])
        brick.update_reference(1, "volume")
        brick.move([-1, 0, 0])
        brick_vol = cubit.volume(1)
        assert brick_vol.centroid() == (0, 0, 0)

def test_get_cubit_geometry(brick):
    brick_handle = get_cubit_geometry(1, "volume")
    cubit.move(brick_handle, [1, 0, 0])
    assert brick_handle.centroid() == (1, 0, 0)
