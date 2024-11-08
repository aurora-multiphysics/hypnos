'''
assemblies.py
author(s): Sid Mungale

Assembly classes and construct function.
Assembly classes organise the arrangement of their children component classes,
for example a Pin would consist of Cladding, Breeder, Coolant, etc. components.

(c) Copyright UKAEA 2024
'''

from blobmaker.generic_classes import CubismError, CubitInstance, cmd, cubit
from blobmaker.components import (
    ComponentBase,
    ExternalComponent,
    SimpleComponent,
    SurroundingWallsComponent,
    AirComponent,
    BreederComponent,
    StructureComponent,
    WallComponent,
    CladdingComponent,
    PinCoolant,
    PressureTubeComponent,
    FilterLidComponent,
    PurgeGasComponent,
    FilterDiskComponent,
    MultiplierComponent,
    PinBreeder,
    FirstWallComponent,
    BZBackplate,
    PurgeGasPlate,
    FrontRib,
    BackRib,
    CoolantOutletPlenum,
    SeparatorPlate,
    FWBackplate
)
from blobmaker.cubit_functions import to_volumes, get_entities_from_group
from blobmaker.geometry import Vertex, arctan
from blobmaker.cubit_functions import to_bodies
from blobmaker.constants import (
    CLASS_MAPPING,
    NEUTRON_TEST_FACILITY_REQUIREMENTS,
    ROOM_REQUIREMENTS,
    BLANKET_REQUIREMENTS,
    BLANKET_SHELL_REQUIREMENTS,
    FACILITY_MORPHOLOGIES,
    HCPB_BLANKET_REQUIREMENTS
)
import numpy as np


class GenericComponentAssembly(ComponentBase):
    '''
    Generic assembly to store components
    '''
    def __init__(self, classname, json_object):
        super().__init__(classname, json_object)
        self.components = []

    # 'geometries' refer to CubitInstance objects
    def get_geometries_from(self, class_list: list[str]) -> list[CubitInstance]:
        '''Get list of geometries with given classnames

        Parameters
        ----------
        class_list : list[str]
            list of classnames

        Returns
        -------
        list[CubitInstance]
            list of geometries
        '''
        component_list = []
        for component in self.get_components():
            for component_class in class_list:
                if isinstance(component, component_class):
                    if isinstance(component, CubitInstance):
                        component_list.append(component)
                    elif isinstance(component, SimpleComponent):
                        component_list += component.subcomponents
                    elif isinstance(component, GenericComponentAssembly):
                        component_list += component.get_geometries_from(class_list)
        return component_list

    def find_parent_component(self, geometry: CubitInstance):
        '''If this assembly contains given geometry, return owning component.
        Else return None.

        Parameters
        ----------
        geometry : CubitInstance
            Child geometry

        Returns
        -------
        SimpleComponent | None
            Parent component | None
        '''
        for component in self.get_components():
            if isinstance(component, SimpleComponent):
                for component_geometry in component.get_geometries():
                    if isinstance(component_geometry, CubitInstance):
                        if str(geometry) == str(component_geometry):
                            return component
            elif isinstance(component, GenericComponentAssembly):
                found_component = component.find_parent_component(geometry)
                if found_component:
                    return found_component
        return None

    def get_geometries(self):
        instances_list = []
        for component in self.get_components():
            if isinstance(component, CubitInstance):
                instances_list.append(component)
            elif isinstance(component, ComponentBase):
                instances_list.extend(component.get_geometries())
        return instances_list

    def get_volumes_list(self) -> list[int]:
        volumes_list = to_volumes(self.get_all_geometries())
        return [volume.cid for volume in volumes_list]

    def get_components(self) -> list:
        '''Return components stored in this assembly at the top-level,
        i.e. SimpleComponents and GenericComponentAssemblys, if any.

        Returns
        -------
        list
            list of components
        '''
        return self.components

    def get_all_components(self) -> list[SimpleComponent]:
        '''Return all simple components stored in this assembly recursively

        Returns
        -------
        list[SimpleComponent]
            list of simple components
        '''
        instances_list = []
        for component in self.get_components():
            if isinstance(component, SimpleComponent):
                instances_list.append(component)
            elif isinstance(component, GenericComponentAssembly):
                instances_list.extend(component.get_all_components())
        return instances_list

    def get_components_of_class(self, classes: list) -> list:
        '''Find components of with given classnames.
        Searches through assemblies recursively.

        Parameters
        ----------
        classes : list
            list of component classes

        Returns
        -------
        list
            list of components
        '''
        component_list = []
        if type(classes) is not list:
            classes = [classes]
        for component in self.get_components():
            for component_class in classes:
                if isinstance(component, component_class):
                    component_list.append(component)
                elif isinstance(component, GenericComponentAssembly):
                    component_list += component.get_components_of_class(classes)
        return component_list

    def set_mesh_size(self, component_classes: list, size: int):
        component_classes = [globals()[CLASS_MAPPING[classname]] for classname in component_classes]
        components = self.get_components_of_class(component_classes)
        for component in components:
            if isinstance(component, SimpleComponent):
                component.set_mesh_size(size)
            elif isinstance(component, GenericComponentAssembly):
                component.set_mesh_size(component_classes, size)


