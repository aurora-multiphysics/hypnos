from blobmaker.cubit_functions import (
    get_last_geometry,
    cmd_check,
    get_id_string,
    delete_instances,
    copy_geometries,
    to_owning_body,
    get_bodies_and_volumes_from_group,
    remove_overlaps_between_geometries,
    to_volumes,
    to_surfaces,
    to_bodies,
    get_entities_from_group
)
from blobmaker.generic_classes import CubitInstance

import pytest, cubit

@pytest.fixture(autouse=True)
def brick():
    cubit.reset()
    cubit.brick(1, 1, 1)
    return CubitInstance(1, "volume")

def test_get_last_geometry(brick):
    geom = get_last_geometry("volume")
    assert str(geom) == str(brick)

def test_cmd_check():
    geom = cmd_check("create brick x 5", "volume")
    assert str(geom) == "volume 2"

