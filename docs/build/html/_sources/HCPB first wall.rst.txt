HCPB first wall
===============

The HCPB-style first wall was based off the design from the following paper:

Zhou, G.; Hernández, F.A.; Pereslavtsev, P.; Kiss, B.; Retheesh, A.; Maqueda, L.; Park, J.H.
The European DEMO Helium Cooled Pebble Bed Breeding Blanket:
Design Status at the Conclusion of the Pre-Concept Design Phase.
Energies 2023, 16, 5377. https://doi.org/10.3390/en16145377

This component has the ``class`` key ``first_wall``. An example is given in ``examples/sample_first_wall.json``.
This component requires a `material` key with the desired material and geometrical parameters
as shown in :ref:`first_wall_params`.

.. _first_wall_params:
.. figure:: images/first_wall_top_params.png
    :alt: first wall parameters

    First wall parameters