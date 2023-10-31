if __name__ == "main":
    sys.path.append('/opt/Coreform-Cubit-2023.8/bin')
    import cubit
    cubit.init(['cubit', '-nojournal'])
elif __name__ == "__coreformcubit":
    cubit.cmd("reset")

import sys
import json

filename = "sample_morphology.json"

def object_reader(json_object: dict):
    '''set up class instance according to the class name provided'''
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
        # instance storage
        self.rooms= []
        self.sources= []
        self.blankets= []
        self.other_components= []
        # store instances
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
    # doesnt do anything yet
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
        # if the class is a room, make a room. otherwise make a blob.
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
        '''create room with inner dimensions inner_dims and thickness'''
        # create a cube or cuboid.
        if type(inner_dims) == int:
            inner_dims = [inner_dims, inner_dims, inner_dims]
        elif len(inner_dims) == 1:
            inner_dims = [inner_dims[0], inner_dims[0], inner_dims[0]]
        elif len(inner_dims) == 3:
            pass
        else:
            raise StructureError("dimensions should be either a 1D or 3D vector (or scalar)")
        if type(thickness) == int:
            thickness = [thickness, thickness, thickness]
        elif len(thickness) == 1:
            thickness = [thickness[0], thickness[0], thickness[0]]
        elif len(thickness) == 3:
            pass
        else:
            raise StructureError("thickness should be either a 1D or 3D vector (or scalar)")
        block = cubit.brick(inner_dims[0]+2*thickness[0], inner_dims[1]+2*thickness[1], inner_dims[2]+2*thickness[2])
        subtract_vol = cubit.brick(inner_dims[0], inner_dims[1], inner_dims[2])
        room = cubit.subtract([subtract_vol], [block])
        room_id = cubit.get_last_id("volume")
        return room, room_id
    

# very basic implementations for component classes
class ComplexComponent(BaseCubitInstance):
    def __init__(self, material, name, geometry, classname):
        BaseCubitInstance.__init__(self, name, geometry, classname)
        self.material = material
        cubit.cmd(f'group "{self.material}" add volume {self.id}')

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

def enforce_facility_morphology(facility: NeutronTestFacility):
    '''checks for expected overlaps between source and blanket objects
    currently only checks for first source and blanket created
    '''
    FACILITY_MORPHOLOGIES= ["exclusive", "inclusive", "overlap", "wall"]
    if facility.morphology in FACILITY_MORPHOLOGIES:
        source_volume = facility.sources[0].cubitInstance.volume()
        testing_source = cubit.copy_body(facility.sources[0].cubitInstance)
        blanket_volume = facility.blankets[0].cubitInstance.volume()
        testing_blanket = cubit.copy_body(facility.blankets[0].cubitInstance)
        union_object = cubit.unite([testing_blanket, testing_source])[0]
        union_id = cubit.get_last_id("volume")
        union_body_id = cubit.get_last_id("body")
        union_volume = union_object.volume()
        if union_volume == blanket_volume:
            if facility.morphology == "inclusive":
                cubit.cmd(f"del vol {union_id}")
                return True
            else:
                raise StructureError("Source not completely enclosed")
        elif union_volume == blanket_volume + source_volume:
            if facility.morphology == "exclusive":
                cubit.cmd(f"del body {union_body_id}")
                return True
            else:
                raise StructureError("Source not completely outside blanket")
        elif union_volume < blanket_volume + source_volume:
            if facility.morphology == "overlap":
                cubit.cmd(f"del vol {union_id}")
                return True
            else:
                raise StructureError("Source and blanket not partially overlapping")
        else:
            raise StructureError("Something has gone very wrong")
with open(filename) as jsonFile:
    data = jsonFile.read()
    objects = json.loads(data)
neutronTestFacility = []
for json_object in objects:
    neutronTestFacility.append(object_reader(json_object=json_object))
    if json_object["class"] == "neutron test facility":
        print("morphology enforced? ", enforce_facility_morphology(neutronTestFacility[-1]))


cubit.cmd('export cubit "please_work.cub5')
# cubit.cmd('volume all scheme auto')
# cubit.cmd('mesh volume all')
# cubit.cmd('export genesis "testblob.g"')
