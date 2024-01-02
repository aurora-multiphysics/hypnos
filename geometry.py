from generic_classes import GenericCubitInstance, CubismError
from cubit_functions import cubit_cmd_check, get_id_string
import numpy as np
import cubit

def create_2d_vertex(x, y):
    '''Create a vertex in the x-y plane

    :param x: x-coordinate of vertex
    :type x: int
    :param y: y-coordinate of vertex
    :type y: int
    :raises CubismError: If unable to create vertex
    :return: created vertex
    :rtype: GenericCubitInstance
    '''
    vertex = cubit_cmd_check(f"create vertex {x} {y} 0", "vertex")
    if vertex:
        return vertex
    else:
        raise CubismError("Failed to create vertex")

def connect_vertices_straight(vertex1: GenericCubitInstance, vertex2: GenericCubitInstance):
    '''Connect 2 vertices with a straight curve

    :param vertex1: Vertex to connect
    :type vertex1: GenericCubitInstance
    :param vertex2: Vertex to connect
    :type vertex2: GenericCubitInstance
    :return: Connection curve or False if connection fails
    :rtype: GenericCubitInstance/ bool
    '''
    assert vertex1.geometry_type == "vertex" and vertex2.geometry_type == "vertex" 
    connection = cubit_cmd_check(f"create curve vertex {vertex1.cid} {vertex2.cid}", "curve")
    return connection

def connect_curves_tangentially(vertex1: GenericCubitInstance, vertex2: GenericCubitInstance):
    '''Connect 2 curves at the given vertices, with the connection tangent to both curves. 

    :param vertex1: Vertex to connect
    :type vertex1: GenericCubitInstance
    :param vertex2: Vertex to connect
    :type vertex2: GenericCubitInstance
    :return: Connection curve or False if connection fails
    :rtype: GenericCubitInstance/ bool
    '''
    assert vertex1.geometry_type == "vertex" and vertex2.geometry_type == "vertex"
    connection = cubit_cmd_check(f"create curve tangent vertex {vertex1.cid} vertex {vertex2.cid}", "curve")
    return connection

def make_surface_from_curves(curves_list: list[GenericCubitInstance]):
    '''Make surface from bounding curves

    :param curves_list: List of bounding curves
    :type curves_list: list[GenericCubitInstance]
    :return: surface geometry/ false
    :rtype: GenericCubitInstance/ bool
    '''
    curve_id_string= get_id_string(curves_list)
    surface = cubit_cmd_check(f"create surface curve {curve_id_string}", "surface")
    return surface

def make_cylinder_along(radius: int, length: int, axis: str):
    '''Make a cylinder along one of the cartesian axes

    :param radius: radius of cylinder
    :type radius: int
    :param length: length of cylinder
    :type length: int
    :param axis: axes to create cylinder along: x, y, or z
    :type axis: str
    :return: cylinder geometry
    :rtype: GenericCubitInstance
    '''
    cylinder = cubit_cmd_check(f"create cylinder radius {radius} height {length}", "volume")
    if axis == "x":
        cubit.cmd(f"rotate volume {cylinder.cid} about Y angle -90")
    elif axis == "y":
        cubit.cmd(f"rotate volume {cylinder.cid} about X angle -90")
    return cylinder

def make_loop(vertices: list[GenericCubitInstance], tangent_indices: list[int]):
    '''Connect vertices with straight curves. 
    For specified indices connect with curves tangential to adjacent curves.

    :param vertices: Vertices to connect
    :type vertices: list[GenericCubitInstance]
    :param tangent_indices: Vertices to start tangent curves from
    :type tangent_indices: list[int]
    :return: curve geometries
    :rtype: list[GenericCubitInstance]
    '''
    curves = list(np.zeros(len(vertices)))
    for i in range(len(vertices)-1):
         if not i in tangent_indices:
            curves[i] = connect_vertices_straight(vertices[i], vertices[i+1])
    curves[-1] = connect_vertices_straight(vertices[-1], vertices[0])
    # need to do this after straight connections for tangents to actually exist
    for i in tangent_indices:
        curves[i] = connect_curves_tangentially(vertices[i], vertices[i+1])
    return curves

class Vertex():
    '''Representation of a vertex'''
    def __init__(self, x: int, y= 0, z= 0) -> None:
        self.x = x
        self.y = y
        self.z = z
    
    def __add__(self, other):
        x = self.x + other.x
        y = self.y + other.y
        z = self.z + other.z
        return Vertex(x, y, z)
    
    def __str__(self) -> str:
        return f"{self.x} {self.y} {self.z}"
    
    def create(self):
        '''Create this vertex in cubit.

        :return: created vertex
        :rtype: GenericCubitInstance
        '''
        vertex = cubit_cmd_check(f"create vertex {self.x} {self.y} {self.z}", "vertex")
        if vertex:
            return vertex
        else:
            raise CubismError("Failed to create vertex")
    
    def rotate(self, z: int, y=0, x=0):
        '''Rotate about z then y and then x axes.

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
        return np.sqrt(np.square(self.x)+np.square(self.y)+np.square(self.z))

class Vertex2D(Vertex):
    '''Representation of a vertex in the x-y plane'''
    def __init__(self, x: int, y=0) -> None:
        super().__init__(x, y, 0)
    
    def __add__(self, other):
        x = self.x + other.x
        y = self.y + other.y
        if isinstance(other, Vertex2D):
            return Vertex2D(x, y)
        else:
            return Vertex(x, y, 0)
    
    def __str__(self) -> str:
        return f"{self.x} {self.y}"
    
    def rotate(self, angle: int):
        '''Rotate about the z-axis

        :param angle: angle in radians
        :type angle: int
        :return: rotated vertex
        :rtype: Vertex
        '''
        
        return super().rotate(angle)