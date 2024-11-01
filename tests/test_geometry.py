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
    make_surface,
    Line,
    blunt_corner,
    fetch,
    unroll,
    blunt_corners
)
from blobmaker.generic_classes import (
    CubitInstance,
    CubismError
)
import pytest
import cubit
import numpy as np
from funcs_for_tests import verts_approx_equal

cubism_err = pytest.raises(CubismError)
type_err = pytest.raises(TypeError)


@pytest.fixture(autouse=True)
def verts():
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
    '''1 2 3'''
    return Vertex(1, 2, 3)


@pytest.fixture()
def line():
    '''y = 2x - 2'''
    return Line(Vertex(1, 2), Vertex(1))


def test_create_2d_vertex():
    x = 23
    y = -45
    vert = create_2d_vertex(x, y)
    assert vert.handle.coordinates() == (x, y, 0)

    with cubism_err:
        create_2d_vertex("not a coord", 1)


def test_connect_vertices_straight(verts):
    connecting_curve = connect_vertices_straight(verts[0], verts[1])
    assert isinstance(connecting_curve, CubitInstance)
    assert connecting_curve.cid > 0
    assert connecting_curve.handle.curve_center() == (0, -5, 0)

    with cubism_err:
        cubit.brick(1, 1, 1)
        connect_vertices_straight(verts[0], CubitInstance(1, "volume"))


def test_connect_curves_tangentially(verts):
    connect_vertices_straight(verts[0], verts[1])
    connect_vertices_straight(verts[2], verts[3])
    connecting_curve = connect_curves_tangentially(verts[1], verts[2])
    # if this has worked, the center of the created curve should be at x=0, y=0
    # (i dont know how to work out where cubit would put the z coord)
    assert connecting_curve.handle.curve_center()[1] == 0
    assert connecting_curve.handle.curve_center()[2] == 0

    with cubism_err:
        # fail if wrong CubitInstance geometry type
        cubit.brick(1, 1, 1)
        connect_curves_tangentially(verts[0], CubitInstance(1, "volume"))

    with cubism_err:
        # fail if either of the curves have a missing tangent
        connect_curves_tangentially(verts[0], Vertex(5, 5, 5).create())


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
    assert (
        surf.normal_at((0, 0, 0)) == (0, 0, 1) or
        surf.normal_at((0, 0, 0)) == (0, 0, -1)
        )


def test_make_cylinder_along():
    cylinder = make_cylinder_along(2, 5, "x")
    moments = cylinder.handle.principal_moments()
    assert cylinder.handle.volume() == pytest.approx(20*np.pi)
    assert cylinder.handle.centroid() == pytest.approx((0, 0, 0))
    assert moments[0] < moments[1] and moments[0] < moments[2]

    cylinderY = make_cylinder_along(1, 5, "y")
    momentsY = cylinderY.handle.principal_moments()
    assert cylinderY.handle.volume() == pytest.approx(5*np.pi)
    assert cylinderY.handle.centroid() == pytest.approx((0, 0, 0))
    assert momentsY[1] < momentsY[0] and momentsY[1] < momentsY[2]

    cylinderZ = make_cylinder_along(1, 5, "z")
    momentsZ = cylinderZ.handle.principal_moments()
    assert cylinderZ.handle.volume() == pytest.approx(5*np.pi)
    assert cylinderZ.handle.centroid() == pytest.approx((0, 0, 0))
    assert momentsZ[2] < momentsZ[0] and momentsZ[2] < momentsZ[1]

    with cubism_err:
        make_cylinder_along(2, 2, "not an axis")


def test_hypotenuse():
    assert hypotenuse(3, 4) == 5
    assert hypotenuse(-3, 4) == 5
    assert hypotenuse(2, 2, 2, 2) == hypotenuse(4)


def test_arctan():
    assert arctan(3, 3) == np.pi/4
    assert arctan(1, 0) == np.pi/2
    assert arctan(3, -3) == 3*np.pi/4


# tests for Vertex
def test_eq(vertex):
    assert vertex == Vertex(1, 2, 3)
    assert vertex != Vertex(1, 2, 2)


def test_repr(vertex):
    assert vertex == eval(repr(vertex))


def test_str(vertex):
    assert str(vertex) == "1 2 3"


def test_add(vertex: Vertex):
    vert_sum = vertex + Vertex(1, 0, -1)
    assert vert_sum == Vertex(2, 2, 2)
    with type_err:
        vertex + 1


def test_neg(vertex):
    assert -vertex == Vertex(-1, -2, -3)


def test_sub(vertex):
    assert vertex - Vertex(0, 1, 2) == Vertex(1, 1, 1)
    with type_err:
        vertex - 1


def test_mul(vertex: Vertex):
    assert vertex * Vertex(1, 2, 3) == Vertex(1, 4, 9)
    assert vertex.__rmul__(Vertex(1, 2, 3)) == Vertex(1, 4, 9)
    assert vertex * 2 == Vertex(2, 4, 6)
    assert 2 * vertex == Vertex(2, 4, 6)
    assert vertex * Line(Vertex(1, 2, 3)) == Vertex(1, 4, 9)
    assert vertex.__rmul__(Line(Vertex(1, 2, 3))) == Vertex(1, 4, 9)


