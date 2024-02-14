import json
from default_params import DEFAULTS
from generic_classes import CubismError

def extract_data(filename):
    with open(filename) as jsonFile:
        data = jsonFile.read()
        objects = json.loads(data)
    return objects

def delve(component_list: list):
    delved_list = []
    for component in component_list:
        if type(component) == str:
            delved_list.append(extract_data(component))
        else:
            delved_list.append(component)
    return delved_list

class ParameterFiller():
    log = []
    def __init__(self):
        pass

    def add_log(self, message: str):
        self.log.append(message)
    
    def print_log(self):
        for message in self.log:
            print(message)

    def __get_default_object(self, json_object) -> dict:
        try:
            for default_class in DEFAULTS:
                if default_class["class"].lower() == json_object["class"].lower():
                    return default_class
        except KeyError:
            raise CubismError("All json objects need to have a class")
        return False
    
    def __fill_params(self, dict_to_fill: dict, default_dict: dict):
        for key, default_value in default_dict.items():
            if key in dict_to_fill.keys():
                self.add_log(f"{key} set to: {dict_to_fill[key]} (default: {default_value})")
            else:
                dict_to_fill[default_value] = default_value
                self.add_log(f"{key} set to default: {default_value}")
        for key in dict_to_fill.keys():
            if key not in default_dict:
                print(f"Key not recognised: {key}")
        return dict_to_fill

    def process_defaults(self, json_object: dict):
        default_object = self.__get_default_object(json_object)
        self.add_log(f"Logging class: {json_object['class']}")
        if default_object:
            for key, default_value in default_object.items():
                if key in json_object.keys():
                    if type(default_value) == dict:
                        json_object[key] = self.__fill_params(json_object[key], default_value)
                    elif type(default_value) == list:
                        delved_list = delve(json_object[key])
                        for i in range(len(default_value)):
                            json_object[key][i] = self.process_defaults(delved_list[i])
                else:
                    json_object[key] = default_value
                    self.add_log(f"key {key} not specified. Added default configuration.")
        else:
            self.add_log(f"Default configuration not found for: {json_object['class']}")
        self.add_log(f"Finished logging class: {json_object['class']}")
        return json_object
