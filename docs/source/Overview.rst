Overview
========

Hypnos' goal is to construct a geometry from the parameters you give it. The workflow is as follows:

* Import parameters from a json file
* Build geometry in cubit, imprint and merge
* Add blocks, sidesets, and groups
* Mesh and/or Export

This can be achieved either through running main.py, or in your own python script using the GeometryMaker class.
These are explained in :doc:`User Guide`.

.. rubric:: types of geometries

The following terminology will be used when describing geometries:

* simple component: A single geometrical entity or collection of entities made of the same material.
  For example, the cladding of a pin is described by a 'cladding' simple component.
  These need not be 'simple' geometrically.
* assembly: A collection of other components
* component: A simple component or an assembly

.. caution:: This is probably a silly way of naming things.

.. rubric:: json files

Hypnos uses json files to describe parameters of a component.
Components are represented by dictionaries of parameters ``{"key": value }``.

These will usually contain the following parameters:

* ``"class"``: This must be declared to select a specific component
* ``"material"``: The material this simple component is made of or a dictionary of materials used in this assembly
* ``"geometry"``: The geometrical parameters describing this component.

Json file names containing a json object describing a component (ex. hcpb_pin.json)
can be used where such a json object is expected by using a string with the file name
(ex. ``{"class": "blanket" ... "components" : ["hpcb_pin.json"]}``)

Examples are given in sample json files in ``examples/``.

