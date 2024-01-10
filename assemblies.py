from generic_classes import *
from components import *
from cubit_functions import from_bodies_to_volumes, get_bodies_and_volumes_from_group, delve
from constants import STANDARD_COMPONENTS

class GenericComponentAssembly:
    '''
    Generic assembly to store components
    '''
    def __init__(self, classname):
        self.classname = classname
        self.components = []

    # These refer to cubit handles
    def get_cubit_instances_from_class(self, class_list: list) -> list:
        '''Get list of cubit instances of specified classnames

        :param classname_list: list of classnames to search in
        :type classname_list: list
        :return: list of cubit handles
        :rtype: list
        '''
        instances_list = []
        for component in self.get_components():
            for component_class in class_list:
                if isinstance(component, component_class):
                    # fetches instances
                    if isinstance(component, GenericCubitInstance):
                        instances_list.append(component.cubitInstance)
                    elif isinstance(component, ComplexComponent):
                        instances_list += component.subcomponents
                    elif isinstance(component, GenericComponentAssembly):
                        # This feels very scuffed
                        instances_list += component.get_cubit_instances_from_class(class_list)
        return instances_list
    
    def get_all_cubit_instances(self) -> list:
        '''get every cubit instance stored in this assembly instance recursively

        :return: list of cubit handles
        :rtype: list
        '''
        instances_list = []
        for component in self.get_components():
            if isinstance(component, GenericCubitInstance):
                instances_list.append(component.cubitInstance)
            elif isinstance(component, ComplexComponent):
                instances_list += [subcomp.cubitInstance for subcomp in component.subcomponents]
            elif isinstance(component, GenericComponentAssembly):
                instances_list += component.get_all_cubit_instances()
        return instances_list

    # These refer to GenericCubitInstance objects
    def get_geometries_from(self, class_list: list) -> list[GenericCubitInstance]:
        '''Get list of geometries under given classnames

        :param classname_list: list of classnames to search under
        :type classname_list: list
        :return: list of GenericCubitInstances
        :rtype: list
        '''
        component_list = []
        for component in self.get_components():
            for component_class in class_list:
                if isinstance(component, component_class):
                    if isinstance(component, GenericCubitInstance):
                        component_list.append(component)
                    elif isinstance(component, ComplexComponent):
                        component_list += component.subcomponents
                    elif isinstance(component, GenericComponentAssembly):
                        component_list += component.get_generic_cubit_instances_from(class_list)
        return component_list
    
    def get_all_geometries(self) -> list[GenericCubitInstance]:
        '''get every geometry stored in this assembly instance recursively

        :return: list of GenericCubitInstances
        :rtype: list
        '''
        instances_list = []
        for component in self.get_components():
            if isinstance(component, GenericCubitInstance):
                instances_list.append(component)
            elif isinstance(component,ComplexComponent):
                instances_list += component.subcomponents 
            elif isinstance(component, GenericComponentAssembly):
                instances_list += component.get_all_geometries()
        return instances_list

    def get_volumes_list(self) -> list[int]:
        volumes_list = from_bodies_to_volumes(self.get_all_generic_cubit_instances)
        return [volume.cid for volume in volumes_list]

    def get_components(self) -> list:
        '''Return all components stored in this assembly at the top-level

        :return: List of all components
        :rtype: list
        '''
        return self.components

    def get_components_of_class(self, class_list: list) -> list:
        '''Find components of given classes recursively

        :param class_list: List of classes to search for
        :type class_list: list
        :return: List of components
        :rtype: list
        '''
        component_list = []
        if type(class_list) != list:
            class_list = [class_list]
        for component in self.get_components():
            for component_class in class_list:
                if isinstance(component, component_class):
                    component_list.append(component)
                if isinstance(component, GenericComponentAssembly):
                    component_list += component.get_components_of_class(class_list)
        return component_list

    def move(self, vector: Vertex):
        for component in self.get_components():
            component.move(vector)

