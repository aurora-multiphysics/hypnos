from hypnos.cubit_functions import (
    get_last_geometry,
    reset_cubit,
    cmd_geom,
    cmd_group,
    get_id_string,
    to_owning_body,
    to_volumes,
    to_surfaces,
    to_bodies,
    get_entities_from_group,
    add_to_new_entity,
    subtract,
    union
)
from hypnos.generic_classes import (
    CubitInstance,
    CubismError,
    cmd
)

import pytest
import cubit


def test_reset_cubit(brick):
    reset_cubit()
    # brick should disappear
    assert cubit.get_entities("volume") == ()


def test_get_last_geometry(brick):
    # this should get brick
    geom = get_last_geometry("body")
    assert geom == brick


def test_cmd_geom():
    geom = cmd_geom("create brick x 5", "volume")
    assert geom == CubitInstance(1, "volume")

    # no volume created so this should fail
    with pytest.raises(CubismError):
        geom = cmd_geom("create circle r 5", "volume")

    # group isnt a geometrical entity so this should fail
    with pytest.raises(CubismError):
        geom = cmd_geom("create circle r 5", "group")


def test_cmd_group():
    # this creates a group
    grp = cmd_group("create group 'test_group'")
    assert grp > 0

    # these dont create a group
    assert cmd_group("create group 'test_group'") == 0
    assert cmd_group("create brick x 10") == 0


def test_get_id_string():
    geom1 = cmd_geom("create brick x 5", "volume")
    geom2 = cmd_geom("create brick x 5", "volume")
    assert get_id_string([geom1, geom2]) == f"{geom1.cid} {geom2.cid}"


def test_to_owning_body(brick):
    # surface and volume owned by same body
    assert (to_owning_body(CubitInstance(1, "surface"))
            == to_owning_body(brick)
            == to_owning_body(CubitInstance(1, "body")))
    # fetched body should exist
    assert to_owning_body(brick).geometry_type == "body"
    assert to_owning_body(brick).cid > 0


def test_to_volumes(brick):
    # should break down to the same volume
    vols = to_volumes([CubitInstance(1, "body"), brick])
    assert len(vols) == 1
    assert vols[0].geometry_type == "volume"
    assert vols[0].cid > 0


def test_to_surfaces(brick):
    # all are parts of the same body
    surfs = to_surfaces([
        CubitInstance(1, "body"),
        CubitInstance(2, "surface"),
        CubitInstance(1, "volume")
        ])
    # a cube has 6 faces
    assert len(surfs) == 6
    for surf in surfs:
        assert surf.geometry_type == "surface"
        assert 0 < surf.cid < 7


def test_to_bodies(brick):
    brick2 = cmd_geom("brick x 5", "body")
    bodies = to_bodies([
        CubitInstance(1, "surface"),
        CubitInstance(2, "surface"),
        CubitInstance(1, "volume"),
        brick2,
        CubitInstance(2, "volume")
        ])
    assert len(bodies) == 2
    for body in bodies:
        assert body.geometry_type == "body"
        assert body.cid > 0


def test_get_entities_from_group(brick):
    cmd('create group "test_group"')
    cmd('create group "sub_group"')
    cmd('group "test_group" add group 3')
    cmd('group "test_group" add vertex 3 4 5')
    cmd('group "test_group" add curve 2 3 4 5')
    cmd('group "test_group" add surface 1 2 3 4')
    cmd('group "test_group" add volume 1')
    cmd('group "test_group" add body 1')

    assert get_entities_from_group("test_group", "group") == [3]
    assert get_entities_from_group("test_group", "vertex") == [3, 4, 5]
    assert get_entities_from_group("test_group", "curve") == [2, 3, 4, 5]
    assert get_entities_from_group("test_group", "surface") == [1, 2, 3, 4]
    assert get_entities_from_group("test_group", "volume") == [1]
    assert get_entities_from_group("test_group", "body") == [1]

    with pytest.raises(CubismError):
        get_entities_from_group("this group doesnt exist lmao", "vertex")
    with pytest.raises(CubismError):
        get_entities_from_group("test_group", "and this is not an entity type")


def test_add_to_new_entity(brick):
    group_id = cubit.get_next_group_id()
    add_to_new_entity("group", "test_group", "surface", [1, 2, 3, 4])
    assert cubit.get_next_group_id() == group_id + 1
    assert get_entities_from_group("test_group", "surface") == [1, 2, 3, 4]

    # using an already created group should just add to that group
    add_to_new_entity("group", "test_group", "surface", 5)
    assert cubit.get_next_group_id() == group_id + 1
    assert get_entities_from_group("test_group", "surface") == [1, 2, 3, 4, 5]

    block_id = cubit.get_next_block_id()
    add_to_new_entity("block", "test_block", "volume", [1])
    assert cubit.get_next_block_id() == block_id + 1
    assert list(cubit.get_block_volumes(block_id)) == [1]

    sideset_id = cubit.get_next_sideset_id()
    add_to_new_entity("sideset", "test_sideset", "surface", [3, 4, 5])
    assert cubit.get_next_sideset_id() == sideset_id + 1
    assert list(cubit.get_sideset_surfaces(sideset_id)) == [3, 4, 5]


def test_subtract(brick):
    brick.update_reference(1, "volume")
    brick2 = cmd_geom("create brick x 3", "volume")
    brick.move([1, 0, 0])
    assert brick.handle.volume() == 1
    assert brick2.handle.volume() == 27

    remainder = subtract([brick2], [brick], destroy=False)
    assert len(remainder) == 1
    assert remainder[0].handle.volume() == 26
    assert brick.handle.centroid() == (1, 0, 0)
    assert brick2.handle.centroid() == (0, 0, 0)

    remains = subtract([brick2], [brick])
    assert len(remains) == 1
    assert remains[0].handle.volume() == 26
    assert brick2.handle.volume() == 26
    assert brick2.cid == remains[0].cid


def test_union(brick):
    brick.move([0.5, 0, 0])
    brick2 = cmd_geom("brick x 1", "body")

    added = union([brick, brick2], destroy=False)
    assert len(added) == 1
    assert added[0].handle.volume() == 1.5

    brick.move([1, 0, 0])
    added2 = union([brick, brick2])
    assert len(added2) == 2
    assert added2[0].handle.volume() == 1
    assert added2[1].handle.volume() == 1
