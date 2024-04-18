from blobmaker.components import SimpleComponent
from blobmaker.assemblies import GenericComponentAssembly, ExternalComponentAssembly
from blobmaker.generic_classes import CubismError, CubitInstance, cubit, cmd
from blobmaker.cubit_functions import to_surfaces, to_volumes, cmd_check, get_entities_from_group, create_new_entity, merge_volumes
import itertools


class Group:
    '''Tracks a cubit group.'''
    def __init__(self, name: str) -> None:
        self.name = name
        self.group_id = cubit.get_id_from_name(name)
        if not self.group_id:
            self.group_id = cmd_check(f'create group "{self.name}"', "group")
        # should only store CubitInstances
        self.geometries = []

    def add_geometry(self, geometry):
        if isinstance(geometry, CubitInstance):
            self.geometries.append(geometry)
            cmd(f'group "{self.name}" add {str(geometry)}')
        elif type(geometry) is list:
            filtered_list = [geom for geom in geometry if isinstance(geom, CubitInstance)]
            for obj in filtered_list:
                cmd(f'group "{self.name}" add {str(obj)}')
            self.geometries.extend(filtered_list)
        else:
            raise CubismError("Geometries should be added as CubitInstances")

    def get_surface_ids(self):
        return [i.cid for i in to_surfaces(self.geometries)]

    def get_volume_ids(self):
        return [i.cid for i in to_volumes(self.geometries)]


class Sideset:
    def __init__(self, name: str) -> None:
        self.name = name
        self.id = create_new_entity("sideset", name)
        self.surfaces = []
    
    def __str__(self) -> str:
        return self.name

    def add_surface(self, surface):
        if type(surface) is int:
            self.__add_if_unique(surface)
        elif type(surface) is list:
            for surf in surface:
                self.add_surface(surf)
        elif isinstance(surface, CubitInstance) and surface.geometry_type == "surface":
            self.__add_if_unique(surface.cid)
    
    def __add_if_unique(self, surface: int):
        if surface not in self.surfaces:
            self.surfaces.append(surface)
            cmd(f'sideset {self.id} add surface {surface}')
    
    def get_surfaces(self):
        return self.surfaces
    
    def get_surfaces_string(self):
        return " ".join([str(surf) for surf in self.surfaces])


class ComponentGroup:
    def __init__(self, component: SimpleComponent) -> None:
        self.identifier = component.identifier
        self.material = component.material
        self.geometries = component.get_subcomponents()
        self.component_boundaries = []
        self.material_boundaries = []
        self.__track_material()
        self.__find_self_overlaps()

    def __track_material(self):
        mat_id = create_new_entity("group", self.material)
        for geometry in self.geometries:
            cmd(f"group {mat_id} add {geometry}")
    
    def __find_self_overlaps(self):
        vols = [geom for geom in self.geometries if geom.geometry_type == "volume" ]
        overlaps = []
        for vol1, vol2 in itertools.combinations(vols, 2):
            overlaps += self.__get_shared_surfs([vol1], [vol2])
        if overlaps:
            identifiers = [self.identifier, self.identifier]
            mats = [self.material, self.material]
            id_group = self.__make_boundary_group(identifiers, overlaps)
            self.component_boundaries.append(id_group)
            mat_group = self.__make_boundary_group(mats, overlaps)
            self.material_boundaries.append(mat_group)

    def track_shared_surfaces(self, component: 'ComponentGroup'):
        shared_surfs = self.__get_shared_surfs(self.geometries, component.geometries)
        if shared_surfs:
            identifiers = [self.identifier, component.identifier]
            mats = [self.material, component.material]
            id_group = self.__make_boundary_group(identifiers, shared_surfs)
            self.component_boundaries.append(id_group)
            mat_group = self.__make_boundary_group(mats, shared_surfs)
            self.material_boundaries.append(mat_group)

    def __get_shared_surfs(self, vols1, vols2):
        surfs1 = {surf.cid for surf in to_surfaces(vols1)}
        surfs2 = {surf.cid for surf in to_surfaces(vols2)}
        return list(surfs1.intersection(surfs2))
    
    def __make_boundary_group(self, parts_of_name: list[str], surfs: list[int]):
        group_name = self.make_group_name(parts_of_name)
        group_id = create_new_entity("group", group_name)
        cubit.add_entities_to_group(group_id, surfs, "surface")
        return group_name

    def make_group_name(self, names: list):
        copy_list = names
        copy_list.sort()
        return '_'.join([str(name) for name in copy_list])


