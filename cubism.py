import sys
import json

if __name__ == "__main__":
    sys.path.append('/opt/Coreform-Cubit-2023.8/bin')
    import cubit
    cubit.init(['cubit', '-nojournal'])
elif __name__ == "__coreformcubit__":
    cubit.cmd("reset")

# Files to look at
JSON_FILENAME = "sample_morphology.json"
SOURCE_FILENAME = "dummy_source.stp"

# just need os to generate filepath
import os
SOURCE_FILEPATH = os.path.join(os.getcwd(), SOURCE_FILENAME)

# components in assemblies to be generated
NEUTRON_TEST_FACILITY_REQUIREMENTS = ["room", "source", "blanket"]
NEUTRON_TEST_FACILITY_ADDITIONAL = []
BLANKET_REQUIREMENTS = ["breeder", "structure"]
BLANKET_ADDITIONAL = ["coolant"]

NEUTRON_TEST_FACLITY_ALL = NEUTRON_TEST_FACILITY_REQUIREMENTS + NEUTRON_TEST_FACILITY_ADDITIONAL
BLANKET_ALL = BLANKET_REQUIREMENTS + BLANKET_ADDITIONAL

# classes according to what make_geometry subfunction(?) needs to be called
BLOB_CLASSES = ["source", "complex", "external", "breeder", "structure"]
ROOM_CLASSES = ["room"]

# be aware: FACILITY_MORPHOLOGIES defined in enforce_facility_morphology because morphology checking is hard-coded

# map classnames to instances - there should be a better way to do this
def object_reader(json_object: dict):
    '''set up class instance according to the class name provided'''
    if json_object["class"] == "complex":
        return ComplexComponent(
            name = json_object["name"],
            material = json_object["material"],
            geometry = json_object["geometry"],
            classname = "complex"
        )
    elif json_object["class"] == "external":
        return ExternalComponentAssembly(
            name = json_object["name"],
            manufacturer = json_object["manufacturer"],
            geometry = json_object["geometry"],
            classname = "external"
        )
    elif json_object["class"] == "native component assembly":
        return CreatedComponentAssembly(
            morphology= json_object["morphology"],
            component_list= json_object["components"]
        )
    elif json_object["class"] == "neutron test facility":
        return NeutronTestFacility(
            morphology= json_object["morphology"],
            component_list= list(json_object["components"])
        )
    elif json_object["class"] == "source":
        return SourceComponent(
            name= json_object["name"],
            manufacturer= json_object["manufacturer"],
            geometry= json_object["geometry"]
        )
    elif json_object["class"] == "blanket":
        return BlanketAssembly(
            morphology= json_object["morphology"],
            component_list= json_object["components"]
        )
    elif json_object["class"] == "room":
        return RoomComponent(
            material= json_object["material"],
            name= json_object["name"],
            geometry= json_object["geometry"]
        )
    elif json_object["class"] == "breeder":
        return BreederComponent(
            material= json_object["material"],
            name= json_object["name"],
            geometry= json_object["geometry"]
        )
    elif json_object["class"] == "structure":
        return StructureComponent(
            material= json_object["material"],
            name= json_object["name"],
            geometry= json_object["geometry"]
        )

def get_cubit_geometry(geometry_id, geometry_type):
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

def setup_source():
    cubit.cmd(f"import {SOURCE_FILEPATH} heal")
    cubit.cmd("group 'source_volumes' add volume all")
    source_volume_ids = cubit.get_entities("volume")
    source_volumes = [cubit.volume(volume_id) for volume_id in source_volume_ids]


class GenericComponentAssembly:
    '''
    Generic assembly that takes a list of classnames to set up a subclass

    An assembly class specified from this will:
    - have attributes corresponding to the supplied classnames
    - store components of the specified classnames in corresponding attributes, otherwise other_components
    - be able to fetch cubit instances of components stores in these attributes (get_cubit_instances)
    '''
    def __init__(self, setup_classnames: list):
        # this defines what attributes are set up
        self.setup_classnames = setup_classnames

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
        '''get every cubit instance stored in this instance recursively'''
        instances_list = []
        for component_attribute in self.component_mapping.values():
            for component in component_attribute:
                if isinstance(component, CreatedCubitInstance):
                    instances_list.append(component.cubitInstance)
                elif isinstance(component, CreatedComponentAssembly):
                    instances_list += component.get_all_cubit_instances()

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
        '''make sure the instance contains the required components'''
        class_list = [i["class"] for i in comp_list]
        for classes_required in self.required_classnames:
            if classes_required not in class_list:
                # Can change this to a warning, for now it just throws an error
                raise CubismError(f"This assembly must contain: {self.required_classnames}. Currently contains: {class_list}")
        return True
    
    def setup_facility(self, component_list: list):
        '''adds components to lists in the appropriate attributes'''
        for component_dict in component_list:
            # if you are looking for the class-attribute mapping it is the component_mapping dict in __init__
            if component_dict["class"] in self.component_mapping.keys():
                self.component_mapping[component_dict["class"]].append(object_reader(component_dict))
            else:
                self.other_components.append(object_reader(component_dict))

class CubismError(Exception):
    pass

class NeutronTestFacility(CreatedComponentAssembly):
    '''Assmebly class that requires at least one source, blanket, and room'''
    def __init__(self, morphology: str, component_list: list):
        super().__init__(morphology, component_list, required_classnames = NEUTRON_TEST_FACILITY_REQUIREMENTS, additional_classnames = NEUTRON_TEST_FACILITY_ADDITIONAL)

