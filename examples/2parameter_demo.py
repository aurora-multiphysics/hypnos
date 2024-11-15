from hypnos import GeometryMaker

multiplier_lengths = [385, 355, 325, 295, 265]


def build():
    # instantiating this class initialises cubit
    maker = GeometryMaker()
    maker.parse_json('sample_blanket.json')

    for length in multiplier_lengths:
        maker.change_params({"components/pin/geometry/multiplier length": length})
        maker.make_geometry()
        maker.imprint_and_merge()
        # change destination path!
        maker.export("cubit", f"multiplier_length_{length}")

        # this will take a while
        # maker.tetmesh()
        # maker.export_exodus(f"multiplier_length_{length}")

        maker.reset()


if __name__ == "__main__":
    build()
