import sys
import json
import argparse

if __name__ == "__main__":
    # if this is run as a python file, import cubit
    sys.path.append('/opt/Coreform-Cubit-2023.8/bin')
    import cubit
    cubit.init(['cubit', '-nojournal'])

    # accept command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--file", type=str, help="name of json file", default="sample_morphology.json")
    parser.add_argument("-p", "--printinfo", action="store_true")
    args = parser.parse_args()

    # File to look at
    JSON_FILENAME = args.file
elif __name__ == "__coreformcubit__":
    # if this is cubit, reset first
    cubit.cmd("reset")
    JSON_FILENAME = "sample_morphology.json"
# NEED TO SET UP JSON_FILENAME VARIABLE IF THIS IS USED IN ANY OTHER CONTEXT

# components in assemblies to be generated
NEUTRON_TEST_FACILITY_REQUIREMENTS = ["room", "source"]
NEUTRON_TEST_FACILITY_ADDITIONAL = []
BLANKET_REQUIREMENTS = ["breeder", "structure"]
BLANKET_ADDITIONAL = ["coolant", "multiplier"]
ROOM_REQUIREMENTS = ["blanket", "surrounding_walls"]
ROOM_ADDITIONAL = ["wall"]

# classes according to what make_geometry subfunction(?) needs to be called
BLOB_CLASSES = ["complex", "breeder", "structure", "air"]
ROOM_CLASSES = ["surrounding_walls"]
WALL_CLASSES = ["wall"]

# currently only supports exclusive, inclusive, and overlap
FACILITY_MORPHOLOGIES= ["exclusive", "inclusive", "overlap", "wall"]

# mapping from json class names to python class names
CLASS_MAPPING = {
    "complex": "ComplexComponent",
    "external": "ExternalComponentAssembly",
    "source": "SourceAssembly",
    "neutron test facility": "NeutronTestFacility",
    "blanket": "BlanketAssembly",
    "room": "RoomAssembly",
    "surrounding_walls": "SurroundingWallsComponent",
    "breeder": "BreederComponent",
    "structure": "StructureComponent"
}

# raise this when bad things happen
class CubismError(Exception):
    pass

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
    elif json_object["class"] == "breeder":
        return constructor(
            geometry= json_object["geometry"],
            material= json_object["material"]
        )
    elif json_object["class"] == "structure":
        return constructor(
            geometry= json_object["geometry"],
            material= json_object["material"]
        )

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

class GenericComponentAssembly:
    '''
    Generic assembly that takes a list of classnames to set up a subclass.

    An assembly class specified from this will:

    * have attributes corresponding to the supplied classnames
    * store components of the specified classnames in corresponding attributes, otherwise other_components
    * be able to fetch cubit instances of components stores in these attributes (get_cubit_instances)
    '''
    def __init__(self, classname, setup_classnames: list):
        self.classname = classname
        # component_mapping defines what classes get stored in what attributes (other_components is default)
        self.other_components = []
        self.component_mapping = {"other": self.other_components}

        # set up attributes and component_mapping for specified components
        for classname in setup_classnames:
            component_name = classname + "_components"
            self.__setattr__(component_name, [])
            self.component_mapping[classname] = self.__getattribute__(component_name)

    # These refer to cubit handles
    def get_cubit_instances_from_classname(self, classname_list: list):
        '''Get list of cubit instances of specified classnames

        :param classname_list: list of classnames to search in
        :type classname_list: list
        :return: list of cubit handles
        :rtype: list
        '''
        instances_list = []
        for component_classname in classname_list:
            # checks if valid classname
            if component_classname in self.component_mapping.keys():
                for component in self.component_mapping[component_classname]:
                    # fetches instances
                    if isinstance(component, GenericCubitInstance):
                        instances_list.append(component.cubitInstance)
                    elif isinstance(component, ComplexComponent):
                        instances_list += component.subcomponents
                    elif isinstance(component, GenericComponentAssembly):
                        # This feels very scuffed
                        instances_list += component.get_cubit_instances_from_classname(classname_list)
        return instances_list
    
    def get_all_cubit_instances(self) -> list:
        '''get every cubit instance stored in this assembly instance recursively

        :return: list of cubit handles
        :rtype: list
        '''
        instances_list = []
        for component_attribute in self.component_mapping.values():
            for component in component_attribute:
                if isinstance(component, GenericCubitInstance):
                    instances_list.append(component.cubitInstance)
                elif isinstance(component, ComplexComponent):
                    instances_list += [subcomp.cubitInstance for subcomp in component.subcomponents]
                elif isinstance(component, GenericComponentAssembly):
                    instances_list += component.get_all_cubit_instances()
        return instances_list

    # These refer to GenericCubitInstance objects
    def get_generic_cubit_instances_from_classname(self, classname_list: list) -> list:
        '''Get list of geometries under given classnames

        :param classname_list: list of classnames to search under
        :type classname_list: list
        :return: list of GenericCubitInstances
        :rtype: list
        '''
        component_list = []
        for classname in classname_list:
            if classname in self.component_mapping.keys():
                for component in self.component_mapping[classname]:
                    if isinstance(component, GenericCubitInstance):
                        component_list.append(component)
                    elif isinstance(component, ComplexComponent):
                        component_list += component.subcomponents
                    elif isinstance(component, GenericComponentAssembly):
                        component_list += component.get_generic_cubit_instances_from_classname(classname_list)
        return component_list
    
    def get_all_generic_cubit_instances(self) -> list:
        '''get every geometry stored in this assembly instance recursively

        :return: list of GenericCubitInstances
        :rtype: list
        '''
        instances_list = []
        for component_attribute in self.component_mapping.values():
            for component in component_attribute:
                if isinstance(component, GenericCubitInstance):
                    instances_list.append(component)
                elif isinstance(component,ComplexComponent):
                    instances_list += component.subcomponents 
                elif isinstance(component, GenericComponentAssembly):
                    instances_list += component.get_all_generic_cubit_instances()
        return instances_list

    def get_volumes_list(self) -> list:
        volumes_list = from_bodies_to_volumes(self.get_all_generic_cubit_instances)
        return [volume.cid for volume in volumes_list]

