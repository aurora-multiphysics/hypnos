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
            dimensions= json_object["dimensions"],
            position= json_object["position"],
            euler_angles= json_object["euler_angles"]
        )
    elif json_object["class"] == "external component assembly":
        return ExternalComponentAssembly(
            name= json_object["name"],
            manufacturer= json_object["manufacturer"],
            dimensions= json_object["dimensions"],
            position= json_object["position"],
            euler_angles= json_object["euler_angles"]
        )
    elif json_object["class"] == "native component assembly":
        return NativeComponentAssembly(
            morphology= json_object["morphology"],
            component_list= json_object["components"]
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



# everything instanced in cubit will need a name/dims/pos/euler_angles/id
class BaseCubitInstance:
    """Instance of component in cubit, referenced via cubitInstance attribute"""
    def __init__(self, name, dimensions, position, euler_angles):
        self.name = name
        self.cubitInstance, self.id = make_geometry((dimensions, position, euler_angles))


# very basic implementations for component classes
class ComplexComponent(BaseCubitInstance):
    def __init__(self, material, name, dimensions, position, euler_angles):
        BaseCubitInstance.__init__(self, name, dimensions, position, euler_angles)
        self.material = material

class ExternalComponentAssembly(BaseCubitInstance):
    def __init__(self, manufacturer, name, dimensions, position, euler_angles):
        BaseCubitInstance.__init__(self, name, dimensions, position, euler_angles)
        self.manufacturer = manufacturer

def __create_cubit_blob(dims, pos, euler_angles):
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

def make_geometry(params):
    return __create_cubit_blob(params[0], params[1], params[2])
    

with open(filename) as jsonFile:
    data = jsonFile.read()
    objects = json.loads(data)
neutronTestFacility = []
for json_object in objects:
    neutronTestFacility.append(object_reader(json_object=json_object))

cubit.cmd('volume all scheme auto')
cubit.cmd('mesh volume all')
cubit.cmd('export genesis "testblob.g"')
