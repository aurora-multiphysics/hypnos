'''
geometry.py
author(s): Sid Mungale

Functions and classes to help with geometrical calculations in cubit

Functions
---------
create_2d_vertex: x-y plane vertex in 3D space
connect_vertices_straight: connect with straight curve
connect_vertices_tangentially: connect along tangent curves
make_surface_from_curves: make surface from bounding curves
make_cylinder_along: make cylinder along an cartesian axis
make_loop: connect many vertices with curves
hypotenuse: square of sum of roots
arctan: arctan -> (0, pi)
make_surface: make surface from bounding vertices

Classes
-------
Vertex: Representation of a vertex in 3D space
Line: Representation of a line in point-slope form

(c) Copyright UKAEA 2024
'''


from blobmaker.generic_classes import CubitInstance, CubismError, cmd
from blobmaker.cubit_functions import get_id_string, cmd_geom
import numpy as np


def create_2d_vertex(x: float, y: float):
    '''Create a vertex in the x-y plane

    Parameters
    ----------
    x : float
        x-coordinate
    y : float
        y-coordinate

    Returns
    -------
    CubitInstance
        created vertex
    '''
    vertex = cmd_geom(f"create vertex {x} {y} 0", "vertex")
    return vertex


def connect_vertices_straight(vertex1: CubitInstance, vertex2: CubitInstance) -> CubitInstance:
    '''Connect 2 vertices with a straight curve

    Parameters
    ----------
    vertex1 : CubitInstance
        vertex to connect
    vertex2 : CubitInstance
        vertex to connect

    Returns
    -------
    CubitInstance
        Connection curve
    '''
    if vertex1.geometry_type == "vertex" and vertex2.geometry_type == "vertex":
        connection = cmd_geom(
            f"create curve vertex {vertex1.cid} {vertex2.cid}", "curve"
            )
    else:
        raise CubismError("Given geometries are not vertices")
    return connection


def connect_curves_tangentially(vertex1: CubitInstance, vertex2: CubitInstance) -> CubitInstance:
    '''Connect 2 curves at the given vertices,
    with the connection tangent to both curves.

    Parameters
    ----------
    vertex1 : CubitInstance
        vertex to connect from
    vertex2 : CubitInstance
        vertex to connect to

    Returns
    -------
    CubitInstance
        Connection curve
    '''
    if vertex1.geometry_type == "vertex" and vertex2.geometry_type == "vertex":
        connection = cmd_geom(
            f"create curve tangent vertex {vertex1.cid} vertex {vertex2.cid}",
            "curve"
            )
    else:
        raise CubismError("Given geometries are not vertices")
    return connection


def make_surface_from_curves(curves_list: list[CubitInstance]) -> CubitInstance:
    '''Make surface from bounding curves

    Parameters
    ----------
    curves_list : list[CubitInstance]
        list of bounding curves

    Returns
    -------
    CubitInstance
        Created surface
    '''
    curve_id_string = get_id_string(curves_list)
    surface = cmd_geom(f"create surface curve {curve_id_string}", "surface")
    return surface


def make_cylinder_along(radius: float, length: float, axis: str = "z") -> CubitInstance:
    '''Make a cylinder along a cartesian axis

    Parameters
    ----------
    radius : float
    length : float
    axis : str, optional
        cartesian axis along which to make cylinder, by default "z"

    Returns
    -------
    CubitInstance
        created cylinder
    '''
    axis = axis.lower()
    cylinder = cmd_geom(
        f"create cylinder radius {radius} height {length}",
        "volume"
        )
    if axis == "x":
        cmd(f"rotate volume {cylinder.cid} about Y angle -90")
    elif axis == "y":
        cmd(f"rotate volume {cylinder.cid} about X angle -90")
    elif axis != "z":
        raise CubismError(f"Axis not recognised: {axis}")
    return cylinder


