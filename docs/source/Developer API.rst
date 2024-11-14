Developer API
=============

Here are the steps to make a custom simple component for use with Hypnos:

.. rubric:: json file

* Decide on a class name and the geometrical parameters you will need to construct this component.
* create a json file with a dictionary of this information, and a material.

.. code-block:: json
    :caption: custom_component.json

    {
        "class": "custom_component",
        "material": "material_name",
        "geometry": {
            "length": 5,
            "height": 7.931
        }
    }

* Import ``SimpleComponent`` from :doc:`Components`
* Create your custom class, subclassing SimpleComponent.
  You will have access to the geometrical parameters via ``self.geometry``, a dictionary.
* Implement a ``check_sanity`` method to ensure the parameters you receive are physical.
* Implement a ``make_geometry`` method to construct your component in cubit.
  This should return a list of created CubitInstances.

.. code-block:: python
    :caption: custom_component.py

    from hypnos.components import SimpleComponent
    from hypnos.geometry import create_brick

    CustomComponent(SimpleComponent):
        def check_sanity(self):
            length = self.geometry["length"]
            height = self.geometry["height"]
            if length < 0 or height < 0:
                raise ValueError("parameters must be positive")

        def make_geometry(self):
            length = self.geometry["length"]
            height = self.geometry["height"]
            brick = create_brick(x=length, y=length, z=height)
            return brick

.. rubric:: creating geometries in cubit

Hypnos knows about the existence of a geometrical entity in cubit via instances of the CubitInstance class.
For example after creating a cuboid in a fresh session of cubit, Hypnos can track the created volume with
``CubitInstance(1, "volume")``.

To create geometries in cubit, you may use the cubit python API, or issue commands to the cubit command line
using :func:`~generic_classes.cmd`. However, it is preferable to the functions in :doc:`Geometry`,
or to create similar functions.

For example :func:`~geometry.make_cylinder_along` will create a cylinder in cubit and return
a CubitInstance object referring to it.

.. toctree::
    Assemblies
    Components
    Cubit Functions
    Generic Classes
    Geometry
    Tracking
    GeometryMaker