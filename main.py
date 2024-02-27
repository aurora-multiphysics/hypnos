from component_tracker import ComponentTracker
from assemblies import *
from cubit_functions import initialise_cubit, reset_cubit
from parsing import extract_data, ParameterFiller
from default_params import DEFAULTS
import pprint, argparse, shutil

def make_everything(json_object):
    '''Construct all specified components

    :return: list of all top-level components
    :rtype: list
    '''
    if type(json_object) == list:
        return [construct(json_component) for json_component in json_object]
    elif type(json_object) == dict:
        return [construct(json_object)]
    raise CubismError("json object not recognised")

class GeometryMaker():
    def __init__(self) -> None:
        initialise_cubit()
        self.parameter_filler = ParameterFiller()
        self.materials_tracker = MaterialsTracker()
        self.design_tree = {}
        self.print_parameter_logs = False
        self.print_boundary_info = False

    def parse_json(self, filename):
        json_object = extract_data(filename)
        filled_json_object = json_object
        #TODO: FIX PARAMETER FILLER
        #filled_json_object = self.parameter_filler.process_defaults(json_object)
        if self.print_parameter_logs:
            self.parameter_filler.print_log()
        self.design_tree = filled_json_object
        return filled_json_object

    def change_params(self, updated_params: dict):
        for param_path, updated_value in updated_params.items():
            assert type(param_path) == str
            key_route = param_path.split('/')
            self.design_tree = self.__build_param_dict(key_route, self.design_tree, updated_value)

    def __build_param_dict(self, key_route: list, param_dict: dict, updated_value):
        if len(key_route) == 0:
            return updated_value
        param_dict[key_route[0]] = self.__build_param_dict(key_route[1:], param_dict[key_route[0]], updated_value)
        return param_dict

    def make_geometry(self):
        return make_everything(self.design_tree)
    
    def imprint_and_merge(self):
        cmd("imprint volume all")
        self.materials_tracker.merge_and_track_boundaries()
        cmd("merge volume all")
        self.materials_tracker.add_boundaries_to_sidesets()
        self.materials_tracker.organise_into_groups()
        if self.print_boundary_info:
            self.materials_tracker.print_info()

    def tetmesh(self):
        cmd('volume all scheme tet')
        cmd('mesh volume all')
    
    def export_geometry(self, filename= 'out_geometry.cub5', destination='.'):
        cmd(f'export cubit "{filename}"')
        shutil.move(f"./{filename}", f"{destination}/{filename}")
    
    def export_mesh(self, filename='out_mesh.e', destination='.'):
        cmd(f'export mesh "{filename}"')
        shutil.move(f"./{filename}", f"{destination}/{filename}")

    def reset_cubit(self):
        reset_cubit()
        self.materials_tracker.reset()

if __name__ == '__coreformcubit__':
    reset_cubit()
    make_everything(extract_data("sample_morphology.json"))
elif __name__ == "__main__":
    # accept command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--file", type=str, help="Name of json file describing geometry", default="sample_blanket.json")
    parser.add_argument("-i", "--info", type=str, help="Print cubit IDs of volumes in materials and surfaces in boundaries", default='false')
    parser.add_argument("-c", "--classname", type=str, help="Get available classes", default='none')
    parser.add_argument("-o", "--outputfilename", type=str, help="Name of output file", default='out_geometry.cub5')
    parser.add_argument("-d", "--destination", type=str, help="path of directory to generate output file in", default='.')
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
    
    maker = GeometryMaker()
    maker.print_parameter_logs = True
    maker.parse_json(args.file)
    universe = maker.make_geometry()

    # track all components, materials, and boundaries as groups
    for component in universe:
        print(f"components being tracked in root {ComponentTracker(component).root_name}")
    if IMPRINT_AND_MERGE:
        maker.imprint_and_merge()
    maker.export_geometry(args.outputfilename, args.destination)

    # print this information if cli flag used
    if args.info == 'true':
        MaterialsTracker().print_info()
    if MESH:
        maker.tetmesh()
        cmd('export mesh "meshed.e"')
