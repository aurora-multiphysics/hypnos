from blobmaker import GeometryMaker

multiplier_lengths = [385, 355, 325, 295, 265]

def build():
    # instantiating this class initialises cubit
    maker = GeometryMaker()
    maker.parse_json('sample_blanket.json')

    for length in multiplier_lengths:
        maker.change_params({"components/breeder_unit/geometry/multiplier length": length})
        maker.make_geometry()
        maker.imprint_and_merge()
        # change destination path!
        maker.export_geometry(f"multiplier_length_{length}.cub5", ".")
        # this will take a while
        #maker.tetmesh()
        #maker.export_mesh(f"multiplier_length_{length}.e", "./parameter_demo_files/mesh_files")
        maker.reset_cubit()

def make_breeder_unit():
    maker = GeometryMaker()
    maker.parse_json("sample_breeder_unit.json")
    maker.make_geometry()
    maker.imprint_and_merge()
    maker.export_geometry(f"breeder_unit.cub5", ".")
    maker.set_mesh_size(4)
    maker.tetmesh()
    maker.export_mesh("breeder_unit.e", ".")

if __name__ == "__main__":
    build()