class CreatedComponentAssembly(GenericComponentAssembly):
    '''
    Assembly to handle components created natively. Takes a list of required and additional classnames to set up a specific assembly:

    * *required classnames*: instantiating will fail without at least one component of the given classnames
    * *additional classnames*: defines attributes to store components with this classname

    An assembly class specified from this will:

    * have attributes corresponding to the supplied classnames
    * require every instance have at least one component from the required classnames
    * store components of the specified classnames in corresponding attributes, otherwise other_components
    * be able to fetch cubit instances of components stores in these attributes (get_cubit_instances)
    '''
    def __init__(self, classname, component_list: list, required_classnames: list, additional_classnames: list):
        self.classname = classname
        # this defines what components to require in every instance
        self.required_classnames = required_classnames

        # component_mapping defines what classes get stored in what attributes (other_components is default)
        self.other_components = []
        self.component_mapping = {"other": self.other_components}

        # set up attributes and component_mapping for required components
        for classname in required_classnames + additional_classnames:
            component_name = classname + "_components"
            self.__setattr__(component_name, [])
            self.component_mapping[classname] = self.__getattribute__(component_name)

        # enforce given component_list based on required_classnames
        self.enforced = self.enforce_structure(component_list)
        # store instances
        self.setup_assembly(component_list)

    def enforce_structure(self, comp_list: list):
        '''Make sure the instance contains the required components. This looks at the classes specified in the json file'''
        class_list = [i["class"] for i in comp_list]
        for classes_required in self.required_classnames:
            if classes_required not in class_list:
                # Can change this to a warning, for now it just throws an error
                raise CubismError(f"This assembly must contain: {self.required_classnames}. Currently contains: {class_list}")
        return True
    
    def setup_assembly(self, component_list: list):
        '''Add components to attributes according to their class'''
        for component_dict in component_list:
            # if you are looking for the class-attribute mapping it is the component_mapping dict in __init__
            if (component_dict["class"] in self.component_mapping.keys()):
                self.component_mapping[component_dict["class"]].append(json_object_reader(component_dict))
            else:
                self.other_components.append(json_object_reader(component_dict))

