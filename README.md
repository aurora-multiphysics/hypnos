# Hypnos

Hypnos is a parametric geometry engine to create meshes for structures involved in the analysis of breeder blankets.

## Requirements
+ [Coreform cubit](https://coreform.com/products/downloads/), along with a working license
+ [Python 3](https://www.python.org/downloads/)
+ The numpy python library: `pip install numpy`

This code should be run with Coreform Cubit 2024.3. The DAGMC workflow will not work in previous versions.
The cubit python library must be on your python path

## Usage
Hypnos uses json files to describe parameters of a component.
Components are represented by json objects "{ }", using the "class" key to select a specific component type.
Json files containing a json object describing a component (ex. hcpb_pin.json) can be used where such a json object is expected by using a string with the file name (ex. {"class": "blanket" ... "components" : \["hpcb_pin.json"]})

Examples are given in sample json files

To use hypnos, run main.py, passing the name of the json file to a -f flag (default: examples/sample_pin.json):
```python main.py -f examples/sample_pin.json```

The following flags are also available:
+ -h: Print available flags for use
+ -c: Name of config file to use (optional)
+ -o: Name of geometry file to export including path (default: geometry)
+ -d: Destination to create output file(s) (default: ./)
+ -i: Name of class to print default template for. Leaving empty prints the available templates.
+ -g : Names of formats to export geometry to (defaults to cubit if neither geometry nor mesh options provided anywhere)
+ -m : Names of formats to export mesh to (optional)

The names given to flags -f, -o, and -d will be preferred over their equivalent options in the config file (file, root name, destination)

## References
Users are suggested to cite the below work(s) if using parts of this code based off of them.

The HCPB geometry parametrised in this code was based off of a design for the DEMO reactor from the following paper:
Zhou, G.; Hernández, F.A.; Pereslavtsev, P.; Kiss, B.; Retheesh, A.; Maqueda, L.; Park, J.H. The European DEMO Helium Cooled Pebble Bed Breeding Blanket: Design Status at the Conclusion of the Pre-Concept Design Phase. Energies 2023, 16, 5377. https://doi.org/10.3390/en16145377