def make_loop(vertices: list[CubitInstance], tangent_indices: list[int]) -> list[CubitInstance]:
    '''Connect vertices with straight curves.
    For specified indices connect with curves tangential to adjacent curves.

    Parameters
    ----------
    vertices : list[CubitInstance]
        vertices to connect
    tangent_indices : list[int]
        indices of vertices to start a tangent-connection from,
        for example to connect the 2nd and 3rd vertices tangentially
        this would be [1]

    Returns
    -------
    list[CubitInstance]
        Curves making up the connected vertices
    '''
    curves = list(np.zeros(len(vertices)))
    for i in range(len(vertices)-1):
        if i not in tangent_indices:
            curves[i] = connect_vertices_straight(vertices[i], vertices[i+1])
    if -1 in tangent_indices or len(vertices)-1 in tangent_indices:
        curves[-1] = connect_curves_tangentially(vertices[-1], vertices[0])
    else:
        curves[-1] = connect_vertices_straight(vertices[-1], vertices[0])
    # need to do this after straight connections for tangents to actually exist
    for i in tangent_indices:
        if 0 <= i < len(vertices) - 1:
            curves[i] = connect_curves_tangentially(vertices[i], vertices[i+1])
    return curves


def hypotenuse(*sides: float):
    '''Take root of sum of squares

    Returns
    -------
    np.float64 (probably)
        hypotenuse
    '''
    squared = [np.square(side) for side in sides]
    return np.sqrt(np.sum(squared))


def arctan(opposite: float, adjacent: float):
    '''Arctan with range 0, 2pi. Takes triangle side lengths.

    Parameters
    ----------
    opposite : float
        'opposite' side of a right-angled triangle
    adjacent : float
        'adjacent' side of a right-angled triangle

    Returns
    -------
    float
        arctan(opposite/adjacent)
    '''
    if adjacent == 0:
        arctan_angle = np.pi/2
    elif adjacent > 0:
        arctan_angle = np.arctan(opposite / adjacent)
    else:
        arctan_angle = np.pi + np.arctan(opposite / adjacent)
    return arctan_angle


class Vertex():
    '''Representation of a vertex. Attributes are 3D coordinates.'''
    def __init__(self, x: int, y=0, z=0) -> None:
        self.x = x
        self.y = y
        self.z = z

    def __eq__(self, other):
        if not isinstance(other, Vertex):
            return NotImplemented
        return self.x == other.x and self.y == other.y and self.z == other.z

    def __repr__(self) -> str:
        return f"Vertex({self.x}, {self.y}, {self.z})"

    def __add__(self, other):
        if isinstance(other, Vertex):
            x = self.x + other.x
            y = self.y + other.y
            z = self.z + other.z
            return Vertex(x, y, z)
        else:
            return NotImplemented

    def __neg__(self):
        x = -self.x
        y = -self.y
        z = -self.z
        return Vertex(x, y, z)

    def __sub__(self, other):
        if isinstance(other, Vertex):
            x = self.x - other.x
            y = self.y - other.y
            z = self.z - other.z
            return Vertex(x, y, z)
        else:
            return NotImplemented

    def __mul__(self, other):
        if isinstance(other, Vertex):
            return Vertex(self.x*other.x, self.y*other.y, self.z*other.z)
        elif isinstance(other, Line):
            return Vertex(
                self.x*other.slope.x,
                self.y*other.slope.y,
                self.z*other.slope.z)
        else:
            return Vertex(self.x*other, self.y*other, self.z*other)

    def __rmul__(self, other):
        if isinstance(other, Vertex):
            return Vertex(self.x*other.x, self.y*other.y, self.z*other.z)
        elif isinstance(other, Line):
            return Vertex(
                self.x*other.slope.x,
                self.y*other.slope.y,
                self.z*other.slope.z)
        else:
            return Vertex(self.x*other, self.y*other, self.z*other)

    def __str__(self) -> str:
        return f"{self.x} {self.y} {self.z}"

    def create(self) -> CubitInstance:
        '''Create this vertex in cubit.

        Returns
        -------
        CubitInstance
            created vertex
        '''
        vertex = cmd_geom(f"create vertex {str(self)}", "vertex")
        return vertex

    def rotate(self, z: float, y=0, x=0) -> 'Vertex':
        '''Rotate about z, then y, and then x axes in 3D space.
        IN RADIANS.

        Parameters
        ----------
        z : float
            angle to rotate about z-axis
        y : float, optional
            angle to rotate about y-axis, by default 0
        x : float, optional
            angle to rotate about x-axis, by default 0

        Returns
        -------
        Vertex
            rotated vertex
        '''
        x_rotated = (self.x*np.cos(z)*np.cos(y)) + (self.y*(np.cos(z)*np.sin(y)*np.sin(x) - np.sin(z)*np.cos(x))) + (self.z*(np.cos(z)*np.sin(y)*np.cos(x) + np.sin(z)*np.sin(x)))
        y_rotated = (self.x*np.sin(z)*np.cos(y)) + (self.y*(np.sin(z)*np.sin(y)*np.sin(x) + np.cos(z)*np.cos(x))) + (self.z*(np.sin(z)*np.sin(y)*np.cos(x) - np.cos(z)*np.sin(x)))
        z_rotated = (-self.z*np.sin(y)) + (self.y*np.cos(y)*np.sin(x)) + (self.z*np.cos(y)*np.cos(x))
        return Vertex(x_rotated, y_rotated, z_rotated)

    def distance(self):
        '''Return distance of vertex from (0, 0, 0)

        Returns
        -------
        np.float64
            distance
        '''
        return np.sqrt(np.square(self.x)+np.square(self.y)+np.square(self.z))

    def unit(self) -> 'Vertex':
        '''Return a vertex in the same direction with length 1 unit

        Returns
        -------
        Vertex
            unit vector
        '''
        dist = self.distance()
        if dist == 0:
            return Vertex(0)
        x = self.x / dist
        y = self.y / dist
        z = self.z / dist
        return Vertex(x, y, z)

    def extend_to_y(self, y: float) -> 'Vertex':
        '''Extend vertex from (0, 0, 0) up to y-coord

        Parameters
        ----------
        y : float
            y-coordinate of point to extend to

        Returns
        -------
        Vertex
            extended point
        '''
        x = self.x * y / self.y
        return Vertex(x, y)

    def extend_to_x(self, x):
        '''Extend vertex from (0, 0, 0) up to x-coord

        Parameters
        ----------
        x : float
            x-coordinate of point to extend to

        Returns
        -------
        Vertex
            extended point
        '''
        y = self.y * x / self.x
        return Vertex(x, y)


