from constants import *
from generic_classes import *
from materials import MaterialsTracker
from cubit_functions import from_bodies_to_volumes, from_everything_to_bodies, cubit_cmd_check

class ExternalComponent(GenericCubitInstance):
    def __init__(self, cid: int, geometry_type: str) -> None:
        super().__init__(cid, geometry_type)
        # track external components
        MaterialsTracker().add_geometry_to_material(GenericCubitInstance(self.cid, self.geometry_type), "external")

# very basic implementations for complex components
class ComplexComponent:
    # stores information about what materials exist. geometries can then be found from groups with the same name
    complexComponentMaterials = MaterialsTracker()
    def __init__(self, geometry, classname, material):
        self.subcomponents = []
        self.classname = classname
        self.geometry = geometry
        self.material = material
        self.make_geometry()
        # add geometries to material tracker
        for subcomponent in self.subcomponents:
            self.complexComponentMaterials.add_geometry_to_material(subcomponent, self.material)
    
    def add_to_subcomponents(self, subcomponents):
        '''Add GenericCubitInstance or list of GenericCubitInstances to subcomponents attribute'''
        if isinstance(subcomponents, GenericCubitInstance):
            self.subcomponents.append(subcomponents)
        elif type(subcomponents) == list:
            for subcomponent in subcomponents:
                if isinstance(subcomponent, GenericCubitInstance):
                    self.subcomponents.append(subcomponents)

    def make_geometry(self):
        '''create geometry in cubit. if the class is a blob or walls, make those. otherwise break.'''
        if self.classname in BLOB_CLASSES:
            self.add_to_subcomponents(self.__create_cubit_blob(self.geometry))
        else:
            raise CubismError("Wrong class name somewhere?: " + self.classname)

    def convert_to_3d_vector(self, dim):
        if type(dim) == int:
            return_vector = [dim for i in range(3)]
        elif len(dim) == 1:
            return_vector = [dim[0] for i in range(3)]
        elif len(dim) == 3:
            return_vector = dim
        else:
            raise CubismError("thickness should be either a 1D or 3D vector (or scalar)")
        return return_vector

    def __create_cubit_blob(self, geometry: dict):
        '''create cube (if scalar/1D) or cuboid (if 3D) with dimensions. 
        Rotate it about the y-axis, x-axis, y-axis if euler_angles are specified. 
        Move it to position if specified'''
        # setup variables
        dims= self.convert_to_3d_vector(geometry["dimensions"])
        pos= geometry["position"] if "position" in geometry.keys() else [0, 0, 0]
        euler_angles= geometry["euler_angles"] if "euler_angles" in geometry.keys() else [0, 0, 0]
        # create a cube or cuboid.
        blob = cubit.brick(dims[0], dims[1], dims[2])
        cid = cubit.get_last_id("volume")
        # orientate according to euler angles
        axis_list = ['y', 'x', 'y']
        for i in range(3): # hard-coding in 3D?
            if not euler_angles[i] == 0:
                cubit.cmd(f'rotate volume {cid} angle {euler_angles[i]} about {axis_list[i]}')
        # move to specified position
        cubit.move(blob, pos)
        # return instance for further manipulation
        return GenericCubitInstance(cid, "volume")

    def update_reference_and_tracking(self, geometry_list):
        '''Change what geometries this instance refers to'''
        self.complexComponentMaterials.update_tracking_list(self.subcomponents, geometry_list, self.material)
        self.subcomponents = geometry_list
    
    def stop_tracking(self):
        '''stop tracking the material of this component'''
        for subcomponent in self.subcomponents:
            self.complexComponentMaterials.stop_tracking_in_material(subcomponent, self.material)

    def as_bodies(self):
        '''convert subcomponent references to references to their owning bodies'''
        owning_bodies = from_everything_to_bodies(self.subcomponents)
        self.update_reference_and_tracking(owning_bodies)
    
    def as_volumes(self):
        '''convert any references to bodies in the subcomponents to references to their composing volumes'''
        self.update_reference_and_tracking(from_bodies_to_volumes(self.subcomponents))

    def get_subcomponents(self):
        return self.subcomponents

