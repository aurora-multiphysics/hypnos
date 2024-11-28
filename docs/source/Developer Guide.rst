Developer Guide
===============

Here are the steps to make a custom simple component for use with Hypnos:

.. rubric:: json file

* Decide on a class name and the geometrical parameters you will need to construct this component.
* create a json file with a dictionary of this information, and a material.

.. code-block:: json
    :caption: custom_component.json

    {
        "class": "CustomComponent",
        "material": "material_name",
        "geometry": {
            "length": 5,
            "height": 7.931
        }
    }

.. rubric:: python

* Import ``SimpleComponent`` from :doc:`Components`
* Create your custom class, subclassing SimpleComponent.
  You will have access to the geometrical parameters via ``self.geometry``, a dictionary.
* Define ``__init__``, passing a name you want to be used for this component in cubit groups, blocks, and sidesets.
* Implement a ``check_sanity`` method to ensure the parameters you receive are physical.
* Implement a ``make_geometry`` method to construct your component in cubit.
  This should return a list of created CubitInstances.

.. code-block:: python
    :caption: custom_component.py

    from hypnos.components import SimpleComponent
    from hypnos.geometry import create_brick

    class CustomComponent(SimpleComponent):
        def __init__(classname, params):
            super.__init__("custom", params)

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

You can now use this custom class with GeometryMaker!

.. code-block:: python
    :caption: custom_component.py (continued)

    from hypnos.geometry_maker import GeometryMaker

    maker = GeometryMaker([CustomComponent])
    maker.file_to_tracked_geometry("custom_component.json")
    maker.tetmesh()
    maker.export("cub5", "custom")

.. rubric:: creating geometries in cubit

Hypnos knows about the existence of a geometrical entity in cubit via instances of the CubitInstance class.
For example after creating a cuboid in a fresh session of cubit, Hypnos can track the created volume with
``CubitInstance(1, "volume")``.

To create geometries in cubit, you may use the cubit python API, or issue commands to the cubit command line
using :func:`~generic_classes.cmd`. However, it is preferable to use the functions in :doc:`Geometry`,
or to create similar functions.

For example :func:`~geometry.make_cylinder_along` will create a cylinder in cubit and return
a CubitInstance object referring to it.

.. rubric:: contributing

If you would like to contribute to this code, please follow the following process:

* Check whether an issue describing your changes already exists on github, else make one.
  If one already does, it may be that someone is already working on these changes.
* Follow the steps in `Contributing to a project <https://docs.github.com/en/get-started/exploring-projects-on-github/contributing-to-a-project>`_.
  Before making a pull request as described above, it is wise to ensure that you are up to date with the upstream source and also that all tests pass (:ref:`tests`)
* If you are not up to date, you will want to rebase your changes on top. The following code will attempt to rebase on top of the dev branch.

.. code-block:: bash

    git remote add upstream https://github.com/sid-mungale/blobmaker.git
    git fetch upstream
    git switch dev
    git merge upstream/dev
    git switch <branch_with_your_changes>
    git rebase dev


.. toctree::
    Assemblies
    Components
    Cubit Functions
    Generic Classes
    Geometry
    Tracking
    GeometryMaker