class CreatedComponentAssembly(GenericComponentAssembly):
    '''
    Assembly to handle components created natively. Takes a list of
    required classnames to set up a specific assembly. Instantiating
    will fail without at least one component of the given classnames.
    '''

    def __init__(self, classname, required_classnames: list, json_object: dict):
        self.required_classnames = required_classnames
        if "components" in json_object.keys():
            if type(json_object["components"]) is dict:
                self.component_list = json_object["components"].values()
            else:
                self.component_list = json_object["components"]
        else:
            self.component_list = []
        super().__init__(classname, json_object)
        # enforce given component_list based on required_classnames
        self.enforce_structure()
        self.setup_assembly()
        self.move(self.origin)

    def check_for_overlaps(self):
        '''Raise an error if any overlaps exist between children volumes
        '''
        volume_ids_list = [i.cid for i in to_volumes(self.get_all_geometries())]
        overlaps = cubit.get_overlapping_volumes(volume_ids_list)
        if overlaps != ():
            overlapping_components = [self.find_parent_component(CubitInstance(overlap_vol_id, "volume")) for overlap_vol_id in overlaps]
            overlapping_components = {comp.classname for comp in overlapping_components if comp}
            raise CubismError(f"The following volumes have overlaps: {overlaps}. These components have overlaps: {overlapping_components}")

    def enforce_structure(self):
        '''Make sure an instance of this class contains the required components.
        This looks at the classnames specified in the json file'''
        class_list = [i["class"] for i in self.component_list]
        for classes_required in self.required_classnames:
            if classes_required not in class_list:
                # Can change this to a warning, for now it just throws an error
                raise CubismError(f"This assembly must contain: {self.required_classnames}. Currently contains: {class_list}")

    def setup_assembly(self):
        '''Instantiate components in cubit'''
        for component_json_dict in self.component_list:
            self.components.append(construct(component_json_dict))

    def rotate(self, angle: float, origin: Vertex = Vertex(0, 0, 0), axis: Vertex = Vertex(0, 0, 1)):
        '''Rotate geometries about a given axis

        Parameters
        ----------
        angle : float
            Angle to rotate by IN DEGREES
        origin : Vertex
            Point to rotate about, by default 0, 0, 0
        axis : Vertex, optional
            axis to rotate about, by default z-axis
        '''
        if origin == "origin":
            origin = self.origin

        for component in self.get_components():
            if isinstance(component, CreatedComponentAssembly):
                component.rotate(angle, origin, axis)
            elif isinstance(component, SimpleComponent):
                for subcomponent in component.get_geometries():
                    cmd(f"rotate {subcomponent.geometry_type} {subcomponent.cid} about origin {str(origin)} direction {str(axis)} angle {angle}")

    def check_sanity(self):
        '''Check whether geometrical parameters are physical on the
        assembly level.
        '''
        pass


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
    def __init__(self, json_object):
        super().__init__("NTF", NEUTRON_TEST_FACILITY_REQUIREMENTS, json_object)
        # this defines what morphology will be enforced later
        self.morphology = json_object["morphology"]
        self.enforce_facility_morphology()
        self.apply_facility_morphology()
        self.validate_rooms_and_fix_air()
        self.change_air_to_volumes()
        self.check_for_overlaps()

    def enforce_facility_morphology(self):
        '''
        Make sure the specified morphology is followed.
        This works by comparing the volumes of the source and blanket to the
        volume of their union
        '''

        if self.morphology not in FACILITY_MORPHOLOGIES:
            raise CubismError(f"Morphology not supported by this facility: {self.morphology}")

        # Get the net source, blanket, and the union of both
        source_object = unionise(self.get_components_of_class(SourceAssembly))
        blanket_components = []
        for i in self.get_components_of_class(RoomAssembly):
            blanket_components += i.get_components_of_class(BlanketAssembly) 
        blanket_object = unionise(blanket_components)
        union_object = unionise([source_object, blanket_object])

        # get their volumes
        source_volume = source_object.handle.volume()
        blanket_volume = blanket_object.handle.volume()
        union_volume = union_object.handle.volume()

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
        '''If the morphology is inclusive/overlap,
        remove the parts of the blanket inside the neutron source'''
        if self.morphology in ["inclusive", "overlap"]:
            # convert everything to volumes in case of stray bodies
            source_volumes = to_volumes(self.get_geometries_from([SourceAssembly, ExternalComponent]))
            blanket_volumes = []
            for room in self.get_components_of_class(RoomAssembly):
                for blanket in room.get_components_of_class(BlanketAssembly):
                    blanket_volumes += to_volumes(blanket.get_all_geometries())
            # if there is an overlap, remove it
            for source_volume in source_volumes:
                for blanket_volume in blanket_volumes:
                    if isinstance(source_volume, CubitInstance) and isinstance(blanket_volume, CubitInstance):
                        if not (cubit.get_overlapping_volumes([source_volume.cid, blanket_volume.cid]) == ()):
                            # i have given up on my python api dreams. we all return to cubit ccl in the end.
                            cmd(f"remove overlap volume {source_volume.cid} {blanket_volume.cid} modify volume {blanket_volume.cid}")
            print(f"{self.morphology} morphology applied")

    def validate_rooms_and_fix_air(self):
        '''Subtract all non-air geometries from all air geometries. 
        Validate that everything is inside a room'''

        # collect geometries that define the complete space of the facility
        room_bounding_boxes = []
        for room in self.get_components_of_class(RoomAssembly):
            # get all air (it is set up to be overlapping with the surrounding walls at this stage)
            for surrounding_walls in room.get_components_of_class(SurroundingWallsComponent):
                room_bounding_boxes += surrounding_walls.get_air_subcomponents()
            # walls are set up to be subtracted from air on creation so need to add them in manually
            for walls in room.get_components_of_class(WallComponent):
                room_bounding_boxes += walls.get_geometries()

        # get a union defining the 'bounding boxes' for all rooms,
        # and a union of every geometry in the facility.
        # as well as the union of those two unions
        room_bounding_box = unionise(room_bounding_boxes)
        all_geometries = unionise(self.get_all_geometries())
        union_object = unionise([room_bounding_box, all_geometries])

        # get volumes
        bounding_volume = room_bounding_box.handle.volume()
        union_volume = union_object.handle.volume()

        # cleanup
        room_bounding_box.destroy_cubit_instance()
        union_object.destroy_cubit_instance()

        # if any part of the geometries are sticking out of a room,
        # the volume of their union with the room will be greater
        # than the volume of the room
        if union_volume > bounding_volume:
            raise CubismError("Everything not inside a room!")

        # there is probably a better way of doing this
        # if a room is filled with air, subtract the union of all
        # non-air geometries from it
        for surrounding_walls in self.get_components_of_class(SurroundingWallsComponent):
            if surrounding_walls.is_air():
                for air in surrounding_walls.get_air_subcomponents():
                    all_geometries_copy = all_geometries.copy()
                    cmd(f'subtract {all_geometries_copy.geometry_type} {all_geometries_copy.cid} from {air.geometry_type} {air.cid}')
        # cleanup
        all_geometries.destroy_cubit_instance()

    # this is just ridiculous. like actually why.
    def change_air_to_volumes(self):
        '''Components referring to air now only contain volumes'''
        for surrounding_walls in self.get_components_of_class(SurroundingWallsComponent):
            surrounding_walls.air_as_volumes()