class SurroundingWallsComponent(ComplexComponent):
    '''Surrounding walls, filled with air'''
    def __init__(self, geometry: dict, material, air):
        super().__init__(geometry, "surrounding_walls", material)

        # fill room with air
        self.air_material = air
        self.air = AirComponent(self.geometry, air) if air != "none" else False
    
    def is_air(self):
        '''Does this room have air in it?'''
        return isinstance(self.air, AirComponent)
    
    def air_as_volumes(self):
        '''reference air as volume entities instead of body entities'''
        if self.is_air():
            self.air.as_volumes()
    
    def get_air_subcomponents(self):
        return self.air.get_subcomponents()
    
    def make_geometry(self):
        '''create 3d room with outer dimensions dimensions (int or list) and thickness (int or list)'''
        # get variables
        outer_dims= self.convert_to_3d_vector(self.geometry["dimensions"])
        thickness= self.convert_to_3d_vector(self.geometry["thickness"])
        # create room
        subtract_vol = cubit.brick(outer_dims[0]-2*thickness[0], outer_dims[1]-2*thickness[1], outer_dims[2]-2*thickness[2])
        block = cubit.brick(outer_dims[0], outer_dims[1], outer_dims[2])
        room = cubit.subtract([subtract_vol], [block])
        room_id = cubit.get_last_id("volume")
        return GenericCubitInstance(room_id, "volume")

class AirComponent(ComplexComponent):
    '''Air, stored as body'''
    def __init__(self, geometry, material):
        super().__init__(geometry, "air", material)
        # cubit subtract only keeps body ID invariant, so i will store air as a body
        self.as_bodies()

class BreederComponent(ComplexComponent):
    def __init__(self, geometry, material):
        super().__init__(geometry, "breeder", material)

class StructureComponent(ComplexComponent):
    def __init__(self, geometry, material):
        super().__init__(geometry, "structure", material)

class WallComponent(ComplexComponent):
    def __init__(self, geometry, material):
        super().__init__(geometry, "wall", material)

    def make_geometry(self):
        # get variables
        # wall
        geometry = self.geometry
        thickness= geometry["wall thickness"]
        plane= geometry["wall plane"] if "wall plane" in geometry.keys() else "x"
        pos= geometry["wall position"] if "wall position" in geometry.keys() else 0
        # hole
        hole_pos= geometry["wall hole position"] if "wall hole position" in geometry.keys() else [0, 0]
        hole_radius= geometry["wall hole radius"]
        # wall fills room
        room_dims= self.convert_to_3d_vector(geometry["dimensions"])
        room_thickness= self.convert_to_3d_vector(geometry["thickness"])
        wall_dims = [room_dims[i]-2*room_thickness[i] for i in range(3)]

        # volume to subtract to create a hole
        cubit.cmd(f"create cylinder height {thickness} radius {hole_radius}")
        subtract_vol = GenericCubitInstance(cubit.get_last_id("volume"), "volume")

        # depending on what plane the wall needs to be in, create wall + make hole at right place
        if plane == "x":
            cubit.brick(thickness, wall_dims[1], wall_dims[2])
            wall = GenericCubitInstance(cubit.get_last_id("volume"), "volume")
            cubit.cmd(f"rotate volume {subtract_vol.cid} angle 90 about Y")
            cubit.cmd(f"move volume {subtract_vol.cid} y {hole_pos[1]} z {hole_pos[0]}")
        elif plane == "y":
            cubit.brick( wall_dims[0], thickness, wall_dims[2])
            wall = GenericCubitInstance(cubit.get_last_id("volume"), "volume")
            cubit.cmd(f"rotate volume {subtract_vol.cid} angle 90 about X")
            cubit.cmd(f"move volume {subtract_vol.cid} x {hole_pos[0]} z {hole_pos[1]}")
        elif plane == "z":
            cubit.brick( wall_dims[0], wall_dims[1], thickness)
            wall = GenericCubitInstance(cubit.get_last_id("volume"), "volume")
            cubit.cmd(f"move volume {subtract_vol.cid} x {hole_pos[0]} y {hole_pos[1]}")
        else:
            raise CubismError("unrecognised plane specified")
        
        cubit.cmd(f"subtract volume {subtract_vol.cid} from volume {wall.cid}")
        # move wall
        cubit.cmd(f"move volume {wall.cid} {plane} {pos}")
        
        return GenericCubitInstance(wall.cid, wall.geometry_type)            

class PinComponent(ComplexComponent):
    def __init__(self, geometry, material):
        super().__init__(geometry, "pin", material)
    
    def make_geometry(self):
        geometry = self.geometry
        outer_length = geometry["outer length"]
        inner_length = geometry["inner length"]
        offset = geometry["offset"]
        bluntness = geometry["bluntness"]
        coolant_inlet_radius = geometry["coolant inlet radius"]
        inner_cladding = geometry["inner cladding"]
        breeder_chamber_thickness = geometry["breeder chamber thickness"]
        outer_cladding = geometry["outer cladding"]

