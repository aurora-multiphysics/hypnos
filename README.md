# Blobmaker

Blobmaker is a parametric geometry engine to create meshes for structures involved in the analysis of breeder blankets.

## Requirements
(Coreform cubit)[https://coreform.com/products/downloads/], along with a working license
(Python 3)[https://www.python.org/downloads/]

The oldest version of coreform cubit used with this code is Coreform Cubit 2021.8

## Usage
Blobmaker uses json files to describe parameters of a component.
Components are represented by json objects "{ }", using the "class" key to select a specific component type.
Json files containing a json object describing a component (ex. hcpb_breeder_unit.json) can be used where such a json object is expected by using a string with the file name (ex. {"class": "blanket" ... "components" : \["hpcb_breeder_unit.json"]})

Examples are given in sample json files

To use blobmaker, run the main.py file in python, passing the name of the json file to a --file (-f) flag:
```python main.py -f "sample_blanket.json"```

The following flags are also available:
--cubitpath (-c): To specify the path to cubit's python library if it isn't already in your pythonpath
--info (-i): Print cubit IDs of volumes in materials and surfaces in boundaries