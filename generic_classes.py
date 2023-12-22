import sys
sys.path.append('/opt/Coreform-Cubit-2023.8/bin')
import cubit
from constants import *

# everything in cubit will need to be referenced by a geometry type and id
class GenericCubitInstance:
    '''
    Wrapper for cubit geometry entity.
    Can access cubit ID (cid), geometry type, and cubit handle (cubitInstance).
    Can destroy cubit instance. Can copy itself. Can update an instance to refer to a different cubit instance.
    '''
    def __init__(self, cid: int, geometry_type: str) -> None:
        self.cid = cid
        self.geometry_type = geometry_type
        self.cubitInstance = get_cubit_geometry(self.cid, self.geometry_type)
    
    def __str__(self) -> str:
        return f"{self.geometry_type} {self.cid}"

    def destroy_cubit_instance(self):
        '''delete cubitside instance'''
        cubit.cmd(f"delete {self.geometry_type} {self.cid}")
    
    def copy_cubit_instance(self):
        '''create a copy, both of this GenericCubitInstance and the cubitside instance'''
        cubit.cmd(f"{self.geometry_type} {self.cid} copy")
        copied_id = cubit.get_last_id(self.geometry_type)
        return GenericCubitInstance(copied_id, self.geometry_type)
    
    def update_reference(self, cid, geometry_type):
        '''change what this instance refers to cubitside'''
        self.cid = cid
        self.geometry_type = geometry_type
        self.cubitInstance = get_cubit_geometry(cid, geometry_type)

# make finding instances less annoying
def get_cubit_geometry(geometry_id: int, geometry_type: str):
    '''returns cubit instance given id and geometry type

    :param geometry_id: Cubit ID of geometry
    :type geometry_id: int
    :param geometry_type: Cubit geometry type (body/volume/surface/curve/vertex)
    :type geometry_type: str
    :raises CubismError: If geometry type provided is not recognised
    :return: Cubit handle of geometry
    '''
    if geometry_type == "body":
        return cubit.body(geometry_id)
    elif geometry_type == "volume":
        return cubit.volume(geometry_id)
    elif geometry_type == "surface":
        return cubit.surface(geometry_id)
    elif geometry_type == "curve":
        return cubit.curve(geometry_id)
    elif geometry_type == "vertex":
        return cubit.vertex(geometry_id)
    else:
        raise CubismError(f"geometry type not recognised: {geometry_type}")

# raise this when bad things happen
class CubismError(Exception):
    pass