class CreatedComponentAssembly(GenericComponentAssembly):
    '''
    Assembly to handle components created natively. Takes a list of required classnames to set up a specific assembly. 
    Instantiating will fail without at least one component of the given classnames.
    '''
    def __init__(self, classname, component_list: list, required_classnames: list, origin=Vertex(0,0,0)):
        self.classname = classname
        self.origin = origin
        # this defines what components to require in every instance
        self.required_classnames = required_classnames
        self.components = []
        self.component_list = delve(component_list)

        # enforce given component_list based on required_classnames
        self.enforce_structure()
        # store instances
        self.setup_assembly()
        self.move(origin)

    def enforce_structure(self):
        '''Make sure an instance of this class contains the required components. This looks at the classnames specified in the json file'''
        class_list = [i["class"] for i in self.component_list]
        for classes_required in self.required_classnames:
            if classes_required not in class_list:
                # Can change this to a warning, for now it just throws an error
                raise CubismError(f"This assembly must contain: {self.required_classnames}. Currently contains: {class_list}")
    
    def setup_assembly(self):
        '''Add components to attributes according to their class'''
        for component_json_dict in self.component_list:
            self.components.append(json_object_reader(component_json_dict))
    
    def rotate(self, angle, origin: Vertex, axis=Vertex(0,0,1)):
        '''Rotate about a point+axis (IN DEGREES)

        :param angle: Angle to rotate by in degrees
        :type angle: int
        :param origin: centre of rotation
        :type origin: Vertex
        :param axis: axis to rotate about, defaults to Vertex(0,0,1)
        :type axis: Vertex, optional
        '''
        if origin == "origin":
            origin = self.origin
    
        for component in self.get_components():
            if isinstance(component, CreatedComponentAssembly):
                component.rotate(angle, origin, axis)
            elif isinstance(component, ComplexComponent):
                for subcomponent in component.get_subcomponents():
                    cubit.cmd(f"rotate {subcomponent.geometry_type} {subcomponent.cid} about origin {str(origin)} direction {str(axis)} angle {angle}")

