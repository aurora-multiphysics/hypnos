import cubit
import pytest
from blobmaker.generic_classes import (
    CubismError,
    CubitInstance,
    cmd,
    get_cubit_geometry
)

@pytest.fixture(autouse=True)
def brick_handle():
    cubit.reset()
    return cubit.brick(1, 1, 1)

@pytest.fixture()
def brick():
    return CubitInstance(1, "body")


class TestCubitInstance:
    def test_handle_get(self, brick_handle, brick):
        assert brick.handle == brick_handle
    
    def test_stringify(self, brick):
        assert str(brick) == "body 1"
    
    def test_copy(self, brick):
        # am i allowed to use union here smiley face
        brick_vol = cubit.get_volume_volume(brick.cid)
        brick2 = brick.copy_cubit_instance()
        brick2_vol = cubit.get_volume_volume(brick2.cid)

        assert brick_vol == brick2_vol
    
    def test_delete(self, brick):
        brick.destroy_cubit_instance()
        assert cubit.get_entities("volume") == ()
    
    def test_move(self, brick):
        brick.move([1, 1, 1])
        brick = cubit.Body(brick.handle)
        assert brick.centroid() == (1, 1, 1)
