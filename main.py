import argparse
from component_tracker import ComponentTracker
from assemblies import *
from cubit_functions import initialise_cubit, reset_cubit
from parsing import extract_data, ParameterFiller
from default_params import DEFAULTS
import pprint

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
    parser.add_argument("-f", "--file", type=str, help="Name of json file describing geometry", default="sample_blanket.json")
    parser.add_argument("-i", "--info", type=str, help="Print cubit IDs of volumes in materials and surfaces in boundaries", default='false')
    parser.add_argument("-c", "--classname", type=str, help="Get available classes", default='none')
    args = parser.parse_args()

    if args.classname != 'none':
        if args.classname not in [default_class["class"] for default_class in DEFAULTS]:
            print("The available classes are:")
            for default_class in DEFAULTS:
                print(default_class["class"])
        for default_class in DEFAULTS:
            if default_class["class"] == args.classname:
                print(f"The parameters and defaults for class {args.classname} are: ")
                pp = pprint.PrettyPrinter(indent=4)
                pp.pprint(default_class)
        exit(0)

    
    initialise_cubit()

    json_object = extract_data(args.file)
    filled_json_object = ParameterFiller().process_defaults(json_object)
    ParameterFiller().print_log()
    universe = make_everything(filled_json_object)
    # track all components, materials, and boundaries as groups
    for component in universe:
        print(f"components being tracked in root {ComponentTracker(component).root_name}")
    if IMPRINT_AND_MERGE:
        materials_tracker = MaterialsTracker()
        cmd("imprint volume all")
        materials_tracker.merge_and_track_boundaries()
        cmd("merge volume all")
        materials_tracker.add_boundaries_to_sidesets()
        materials_tracker.organise_into_groups()

    cmd('export cubit "please_work.cub5')
    # print this information if cli flag used
    if args.info == 'true':
        MaterialsTracker().print_info()
    if MESH:
        cmd('volume all scheme tet')
        cmd('mesh volume all')
        cmd('export genesis "hcpb_meshed.g"')
