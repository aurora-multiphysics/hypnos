from constants import *
from generic_classes import *
from materials import MaterialsTracker
from cubit_functions import from_bodies_to_volumes, from_everything_to_bodies, cubit_cmd_check, get_last_geometry
from geometry import make_surface_from_curves, make_cylinder_along, make_loop, Vertex
import numpy as np

class ExternalComponent(GenericCubitInstance):
    def __init__(self, cid: int, geometry_type: str) -> None:
        super().__init__(cid, geometry_type)
        # track external components
        MaterialsTracker().add_geometry_to_material(GenericCubitInstance(self.cid, self.geometry_type), "external")

# very basic implementations for complex components
class ComplexComponent:
    # stores information about what materials exist. geometries can then be found from groups with the same name
    complexComponentMaterials = MaterialsTracker()
    def __init__(self, classname, json_object: dict):
        self.subcomponents = []
        self.classname = classname
        self.geometry = json_object["geometry"]
        self.material = json_object["material"]
        self.origin = json_object["origin"] if "origin" in json_object.keys() else Vertex(0)

        self.add_to_subcomponents(self.make_geometry())
        if not self.origin == Vertex(0):
            self.move(self.origin)
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
                    self.subcomponents.append(subcomponent)

    def make_geometry(self):
        '''create geometry in cubit. if the class is a blob or walls, make those. otherwise break.'''
        if self.classname in BLOB_CLASSES:
            return self.__create_cubit_blob(self.geometry)
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
                cmd(f'rotate volume {cid} angle {euler_angles[i]} about {axis_list[i]}')
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

    def get_parameters(self, parameters: list):
        return [self.geometry[parameter] for parameter in parameters]
    
    def move(self, vector: Vertex):
        for subcomponent in self.subcomponents:
            cmd(f"{subcomponent.geometry_type} {subcomponent.cid} move {str(vector)}")

class SurroundingWallsComponent(ComplexComponent):
    '''Surrounding walls, filled with air'''
    def __init__(self, json_object: dict):
        super().__init__("surrounding_walls", json_object)

        # fill room with air
        self.air_material = json_object["air"]
        self.air = AirComponent(self.geometry, self.air_material) if self.air_material != "none" else False
    
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
    def __init__(self, json_object: dict):
        super().__init__("air", json_object)
        # cubit subtract only keeps body ID invariant, so i will store air as a body
        self.as_bodies()

class BreederComponent(ComplexComponent):
    def __init__(self, json_object):
        super().__init__("breeder", json_object)

class StructureComponent(ComplexComponent):
    def __init__(self, json_object):
        super().__init__("structure", json_object)

class WallComponent(ComplexComponent):
    def __init__(self, json_object):
        super().__init__("wall", json_object)

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
        cmd(f"create cylinder height {thickness} radius {hole_radius}")
        subtract_vol = GenericCubitInstance(cubit.get_last_id("volume"), "volume")

        # depending on what plane the wall needs to be in, create wall + make hole at right place
        if plane == "x":
            cubit.brick(thickness, wall_dims[1], wall_dims[2])
            wall = GenericCubitInstance(cubit.get_last_id("volume"), "volume")
            cmd(f"rotate volume {subtract_vol.cid} angle 90 about Y")
            cmd(f"move volume {subtract_vol.cid} y {hole_pos[1]} z {hole_pos[0]}")
        elif plane == "y":
            cubit.brick( wall_dims[0], thickness, wall_dims[2])
            wall = GenericCubitInstance(cubit.get_last_id("volume"), "volume")
            cmd(f"rotate volume {subtract_vol.cid} angle 90 about X")
            cmd(f"move volume {subtract_vol.cid} x {hole_pos[0]} z {hole_pos[1]}")
        elif plane == "z":
            cubit.brick( wall_dims[0], wall_dims[1], thickness)
            wall = GenericCubitInstance(cubit.get_last_id("volume"), "volume")
            cmd(f"move volume {subtract_vol.cid} x {hole_pos[0]} y {hole_pos[1]}")
        else:
            raise CubismError("unrecognised plane specified")
        
        cmd(f"subtract volume {subtract_vol.cid} from volume {wall.cid}")
        # move wall
        cmd(f"move volume {wall.cid} {plane} {pos}")
        
        return GenericCubitInstance(wall.cid, wall.geometry_type)            

