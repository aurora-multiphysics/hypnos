from generic_classes import *
from cubit_functions import from_bodies_and_volumes_to_surfaces, from_bodies_to_volumes, cubit_cmd_check

# Classes to track materials and geometries made of those materials
class Material:
    '''Tracks cubit instances made of this material.
    '''
    def __init__(self, name: str, group_id: int) -> None:
        self.name = name
        self.group_id = group_id
        # should only store GenericCubitInstances
        self.geometries = []
        # currently does nothing
        self.state_of_matter = ""
    
    def add_geometry(self, geometry):
        if isinstance(geometry, GenericCubitInstance):
            self.geometries.append(geometry)
        else:
            raise CubismError("Not a GenericCubitInstance???")
    
    def change_state(self, state: str):
        self.state_of_matter = state
    
    def get_surface_ids(self):
        return [i.cid for i in from_bodies_and_volumes_to_surfaces(self.geometries)]
    
    def get_volume_ids(self):
        return [i.cid for i in from_bodies_to_volumes(self.geometries)]

class MaterialsTracker:
    '''Tracks materials and boundaries between those materials (including nullspace)
    '''
    #i think i want materials to be tracked globally
    materials = []
    boundaries = []

    def make_material(self, material_name: str, group_id: int):
        '''Add material to internal list. Will not add if material name already exists

        :param material_name: Name of material
        :type material_name: str
        :param group_id: Cubit ID of group
        :type group_id: int
        '''
        if material_name not in [i.name for i in self.materials]:
            self.materials.append(Material(material_name, group_id))
    
    def add_geometry_to_material(self, geometry: GenericCubitInstance, material_name: str):
        '''Add geometry to material and track in cubit.

        :param geometry: Geometry to add
        :type geometry: GenericCubitInstance
        :param material_name: name of material to add geometry to
        :type material_name: str
        :return: True or raises error
        '''
        cmd(f'group "{material_name}" add {geometry.geometry_type} {geometry.cid}')
        group_id = cubit.get_id_from_name(material_name)
        self.make_material(material_name, group_id)

        # Add geometry to appropriate material. If it can't something has gone wrong
        for material in self.materials:
            if material.name == material_name:
                material.add_geometry(geometry)
                return True
        return CubismError("Could not add component")

    def contains_material(self, material_name):
        '''Check for the existence of a material

        :param material_name: name of material to check for
        :type material_name: str
        :return: True or False
        :rtype: bool
        '''
        return True if material_name in [i.name for i in self.materials] else False
    
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
            min_counter+=1
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
    
    def add_geometry_to_boundary(self, geometry: GenericCubitInstance, boundary_name: str):
        '''If boundary exists, add geometry to it

        :param geometry: geometry to add
        :type geometry: GenericCubitInstance
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
        '''tries to merge every possible pair of materials, and tracks the resultant material boundaries (if any exist).'''
        pair_list = self.sort_materials_into_pairs()
        #intra-group merge
        for material in self.materials:
            self.__merge_and_track_between(material, material)

        #try to merge volumes in every pair of materials
        for (material1, material2) in pair_list:
            self.__merge_and_track_between(material1, material2)
        
        # track material-air boundaries

        # collect every unmerged surface because only these are in contact with air?
        cmd('group "unmerged_surfaces" add surface with is_merged=0')
        unmerged_group_id = cubit.get_id_from_name("unmerged_surfaces")
        all_unmerged_surfaces = cubit.get_group_surfaces(unmerged_group_id)
        # look at every collected material
        for material in self.materials:
            # setup group and tracking for interface with air
            boundary_name = material.name + "_air"
            boundary_id = cubit_cmd_check(f'create group "{boundary_name}"', "group")
            self.boundaries.append(Material(boundary_name, boundary_id))
            # look at every surface of this material
            material_surface_ids = material.get_surface_ids()
            # if this surface is unmerged, it is in contact with air so add it to the boundary
            for material_surface_id in material_surface_ids:
                if material_surface_id in all_unmerged_surfaces:
                    cmd(f'group "{boundary_name}" add surface {material_surface_id}')
                    self.add_geometry_to_boundary(GenericCubitInstance(material_surface_id, "surface"), boundary_name)
                    
        cmd(f'delete group {unmerged_group_id}')

    def __merge_and_track_between(self, material1: Material, material2: Material):
        group_id_1 = material1.group_id
        group_id_2 = material2.group_id
        group_name = str(material1.name) + "_" + str(material2.name)

        # is new group created when trying to merge?
        group_id = cubit_cmd_check(f"merge group {group_id_1} with group {group_id_2} group_results", "group")

        # if a new group is created, track the material boundary it corresponds to
        if group_id:
            cmd(f'group {group_id} rename "{group_name}"')
            self.__track_as_boundary(group_name, group_id)

    def __track_as_boundary(self, group_name: str, group_id: int):
        self.boundaries.append(Material(group_name, group_id))
        group_surface_ids = cubit.get_group_surfaces(group_id)
        for group_surface_id in group_surface_ids:
            self.add_geometry_to_boundary(GenericCubitInstance(group_surface_id, "surface"), group_name)
    
    def organise_into_groups(self):
        '''create groups for material groups and boundary groups in cubit'''

        # create material groups group
        cmd('create group "materials"')
        material_group_id = cubit.get_last_id("group") # in case i need to do something similar to boundaries later
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
        '''print cubit IDs of volumes in materials and surfaces in boundaries'''
        print("Materials:")
        for material in self.materials:
            print(f"{material.name}: Volumes {[i.cid for i in from_bodies_to_volumes(material.geometries)]}")
        print("\nBoundaries:")
        for boundary in self.boundaries:
            print(f"{boundary.name}: Surfaces {[i.cid for i in boundary.geometries]}")

    def update_tracking(self, old_geometry: GenericCubitInstance, new_geometry: GenericCubitInstance, material_name: str):
        '''change reference to a geometry currently being tracked

        :param old_geometry: geometry to replace
        :type old_geometry: GenericCubitInstance
        :param new_geometry: geometry with which to replace
        :type new_geometry: GenericCubitInstance
        :param material_name: name of material geometry belongs to
        :type material_name: str
        '''
        for material in self.materials:
            if material.name == material_name:
                for geometry in material.geometries:
                    if (geometry.geometry_type == old_geometry.geometry_type) and (geometry.cid == old_geometry.cid):
                        # update internally
                        material.geometries.remove(geometry)
                        material.geometries.append(GenericCubitInstance(new_geometry.cid, new_geometry.geometry_type))
                        # update cubitside
                        cmd(f'group {material_name} remove {old_geometry.geometry_type} {old_geometry.cid}')
                        cmd(f'group {material_name} add {new_geometry.geometry_type} {new_geometry.cid}')

    def update_tracking_list(self, old_instances: list, new_instances: list, material_name: str):
        '''remove and adds references to specified GenericCubitInstances in a given material

        :param old_instances: list of GenericCubitInstances to replace
        :type old_instances: list
        :param new_instances: list of GenericCubitInstances with which to replace
        :type new_instances: list
        :param material_name: name of material geometries belong to
        :type material_name: str
        '''
        for material in self.materials:
            if material.name == material_name:
                for geometry in material.geometries:
                    for generic_cubit_instance in old_instances:
                        if isinstance(generic_cubit_instance, GenericCubitInstance):
                            if (geometry.geometry_type == generic_cubit_instance.geometry_type) and (geometry.cid == generic_cubit_instance.cid):
                                material.geometries.remove(geometry)
                                cmd(f'group {material_name} remove {generic_cubit_instance.geometry_type} {generic_cubit_instance.cid}')
                for generic_cubit_instance in new_instances:
                    if isinstance(generic_cubit_instance, GenericCubitInstance):
                        material.geometries.append(generic_cubit_instance)
                        cmd(f'group {material_name} add {generic_cubit_instance.geometry_type} {generic_cubit_instance.cid}')

    def stop_tracking_in_material(self, generic_cubit_instance: GenericCubitInstance, material_name: str):
        '''stop tracking a currently tracked geometry

        :param generic_cubit_instance: geometry to stop tracking
        :type generic_cubit_instance: GenericCubitInstance
        :param material_name: name of material geometry belongs to
        :type material_name: str
        '''
        for material in self.materials:
            if material.name == material_name:
                for geometry in material.geometries:
                    if (geometry.geometry_type == generic_cubit_instance.geometry_type) and (geometry.cid == generic_cubit_instance.cid):
                        material.geometries.remove(geometry)
                        cmd(f'group {material_name} remove {generic_cubit_instance.geometry_type} {generic_cubit_instance.cid}')

    def add_boundaries_to_sidesets(self):
        '''Add boundaries to cubit sidesets'''
        for boundary in self.boundaries:
            if len(boundary.get_surface_ids()) > 0:
                cmd(f"sideset {boundary.group_id} add surface {boundary.get_surface_ids()}")
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