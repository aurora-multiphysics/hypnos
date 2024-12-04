User Guide
==========

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
* ``-g`` : Names of formats to export geometry to (defaults to cubit if neither geometry nor mesh options provided anywhere) ["cubit", "stp"]
* ``-m`` : Names of formats to export mesh to (optional) ["exodus", "DAGMC"]

The names given to flags -f, -o, and -d will be preferred over their equivalent options in the config file (file, root name, destination)

There are several example json files provided in ``examples/``, along with descriptions of their corresponding classes:

* :doc:`HCPB first wall`
* :doc:`HCPB pin`
* :doc:`HCPB blanket`

There is also a sample config file for use with the -c tag: ``examples/sample_config.json``

.. rubric:: GeometryMaker

The GeometryMaker class may be imported from the Hypnos module in order to proceed through the workflow.
Its attributes and some terminology is explained below:

* ``design_tree``: A dictionary of the parameters used to construct a geometry.
  These will usually describe its 'class', geometrical parameters, and material(s) it is made of.
* ``constructed_geometry``: A list of python classes that correspond to the component(s) being constructed.
* ``key_route_delimiter``: Delimiter separating parameter paths in the design tree,
  as explained in :py:meth:`~geometry_maker.GeometryMaker.get_param`

The following methods will take you through the workflow:

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

Aside from these,

* ``fill_design_tree``: Process design_tree manually
* ``change_delimiter``: Change key_route_delimiter
* ``get_param``: Get the value of a parameter stored in the design tree
* ``change_params``: Update parameters stored in the design tree
* ``set_mesh_size``: Set the approximate mesh size
* ``export_exodus``: Exodus export with options for large file sizes
* ``reset_cubit``: Reset cubit and corresponding internal states
* ``exp_scale``: Scale cubit geometries by powers of 10

The full class is documented in :doc:`GeometryMaker`.
Some examples of use are given in the python files in ``examples/``.