class Line:
    '''Helps with calculations involving points on a line
    defined by a point + slope

    Attributes
    ----------
    const: Vertex
        Point the line passes through
    slope: Vertex
        Direction the line points in
    '''
    def __init__(self, slope: Vertex, const: Vertex = Vertex(0)) -> None:
        self.const = const
        self.slope = slope

    def __repr__(self) -> str:
        return f"Line({repr(self.slope)}, {repr(self.const)})"

    def __eq__(self, other) -> bool:
        if not isinstance(other, Line):
            return NotImplemented
        return self.const == other.const and self.slope == other.slope

    def __mul__(self, other):
        return other * self.slope

    def __rmul__(self, other):
        return other * self.slope

    def vertex_at(self, x: float = None, y: float = None, z: float = None) -> Vertex | None:
        '''Find the point on this line with given x, y, or z coordinate

        Parameters
        ----------
        x : float, optional
            x-coordinate, by default None
        y : float, optional
            y-coordinate, by default None
        z : float, optional
            z-coordinate, by default None

        Returns
        -------
        Vertex | None
            Point on line | None
        '''
        slope = self.slope.unit()
        if x is not None:
            if slope.x == 0:
                return None
            k = (x - self.const.x) / slope.x
            return Vertex(
                x,
                self.const.y + k*slope.y,
                self.const.z + k*slope.z
                )
        elif y is not None:
            if slope.y == 0:
                return None
            k = (y - self.const.y) / slope.y
            return Vertex(
                self.const.x + k*slope.x,
                y,
                self.const.z + k*slope.z
                )
        elif z is not None:
            if slope.z == 0:
                return None
            k = (z - self.const.z) / slope.z
            return Vertex(
                self.const.x + k*slope.x,
                self.const.y + k*slope.y,
                z
                )
        else:
            raise CubismError("At least one argument should be provided")

    def line_at(self, const: Vertex) -> 'Line':
        '''Return a line with the same slope but new const

        Parameters
        ----------
        const : Vertex
            vertex the new line passes through

        Returns
        -------
        Line
            line with same slope
        '''
        return Line(self.slope, const)

    def vertex_from_dist(self, distance: float) -> Vertex:
        '''Get the vertex on this line at specified distance from const

        Parameters
        ----------
        distance : float
            distance along line to find vertex

        Returns
        -------
        Vertex
            vertex on line at specified distance
        '''
        unit_slope = self.slope.unit()
        vert = self.const + (distance * unit_slope)
        return vert

    @classmethod
    def from_vertices(cls, from_vert: Vertex, to_vert: Vertex) -> 'Line':
        '''create a line passing through the given two vertices

        Parameters
        ----------
        from_vert : Vertex
            describes const of new line
        to_vert : Vertex
            describes slope along with from_vert

        Returns
        -------
        Line
            line passing through given vertices
        '''
        slope = to_vert - from_vert
        point = from_vert
        return Line(slope, point)