class PinComponent(ComplexComponent):
    def __init__(self, json_object):
        super().__init__("pin", json_object)
    
    def make_geometry(self):
        # get params
        geometry = self.geometry
        outer_length = geometry["outer length"]
        inner_length = geometry["inner length"]
        offset = geometry["offset"]
        if "bluntness" in geometry.keys():
            inner_bluntness = geometry["bluntness"]
            outer_bluntness = geometry["bluntness"]
        else:
            inner_bluntness = geometry["inner bluntness"]
            outer_bluntness = geometry["outer bluntness"]
        coolant_inlet_radius = geometry["coolant inlet radius"]
        inner_cladding = geometry["inner cladding"]
        breeder_chamber_thickness = geometry["breeder chamber thickness"]
        outer_cladding = geometry["outer cladding"]
        # helpful calculations
        net_thickness = inner_cladding + breeder_chamber_thickness + outer_cladding
        slope_angle = np.arctan(net_thickness / offset)

        pin_vertices = list(np.zeros(12))
        
        # set up points of face-to-sweep
        pin_vertices[0] = Vertex(0, inner_cladding)
        pin_vertices[1] = Vertex(0)

        inner_cladding_ref1 = Vertex(-inner_length)
        pin_vertices[2] = inner_cladding_ref1 + Vertex(inner_bluntness)
        pin_vertices[3] = inner_cladding_ref1 + Vertex(inner_bluntness).rotate(slope_angle)

        outer_cladding_ref1 = inner_cladding_ref1 + Vertex(offset, net_thickness)
        pin_vertices[4] = outer_cladding_ref1 + Vertex(outer_bluntness).rotate(slope_angle-np.pi)
        pin_vertices[5] = outer_cladding_ref1 + Vertex(outer_bluntness)

        pin_vertices[6] = outer_cladding_ref1 + Vertex(outer_length)
        pin_vertices[7] = outer_cladding_ref1 + Vertex(outer_length, -outer_cladding)

        outer_cladding_ref2 = outer_cladding_ref1 + Vertex(outer_cladding * np.tan(slope_angle/2), -outer_cladding)
        pin_vertices[8] = outer_cladding_ref2 + Vertex(outer_bluntness)
        pin_vertices[9] = outer_cladding_ref2 + Vertex(outer_bluntness).rotate(slope_angle-np.pi)

        inner_cladding_ref2 = inner_cladding_ref1 + Vertex(inner_cladding/np.tan(slope_angle) + outer_cladding/np.sin(slope_angle), inner_cladding)
        pin_vertices[10] = inner_cladding_ref2 + Vertex(inner_bluntness).rotate(slope_angle)
        pin_vertices[11] = inner_cladding_ref2 + Vertex(inner_bluntness)

        pin_vertices = [vertex.create() for vertex in pin_vertices]
        pin_curves = make_loop(pin_vertices, [2, 4, 8, 10])                
        surface_to_sweep = make_surface_from_curves(pin_curves)
        cmd(f"sweep surface {surface_to_sweep.cid} axis 0 {-coolant_inlet_radius} 0 1 0 0 angle 360")
        pin = get_last_geometry("volume")
        # realign with origin
        cubit.move(pin.cubitInstance, [inner_length, coolant_inlet_radius, 0])
        return pin

