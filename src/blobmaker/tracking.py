from blobmaker.components import ComplexComponent
from blobmaker.assemblies import GenericComponentAssembly, ExternalComponentAssembly
from blobmaker.generic_classes import CubismError, CubitInstance, cubit, cmd
from blobmaker.cubit_functions import to_surfaces, to_volumes, cmd_check, get_entities_from_group, create_new_entity
import itertools


class Group:
    '''Tracks cubit groups.'''
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


class ComponentGroup:
    def __init__(self, component: ComplexComponent) -> None:
        self.identifier = component.identifier
        self.material = component.material
        self.vols = component.volume_id_string()
        self.boundaries_created = []
        self.track_material()
        if len(component.get_subcomponents()) > 1:
            self.boundaries_created.extend(self.__merge_between(self.identifier, self.vols, self.material))

    def track_material(self):
        mat_id = create_new_entity("group", self.material)
        cmd(f"group {mat_id} add volume {self.vols}")

    def merge_with_component(self, component: 'ComponentGroup'):
        identifiers = [self.identifier, component.identifier]
        mats = [self.material, component.material]
        vols = [self.vols, component.vols]

        self.boundaries_created.extend(self.__merge_between(identifiers, vols, mats))

    def __merge_between(self, identifiers, vols, mats):
        identifiers, vols, mats = self.__turn_to_lists(identifiers, vols, mats)
        cmd(f"imprint volume {vols[0]} with volume {vols[1]}")
        # is new group created when trying to merge?
        group_id = cmd_check(f"merge volume {vols[0]} with volume {vols[1]} group_results", "group")

        # if a new group is created, track the corresponding boundary
        if group_id:
            group_surfs = get_entities_from_group(group_id, "surface")
            id_group = self.make_group_name(identifiers)
            mat_group = self.make_group_name(mats)
            cmd(f'group {group_id} rename "{id_group}"')
            mat_id = cubit.get_id_from_name(mat_group)
            if not mat_id:
                mat_id = cmd_check(f'create group "{mat_group}"', "group")
            cubit.add_entities_to_group(mat_id, group_surfs, "surface")
            return [id_group, mat_group]
        return []

    def make_group_name(self, names: list):
        copy_list = names
        copy_list.sort()
        return '_'.join([str(name) for name in copy_list])

    def __turn_to_lists(self, *maybe_lists) -> list[list]:
        definitely_lists = []
        for maybe_list in maybe_lists:
            if type(maybe_list) is list:
                definitely_lists.append(maybe_list)
            else:
                definitely_lists.append([maybe_list for i in range(2)])
        return definitely_lists


class MaterialsTracker:
    def __init__(self) -> None:
        self.components = []
        self.materials = []
        self.boundaries = []

    def extract_components(self, root_component):
        '''Get all components stored in root and every material they are made of.

        :param root_component: _description_
        :type root_component: _type_
        '''
        if isinstance(root_component, ComplexComponent):
            self.components [root_component]
        elif isinstance(root_component, GenericComponentAssembly):
            self.components = root_component.get_all_components()
            self.materials = list(set(component.material for component in self.components))
    
    def merge_components(self):
        '''Merge every combination of component. Make component-component and material-material groups.
        '''
        self.components = [ComponentGroup(component) for component in self.components]
        if len(self.components) > 1:
            for comp1, comp2 in itertools.combinations(self.components, 2):
                comp1.merge_with_component(comp2)
                self.boundaries.extend(comp1.boundaries_created)
    
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
            material_surface_ids = get_entities_from_group(boundary_name, "surface")
            # if this surface is unmerged, it is in contact with air so add it to the boundary
            for material_surface_id in material_surface_ids:
                if material_surface_id in all_unmerged_surfaces:
                    cmd(f'group "{boundary_name}" add surface {material_surface_id}')
        cmd(f'delete group {unmerged_group_id}')
    
    def organise_into_groups(self):
        '''create groups for material groups and boundary groups in cubit'''

        # create material groups group
        cmd('create group "materials"')
        for material in self.materials:
            cmd(f'group "materials" add group "{material}"')

        # create boundary group groups
        cmd('create group "boundaries"')
        boundaries_group_id = cubit.get_last_id("group")
        for boundary in self.boundaries:
            cmd(f'group "boundaries" add group "{boundary}"')
        # delete empty boundaries
        for group_id in get_entities_from_group(boundaries_group_id, "group"):
            if cubit.get_group_surfaces(group_id) == ():
                cmd(f"delete group {group_id}")
    
    def add_blocks(self):
        for material in self.materials:
            surfs = get_entities_from_group(material, "surface")
            surf_string = " ".join(surfs)
            block_id = create_new_entity("block", material)
            cmd(f"block {block_id} add surface {surf_string}")
    
    def add_sidesets(self):
        for boundary in self.boundaries:
            bound_surfs = get_entities_from_group(boundary, "surface")
            if len(bound_surfs) > 0:
                sideset_id = create_new_entity("sideset", boundary)
                cmd(f"sideset {sideset_id} add surface {bound_surfs}")
    
    def reset(self):
        self.materials = []
        self.boundaries = []


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
            groupname = self.__make_group_name(root_component.classname)
            for component in root_component.get_components():
                self.give_identifiers(component)
        # if this is a complex component, add volumes to group
        elif isinstance(root_component, ComplexComponent):
            groupname = self.__make_group_name(root_component.classname)
            root_component.identifier = groupname
        else:
            raise CubismError(f'Component not recognised: {root_component}')

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
        elif isinstance(root_component, ComplexComponent):
            groupname = root_component.identifier
            for geometry in root_component.subcomponents:
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