def make_surface(vertices: list[Vertex], tangent_indices: list[int]) -> CubitInstance:
    '''Make surface from vertices.
    Curves between specified vertices will be tangential to
    straight lines at either vertex.

    Parameters
    ----------
    vertices : list[Vertex]
        list of vertices to connect into bounding curves
    tangent_indices : list[int]
        indices of vertices to begin a tangent-connection from

    Returns
    -------
    CubitInstance
        Connected and bound surface
    '''
    created_vertices = [vertex.create() for vertex in vertices]
    loop = make_loop(created_vertices, tangent_indices)
    surface = make_surface_from_curves(loop)
    return surface


def blunt_corner(vertices: list[Vertex], idx: int, bluntness: float) -> list[Vertex]:
    '''Blunt a corner in a list of vertices. The provided list of vertices
    describe the outline of some geometry bounded by straight lines connecting
    the points. This function will look at vertex at the provided index, and
    'blunt' the corner it represents by splitting it into 2 vertices, each a
    distance <bluntness> away from the original.

    Parameters
    ----------
    vertices : list[Vertex]
        vertices describing the outline of a geometry
    idx : int
        index of corner to be blunted
    bluntness : float
        distance to blunt vertex by

    Returns
    -------
    list[Vertex]
        list of 'blunted' vertices
    '''
    if bluntness == 0:
        return [vertices[idx]]

    dir1 = Line.from_vertices(vertices[idx], vertices[idx-1])
    dir2 = Line.from_vertices(vertices[idx], vertices[idx+1])

    split1 = dir1.vertex_from_dist(bluntness)
    split2 = dir2.vertex_from_dist(bluntness)

    return [split1, split2]


def fetch(unwrap: list) -> list:
    '''
    "unwrap" a list locally and return items.
    [[A, B], C, [D, E]] -> [B, C, D]
    [B, C, [D, E]]      -> [B, C, D]
    [[A, B], C, D]      -> [B, C, D]
    [B, C, D]           -> [B, C, D]

    Parameters
    ----------
    verts : list
        list

    Returns
    -------
    list
        "unwrapped" list
    '''
    return_list = [0, unwrap[1], 0]
    if len(unwrap) != 3:
        raise CubismError('expected list of length 3')
    return_list[0] = unwrap[0][1] if type(unwrap[0]) is list else unwrap[0]
    return_list[2] = unwrap[2][0] if type(unwrap[2]) is list else unwrap[2]
    return return_list


def unroll(listlike: list) -> list:
    '''Unroll lists inside lists

    Parameters
    ----------
    listlike : list
        A list that may have other lists inside it

    Returns
    -------
    list
        "unrolled" list
    '''
    return_list = []
    for item in listlike:
        if type(item) is list:
            return_list.extend(item)
        else:
            return_list.append(item)
    return return_list


def blunt_corners(vertices: list[Vertex], ids: list[int], bluntnesses: list[int]) -> list:
    '''Blunt many corners as in blunt_corner simultaneously

    Parameters
    ----------
    vertices : list[Vertex]
        vertices describing a geometrical outline
    ids : list[int]
        indices of vertices to blunt
    bluntnesses : list[int]
    corresponding amounts to blunt by

    Returns
    -------
    list
        list of blunted vertices
    '''
    if len(bluntnesses) != len(ids):
        raise CubismError('length of bluntnesses should be the same as ids')
    for i, bluntness in zip(ids, bluntnesses):
        vertices[i] = blunt_corner(fetch(vertices[i-1:i+2]), 1, bluntness)
    return unroll(vertices)