class BreederUnitCoolant(ComplexComponent):
    def __init__(self, json_object: dict):
        super().__init__("coolant", json_object)
    
    def make_geometry(self):
        geometry=self.geometry
        inner_length = geometry["inner length"]
        if "bluntness" in geometry.keys():
            inner_bluntness = geometry["bluntness"]
            outer_bluntness = geometry["bluntness"]
        else:
            inner_bluntness = geometry["inner bluntness"]
            outer_bluntness = geometry["outer bluntness"]
        offset = geometry["offset"]
        pressure_tube_length = geometry["pressure tube length"]
        pressure_tube_radius = geometry["pressure tube radius"]
        pressure_tube_gap = geometry["pressure tube gap"]
        pin_thickness = geometry["pin thickness"]
        inlet_radius = geometry["coolant inlet radius"]

        slope_angle = np.arctan(pin_thickness / offset)

        coolant_vertices = list(np.zeros(10))

        coolant_vertices[0] = Vertex(0)
        coolant_vertices[1] = Vertex(0, inlet_radius)

        inner_cladding_ref1 = Vertex(-inner_length, inlet_radius)
        coolant_vertices[2] = inner_cladding_ref1 + Vertex(inner_bluntness)
        coolant_vertices[3] = inner_cladding_ref1 + Vertex(inner_bluntness).rotate(slope_angle)

        outer_cladding_ref1 = inner_cladding_ref1 + Vertex(offset, pin_thickness)
        coolant_vertices[4] = outer_cladding_ref1 + Vertex(outer_bluntness).rotate(slope_angle-np.pi)
        coolant_vertices[5] = outer_cladding_ref1 + Vertex(outer_bluntness)
        coolant_vertices[6] = outer_cladding_ref1 + Vertex(pressure_tube_length-(offset+pressure_tube_gap))

        coolant_vertices[9] = coolant_vertices[0] + Vertex(-(inner_length+pressure_tube_gap))
        coolant_vertices[8] = coolant_vertices[9] + Vertex(0, pressure_tube_radius)
        coolant_vertices[7] = coolant_vertices[8] + Vertex(pressure_tube_length)

        coolant_vertices = [vertex.create() for vertex in coolant_vertices]
        coolant_curves = make_loop(coolant_vertices, [2, 4])
        surface_to_sweep = make_surface_from_curves(coolant_curves)
        cmd(f"sweep surface {surface_to_sweep.cid} axis 0 0 0 1 0 0 angle 360")
        coolant = get_last_geometry("volume")
        # realign with origin
        cubit.move(coolant.cubitInstance, [inner_length+pressure_tube_gap, 0, 0])
        return coolant

class PressureTubeComponent(ComplexComponent):
    def __init__(self, json_object):
        super().__init__("pressure_tube", json_object)
    
    def make_geometry(self):
        length = self.geometry["length"]
        outer_radius = self.geometry["outer radius"]
        thickness = self.geometry["thickness"]

        subtract_vol = cubit_cmd_check(f"create cylinder height {length-thickness} radius {outer_radius-thickness}", "volume")
        cmd(f"volume {subtract_vol.cid} move 0 0 {-thickness/2}")
        cylinder = cubit_cmd_check(f"create cylinder height {length} radius {outer_radius}", "volume")

        cmd(f"subtract volume {subtract_vol.cid} from volume {cylinder.cid}")
        tube = get_last_geometry("volume")
        cmd(f"rotate volume {tube.cid} about Y angle -90")
        cmd(f"volume {tube.cid} move {length/2} 0 0")
        return tube

class FilterDiskComponent(ComplexComponent):
    def __init__(self, json_object):
        super().__init__("filter_disk", json_object)
    
    def make_geometry(self):
        length = self.geometry["length"]
        outer_radius = self.geometry["outer radius"]
        thickness = self.geometry["thickness"]

        subtract_vol = cubit_cmd_check(f"create cylinder height {length} radius {outer_radius-thickness}", "volume")
        cylinder = cubit_cmd_check(f"create cylinder height {length} radius {outer_radius}", "volume")

        cmd(f"subtract volume {subtract_vol.cid} from volume {cylinder.cid}")
        tube = get_last_geometry("volume")
        cmd(f"rotate volume {tube.cid} about Y angle -90")
        cmd(f"volume {tube.cid} move {length/2} 0 0")
        return tube

