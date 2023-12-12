from generic_classes import GenericCubitInstance, CubismError
from cubit_functions import cubit_cmd_check
import numpy as np

def create_2d_vertex(x, y):
    vertex = cubit_cmd_check(f"create vertex {x} {y} 0", "vertex")
    if vertex:
        return vertex
    else:
        raise CubismError("Failed to create vertex")

def connect_vertices_straight(vertex1: GenericCubitInstance, vertex2: GenericCubitInstance):
    assert vertex1.geometry_type == "vertex" and vertex2.geometry_type == "vertex" 
    connection = cubit_cmd_check(f"create curve vertex {vertex1.cid} {vertex2.cid}", "curve")
    return connection

def connect_curves_tangentially(vertex1: GenericCubitInstance, vertex2: GenericCubitInstance):
    assert vertex1.geometry_type == "vertex" and vertex2.geometry_type == "vertex"
    connection = cubit_cmd_check(f"create curve tangent vertex {vertex1.cid} vertex {vertex2.cid}", "curve")
    return connection

class Vertex2D():
    def __init__(self, x: int, y: int=0) -> None:
        self.x = x
        self.y = y
    
    def __add__(self, other):
        x = self.x + other.x
        y = self.y + other.y
        return Vertex2D(x, y)
    
    def create(self):
        return create_2d_vertex(self.x, self.y)
    
    def rotate(self, angle: int):
        '''rotate clockwise by angle. don't rotate after creation.

        :param angle: angle in radians
        :type angle: int
        '''
        x = (self.x * np.cos(angle)) - (self.y * np.sin(angle))
        y = (self.x * np.sin(angle)) + (self.y * np.cos(angle))
        return Vertex2D(x, y)