class NeutronTestFacility(CreatedComponentAssembly):
    '''
    Assembly class that requires at least one source, blanket, and room.
    Fails if specified morphology is not followed.
    Currently supports inclusive, exclusive, and overlap morphologies.

    On instantiating this performs the following tasks:

    * Ensures the specified morphology is followed
    * Fills rooms with 'air'
    * Checks that all components are inside rooms
    * Checks for any overlaps between components

    '''
    def __init__(self, morphology: str, component_list: list):
        super().__init__("NTF", component_list, NEUTRON_TEST_FACILITY_REQUIREMENTS)
        # this defines what morphology will be enforced later
        self.morphology = morphology
        self.enforce_facility_morphology()
        self.apply_facility_morphology()
        self.validate_rooms_and_fix_air()
        self.change_air_to_volumes()
        self.check_for_overlaps()

    def enforce_facility_morphology(self):
        '''
        Make sure the specified morphology is followed. 
        This works by comparing the volumes of the source and blanket to the volume of their union
        '''

        if self.morphology not in FACILITY_MORPHOLOGIES:
            raise CubismError(f"Morphology not supported by this facility: {self.morphology}")
        
        # Get the net source, blanket, and the union of both
        source_object= unionise(self.get_components_of_class(SourceAssembly))
        blanket_components = []
        for i in self.get_components_of_class(RoomAssembly):
            blanket_components += i.get_components_of_class(BlanketAssembly) 
        blanket_object= unionise(blanket_components)
        union_object= unionise([source_object, blanket_object])

        # get their volumes
        source_volume= source_object.cubitInstance.volume()
        blanket_volume= blanket_object.cubitInstance.volume()
        union_volume= union_object.cubitInstance.volume()

        # cleanup
        source_object.destroy_cubit_instance()
        blanket_object.destroy_cubit_instance()
        union_object.destroy_cubit_instance()

        # different enforcing depending on the morphology specified
        if (self.morphology == "inclusive") & (not (union_volume == blanket_volume)):
            raise CubismError("Source not completely enclosed")
        elif (self.morphology == "exclusive") & (not (union_volume == blanket_volume + source_volume)):
            raise CubismError("Source not completely outside blanket")
        elif (self.morphology == "overlap") & (not (union_volume < blanket_volume + source_volume)):
            raise CubismError("Source and blanket not partially overlapping")
        else:
            print(f"{self.morphology} morphology enforced")

    def apply_facility_morphology(self):
        '''If the morphology is inclusive/overlap, remove the parts of the blanket inside the neutron source'''
        if self.morphology in ["inclusive", "overlap"]:
            # convert everything to volumes in case of stray bodies
            source_volumes = from_bodies_to_volumes(self.get_geometries_from([SourceAssembly, ExternalComponent]))
            blanket_volumes = []
            for room in self.get_components_of_class(RoomAssembly):
                for blanket in room.get_components_of_class(BlanketAssembly):
                    blanket_volumes += from_bodies_to_volumes(blanket.get_all_geometries())
            # if there is an overlap, remove it
            for source_volume in source_volumes:
                for blanket_volume in blanket_volumes:
                    if isinstance(source_volume, GenericCubitInstance) and isinstance(blanket_volume, GenericCubitInstance):
                        if not (cubit.get_overlapping_volumes([source_volume.cid, blanket_volume.cid]) == ()):
                            # i have given up on my python api dreams. we all return to cubit ccl in the end.
                            cubit.cmd(f"remove overlap volume {source_volume.cid} {blanket_volume.cid} modify volume {blanket_volume.cid}")
            print(f"{self.morphology} morphology applied")

    def check_for_overlaps(self):
        volume_ids_list = [i.cid for i in from_bodies_to_volumes(self.get_all_generic_cubit_instances())]
        overlaps = cubit.get_overlapping_volumes(volume_ids_list)
        if overlaps != ():
            raise CubismError(f"Here be overlaps: {overlaps}")

    def validate_rooms_and_fix_air(self):
        '''subtract all non-air geometries from all air geometries. Validate that everything is inside a room'''

        # collect geometries that define the complete space of the facility
        room_bounding_boxes = []
        for room in self.get_components_of_class(RoomAssembly):
            # get all air (it is set up to be overlapping with the surrounding walls at this stage)
            for surrounding_walls in room.get_components_of_class(SurroundingWallsComponent):
                room_bounding_boxes += surrounding_walls.get_air_subcomponents()
            # walls are set up to be subtracted from air on creation so need to add them in manually
            for walls in room.get_components_of_class(WallComponent):
                room_bounding_boxes += walls.get_subcomponents()
        
        # get a union defining the 'bounding boxes' for all rooms, and a union of every geometry in the facility. 
        # as well as the union of those two unions
        room_bounding_box = unionise(room_bounding_boxes)
        all_geometries = unionise(self.get_all_geometries())
        union_object = unionise([room_bounding_box, all_geometries])

        # get volumes
        bounding_volume = room_bounding_box.cubitInstance.volume()
        union_volume = union_object.cubitInstance.volume()

        # cleanup
        room_bounding_box.destroy_cubit_instance()
        union_object.destroy_cubit_instance()

        # if any part of the geometries are sticking out of a room, the volume of their union with the room will be greater than the volume of the room
        if union_volume > bounding_volume:
            raise CubismError("Everything not inside a room!")
        
        # there is probably a better way of doing this
        # if a room is filled with air, subtract the union of all non-air geometries from it
        for surrounding_walls in self.get_components_of_class(SurroundingWallsComponent):
            if surrounding_walls.is_air():
                for air in surrounding_walls.get_air_subcomponents():
                    all_geometries_copy = all_geometries.copy_cubit_instance()
                    cubit.cmd(f'subtract {all_geometries_copy.geometry_type} {all_geometries_copy.cid} from {air.geometry_type} {air.cid}')
        # cleanup
        all_geometries.destroy_cubit_instance()

    # this is just ridiculous. like actually why.
    def change_air_to_volumes(self):
        '''Components referring to air now only contain volumes'''
        for surrounding_walls in self.get_components_of_class(SurroundingWallsComponent):
            surrounding_walls.air_as_volumes()

# replace this at some point
class BlanketAssembly(CreatedComponentAssembly):
    '''Assembly class that requires at least one breeder and structure. Additionally stores coolants separately'''
    def __init__(self, component_list: list):
        super().__init__("Blanket", component_list, BLANKET_REQUIREMENTS)

class RoomAssembly(CreatedComponentAssembly):
    '''Assembly class that requires surrounding walls and a blanket. Fills with air. Can add walls.'''
    def __init__(self, component_list: list):

        # Take out any walls from component list
        json_walls = []
        for json_component in component_list:
            if json_component["class"] == "wall":
                json_walls.append(json_component)
                component_list.remove(json_component)

        # set up rest of components
        super().__init__("Room", component_list, ROOM_REQUIREMENTS)
        self.setup_walls(json_walls)

    def setup_walls(self, json_walls):
        '''Set up walls in surrounding walls. Remove air from walls'''
        for surrounding_walls in self.get_components_of_class(SurroundingWallsComponent):
            for json_wall in json_walls:
                # make wall
                wall_geometry = surrounding_walls.geometry
                wall_material = json_wall["material"] if "material" in json_wall.keys() else surrounding_walls.material
                for wall_key in json_wall["geometry"].keys():
                    wall_geometry["wall " + wall_key] = json_wall["geometry"][wall_key]
                self.components.append(WallComponent(wall_geometry, wall_material))
                # remove air
                for air in surrounding_walls.get_air_subcomponents():
                    temp_wall = WallComponent(wall_geometry, wall_material)
                    for t_w in temp_wall.subcomponents:
                        cubit.cmd(f"subtract {t_w.geometry_type} {t_w.cid} from {air.geometry_type} {air.cid}")

