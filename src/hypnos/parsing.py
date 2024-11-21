'''
parsing.py
author(s): Sid Mungale

Classes and functions to process json files describing the parameters

(c) Copyright UKAEA 2024
'''

import json
import copy
from hypnos.default_params import DEFAULTS
from hypnos.generic_classes import CubismError


def extract_data(filename) -> dict:
    '''Load dictionary from a json file

    Parameters
    ----------
    filename : str
        path to json file

    Returns
    -------
    dict
        data inside json file
    '''
    with open(filename) as jsonFile:
        data = jsonFile.read()
        objects = json.loads(data)
    return objects


def extract_if_string(possible_filename):
    '''If the input is a string, try to use extract_data

    Parameters
    ----------
    possible_filename : any
        input to check

    Returns
    -------
    any
        if the input was a filename, this will be a dict
    '''
    if type(possible_filename) is str:
        return extract_data(possible_filename)
    return possible_filename


def delve(component_obj: list | dict):
    '''Ensure any strings in lists or dictionary values are processed

    Parameters
    ----------
    component_obj : list | dict
        object to check for strings

    Returns
    -------
    list | dict
        appropriately processed json object
    '''
    if type(component_obj) is dict:
        return {comp_key: extract_if_string(comp_value) for comp_key, comp_value in component_obj.items()}
    elif type(component_obj) is list:
        return [extract_if_string(component) for component in component_obj]
    elif type(component_obj) is str:
        return extract_data(component_obj)
    raise TypeError(f"Unrecognised delvee: {component_obj}")


class ParameterFiller():
    '''Process json files. Fill in missed input parameters with defaults.

    Attributes
    ----------
    log: list
        stores info about the json processing step
    design_tree: dict
        stores the design tree for the geometry we want to construct
    config: dict
        stores the default configuration for our design tree (if any)
    '''
    def __init__(self):
        self.log = []
        self.design_tree = {}
        self.config = {}

    def add_log(self, message: str):
        '''Add message to log'''
        self.log.append(message)

    def process_design_tree(self, design_tree: dict) -> dict:
        '''Fill in missing parameters of design tree with default config values

        Parameters
        ----------
        design_tree : dict
            Parametrical description of geometry

        Returns
        -------
        dict
            Filled design tree
        '''
        self.design_tree = design_tree
        self.__prereq_check()
        self.config = self.__get_config()
        if self.config:
            self.design_tree = self.__fill_params(self.design_tree, self.config)
        return self.design_tree

    def print_log(self):
        '''Print messages in log'''
        for message in self.log:
            print(message)

    def __prereq_check(self):
        '''Ensure design tree has a class'''
        try:
            if type(self.design_tree["class"]) is not str:
                raise CubismError("json object class must be a string")
        except KeyError:
            raise CubismError("All json objects need to have a class")

    def __get_config(self):
        '''Fetch default config for given class if it exists'''
        for default_class in DEFAULTS:
            if default_class["class"].lower() == self.design_tree["class"].lower():
                return copy.deepcopy(default_class)
        self.add_log(f"Default configuration not found for: {self.design_tree['class']}")
        return False

    def __fill_params(self, design_tree: dict, config: dict):
        '''Fill any missing parameters of given dict by
        comparing it's keys to the default config's keys

        Parameters
        ----------
        design_tree : dict
            Dictionary to compare to default
        config : dict
            Default key-value pairs for the given class

        Returns
        -------
        dict
            Filled-out dict 
        '''
        design_tree = self.__setup_tree(design_tree)
        # we look at every key-value pair in the default dictionary
        for key, default_value in config.items():
            # stuff we do if the corresponding key also exists in our dictionary
            if key in design_tree.keys():
                if type(default_value) is dict:
                    # if there is another layer of nesting, recurse
                    # set our value to the filled dictionary that gets returned
                    design_tree[key] = self.__fill_params(design_tree[key], config[key])
                else:
                    # if the user has set a value we are happy
                    self.add_log(f"{key} set to: {design_tree[key]} (default: {default_value})")
            # otherwise set our key to the default value
            else:
                design_tree[key] = default_value
                self.add_log(f"key {key} not specified. Added default.")
        self.__cleanup_logs(design_tree, config)
        return design_tree

    def __setup_tree(self, design_tree: dict):
        '''Start logging a class and process any references to filenames'''
        if "class" in design_tree.keys():
            self.add_log(f"---------- Logging class: {design_tree['class']} ----------")
        if "components" in design_tree.keys():
            design_tree["components"] = delve(design_tree["components"])
        return design_tree

    def __cleanup_logs(self, design_tree: dict, config: dict):
        '''Log if design_tree has any keys missing from the config,
        Finish logging class'''
        for key in list(set(design_tree.keys()) - set(config.keys())):
            self.add_log(f"key {key} not in default config")
        if "class" in design_tree.keys():
            self.add_log(f"---------- Finished logging class: {design_tree['class']} ----------")


def get_format_extension(format_type: str) -> str:
    '''Get the extension given a file format

    Parameters
    ----------
    format_type : str
        file format

    Returns
    -------
    str
        file extension
    '''
    format_type = format_type.lower()
    if format_type == "cubit" or "cub5" in format_type:
        return ".cub5"
    elif format_type == "exodus" or ".e" in format_type:
        return ".e"
    elif format_type == "dagmc" or "h5m" in format_type:
        return ".h5m"
    elif format_type == "step" or "stp" in format_type:
        return ".stp"
    else:
        raise CubismError(f"Unrecognised format: {format_type}")