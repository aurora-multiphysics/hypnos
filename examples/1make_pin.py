from blobmaker import GeometryMaker


def make_pin():
    maker = GeometryMaker()
    maker.track_components = True

    # parses json file to a python dict in design_tree attribute
    maker.file_to_tracked_geometry("sample_pin.json")

    # replace the . with destination path
    maker.export("cubit", "pin")

    # global mesh setting
    maker.set_mesh_size(4)
    # maker.tetmesh()

    # again, replace the . with destination path
    # maker.export_mesh("pin.e", ".")


if __name__ == "__main__":
    make_pin()