# replace this at some point
class BlanketAssembly(CreatedComponentAssembly):
    '''Assembly class that requires at least one breeder and structure.
    Additionally stores coolants separately'''
    def __init__(self, json_object: dict):
        super().__init__("Blanket", BLANKET_REQUIREMENTS, json_object)


class RoomAssembly(CreatedComponentAssembly):
    '''Assembly class that requires surrounding walls and a blanket.
    Fills with air. Can add walls.'''
    def __init__(self, json_object):
        component_list = list(json_object["components"].values())

        # Take out any walls from component list
        json_walls = []
        for json_component in component_list:
            if json_component["class"] == "wall":
                json_walls.append(json_component)
                component_list.remove(json_component)
        json_object["components"] = component_list

        # set up rest of components
        super().__init__("Room", ROOM_REQUIREMENTS, json_object)
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
                self.components.append(WallComponent({"geometry": wall_geometry, "material": wall_material}))
                # remove air
                for air in surrounding_walls.get_air_subcomponents():
                    temp_wall = WallComponent({"geometry": wall_geometry, "material": wall_material})
                    for t_w in temp_wall.get_geometries():
                        cmd(f"subtract {t_w.geometry_type} {t_w.cid} from {air.geometry_type} {air.cid}")


class ExternalComponentAssembly(GenericComponentAssembly):
    '''
    Assembly to store and manage bodies imported from an external file
    requires:
    - external_filepath: path to external file relative to this python file
    - external_groupname: name of group to add external components to
    - manufacturer
    '''
    def __init__(self, json_object: dict):
        super().__init__(classname="ExternalAssembly")
        self.group = json_object["group"]
        self.filepath = json_object["filepath"]
        self.manufacturer = json_object["manufacturer"]
        self.import_file()
        self.group_id = self.get_group_id()
        self.add_volumes_and_bodies()

    def import_file(self):
        '''Import file at specified filepath and add to specified group name'''
        # cubit imports bodies instead of volumes. why.

        # import the bodies in a temporary group
        temp_group_name = str(self.group) + "_temp"
        print(f'import "{self.filepath}" heal group "{temp_group_name}"')
        cmd(f'import "{self.filepath}" heal group "{temp_group_name}"')
        temp_group_id = cubit.get_id_from_name(temp_group_name)

        # convert everything to volumes
        volumes_list = to_volumes([CubitInstance(cid, "body") for cid in get_entities_from_group(temp_group_id, "body")])
        for volume in volumes_list:
            cmd(f'group "{self.group}" add {volume.geometry_type} {volume.cid}')
        print(f"volumes imported in group {self.group}")

        # cleanup
        cmd(f"delete group {temp_group_id}")

    def get_group_id(self):
        '''Get ID of group (group needs to exist first)'''
        for (group_name, group_id) in cubit.group_names_ids():
            if group_name == self.group:
                return group_id
        raise CubismError("Can't find group ID?????")

    def add_volumes_and_bodies(self):
        '''Add volumes and bodies in group to this assembly as
        ExternalComponent objects'''
        source_volume_ids = cubit.get_group_volumes(self.group_id)
        for volume_id in source_volume_ids:
            self.components.append(ExternalComponent(volume_id, "volume"))
        source_body_ids = cubit.get_group_bodies(self.group_id)
        for body_id in source_body_ids:
            self.components.append(ExternalComponent(body_id, "body"))


# in case we need to do source-specific actions
class SourceAssembly(ExternalComponentAssembly):
    '''Assembly of external components,
    created when a json object has class= source'''
    def __init__(self, json_object: dict):
        super().__init__(json_object)


