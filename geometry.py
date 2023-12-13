from generic_classes import GenericCubitInstance, CubismError
from cubit_functions import cubit_cmd_check
import numpy as np

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

class Vertex2D():
    '''Representation of a vertex in the x-y plane
    '''
    def __init__(self, x: int, y: int=0) -> None:
        self.x = x
        self.y = y
    
    def __add__(self, other):
        x = self.x + other.x
        y = self.y + other.y
        return Vertex2D(x, y)
    
    def create(self):
        '''Create this vertex in cubit.

        :return: created vertex
        :rtype: GenericCubitInstance
        '''
        return create_2d_vertex(self.x, self.y)
    
    def rotate(self, angle: int):
        '''rotate clockwise by angle.

        :param angle: angle in radians
        :type angle: int
        '''
        x = (self.x * np.cos(angle)) - (self.y * np.sin(angle))
        y = (self.x * np.sin(angle)) + (self.y * np.cos(angle))
        return Vertex2D(x, y)
    
    def add_x(self, x: int):
        '''Add to x-coord

        :param x: value to add
        :type x: int
        '''
        return Vertex2D(self.x + x, self.y)
    
    def add_y(self, y):
        '''Add to y-coord

        :param y: value to add
        :type y: int
        '''
        return Vertex2D(self.y, self.y + y)