from blobmaker.components import ComplexComponent
from blobmaker.assemblies import GenericComponentAssembly, ExternalComponentAssembly
from blobmaker.generic_classes import CubismError, CubitInstance, cubit, cmd
from blobmaker.cubit_functions import to_surfaces, to_volumes, cmd_check


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


class Material(Group):
    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.state_of_matter = ""

    def set_state(self, state: str):
        self.state_of_matter = state


class Boundary:
    def __init__(self, comp1: ComplexComponent, comp2: ComplexComponent) -> None:
        self.identifiers = [comp1.identifier, comp2.identifier]
        self.identifiers.sort()
        boundary_name = str(self.identifiers[0]) + "_" + self.identifiers[1]

    def merge_between(self):
        pass
        


class MaterialsTracker:
    '''Tracks materials and boundaries between those materials
    (including nullspace)'''
    def __init__(self):
        self.materials = []
        self.boundaries = []

    def make_material(self, material_name: str):
        '''Add material to internal list.
        Will not add if material name already exists.

        :param material_name: Name of material
        :type material_name: str
        :param group_id: Cubit ID of group
        :type group_id: int
        '''
        if material_name not in [i.name for i in self.materials]:
            self.materials.append(Material(material_name))

    def track_component(self, root_component):
        self.__track_components_as_groups(root_component)

    def __track_components_as_groups(self, root_component):
        '''Track volumes of components as groups (recursively)

        :param root_component: Component to track in
        :type root_component: Any Assembly or ComplexComponent
        :return: Name of group tracking the root component
        :rtype: str
        '''
        # if this is an assembly, run this function on each of its components
        if isinstance(root_component, GenericComponentAssembly):
            for component in root_component.get_components():
                self.__track_components_as_groups(component)
        # if this is a complex component, add volumes to group
        elif isinstance(root_component, ComplexComponent):
            for geometry in root_component.subcomponents:
                self.add_geometry_to_material(geometry, root_component.material)
        else:
            raise CubismError(f'Component not recognised: {root_component}')

    def add_geometry_to_material(self, geometry: CubitInstance, material_name: str):
        '''Add geometry to material and track in cubit.

        :param geometry: Geometry to add
        :type geometry: CubitInstance | list[CubitInstance]
        :param material_name: name of material to add geometry to
        :type material_name: str
        :return: True or raises error
        '''
        self.make_material(material_name)

        # Add geometry to appropriate material.
        # If it can't something has gone wrong
        for material in self.materials:
            if material.name == material_name:
                material.add_geometry(geometry)
                return True
        return CubismError("Could not add component")

    def contains_material(self, material_name: str):
        '''Check for the existence of a material

        :param material_name: name of material to check for
        :type material_name: str
        :return: True or False
        :rtype: bool
        '''
        return material_name in [i.name for i in self.materials]

    def sort_materials_into_pairs(self):
        '''Get all combinations of pairs of materials (not all permutations)

        :return: List of all pairs of materials in the class
        :rtype: list
        '''
        pair_list = []
        # this is my scuffed way of doing this
        min_counter = 0
        for i in range(len(self.materials)):
            for j in range(len(self.materials)):
                if j > min_counter:
                    pair_list.append((self.materials[i], self.materials[j]))
            min_counter += 1
        return pair_list

    def get_boundary_ids(self, boundary_name: str):
        '''Get cubit IDs of the geometries belonging to a boundary

        :param boundary_name: name of boundary to look in
        :type boundary_name: str
        :raises CubismError: If boundary cannot be found
        :return: list of cubit IDs
        :rtype: list
        '''
        for boundary in self.boundaries:
            if boundary.name == boundary_name:
                return [component.cid for component in boundary.geometries]
        raise CubismError("Could not find boundary")

    def add_geometry_to_boundary(self, geometry: CubitInstance, boundary_name: str):
        '''If boundary exists, add geometry to it

        :param geometry: geometry to add
        :type geometry: CubitInstance
        :param boundary_name: name of boundary to add to
        :type boundary_name: str
        :raises CubismError: If boundary can't be found
        :return: True
        :rtype: bool
        '''
        for boundary in self.boundaries:
            if boundary.name == boundary_name:
                boundary.add_geometry(geometry)
                return True
        raise CubismError("Could not find boundary")

    def merge_and_track_boundaries(self):
        '''tries to merge every possible pair of materials,
        and tracks the resultant material boundaries (if any exist).'''
        pair_list = self.sort_materials_into_pairs()
        # intra-group merge
        for material in self.materials:
            self.__merge_and_track_between(material, material)

        # try to merge volumes in every pair of materials
        for (material1, material2) in pair_list:
            self.__merge_and_track_between(material1, material2)

        # track material-air boundaries

        # only unmerged surfaces are in contact with air?
        cmd('group "unmerged_surfaces" add surface with is_merged=0')
        unmerged_group_id = cubit.get_id_from_name("unmerged_surfaces")
        all_unmerged_surfaces = cubit.get_group_surfaces(unmerged_group_id)
        # look at every collected material
        for material in self.materials:
            # setup group and tracking for interface with air
            boundary_name = material.name + "_air"
            self.boundaries.append(Group(boundary_name))
            # look at every surface of this material
            material_surface_ids = material.get_surface_ids()
            # if this surface is unmerged, it is in contact with air so add it to the boundary
            for material_surface_id in material_surface_ids:
                if material_surface_id in all_unmerged_surfaces:
                    cmd(f'group "{boundary_name}" add surface {material_surface_id}')
                    self.add_geometry_to_boundary(CubitInstance(material_surface_id, "surface"), boundary_name)

        cmd(f'delete group {unmerged_group_id}')

    def __merge_and_track_between(self, material1: Material, material2: Material):
        group_id_1 = material1.group_id
        group_id_2 = material2.group_id
        group_name = str(material1.name) + "_" + str(material2.name)

        # is new group created when trying to merge?
        group_id = cmd_check(f"merge group {group_id_1} with group {group_id_2} group_results", "group")

        # if a new group is created, track the corresponding boundary
        if group_id:
            cmd(f'group {group_id} rename "{group_name}"')
            self.__track_as_boundary(group_name, group_id)

    def __track_as_boundary(self, group_name: str, group_id: int):
        self.boundaries.append(Group(group_name))
        group_surface_ids = cubit.get_group_surfaces(group_id)
        for group_surface_id in group_surface_ids:
            boundary = CubitInstance(group_surface_id, "surface")
            self.add_geometry_to_boundary(boundary, group_name)

    def organise_into_groups(self):
        '''create groups for material groups and boundary groups in cubit'''

        # create material groups group
        cmd('create group "materials"')
        for material in self.materials:
            cmd(f'group "materials" add group {material.group_id}')

        # create boundary group groups
        cmd('create group "boundaries"')
        boundaries_group_id = cubit.get_last_id("group")
        for boundary in self.boundaries:
            cmd(f'group "boundaries" add group {boundary.group_id}')
        # delete empty boundaries
        for group_id in cubit.get_group_groups(boundaries_group_id):
            if cubit.get_group_surfaces(group_id) == ():
                cmd(f"delete group {group_id}")

    def print_info(self):
        '''print cubit IDs of volumes in materials and surfaces in boundaries
        '''
        print("Materials:")
        for material in self.materials:
            material_vols = [i.cid for i in to_volumes(material.geometries)]
            print(f"{material.name}: Volumes {material_vols}")
        print("\nBoundaries:")
        for boundary in self.boundaries:
            boundary_surfs = [i.cid for i in boundary.geometries]
            print(f"{boundary.name}: Surfaces {boundary_surfs}")

    def update_tracking(self, old_geometry: CubitInstance, new_geometry: CubitInstance, material_name: str):
        '''change reference to a geometry currently being tracked

        :param old_geometry: geometry to replace
        :type old_geometry: CubitInstance
        :param new_geometry: geometry with which to replace
        :type new_geometry: CubitInstance
        :param material_name: name of material geometry belongs to
        :type material_name: str
        '''
        for material in self.materials:
            if material.name == material_name:
                for geometry in material.geometries:
                    if str(geometry) == str(old_geometry):
                        # update internally
                        material.geometries.remove(geometry)
                        material.geometries.append(CubitInstance(new_geometry.cid, new_geometry.geometry_type))
                        # update cubitside
                        cmd(f'group {material_name} remove {str(old_geometry)}')
                        cmd(f'group {material_name} add {str(new_geometry)}')

    def update_tracking_list(self, old_instances: list, new_instances: list, material_name: str):
        '''remove and adds geometries in a given material

        :param old_instances: list of geometries to replace
        :type old_instances: list
        :param new_instances: list of geometries with which to replace
        :type new_instances: list
        :param material_name: name of material geometries belong to
        :type material_name: str
        '''
        for material in self.materials:
            if material.name == material_name:
                for geometry in material.geometries:
                    for cubit_inst in old_instances:
                        if str(geometry) == str(cubit_inst):
                            material.geometries.remove(geometry)
                            cmd(f'group {material_name} remove {str(cubit_inst)}')
                for cubit_inst in new_instances:
                    material.geometries.append(cubit_inst)
                    cmd(f'group {material_name} add {str(cubit_inst)}')

    def stop_tracking_in_material(self, cubit_instance: CubitInstance, material_name: str):
        '''stop tracking a currently tracked geometry

        :param generic_cubit_instance: geometry to stop tracking
        :type generic_cubit_instance: CubitInstance
        :param material_name: name of material geometry belongs to
        :type material_name: str
        '''
        for material in self.materials:
            if material.name == material_name:
                for geometry in material.geometries:
                    if str(geometry) == str(cubit_instance):
                        material.geometries.remove(geometry)
                        cmd(f'group {material_name} remove {str(cubit_instance)}')

    def add_boundaries_to_sidesets(self):
        '''Add boundaries to cubit sidesets'''
        for boundary in self.boundaries:
            bound_surfs = boundary.get_surface_ids()
            if len(bound_surfs) > 0:
                cmd(f"sideset {boundary.group_id} add surface {bound_surfs}")
                cmd(f'sideset {boundary.group_id} name "{boundary.name}"')

    def add_materials_to_blocks(self):
        for material in self.materials:
            cmd(f"block {material.group_id} add volume {material.get_volume_ids()}")
            cmd(f'block {material.group_id} name "{material.name}"')

    def reset(self):
        self.materials = []
        self.boundaries = []

    def get_block_names(self):
        return [material.name for material in self.materials]

    def get_sideset_names(self):
        return [boundary.name for boundary in self.boundaries]


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
