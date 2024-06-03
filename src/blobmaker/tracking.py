from blobmaker.components import SimpleComponent
from blobmaker.assemblies import GenericComponentAssembly, ExternalComponentAssembly
from blobmaker.generic_classes import CubismError, CubitInstance, cubit, cmd
from blobmaker.cubit_functions import to_surfaces, add_to_new_entity
from blobmaker.cubit_functions import to_surfaces, add_to_new_entity

class MaterialsTracker:
    '''Track materials and boundaries between all provided components
    '''
    def __init__(self) -> None:
        # to collect components and existing material names
        self.components = []
        self.materials = set()
        # names of blocks + sidesets
        self.sidesets = []
        self.blocks = []
        # names of interfaces between materials
        self.material_boundaries = []
        # mappings to sidesets
        self.materials_to_sidesets = {}
        self.types_to_sidesets = {}
        # string to use as a separator
        self.external_separator = "_" # in cubit
        self.internal_separator = "---" # internally

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
        surface_ids = cubit.get_entities("surface")
        surface_to_components = {surf_id : [] for surf_id in surface_ids}
        surface_to_materials = {surf_id : [] for surf_id in surface_ids}
        surface_to_types = {surf_id : [] for surf_id in surface_ids}
        material_to_volumes = {material: [] for material in self.materials}

        for component in self.components:
            material_to_volumes[component.material].append(component.volume_id_string())
            for surf_id in [surface.cid for surface in to_surfaces(component.get_subcomponents())]:
                surface_to_components[surf_id].append(component.identifier)
                surface_to_materials[surf_id].append(component.material)
                surface_to_types[surf_id].append(component.classname)

        self.types_to_sidesets = self.__merge_mapping(surface_to_types, surface_to_components)
        self.materials_to_sidesets = self.__merge_mapping(surface_to_materials, surface_to_components)

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

        self.sidesets = list(component_to_surfaces.keys())
        self.material_boundaries = list(material_to_surfaces.keys())
        self.blocks = [comp.identifier for comp in self.components]

    def __invert_mapping(self, x_to_ys: dict):
        y_to_xs = {}
        for x, ys in x_to_ys.items():
            boundary_name = self.make_boundary_name(ys)
            if boundary_name in y_to_xs.keys():
                y_to_xs[boundary_name].append(x)
            else:
                y_to_xs[boundary_name] = [x]
        return y_to_xs

    def __merge_mapping(self, surf_to_keys, surf_to_values):
        return_dict = {}
        for surf_id in cubit.get_entities("surface"):
            key = self.make_boundary_name(surf_to_keys[surf_id], True)
            value = self.make_boundary_name(surf_to_values[surf_id])
            if key in return_dict.keys():
                return_dict[key].add(value)
            else:
                return_dict[key] = set([value])
        return return_dict

    def make_boundary_name(self, parts_of_name: list[str], internal=False):
        separator = self.internal_separator if internal else self.external_separator
        if len(parts_of_name) == 1:
            return parts_of_name[0] + separator + "air"
        else:
            p_o_n = parts_of_name.copy()
            p_o_n.sort()
            return separator.join(p_o_n)
    
    def organise_into_groups(self):
        '''Create groups for material, component, component boundary, 
        and material boundary groups in cubit'''

        add_to_new_entity("group", "materials", "group", list(self.materials))
        add_to_new_entity("group", "simple_components", "group", [comp.identifier for comp in self.components])
        add_to_new_entity("group", "component_boundaries", "group", self.sidesets)
        add_to_new_entity("group", "material_boundaries", "group", self.material_boundaries)
    
    def reset(self):
        '''Reset internal states
        '''
        self.components = []
        self.materials = set()
        self.sidesets = []
        self.blocks = []
        self.material_boundaries = []
        self.types_to_sidesets = {}
        self.materials_to_sidesets = {}
        self.external_separator = "_"
        self.internal_separator = "---"

    def get_blocks(self) -> list[str]:
        '''Get names of created blocks. Blocks are named
        the same as their corresponding simple components.
        For example the block corresponding to coolant0 is
        named coolant0.

        :return: list of names
        :rtype: list[str]
        '''
        return self.blocks

    def get_sidesets(self) -> list[str]:
        '''Get names of created sidesets. 
        Sidesets are named according to the names of the simple
        components on either side. For example the sideset between
        coolant0 and cladding0 is coolant0_cladding0. Sidesets not 
        at interfaces are named like <component_name>_air.

        :return: list of names
        :rtype: list[str]
        '''
        return self.sidesets

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

    def get_sidesets_between_components(self, *types: str) -> list[str]:
        '''Get sidesets between specified simple component types. 
        Providing only 1 type will assume the other side of the interface to be 'air'

        :return: list of sideset names
        :rtype: list[str] | None
        '''
        if not 0 <len(types) <= 2:
            print("No boundaries can exist between provided number of types")
            return None
        type_ref = self.make_boundary_name(list(types), True)
        if type_ref not in self.types_to_sidesets.keys():
            print(f"No boundaries exist: {types}")
            return None
        return list(self.types_to_sidesets[type_ref])
    
    def get_sidesets_between_materials(self, *materials: str) -> list[str]:
        if not 0 < len(materials) <= 2:
            print("No boundaries can exist between provided number of types")
            return None
        type_ref = self.make_boundary_name(list(materials), True)
        if type_ref not in self.materials_to_sidesets.keys():
            print(f"No boundaries exist: {materials}")
            return None
        return list(self.materials_to_sidesets[type_ref])

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
