import sys
import json

# if this is run as a python file, import cubit
if __name__ == "__main__":
    sys.path.append('/opt/Coreform-Cubit-2023.8/bin')
    import cubit
    cubit.init(['cubit', '-nojournal'])
# if this is cubit, reset
elif __name__ == "__coreformcubit__":
    cubit.cmd("reset")

# File to look at
JSON_FILENAME = "sample_morphology.json"

# components in assemblies to be generated
NEUTRON_TEST_FACILITY_REQUIREMENTS = ["room", "source", "blanket"]
NEUTRON_TEST_FACILITY_ADDITIONAL = []
BLANKET_REQUIREMENTS = ["breeder", "structure"]
BLANKET_ADDITIONAL = ["coolant"]

NEUTRON_TEST_FACLITY_ALL = NEUTRON_TEST_FACILITY_REQUIREMENTS + NEUTRON_TEST_FACILITY_ADDITIONAL
BLANKET_ALL = BLANKET_REQUIREMENTS + BLANKET_ADDITIONAL

# classes according to what make_geometry subfunction(?) needs to be called
BLOB_CLASSES = ["complex", "breeder", "structure"]
ROOM_CLASSES = ["room"]

# currently only supports exclusive, inclusive, and overlap
FACILITY_MORPHOLOGIES= ["exclusive", "inclusive", "overlap", "wall"]

# raise this when bad things happen
class CubismError(Exception):
    pass

# map classnames to instances - there should be a better way to do this?
def json_object_reader(json_object: dict):
    '''set up class instance according to the class name provided'''
    if json_object["class"] == "complex":
        return ComplexComponent(
            geometry = json_object["geometry"],
            classname = "complex",
            material = json_object["material"]
        )
    elif json_object["class"] == "external":
        return ExternalComponentAssembly(
            external_filepath= json_object["filepath"],
            external_groupname= json_object["group"],
            manufacturer = json_object["manufacturer"],
        )
    elif json_object["class"] == "source":
        return SourceAssembly(
            external_filepath= json_object["filepath"],
            external_groupname= json_object["group"],
            manufacturer = json_object["manufacturer"],
        )
    elif json_object["class"] == "neutron test facility":
        return NeutronTestFacility(
            morphology= json_object["morphology"],
            component_list= list(json_object["components"])
        )
    elif json_object["class"] == "blanket":
        return BlanketAssembly(
            morphology= json_object["morphology"],
            component_list= json_object["components"]
        )
    elif json_object["class"] == "room":
        return RoomComponent(
            geometry= json_object["geometry"],
            material= json_object["material"]
        )
    elif json_object["class"] == "breeder":
        return BreederComponent(
            geometry= json_object["geometry"],
            material= json_object["material"]
        )
    elif json_object["class"] == "structure":
        return StructureComponent(
            geometry= json_object["geometry"],
            material= json_object["material"]
        )

