'''
legacy.py
author(s): Sid Mungale

Legacy code that for components no longer in use
(c) Copyright UKAEA 2024
'''

import cubit
from hypnos.generic_classes import (
    cmd,
    CubitInstance,
    CubismError
)
from hypnos.geometry import (
    convert_to_3d_vector,
    create_brick
)
from hypnos.components import SimpleComponent
from hypnos.assemblies import (
    CreatedComponentAssembly,
    ExternalComponentAssembly
)

# constants
NEUTRON_TEST_FACILITY_REQUIREMENTS = ["room", "source"]
BLANKET_REQUIREMENTS = ["breeder", "structure"]
ROOM_REQUIREMENTS = ["blanket", "surrounding_walls"]
BLANKET_SHELL_REQUIREMENTS = ["first_wall", "pin"]
FACILITY_MORPHOLOGIES = ["exclusive", "inclusive", "overlap", "wall"]


# Simple components
class SurroundingWallsComponent(SimpleComponent):
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
        return self.air.get_geometries()

    def make_geometry(self):
        '''create 3d room with outer dimensions dimensions (int or list) and thickness (int or list)'''
        # get variables
        outer_dims = convert_to_3d_vector(self.geometry["dimensions"])
        thickness = convert_to_3d_vector(self.geometry["thickness"])
        # create room
        subtract_vol = cubit.brick(outer_dims[0]-2*thickness[0], outer_dims[1]-2*thickness[1], outer_dims[2]-2*thickness[2])
        block = cubit.brick(outer_dims[0], outer_dims[1], outer_dims[2])
        cubit.subtract([subtract_vol], [block])
        room_id = cubit.get_last_id("volume")
        return CubitInstance(room_id, "volume")


class AirComponent(SimpleComponent):
    '''Air, stored as body'''
    def __init__(self, json_object: dict):
        super().__init__("air", json_object)
        # cubit subtract only keeps body ID invariant, so i will store air as a body
        self.as_bodies()

    def make_geometry(self):
        return create_brick(self.geometry)


class BreederComponent(SimpleComponent):
    def __init__(self, json_object):
        super().__init__("breeder", json_object)

    def make_geometry(self):
        return create_brick(self.geometry)


class StructureComponent(SimpleComponent):
    def __init__(self, json_object):
        super().__init__("structure", json_object)
    def make_geometry(self):
        return create_brick(self.geometry)


class WallComponent(SimpleComponent):
    def __init__(self, json_object):
        super().__init__("wall", json_object)

    def make_geometry(self):
        # get variables
        # wall
        geom = self.geometry
        thickness = geom["wall thickness"]
        plane = geom["wall plane"] if "wall plane" in geom.keys() else "x"
        pos = geom["wall position"] if "wall position" in geom.keys() else 0
        # hole
        hole_pos = geom["wall hole position"] if "wall hole position" in geom.keys() else [0, 0]
        hole_radius = geom["wall hole radius"]
        # wall fills room
        room_dims = convert_to_3d_vector(geom["dimensions"])
        room_thickness = convert_to_3d_vector(geom["thickness"])
        wall_dims = [room_dims[i]-2*room_thickness[i] for i in range(3)]

        # volume to subtract to create a hole
        cmd(f"create cylinder height {thickness} radius {hole_radius}")
        subtract_vol = CubitInstance(cubit.get_last_id("volume"), "volume")

        # depending on what plane the wall needs to be in,
        # create wall + make hole at right place
        if plane == "x":
            cubit.brick(thickness, wall_dims[1], wall_dims[2])
            wall = CubitInstance(cubit.get_last_id("volume"), "volume")
            cmd(f"rotate volume {subtract_vol.cid} angle 90 about Y")
            cmd(f"move volume {subtract_vol.cid} y {hole_pos[1]} z {hole_pos[0]}")
        elif plane == "y":
            cubit.brick(wall_dims[0], thickness, wall_dims[2])
            wall = CubitInstance(cubit.get_last_id("volume"), "volume")
            cmd(f"rotate volume {subtract_vol.cid} angle 90 about X")
            cmd(f"move volume {subtract_vol.cid} x {hole_pos[0]} z {hole_pos[1]}")
        elif plane == "z":
            cubit.brick(wall_dims[0], wall_dims[1], thickness)
            wall = CubitInstance(cubit.get_last_id("volume"), "volume")
            cmd(f"move volume {subtract_vol.cid} x {hole_pos[0]} y {hole_pos[1]}")
        else:
            raise CubismError("unrecognised plane specified")

        cmd(f"subtract volume {subtract_vol.cid} from volume {wall.cid}")
        # move wall
        cmd(f"move volume {wall.cid} {plane} {pos}")

        return CubitInstance(wall.cid, wall.geometry_type)


# Assemblies
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


# in case we need to do source-specific actions
class SourceAssembly(ExternalComponentAssembly):
    '''Assembly of external components,
    created when a json object has class= source'''
    def __init__(self, json_object: dict):
        super().__init__(json_object)


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
