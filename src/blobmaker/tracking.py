from blobmaker.components import SimpleComponent
from blobmaker.assemblies import GenericComponentAssembly, ExternalComponentAssembly
from blobmaker.generic_classes import CubismError, CubitInstance, cubit, cmd
from blobmaker.cubit_functions import to_surfaces, add_to_new_entity

class MaterialsTracker:
    '''Track materials and boundaries between all provided components
    '''
    def __init__(self) -> None:
        self.components = []
        self.materials = set()
        self.component_boundaries = []
        self.material_boundaries = []
        self.blocks = []
        self.sidesets = []
        self.blocks = []
        self.sideset_types = []
        self.block_types = []

    def extract_components(self, root_component):
        '''Get all components stored in root and every material they are made of.

        :param root_component: component to track
        :type root_component: SimpleComponent | GenericComponentAssembly
        '''
        if isinstance(root_component, SimpleComponent):
            self.components += [root_component]
            self.materials.add(root_component.material)
        elif isinstance(root_component, GenericComponentAssembly):
            self.components += root_component.get_all_components()
            self.materials = self.materials.union({component.material for component in root_component.get_all_components()})
    
    def track_boundaries(self):
        '''Find boundaries between simple components. 
        Make component-component and material-material groups.
        Add simple components to blocks.
        Add component interfaces to sidesets.
        '''
        surface_to_components = {surf_id : [] for surf_id in cubit.get_entities("surface")}
        surface_to_materials = {surf_id : [] for surf_id in cubit.get_entities("surface")}
        material_to_volumes = {material: [] for material in self.materials}

        for component in self.components:
            material_to_volumes[component.material].append(component.volume_id_string())
            for surf_id in [surface.cid for surface in to_surfaces(component.get_subcomponents())]:
                surface_to_components[surf_id].append(component.identifier)
                surface_to_materials[surf_id].append(component.material)

        component_to_surfaces = self.__invert_mapping(surface_to_components)
        material_to_surfaces = self.__invert_mapping(surface_to_materials)

        for component in self.components:
            add_to_new_entity("block", component.identifier, "volume", component.volume_id_string())

        for material_name, vol_id_strings in material_to_volumes.items():
            add_to_new_entity("group", material_name, "volume", vol_id_strings)

        for boundary_name, surf_ids in component_to_surfaces.items():
            add_to_new_entity("sideset", boundary_name, "surface", surf_ids)
            add_to_new_entity("group", boundary_name, "surface", surf_ids)

        for boundary_name, surf_ids in material_to_surfaces.items():
            add_to_new_entity("group", boundary_name, "surface", surf_ids)

        self.component_boundaries = list(component_to_surfaces.keys())
        self.material_boundaries = list(material_to_surfaces.keys())


    def __invert_mapping(self, x_to_ys: dict):
        y_to_xs = {}
        for x, ys in x_to_ys.items():
            boundary_name = self.make_boundary_name(ys)
            if boundary_name in y_to_xs.keys():
                y_to_xs[boundary_name].append(x)
            else:
                y_to_xs[boundary_name] = [x]
        return y_to_xs

    def make_boundary_name(self, parts_of_name: list[str]):
        if len(parts_of_name) == 1:
            return parts_of_name[0] + "_air"
        else:
            p_o_n = parts_of_name.copy()
            p_o_n.sort()
            return "_".join(p_o_n)
    
    def organise_into_groups(self):
        '''Create groups for material, component, component boundary, 
        and material boundary groups in cubit'''

        add_to_new_entity("group", "materials", "group", list(self.materials))
        add_to_new_entity("group", "simple_components", "group", [comp.identifier for comp in self.components])
        add_to_new_entity("group", "component_boundaries", "group", self.component_boundaries)
        add_to_new_entity("group", "material_boundaries", "group", self.material_boundaries)
    
    def reset(self):
        '''Reset internal states
        '''
        self.materials = set()
        self.component_boundaries = []
        self.material_boundaries = []
        self.blocks = []
        self.sidesets = []
        self.components = []
        self.materials = set()
        self.component_boundaries = []
        self.material_boundaries = []
        self.blocks = []
        self.sidesets = []

    def get_blocks(self) -> list[str]:
        '''Get names of created blocks

        :return: list of names
        :rtype: list[str]
        '''
        return [block.name for block in self.blocks]

    def get_sidesets(self) -> list[str]:
        '''Get names of created sidesets

        :return: list of names
        :rtype: list[str]
        '''
        return [sideset.name for sideset in self.sidesets]
    
    def get_sidesets_between(self, class1: str, class2: str) -> list[str]:
        '''Get sidesets of interfaces between specified simple component classes

        :param class1: simple component class
        :type class1: str
        :param class2: simple component class
        :type class2: str
        :return: list of names
        :rtype: list[str]
        '''
        return [sideset.name for sideset in self.sidesets if class1 in sideset.name and class2 in sideset.name]

    def get_blocks_of_material(self, material: str) -> list[str]:
        '''Get blocks of simple components made of specified material

        :param material: name of material
        :type material: str
        :return: list of block names
        :rtype: list[str]
        '''
        return [component.identifier for component in self.components if component.material == material]

    def get_block_types(self):
        '''Get block types

        :return: list of names
        :rtype: list[str]
        '''
        return list({comp.classname for comp in self.components})

    def get_sideset_types(self):
        '''Get sideset types

        :return: list of names
        :rtype: list[str]
        '''
        return list({self.get_sideset_type(sideset.name) for sideset in self.sidesets})

    def get_sideset_type(self, sideset_name: str):
        '''Get type of a specific sideset

        :return: list of names
        :rtype: list[str]
        '''
        components = sideset_name.split("_")
        sideset_type = ""
        for comp in components:
            sideset_type += (comp.rstrip("0123456789") + "_")
        return sideset_type.rstrip("_")

    def get_sidesets_of_type(self, sideset_type: str):
        '''Get sidesets of a specific type

        :return: list of names
        :rtype: list[str]
        '''
        return list({sideset.name for sideset in self.sidesets if self.get_sideset_type(sideset.name) == sideset_type})

    def get_blocks(self) -> list[str]:
        '''Get names of created blocks. Blocks are named
        the same as their corresponding simple components.
        For example the block corresponding to coolant0 is
        named coolant0.

        :return: list of names
        :rtype: list[str]
        '''
        return [block.name for block in self.blocks]

    def get_sidesets(self) -> list[str]:
        '''Get names of created sidesets. 
        Sidesets are named according to the names of the simple
        components on either side. For example the sideset between
        coolant0 and cladding0 is coolant0_cladding0. Sidesets not 
        at interfaces are named like <component_name>_air.

        :return: list of names
        :rtype: list[str]
        '''
        return [sideset.name for sideset in self.sidesets]
    
    def get_sidesets_between_components(self, type1: str, type2: str) -> list[str]:
        '''Get sidesets of interfaces between specified simple component types

        :param type1: simple component type
        :type type1: str
        :param type2: simple component type
        :type type2: str
        :return: list of names
        :rtype: list[str]
        '''
        classes = list({comp.classname for comp in self.components})
        if type1 not in classes:
            raise CubismError(f"type {type1} not recognised")
        elif type2 not in classes:
            raise CubismError(f"type {type2} not recognised")
        return [sideset.name for sideset in self.sidesets if type1 in sideset.name and type2 in sideset.name]

    def get_blocks_of_material(self, material: str) -> list[str]:
        '''Get blocks of simple components made of specified material

        :param material: name of material
        :type material: str
        :return: list of block names
        :rtype: list[str]
        '''
        return [component.identifier for component in self.components if component.material == material]

    def get_block_types(self):
        '''Get block types. These are the same as the types of simple components.
        For example the type of coolant1 is coolant.

        :return: list of names
        :rtype: list[str]
        '''
        return list({comp.classname for comp in self.components})

    def get_sideset_types(self):
        '''Get sideset types. Each sideset has a type corresponding to the 
        type of the simple components on either side. For example the 
        type of the sideset cladding0_coolant0 is cladding_coolant.

        :return: list of names
        :rtype: list[str]
        '''
        return list({self.get_sideset_type(sideset.name) for sideset in self.sidesets})

    def get_sideset_type(self, sideset_name: str):
        '''Get type of a specific sideset

        :return: list of names
        :rtype: list[str]
        '''
        components = sideset_name.split("_")
        sideset_type = ""
        for comp in components:
            sideset_type += (comp.rstrip("0123456789") + "_")
        return sideset_type.rstrip("_")

    def get_sidesets_of_type(self, sideset_type: str):
        '''Get sidesets of a specific type

        :return: list of names
        :rtype: list[str]
        '''
        return list({sideset.name for sideset in self.sidesets if self.get_sideset_type(sideset.name) == sideset_type})


