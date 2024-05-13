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
import numpy as np

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
def midpoints():
    return [
        (0, -5, 0),
        (5, 0, 0),
        (0, 5, 0),
        (-5, 0, 0)
    ]

@pytest.fixture()
def vertex():
    return Vertex(1, 2, 3)


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

def test_make_surface_from_curves(verts):
    loop = make_loop(verts, [])
    surf = make_surface_from_curves(loop).handle
    assert surf.area() == 100
    assert surf.normal_at((0, 0, 0)) == (0, 0, 1) or surf.normal_at((0, 0, 0)) == (0, 0, -1)

def test_make_cylinder_along():
    cylinder = make_cylinder_along(2, 5, "x")
    assert round(cylinder.handle.volume(), 3) == round(20*np.pi, 3)
    centroid = [round(coord, 10) for coord in cylinder.handle.centroid()]
    assert centroid == [0, 0, 0]

def test_hypotenuse():
    assert hypotenuse(3, 4) == 5
    assert hypotenuse(-3, 4) == 5
    assert hypotenuse(2, 2, 2, 2) == hypotenuse(4)

def test_arctan():
    assert arctan(3, 3) == np.pi/4
    assert arctan(1, 0) == np.pi/2
    assert arctan(3, -3) == 3*np.pi/4

class TestVertex:
    def test_str(self, vertex):
        assert str(vertex) == "1 2 3"

    def test_add(self, vertex: Vertex):
        vert_sum = vertex + Vertex(1, 0, -1)
        assert str(vert_sum) == "2 2 2"

    def test_create(self, vertex: Vertex):
        created_vertex = vertex.create()
        assert created_vertex.handle.coordinates() == (1, 2, 3)

    def test_rotate(self, vertex: Vertex):
        vert1 = vertex.rotate(np.pi/2)
        assert str(vert1) == "-2 1 3"

    def test_distance(self, vertex: Vertex):
        assert vertex.distance() == hypotenuse(vertex.x, vertex.y, vertex.z)


def test_make_surface(verts):
    vertices = [Vertex(5, 5), Vertex(5, -5), Vertex(-5, -5), Vertex(-5, 5)]
    surf = make_surface(vertices, []).handle
    assert surf.area() == 100
    assert surf.normal_at((0, 0, 0)) == (0, 0, 1) or surf.normal_at((0, 0, 0)) == (0, 0, -1)