class NeutronTestFacility(CreatedComponentAssembly):
    '''
    Assmebly class that requires at least one source, blanket, and room.
    Fails if specified morphology is not followed.
    Currently supports inclusive, exclusive, and overlap morphologies.

    On instantiating this performs the following tasks:

    * Ensure the specified morphology is followed
    * Fills room components with air
    * Imprints and merges geometry
    * Tracks specified materials and material interfaces
    * Adds material interfaces to sidesets
    '''
    def __init__(self, morphology: str, component_list: list):
        super().__init__("NTF", component_list, NEUTRON_TEST_FACILITY_REQUIREMENTS, NEUTRON_TEST_FACILITY_ADDITIONAL)
        # this defines what morphology will be enforced later
        self.morphology = morphology
        self.enforce_facility_morphology()
        self.apply_facility_morphology()
        self.validate_rooms_and_fix_air()
        self.change_air_to_volumes()
        self.check_for_overlaps()
        self.imprint_all()
        MaterialsTracker().merge_and_track_boundaries()
        self.merge_all()
        MaterialsTracker().add_boundaries_to_sidesets()

    def enforce_facility_morphology(self):
        '''Make sure the specified morphology is followed. This works by comparing the volumes of the source and blanket to the volume of their union'''

        if self.morphology not in FACILITY_MORPHOLOGIES:
            raise CubismError(f"Morphology not supported by this facility: {self.morphology}")
        
        # Get the net source, blanket, and the union of both
        source_object= unionise(self.source_components)
        blanket_components = []
        for i in self.room_components:
            blanket_components += i.blanket_components 
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
            source_volumes = from_bodies_to_volumes(self.get_generic_cubit_instances_from_classname(["source", "external"]))
            blanket_volumes = []
            for room in self.room_components:
                blanket_volumes += from_bodies_to_volumes(room.get_generic_cubit_instances_from_classname(["blanket", "breeder", "structure", "coolant"]))
            # if there is an overlap, remove it
            for source_volume in source_volumes:
                for blanket_volume in blanket_volumes:
                    if isinstance(source_volume, GenericCubitInstance) & isinstance(blanket_volume, GenericCubitInstance):
                        if not (cubit.get_overlapping_volumes([source_volume.cid, blanket_volume.cid]) == ()):
                            # i have given up on my python api dreams. we all return to cubit ccl in the end.
                            cubit.cmd(f"remove overlap volume {source_volume.cid} {blanket_volume.cid} modify volume {blanket_volume.cid}")
            print(f"{self.morphology} morphology applied")

    def check_for_overlaps(self):
        volume_ids_list = [i.cid for i in from_bodies_to_volumes(self.get_all_generic_cubit_instances())]
        overlaps = cubit.get_overlapping_volumes(volume_ids_list)
        if overlaps != ():
            raise CubismError(f"Here be overlaps: {overlaps}")

    def imprint_all(self):
        '''imprint all :)'''
        cubit.cmd("imprint all")
    
    def merge_all(self):
        '''merge all :)'''
        cubit.cmd("merge all")

    def validate_rooms_and_fix_air(self):
        '''subtract all non-air geometries from all air geometries. Validate that everything is inside a room'''

        # collect geometries that define the complete space of the facility
        room_bounding_boxes = []
        for room in self.room_components:
            # get all air (it is set up to be overlapping with the surrounding walls at this stage)
            for surrounding_walls in room.surrounding_walls_components:
                if isinstance(surrounding_walls, SurroundingWallsComponent):
                    room_bounding_boxes += surrounding_walls.air.subcomponents
            # walls are set up to be subtracted from air on creation so need to add them in manually
            for walls in room.wall_components:
                if isinstance(walls, WallComponent):
                    room_bounding_boxes += walls.subcomponents
        
        # get a union defining the 'bounding boxes' for all rooms, and a union of every geometry in the facility. 
        # as well as the union of those two unions
        room_bounding_box = unionise(room_bounding_boxes)
        all_geometries = unionise(self.get_all_generic_cubit_instances())
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
        for room in self.room_components:
            for surrounding_walls in room.surrounding_walls_components:
                if isinstance(surrounding_walls, SurroundingWallsComponent):
                    if surrounding_walls.is_air():
                        for air in surrounding_walls.get_air_subcomponents():
                            all_geometries_copy = all_geometries.copy_cubit_instance()
                            cubit.cmd(f'subtract {all_geometries_copy.geometry_type} {all_geometries_copy.cid} from {air.geometry_type} {air.cid}')
        # cleanup
        all_geometries.destroy_cubit_instance()

    # this is just ridiculous. like actually why.
    def change_air_to_volumes(self):
        '''Components referring to air now only contain volumes'''
        for room in self.room_components:
            for surrounding_walls in room.surrounding_walls_components:
                if isinstance(surrounding_walls, SurroundingWallsComponent):
                    surrounding_walls.air_as_volumes()

class BlanketAssembly(CreatedComponentAssembly):
    '''Assembly class that requires at least one breeder and structure. Additionally stores coolants separately'''
    def __init__(self, component_list: list):
        super().__init__("Blanket", component_list, BLANKET_REQUIREMENTS, BLANKET_ADDITIONAL)

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
        super().__init__("Room", component_list, ROOM_REQUIREMENTS, ROOM_ADDITIONAL)

        self.setup_walls(json_walls)

    def setup_walls(self, json_walls):
        '''Set up walls in surrounding walls. Remove air from walls'''
        for surrounding_walls in self.surrounding_walls_components:
            for json_wall in json_walls:
                # make wall
                wall_geometry = surrounding_walls.geometry
                wall_material = json_wall["material"] if "material" in json_wall.keys() else surrounding_walls.material
                for wall_key in json_wall["geometry"].keys():
                    wall_geometry["wall " + wall_key] = json_wall["geometry"][wall_key]
                self.wall_components.append(WallComponent(wall_geometry, wall_material))
                # remove air
                for air in surrounding_walls.air.subcomponents:
                    temp_wall = WallComponent(wall_geometry, wall_material)
                    for t_w in temp_wall.subcomponents:
                        cubit.cmd(f"subtract {t_w.geometry_type} {t_w.cid} from {air.geometry_type} {air.cid}")

# everything in cubit will need to be referenced by a geometry type and id
class GenericCubitInstance:
    '''
    Wrapper for cubit geometry entity.
    Can access cubit ID (cid), geometry type, and cubit handle (cubitInstance).
    Can destroy cubit instance. Can copy itself (and thus also the cubit instance it refers to). Can update this to refer to a different cubit instance.
    '''
    def __init__(self, cid: int, geometry_type: str) -> None:
        self.cid = cid
        self.geometry_type = geometry_type
        self.cubitInstance = get_cubit_geometry(self.cid, self.geometry_type)
    
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

