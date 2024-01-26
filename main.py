import argparse
from component_tracker import ComponentTracker
from assemblies import *
from cubit_functions import initialise_cubit, reset_cubit
from parsing import extract_data, ParameterFiller

def make_everything(json_object):
    '''Construct all specified components

    :return: list of all top-level components
    :rtype: list
    '''
    universe = []
    if type(json_object) == list:
        for json_component in json_object:
            universe.append(construct(json_component))
        return universe
    elif type(json_object) == dict:
        universe.append(construct(json_object))
        return universe
    raise CubismError("json object not recognised")

if __name__ == '__coreformcubit__':
    reset_cubit()
    make_everything(extract_data("sample_morphology.json"))
elif __name__ == "__main__":
    # accept command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--file", type=str, help="name of json file describing geometry", default="sample_blanket.json")
    parser.add_argument("-i", "--info", action="store_true")
    args = parser.parse_args()

    initialise_cubit()

    json_object = extract_data(args.file)
    filled_json_object = ParameterFiller().process_defaults(json_object)
    ParameterFiller().print_log()
    universe = make_everything(filled_json_object)
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