# make finding instances less annoying
def get_cubit_geometry(geometry_id, geometry_type):
    '''returns cubit instance given id and geometry type'''
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
    Generic assembly that takes a list of classnames to set up a subclass

    An assembly class specified from this will:
    - have attributes corresponding to the supplied classnames
    - store components of the specified classnames in corresponding attributes, otherwise other_components
    - be able to fetch cubit instances of components stores in these attributes (get_cubit_instances)
    '''
    def __init__(self, setup_classnames: list):
        # component_mapping defines what classes get stored in what attributes (other_components is default)
        self.other_components = []
        self.component_mapping = {"other": self.other_components}

        # set up attributes and component_mapping for specified components
        for classname in setup_classnames:
            component_name = classname + "_components"
            self.__setattr__(component_name, [])
            self.component_mapping[classname] = self.__getattribute__(component_name)

    def get_cubit_instances_from_classname(self, classname_list: list):
        '''returns list of cubit instances of specified classnames'''
        instances_list = []
        for component_classname in classname_list:
            # checks if valid classname
            if component_classname in self.component_mapping.keys():
                for component in self.component_mapping[component_classname]:
                    # fetches instances
                    if isinstance(component, GenericCubitInstance):
                        instances_list.append(component.cubitInstance)
                    elif isinstance(component, GenericComponentAssembly):
                        # This feels very scuffed
                        instances_list += component.get_cubit_instances_from_classname(classname_list)
        return instances_list
    
    def get_all_cubit_instances(self) -> list:
        '''get every cubit instance stored in this assembly instance recursively'''
        instances_list = []
        for component_attribute in self.component_mapping.values():
            for component in component_attribute:
                if isinstance(component, GenericCubitInstance):
                    instances_list.append(component.cubitInstance)
                elif isinstance(component, GenericComponentAssembly):
                    instances_list += component.get_all_cubit_instances()
        return instances_list

    def get_generic_cubit_instances_from_classname(self, classname_list: list) -> list:
        component_list = []
        for classname in classname_list:
            if classname in self.component_mapping.keys():
                for component in self.component_mapping[classname]:
                    if isinstance(component, GenericCubitInstance):
                        component_list.append(component)
                    elif isinstance(component, GenericComponentAssembly):
                        component_list += component.get_generic_cubit_instances_from_classname(classname_list)
        return component_list
    
    def get_all_generic_cubit_instances(self) -> list:
        '''get every cubit instance stored in this assembly instance recursively'''
        instances_list = []
        for component_attribute in self.component_mapping.values():
            for component in component_attribute:
                if isinstance(component, GenericCubitInstance):
                    instances_list.append(component)
                elif isinstance(component, GenericComponentAssembly):
                    instances_list += component.get_all_generic_cubit_instances()
        return instances_list


class CreatedComponentAssembly(GenericComponentAssembly):
    '''
    Assembly to handle components created natively. Takes a list of required and additional classnames to set up a specific assembly
    - required classnames: instantiating will fail without at least one component of the given classnames
    - additional classnames: defines attributes to store components with this classname

    An assembly class specified from this will:
    - have attributes corresponding to the supplied classnames
    - require every instance have at least one component from the required classnames
    - store components of the specified classnames in corresponding attributes, otherwise other_components
    - be able to fetch cubit instances of components stores in these attributes (get_cubit_instances)
    '''
    def __init__(self, morphology: str, component_list: list, required_classnames: list, additional_classnames: list):
        # this defines what morphology will be enforced later
        self.morphology = morphology
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
        self.setup_facility(component_list)

    def enforce_structure(self, comp_list: list):
        '''Make sure the instance contains the required components. This looks at the classes specified in the json file'''
        class_list = [i["class"] for i in comp_list]
        for classes_required in self.required_classnames:
            if classes_required not in class_list:
                # Can change this to a warning, for now it just throws an error
                raise CubismError(f"This assembly must contain: {self.required_classnames}. Currently contains: {class_list}")
        return True
    
    def setup_facility(self, component_list: list):
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
    Currently supports inclusive, exclusive, and overlap morphologies
    '''
    def __init__(self, morphology: str, component_list: list):
        super().__init__(morphology, component_list, required_classnames = NEUTRON_TEST_FACILITY_REQUIREMENTS, additional_classnames = NEUTRON_TEST_FACILITY_ADDITIONAL)
        self.enforce_facility_morphology()
        self.apply_facility_morphology()
        self.imprint()
        self.track_material_boundaries_and_merge()

    def enforce_facility_morphology(self):
        '''Make sure the specified morphology is followed. This works by comparing the volumes of the source and blanket to the volume of their union'''

        if self.morphology not in FACILITY_MORPHOLOGIES:
            raise CubismError(f"Morphology not supported by this facility: {self.morphology}")
        
        # Get the net source, blanket, and the union of both
        source_object= unionise(self.source_components)
        blanket_object= unionise(self.blanket_components)
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
        '''If the morphology is inclusive/overlap, apply it'''
        if self.morphology in ["inclusive", "overlap"]:
            # convert everything to volumes in case of stray bodies
            source_volumes = from_bodies_to_volumes(self.get_generic_cubit_instances_from_classname(["source", "external"]))
            blanket_volumes = from_bodies_to_volumes(self.get_generic_cubit_instances_from_classname(["blanket", "breeder", "structure", "coolant"]))
            # if there is an overlap, remove it
            for source_volume in source_volumes:
                for blanket_volume in blanket_volumes:
                    if isinstance(source_volume, GenericCubitInstance) & isinstance(blanket_volume, GenericCubitInstance):
                        if not (cubit.get_overlapping_volumes([source_volume.cid, blanket_volume.cid]) == ()):
                            # i have given up on my python api dreams. we all return to cubit ccl in the end.
                            cubit.cmd(f"remove overlap volume {source_volume.cid} {blanket_volume.cid} modify volume {blanket_volume.cid}")
            print(f"{self.morphology} morphology applied")

    def imprint(self):
        '''imprint volume all :)'''
        cubit.cmd("imprint volume all")
    
    def track_material_boundaries_and_merge(self):
        materials = MaterialsTracker()
        materials.merge_and_track_boundaries()
        cubit.cmd("merge volume all")
    
    def track_material_boundaries(self):
        cubit.cmd('group "merged_surfaces" add surface with is_merged')

