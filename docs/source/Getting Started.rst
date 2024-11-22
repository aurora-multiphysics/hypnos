Getting Started
===============


.. rubric:: Dependencies

To use Hypnos, the following are required:

* `Coreform cubit <https://coreform.com/products/downloads/>`_ (2024.3+), along with a working license
* `Python 3 <https://www.python.org/downloads/>`_ (3.10+)
* `Numpy <https://numpy.org/install/>`_

This code should be run with Coreform Cubit 2024.3+.
The DAGMC workflow will not work in previous versions.
The cubit python library must be accessible by python. On linux::

    export PYTHONPATH=$PYTHONPATH:/path-to-cubit/bin

.. rubric:: Package Installation

Install Hypnos using pip (in hypnos/, the root directory)::

    pip install .

If using as a developer, install as an editable::

    pip install --editable .

.. rubric:: Tests

To run tests, use `Pytest <https://docs.pytest.org/en/8.2.x/getting-started.html>`_::

    pip install pytest
    pytest

After setting up Hypnos, consult the :doc:`User Guide`