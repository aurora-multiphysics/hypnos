'''
geometry_maker.py
author(s): Sid Mungale

Python interface to access program functionality

(c) Copyright UKAEA 2024
'''

from hypnos.tracking import Tracker
from hypnos.assemblies import construct
from hypnos.generic_classes import CubismError, cmd
from hypnos.cubit_functions import initialise_cubit, reset_cubit
from hypnos.parsing import extract_data, ParameterFiller, get_format_extension, Config
import functools


def make_everything(json_object):
    '''Construct all specified components

    Parameters
    ----------
    json_object : dict or list
        Description of geometry(ies) to construct in cubit

    Returns
    -------
    Class corresponding to constructed geometry
    '''
    if type(json_object) is list:
        return [construct(json_component) for json_component in json_object]
    elif type(json_object) is dict:
        return [construct(json_object)]
    raise CubismError("json object not recognised")


def log_method(method_name: str):
    '''Decorator to print logs for class methods

    :param method_name: Name of task the method will perform
    :type method_name: str
    '''
    def decorator_log(func):
        @functools.wraps(func)
        def wrapper_logger(*args, **kwargs):
            print(f"Starting: {method_name}")
            to_return = func(*args, **kwargs)
            print(f"Finished: {method_name}")
            return to_return
        return wrapper_logger
    return decorator_log