# Classes to track materials and geometries made of those materials
class Material:
    '''Tracks cubit instances made of this material.
    '''
    def __init__(self, name: str, group_id: int) -> None:
        self.name = name
        self.group_id = group_id
        # only stores GenericCubitInstances, i would make this a private member if i could :(
        self.geometries = []
        # currently does nothing
        self.state_of_matter = ""
    
    def add_geometry(self, geometry):
        if isinstance(geometry, GenericCubitInstance):
            self.geometries.append(geometry)
        else:
            raise CubismError("Not a GenericCubitInstance???")
    
    def change_state(self, state: str):
        self.state_of_matter = state
    
    def get_surface_ids(self):
        return [i.cid for i in from_bodies_and_volumes_to_surfaces(self.geometries)]

class MaterialsTracker:
    '''Tracks materials and boundaries between those materials (including nullspace)
    '''
    #i think i want materials to be tracked globally
    materials = []
    boundaries = []

    def make_material(self, material_name: str, group_id: int):
        '''Add material to internal list. Will not add if material name already exists

        :param material_name: Name of material
        :type material_name: str
        :param group_id: Cubit ID of group
        :type group_id: int
        '''
        if material_name not in [i.name for i in self.materials]:
            self.materials.append(Material(material_name, group_id))
    
    def add_geometry_to_material(self, geometry: GenericCubitInstance, material_name: str):
        '''Add geometry to material and track in cubit.

        :param geometry: Geometry to add
        :type geometry: GenericCubitInstance
        :param material_name: name of material to add geometry to
        :type material_name: str
        :return: True or raises error
        '''
        cubit.cmd(f'group "{material_name}" add {geometry.geometry_type} {geometry.cid}')
        group_id = cubit.get_id_from_name(material_name)
        self.make_material(material_name, group_id)

        # Add geometry to appropriate material. If it can't something has gone wrong
        for material in self.materials:
            if material.name == material_name:
                material.add_geometry(geometry)
                return True
        return CubismError("Could not add component")

    def contains_material(self, material_name):
        '''Check for the existence of a material

        :param material_name: name of material to check for
        :type material_name: str
        :return: True or False
        :rtype: bool
        '''
        return True if material_name in [i.name for i in self.materials] else False
    
    def sort_materials_into_pairs(self):
        '''Get all combinations of pairs of materials (not all permutations)

        :return: List of all pairs of materials in the class
        :rtype: list
        '''
        pair_list = []
        # this is my scuffed way of doing this
        min_counter = 0
        for i in range(len(self.materials)):
            for j in range(len(self.materials)):
                if j > min_counter:
                    pair_list.append((self.materials[i], self.materials[j]))
            min_counter+=1
        return pair_list
    
    def get_boundary_ids(self, boundary_name: str):
        '''Get cubit IDs of the geometries belonging to a boundary

        :param boundary_name: name of boundary to look in
        :type boundary_name: str
        :raises CubismError: If boundary cannot be found
        :return: list of cubit IDs
        :rtype: list
        '''
        for boundary in self.boundaries:
            if boundary.name == boundary_name:
                return [component.cid for component in boundary.geometries]
        raise CubismError("Could not find boundary")
    
    def add_geometry_to_boundary(self, geometry: GenericCubitInstance, boundary_name: str):
        '''If boundary exists, add geometry to it

        :param geometry: geometry to add
        :type geometry: GenericCubitInstance
        :param boundary_name: name of boundary to add to
        :type boundary_name: str
        :raises CubismError: If boundary can't be found
        :return: True
        :rtype: bool
        '''
        for boundary in self.boundaries:
            if boundary.name == boundary_name:
                boundary.add_geometry(geometry)
                return True
        raise CubismError("Could not find boundary")
    
    def merge_and_track_boundaries(self):
        '''tries to merge every possible pair of materials, and tracks the resultant material boundaries (if any exist).'''
        pair_list = self.sort_materials_into_pairs()
        # to check if merging has actually happened 
        last_tracked_group = cubit.get_last_id("group")

        # try to merge volumes in each group (ie intra-group merge)
        for material in self.materials:
            group_name = str(material.name) + "_" + str(material.name)
            cubit.cmd(f"merge group {material.group_id} with group {material.group_id} group_results")
            group_id = cubit.get_last_id("group")

            if not (group_id == last_tracked_group):
                cubit.cmd(f'group {group_id} rename "{group_name}"')
                self.boundaries.append(Material(group_name, group_id))
                group_surface_ids = cubit.get_group_surfaces(group_id)
                for group_surface_id in group_surface_ids:
                    self.add_geometry_to_boundary(GenericCubitInstance(group_surface_id, "surface"), group_name)
                # update last tracked group
                last_tracked_group = group_id

        #try to merge volumes in every pair of materials
        for (Material1, Material2) in pair_list:
            group_id_1 = Material1.group_id
            group_id_2 = Material2.group_id
            group_name = str(Material1.name) + "_" + str(Material2.name)
            cubit.cmd(f"merge group {group_id_1} with group {group_id_2} group_results")
            group_id = cubit.get_last_id("group")

            # if a new group is created, track the material boundary it corresponds to
            if not (group_id == last_tracked_group):
                cubit.cmd(f'group {group_id} rename "{group_name}"')
                # track internally
                self.boundaries.append(Material(group_name, group_id))
                group_surface_ids = cubit.get_group_surfaces(group_id)
                for group_surface_id in group_surface_ids:
                    self.add_geometry_to_boundary(GenericCubitInstance(group_surface_id, "surface"), group_name)
                    # update last tracked group
                last_tracked_group = group_id
        
        # track material-air boundaries

        # collect every unmerged surface because only these are in contact with air?
        cubit.cmd('group "unmerged_surfaces" add surface with is_merged=0')
        unmerged_group_id = cubit.get_id_from_name("unmerged_surfaces")
        all_unmerged_surfaces = cubit.get_group_surfaces(unmerged_group_id)
        # look at every collected material
        for material in self.materials:
            # setup group and tracking for interface with air
            boundary_name = material.name + "_air"
            cubit.cmd(f'create group "{boundary_name}"')
            boundary_id = cubit.get_last_id("group")
            self.boundaries.append(Material(boundary_name, boundary_id))
            # look at every surface of this material
            material_surface_ids = material.get_surface_ids()
            # if this surface is unmerged, it is in contact with air so add it to the boundary
            for material_surface_id in material_surface_ids:
                if material_surface_id in all_unmerged_surfaces:
                    cubit.cmd(f'group "{boundary_name}" add surface {material_surface_id}')
                    self.add_geometry_to_boundary(GenericCubitInstance(material_surface_id, "surface"), boundary_name)
                    
        cubit.cmd(f'delete group {unmerged_group_id}')

    def organise_into_groups(self):
        '''create groups for material groups and boundary groups in cubit'''

        # create material groups group
        cubit.cmd('create group "materials"')
        material_group_id = cubit.get_last_id("group") # in case i need to do something similar to boundaries later
        for material in self.materials:
            cubit.cmd(f'group "materials" add group {material.group_id}')

        # create boundary group groups
        cubit.cmd('create group "boundaries"')
        boundaries_group_id = cubit.get_last_id("group")
        for boundary in self.boundaries:
            cubit.cmd(f'group "boundaries" add group {boundary.group_id}')
        # delete empty boundaries
        for group_id in cubit.get_group_groups(boundaries_group_id):
            if cubit.get_group_surfaces(group_id) == ():
                cubit.cmd(f"delete group {group_id}")

    def print_info(self):
        '''print cubit IDs of volumes in materials and surfaces in boundaries'''
        print("Materials:")
        for material in self.materials:
            print(f"{material.name}: Volumes {[i.cid for i in from_bodies_to_volumes(material.geometries)]}")
        print("\nBoundaries:")
        for boundary in self.boundaries:
            print(f"{boundary.name}: Surfaces {[i.cid for i in boundary.geometries]}")

    def update_tracking(self, old_geometry: GenericCubitInstance, new_geometry: GenericCubitInstance, material_name: str):
        '''change reference to a geometry currently being tracked

        :param old_geometry: geometry to replace
        :type old_geometry: GenericCubitInstance
        :param new_geometry: geometry with which to replace
        :type new_geometry: GenericCubitInstance
        :param material_name: name of material geometry belongs to
        :type material_name: str
        '''
        for material in self.materials:
            if material.name == material_name:
                for geometry in material.geometries:
                    if (geometry.geometry_type == old_geometry.geometry_type) and (geometry.cid == old_geometry.cid):
                        # update internally
                        material.geometries.remove(geometry)
                        material.geometries.append(GenericCubitInstance(new_geometry.cid, new_geometry.geometry_type))
                        # update cubitside
                        cubit.cmd(f'group {material_name} remove {old_geometry.geometry_type} {old_geometry.cid}')
                        cubit.cmd(f'group {material_name} add {new_geometry.geometry_type} {new_geometry.cid}')

    def update_tracking_list(self, old_instances: list, new_instances: list, material_name: str):
        '''remove and adds references to specified GenericCubitInstances in a given material

        :param old_instances: list of GenericCubitInstances to replace
        :type old_instances: list
        :param new_instances: list of GenericCubitInstances with which to replace
        :type new_instances: list
        :param material_name: name of material geometries belong to
        :type material_name: str
        '''
        for material in self.materials:
            if material.name == material_name:
                for geometry in material.geometries:
                    for generic_cubit_instance in old_instances:
                        if isinstance(generic_cubit_instance, GenericCubitInstance):
                            if (geometry.geometry_type == generic_cubit_instance.geometry_type) and (geometry.cid == generic_cubit_instance.cid):
                                material.geometries.remove(geometry)
                                cubit.cmd(f'group {material_name} remove {generic_cubit_instance.geometry_type} {generic_cubit_instance.cid}')
                for generic_cubit_instance in new_instances:
                    if isinstance(generic_cubit_instance, GenericCubitInstance):
                        material.geometries.append(generic_cubit_instance)
                        cubit.cmd(f'group {material_name} add {generic_cubit_instance.geometry_type} {generic_cubit_instance.cid}')

    def stop_tracking_in_material(self, generic_cubit_instance: GenericCubitInstance, material_name: str):
        '''stop tracking a currently tracked geometry

        :param generic_cubit_instance: geometry to stop tracking
        :type generic_cubit_instance: GenericCubitInstance
        :param material_name: name of material geometry belongs to
        :type material_name: str
        '''
        for material in self.materials:
            if material.name == material_name:
                for geometry in material.geometries:
                    if (geometry.geometry_type == generic_cubit_instance.geometry_type) and (geometry.cid == generic_cubit_instance.cid):
                        material.geometries.remove(geometry)
                        cubit.cmd(f'group {material_name} remove {generic_cubit_instance.geometry_type} {generic_cubit_instance.cid}')

    def add_boundaries_to_sidesets(self):
        '''Add boundaries to cubit sidesets'''
        for boundary in self.boundaries:
            cubit.cmd(f"sideset {boundary.group_id} add surface {boundary.get_surface_ids()}")
            cubit.cmd(f'sideset {boundary.group_id} name "{boundary.name}"')

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
        elif self.classname in ROOM_CLASSES:
            self.add_to_subcomponents(self.__create_cubit_room(self.geometry))
        elif self.classname in WALL_CLASSES:
            self.add_to_subcomponents(self.__create_cubit_wall(self.geometry))
        else:
            raise CubismError("Wrong class name somewhere?: " + self.classname)

    def __convert_to_3d_vector(self, dim):
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
        dims= self.__convert_to_3d_vector(geometry["dimensions"])
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

    def __create_cubit_room(self, geometry: dict):
        '''create 3d room with outer dimensions dimensions (int or list) and thickness (int or list)'''
        # get variables
        outer_dims= self.__convert_to_3d_vector(geometry["dimensions"])
        thickness= self.__convert_to_3d_vector(geometry["thickness"])
        # create room
        subtract_vol = cubit.brick(outer_dims[0]-2*thickness[0], outer_dims[1]-2*thickness[1], outer_dims[2]-2*thickness[2])
        block = cubit.brick(outer_dims[0], outer_dims[1], outer_dims[2])
        room = cubit.subtract([subtract_vol], [block])
        room_id = cubit.get_last_id("volume")
        return GenericCubitInstance(room_id, "volume")

    def __create_cubit_wall(self, geometry: dict):
        # get variables
        # wall
        thickness= geometry["wall thickness"]
        plane= geometry["wall plane"] if "wall plane" in geometry.keys() else "x"
        pos= geometry["wall position"] if "wall position" in geometry.keys() else 0
        # hole
        hole_pos= geometry["wall hole position"] if "wall hole position" in geometry.keys() else [0, 0]
        hole_radius= geometry["wall hole radius"]
        # wall fills room
        room_dims= self.__convert_to_3d_vector(geometry["dimensions"])
        room_thickness= self.__convert_to_3d_vector(geometry["thickness"])
        wall_dims = [room_dims[i]-2*room_thickness[i] for i in range(3)]

        # volume to subtract to create a hole
        cubit.cmd(f"create cylinder height {thickness} radius {hole_radius}")
        subtract_vol = GenericCubitInstance(cubit.get_last_id("volume"), "volume")

        # depending on what plane the wall needs to be in, create wall + make hole at right place + move wall
        if plane == "x":
            cubit.brick(thickness, wall_dims[1], wall_dims[2])
            wall = GenericCubitInstance(cubit.get_last_id("volume"), "volume")
            cubit.cmd(f"rotate volume {subtract_vol.cid} angle 90 about Y")
            cubit.cmd(f"move volume {subtract_vol.cid} y {hole_pos[1]} z {hole_pos[0]}")
            cubit.cmd(f"subtract volume {subtract_vol.cid} from volume {wall.cid}")
            cubit.cmd(f"move volume {wall.cid} x {pos}")
        elif plane == "y":
            cubit.brick( wall_dims[0], thickness, wall_dims[2])
            wall = GenericCubitInstance(cubit.get_last_id("volume"), "volume")
            cubit.cmd(f"rotate volume {subtract_vol.cid} angle 90 about X")
            cubit.cmd(f"move volume {subtract_vol.cid} x {hole_pos[0]} z {hole_pos[1]}")
            cubit.cmd(f"subtract volume {subtract_vol.cid} from volume {wall.cid}")
            cubit.cmd(f"move volume {wall.cid} y {pos}")
        elif plane == "z":
            cubit.brick( wall_dims[0], wall_dims[1], thickness)
            wall = GenericCubitInstance(cubit.get_last_id("volume"), "volume")
            cubit.cmd(f"move volume {subtract_vol.cid} x {hole_pos[0]} y {hole_pos[1]}")
            cubit.cmd(f"subtract volume {subtract_vol.cid} from volume {wall.cid}")
            cubit.cmd(f"move volume {wall.cid} z {pos}")
        else:
            raise CubismError("unrecognised plane specified")
        
        return GenericCubitInstance(wall.cid, wall.geometry_type)            
    
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