# more detailed components
class PinAssembly(CreatedComponentAssembly):
    '''Cladding filled with breeder capped by a filter disc.
    Enclosed in a pressure tube surrounded by a hexagonal prism of multiplier'''
    def __init__(self, json_object: dict):
        self.components = []
        super().__init__("pin", [], json_object)

    def check_sanity(self):
        cladding_radius = self.geometry["coolant inlet radius"] + self.geometry["inner cladding"] + self.geometry["breeder chamber thickness"] + self.geometry["outer cladding"]
        if self.geometry["pressure tube outer radius"] - self.geometry["pressure tube thickness"] < cladding_radius:
            raise ValueError("cladding radius larger than pressure tube radius")

    def setup_assembly(self):
        cladding_json = self.__get_cladding_parameters()
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
        breeder_json = self.__get_breeder_parameters()
        filter_disk_json = self.__get_filter_disk_parameters()
        filter_lid_json = self.__get_filter_lid_parameters()
        coolant_json = self.__get_coolant_parameters()
        purge_gas_json = self.__get_purge_gas_parameters()

        cladding = CladdingComponent(cladding_json)
        pressure_tube = PressureTubeComponent(self.__jsonify(pressure_tube_geometry, "pressure tube", 0))
        multiplier = MultiplierComponent(self.__jsonify(multiplier_geometry, "multiplier", 0))
        breeder = PinBreeder(breeder_json)
        filter_disk = FilterDiskComponent(filter_disk_json)
        filter_lid = FilterLidComponent(filter_lid_json)
        coolant = PinCoolant(coolant_json)
        purge_gas = PurgeGasComponent(purge_gas_json)

        self.components.extend([cladding, pressure_tube, multiplier, breeder, filter_disk, filter_lid, coolant, purge_gas])
        # align with z-axis properly
        self.rotate(90, Vertex(0, 0, 0), Vertex(0, 1, 0))

    def __extract_parameters(self, parameters: list | dict):
        out_dict = {}
        if type(parameters) is list:
            for parameter in parameters:
                out_dict[parameter] = self.geometry[parameter]
        elif type(parameters) is dict:
            for fetch_parameter, out_parameter in parameters.items():
                out_dict[out_parameter] = self.geometry[fetch_parameter]
        else:
            raise CubismError(f"parameters type not recognised: {type(parameters)}")
        return out_dict

    def __get_cladding_parameters(self):
        parameters = self.__extract_parameters(["outer length", "inner length", "offset", "bluntness", "inner cladding", "outer cladding", "breeder chamber thickness", "coolant inlet radius", "purge duct thickness", "purge duct cladding", "purge duct offset", "filter disk thickness"])
        parameters["distance to step"] = self.geometry["filter lid length"] + self.geometry["filter disk thickness"] + self.geometry["inner length"] - (self.geometry["offset"] + self.geometry["outer length"])
        parameters["distance to disk"] = parameters["distance to step"] - self.geometry["filter lid length"]
        start_x = self.geometry["pressure tube gap"] + self.geometry["pressure tube thickness"]

        return self.__jsonify(parameters, "cladding", start_x)

    def __get_breeder_parameters(self):
        geometry = self.geometry
        outer_length = geometry["outer length"]
        offset = geometry["offset"]
        coolant_inlet_radius = geometry["coolant inlet radius"]
        inner_cladding = geometry["inner cladding"]
        breeder_chamber_thickness = geometry["breeder chamber thickness"]
        outer_cladding = geometry["outer cladding"]
        filter_disc_thickness = geometry["filter disk thickness"]

        slope_angle = np.arctan((inner_cladding + breeder_chamber_thickness + outer_cladding) / offset)

        parameters = self.__extract_parameters(["bluntness"])
        parameters["inner radius"] = coolant_inlet_radius + inner_cladding
        parameters["outer radius"] = coolant_inlet_radius + inner_cladding + breeder_chamber_thickness
        parameters["chamber offset"] = outer_cladding/np.sin(slope_angle) + inner_cladding/np.tan(slope_angle)
        parameters["length"] = offset + outer_length - (filter_disc_thickness + parameters["chamber offset"])
        parameters["offset"] = geometry["offset"] + (outer_cladding*np.tan(slope_angle/2)) - parameters["chamber offset"]

        start_x = parameters["chamber offset"] + geometry["pressure tube gap"] + geometry["pressure tube thickness"]

        return self.__jsonify(parameters, "breeder", start_x)

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
        start_x = geometry["pressure tube gap"] + geometry["pressure tube thickness"] + geometry["offset"] + geometry["outer length"] - parameters["length"]

        return self.__jsonify(parameters, "filter disk", start_x)

    def __get_filter_lid_parameters(self):
        parameters = self.__extract_parameters({"purge duct cladding": "thickness", 
                                                "filter lid length": "length"})
        parameters["outer radius"] = self.geometry["coolant inlet radius"] + self.geometry["inner cladding"]

        start_x = self.geometry["pressure tube gap"] + self.geometry["pressure tube thickness"]
        start_x = start_x + self.geometry["outer length"] + self.geometry["offset"] - (self.geometry["filter disk thickness"] + self.geometry["filter lid length"])

        return self.__jsonify(parameters, "filter lid", start_x)

    def __get_purge_gas_parameters(self):
        parameters = self.__extract_parameters({"purge duct thickness": "thickness"})
        parameters["outer radius"] = self.geometry["coolant inlet radius"] + self.geometry["inner cladding"] - self.geometry["purge duct cladding"]
        added_extension = self.geometry["inner length"] - (self.geometry["outer length"] + self.geometry["offset"] + self.geometry["purge duct offset"])
        parameters["length"] = self.geometry["filter lid length"] + self.geometry["filter disk thickness"] + added_extension

        start_x = self.geometry["pressure tube gap"] + self.geometry["pressure tube thickness"]
        start_x = start_x + self.geometry["outer length"] + self.geometry["offset"] - (self.geometry["filter disk thickness"] + self.geometry["filter lid length"])

        return self.__jsonify(parameters, "purge gas", start_x)

    def __get_coolant_parameters(self):
        geometry = self.geometry
        pressure_tube_gap = geometry["pressure tube gap"]
        pressure_tube_thickness = geometry["pressure tube thickness"]
        pressure_tube_length = geometry["pressure tube length"]
        pressure_tube_outer_radius = geometry["pressure tube outer radius"]

        parameters = self.__extract_parameters(["coolant inlet radius", "inner length", "offset", "bluntness"])
        parameters["pressure tube length"] = pressure_tube_length - pressure_tube_thickness
        parameters["pressure tube gap"] = pressure_tube_gap
        parameters["pressure tube radius"] = pressure_tube_outer_radius - pressure_tube_thickness
        parameters["cladding thickness"] = geometry["inner cladding"] + geometry["breeder chamber thickness"] + geometry["outer cladding"]

        return self.__jsonify(parameters, "coolant", pressure_tube_thickness)

    def __jsonify(self, geometry: dict, material: str, start_x: int):
        '''Create dictionary with geometry, material, and origin keys.

        :param geometry: Json dictionary of geometrical parameters
        :type geometry: dict
        :param material: Name of component
        :type material: str
        :param start_x: x coordinate of component origin
        :type start_x: int
        :return: dictionary in the input json style
        :rtype: dict
        '''
        try:
            material_obj = self.material[material.lower()]
        except KeyError:
            raise CubismError(f"Component {self.classname} should contain material of {material}")
        return {"geometry": geometry, "material": material_obj, "origin": Vertex(start_x)}


class BlanketShellAssembly(CreatedComponentAssembly):
    '''First wall with tiled breeder units'''
    def __init__(self, json_object):
        self.geometry = json_object["geometry"]
        super().__init__("blanket_shell", BLANKET_SHELL_REQUIREMENTS, json_object)

    def setup_assembly(self):
        for component in self.component_list:
            if component["class"] == "first_wall":
                first_wall_object = component
                first_wall_geometry = first_wall_object["geometry"]
            elif component["class"] == "pin":
                breeder_materials = component["material"]
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
                    self.components.append(PinAssembly({"material":breeder_materials, "geometry":breeder_geometry, "origin":pin_pos}))
                pin_pos = pin_pos + Vertex(pin_spacing).rotate(((-1)**(i+1))*np.pi/6)

        self.components.append(FirstWallComponent(first_wall_object))


