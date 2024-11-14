Usage
=====

Hypnos can be used either through running the main.py script,
or by importing the GeometryMaker class from the python library.

.. rubric:: main.py

To use hypnos, run main.py, passing the name of the json file to a ``-f`` flag (default: examples/sample_pin.json)::
    
    python main.py -f examples/sample_pin.json

The following flags are also available:

* ``-h``: Print available flags for use
* ``-c``: Name of config file to use (optional)
* ``-o``: Name of geometry file to export including path (default: geometry)
* ``-d``: Destination to create output file(s) (default: ./)
* ``-i``: Name of class to print default template for. Leaving empty prints the available templates.
* ``-g`` : Names of formats to export geometry to (defaults to cubit if neither geometry nor mesh options provided anywhere)
* ``-m`` : Names of formats to export mesh to (optional)

The names given to flags -f, -o, and -d will be preferred over their equivalent options in the config file (file, root name, destination)

.. rubric:: GeometryMaker

The GeometryMaker class may be imported from the Hypnos module in order to proceed through the workflow.

The following methods are available:

* ``parse_json``: Read in parameters from a json file
* ``make_geometry``: Construct geometry in cubit
* ``imprint_and_merge``: Run imprint and merge in cubit
* ``track_components_and_materials``: Add components to blocks, and component-component interfaces to sidesets
* ``tetmesh``: Run cubit's automatic tetmeshing command
* ``export``: Export geometry (and mesh if any) to a file of specified format

There are also some convenience functions to do multiple steps at once:

* ``file_to_merged_geometry``: parse, make, imprint and merge
* ``file_to_tracked_geometry``: parse, make, imprint and merge, track
* ``make_tracked_geometry``: make, imprint and merge, track

These are described in more detail in :doc:`User API`