class MaterialsTracker:
    def __init__(self) -> None:
        self.components = []
        self.materials = []
        self.component_boundaries = []
        self.material_boundaries = []
        self.sidesets = []

    def extract_components(self, root_component):
        '''Get all components stored in root and every material they are made of.

        :param root_component: _description_
        :type root_component: _type_
        '''
        if isinstance(root_component, SimpleComponent):
            self.components += [root_component]
            self.materials += [root_component.material]
        elif isinstance(root_component, GenericComponentAssembly):
            self.components += root_component.get_all_components()
            self.materials += list(set([component.material for component in self.components]))
        self.materials = list(set(self.materials))
    
    def track_boundaries(self):
        '''Merge every combination of component. Make component-component and material-material groups.
        '''
        self.components = [ComponentGroup(component) for component in self.components]
        if len(self.components) > 1:
            for comp1, comp2 in itertools.combinations(self.components, 2):
                comp1.track_shared_surfaces(comp2)
        for component in self.components:
            self.component_boundaries.extend(component.component_boundaries)
            self.material_boundaries.extend(component.material_boundaries)

    def merge_with_air(self):
        '''Merge every component with air
        '''
        cmd('group "unmerged_surfaces" add surface with is_merged=0')
        unmerged_group_id = cubit.get_id_from_name("unmerged_surfaces")
        all_unmerged_surfaces = cubit.get_group_surfaces(unmerged_group_id)

        for material in self.materials:
            # setup group and tracking for interface with air
            boundary_name = material + "_air"
            # look at every surface of this material
            surface_ids = get_entities_from_group(boundary_name, "surface")
            # if this surface is unmerged, it is in contact with air so add it to the boundary
            for surface_id in surface_ids:
                if surface_id in all_unmerged_surfaces:
                    cmd(f'group "{boundary_name}" add surface {surface_id}')
        cmd(f'delete group {unmerged_group_id}')
    
    def organise_into_groups(self):
        '''create groups for material groups and boundary groups in cubit'''

        self.__fill_group_with_groups("materials", self.materials)
        self.__fill_group_with_groups("components", [comp.identifier for comp in self.components])
        print(self.component_boundaries)
        self.__fill_group_with_groups("component_boundaries", self.component_boundaries)
        self.__fill_group_with_groups("material_boundaries", self.material_boundaries)

        # # delete empty boundaries
        # for group_id in get_entities_from_group(boundaries_group_id, "group"):
        #     if cubit.get_group_surfaces(group_id) == ():
        #         cmd(f"delete group {group_id}")
    
    def __fill_group_with_groups(self, name: str, groups_to_fill: list[str]):
        group_id = create_new_entity("group", name)
        for group in groups_to_fill:
            cmd(f'group {group_id} add group {group}')
    
    def add_blocks(self):
        for component in self.components:
            if isinstance(component, SimpleComponent):
                self.__add_component_to_block(component)
            elif isinstance(component, GenericComponentAssembly):
                for comp in component.get_all_components():
                    self.__add_component_to_block(comp)
    
    def __add_component_to_block(self, component: SimpleComponent):
        block_id = create_new_entity("block", component.identifier)
        cmd(f"block {block_id} add volume {component.volume_id_string()}")
    
    def add_sidesets(self):
        for boundary in self.component_boundaries + self.material_boundaries:            
            bound_surfs = get_entities_from_group(boundary, "surface")
            if len(bound_surfs) > 0:
                self.__create_sideset(boundary)
                for sideset in self.sidesets:
                    assert isinstance(sideset, Sideset)
                    if sideset.name == boundary:
                        sideset.add_surface(bound_surfs)
    
    def __create_sideset(self, name: str):
        boundary_names = [str(sideset) for sideset in self.sidesets]
        if name not in boundary_names:
            self.sidesets.append(Sideset(name))
    
    def reset(self):
        self.materials = []
        self.boundaries = []
        self.sidesets = []
        self.components = []


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
        if isinstance(root_component, GenericComponentAssembly):
            self.__name_component(root_component)
            for component in root_component.get_components():
                self.give_identifiers(component)
        # if this is a complex component, give it a unique identifier
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
        self.identifiers = {}