class BlanketAssembly(CreatedComponentAssembly):
    '''Assembly class that requires at least one breeder and structure. Additionally stores coolants separately'''
    def __init__(self, morphology: str, component_list: list, required_classnames = BLANKET_REQUIREMENTS, additional_classnames = BLANKET_ADDITIONAL):
        super().__init__(morphology, component_list, required_classnames, additional_classnames)

# everything in cubit will need to be referenced by a geometry type and id
class GenericCubitInstance:
    '''
    Wrapper for cubit geometry entity.
    Can access cubit ID (cid), geometry type, and cubit handle (cubitInstance).
    Can destroy cubit instance. Can copy itself (and thus also the cubit instance it refers to)
    '''
    def __init__(self, cid: int, geometry_type: str) -> None:
        self.cid = cid
        self.geometry_type = geometry_type
        self.cubitInstance = get_cubit_geometry(self.cid, self.geometry_type)
    
    def destroy_cubit_instance(self):
        cubit.cmd(f"delete {self.geometry_type} {self.cid}")
    
    def copy_cubit_instance(self):
        cubit.cmd(f"{self.geometry_type} {self.cid} copy")
        copied_id = cubit.get_last_id(self.geometry_type)
        return GenericCubitInstance(copied_id, self.geometry_type)

# every blob/room instanced in cubit will need a name/ classname/ geometry specification/ handle
class CreatedCubitInstance(GenericCubitInstance):
    """Instance of component created in cubit"""
    def __init__(self, geometry, classname) -> None:       
        self.classname= classname
        self.geometry = geometry
        self.make_cubit_instance()
    
    def make_geometry(self, geometry: dict):
        '''create geometry in cubit. if the class is a blob, make a blob. if the class is a room, make a room. otherwise break.'''
        if self.classname in BLOB_CLASSES:
            return self.__create_cubit_blob(geometry)
        elif self.classname in ROOM_CLASSES:
            return self.__create_cubit_room(geometry)
        else:
            raise CubismError("Wrong class name somewhere?: " + self.classname)
    
    def make_cubit_instance(self):
            self.cubitInstance, self.cid, self.geometry_type= self.make_geometry(self.geometry)
    
    def copy(self):
        return CreatedCubitInstance(self.name + "_copy", self.geometry, self.classname)

    def __create_cubit_blob(self, geometry: dict):
        '''create cube (if scalar/1D) or cuboid (if 3D) with dimensions. 
        Rotate it about the y-axis, x-axis, y-axis if euler_angles are specified. 
        Move it to position if specified'''
        # setup variables
        dims= geometry["dimensions"]
        pos= geometry["position"] if "position" in geometry.keys() else [0, 0, 0]
        euler_angles= geometry["euler_angles"] if "euler_angles" in geometry.keys() else [0, 0, 0]
        # create a cube or cuboid.
        if type(dims) == int:
            dims = [dims for i in range(3)]
        elif len(dims) == 1:
            dims = [dims[0] for i in range(3)]
        elif len(dims) == 3:
            pass
        else:
            raise CubismError("dimensions should be either a 1D or 3D vector (or scalar)")
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
        return blob, cid, "volume"

    def __create_cubit_room(self, geometry: dict):
        '''create 3d room with inner dimensions dimensions (int or list) and thickness (int or list)'''
        inner_dims= geometry["dimensions"]
        thickness= geometry["thickness"]
        # create a cube or cuboid.
        if type(inner_dims) == int:
            inner_dims = [inner_dims, inner_dims, inner_dims]
        elif len(inner_dims) == 1:
            inner_dims = [inner_dims[0], inner_dims[0], inner_dims[0]]
        elif len(inner_dims) == 3:
            pass
        else:
            raise CubismError("dimensions should be either a 1D or 3D vector (or scalar)")
        if type(thickness) == int:
            thickness = [thickness, thickness, thickness]
        elif len(thickness) == 1:
            thickness = [thickness[0], thickness[0], thickness[0]]
        elif len(thickness) == 3:
            pass
        else:
            raise CubismError("thickness should be either a 1D or 3D vector (or scalar)")
        block = cubit.brick(inner_dims[0]+2*thickness[0], inner_dims[1]+2*thickness[1], inner_dims[2]+2*thickness[2])
        subtract_vol = cubit.brick(inner_dims[0], inner_dims[1], inner_dims[2])
        room = cubit.subtract([subtract_vol], [block])
        room_id = cubit.get_last_id("volume")
        return room, room_id, "volume"

