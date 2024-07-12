from blobmaker.generic_classes import CubitInstance, CubismError, cmd
from blobmaker.cubit_functions import get_id_string, cmd_geom
import numpy as np


def create_2d_vertex(x, y):
    '''Create a vertex in the x-y plane

    :param x: x-coordinate of vertex
    :type x: int
    :param y: y-coordinate of vertex
    :type y: int
    :raises CubismError: If unable to create vertex
    :return: created vertex
    :rtype: CubitInstance
    '''
    vertex = cmd_geom(f"create vertex {x} {y} 0", "vertex")
    if vertex:
        return vertex
    else:
        raise CubismError("Failed to create vertex")


def connect_vertices_straight(vertex1: CubitInstance, vertex2: CubitInstance):
    '''Connect 2 vertices with a straight curve

    :param vertex1: Vertex to connect
    :type vertex1: CubitInstance
    :param vertex2: Vertex to connect
    :type vertex2: CubitInstance
    :return: Connection curve or False if connection fails
    :rtype: CubitInstance/ bool
    '''
    if vertex1.geometry_type == "vertex" and vertex2.geometry_type == "vertex":
        connection = cmd_geom(f"create curve vertex {vertex1.cid} {vertex2.cid}", "curve")
    else:
        raise CubismError("Given geometries are not vertices")
    return connection


def connect_curves_tangentially(vertex1: CubitInstance, vertex2: CubitInstance):
    '''Connect 2 curves at the given vertices,
    with the connection tangent to both curves.

    :param vertex1: Vertex to connect
    :type vertex1: CubitInstance
    :param vertex2: Vertex to connect
    :type vertex2: CubitInstance
    :return: Connection curve or False if connection fails
    :rtype: CubitInstance/ bool
    '''
    if vertex1.geometry_type == "vertex" and vertex2.geometry_type == "vertex":
        connection = cmd_geom(f"create curve tangent vertex {vertex1.cid} vertex {vertex2.cid}", "curve")
    else:
        raise CubismError("Given geometries are not vertices")
    return connection


def make_surface_from_curves(curves_list: list[CubitInstance]):
    '''Make surface from bounding curves

    :param curves_list: List of bounding curves
    :type curves_list: list[CubitInstance]
    :return: surface geometry/ false
    :rtype: CubitInstance/ bool
    '''
    curve_id_string = get_id_string(curves_list)
    surface = cmd_geom(f"create surface curve {curve_id_string}", "surface")
    return surface


def make_cylinder_along(radius: int, length: int, axis: str = "z"):
    '''Make a cylinder along one of the cartesian axes

    :param radius: radius of cylinder
    :type radius: int
    :param length: length of cylinder
    :type length: int
    :param axis: axes to create cylinder along: x, y, or z
    :type axis: str
    :return: cylinder geometry
    :rtype: CubitInstance
    '''
    axis = axis.lower()
    cylinder = cmd_geom(f"create cylinder radius {radius} height {length}", "volume")
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

    :param vertices: Vertices to connect
    :type vertices: list[CubitInstance]
    :param tangent_indices: Vertices to start tangent curves from
    :type tangent_indices: list[int]
    :return: curve geometries
    :rtype: list[CubitInstance]
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


def hypotenuse(*sides: int):
    '''Take root of sum of squares

    :return: hypotenuse
    :rtype: float
    '''
    squared = [np.square(side) for side in sides]
    return np.sqrt(np.sum(squared))


def arctan(opposite: int, adjacent: int):
    '''Arctan with range 0, 2pi. Takes triangle side lengths.

    :param opposite: 'Opposite' side of a right-angled triangle
    :type opposite: int
    :param adjacent: 'Adjacent' side of a right-angled triangle
    :type adjacent: int
    :return: arctan(opposite/ adjacent)
    :rtype: int
    '''
    if adjacent == 0:
        arctan_angle = np.pi/2
    elif adjacent > 0:
        arctan_angle = np.arctan(opposite / adjacent)
    else:
        arctan_angle = np.pi + np.arctan(opposite / adjacent)
    return arctan_angle


