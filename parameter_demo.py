from main import GeometryMaker

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
        maker.export_geometry(f"multiplier_length_{length}.cub5", "./parameter_demo_files/geometry_files")
        # this will take a while
        #maker.tetmesh()
        #maker.export_mesh(f"multiplier_length_{length}.e", "./parameter_demo_files/mesh_files")
        maker.reset_cubit()

if __name__ == "__main__":
    build()