class ComponentTracker:
    '''Adds components to cubit groups recursively'''
    # this counter is to ensure every component is named uniquely
    counter = 0

    def __init__(self) -> str:
        self.root_name = "no root component"
        self.identifiers = {}

    def track_component(self, root_component):
        self.give_identifiers(root_component)
        self.root_name = self.__track_components_as_groups(root_component)

    def give_identifiers(self, root_component):
        '''Give every component a unique identifier

        :param root_component: Component
        :type root_component: GenericComponentAssembly | SimpleComponent
        '''
        if isinstance(root_component, GenericComponentAssembly):
            self.__name_component(root_component)
            for component in root_component.get_components():
                self.give_identifiers(component)
        # if this is a simple component, give it a unique identifier
        elif isinstance(root_component, SimpleComponent):
            self.__name_component(root_component)
        else:
            raise CubismError(f'Component not recognised: {root_component}')
    
    def __name_component(self, root_component: GenericComponentAssembly | SimpleComponent):
        '''If component doesn't already have a unique identifier, give it one

        :param root_component: component to name
        :type root_component: GenericComponentAssembly | ComplexComponent
        '''
        if root_component.classname == root_component.identifier:
            groupname = self.__make_group_name(root_component.classname)
            root_component.identifier = groupname

    def __track_components_as_groups(self, root_component):
        '''Track volumes of components as groups (recursively)

        :param root_component: Component to track in
        :type root_component: Any Assembly or ComplexComponent
        :return: Name of group tracking the root component
        :rtype: str
        '''
        # volumes of these should already belong to a group
        if isinstance(root_component, ExternalComponentAssembly):
            groupname = str(root_component.group)
        # if this is an assembly, run this function on each of its components
        elif isinstance(root_component, GenericComponentAssembly):
            groupname = root_component.identifier
            for component in root_component.get_components():
                self.__add_to_group(groupname, self.__track_components_as_groups(component))
        # if this is a complex component, add volumes to group
        elif isinstance(root_component, SimpleComponent):
            groupname = root_component.identifier
            for geometry in root_component.get_subcomponents():
                self.__add_to_group(groupname, geometry)
        else:
            raise CubismError(f'Component not recognised: {root_component}')
        return groupname

    def __make_group_name(self, classname: str):
        '''Construct unique group name

        :param classname: Name of component class
        :type classname: str
        :return: Name of group
        :rtype: str
        '''
        if classname in self.identifiers.keys():
            self.identifiers[classname] += 1
        else:
            self.identifiers[classname] = 0
        count = self.identifiers[classname]
        groupname = f"{classname}{count}"
        cmd(f'create group "{groupname}"')
        return groupname

    def __add_to_group(self, group: str, entity):
        '''Add entity to group

        :param group: entity to add
        :type group: str
        :param entity: geometry or name of group
        :type entity: CubitInstance or str
        '''
        if type(entity) is str:
            cmd(f'group {group} add group {entity}')
        elif isinstance(entity, CubitInstance):
            cmd(f'group {group} add {entity.geometry_type} {entity.cid}')

    def reset_counter(self):
        '''Reset internal states
        '''
        self.identifiers = {}