class ExternalComponentAssembly(GenericComponentAssembly):
    '''
    Assembly to store and manage bodies imported from an external file
    requires:
    - external_filepath: path to external file relative to this python file
    - external_groupname: name of group to add external components to
    - manufacturer
    '''
    def __init__(self, external_filepath: str, external_groupname: str, manufacturer: str):
        super().__init__(classname="ExternalAssembly")
        self.group = external_groupname
        self.filepath = external_filepath
        self.manufacturer = manufacturer
        self.import_file()
        self.group_id = self.get_group_id()
        self.add_volumes_and_bodies()

    def import_file(self):
        '''Import file at specified filepath and add to specified group name'''
        # cubit imports bodies instead of volumes. why.

        # import the bodies in a temporary group
        temp_group_name = str(self.group) + "_temp"
        print(f'import "{self.filepath}" heal group "{temp_group_name}"')
        cubit.cmd(f'import "{self.filepath}" heal group "{temp_group_name}"')
        temp_group_id = cubit.get_id_from_name(temp_group_name)

        # convert everything to volumes
        volumes_list = from_bodies_to_volumes(get_bodies_and_volumes_from_group(temp_group_id))
        for volume in volumes_list:
            cubit.cmd(f'group "{self.group}" add {volume.geometry_type} {volume.cid}')
        print(f"volumes imported in group {self.group}")

        # cleanup
        cubit.cmd(f"delete group {temp_group_id}")

    def get_group_id(self):
        '''get ID of group (group needs to exist first)'''
        for (group_name, group_id) in cubit.group_names_ids():
            if group_name == self.group:
                return group_id
        raise CubismError("Can't find group ID?????")
    
    def add_volumes_and_bodies(self):
        '''Add volumes and bodies in group to this assembly as ExternalComponent objects'''
        source_volume_ids = cubit.get_group_volumes(self.group_id)
        for volume_id in source_volume_ids:
            self.components.append(ExternalComponent(volume_id, "volume"))
        source_body_ids = cubit.get_group_bodies(self.group_id)
        for body_id in source_body_ids:
            self.components.append(ExternalComponent(body_id, "body"))

# in case we need to do source-specific actions at some point
class SourceAssembly(ExternalComponentAssembly):
    '''Assembly of external components, created when a json object has class= source'''
    def __init__(self, external_filepath: str, external_groupname: str, manufacturer: str):
        super().__init__(external_filepath, external_groupname, manufacturer)

