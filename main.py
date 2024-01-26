import argparse
from component_tracker import ComponentTracker
from assemblies import *
from cubit_functions import initialise_cubit, reset_cubit
from parsing import extract_data

def read_file(filename):
    '''Read in json file, construct all specified components

    :return: list of all top-level components
    :rtype: list
    '''
    objects = extract_data(filename)
    universe = []
    if type(objects) == list:
        for json_object in objects:
            universe.append(construct(json_object))
        return universe
    elif type(objects) == dict:
        universe.append(construct(objects))
        return universe
    raise CubismError("File not in readable format")

if __name__ == '__coreformcubit__':
    reset_cubit()
    read_file("sample_morphology.json")
elif __name__ == "__main__":
    # accept command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--file", type=str, help="name of json file describing geometry", default="sample_blanket_ring.json")
    parser.add_argument("-i", "--info", action="store_true")
    args = parser.parse_args()

    initialise_cubit()

    universe = read_file(args.file)
    # track all components, materials, and boundaries as groups
    for component in universe:
        print(f"components being tracked in root {ComponentTracker(component).root_name}")
    #cmd("imprint volume all")
    #MaterialsTracker().merge_and_track_boundaries()
    #cmd("merge volume all")
    #MaterialsTracker().add_boundaries_to_sidesets()
    #MaterialsTracker().organise_into_groups()

    cmd('export cubit "please_work.cub5')
    # print this information if cli flag used
    if args.info:
        MaterialsTracker().print_info()
#    cmd('volume all scheme auto')
#    cmd('mesh volume all')
#    cmd('export genesis "testblob.g"')
