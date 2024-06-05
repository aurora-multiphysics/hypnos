from blobmaker import GeometryMaker


def make_pin():
    maker = GeometryMaker()
    maker.track_components = True

    # parses json file to a python dict in design_tree attribute
    maker.parse_json("sample_pin.json")
    
    # constructs geometry from design_tree, class structure in constructed_geometry
    maker.make_geometry()

    # this also adds materials to blocks and material-material interfaces to sidesets
    maker.imprint_and_merge()

    # replace the . with destination path
    maker.export("cubit", "pin")

    # global mesh setting
    maker.set_mesh_size(4)
    # maker.tetmesh()

    # again, replace the . with destination path
    # maker.export_mesh("pin.e", ".")


if __name__ == "__main__":
    make_pin()