# more detailed components
class BreederUnitAssembly(CreatedComponentAssembly):
    '''Pin filled with breeder capped by a filter disc. Enclosed in a pressure surrounded by a hexagonal prism of multiplier'''
    def __init__(self, materials_dict: dict, geometry_dict: dict, origin=Vertex(0,0,0)):
        self.components = []
        self.classname = "breeder_unit"
        self.materials = materials_dict
        self.geometry = geometry_dict
        self.origin = origin
        self.setup_assembly()
        self.move(self.origin)
    
    def setup_assembly(self):
        pin_geometry = self.__extract_parameters(["outer length", "inner length", "offset", "bluntness", "inner cladding", "outer cladding", "breeder chamber thickness", "coolant inlet radius"])
        pressure_tube_geometry = self.__extract_parameters({
            "pressure tube outer radius": "outer radius",
            "pressure tube thickness": "thickness",
            "pressure tube length": "length"
        })
        multiplier_geometry = self.__extract_parameters({
            "multiplier length": "length",
            "multiplier side": "side",
            "pressure tube outer radius": "inner radius"
        })
        breeder_geometry = self.__get_breeder_parameters()
        filter_disk_geometry = self.__get_filter_disk_parameters()

        pressure_tube_gap = self.geometry["pressure tube gap"]
        chamber_spacing = breeder_geometry["chamber offset"] + pressure_tube_gap
        filter_disk_spacing = pressure_tube_gap + self.geometry["offset"] + self.geometry["outer length"] - filter_disk_geometry["length"]

        pin = PinComponent(pin_geometry, self.materials["pin"])
        pressure_tube = PressureTubeComponent(pressure_tube_geometry, self.materials["pressure tube"])
        multiplier = MultiplierComponent(multiplier_geometry, self.materials["multiplier"])
        breeder = BreederChamber(breeder_geometry, self.materials["breeder"])
        filter_disk = FilterDiskComponent(filter_disk_geometry, self.materials["filter disk"])

        cubit.move(pin.get_subcomponents()[0].cubitInstance, [pressure_tube_gap, 0, 0])
        cubit.move(breeder.get_subcomponents()[0].cubitInstance, [chamber_spacing, 0, 0])
        cubit.move(filter_disk.get_subcomponents()[0].cubitInstance, [filter_disk_spacing, 0, 0])
        self.components.extend([pin, pressure_tube, multiplier, breeder, filter_disk])
        # align with z-axis properly
        self.rotate(90, Vertex(0, 0, 0), Vertex(0, 1, 0))
        #self.rotate(30, Vertex(0, 0, 0), Vertex(0, 0, 1))
    
    def __extract_parameters(self, parameters):
        out_dict = {}
        if type(parameters) == list:
            for parameter in parameters:
                out_dict[parameter] = self.geometry[parameter]
        elif type(parameters) == dict:
            for fetch_parameter, out_parameter in parameters.items():
                out_dict[out_parameter] = self.geometry[fetch_parameter]
        else:
            raise CubismError(f"parameters type not recognised: {type(parameters)}")
        return out_dict
    
    def __get_breeder_parameters(self):
        geometry = self.geometry
        outer_length = geometry["outer length"]
        #inner_length = geometry["inner length"]
        offset = geometry["offset"]
        coolant_inlet_radius = geometry["coolant inlet radius"]
        inner_cladding = geometry["inner cladding"]
        breeder_chamber_thickness = geometry["breeder chamber thickness"]
        outer_cladding = geometry["outer cladding"]
        filter_disc_thickness = geometry["filter disk thickness"]

        slope_angle = np.arctan((inner_cladding + breeder_chamber_thickness + outer_cladding) / offset)

        parameters = {}
        parameters["bluntness"] = geometry["bluntness"]
        parameters["inner radius"] = coolant_inlet_radius + inner_cladding
        parameters["outer radius"] = coolant_inlet_radius + inner_cladding + breeder_chamber_thickness
        parameters["chamber offset"] = outer_cladding/np.sin(slope_angle) + inner_cladding/np.tan(slope_angle)
        parameters["length"] = offset + outer_length - (filter_disc_thickness + parameters["chamber offset"])
        parameters["offset"] = geometry["offset"] + (outer_cladding*np.tan(slope_angle/2)) - parameters["chamber offset"]

        return parameters

    def __get_filter_disk_parameters(self):
        geometry = self.geometry
        coolant_inlet_radius = geometry["coolant inlet radius"]
        inner_cladding = geometry["inner cladding"]
        breeder_chamber_thickness = geometry["breeder chamber thickness"]

        parameters = self.__extract_parameters({
            "breeder chamber thickness": "thickness",
            "filter disk thickness": "length"
        })
        parameters["outer radius"] = coolant_inlet_radius + inner_cladding + breeder_chamber_thickness

        return parameters

