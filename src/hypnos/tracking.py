'''
tracking.py
author(s): Sid Mungale

Tracks blocks, sidesets, and groups for components and their boundaries

(c) Copyright UKAEA 2024
'''

from hypnos.components import SimpleComponent
from hypnos.assemblies import GenericComponentAssembly
from hypnos.generic_classes import CubismError, cubit, cmd
from hypnos.cubit_functions import to_surfaces, add_to_new_entity


class Tracker:
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
        self.external_separator = "_"  # in cubit
        self.internal_separator = "---"  # internally
        # counts how many of each component type we have
        self.identifiers = {}

    def extract_components(self, root_component):
        '''Get all components stored in root and their materials.

        Parameters
        ----------
        root_component : SimpleComponent | GenericComponentAssembly
            component to track
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
        Add simple components to blocks and groups.
        Add component interfaces to sidesets and groups.
        '''
        # surface ID : [index of component on either side of surface]
        surface_to_comp_id = {}
        # material : [volumes made of material]
        material_to_volumes = {}

        # For each component we want to keep track of
        # 1) The material its volumes are made of
        # 2) Its surface IDs
        # This is used to populate the above dictionaries
        for idx, component in enumerate(self.components):
            # initialise
            if component.material not in material_to_volumes.keys():
                material_to_volumes[component.material] = []
            # add volumes to corresponding materials
            material_to_volumes[component.material].append(component.volume_id_string())

            for surf_id in [surface.cid for surface in to_surfaces(component.get_geometries())]:
                # initialise
                if surf_id not in surface_to_comp_id:
                    surface_to_comp_id[surf_id] = []
                surface_to_comp_id[surf_id].append(idx)

        # x_to_sidesets = x : {sidesets belonging to boundary type x}.
        # Here x is either component1_component2 or material1_material2
        components_to_sidesets = {}
        materials_to_sidesets = {}

        # x_to_surfaces = name of boundary: [surface IDs belonging to boundary]
        component_to_surfaces = {}
        material_to_surfaces = {}

        for surf_id, comp_ids in surface_to_comp_id.items():
            # get components
            comps = [self.components[idx] for idx in comp_ids]
            # make various boundary names
            sideset_name = self.make_boundary_name([comp.identifier for comp in comps])
            material_boundary_name = self.make_boundary_name([comp.material for comp in comps])
            mat_boundary_internal = self.make_boundary_name([comp.material for comp in comps], True)
            type_boundary_internal = self.make_boundary_name([comp.classname for comp in comps], True)

            # initialise
            if type_boundary_internal not in components_to_sidesets.keys():
                components_to_sidesets[type_boundary_internal] = []
            if mat_boundary_internal not in materials_to_sidesets.keys():
                materials_to_sidesets[mat_boundary_internal] = []
            if sideset_name not in component_to_surfaces.keys():
                component_to_surfaces[sideset_name] = []
            if material_boundary_name not in material_to_surfaces.keys():
                material_to_surfaces[material_boundary_name] = []

            # these are used internally for queries
            components_to_sidesets[type_boundary_internal].append(sideset_name)
            materials_to_sidesets[mat_boundary_internal].append(sideset_name)
            # these are used to add entities to cubit
            component_to_surfaces[sideset_name].append(surf_id)
            material_to_surfaces[material_boundary_name].append(surf_id)

        # create cubit materials for DAGMC
        for material in self.materials:
            cmd(f'create material name "{material}"')

        # add blocks for each simple component
        for component in self.components:
            entity_id = cubit.get_next_block_id()
            cmd(f"create block {entity_id}")
            cmd(f'block {entity_id} name "{component.identifier}"')
            cmd(f'block {entity_id} add volume {component.volume_id_string()}')
            cmd(f'block {entity_id} material "{component.material}"')
            add_to_new_entity("group", component.identifier, "volume", component.volume_id_string())

        # add groups for each material
        for material_name, vol_id_strings in material_to_volumes.items():
            add_to_new_entity("group", material_name, "volume", vol_id_strings)

        # add sidesets corresponding to the simple components (comp1_comp2)
        for boundary_name, surf_ids in component_to_surfaces.items():
            add_to_new_entity("sideset", boundary_name, "surface", surf_ids)
            add_to_new_entity("group", boundary_name, "surface", surf_ids)

        # add groups corresponding to the material (mat1_mat2)
        for boundary_name, surf_ids in material_to_surfaces.items():
            add_to_new_entity("group", boundary_name, "surface", surf_ids)

        # info for querying purposes
        self.sidesets = list(component_to_surfaces.keys())
        self.material_boundaries = list(material_to_surfaces.keys())
        self.blocks = [comp.identifier for comp in self.components]
        self.materials_to_sidesets = materials_to_sidesets
        self.types_to_sidesets = components_to_sidesets

    def make_boundary_name(self, parts_of_name: list[str], internal=False) -> str:
        '''Generate a standardised boundary name

        Parameters
        ----------
        parts_of_name : list[str]
            list of components or materials
        internal : bool, optional
            whether this name is only to be used internally, by default False

        Returns
        -------
        str
            standardised boundary name
        '''
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
        '''Reset internal state
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
        self.identifiers = {}

    def get_blocks(self) -> list[str]:
        '''Get names of created blocks. Blocks are named
        the same as their corresponding simple components.
        For example the block corresponding to coolant0 is
        named coolant0.

        Returns
        -------
        list[str]
            list of block names
        '''
        return self.blocks

    def get_sidesets(self) -> list[str]:
        '''Get names of created sidesets.
        Sidesets are named according to the names of the simple
        components on either side. For example the sideset between
        coolant0 and cladding0 is coolant0_cladding0. Sidesets not
        at interfaces are named like <component_name>_air.

        Returns
        -------
        list[str]
            list of sideset names
        '''
        return self.sidesets

    def get_blocks_of_material(self, material: str) -> list[str]:
        '''Get blocks of simple components made of specified material

        Parameters
        ----------
        material : str
            name of material

        Returns
        -------
        list[str]
            block names made of that material
        '''
        return [component.identifier for component in self.components if component.material == material]

    def get_block_types(self) -> list[str]:
        '''Get block types. These are the same as the types of simple components.
        For example the type of coolant1 is coolant.

        Returns
        -------
        list[str]
            list of block types
        '''
        return list({comp.classname for comp in self.components})

    def get_sidesets_between_components(self, *types: str) -> list[str]:
        '''Get sidesets between specified simple component types.
        Providing only 1 type will assume that the other side of the
        interface is 'air'

        Returns
        -------
        list[str]
            list of sidesets
        '''
        if not 0 < len(types) <= 2:
            print("No boundaries can exist between provided number of types")
            return None
        type_ref = self.make_boundary_name(list(types), True)
        if type_ref not in self.types_to_sidesets.keys():
            print(f"No boundaries exist: {types}")
            return None
        return list(self.types_to_sidesets[type_ref])

    def get_sidesets_between_materials(self, *materials: str) -> list[str]:
        '''Get all sidesets between components made of these materials.
        Providing only 1 material will assume the other to be 'air'.

        Returns
        -------
        list[str]
            list of sidesets
        '''
        if not 0 < len(materials) <= 2:
            print("No boundaries can exist between provided number of types")
            return None
        type_ref = self.make_boundary_name(list(materials), True)
        if type_ref not in self.materials_to_sidesets.keys():
            print(f"No boundaries exist: {materials}")
            return None
        return list(self.materials_to_sidesets[type_ref])

    def give_identifiers(self, root_component):
        '''Give every component a unique identifier recursively,
        if it doesn't already have one

        Parameters
        ----------
        root_component : GenericComponentAssembly
            top-level component class
        '''
        # if this is a simple component, give it a unique identifier
        if isinstance(root_component, SimpleComponent):
            self.__name_component(root_component)
        # if this is an assembly, also recurse to children components
        elif isinstance(root_component, GenericComponentAssembly):
            self.__name_component(root_component)
            for component in root_component.get_components():
                self.give_identifiers(component)
        else:
            raise CubismError(f'Component not recognised: {root_component}')

    def __name_component(self, comp):
        '''If component doesn't already have a unique identifier, give it one

        Parameters
        ----------
        root_component : GenericComponentAssembly | SimpleComponent
            component_to_name
        '''
        classname = comp.classname
        # by default the identifier attribute is set to the classname
        if classname == comp.identifier:
            if classname in self.identifiers.keys():
                self.identifiers[classname] += 1
            else:
                self.identifiers[classname] = 0
            comp.identifier = f"{classname}{self.identifiers[classname]}"