# Classes to track materials and components made of those materials
class Material:
    def __init__(self, name, group_id) -> None:
        self.name = name
        self.components = []
        self.state_of_matter = ""
        self.group_id = group_id
    
    def add_component(self, component):
        if isinstance(component, GenericCubitInstance):
            self.components.append(component)
        else:
            raise CubismError("Not a GenericCubitInstance???")
    
    def change_state(self, state: str):
        self.state_of_matter = state
    
    def get_surface_ids(self):
        return [i.cid for i in from_bodies_and_volumes_to_surfaces(self.components)]

class MaterialsTracker:
    #i think i want materials to be tracked globally
    materials = []
    boundaries = []

    def make_material(self, material_name: str, group_id: int):
        '''Add material to internal list. Will not add if material name already exists'''
        if material_name not in [i.name for i in self.materials]:
            self.materials.append(Material(material_name, group_id))
    
    def add_component_to_material(self, component: GenericCubitInstance, material_name: str):
        '''Add cubit instance to group= material name and track internally'''
        cubit.cmd(f'group "{material_name}" add {component.geometry_type} {component.cid}')
        group_id = cubit.get_id_from_name(material_name)
        self.make_material(material_name, group_id)

        # Add component to appropriate material. If it can't something has gone wrong
        for material in self.materials:
            if material.name == material_name:
                material.add_component(component)
                return True
        return CubismError("Could not add component")

    def contains_material(self, material_name):
        '''Checks for existence of a material with the given name'''
        return True if material_name in [i.name for i in self.materials] else False
    
    def sort_materials_into_pairs(self):
        '''Returns a list with all combinations of pairs of materials, including with themselves (not all permutations)'''
        pair_list = []
        # this is my scuffed way of doing this
        min_counter = -1
        for i in range(len(self.materials)):
            for j in range(len(self.materials)):
                if j > min_counter:
                    pair_list.append((self.materials[i], self.materials[j]))
            min_counter+=1
        return pair_list
    
    def get_boundary_ids(self, boundary_name: str):
        for boundary in self.boundaries:
            if boundary.name == boundary_name:
                return [component.cid for component in boundary.components]
        raise CubismError("Could not find boundary")
    
    def add_geometry_to_boundary(self, geometry: GenericCubitInstance, boundary_name: str):
        for boundary in self.boundaries:
            if boundary.name == boundary_name:
                boundary.add_component(geometry)
                return True
        raise CubismError("Could not find boundary")
    
    def merge_and_track_boundaries(self):
        '''tries to merge every possible pair of materials, and tracks the resultant material boundaries (if any).'''
        pair_list = self.sort_materials_into_pairs()
        # to check if merging has actually happened 
        last_tracked_group = cubit.get_last_id("group")

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
                self.boundaries.append(Material(group_name, group_id))
                group_surface_ids = cubit.get_group_surfaces(group_id)
                for group_surface_id in group_surface_ids:
                    self.add_geometry_to_boundary(GenericCubitInstance(group_surface_id, "surface"), group_name)
                last_tracked_group = group_id
        
        cubit.cmd('group "unmerged_surfaces" add surface with is_merged=0')
        unmerged_group_id = cubit.get_id_from_name("unmerged_surfaces")
        all_unmerged_surfaces = cubit.get_group_surfaces(unmerged_group_id)
        for material in self.materials:
            boundary_name = material.name + "_air"
            cubit.cmd(f'group "{boundary_name}"')
            boundary_id = cubit.get_last_id("group")
            self.boundaries.append(Material(boundary_name, boundary_id))
            material_surface_ids = material.get_surface_ids()
            for material_surface_id in material_surface_ids:
                if material_surface_id in all_unmerged_surfaces:
                    cubit.cmd(f'group "{boundary_name}" add surface {material_surface_id}')
                    self.add_geometry_to_boundary(GenericCubitInstance(material_surface_id, "surface"), boundary_name)
                    
        cubit.cmd(f'delete group {unmerged_group_id}')

    def print_info(self):
        print("Materials:")
        for material in self.materials:
            print(f"{material.name}: Volumes {[i.cid for i in from_bodies_to_volumes(material.components)]}")
        print("\nBoundaries:")
        for boundary in self.boundaries:
            print(f"{boundary.name}: Surfaces {[i.cid for i in boundary.components]}")


