from blobmaker.geometry import (
    create_2d_vertex,
    connect_vertices_straight,
    connect_curves_tangentially,
    make_surface_from_curves,
    make_cylinder_along,
    make_loop,
    hypotenuse,
    arctan,
    Vertex,
    make_surface
)
import pytest, cubit

@pytest.fixture(autouse=True)
def verts():
    cubit.reset()
    verts = [0, 0, 0, 0]
    verts[0] = create_2d_vertex(-5, -5)
    verts[1] = create_2d_vertex(5, -5)
    verts[2] = create_2d_vertex(5, 5)
    verts[3] = create_2d_vertex(-5, 5)
    return verts

@pytest.fixture()
def midpoints(verts):
    return [
        (0, -5, 0),
        (5, 0, 0),
        (0, 5, 0),
        (-5, 0, 0)
    ]


def test_create_2d_vertex():
    x = 23
    y = -45
    vert = create_2d_vertex(x, y)
    assert vert.handle.coordinates() == (x, y, 0)

def test_connect_vertices_straight(verts):
    connecting_curve = connect_vertices_straight(verts[0], verts[1])
    assert connecting_curve.handle.curve_center() == (0, -5, 0)

def test_connect_curves_tangentially(verts):
    connect_vertices_straight(verts[0], verts[1])
    connect_vertices_straight(verts[2], verts[3])
    connecting_curve = connect_curves_tangentially(verts[1], verts[2])
    assert connecting_curve.handle.curve_center()[1] == 0
    assert connecting_curve.handle.curve_center()[2] == 0

def test_make_loop_straight(verts, midpoints):
    loop = make_loop(verts, [])
    for i in range(4):
        assert loop[i].handle.curve_center() == midpoints[i]

def test_make_loop_tangent(verts, midpoints):
    loop = make_loop(verts, [3])
    for i in range(3):
        assert loop[i].handle.curve_center() == midpoints[i]
    assert loop[3].handle.curve_center()[1] == 0

def test_make_surface_from_curves():
    assert True