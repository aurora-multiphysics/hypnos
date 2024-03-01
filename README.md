# Blobmaker

Blobmaker is a parametric geometry engine to create meshes for structures involved in the analysis of breeder blankets.

## Requirements
(Coreform cubit)[https://coreform.com/products/downloads/], along with a working license
(Python 3)[https://www.python.org/downloads/]
The numpy python library: `pip install numpy`

The oldest version of coreform cubit used with this code is Coreform Cubit 2021.8
The cubit python library must be on your python path

## Usage
Blobmaker uses json files to describe parameters of a component.
Components are represented by json objects "{ }", using the "class" key to select a specific component type.
Json files containing a json object describing a component (ex. hcpb_breeder_unit.json) can be used where such a json object is expected by using a string with the file name (ex. {"class": "blanket" ... "components" : \["hpcb_breeder_unit.json"]})

Examples are given in sample json files

To use blobmaker, run main.py, passing the name of the json file to a -f flag:
```python main.py -f sample_blanket.json```

The following flags are also available:
-h: Print available flags for use
-c: Name of class to print default template for
-o: Name of geometry file to export
-d: Destination to create output file(s)
-i: Print cubit IDs of volumes in materials and surfaces in boundaries