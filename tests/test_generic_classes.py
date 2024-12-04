import cubit
import pytest
import numpy as np
from hypnos.generic_classes import (
    CubitInstance,
    get_cubit_geometry,
    cmd,
    CubismError
)


def test_cmd():
    assert cubit.get_entities("volume") == ()
    cmd("create brick x 5")
    assert list(cubit.get_entities("volume")) == [1]


# Cubit Instance tests
def test_handle(brick):
    assert CubitInstance(1, "volume").handle.volume() == 1
    with pytest.raises(CubismError):
        CubitInstance(100000, "volume")
    with pytest.raises(TypeError):
        CubitInstance(1)


def test_eq(brick):
    cubit.brick(1, 1, 1)
    assert brick == CubitInstance(1, "body")
    assert brick != CubitInstance(2, "body")
    assert brick != CubitInstance(1, "volume")
    assert brick != 1


def test_stringify(brick):
    assert str(brick) == "body 1"


def test_copy(brick):
    # am i allowed to use union here smiley face
    brick_vol = cubit.get_volume_volume(brick.cid)
    brick2 = brick.copy()
    brick2_vol = cubit.get_volume_volume(brick2.cid)
    assert brick_vol == brick2_vol


def test_delete(brick):
    brick.destroy_cubit_instance()
    assert cubit.get_entities("volume") == ()


def test_move(brick):
    brick.move([1, 1, 1])
    brick_vol = cubit.volume(1)
    assert brick_vol.centroid() == (1, 1, 1)


def test_update_reference(brick):
    # here we want to check that 'updating' the reference to volume 1 will
    # make CubitInstance refer to the same volume
    cubit.brick(2, 2, 2)
    brick1 = cubit.volume(1)
    brick2 = cubit.volume(2)
    brick.move([1, 0, 0])
    assert brick1.centroid() == (1, 0, 0)
    assert brick2.centroid() == (0, 0, 0)
    brick.update_reference(2, "volume")
    brick.move([-1, 0, 0])
    assert brick1.centroid() == (1, 0, 0)
    assert brick2.centroid() == (-1, 0, 0)


# function tests
def test_get_cubit_geometry(brick):
    brick_handle = get_cubit_geometry(1, "volume")
    cubit.move(brick_handle, [1, 0, 0])
    assert brick_handle.centroid() == (1, 0, 0)

    cubit.reset()
    cmd("create vertex 1 1 1")
    vertex_handle = get_cubit_geometry(1, "vertex")
    assert vertex_handle.coordinates() == (1, 1, 1)

    cubit.reset()
    cmd("create vertex 1 1 1")
    cmd("create vertex 0 0 0")
    cmd("create curve vertex 1 2")
    curve_handle = get_cubit_geometry(1, "curve")
    assert curve_handle.curve_center() == (0.5, 0.5, 0.5)

    cubit.reset()
    cmd("create surface circle radius 5")
    surf_handle = get_cubit_geometry(1, "surface")
    assert surf_handle.area() == pytest.approx(25*np.pi)

    with pytest.raises(CubismError):
        get_cubit_geometry(1, "not a geometry type")


def test_cubism_error():
    with pytest.raises(CubismError) as excinfo:
        raise CubismError("error occurred")
    assert excinfo.match("error occurred")