# external component assembly and subclass(es)
class ExternalComponent(GenericCubitInstance):
    def __init__(self, cid: int, geometry_type: str) -> None:
        super().__init__(cid, geometry_type)
        # track external components
        MaterialsTracker().add_geometry_to_material(GenericCubitInstance(self.cid, self.geometry_type), "external")
        #cubit.cmd(f'group "external" add {self.geometry_type} {self.cid}')

class ExternalComponentAssembly(GenericComponentAssembly):
    '''
    Assembly to store and manage bodies imported from an external file
    requires:
    - external_filepath: path to external file relative to this python file
    - external_groupname: name of group to add external components to
    - manufacturer
    '''
    def __init__(self, external_filepath: str, external_groupname: str, manufacturer: str):
        super().__init__(classname="ExternalAssembly", setup_classnames= ["external"])
        self.group = external_groupname
        self.filepath = external_filepath
        self.manufacturer = manufacturer
        self.import_file()
        self.group_id = self.get_group_id()
        self.add_volumes_and_bodies()

    def import_file(self):
        '''Import file at specified filepath and add to specified group name'''
        # cubit imports bodies instead of volumes. why. please.

        # this imports the bodies in a temporary group
        temp_group_name = str(self.group) + "_temp"
        print(f'import "{self.filepath}" heal group "{temp_group_name}"')
        cubit.cmd(f'import "{self.filepath}" heal group "{temp_group_name}"')
        temp_group_id = cubit.get_id_from_name(temp_group_name)

        # convert everything to volumes
        volumes_list = from_bodies_to_volumes(get_bodies_and_volumes_from_group(temp_group_id))

        # add volumes to actual group
        for volume in volumes_list:
            cubit.cmd(f'group "{self.group}" add {volume.geometry_type} {volume.cid}')
        print(f"volumes imported in group {self.group}")

        # this is what you deserve
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
            self.external_components.append(ExternalComponent(volume_id, "volume"))
        source_body_ids = cubit.get_group_bodies(self.group_id)
        for body_id in source_body_ids:
            self.external_components.append(ExternalComponent(body_id, "body"))

