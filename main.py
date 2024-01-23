import sys
#import json
import argparse
#from constants import CLASS_MAPPING
from components import *
from assemblies import *
from cubit_functions import extract_data

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
        cubit.cmd(f'create group "{groupname}"')
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
            cubit.cmd(f'group {group} add group {thing_to_add}')
        elif isinstance(thing_to_add, GenericCubitInstance):
            cubit.cmd(f'group {group} add {thing_to_add.geometry_type} {thing_to_add.cid}')

def read_file(filename):
    '''Read in json file, construct all specified components

    :return: list of all top-level components
    :rtype: list
    '''
    objects = extract_data(filename)
    universe = []
    if type(objects) == list:
        for json_object in objects:
            universe.append(json_object_reader(json_object))
        return universe
    elif type(objects) == dict:
        universe.append(json_object_reader(objects))
        return universe
    raise CubismError("File not in readable format")

if __name__ == '__coreformcubit__':
    cubit.cmd("reset")
    read_file("sample_morphology.json")
elif __name__ == "__main__":
    # accept command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--file", type=str, help="name of json file describing geometry", default="sample_blanket_ring.json")
    parser.add_argument("-c", "--cubitpath", type=str, help="path of the cubit python library", default='/opt/Coreform-Cubit-2023.8/bin')
    parser.add_argument("-i", "--info", action="store_true")
    args = parser.parse_args()

    # if this is run as a python file, import cubit
    sys.path.append(args.cubitpath)
    import cubit
    cubit.init(['cubit', '-nojournal'])

    universe = read_file(args.file)
    # track all components, materials, and boundaries as groups
    for component in universe:
        print(f"components being tracked in root {ComponentTracker(component).root_name}")
    #cubit.cmd("imprint volume all")
    #MaterialsTracker().merge_and_track_boundaries()
    #cubit.cmd("merge volume all")
    #MaterialsTracker().add_boundaries_to_sidesets()
    #MaterialsTracker().organise_into_groups()

    cubit.cmd('export cubit "please_work.cub5')
    # print this information if cli flag used
    if args.info:
        MaterialsTracker().print_info()
#    cubit.cmd('volume all scheme auto')
#    cubit.cmd('mesh volume all')
#    cubit.cmd('export genesis "testblob.g"')
