from assemblies import *

class ComponentTracker:
    '''Adds components to cubit groups recursively'''
    # this counter is to ensure every component is named uniquely
    counter = 0
    def __init__(self, root_component) -> str:
        self.root_name = self.__track_components_as_groups(root_component)

    def __track_components_as_groups(self, root_component):
        '''Track volumes of components as groups (recursively)

        :param root_component: Component to track in
        :type root_component: Any Assembly or ComplexComponent
        :return: Name of group tracking the root component
        :rtype: str
        '''
        # if this is an external assembly its volumes should already belong to a group
        if isinstance(root_component, ExternalComponentAssembly):
            groupname = str(root_component.group)
        # if this is an assembly, run this function on each of its components
        elif isinstance(root_component, GenericComponentAssembly):
            groupname = self.__make_group_name(root_component.classname)
            for component in root_component.get_components():
                self.__add_to_group(groupname, self.__track_components_as_groups(component))
        # if this is a complex component, add volumes to group
        elif isinstance(root_component, ComplexComponent):
            groupname = self.__make_group_name(root_component.classname)
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
        groupname = f"{classname}{self.counter}"
        cmd(f'create group "{groupname}"')
        self.counter += 1
        return groupname
    
    def __add_to_group(self, group: str, thing_to_add):
        '''Add thing to group

        :param group: _description_
        :type group: str
        :param thing_to_add: geometry or name of group
        :type thing_to_add: GenericCubitInstance or str
        '''
        if type(thing_to_add) == str:
            cmd(f'group {group} add group {thing_to_add}')
        elif isinstance(thing_to_add, GenericCubitInstance):
            cmd(f'group {group} add {thing_to_add.geometry_type} {thing_to_add.cid}')
