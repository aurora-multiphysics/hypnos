import sys
import json
import argparse
from constants import CLASS_MAPPING
from components import *
from assemblies import *

if __name__ == "__main__":
    # if this is run as a python file, import cubit
    sys.path.append('/opt/Coreform-Cubit-2023.8/bin')
    import cubit
    cubit.init(['cubit', '-nojournal'])

    # accept command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--file", type=str, help="name of json file", default="sample_morphology.json")
    parser.add_argument("-p", "--printinfo", action="store_true")
    args = parser.parse_args()

    # File to look at
    JSON_FILENAME = args.file
elif __name__ == "__coreformcubit__":
    # if this is cubit, reset first
    cubit.cmd("reset")
    JSON_FILENAME = "sample_morphology.json"

class ComponentTracker:
    '''Adds components to cubit groups recursively'''
    # this counter is to ensure every component is named uniquely
    counter = 0

    def track_components_as_groups(self, root_component):
        # if this is an external assembly its volumes should already belong to a group, return that name
        if isinstance(root_component, ExternalComponentAssembly):
            return str(root_component.group)
        # if this is an assembly, run this function on each component of every attribute
        elif isinstance(root_component, GenericComponentAssembly):
            groupname = f"{root_component.classname}{self.counter}"
            cubit.cmd(f'create group "{groupname}"')
            self.counter += 1
            for attribute in root_component.component_mapping.values():
                for component in attribute:
                    # need this function to return the group name it adds components to
                    component_groupname = self.track_components_as_groups(component)
                    if type(groupname) == str:
                        cubit.cmd(f'group {groupname} add group {component_groupname}')
            # pass up group name
            return groupname
        # if this is a complex component, add volumes to group
        elif isinstance(root_component, ComplexComponent):
            groupname = f"{root_component.classname}{self.counter}"
            cubit.cmd(f'create group "{groupname}"')
            self.counter += 1
            for geometry in root_component.subcomponents:
                if isinstance(geometry, GenericCubitInstance):
                    cubit.cmd(f'group {groupname} add {geometry.geometry_type} {geometry.cid}')#
            # pass up group name
            return groupname

def read_file():
    '''Read in json file, construct all specified components

    :return: list of all top-level components
    :rtype: list
    '''
    with open(JSON_FILENAME) as jsonFile:
        data = jsonFile.read()
        objects = json.loads(data)
    universe = []
    for json_object in objects:
        universe.append(json_object_reader(json_object=json_object))
    return universe

if __name__ == '__coreformcubit__':
    read_file()
elif __name__ == "__main__":
    universe = read_file()
    # track all components as groups
    for component in universe:
        root_name = ComponentTracker().track_components_as_groups(component)
        print(f"components being tracked in root {root_name}")
    # track all materials and boundaries as groups
    MaterialsTracker().organise_into_groups()
    cubit.cmd('export cubit "please_work.cub5')
    # print this information if cli flag used
    if args.printinfo:
        MaterialsTracker().print_info()
    pass
#       cubit.cmd('volume all scheme auto')
#       cubit.cmd('mesh volume all')
#       cubit.cmd('export genesis "testblob.g"')
