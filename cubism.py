import sys
import json

if __name__ == "__main__":
    sys.path.append('/opt/Coreform-Cubit-2023.8/bin')
    import cubit
    cubit.init(['cubit', '-nojournal'])
elif __name__ == "__coreformcubit__":
    cubit.cmd("reset")

filename = "sample_morphology.json"

def object_reader(json_object: dict):
    '''set up class instance according to the class name provided'''
    if json_object["class"] == "complex component":
        return ComplexComponent(
            name = json_object["name"],
            material = json_object["material"],
            geometry = json_object["geometry"],
            classname = "complex"
        )
    elif json_object["class"] == "external component assembly":
        return ExternalComponentAssembly(
            name = json_object["name"],
            manufacturer = json_object["manufacturer"],
            geometry = json_object["geometry"],
            classname = "external"
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
    # elif json_object["class"] == "blanket":
    #     return BlanketAssembly(
    #         morphology= json_object["morphology"],
    #         component_list= json_object["components"]
    #     )
    elif json_object["class"] == "room":
        return RoomComponent(
            material= json_object["material"],
            name= json_object["name"],
            geometry= json_object["geometry"]
        )
    elif json_object["class"] == "blanket":
        return BlanketComponent(
            name= json_object["name"],
            material= json_object["material"],
            geometry= json_object["geometry"]
        )

class NativeComponentAssembly:
    '''
    Generic assembly
    This takes a list of required and additional classnames to set up a specific assembly
    - required classnames: instantiating will fail without at least one component of the given classnames
    - additional classnames: defines attributes to store components with this classname
    An assembly class specified from this will:
    - have attributes corresponding to the supplied classnames
    - require every instance have at least one component from the required classnames
    - store components of the specified classnames in corresponding attributes, otherwise other_components
    - be able to fetch cubit instances of components stores in these attributes (get_cubit_instances)
    '''
    def __init__(self, morphology: str, component_list:list, required_classnames: list, additional_classnames: list):
        # this defines what morphology will be enforced later
        self.morphology = morphology
        # this defines what components to require in every instance
        self.required_classnames = required_classnames

        # component_mapping defines what classes get stored in what attributes (other_components is default)
        self.other_components = []
        self.component_mapping = {"other": self.other_components}

        # set up attributes and component_mapping for specified components
        for classname in required_classnames + additional_classnames:
            component_name = classname + "_components"
            self.__setattr__(component_name, [])
            self.component_mapping[classname] = self.__getattribute__(component_name)
        
        # enforce given component_list based on required_classnames
        self.enforced = self.enforce_structure(component_list)
        # store instances
        self.setup_facility(component_list)
        print("hello")

    def enforce_structure(self, comp_list: list):
        '''make sure the instance contains the required components'''
        class_list = [i["class"] for i in comp_list]
        for classes_required in self.required_classnames:
            if classes_required not in class_list:
                # Can change this to a warning, for now it just throws an error
                raise StructureError("Neutron test facility must contain a room, source, and blanket")
        return True
    
    def setup_facility(self, component_list: list):
        '''adds components to lists in the appropriate attributes'''
        for component_dict in component_list:
            # if you are looking for the class-attribute mapping it is the component_mapping dict in __init__
            if component_dict["class"] in self.component_mapping.keys():
                self.component_mapping[component_dict["class"]].append(object_reader(component_dict))
            else:
                self.other_components.append(object_reader(component_dict))

    def get_cubit_instances(self, classname_list: list):
        '''returns list of cubit instances of specified classnames'''
        instances_list = []
        for component_classname in classname_list:
            # checks if valid classname
            if component_classname in self.component_mapping.keys():
                for component in self.component_mapping[component_classname]:
                    # fetches instances
                    if isinstance(component, BaseCubitInstance):
                        instances_list.append(component.cubitInstance)
                    else:
                        raise StructureError(f"component ({component}) not recognised")
            else:
                raise StructureError(f"Classname not recognised: {component_classname}")
        return instances_list

class StructureError(Exception):
    pass

class NeutronTestFacility(NativeComponentAssembly):
    def __init__(self, morphology: str, component_list: list):
        super().__init__(morphology, component_list, required_classnames = ["source", "blanket", "room"], additional_classnames = [])

class BlanketAssembly:
    def __init__(self, morphology: str, component_list: list) -> None:
        self.morphology = morphology
        #instance storage
        self.breeder_components = []
        self.structure_components = []
        self.other_components = []
        self.setup_blanket(component_list)
        #store instances

    def setup_blanket(self, component_list: list):
        for component_dict in component_list:
            if component_dict["class"] == "breeder":
                self.breeder_components.append(object_reader(component_dict))
            elif component_dict["class"] == "structure":
                self.structure_components.append(object_reader(component_dict))
            else:
                self.other_components.append(object_reader(component_dict))

    def get_cubit_instances(self):
        components_to_check = [self.breeder_components, self.structure_components, self.other_components]

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
        '''create 3d room with inner dimensions inner_dims (int or list) and thickness (int or list)'''
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
        testing_source = cubit.copy_body(facility.source_components[0].cubitInstance)
        testing_blanket = cubit.copy_body(facility.blanket_components[0].cubitInstance)
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

# maybe i should add this to main()
with open(filename) as jsonFile:
    data = jsonFile.read()
    objects = json.loads(data)
neutronTestFacility = []
for json_object in objects:
    neutronTestFacility.append(object_reader(json_object=json_object))
    if json_object["class"] == "neutron test facility":
        print("morphology enforced? ", enforce_facility_morphology(neutronTestFacility[-1]))

if __name__ == "__main__":
    #cubit.cmd('export cubit "please_work.cub5')
    pass
#       cubit.cmd('volume all scheme auto')
#       cubit.cmd('mesh volume all')
#       cubit.cmd('export genesis "testblob.g"')
