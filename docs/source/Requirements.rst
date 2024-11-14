Requirements
============

To use Hypnos, the following are required:

* `Coreform cubit <https://coreform.com/products/downloads/>`_, along with a working license
* `Python 3 <https://www.python.org/downloads/>`_
* `Numpy <https://numpy.org/install/>`_

This code should be run with Coreform Cubit 2024.3+.
The DAGMC workflow will not work in previous versions.
The cubit python library must be accessible by python. On linux::

    PATH=$PATH:<path to cubit.py>

Install Hypnos using pip::

    pip install .

If using as a developer, install as an editable::

    pip install --editable .