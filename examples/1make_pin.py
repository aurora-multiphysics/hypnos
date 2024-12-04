'''
1make_pin.py
author(s): Sid Mungale

An example to demonstrate basic usage of the GeometryMaker class
'''
from hypnos import GeometryMaker


def make_pin():
    maker = GeometryMaker()

    # parses json file to a python dict in design_tree attribute
    maker.file_to_tracked_geometry("sample_pin.json")

    # replace the . with destination path
    # this will export a .cub5 file containing the pin
    maker.export("cubit", "./pin")

    # global mesh setting
    maker.set_mesh_size(4)
    maker.tetmesh()

    # again, replace the . with destination path
    # this will export a .e file with the pin mesh
    maker.export("exodus", "./pin")


if __name__ == "__main__":
    make_pin()
