# Hypnos

Hypnos is a parametric geometry engine to create meshes for structures involved in the analysis of breeder blankets.
Code blocks and paths are relative to the root directory.

## Dependencies
+ [Coreform cubit](https://coreform.com/products/downloads/) (2024.3+), along with a working license
+ [Python 3](https://www.python.org/downloads/) (3.10+)
+ The numpy python library: `pip install numpy`

This code should be run with Coreform Cubit 2024.3+. The DAGMC workflow will not work in previous versions.
The cubit python library must be accessible by python. On linux,
`export PYTHONPATH=$PYTHONPATH:/path-to-cubit/bin`

## Installation
Install Hypnos using pip (in hypnos/, the root directory)
`pip install .`
If using as a developer, install as an editable
`pip install --editable .`

## Docs
For the full instructions you will need to build the documentation via sphinx.
```
pip install sphinx
sphinx-build -M html docs/source docs/build
```
You will then be able to access the documentation by opening `docs/build/html/index.html` in your preferred browser.
Please ensure you don't have an older version of sphinx-build in your path. You can do this by running:
```
which sphinx-build
```

## Usage
Hypnos uses json files to describe parameters of a component.
Components are represented by json objects "{ }", using the "class" key to select a specific component type.
Json files containing a json object describing a component (ex. hcpb_pin.json) can be used where such a json object is expected by using a string with the file name (ex. {"class": "blanket" ... "components" : \["hpcb_pin.json"]})

Examples are given in sample json files in `examples/`, and explained further in the sphinx documentation.

To use hypnos, run main.py, passing the name of the json file to a `-f` flag:
```python main.py -f examples/sample_pin.json```
By default, this will export the described geometry as a .cub5 file (with no mesh).

To configure this process, pass the name of a config json file to a `-c` flag:
```python main.py -f examples/sample_config.json```
The structure of a config file is described in the section below.

To print the default template of a class, pass its name to a `-i` flag.
If no argument is given, the available templates will be printed.
```python main.py -i "first_wall"```


## Config
A config file lets you configure the exporting process of a geometry.
It is a json file with a dictionary with the format {"option": option_value}
The options a config file will accept are:

+ `"parameter_file"`: Name of the parameter json file.
+ `"scale_exponent"`: Power of 10 to scale geometry by before exporting (int, default: 0 i.e. no scaling)
+ `"export_name"`: Name to use when exporting a file, including the path (defaults to './geometry')
+ `"export_geom"`: List of format names to export geometry to {"cubit", "stp"}
+ `"export_mesh"` List of format names to export meshed geometry to {"exodus", "DAGMC", "cubit"}
+ `"exodus_options"`: Dictionary of options to use when exporting to an exodus file
    + `"large_exodus"`: Create a large model that can store individual datasets > 2GB (bool, default: false)
    + `"hdf5"`: Create a model that can store even larger files (bool, default: false)


## References
Users are suggested to cite the below work(s) if using parts of this code based off of them.

The HCPB geometry parametrised in this code was based off of a design for the DEMO reactor from the following paper:
Zhou, G.; Hernández, F.A.; Pereslavtsev, P.; Kiss, B.; Retheesh, A.; Maqueda, L.; Park, J.H. The European DEMO Helium Cooled Pebble Bed Breeding Blanket: Design Status at the Conclusion of the Pre-Concept Design Phase. Energies 2023, 16, 5377. https://doi.org/10.3390/en16145377