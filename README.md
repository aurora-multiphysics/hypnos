# Blobmaker

Blobmaker is a parametric geometry engine to create meshes for structures involved in the analysis of breeder blankets.

## Requirements
+ [Coreform cubit](https://coreform.com/products/downloads/), along with a working license
+ [Python 3](https://www.python.org/downloads/)
+ The numpy python library: `pip install numpy`

This code should be run with Coreform Cubit 2023.8
The cubit python library must be on your python path

## Usage
Blobmaker uses json files to describe parameters of a component.
Components are represented by json objects "{ }", using the "class" key to select a specific component type.
Json files containing a json object describing a component (ex. hcpb_pin.json) can be used where such a json object is expected by using a string with the file name (ex. {"class": "blanket" ... "components" : \["hpcb_pin.json"]})

Examples are given in sample json files

To use blobmaker, run main.py, passing the name of the json file to a -f flag (default: examples/sample_pin.json):
```python main.py -f examples/sample_pin.json```

The following flags are also available:
+ -h: Print available flags for use
+ -c: Name of config file to use (optional)
+ -o: Name of geometry file to export including path (default: examples/sample_pin)
+ -d: Destination to create output file(s) (default: ./)
+ -i: Name of class to print default template for. Leaving empty prints the available templates.

The names given to flags -f, -o, and -d will be preferred over their equivalent options in the config file (file, root name, destination)