# in case we need to do source-specific actions at some point
class SourceAssembly(ExternalComponentAssembly):
    '''Assembly of external components, created when a json object has class= source'''
    def __init__(self, external_filepath: str, external_groupname: str, manufacturer: str):
        super().__init__(external_filepath, external_groupname, manufacturer)

# functions to delete and copy lists of GenericCubitInstances
def delete_instances(component_list: list):
    '''Deletes cubit instances of all GenericCubitInstance objects in list'''
    for component in component_list:
        if isinstance(component, GenericCubitInstance):
            component.destroy_cubit_instance()

def delete_instances_of_same_type(component_list: list):
    '''similar to delete_instances. fails if all items in list aren't cubit instances or are of different geometry types'''
    if isinstance(component_list[0], GenericCubitInstance):
        component_type = component_list[0].geometry_type
        instances_to_delete = ""
        for component in component_list:
            if (isinstance(component, GenericCubitInstance)):
                if component.geometry_type == component_type:
                    instances_to_delete += " " + str(component.cid)
                else:
                    raise CubismError("All components aren't of the same type")
            else:
                raise CubismError("All components aren't cubit instances")
    else:
        raise CubismError("First element is not a cubit instance!")
    cubit.cmd(f"delete {component_type}{instances_to_delete}")

def copy_instances(component_list: list):
    '''Returns a list of copied CreatedCubitInstance objects'''
    copied_list = []
    for component in component_list:
        if isinstance(component, GenericCubitInstance):
            copied_list.append(component.copy())
        else:
            raise CubismError("All components are not instances :(")

