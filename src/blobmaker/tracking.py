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
        self.components = []
        self.materials = set()
        self.component_boundaries = []
        self.material_boundaries = []
        self.blocks = []
        self.sidesets = []


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
