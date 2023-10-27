import sys
sys.path.append('/opt/Coreform-Cubit-2023.8/bin')
import cubit
cubit.init(['cubit', '-nojournal'])
import json

filename = "sample_input.json"

    
def object_reader(object: dict):
    '''set up object instance according to the class name provided'''
    if object["class"] == "complex component":
        return ComplexComponent(
            name= object["name"],
            material= object["material"],
            dimensions= object["dimensions"],
            position= object["position"],
            euler_angles= object["euler_angles"]
        )
    elif object["class"] == "external component assembly":
        return ExternalComponentAssembly(
            name= object["name"],
            manufacturer= object["manufacturer"],
            dimensions= object["dimensions"],
            position= object["position"],
            euler_angles= object["euler_angles"]
        )

class NativeComponentAssembly:
    """collection of components, referenced by name"""
    def __init__(self):
        self.assemblyDict = {}
        self.morphology = ""
    def add_component(self, name: str, component):
        self.assemblyDict[name] = component

# everything instanced in cubit will need a name/dims/pos/euler_angles/id
class BaseCubitInstance:
    """Instance of component in cubit, referenced via cubitInstance attribute"""
    def __init__(self, name, dimensions, position, euler_angles):
        self.name = name
        self.cubitInstance, self.id = create_cubit_blob(dimensions, position, euler_angles)


# very basic implementations for component classes
class ComplexComponent(BaseCubitInstance):
    def __init__(self, material, name, dimensions, position, euler_angles):
        BaseCubitInstance.__init__(self, name, dimensions, position, euler_angles)
        self.material = material

class ExternalComponentAssembly(BaseCubitInstance):
    def __init__(self, manufacturer, name, dimensions, position, euler_angles):
        BaseCubitInstance.__init__(self, name, dimensions, position, euler_angles)
        self.manufacturer = manufacturer

def create_cubit_blob(dims, pos, euler_angles):
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



with open(filename) as jsonFile:
    data = jsonFile.read()
    objects = json.loads(data)
neutronTestFacility = NativeComponentAssembly()
for object in objects:
    neutronTestFacility.add_component(object["name"], object_reader(object))

cubit.cmd('volume all scheme auto')
cubit.cmd('mesh volume all')
cubit.cmd('export genesis "testblob.g"')
