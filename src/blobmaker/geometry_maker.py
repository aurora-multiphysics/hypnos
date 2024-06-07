from blobmaker.tracking import ComponentTracker, MaterialsTracker
from blobmaker.assemblies import construct
from blobmaker.generic_classes import CubismError, cmd
from blobmaker.cubit_functions import initialise_cubit, reset_cubit
from blobmaker.parsing import extract_data, ParameterFiller


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
        self.key_route_delimiter = '/'

    def fill_design_tree(self):
        '''Manually activate ParameterFiller to fill design tree parameters.

        :return: Filled design tree
        :rtype: dict
        '''
        self.design_tree = self.parameter_filler.process_design_tree(self.design_tree)
        if self.print_parameter_logs:
            self.parameter_filler.print_log()
        return self.design_tree

    def parse_json(self, filename: str):
        '''Parse a json file and add corresponding design tree to design_tree attribute

        :param filename: name of json file to parse
        :type filename: str
        :return: design tree corresponding to given json file
        :rtype: dict
        '''
        self.design_tree = extract_data(filename)
        return self.fill_design_tree()

    def change_delimiter(self, delimiter: str):
        '''Change the delimiter to use in key paths 
        for the change_params and get_param methods.
        By default the delimiter is '/'.

        :param delimiter: New delimiter
        :type delimiter: str
        '''
        self.key_route_delimiter = delimiter
        print(f"Delimiter changed to: {delimiter}")

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
        with '/' being the default delimiter.

        :param updated_params: {path : updated value} pairs
        :type updated_params: dict
        '''
        for param_path, updated_value in updated_params.items():
            if type(param_path) is not str:
                raise CubismError(f"path should be given as a string: {str(param_path)}")
            key_route = param_path.split(self.key_route_delimiter)
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
        with '/' being the default delimiter.

        :param param_path: path to parameter
        :type param_path: str
        :return: Value of parameter
        :rtype: any
        '''
        key_route = param_path.split(self.key_route_delimiter)
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
        '''Imprint and merge geometry in cubit. 
        '''
        cmd("imprint volume all")
        cmd("merge volume all")

    def track_components_and_materials(self):
        '''Add components to blocks and component-component interfaces to sidesets.
        Add materials and material-material interfaces to groups. 
        '''
        for component in self.constructed_geometry:
            self.component_tracker.give_identifiers(component)
            self.materials_tracker.extract_components(component)
        self.materials_tracker.track_boundaries()
        self.materials_tracker.organise_into_groups()

    def set_mesh_size(self, size: int):
        cmd(f'volume all size {size}')

    def tetmesh(self):
        '''Mesh geometry in cubit
        '''
        cmd('volume all scheme tet')
        cmd('mesh volume all')

    def export(self, format: str = "cubit", rootname: str = "geometry"):
        '''Export mesh/ geometry in specfied format

        :param format: Name of export format, defaults to "cubit"
        :type format: str, optional
        :param rootname: Name to give output file including path, defaults to "geometry"
        :type rootname: str, optional
        '''
        format = format.lower()
        if format == "cubit" or "cub5" in format:
            cmd(f'export cubit "{rootname}.cub5"')
        elif format == "exodus" or ".e" in format:
            print("The export_exodus method has more options for exodus file exports")
            cmd(f'export mesh "{rootname}.e"')
            print("The export_exodus method has more options for exodus file exports")
        elif format == "dagmc" or "h5m" in format:
            cmd(f'export dagmc "{rootname}.h5m"')
        elif format == "step" or "stp" in format:
            cmd(f'export Step "{rootname}.stp"')
        else:
            print("format not recognised")
            raise CubismError(f"Export format not recognised: {format}")
        print(f"exported {format} file")

    def export_exodus(self, rootname: str = "geometry", large_exodus= False, HDF5 = False):
        '''Export as exodus II file.

        :param rootname: Name to give output file including path, defaults to "geometry"
        :type rootname: str, optional
        :param large_exodus: Create a large model that can store individual datasets > 2GB, defaults to False
        :type large_exodus: bool, optional
        :param HDF5: Create a model that can store even larger files, defaults to False
        :type HDF5: bool, optional
        '''
        if large_exodus:
            cmd("set large exodus on")
        if HDF5:
            cmd("set exodus NetCDF4 on")
        cmd(f'export mesh "{rootname}.e"')

    def reset_cubit(self):
        '''Reset cubit and corresponding internal states.'''
        reset_cubit()
        self.materials_tracker.reset()
        self.component_tracker.reset_counter()
        self.constructed_geometry = []
    
    def file_to_tracked_geometry(self, filename: str):
        '''Parse json file, make geometry, imprint + merge it, track boundaries.

        :param filename: Name of file to parse
        :type filename: str
        '''
        self.parse_json(filename)
        self.make_geometry()
        self.imprint_and_merge()
        self.track_components_and_materials()
    
    def make_tracked_geometry(self):
        '''Make geometry, imprint and merge, track blocks + sidesets
        '''
        self.make_geometry()
        self.imprint_and_merge()
        self.track_components_and_materials()

