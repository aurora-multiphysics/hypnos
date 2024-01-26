import json
from default_params import DEFAULTS
from generic_classes import CubismError

def extract_data(filename):
    with open(filename) as jsonFile:
        data = jsonFile.read()
        objects = json.loads(data)
    return objects

def delve(component_list):
    for i in range(len(component_list)):
        if type(component_list[i]) == str:
            component_list[i] = extract_data(component_list[i])
    return component_list

class ParameterFiller():
    log = []
    def __init__(self) -> None:
        pass

    def add_log(self, message: str):
        self.log.append(message)
    
    def print_log(self):
        for message in self.log:
            print(message)

    def __get_default_object(self, json_object) -> dict:
        try:
            for default_class in DEFAULTS:
                if default_class["class"] == json_object["class"]:
                    return default_class
        except KeyError:
            raise CubismError("All json objects need to have a class")
        return False
    
    def __fill_params(self, dict_to_fill: dict, default_dict: dict):
        for key, value in default_dict:
            if key in dict_to_fill.keys():
                self.add_log(f"Parameter {key} set to: {dict_to_fill[key]} (default: {value})")
            else:
                dict_to_fill[key] = value
                self.add_log(f"Parameter {key} set to default: {value}")
        return dict_to_fill

    def process_defaults(self, json_object: dict):
        default_object = self.__get_default_object(json_object)
        self.add_log(f"Logging object of class {json_object['class']}")
        if default_object:
            for key, value in default_object.items():
                if key not in json_object.keys():
                    json_object[key] = value
                    self.add_log(f"key {key} not specified. Added default value.")
                else:
                    if type(value) == dict:
                        json_object[key] = self.__fill_params(json_object[key], default_object[key])
                    elif type(value) == list:
                        for component in delve(value):
                            json_object[key] = self.process_defaults(component)
        else:
            self.add_log(f"Default object not found for: {json_object['class']}")
        return json_object
