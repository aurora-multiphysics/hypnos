import sys
sys.path.append('/opt/Coreform-Cubit-2023.8/bin')
import cubit
cubit.init(['cubit', '-nojournal'])
import json

filename = "sample_morphology.json"   
    
def object_reader(json_object: dict):
    '''set up json_object instance according to the class name provided'''
    if json_object["class"] == "complex component":
        return ComplexComponent(
            name= json_object["name"],
            material= json_object["material"],
            geometry= json_object["geometry"],
            classname= "complex"
        )
    elif json_object["class"] == "external component assembly":
        return ExternalComponentAssembly(
            name= json_object["name"],
            manufacturer= json_object["manufacturer"],
            geometry= json_object["geometry"],
            classname= "external"
        )
    elif json_object["class"] == "native component assembly":
        return NativeComponentAssembly(
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
    elif json_object["class"] == "blanket component":
        return BlanketComponent(
            name= json_object["name"],
            material= json_object["material"],
            geometry= json_object["geometry"]
        )

class NativeComponentAssembly:
    """collection of components, referenced by name"""
    def __init__(self, morphology, component_list):
        self.components = {}
        self.morphology = morphology
        self.setup_assembly(component_list)
    def add_component(self, name: str, component):
        self.components[name] = component
    def setup_assembly(self, component_list: list):
        for component_dict in component_list:
            self.add_component(component_dict["name"], object_reader(component_dict))

class StructureError(Exception):
    pass

class NeutronTestFacility:
    '''Neutron test facility assembly requiring at least one of each: room, blanket, and source'''
    def __init__(self, morphology: str, component_list:list):
        self.morphology = morphology
        self.enforced= self.enforce_structure(component_list)
        self.rooms= []
        self.sources= []
        self.blankets= []
        self.other_components= []
        self.setup_facility(component_list)
    def enforce_structure(self, comp_list: list):
        '''make sure the neutron test facility contains a room, source, and blanket'''
        class_list = [i["class"] for i in comp_list]
        if ("room" in class_list) & ("source" in class_list) & ("blanket component" in class_list): # CHANGE BLANKET COMPONENT -> BLANKET
            return True
        # Can change this to a warning, for now it just throws an error
        raise StructureError("Neutron test facility must contain a room, source, and blanket")
    def setup_facility(self, component_list: list):
        for component_dict in component_list:
            if component_dict["class"] == "room":
                self.rooms.append(object_reader(component_dict))
            elif component_dict["class"] == "source":
                self.sources.append(object_reader(component_dict))
            elif component_dict["class"] == "blanket component": # CHANGE THIS LATER
                self.blankets.append(object_reader(component_dict))
            else:
                self.other_components.append(object_reader(component_dict))

class BlanketAssembly(NativeComponentAssembly):
    pass

# everything instanced in cubit will need a name/dims/pos/euler_angles/id
class BaseCubitInstance:
    """Instance of component in cubit, referenced via cubitInstance attribute"""
    def __init__(self, name, geometry, classname):
        self.name = name
        self.classname= classname
        self.cubitInstance, self.id = self.make_geometry(geometry)
    
    def make_geometry(self, geometry: dict):
        '''abstract function to create geometry in cubit'''
        if self.classname in ["complex component", "blanket component", "source", "external"]:
            return self.__create_cubit_blob(
                dims= geometry["dimensions"],
                pos= geometry["position"],
                euler_angles= geometry["euler_angles"]
            )
        elif self.classname in ["room"]:
            return self.__create_cubit_room(
                inner_dims= geometry["dimensions"],
                thickness= geometry["thickness"]
            )
        else:
            raise StructureError("Wrong class name somewhere?: " + self.classname)
    
    def __create_cubit_blob(self, dims, pos, euler_angles):
        '''create blob with dimensions dims. Rotate it about the y-axis, x-axis, y-axis by specified angles. Move it to position pos'''
        # create cube or cuboid
        if len(dims) == 1:
            blob = cubit.brick(dims[0])
        elif len(dims) == 3:
            blob = cubit.brick(dims[0], dims[1], dims[2])
        else:
            pass
        id = cubit.get_last_id("volume")
        # orientate according to euler angles
        axis_list = ['y', 'x', 'y']
        for i in range(3): # hard-coding in 3D?
            if not euler_angles[i] == 0:
                cubit.cmd(f'rotate volume {id} angle {euler_angles[i]} about {axis_list[i]}')
        # move to specified position
        cubit.move(blob, pos)
        # return instance for further manipulation
        return blob, id

    def __create_cubit_room(self, inner_dims, thickness):
        if len(inner_dims) == 1:
            block = cubit.brick(inner_dims[0] + 2*thickness)
            subtract_vol = cubit.brick(inner_dims[0])
        elif len(inner_dims) == 3:
            pad = 2*thickness
            block = cubit.brick(inner_dims[0]+ pad, inner_dims[1]+ pad, inner_dims[2]+ pad)
        else:
            raise StructureError("dimensions should be either a 1D or 3D vector")
        room = cubit.subtract([subtract_vol], [block])
        room_id = cubit.get_last_id("volume")
        return room, room_id
    

# very basic implementations for component classes
class ComplexComponent(BaseCubitInstance):
    def __init__(self, material, name, geometry, classname):
        BaseCubitInstance.__init__(self, name, geometry, classname)
        self.material = material

class RoomComponent(ComplexComponent):
    def __init__(self, material, name, geometry):
        super().__init__(material, name, geometry, "room")


class BlanketComponent(ComplexComponent):
    def __init__(self, material, name, geometry):
        super().__init__(material, name, geometry, "blanket component")

class ExternalComponentAssembly(BaseCubitInstance):
    def __init__(self, manufacturer, name, geometry, classname):
        BaseCubitInstance.__init__(self, name, geometry, classname)
        self.manufacturer = manufacturer

class SourceComponent(ExternalComponentAssembly):
    def __init__(self, manufacturer, name, geometry):
        super().__init__(manufacturer, name, geometry, "source")

def enforce_morphology(assembly_object: NativeComponentAssembly):
    FACILITY_MORPHOLOGIES= ["exclusive", "inclusive", "overlap", "wall"]
    BLANKET_MORPHOLOGIES= []
    if assembly_object.morphology in FACILITY_MORPHOLOGIES:
        pass

with open(filename) as jsonFile:
    data = jsonFile.read()
    objects = json.loads(data)
neutronTestFacility = []
for json_object in objects:
    neutronTestFacility.append(object_reader(json_object=json_object))

cubit.cmd('export cubit "please_work.cub5')
# cubit.cmd('volume all scheme auto')
# cubit.cmd('mesh volume all')
# cubit.cmd('export genesis "testblob.g"')
