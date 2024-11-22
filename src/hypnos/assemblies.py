'''
assemblies.py
author(s): Sid Mungale

Assembly classes and construct function.
Assembly classes organise the arrangement of their children component classes,
for example a Pin would consist of Cladding, Breeder, Coolant, etc. components.

(c) Copyright UKAEA 2024
'''

from hypnos.generic_classes import CubismError, CubitInstance, cmd, cubit
from hypnos.components import (
    ComponentBase,
    ExternalComponent,
    SimpleComponent,
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
from hypnos.cubit_functions import to_volumes, get_entities_from_group
from hypnos.geometry import Vertex, arctan
from hypnos.constants import (
    CLASS_MAPPING,
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
        volume_ids_list = [i.cid for i in to_volumes(self.get_geometries())]
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

    def check_sanity(self):
        '''Check whether geometrical parameters are physical on the
        assembly level.
        '''
        pass


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