class MultiplierComponent(ComplexComponent):
    def __init__(self, json_object):
        super().__init__("multiplier", json_object)
    
    def make_geometry(self):
        inner_radius = self.geometry["inner radius"]
        length = self.geometry["length"]
        side_length = self.geometry["side"]

        subtract_vol = make_cylinder_along(inner_radius, length, "z")
        cmd(f"volume {subtract_vol.cid} move 0 0 {length/2}")

        # hexagonal face
        face_vertex_positions= [Vertex(side_length).rotate(i*np.pi/3) for i in range(6)]
        face_vertices = [vertex.create() for vertex in face_vertex_positions]
        face_curves = make_loop(face_vertices, [])
        face = make_surface_from_curves(face_curves)
        cmd(f"sweep surface {face.cid} vector 0 0 1 distance {length}")
        hex_prism = get_last_geometry("volume")

        cmd(f"subtract volume {subtract_vol.cid} from volume {hex_prism.cid}")
        multiplier = get_last_geometry("volume")
        cmd(f"rotate volume {multiplier.cid} about Y angle 90")

        return multiplier

class BreederChamber(ComplexComponent):
    def __init__(self, json_object):
        super().__init__("breeder", json_object)
    
    def make_geometry(self):
        geometry = self.geometry
        inner_radius = geometry["inner radius"]
        outer_radius = geometry["outer radius"]
        if "bluntness" in geometry.keys():
            inner_bluntness = geometry["bluntness"]
            outer_bluntness = geometry["bluntness"]
        else:
            inner_bluntness = geometry["inner bluntness"]
            outer_bluntness = geometry["outer bluntness"]
        length = self.geometry["length"]
        offset = self.geometry["offset"]

        thickness = outer_radius - inner_radius
        slope_angle = np.arctan(thickness/ offset)
        
        breeder_vertices = list(np.zeros(6))
        breeder_vertices[0] = Vertex(length)
        breeder_vertices[1] = Vertex(inner_bluntness)
        breeder_vertices[2] = Vertex(inner_bluntness).rotate(slope_angle)

        outer_ref = Vertex(offset, thickness)
        breeder_vertices[3] = outer_ref + Vertex(outer_bluntness).rotate(slope_angle-np.pi)
        breeder_vertices[4] = outer_ref + Vertex(outer_bluntness)
        breeder_vertices[5] = Vertex(length, thickness)

        breeder_vertices = [vertex.create() for vertex in breeder_vertices]
        breeder_curves = make_loop(breeder_vertices, [1, 3])
        surface_to_sweep = make_surface_from_curves(breeder_curves)
        cmd(f"sweep surface {surface_to_sweep.cid} axis 0 {-inner_radius} 0 1 0 0 angle 360")
        breeder = get_last_geometry("volume")
        cubit.move(breeder.cubitInstance, [0, inner_radius, 0])

        return breeder