class BlanketRingAssembly(CreatedComponentAssembly):
    '''Make a ring of blanket shells'''
    def __init__(self, json_object: dict):
        self.geometry = json_object["geometry"]
        super().__init__("blanket_ring", ["blanket shell"], json_object)

    def setup_assembly(self):
        blanket_shell, min_radius, blanket_segment, blanket_length, ring_thickness = self.__get_data()
        radius = self.__tweak_radius(blanket_segment, min_radius)
        midpoint_vertices, angle_subtended = self.__get_segment_midpoints(radius, blanket_segment, blanket_length)
        for i in range(len(midpoint_vertices)):
            blanket_shell["origin"] = midpoint_vertices[i]+Vertex(0, -blanket_segment/2)
            blanket = BlanketShellAssembly(blanket_shell)
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
        blanket_shell = {}
        for component in self.component_list:
            if component["class"] == "blanket shell":
                blanket_shell["geometry"] = component["geometry"]
                blanket_shell["components"] = component["components"]
                for subcomponent in blanket_shell["components"]:
                    if subcomponent["class"] == "first wall":
                        sub_geometry = subcomponent["geometry"]
                        blanket_segment = sub_geometry["height"]
                        blanket_length = sub_geometry["length"]
                        ring_thickness = sub_geometry["inner width"]
        return blanket_shell, min_radius, blanket_segment, blanket_length, ring_thickness

    def __get_segment_midpoints(self, radius, blanket_segment, blanket_length):
        angle_subtended = 2*np.arcsin(blanket_segment/(2*radius))
        segments_needed = int(2*np.pi/angle_subtended)
        midpoint_vertex = Vertex(radius*np.cos(angle_subtended/2) + blanket_length)
        midpoint_vertices = [midpoint_vertex.rotate(angle_subtended*i) for i in range(segments_needed)]
        return midpoint_vertices, angle_subtended