def test_create(vertex: Vertex):
    created_vertex = vertex.create()
    assert created_vertex.handle.coordinates() == (1, 2, 3)
    with cubism_err:
        Vertex("ha").create()


def test_rotate(vertex: Vertex):
    vert1 = vertex.rotate(np.pi/2)
    assert (vert1.x, vert1.y, vert1.z) == pytest.approx((-2, 1, 3))


def test_distance(vertex: Vertex):
    assert vertex.distance() == hypotenuse(vertex.x, vertex.y, vertex.z)
    assert Vertex(0).unit() == Vertex(0)


def test_unit(vertex: Vertex):
    assert Vertex(5, 0, 0).unit() == Vertex(1, 0, 0)
    assert vertex.unit().distance() == 1


def test_extend_to_y():
    assert Vertex(1, 1).extend_to_y(5).x == 5
    assert Vertex(-3, 2).extend_to_y(-4).x == 6


def test_extend_to_x():
    assert Vertex(1, 1).extend_to_x(5).y == 5
    assert Vertex(4, 5).extend_to_x(8).y == 10


# tests for Line
def test_line_eq(line):
    assert line == Line(Vertex(1, 2), Vertex(1))


def test_line_repr(line):
    assert line == pytest.approx(eval(repr(line)))


def test_line_vertex_at(line: Line):
    assert line.vertex_at(0) == Vertex(0, -2)
    assert line.vertex_at(0, 5, 2) == Vertex(0, -2)
    assert line.vertex_at(y=2) == Vertex(2, 2)
    assert line.vertex_at(z=3) is None
    assert Line(Vertex(0, 1, 0)).vertex_at(x=5) is None
    assert Line(Vertex(1, 0, 0)).vertex_at(y=5) is None
    assert Line(Vertex(0, 0, 1)).vertex_at(z=5) == Vertex(0, 0, 5)
    with cubism_err:
        line.vertex_at()


def test_line_vertex_from_dist():
    line = Line(Vertex(0.03, 0.04), Vertex(3))
    assert verts_approx_equal(line.vertex_from_dist(5), Vertex(6, 4))
    assert verts_approx_equal(line.vertex_from_dist(0), Vertex(3))
    assert verts_approx_equal(line.vertex_from_dist(-5), Vertex(0, -4))


def test_line_from_vertices():
    line1 = Line.from_vertices(Vertex(1, 1, 1), Vertex(3, 3, 3))
    assert line1 == Line(Vertex(2, 2, 2), Vertex(1, 1, 1))
    line2 = Line.from_vertices(Vertex(2, 0, 1), Vertex(3, -3, 3))
    assert line2 == Line(Vertex(1, -3, 2), Vertex(2, 0, 1))


def test_make_surface():
    vertices = [Vertex(5, 5), Vertex(5, -5), Vertex(-5, -5), Vertex(-5, 5)]
    surf = make_surface(vertices, []).handle
    assert surf.area() == 100
    assert (
        surf.normal_at((0, 0, 0)) == (0, 0, 1) or
        surf.normal_at((0, 0, 0)) == (0, 0, -1)
        )


def test_blunt_corner():
    outline = [Vertex(1), Vertex(0), Vertex(0, 1)]

    # bluntness == 0.1 should split (0, 0) along x and y axes
    blunted1 = blunt_corner(outline, 1, 0.1)
    assert blunted1 == [Vertex(0.1), Vertex(0, 0.1)]

    # bluntness == 0 should leave vertices unchanged
    blunted2 = blunt_corner(outline, 1, 0)
    assert blunted2 == [Vertex(0)]


def test_fetch():
    assert fetch([[1, 2], 3, [4, 5]]) == [2, 3, 4]
    assert fetch([[1, 2], 3, 4]) == [2, 3, 4]
    assert fetch([2, 3, [4, 5]]) == [2, 3, 4]
    assert fetch([2, 3, 4]) == [2, 3, 4]


def test_unroll():
    tangled1 = [[0, 1, 2], 3, 4, [5, 6], 7]
    tangled2 = [0, [1, 2], 3, 4, 5, 6, 7]
    assert unroll(tangled1) == unroll(tangled2) == list(range(8))


def test_blunt_corners():
    verts = [Vertex(1), Vertex(0), Vertex(0, 1), Vertex(1, 1)]
    blunted1 = blunt_corners(verts, [1, 2], [0.1, 0.1])
    assert blunted1 == [Vertex(1), Vertex(0.1), Vertex(0, 0.1), Vertex(0, 0.9), Vertex(0.1, 1), Vertex(1, 1)]

    verts = [Vertex(1), Vertex(0), Vertex(0, 1), Vertex(1, 1)]
    blunted2 = blunt_corners(verts, [1], [0.1])
    assert blunted2 == [Vertex(1), Vertex(0.1), Vertex(0, 0.1), Vertex(0, 1), Vertex(1, 1)]