class FirstWallComponent(ComplexComponent):
    def __init__(self, json_object):
        super().__init__("first_wall", json_object)
    
    def make_geometry(self):
        geometry = self.geometry
        inner_width = geometry["inner width"]
        outer_width = geometry["outer width"]
        bluntness = geometry["bluntness"]
        length = geometry["length"]
        thickness = geometry["thickness"]
        sidewall_thickness = geometry["sidewall thickness"]
        height = geometry["height"]

        offset = (outer_width - inner_width)/2
        slope_angle = np.arctan(length/offset)

        # need less vertices when bluntness = 0 so treat as a special case
        if bluntness == 0:
            vertices = list(np.zeros(8))
            vertices[0] = Vertex(0, 0)

            vertices[1] = Vertex(offset, length)
            vertices[2] = vertices[1] + Vertex(inner_width)

            vertices[3] = vertices[0] + Vertex(outer_width)
            vertices[4] = vertices[3] + Vertex(-sidewall_thickness/np.sin(slope_angle))

            vertices[5] = vertices[2] + Vertex(-sidewall_thickness/np.sin(slope_angle)) + Vertex(thickness/np.tan(slope_angle), -thickness, 0)
            vertices[6] = vertices[1] + Vertex(sidewall_thickness/np.sin(slope_angle)) + Vertex(-thickness/np.tan(slope_angle), -thickness, 0)
            vertices[7] = vertices[0] + Vertex(sidewall_thickness/np.sin(slope_angle))

            vertices = [vertex.create() for vertex in vertices]
            face_to_sweep = make_surface_from_curves(make_loop(vertices, []))
        else:
            vertices = list(np.zeros(12))
            vertices[0] = Vertex(0, 0)

            left_ref = Vertex(offset, length)
            vertices[1] = left_ref + Vertex(bluntness).rotate(slope_angle-np.pi)
            vertices[2] = left_ref + Vertex(bluntness)

            right_ref = left_ref + Vertex(inner_width)
            vertices[3] = right_ref + Vertex(-bluntness)
            vertices[4] = right_ref + Vertex(bluntness).rotate(-slope_angle)

            vertices[5] = vertices[0] + Vertex(outer_width)
            vertices[6] = vertices[5] + Vertex(-sidewall_thickness/np.sin(slope_angle))

            right_ref_inner = right_ref + Vertex(-sidewall_thickness/np.sin(slope_angle)) + Vertex(thickness/np.tan(slope_angle), -thickness, 0)
            vertices[7] = right_ref_inner + Vertex(bluntness).rotate(-slope_angle)
            vertices[8] = right_ref_inner + Vertex(-bluntness)

            left_ref_inner = left_ref + Vertex(sidewall_thickness/np.sin(slope_angle)) + Vertex(-thickness/np.tan(slope_angle), -thickness, 0)
            vertices[9] = left_ref_inner + Vertex(bluntness)
            vertices[10] = left_ref_inner + Vertex(bluntness).rotate(slope_angle-np.pi)

            vertices[11] = vertices[0] + Vertex(sidewall_thickness/np.sin(slope_angle))

            vertices = [vertex.create() for vertex in vertices]
            face_to_sweep = make_surface_from_curves(make_loop(vertices, [1, 3, 7, 9]))
        
        # line up sweep direction along y axis
        cmd(f"surface {face_to_sweep.cid} move -{outer_width/2} 0 0")
        cmd(f"surface {face_to_sweep.cid} rotate 90 about x")

        cmd(f"sweep surface {face_to_sweep.cid} vector 0 1 0 distance {height}")
        first_wall = get_last_geometry("volume")
        #cubit.move(first_wall.cubitInstance, [0,0,length])
        return first_wall

class Plate(ComplexComponent):
    def __init__(self, classname, json_object: dict, plate_type, pin_positions= Vertex(0)):
        self.plate_type = plate_type
        self.pin_pos = pin_positions
        super().__init__(classname, json_object)
    
    def __get_back_vertices(self):
        if self.plate_type != "mid":
            extension = self.geometry["extension"]
        front_length = self.geometry["length"]
        right_position = front_length/2 + extension if self.plate_type in ["right", "full"] else front_length/2
        left_position = -(front_length/2 + extension) if self.plate_type in ["left", "full"] else -front_length/2
        return left_position, right_position

    def make_geometry(self):
        thickness = self.geometry["thickness"]
        front_length = self.geometry["length"]
        height = self.geometry["height"]
        back_left_position, back_right_position = self.__get_back_vertices()

        plate_vertices = [Vertex(0) for i in range(4)]

        plate_vertices[0] = Vertex(-front_length/2, 0, thickness)
        plate_vertices[1] = Vertex(front_length/2, 0, thickness)
        plate_vertices[2] = Vertex(back_right_position)
        plate_vertices[3] = Vertex(back_left_position)

        plate_vertices = [vertex.create() for vertex in plate_vertices]
        face_to_sweep = make_surface_from_curves(make_loop(plate_vertices, []))
        cmd(f"sweep surface {face_to_sweep.cid} vector 0 1 0 distance {height}")
        plate = get_last_geometry("body")
        plate = self.__make_holes(plate)
        return from_bodies_to_volumes([plate])

    def __make_holes(self, plate: GenericCubitInstance):
        plate_thickness = self.geometry["thickness"]
        hole_radius = self.geometry["hole radius"]

        for row in self.pin_pos:
            for position in row:
                hole_position = Vertex(position.x, position.y, 0)
                hole_to_be = cubit_cmd_check(f"create cylinder radius {hole_radius} height {plate_thickness*3}", "volume")
                cmd(f"{hole_to_be.geometry_type} {hole_to_be.cid} move {str(hole_position)}")
                cmd(f"subtract {hole_to_be.geometry_type} {hole_to_be.cid} from {plate.geometry_type} {plate.cid}")
        return plate