class HCPBBlanket(CreatedComponentAssembly):
    '''Mockup of a HCPB-style breeder blanket
    '''
    def __init__(self, json_object: dict):
        super().__init__("HCPB_blanket", HCPB_BLANKET_REQUIREMENTS, json_object)
        # self.check_for_overlaps()

    def check_sanity(self):
        self.__add_component_attributes()
        bu_geometry = self.breeder_geometry
        distance_to_sep_plate = self.first_wall_geometry["thickness"] + bu_geometry["pressure tube gap"] + bu_geometry["pressure tube thickness"] + bu_geometry["inner length"] + self.geometry["coolant outlet plenum gap"] + self.cop_geometry["length"] + self.geometry["separator plate gap"] + self.geometry["separator plate thickness"]
        if self.first_wall_geometry["length"] - distance_to_sep_plate < self.geometry["FW backplate thickness"]:
            raise ValueError("First wall length too short")

        row_pins, horizontal_start_pos = self.__get_pin_start_params()
        for pin_number in self.geometry["front rib positions"]:
            if pin_number > row_pins:
                raise ValueError(f"Specified parameters only tile {row_pins} pins in a row on the first wall, but trying to place front rib after pin number {pin_number}")

        first_wall_slope_angle = arctan(self.first_wall_geometry["length"], (self.first_wall_geometry["outer width"] - self.first_wall_geometry["inner width"])/2)
        distance_to_pin_centre = self.first_wall_geometry["inner width"]/2 - (np.abs(horizontal_start_pos) - self.first_wall_geometry["sidewall thickness"]/np.sin(first_wall_slope_angle))
        distance_to_multiplier = distance_to_pin_centre - bu_geometry["multiplier side"]
        distance_to_pin_inner = distance_to_pin_centre - (bu_geometry["coolant inlet radius"] + bu_geometry["inner cladding"])
        distance_to_pin_outer = distance_to_pin_inner - (bu_geometry["breeder chamber thickness"] + bu_geometry["outer cladding"])
        # this isnt very accurate, treating coolant outlet plenum as if it has a rectangular hitbox
        distance_to_cop = (self.first_wall_geometry["inner width"] - self.cop_geometry["width"]) / 2

        multiplier_extent = bu_geometry["multiplier length"] + self.first_wall_geometry["thickness"]
        pin_outer_extent = self.first_wall_geometry["thickness"] + bu_geometry["pressure tube thickness"] + bu_geometry["pressure tube gap"] + bu_geometry["outer length"] + bu_geometry["offset"]
        pin_inner_extent = self.first_wall_geometry["thickness"] + bu_geometry["pressure tube thickness"] + bu_geometry["pressure tube gap"] + bu_geometry["inner length"]
        cop_extent = pin_inner_extent + self.geometry["coolant outlet plenum gap"] + self.cop_geometry["length"]

        self.check_slope(distance_to_multiplier, multiplier_extent, "First wall collides with multiplier!")
        self.check_slope(distance_to_pin_outer, pin_outer_extent, "First wall collides with pin!")
        self.check_slope(distance_to_pin_inner, pin_inner_extent, "First wall collides with pin!")
        self.check_slope(distance_to_cop, cop_extent, "First wall collides with coolant outlet plenum!")

        if not self.geometry["coolant outlet plenum gap"] + self.cop_geometry["thickness"] < self.back_ribs_geometry["side channel horizontal offset"] < self.geometry["coolant outlet plenum gap"] + self.cop_geometry["length"] - (self.cop_geometry["thickness"] + self.back_ribs_geometry["side channel width"]):
            raise ValueError("Back rib side channels don't empty out into coolant outlet plenum")

        rib_positions = [rib_pos.x for rib_pos in self.__get_rib_positions(0)]
        if rib_positions[0] - self.back_ribs_geometry["thickness"]/2 <= -self.cop_geometry["width"]/2 or rib_positions[-1] + self.back_ribs_geometry["thickness"]/2 >= self.cop_geometry["width"]/2:
            raise ValueError("Coolant outlet plenum not wide enough to encapsulate back ribs")

        if self.front_ribs_geometry["side channel horizontal offset"] + self.front_ribs_geometry["side channel width"] > bu_geometry["pressure tube thickness"] + bu_geometry["pressure tube gap"] + bu_geometry["offset"] + bu_geometry["outer length"] - bu_geometry["pressure tube length"]:
            raise ValueError("Front rib side channel not within coolant inlet manifold")

        BZ_backplate_thickness = bu_geometry["pressure tube length"] - bu_geometry["multiplier length"]
        if self.geometry["PG front plate thickness"] >= pin_outer_extent - (multiplier_extent + BZ_backplate_thickness):
            raise ValueError("PG front plate too thick - overlapping/touching BZ backplate")

        if self.geometry["PG mid plate gap"] >= (pin_inner_extent - pin_outer_extent):
            raise ValueError("PG mid plate touching/ out of bounds of front and back plates")

        if self.geometry["PG mid plate thickness"] >= (pin_inner_extent - pin_outer_extent) - (self.geometry["PG back plate thickness"] + self.geometry["PG mid plate gap"]):
            raise ValueError("PG mid plate overlapping/touching backplate")

        FW_backplate_distance_from_FW = self.first_wall_geometry["length"] - self.geometry["FW backplate thickness"]
        backplate_extent = self.__get_plate_length_and_ext(FW_backplate_distance_from_FW, 0)[0]/2
        if np.abs(rib_positions[0]) + self.back_ribs_geometry["thickness"]/2 > backplate_extent:
            raise ValueError("Left side of back rib too thick - overlapping with first wall")
        elif np.abs(rib_positions[-1]) + self.back_ribs_geometry["thickness"]/2 > backplate_extent:
            raise ValueError("Right side of back rib too thick - overlapping with first wall")
        for i in range(len(rib_positions)-1):
            if rib_positions[i+1] - rib_positions[i] <= self.back_ribs_geometry["thickness"]:
                raise ValueError("Back ribs overlapping or touching each other")

    def check_slope(self, distance_to_edge, vertical_extent, error_message):
        fw_offset = (self.first_wall_geometry["outer width"] - self.first_wall_geometry["inner width"])/2
        if fw_offset < 0:
            if np.abs(self.first_wall_geometry["length"]/fw_offset) < np.abs(vertical_extent/distance_to_edge):
                raise ValueError(error_message)

    def setup_assembly(self):
        pin_positions = self.__tile_pins()

        self.components.append(FirstWallComponent({"geometry": self.first_wall_geometry, "material": self.first_wall_material}))

        bz_backplate_json = self.__get_bz_backplate_json()
        self.components.append(BZBackplate(bz_backplate_json, pin_positions))

        front_rib_geometry, front_rib_positions = self.__get_front_ribs_params()
        front_rib_thickness = self.front_ribs_geometry["thickness"]
        for front_rib_pos in front_rib_positions:
            self.components.append(FrontRib({"geometry": front_rib_geometry, "material": self.first_wall_material, "origin": front_rib_pos}))

        purge_gas_hole_positions = self.__sort_pin_positions(pin_positions)
        purge_gas_front_plate_json = self.__get_pg_front_plate_json()
        self.components.append(PurgeGasPlate("purge_gas_front", purge_gas_front_plate_json, front_rib_positions, front_rib_thickness, purge_gas_hole_positions))

        purge_gas_mid_plate_json = self.__get_pg_mid_plate_json()
        self.components.append(PurgeGasPlate("purge_gas_mid", purge_gas_mid_plate_json, front_rib_positions, front_rib_thickness, purge_gas_hole_positions))

        purge_gas_back_plate_json = self.__get_pg_back_plate_json()
        self.components.append(PurgeGasPlate("purge_gas_back", purge_gas_back_plate_json, front_rib_positions, front_rib_thickness, purge_gas_hole_positions))

        back_rib_geometry, back_rib_positions = self.__get_back_ribs_params()
        for back_rib_pos in back_rib_positions:
            self.components.append(BackRib({"geometry": back_rib_geometry, "material": self.first_wall_material, "origin": back_rib_pos}))

        co_plenum_json = self.__get_cop_json()
        self.components.append(CoolantOutletPlenum(co_plenum_json, back_rib_positions, self.back_ribs_geometry["thickness"]))

        sep_plate_json = self.__get_separator_plate_json()
        self.components.append(SeparatorPlate(sep_plate_json, back_rib_positions, self.back_ribs_geometry["thickness"]))

        fw_backplate_geometry = self.__get_fw_backplate_params()
        self.components.append(FWBackplate({"geometry": fw_backplate_geometry, "material": self.first_wall_material}))

    def __add_component_attributes(self):
        for component in self.component_list:
            if component["class"] == "first_wall":
                self.first_wall_geometry = component["geometry"]
                self.first_wall_material = component["material"]
            elif component["class"] == "pin":
                self.breeder_materials = component["material"]
                self.breeder_geometry = component["geometry"]
            elif component["class"] == "front_rib":
                self.front_ribs_geometry = component["geometry"]
            elif component["class"] == "back_rib":
                self.back_ribs_geometry = component["geometry"]
            elif component["class"] == "coolant_outlet_plenum":
                self.cop_geometry = component["geometry"]

    def __dict_with_height(self):
        return {"height": self.first_wall_geometry["height"]}

    def __jsonify(self, geometry: dict, origin_z_coord: int):
        '''Return dictonary with geometry, material, and origin keys. 
        Material is the same as the assembly's first wall. 
        Origin is along the z-axis.

        :param geometry: dictionary with geometry information
        :type geometry: dict
        :param start_z: Origin z coordinate
        :type start_z: int
        :return: Dictionary in the input json style
        :rtype: dict
        '''
        return {"geometry": geometry, "material": self.first_wall_material, "origin": Vertex(0, 0, origin_z_coord)}

    def __get_pin_start_params(self):
        '''Calculate the number of pins that fit in a 'row' for tiling breeder pins on the first wall. 
        Also calculate the x-coordinate of the furthest along the -x axis.

        :return: Number of pins, x-coord
        :rtype: (int, int)
        '''
        multiplier_side = self.breeder_geometry["multiplier side"]
        pin_spacing = self.geometry["pin spacing"]
        accessible_width = self.first_wall_geometry["inner width"] - 2*(self.geometry["pin horizontal offset"] + self.first_wall_geometry["bluntness"])

        row_pins = int((accessible_width - 2*multiplier_side) // (pin_spacing * np.cos(np.pi/6))) + 1
        horizontal_start_pos = -(row_pins-1)*pin_spacing*np.cos(np.pi/6) / 2
        return row_pins, horizontal_start_pos

    def __tile_pins(self):
        fw_geometry = self.first_wall_geometry
        # get parameters
        multiplier_side = self.breeder_geometry["multiplier side"]
        vertical_offset = self.geometry["pin vertical offset"]
        pin_spacing = self.geometry["pin spacing"]
        length = fw_geometry["length"]
        height = fw_geometry["height"]
        wall_thickness = fw_geometry["thickness"]

        # 'accessible' for tiling breeder units
        accessible_height = height - 2*vertical_offset
        # hexagonally tiled breeder units are broken up into 'rows' and 'columns'
        row_pins, horizontal_start_pos = self.__get_pin_start_params() 
        self.first_wall_geometry["pin horizontal start"] = horizontal_start_pos
        # each column 'index' has breeder units at 2 different heights
        columns_indices = int((accessible_height - 2*multiplier_side*np.cos(np.pi/6)) // pin_spacing) + 1
        # number of distinct heights we can place breeder units
        distinct_pin_heights = int((accessible_height - 2*multiplier_side*np.cos(np.pi/6)) // (pin_spacing*np.sin(np.pi/6))) + 1
        centering_vertical_offset = ((accessible_height - 2*multiplier_side*np.cos(np.pi/6)) - (distinct_pin_heights-1)*pin_spacing*np.sin(np.pi/6)) / 2
        vertical_start_pos = height - (vertical_offset + centering_vertical_offset + multiplier_side*np.cos(np.pi/6))

        pin_positions = [[] for j in range(columns_indices)]
        for j in range(columns_indices):
            pin_pos = Vertex(horizontal_start_pos, vertical_start_pos, length-wall_thickness) + Vertex(0, -pin_spacing*j)
            for i in range(row_pins):
                # stop tiling if we overshoot the number of column pins (each column index corresponds to 2 column pins)
                if (j*2)+1 + (i%2) <= distinct_pin_heights:
                    pin_positions[j].append(pin_pos)
                    self.components.append(PinAssembly({"material":self.breeder_materials, "geometry":self.breeder_geometry, "origin":pin_pos}))
                else:
                    pin_positions[j].append(False)
                pin_pos = pin_pos + Vertex(pin_spacing).rotate(((-1)**(i+1))*np.pi/6)
        return pin_positions

    def __fill_fw_width(self, distance_from_fw):
        fw_length = self.first_wall_geometry["length"]
        fw_outer_width = self.first_wall_geometry["outer width"]
        z_position = fw_length - (distance_from_fw + self.first_wall_geometry["thickness"])
        offset = (fw_outer_width - self.first_wall_geometry["inner width"])/2

        if offset == 0:
            slope_angle = np.pi/2
        elif offset > 0:
            slope_angle = np.arctan(fw_length/offset)
        else:
            slope_angle = np.pi + np.arctan(fw_length/offset)

        fw_sidewall_horizontal = self.first_wall_geometry["sidewall thickness"] / np.sin(slope_angle)
        position_fraction = z_position/fw_length

        filled_width = fw_outer_width - 2*(position_fraction*offset + fw_sidewall_horizontal)

        return filled_width

    def __get_plate_length_and_ext(self, distance_from_fw: int, thickness: int):
        '''Calculate length of plate that fits into the assembly's first wall (FW), 
        as well as how much longer the side of the plate further from the FW needs to be (on either end).

        :param distance_from_fw: Distance of the near side of the plate from the FW
        :type distance_from_fw: int
        :param thickness: Thickness of plate
        :type thickness: int
        :return: length of plate, extension of plate
        :rtype: (int, int)
        '''
        back_distance_from_fw = distance_from_fw + thickness
        length = self.__fill_fw_width(distance_from_fw)
        extension = (self.__fill_fw_width(back_distance_from_fw) - length)/2
        return length, extension

    def __get_bz_backplate_json(self):
        fw_geometry = self.first_wall_geometry
        parameters = self.__dict_with_height()
        parameters["thickness"] = self.breeder_geometry["pressure tube length"] - self.breeder_geometry["multiplier length"]
        parameters["hole radius"] = self.breeder_geometry["pressure tube outer radius"]

        front_distance_from_fw = self.breeder_geometry["pressure tube length"] - parameters["thickness"]
        parameters["length"], parameters["extension"] = self.__get_plate_length_and_ext(front_distance_from_fw, parameters["thickness"])

        backplate_start_z = fw_geometry["length"] - (self.breeder_geometry["pressure tube length"] + fw_geometry["thickness"])
        return self.__jsonify(parameters, backplate_start_z)

    def __get_rib_positions(self, z_position) -> list[Vertex]:
        pin_spacing = self.geometry["pin spacing"]*np.sqrt(3/4)
        horizontal_start = self.__get_pin_start_params()[1] - pin_spacing/2

        positions = []
        front_rib_positions = self.geometry["front rib positions"]
        front_rib_positions.sort()
        for position_index in front_rib_positions:
            positions.append(Vertex(horizontal_start + position_index*pin_spacing, 0, z_position))

        return positions

    def __add_common_rib_params(self, params: dict):
        params["height"] = self.first_wall_geometry["height"]
        params["connection height"] = self.geometry["rib connection height"]
        params["connection width"] = self.geometry["rib connection width"]
        params["side channel gap"] = self.geometry["rib side channel gap"]
        params["side channel vertical margin"] = self.geometry["rib side channel vertical margin"]
        return params

    def __get_front_ribs_params(self):
        bu_geometry = self.breeder_geometry

        params = self.front_ribs_geometry
        params = self.__add_common_rib_params(params)
        params["length"] = bu_geometry["pressure tube thickness"] + bu_geometry["pressure tube gap"] + bu_geometry["inner length"] - bu_geometry["pressure tube length"]

        z_position = self.first_wall_geometry["length"] - (self.first_wall_geometry["thickness"] + self.breeder_geometry["pressure tube length"])
        rib_positions = self.__get_rib_positions(z_position)
        return params, rib_positions

    def __get_back_ribs_params(self):
        bu_geometry = self.breeder_geometry

        params = self.back_ribs_geometry
        params = self.__add_common_rib_params(params)

        z_position = self.first_wall_geometry["length"] - (bu_geometry["pressure tube thickness"] + bu_geometry["pressure tube gap"] + bu_geometry["inner length"] + self.first_wall_geometry["thickness"])
        params["length"] = z_position - self.geometry["FW backplate thickness"]
        rib_positions = self.__get_rib_positions(z_position)
        return params, rib_positions

    def __sort_pin_positions(self, pin_positions):
        rib_pos = self.geometry["front rib positions"]
        plate_hole_positions = [[] for i in range(len(rib_pos)+1)]

        for row in pin_positions:
            padded_rib_pos = [0] + rib_pos + [len(row)]
            for i in range(len(padded_rib_pos)-1):
                plate_hole_positions[i].append(row[padded_rib_pos[i]:padded_rib_pos[i+1]])
        return plate_hole_positions

    def __get_pg_front_plate_json(self):
        fw_geometry = self.first_wall_geometry
        bu_geometry = self.breeder_geometry
        parameters = self.__dict_with_height()
        parameters["thickness"] = self.geometry["PG front plate thickness"]
        plate_distance_from_fw = bu_geometry["pressure tube thickness"] + bu_geometry["pressure tube gap"] + bu_geometry["offset"] + bu_geometry["outer length"] - parameters["thickness"]
        parameters["hole radius"] = bu_geometry["inner cladding"] + bu_geometry["outer cladding"] + bu_geometry["breeder chamber thickness"] + bu_geometry["coolant inlet radius"]
        parameters["length"], parameters["extension"] = self.__get_plate_length_and_ext(plate_distance_from_fw, parameters["thickness"])

        start_z = fw_geometry["length"] - (fw_geometry["thickness"] + plate_distance_from_fw + parameters["thickness"])
        return self.__jsonify(parameters, start_z)

    def __get_pg_mid_plate_json(self):
        fw_geometry = self.first_wall_geometry
        bu_geometry = self.breeder_geometry
        parameters = self.__dict_with_height()
        parameters["thickness"] = self.geometry["PG mid plate thickness"]
        parameters["hole radius"] = bu_geometry["inner cladding"] + bu_geometry["coolant inlet radius"]
        plate_distance_from_fw = bu_geometry["pressure tube thickness"] + bu_geometry["pressure tube gap"] + bu_geometry["offset"] + bu_geometry["outer length"] + self.geometry["PG mid plate gap"]
        parameters["length"], parameters["extension"] = self.__get_plate_length_and_ext(plate_distance_from_fw, parameters["thickness"])

        start_z = fw_geometry["length"] - (fw_geometry["thickness"] + plate_distance_from_fw + parameters["thickness"])
        return self.__jsonify(parameters, start_z)

    def __get_pg_back_plate_json(self):
        fw_geometry = self.first_wall_geometry
        bu_geometry = self.breeder_geometry
        parameters = self.__dict_with_height()
        parameters["thickness"] = self.geometry["PG back plate thickness"]
        plate_distance_from_fw = bu_geometry["pressure tube thickness"] + bu_geometry["pressure tube gap"] + bu_geometry["inner length"] - parameters["thickness"]
        parameters["hole radius"] = bu_geometry["inner cladding"] + bu_geometry["coolant inlet radius"]
        parameters["length"], parameters["extension"] = self.__get_plate_length_and_ext(plate_distance_from_fw, parameters["thickness"])

        start_z = fw_geometry["length"] - (fw_geometry["thickness"] + plate_distance_from_fw + parameters["thickness"])
        return self.__jsonify(parameters, start_z)

    def __get_cop_json(self):
        bu_geometry = self.breeder_geometry
        parameters = self.cop_geometry
        offset = self.geometry["coolant outlet plenum gap"]
        parameters["height"] = self.first_wall_geometry["height"]

        start_z = self.first_wall_geometry["length"] - (bu_geometry["pressure tube thickness"] + bu_geometry["pressure tube gap"] + bu_geometry["inner length"] + self.first_wall_geometry["thickness"] + offset)
        return self.__jsonify(parameters, start_z)

    def __get_separator_plate_json(self):
        bu_geometry = self.breeder_geometry
        pg_backplate_distance = bu_geometry["pressure tube thickness"] + bu_geometry["pressure tube gap"] + bu_geometry["inner length"]
        distance_from_fw = pg_backplate_distance + self.geometry["coolant outlet plenum gap"] + self.cop_geometry["length"] + self.geometry["separator plate gap"]

        parameters = self.__dict_with_height()
        parameters["thickness"] = self.geometry["separator plate thickness"]
        parameters["length"], parameters["extension"] = self.__get_plate_length_and_ext(distance_from_fw, parameters["thickness"])
        parameters["hole radius"] = 0

        start_z = self.first_wall_geometry["length"] - (distance_from_fw + parameters["thickness"] + self.first_wall_geometry["thickness"])
        return self.__jsonify(parameters, start_z)

    def __get_fw_backplate_params(self):
        fw_geom = self.first_wall_geometry
        parameters = self.__dict_with_height()
        parameters["thickness"] = self.geometry["FW backplate thickness"]
        parameters["hole radius"] = 0
        distance_from_fw = fw_geom["length"] - (parameters["thickness"] + fw_geom["thickness"])
        parameters["length"], parameters["extension"] = self.__get_plate_length_and_ext(distance_from_fw, parameters["thickness"])
        return parameters


def get_all_geometries_from_components(component_list) -> list[CubitInstance]:
    '''Get all geometries from components :)

    :param component_list: List of components
    :type component_list: list
    :return: List of geometries
    :rtype: list[CubitInstance]
    '''
    instances = []
    for component in component_list:
        if isinstance(component, CubitInstance):
            instances.append(component)
        elif isinstance(component, SimpleComponent):
            instances += component.subcomponents
        elif isinstance(component, GenericComponentAssembly):
            instances += component.get_all_geometries()
    return instances


# DO NOT USE - legacy, there is a new union function in cubit_functions.py
def unionise(component_list: list):
    '''Create a union of all instances in given components.

    :param component_list: list of components
    :type component_list: list
    :return: Geometry of union
    :rtype: CubitInstance
    '''
    if len(component_list) == 0:
        raise CubismError("This is an empty list you have given me")

    # get all CubitInstances from components
    instances_to_union = get_all_geometries_from_components(component_list)

    # convert to bodies :(
    instances_to_union = to_bodies(instances_to_union)

    # check whether a union is possible
    if len(instances_to_union) == 0:
        raise CubismError("Could not find any instances")
    elif len(instances_to_union) == 1:
        return instances_to_union[0].copy()

    # get cubit handles
    instances_to_union = [i.handle for i in instances_to_union]

    # need old and new volumes to check what the union creates
    old_volumes = cubit.get_entities("volume")
    old_bodies = cubit.get_entities("body")
    cubit.unite(instances_to_union, keep_old_in=True)
    new_volumes = cubit.get_entities("volume")
    new_bodies = cubit.get_entities("body")
    if len(new_bodies) == len(old_bodies) + 1:
        return CubitInstance(cubit.get_last_id("body"), "body")
    elif len(new_volumes) == len(old_volumes) + 1:
        return CubitInstance(cubit.get_last_id("volume"), "volume")
    else:
        raise CubismError("Something unknowable was created in this union. Or worse, a surface.")


def construct(json_object: dict, *args):
    '''Instantiate component in python and cubit

    Parameters
    ----------
    json_object : dict
        json input for component

    Returns
    -------
    SimpleComponent | GenericComponentAssembly
        Instantiated python class
    '''
    constructor = globals()[CLASS_MAPPING[json_object["class"]]]
    return constructor(json_object, *args)