# very basic implementations for component classes created natively
class ComplexComponent(CreatedCubitInstance):
    # stores information about what materials exist. geometries can then be found from groups with the same name
    complexComponentMaterials = MaterialsTracker()
    def __init__(self, geometry, classname, material):
        CreatedCubitInstance.__init__(self= self, geometry= geometry, classname= classname)
        self.material = material
        # add geometry to material tracker
        self.complexComponentMaterials.add_component_to_material(GenericCubitInstance(self.cid, self.geometry_type), self.material)

class RoomComponent(ComplexComponent):
    def __init__(self, geometry, material):
        super().__init__(geometry, "room", material)

class BreederComponent(ComplexComponent):
    def __init__(self, geometry, material):
        super().__init__(geometry, "breeder", material)

class StructureComponent(ComplexComponent):
    def __init__(self, geometry, material):
        super().__init__(geometry, "structure", material)

# external component assembly and subclass(es)
class ExternalComponent(GenericCubitInstance):
    def __init__(self, cid: int, geometry_type: str) -> None:
        super().__init__(cid, geometry_type)
        # track external components
        cubit.cmd(f'group "external" add {self.geometry_type} {self.cid}')

class ExternalComponentAssembly(GenericComponentAssembly):
    '''
    Assembly to store and manage bodies imported from an external file
    requires:
    - external_filepath: path to external file relative to this python file
    - external_groupname: name of group to add external components to
    - manufacturer
    '''
    def __init__(self, external_filepath: str, external_groupname: str, manufacturer: str):
        super().__init__(setup_classnames= ["external"])
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
        elif isinstance(component, GenericComponentAssembly):
            instances_to_union += component.get_all_generic_cubit_instances()
    
    # convert to bodies :(
    instances_to_union = from_everything_to_bodies(instances_to_union)
    instances_to_union = [i.cubitInstance for i in instances_to_union]

    # check whether a union is possible
    if len(instances_to_union) == 0:
        raise CubismError("Could not find any instances")
    elif len(instances_to_union) == 1:
        return instances_to_union[0].copy()
    
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
    instance_list = []
    body_ids= cubit.get_group_bodies(group_id)
    for body_id in body_ids:
        instance_list.append(GenericCubitInstance(body_id, "body"))
    volume_ids= cubit.get_group_volumes(group_id)
    for volume_id in volume_ids:
        instance_list.append(GenericCubitInstance(volume_id, "volume"))
    return instance_list

def remove_overlaps_between_component_lists(from_list: list, tool_list: list):
    '''Remove overlaps between cubit instances of two lists of components'''
    from_volumes = from_bodies_to_volumes(from_list)
    tool_volumes = from_bodies_to_volumes(tool_list)
    for from_volume in from_volumes:
        for tool_volume in tool_volumes:
            if isinstance(from_volume, GenericCubitInstance) & isinstance(tool_volume, GenericCubitInstance):
                if not (cubit.get_overlapping_volumes([from_volume.cid, tool_volume.cid]) == ()):
                    # i have given up on my python api dreams. we all return to cubit ccl in the end.
                    cubit.cmd(f"remove overlap volume {tool_volume.cid} {from_volume.cid} modify volume {from_volume.cid}")

# maybe i should add this to main()
with open(JSON_FILENAME) as jsonFile:
    data = jsonFile.read()
    objects = json.loads(data)
universe = []
for json_object in objects:
    universe.append(json_object_reader(json_object=json_object))

if __name__ == "__main__":
    MaterialsTracker().print_info()
    #cubit.cmd('export cubit "please_work.cub5')
    pass
#       cubit.cmd('volume all scheme auto')
#       cubit.cmd('mesh volume all')
#       cubit.cmd('export genesis "testblob.g"')
