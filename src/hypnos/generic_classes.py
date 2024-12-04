'''
generic_classes.py
author(s): Sid Mungale

Lowest level objects

(c) Copyright UKAEA 2024
'''

import cubit


# every cubit CL command should use this
def cmd(command: str):
    '''Wrapper for cubit commands'''
    cubit.silent_cmd(command)


# everything in cubit will need to be referenced by a geometry type and id
class CubitInstance:
    '''Wrapper for cubit geometry.'''
    def __init__(self, cid: int, geometry_type: str) -> None:
        self.cid = cid
        self.geometry_type = geometry_type
        try:
            self.handle = get_cubit_geometry(self.cid, self.geometry_type)
        except RuntimeError:
            raise CubismError(
                f"Specified {geometry_type} doesn't exist: {cid}"
                )

    def __eq__(self, other) -> bool:
        if isinstance(other, CubitInstance):
            return (
                self.cid == other.cid and
                self.geometry_type == other.geometry_type
                )
        return NotImplemented

    def __str__(self) -> str:
        return f"{self.geometry_type} {self.cid}"

    def destroy_cubit_instance(self):
        '''delete cubitside instance'''
        cmd(f"delete {self.geometry_type} {self.cid}")

    def copy(self) -> 'CubitInstance':
        '''create a copy of geometry and class instance

        Returns
        -------
        CubitInstance
            Copy of class
        '''
        cmd(f"{self.geometry_type} {self.cid} copy")
        copied_id = cubit.get_last_id(self.geometry_type)
        return CubitInstance(copied_id, self.geometry_type)

    def move(self, vector):
        '''Translate geometry by vector

        Parameters
        ----------
        vector : tuple
            tuple of length 3, coordinates to translate by in 3D space
        '''
        cmd(f"{self} move {vector[0]} {vector[1]} {vector[2]}")

    def update_reference(self, cid: int, geometry_type: str):
        '''Change what geometry this instance refers to

        Parameters
        ----------
        cid : int
            New geometry ID
        geometry_type : str
            New geometry type
        '''
        self.cid = cid
        self.geometry_type = geometry_type
        self.handle = get_cubit_geometry(cid, geometry_type)


# make finding handles less annoying - used by CubitInstance
def get_cubit_geometry(geometry_id: int, geometry_type: str):
    '''Returns cubit instance given id and geometry type

    Parameters
    ----------
    geometry_id : int
        cubit id of geometry
    geometry_type : str
        geometry type

    Returns
    -------
    cubit.geom_entitiy
        corresponding cubit handle for the geometry
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