class GeometryMaker():
    '''Access Hypnos functionality

    Attributes
    ----------
    parameter_filler: Handles processing of json files
    tracker: handles tracking groups, blocks, and sidesets in cubit
    design_tree (dict): Parameters for constructing geometry
    constructed_geometry (list): Python classes corresponding to
        constructed geometry
    key_route_delimiter (str): delimiter for parameter paths
    '''
    def __init__(self, config: dict | str = None, json: str = None) -> None:
        initialise_cubit()
        self.parameter_filler = ParameterFiller()
        self.tracker = Tracker()
        self.design_tree = {}
        self.constructed_geometry = []
        self.key_route_delimiter = '/'
        # accept config data
        if type(config) is str:
            self.config = self.read_config(config)
        elif type(config) is dict:
            self.config = Config(**config)
        else:
            self.config = Config()
        # accept a json file
        if json:
            self.parse_json(json)
        elif self.config.parameter_file:
            self.read_json_from_config()
        # if export_immediately is true, run config steps
        if self.config.export_immediately:
            self.export_from_config()

    def read_config(self, config_file: str):
        '''Read config data from a file

        Parameters
        ----------
        config_file : str
            Name of config file (including path)
        '''
        config_dict = extract_data(config_file)
        self.config = Config(**config_dict)

    def fill_design_tree(self):
        '''Process design_tree manually

        Returns
        -------
        dict
            Processed design tree
        '''
        self.design_tree = self.parameter_filler.process_design_tree(self.design_tree)
        if self.config.print_logs:
            self.parameter_filler.print_log()
        return self.design_tree

    def parse_json(self, filename: str):
        '''Parse a json file and add corresponding design tree
        to design_tree attribute

        Parameters
        ----------
        filename : str
            Name of json file

        Returns
        -------
        dict
            Design tree corresponding to parsed json file
        '''
        self.design_tree = extract_data(filename)
        return self.fill_design_tree()

    def change_delimiter(self, delimiter: str):
        '''Change the delimiter to use in key paths
        for the change_params and get_param methods.
        By default the delimiter is '/'.

        Parameters
        ----------
        delimiter : str
            New delimiter
        '''
        self.key_route_delimiter = delimiter
        print(f"Delimiter changed to: {delimiter}")

    def change_params(self, updated_params: dict):
        r'''Change parameters in stored design tree.
        A parameter is referenced using it's path.
        This path is a string of the keys that are
        used to access that parameter in the json file.

        For example to change the value of the parameter
        'pin spacing' to 135 here:
        {
            "class": "hcpb_blanket",
            "geometry": {
            "pin spacing": 100
            }
        }

        The argument provided here would have to be
        {"geometry/pin spacing": 135}
        with '/' being the default delimiter.

        Parameters
        ----------
        updated_params : dict
            dictionary of the form {path to parameter : updated value}
        '''
        for param_path, updated_value in updated_params.items():
            if type(param_path) is not str:
                raise CubismError(f"path should be given as a string: {str(param_path)}")
            key_route = param_path.split(self.key_route_delimiter)
            self.design_tree = self.__build_param_dict(key_route, self.design_tree, updated_value)

    def get_param(self, param_path: str):
        r'''Get parameter in stored design tree.
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

        Parameters
        ----------
        param_path : str
            Path to parameter

        Returns
        -------
        any
            value of parameter
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

    @log_method("Making geometry")
    def make_geometry(self):
        '''Build geometry corresponding to design tree in cubit

        Returns
        -------
        Class corresponding to the constructed cubit geometry
        '''
        self.constructed_geometry = make_everything(self.design_tree)
        return self.constructed_geometry

    @log_method("Imprint and merge")
    def imprint_and_merge(self):
        '''Imprint and merge geometry in cubit.
        '''
        cmd("imprint volume all")
        cmd("merge volume all")

    @log_method("Tracking components and materials")
    def track_components_and_materials(self):
        '''
        Add components to blocks and component-component interfaces to sidesets
        Add materials and material-material interfaces to groups.
        '''
        for component in self.constructed_geometry:
            self.tracker.give_identifiers(component)
            self.tracker.extract_components(component)
        self.tracker.track_boundaries()
        self.tracker.organise_into_groups()

    def set_mesh_size(self, size: int):
        '''Set approximate mesh size in cubit

        Parameters
        ----------
        size : int
            Mesh size in cubit units
        '''
        cmd(f'volume all size {size}')

    @log_method("Meshing")
    def tetmesh(self):
        '''Mesh geometry in cubit
        '''
        cmd('volume all scheme tet')
        cmd('mesh volume all')

    @log_method("Exporting")
    def export(self, format: str = "cubit", rootname: str = "geometry"):
        '''Export mesh/ geometry in specfied format

        :param format: Name of export format, defaults to "cubit"
        :type format: str, optional
        :param rootname: Name to give output file including path,
        defaults to "geometry"
        :type rootname: str, optional
        '''
        print(f"exporting {rootname}{get_format_extension(format)}")
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

    @log_method("Exporting exodus")
    def export_exodus(self, rootname: str = "geometry", large_exodus=False, HDF5=False):
        '''Export as exodus II file.

        :param rootname: Name to give output file including path,
        defaults to "geometry"
        :type rootname: str, optional
        :param large_exodus: Create a large model that can store individual
        datasets > 2GB, defaults to False
        :type large_exodus: bool, optional
        :param HDF5: Create a model that can store even larger files,
        defaults to False
        :type HDF5: bool, optional
        '''
        if large_exodus:
            cmd("set large exodus on")
        if HDF5:
            cmd("set exodus NetCDF4 on")
        cmd(f'export mesh "{rootname}.e"')

    def reset(self):
        '''Reset cubit and corresponding internal states.'''
        reset_cubit()
        self.tracker.reset()
        self.constructed_geometry = []

    def make_tracked_geometry(self):
        '''Make geometry, imprint + merge it, track boundaries.
        '''
        self.make_geometry()
        self.imprint_and_merge()
        self.track_components_and_materials()

    def file_to_tracked_geometry(self, filename: str):
        '''Parse json file, make geometry,
        imprint + merge it,
        track boundaries.

        Parameters
        ----------
        filename : str
            name of json file
        '''
        self.parse_json(filename)
        self.make_geometry()
        self.imprint_and_merge()
        self.track_components_and_materials()

    def make_merged_geometry(self):
        '''Make geometry, imprint and merge
        '''
        self.make_geometry()
        self.imprint_and_merge()

    def exp_scale(self, scaling: int):
        '''Scale size of the geometry by 10^(scaling) to change what units
        cubit reports in.
        The default parameters assume 1 cubit unit = 1mm.
        So, for example, to get 1 cubit unit = 1cm you would use scaling = -1.

        Parameters
        ----------
        scaling : int
            Exponent to scale by
        '''
        cmd(f"volume all scale {10**scaling} about 0 0 0")

    def read_json_from_config(self):
        '''Read json file specified by config
        '''
        self.parse_json(self.config.parameter_file)

    def export_from_config(self):
        '''make_tracked_geometry,
        then export using the supplied config options.
        '''
        cfg = self.config
        self.make_tracked_geometry()
        self.exp_scale(cfg.scale_exponent)
        if cfg.export_geom:
            for export_type in cfg.export_geom:
                self.export(export_type, cfg.export_name)

        if not cfg.export_mesh:
            return

        self.tetmesh()
        for export_type in cfg.export_mesh:
            if export_type == "exodus":
                self.export_exodus(
                    cfg.export_name,
                    cfg.exodus_options.large_exodus,
                    cfg.exodus_options.hdf5
                    )