# wrapper for cubit.union
def unionise(component_list: list):
    '''
    creates a union of all instances in given components.
    accepts list of components.
    returns GenericCubitInstance of created union.
    '''
    if len(component_list) == 0:
        raise CubismError("This is an empty list you have given me")

    # get all GenericCubitInstances from components
    instances_to_union = []
    for component in component_list:
        if isinstance(component, GenericCubitInstance):
            instances_to_union.append(component)
        elif isinstance(component, ComplexComponent):
            instances_to_union += component.subcomponents
        elif isinstance(component, GenericComponentAssembly):
            instances_to_union += component.get_all_generic_cubit_instances()
    
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

# THIS IS VERY SILLY WHY DO I HAVE TO DO THIS
def from_bodies_to_volumes(component_list: list):
    '''
    Turns references to bodies into references to their children volumes.
    Accepts list of GenericCubitInstances.
    Returns list of GenericCubitInstances.
    '''
    all_volumes_that_exist= cubit.get_entities("volume")
    return_list= []
    for component in component_list:
        if isinstance(component, GenericCubitInstance):
            if component.geometry_type == "body":
                for volume_id in all_volumes_that_exist:
                    if cubit.get_owning_body("volume", volume_id) == component.cid:
                        return_list.append(GenericCubitInstance(volume_id, "volume"))
            else:
                return_list.append(component)
        else:
            return_list.append(component)
    return return_list

def from_bodies_and_volumes_to_surfaces(component_list: list):
    '''
    Turns references to bodies and volumes into references to their children surfaces.
    Accepts list of GenericCubitInstances.
    Returns list of GenericCubitInstances.
    '''
    all_surfaces_that_exist = cubit.get_entities("surface")
    volumes_list= from_bodies_to_volumes(component_list)
    return_list = []
    for component in volumes_list:
        if isinstance(component, GenericCubitInstance):
            if component.geometry_type == "volume":
                for surface_id in all_surfaces_that_exist:
                    if cubit.get_owning_volume("surface", surface_id) == component.cid:
                        return_list.append(GenericCubitInstance(surface_id, "surface"))
            else:
                return_list.append(component)
        else:
            return_list.append(component)
    return return_list