class BlanketAssembly(CreatedComponentAssembly):
    '''Assembly class that requires at least one breeder and structure. Additionally stores coolants separately'''
    def __init__(self, morphology: str, component_list: list, required_classnames = BLANKET_REQUIREMENTS, additional_classnames = BLANKET_ADDITIONAL):
        super().__init__(morphology, component_list, required_classnames, additional_classnames)

# everything in cubit will need to be referenced by a geometry type and id
class GenericCubitInstance:
    '''Wrapper for generic cubit geometry'''
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

# every blob/room instanced in cubit will need a name/classname/geometry specification/handle
class CreatedCubitInstance(GenericCubitInstance):
    """Instance of component created in cubit, cubitside referenced via cubitInstance attribute"""
    def __init__(self, name, geometry, classname) -> None:       
        self.name = name
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


# very basic implementations for component classes

# complex component and subclasses
class ComplexComponent(CreatedCubitInstance):
    def __init__(self, material, name, geometry, classname):
        CreatedCubitInstance.__init__(self, name, geometry, classname)
        self.material = material
        cubit.cmd(f'group "{self.material}" add {self.geometry_type} {self.cid}')

class RoomComponent(ComplexComponent):
    def __init__(self, material, name, geometry):
        super().__init__(material, name, geometry, "room")

class BreederComponent(ComplexComponent):
    def __init__(self, material, name, geometry):
        super().__init__(material, name, geometry, "breeder")

class StructureComponent(ComplexComponent):
    def __init__(self, material, name, geometry):
        super().__init__(material, name, geometry, "structure")

# external component and subclasses
class ExternalComponentAssembly(CreatedCubitInstance):
    def __init__(self, manufacturer, name, geometry, classname):
        CreatedCubitInstance.__init__(self, name, geometry, classname)
        self.manufacturer = manufacturer

class SourceComponent(ExternalComponentAssembly):
    def __init__(self, manufacturer, name, geometry):
        super().__init__(manufacturer, name, geometry, "source")

# functions to delete and copy lists of instances
def delete_instances(component_list: list):
    '''Deletes cubit instances of all CreatedCubitInstance objects in list'''
    for component in component_list:
        if isinstance(component, CreatedCubitInstance):
            component.destroy_cubit_instance()

def delete_instances_of_same_type(component_list: list):
    '''similar to delete_instances. fails if all items in list aren't cubit instances or are of different geometry types'''
    if isinstance(component_list[0], CreatedCubitInstance):
        component_type = component_list[0].geometry_type
        instances_to_delete = ""
        for component in component_list:
            if (isinstance(component, CreatedCubitInstance)):
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
        if isinstance(component, CreatedCubitInstance):
            copied_list.append(component.copy())
        else:
            raise CubismError("All components are not instances :(")

def unionise(component_list: list):
    for component in component_list:
        if isinstance(component, CreatedCubitInstance):
            pass


def enforce_facility_morphology(facility: NeutronTestFacility):
    '''
    checks for expected overlaps between source and blanket objects
    these expectations are set by the morphology specified
    currently only checks for first source and blanket created

    :param NeutronTestFacility() facility: The facility to check
    :return: True or raise exception
    '''
    FACILITY_MORPHOLOGIES= ["exclusive", "inclusive", "overlap", "wall"]
    if facility.morphology in FACILITY_MORPHOLOGIES:

        # set up copies so we do not disturb the actual geometry
        testing_source = copy_instances(facility.get_cubit_instances_from_classname("source"))
        testing_blanket = copy_instances(facility.get_cubit_instances_from_classname("blanket", BLANKET_ALL))

        # EVERYTHING FROM HERE SHOULD CURRENTLY BE BROKEN
        union_object = cubit.unite([testing_blanket, testing_source])[0]

        # ids needed for cleanup
        union_id = cubit.get_last_id("volume")
        union_body_id = cubit.get_last_id("body")

        # this works by checking source+blanket volumes against the volume of their union
        source_volume = facility.source_components[0].cubitInstance.volume()
        blanket_volume = facility.blanket_components[0].cubitInstance.volume()
        union_volume = union_object.volume()

        # different enforcing depending on the morphology specified
        # also cleanup because cubit.union makes a Body instead of a Volume for exclusive volumes
        if union_volume == blanket_volume:
            if facility.morphology == "inclusive":
                cubit.cmd(f"del vol {union_id}")
                return True
            else:
                raise CubismError("Source not completely enclosed")
        elif union_volume == blanket_volume + source_volume:
            if facility.morphology == "exclusive":
                cubit.cmd(f"del body {union_body_id}")
                return True
            else:
                raise CubismError("Source not completely outside blanket")
        elif union_volume < blanket_volume + source_volume:
            if facility.morphology == "overlap":
                cubit.cmd(f"del vol {union_id}")
                return True
            else:
                raise CubismError("Source and blanket not partially overlapping")
        else:
            raise CubismError("Something has gone very wrong")

# maybe i should add this to main()
with open(JSON_FILENAME) as jsonFile:
    data = jsonFile.read()
    objects = json.loads(data)
neutronTestFacility = []
for json_object in objects:
    neutronTestFacility.append(object_reader(json_object=json_object))
    if json_object["class"] == "neutron test facility":
        #print("morphology enforced? ", enforce_facility_morphology(neutronTestFacility[-1]))
        pass
if __name__ == "__main__":
    #cubit.cmd('export cubit "please_work.cub5')
    pass
#       cubit.cmd('volume all scheme auto')
#       cubit.cmd('mesh volume all')
#       cubit.cmd('export genesis "testblob.g"')
