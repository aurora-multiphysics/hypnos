from blobmaker.tracking import ComponentTracker, MaterialsTracker
from blobmaker.assemblies import construct
from blobmaker.generic_classes import CubismError, cmd
from blobmaker.cubit_functions import initialise_cubit, reset_cubit
from blobmaker.parsing import extract_data, ParameterFiller
from blobmaker.default_params import DEFAULTS
from blobmaker.constants import IMPRINT_AND_MERGE, MESH
import shutil


def make_everything(json_object):
    '''Construct all specified components

    :return: list of all top-level components
    :rtype: list
    '''
    if type(json_object) is list:
        return [construct(json_component) for json_component in json_object]
    elif type(json_object) is dict:
        return [construct(json_object)]
    raise CubismError("json object not recognised")


class GeometryMaker():
    def __init__(self) -> None:
        initialise_cubit()
        self.parameter_filler = ParameterFiller()
        self.materials_tracker = MaterialsTracker()
        self.component_tracker = ComponentTracker()
        self.design_tree = {}
        self.constructed_geometry = []
        self.print_parameter_logs = False
        self.track_components = False

    def parse_json(self, filename: str):
        '''Parse a json file and add corresponding design tree to design_tree attribute

        :param filename: name of json file to parse
        :type filename: str
        :return: design tree corresponding to given json file
        :rtype: dict
        '''
        json_object = extract_data(filename)
        filled_json_object = self.parameter_filler.process_design_tree(json_object)
        if self.print_parameter_logs:
            self.parameter_filler.print_log()
        self.design_tree = filled_json_object
        return filled_json_object

    def change_params(self, updated_params: dict):
        '''Change parameters in stored design tree.
        A parameter is referenced using it's path.
        This path is a string of the keys that are used to access that parameter in the json file.

        For example to change the value of the parameter 'pin spacing' to 135 here:
        {
            "class": "hcpb_blanket",
            "geometry": {
            "pin spacing": 100
            }
        }

        The argument provided here would have to be {"geometry/pin spacing": 135}

        :param updated_params: {path : updated value} pairs
        :type updated_params: dict
        '''
        for param_path, updated_value in updated_params.items():
            assert type(param_path) is str
            key_route = param_path.split('/')
            self.design_tree = self.__build_param_dict(key_route, self.design_tree, updated_value)

    def get_param(self, param_path: str):
        '''Get parameter in stored design tree.
        A parameter is referenced using it's path.

        For example to get the value of the parameter 'pin spacing' here:
        {
            "class": "hcpb_blanket",
            "geometry": {
            "pin spacing": 100
            }
        }

        The argument provided here would have to be "geometry/pin spacing"

        :param param_path: path to parameter
        :type param_path: str
        :return: Value of parameter
        :rtype: any
        '''
        key_route = param_path.split('/')
        return self.__follow_key_route(key_route, self.design_tree)

    def __follow_key_route(self, key_route: list[str], param_dict: dict):
        if key_route[0] not in param_dict.keys():
            raise CubismError("Path given does not correspond to existing parameters")
        if len(key_route) == 1:
            return param_dict[key_route[0]]
        return self.__follow_key_route(key_route[1:], param_dict[key_route[0]])

    def __build_param_dict(self, key_route: list, param_dict: dict, updated_value):
        if len(key_route) == 0:
            return updated_value
        if key_route[0] not in param_dict.keys():
            raise CubismError("Path given does not correspond to existing parameters")
        param_dict[key_route[0]] = self.__build_param_dict(key_route[1:], param_dict[key_route[0]], updated_value)
        return param_dict

    def make_geometry(self):
        '''Build geometry corresponding to design tree in cubit

        :return: Constructed geometry
        :rtype: Python class corresponding to top-level of design tree
        '''
        self.constructed_geometry = make_everything(self.design_tree)
        if self.track_components:
            for component in self.constructed_geometry:
                self.component_tracker.track_component(component)
                print(f"components being tracked in root {self.component_tracker.root_name}")
        return self.constructed_geometry

    def imprint_and_merge(self):
        '''Imprint and merge geometry in cubit. Add materials to blocks and material-material interfaces to sidesets.
        '''
        for component in self.constructed_geometry:
            self.component_tracker.give_identifiers(component)
            self.materials_tracker.extract_components(component)
        cmd("imprint volume all")
        cmd("merge volume all")
        self.materials_tracker.track_boundaries()
        self.materials_tracker.add_blocks()
        self.materials_tracker.add_sidesets()
        self.materials_tracker.organise_into_groups()

    def set_mesh_size(self, size: int):
        cmd(f'volume all size {size}')

    def tetmesh(self):
        '''Mesh geometry in cubit
        '''
        cmd('volume all scheme tet')
        cmd('mesh volume all')

    def export_geometry(self, filename= 'out_geometry.cub5', destination='.'):
        cmd(f'export cubit "{filename}"')
        shutil.move(f"./{filename}", f"{destination}/{filename}")

    def export_mesh(self, filename='out_mesh.e', destination='.'):
        '''Export exodus II file of mesh, as well as blocks and sidesets.

        :param filename: name of file to output, defaults to 'out_mesh.e'
        :type filename: str, optional
        :param destination: destination to create file, defaults to '.'
        :type destination: str, optional
        '''
        cmd(f'export mesh "{filename}"')
        shutil.move(f"./{filename}", f"{destination}/{filename}")

    def reset_cubit(self):
        '''Reset cubit and corresponding internal states.'''
        reset_cubit()
        self.materials_tracker.reset()
        self.component_tracker.reset_counter()
        self.constructed_geometry = []