class BlanketShellAssembly(CreatedComponentAssembly):
    '''First wall with tiled breeder units'''
    def __init__(self, component_list: list, geometry: dict, origin=Vertex(0,0,0)):
        self.geometry = geometry
        super().__init__("blanket_shell", component_list, ["first wall", "breeder unit"], origin)
    
    def setup_assembly(self):
        for component in self.component_list:
            if component["class"] == "first wall":
                first_wall_geometry = component["geometry"]
                first_wall_material = component["material"]
            elif component["class"] == "breeder unit":
                breeder_materials = component["materials"]
                breeder_geometry = component["geometry"]
                multiplier_side = breeder_geometry["multiplier side"]
        
        vertical_offset = self.geometry["vertical offset"]
        horizontal_offset = self.geometry["horizontal offset"]
        pin_spacing = self.geometry["pin spacing"]
        inner_width = first_wall_geometry["inner width"]
        length = first_wall_geometry["length"]
        height = first_wall_geometry["height"]
        wall_bluntness = first_wall_geometry["bluntness"]
        wall_thickness = first_wall_geometry["thickness"]

        # 'accessible' for tiling breeder units
        accessible_width = inner_width - 2*(horizontal_offset + wall_bluntness)
        accessible_height = height - 2*vertical_offset
        # hexagonally tiled breeder units are broken up into 'rows' and 'columns'
        # number of pins that will fit in a 'row'
        row_pins = int((accessible_width - 2*multiplier_side) // (pin_spacing * np.cos(np.pi/6))) + 1
        horizontal_start_pos = -(row_pins-1)*pin_spacing*np.cos(np.pi/6) / 2
        # each column 'index' has breeder units at 2 different heights
        columns_indices = int((accessible_height - 2*multiplier_side*np.cos(np.pi/6)) // pin_spacing) + 1
        # number of distinct heights we can place breeder units
        distinct_pin_heights = int((accessible_height - 2*multiplier_side*np.cos(np.pi/6)) // (pin_spacing*np.sin(np.pi/6))) + 1
        centering_vertical_offset = ((accessible_height- 2*multiplier_side*np.cos(np.pi/6)) - (distinct_pin_heights-1)*pin_spacing*np.sin(np.pi/6)) / 2
        vertical_start_pos = height - (vertical_offset + centering_vertical_offset + multiplier_side*np.cos(np.pi/6))

        for j in range(columns_indices):
            pin_pos = Vertex(horizontal_start_pos , vertical_start_pos, length-wall_thickness) + Vertex(0, -pin_spacing*j)
            for i in range(row_pins):
                # stop tiling if we overshoot the number of column pins (each column index corresponds to 2 column pins)
                if (j*2)+1 + (i%2) <= distinct_pin_heights:
                    self.components.append(BreederUnitAssembly(breeder_materials, breeder_geometry, pin_pos))
                pin_pos = pin_pos + Vertex(pin_spacing).rotate(((-1)**(i+1))*np.pi/6)
            
        self.components.append(FirstWallComponent(first_wall_geometry, first_wall_material))

class BlanketRingAssembly(CreatedComponentAssembly):
    '''Makes a ring of blanket shells'''
    def __init__(self, component_list: list, geometry: dict):
        self.geometry = geometry
        super().__init__("blanket_ring", component_list, ["blanket shell"])
    
    def setup_assembly(self):
        blanket_shell, min_radius, blanket_segment, blanket_length, ring_thickness = self.__get_data()
        radius = self.__tweak_radius(blanket_segment, min_radius)
        midpoint_vertices, angle_subtended = self.__get_segment_midpoints(radius, blanket_segment, blanket_length)
        for i in range(len(midpoint_vertices)):
            blanket = BlanketShellAssembly(*blanket_shell, origin=midpoint_vertices[i]+Vertex(0, -blanket_segment/2))
            blanket.rotate(-90, "origin", Vertex(0, 1, 0))
            blanket.rotate(180*(angle_subtended*i)/np.pi, midpoint_vertices[i])
            self.components.append(blanket)
        
    def __tweak_radius(self, blanket_segment, min_radius):
        angle_subtended = 2*np.arcsin(blanket_segment/(2*min_radius))
        if not 2*np.pi % angle_subtended == 0:
            segments_needed = int(2*np.pi // angle_subtended) + 1
            angle_needed = 2*np.pi / segments_needed
            radius = blanket_segment / (2*np.sin(angle_needed/2))
            return radius
        else:
            return min_radius
    
    def __get_data(self):
        geometry = self.geometry
        min_radius = geometry["minimum radius"]
        for component in self.component_list:
            if component["class"] == "blanket shell":
                blanket_shell_geometry = component["geometry"]
                blanket_shell_components = delve(component["components"])
                for subcomponent in blanket_shell_components:
                    if subcomponent["class"] == "first wall":
                        sub_geometry = subcomponent["geometry"]
                        blanket_segment = sub_geometry["height"]
                        blanket_length = sub_geometry["length"]
                        ring_thickness = sub_geometry["inner width"]
        return [blanket_shell_components, blanket_shell_geometry], min_radius, blanket_segment, blanket_length, ring_thickness

    def __get_segment_midpoints(self, radius, blanket_segment, blanket_length):
        angle_subtended = 2*np.arcsin(blanket_segment/(2*radius))
        segments_needed = int(2*np.pi/angle_subtended)
        midpoint_vertex = Vertex(radius*np.cos(angle_subtended/2) + blanket_length)
        midpoint_vertices = [midpoint_vertex.rotate(angle_subtended*i) for i in range(segments_needed)]
        return midpoint_vertices, angle_subtended

def get_all_geometries_from_components(component_list):
    instances = []
    for component in component_list:
        if isinstance(component, GenericCubitInstance):
            instances.append(component)
        elif isinstance(component, ComplexComponent):
            instances += component.subcomponents
        elif isinstance(component, GenericComponentAssembly):
            instances += component.get_all_geometries()
    return instances

# wrapper for cubit.union
def unionise(component_list: list):
    '''creates a union of all instances in given components.

    :param component_list: list of components
    :type component_list: list
    :return: Geometry of union
    :rtype: GenericCubitInstance
    '''
    if len(component_list) == 0:
        raise CubismError("This is an empty list you have given me")

    # get all GenericCubitInstances from components
    instances_to_union = get_all_geometries_from_components(component_list)
    
    # convert to bodies :(
    instances_to_union = from_everything_to_bodies(instances_to_union)

    # check whether a union is possible
    if len(instances_to_union) == 0:
        raise CubismError("Could not find any instances")
    elif len(instances_to_union) == 1:
        return instances_to_union[0].copy_cubit_instance()

    # get cubit handles
    instances_to_union = [i.cubitInstance for i in instances_to_union]
    
    # need old and new volumes to check what the union creates
    old_volumes = cubit.get_entities("volume")
    old_bodies = cubit.get_entities("body")
    cubit.unite(instances_to_union, keep_old_in=True)
    new_volumes = cubit.get_entities("volume")
    new_bodies = cubit.get_entities("body")
    if len(new_bodies) == len(old_bodies) + 1:
        return GenericCubitInstance(cubit.get_last_id("body"), "body")
    elif len(new_volumes) == len(old_volumes) + 1:
        return GenericCubitInstance(cubit.get_last_id("volume"), "volume")
    else:
        raise CubismError("Something unknowable was created in this union. Or worse, a surface.")

def get_constructor_from_name(classname: str):
    '''Get component constructor using it's json class name

    :param classname: json class name
    :type classname: str
    :return: constructor for component
    '''
    return globals()[CLASS_MAPPING[classname]]

# map classnames to instances - there should be a better way to do this?
def json_object_reader(json_object: dict):
    '''parse json representation of a component and set up class instance

    :param json_object: json representation of a component. 
    :type json_object: dict
    :return: Instance of a native class, chosen according to the 'class' value provided
    :rtype: various native classes
    '''

    constructor = get_constructor_from_name(json_object["class"])
    if json_object["class"] == "complex":
        return constructor(
            geometry = json_object["geometry"],
            classname = "complex",
            material = json_object["material"]
        )
    elif json_object["class"] == "external":
        return constructor(
            external_filepath= json_object["filepath"],
            external_groupname= json_object["group"],
            manufacturer = json_object["manufacturer"],
        )
    elif json_object["class"] == "source":
        return constructor(
            external_filepath= json_object["filepath"],
            external_groupname= json_object["group"],
            manufacturer = json_object["manufacturer"],
        )
    elif json_object["class"] == "neutron test facility":
        return constructor(
            morphology= json_object["morphology"],
            component_list= list(json_object["components"])
        )
    elif json_object["class"] == "blanket":
        return constructor(
            component_list= json_object["components"]
        )
    elif json_object["class"] == "room":
        return constructor(
            component_list= json_object["components"]
        )
    elif json_object["class"] == "surrounding_walls":
        return constructor(
            geometry= json_object["geometry"],
            material= json_object["material"],
            air= json_object["air"]
        )
    elif json_object["class"] in STANDARD_COMPONENTS:
        return constructor(
            geometry= json_object["geometry"],
            material= json_object["material"]
        )
    elif json_object["class"] == "breeder unit":
        return constructor(
            materials_dict = json_object["materials"],
            geometry_dict = json_object["geometry"]
        )
    elif json_object["class"] == "blanket shell":
        return constructor(
            geometry= json_object["geometry"],
            component_list= json_object["components"]
        )
    elif json_object["class"] == "blanket ring":
        return constructor(
            geometry= json_object["geometry"],
            component_list= json_object["components"]
        )
