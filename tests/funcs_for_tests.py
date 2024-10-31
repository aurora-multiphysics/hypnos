from blobmaker.geometry import Vertex
from pytest import approx


def verts_approx_equal(vert1: Vertex, vert2: Vertex):
    x = (vert1.x == approx(vert2.x))
    y = (vert1.y == approx(vert2.y))
    z = (vert1.z == approx(vert2.z))

    return x and y and z
