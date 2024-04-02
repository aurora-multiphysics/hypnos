from blobmaker.tracking import MaterialsTracker
from blobmaker.generic_classes import cmd
from blobmaker.cubit_functions import reset_cubit
from blobmaker.parsing import extract_data
from blobmaker.default_params import DEFAULTS
from blobmaker.constants import IMPRINT_AND_MERGE, MESH
from blobmaker.geometry_maker import make_everything, GeometryMaker
import pprint, argparse


if __name__ == '__coreformcubit__':
    reset_cubit()
    make_everything(extract_data("sample_blanket.json"))
elif __name__ == "__main__":
    # accept command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--file", type=str, help="Name of json file describing geometry", default="examples/sample_breeder_unit.json")
    parser.add_argument("-i", "--info", help="Print cubit IDs of volumes in materials and surfaces in boundaries", action='store_true')
    parser.add_argument("-c", "--classname", type=str, help="Get available classes", default='none')
    parser.add_argument("-o", "--outputfilename", type=str, help="Name of output file", default='out_geometry.cub5')
    parser.add_argument("-d", "--destination", type=str, help="Path of directory to generate output file in", default='.')
    # parser.add_argument("-p", "--cubitpath", type=str, help="Add cubit path to pythonpath")
    args = parser.parse_args()

    if args.classname != 'none':
        if args.classname not in [default_class["class"] for default_class in DEFAULTS]:
            print("The available classes are:")
            for default_class in DEFAULTS:
                print(default_class["class"])
        for default_class in DEFAULTS:
            if default_class["class"] == args.classname:
                print(f"The parameters and defaults for class {args.classname} are: ")
                pp = pprint.PrettyPrinter(indent=4)
                pp.pprint(default_class)
        exit(0)

    maker = GeometryMaker()
    maker.print_parameter_logs = True
    maker.parse_json(args.file)
    maker.track_components = False
    universe = maker.make_geometry()

    if IMPRINT_AND_MERGE:
        maker.imprint_and_merge()
    maker.export_geometry(args.outputfilename, args.destination)

    # print this information if cli flag used
    if args.info == 'true':
        MaterialsTracker().print_info()
    if MESH:
        maker.tetmesh()
        cmd('export mesh "meshed.e"')