class BZBackplate(Plate):
    def __init__(self, json_object: dict, pin_positions):
        super().__init__("BZ_backplate", json_object, "full", pin_positions)

class FrontRib(ComplexComponent):
    def __init__(self, json_object: dict):
        super().__init__("front_rib", json_object)
    
    def make_geometry(self):
        height = self.geometry["height"]
        length = self.geometry["length"]
        thickness = self.geometry["thickness"]

        structure = cubit_cmd_check(f"create brick x {thickness} y {height} z {length}", "body")
        cmd(f"{structure.geometry_type} {structure.cid} move 0 {height/2} {-length/2}")

        structure, number_of_channels = self.__make_side_channels(structure)
        rib = self.__make_rib_connections(structure, number_of_channels)

        return from_bodies_to_volumes([rib])

    def __make_side_channels(self, structure: GenericCubitInstance):

        structure_height = self.geometry["height"]

        length = self.geometry["thickness"]
        width = self.geometry["side channel width"]
        height = self.geometry["side channel height"]
        gap = self.geometry["side channel gap"]
        z_offset = self.geometry["side channel horizontal offset"]
        y_margin = self.geometry["side channel vertical margin"]

        accessible_height = structure_height - 2*y_margin
        spacing = gap + height
        number_of_channels = (accessible_height // spacing) + 1
        y_margin += (accessible_height - (number_of_channels-1)*spacing)/2

        channel_dims = Vertex(length, height, width)
        structure = self.__tile_channels_vertically(structure, channel_dims, number_of_channels, y_margin, z_offset, spacing)
        
        return structure, number_of_channels

    def __make_rib_connections(self, structure: GenericCubitInstance, number_of_channels: int):
        height = self.geometry["connection height"]
        length = self.geometry["length"] - self.geometry["side channel horizontal offset"]
        connection_dims = Vertex(self.geometry["connection width"], height, length)

        z_offset = self.geometry["side channel horizontal offset"] + self.geometry["side channel width"]
        spacing = self.geometry["side channel gap"] + self.geometry["side channel height"]
        y_margin = (self.geometry["height"] + self.geometry["side channel height"] - (height + (number_of_channels-1)*spacing))/2

        structure = self.__tile_channels_vertically(structure, connection_dims, number_of_channels, y_margin, z_offset, spacing)

        return structure

    def __tile_channels_vertically(self, structure: GenericCubitInstance, channel_dims: Vertex, number_of_channels, y_margin, z_offset, spacing):
        for i in range(number_of_channels):
            hole_to_be = cubit_cmd_check(f"create brick x {channel_dims.x} y {channel_dims.y} z {channel_dims.z}", "volume")
            hole_name = str(hole_to_be)
            cmd(f"{hole_name} move 0 {channel_dims.y/2} {-channel_dims.z/2}")
            cmd(f"{hole_name} move 0 {y_margin + i*spacing} {-z_offset}")
            cmd(f"subtract {hole_name} from {str(structure)}")
        
        return structure