def from_everything_to_bodies(component_list: list):
    bodies_list = []
    for component in component_list:
        if isinstance(component, GenericCubitInstance):
            if component.geometry_type == "body":
                if component.cid not in [i.cid for i in bodies_list]:
                    bodies_list.append(component)
            else:
                owning_body_id = cubit.get_owning_body(component.geometry_type, component.cid)
                if owning_body_id not in [i.cid for i in bodies_list]:
                    bodies_list.append(GenericCubitInstance(owning_body_id, "body"))
    return bodies_list

def to_owning_body(component: GenericCubitInstance):
    '''
    accepts GenericCubitInstance and returns GenericCubitInstance of owning body
    '''
    if isinstance(component, GenericCubitInstance):
        if component.cid == "body":
            return component
        else:
            return GenericCubitInstance(cubit.get_owning_body(component.geometry_type, component.cid), "body")
    raise CubismError("Did not recieve a GenericCubicInstance")

def get_bodies_and_volumes_from_group(group_id: int):
    '''Find bodies and volumes at the top-level of a group.

    :param group_id: ID of group
    :type group_id: int
    :return: list of bodies and volumes as GenericCubitInstances
    :rtype: list
    '''
    instance_list = []
    body_ids= cubit.get_group_bodies(group_id)
    for body_id in body_ids:
        instance_list.append(GenericCubitInstance(body_id, "body"))
    volume_ids= cubit.get_group_volumes(group_id)
    for volume_id in volume_ids:
        instance_list.append(GenericCubitInstance(volume_id, "volume"))
    return instance_list

def remove_overlaps_between_generic_cubit_instance_lists(from_list: list, tool_list: list):
    '''Remove overlaps between cubit instances of two lists of components'''
    from_volumes = from_bodies_to_volumes(from_list)
    tool_volumes = from_bodies_to_volumes(tool_list)
    # check each pair
    for from_volume in from_volumes:
        for tool_volume in tool_volumes:
            # if there is an overlap, remove it
            if isinstance(from_volume, GenericCubitInstance) & isinstance(tool_volume, GenericCubitInstance):
                if not (cubit.get_overlapping_volumes([from_volume.cid, tool_volume.cid]) == ()):
                    # i have given up on my python api dreams. we all return to cubit ccl in the end.
                    cubit.cmd(f"remove overlap volume {tool_volume.cid} {from_volume.cid} modify volume {from_volume.cid}")

class ComponentTracker:
    '''Adds components to cubit groups recursively'''
    # this counter is to ensure every component is named uniquely
    counter = 0

    def track_components_as_groups(self, root_component):
        # if this is an external assembly its volumes should already belong to a group, return that name
        if isinstance(root_component, ExternalComponentAssembly):
            return str(root_component.group)
        # if this is an assembly, run this function on each component of every attribute
        elif isinstance(root_component, GenericComponentAssembly):
            groupname = f"{root_component.classname}{self.counter}"
            cubit.cmd(f'create group "{groupname}"')
            self.counter += 1
            for attribute in root_component.component_mapping.values():
                for component in attribute:
                    # need this function to return the group name it adds components to
                    component_groupname = self.track_components_as_groups(component)
                    if type(groupname) == str:
                        cubit.cmd(f'group {groupname} add group {component_groupname}')
            # pass up group name
            return groupname
        # if this is a complex component, add volumes to group
        elif isinstance(root_component, ComplexComponent):
            groupname = f"{root_component.classname}{self.counter}"
            cubit.cmd(f'create group "{groupname}"')
            self.counter += 1
            for geometry in root_component.subcomponents:
                if isinstance(geometry, GenericCubitInstance):
                    cubit.cmd(f'group {groupname} add {geometry.geometry_type} {geometry.cid}')#
            # pass up group name
            return groupname

def read_file():
    '''Read in json file, construct all specified components

    :return: list of all top-level components
    :rtype: list
    '''
    with open(JSON_FILENAME) as jsonFile:
        data = jsonFile.read()
        objects = json.loads(data)
    universe = []
    for json_object in objects:
        universe.append(json_object_reader(json_object=json_object))
    return universe

if __name__ == '__coreformcubit__':
    read_file()
elif __name__ == "__main__":
    universe = read_file()
    # track all components as groups
    for component in universe:
        root_name = ComponentTracker().track_components_as_groups(component)
        print(f"components being tracked in root {root_name}")
    # track all materials and boundaries as groups
    MaterialsTracker().organise_into_groups()
    cubit.cmd('export cubit "please_work.cub5')
    # print this information if cli flag used
    if args.printinfo:
        MaterialsTracker().print_info()
    pass
#       cubit.cmd('volume all scheme auto')
#       cubit.cmd('mesh volume all')
#       cubit.cmd('export genesis "testblob.g"')