class Vertex():
    '''Representation of a vertex'''
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
            return Vertex(self.x*other.slope.x, self.y*other.slope.y, self.z*other.slope.z)
        else:
            return Vertex(self.x*other, self.y*other, self.z*other)
    
    def __rmul__(self, other):
        if isinstance(other, Vertex):
            return Vertex(self.x*other.x, self.y*other.y, self.z*other.z)
        elif isinstance(other, Line):
            return Vertex(self.x*other.slope.x, self.y*other.slope.y, self.z*other.slope.z)
        else:
            return Vertex(self.x*other, self.y*other, self.z*other)

    def __str__(self) -> str:
        return f"{self.x} {self.y} {self.z}"

    def create(self):
        '''Create this vertex in cubit.

        :return: created vertex
        :rtype: CubitInstance
        '''
        vertex = cmd_geom(f"create vertex {str(self)}", "vertex")
        if vertex:
            return vertex
        else:
            raise CubismError("Failed to create vertex")

    def rotate(self, z: int, y=0, x=0):
        '''Rotate about z, then y, and then x axes.

        :param z: Angle to rotate about the z axis
        :type z: int
        :param y: Angle to rotate about the y axis, defaults to 0
        :type y: int, optional
        :param x: Angle to rotate about the x axis, defaults to 0
        :type x: int, optional
        :return: Rotated vertex
        :rtype: Vertex
        '''
        x_rotated = (self.x*np.cos(z)*np.cos(y)) + (self.y*(np.cos(z)*np.sin(y)*np.sin(x) - np.sin(z)*np.cos(x))) + (self.z*(np.cos(z)*np.sin(y)*np.cos(x) + np.sin(z)*np.sin(x)))
        y_rotated = (self.x*np.sin(z)*np.cos(y)) + (self.y*(np.sin(z)*np.sin(y)*np.sin(x) + np.cos(z)*np.cos(x))) + (self.z*(np.sin(z)*np.sin(y)*np.cos(x) - np.cos(z)*np.sin(x)))
        z_rotated = (-self.z*np.sin(y)) + (self.y*np.cos(y)*np.sin(x)) + (self.z*np.cos(y)*np.cos(x))
        return Vertex(x_rotated, y_rotated, z_rotated)

    def distance(self):
        '''Return distance from (0, 0, 0)

        :return: Distance
        :rtype: np.float64
        '''
        return np.sqrt(np.square(self.x)+np.square(self.y)+np.square(self.z))
    
    def unit(self):
        if self.distance() == 0:
            return Vertex(0)
        x = self.x / self.distance()
        y = self.y / self.distance()
        z = self.z / self.distance()
        return Vertex(x, y, z)
    
    def extend_to_y(self, y):
        x = self.x * y / self.y
        return Vertex(x, y)
    
    def extend_to_x(self, x):
        y = self.y * x / self.x
        return Vertex(x, y)

class Line:
    '''This helps with calculations involving points on a line defined by a point + slope
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

    def vertex_at(self, x: float = None, y: float = None, z: float = None):
        '''Find the vertex on this line with given x, y, or z coordinate

        :param x: x-coordinate, defaults to None
        :type x: float, optional
        :param y: y-coordinate, defaults to None
        :type y: float, optional
        :param z: z-coordinate, defaults to None
        :type z: float, optional
        :return: vertex on the line, if there is no point/ 
        every point has the given x/y/z coordinate then None
        :rtype: Vertex | None
        '''
        slope = self.slope.unit()
        if x is not None:
            if slope.x == 0: return None
            k = (x - self.const.x) / slope.x
            return Vertex(x, self.const.y + k*slope.y, self.const.z + k*slope.z)
        elif y is not None:
            if slope.y == 0: return None
            k = (y - self.const.y) / slope.y
            return Vertex(self.const.x + k*slope.x, y,  self.const.z + k*slope.z)
        elif z is not None:
            if slope.z == 0: return None
            k = (z - self.const.z) / slope.z
            return Vertex(self.const.x + k*slope.x, self.const.y + k*slope.y, z)
        else:
            raise CubismError("At least one argument should be provided")


def make_surface(vertices: list[Vertex], tangent_indices: list[int]):
    '''Make surface from vertices. 
    Curves between chosen vertices will be tangential to straight lines at either vertex.

    :param vertices: Vertices
    :type vertices: list[Vertex]
    :param tangent_indices: Indices of vertices to start a curved line from
    :type tangent_indices: list[int]
    :return: Surface
    :rtype: CubitInstance
    '''
    created_vertices = [vertex.create() for vertex in vertices]
    loop = make_loop(created_vertices, tangent_indices)
    surface = make_surface_from_curves(loop)
    return surface
