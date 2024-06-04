from blobmaker.cubit_functions import reset_cubit
from blobmaker.parsing import extract_data
from blobmaker.default_params import DEFAULTS
from blobmaker.geometry_maker import make_everything, GeometryMaker
import pprint, argparse


if __name__ == '__coreformcubit__':
    reset_cubit()
    make_everything(extract_data("sample_blanket.json"))
elif __name__ == "__main__":
    # accept command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--file", type=str, help="Name of json file describing geometry", default="examples/sample_pin.json")
    parser.add_argument("-i", "--info", type=str, help="Get info on available classes", default='none')
    parser.add_argument("-o", "--output", type=str, help="Root name of output file", default='default')
    parser.add_argument("-d", "--destination", type=str, help="Path of directory to generate output file in", default='default')
    parser.add_argument("-c", "--config", type=str, help="Name of config json file", default="examples/sample_config.json")
    args = parser.parse_args()

    if args.info != 'none':
        if args.info not in [default_class["class"] for default_class in DEFAULTS]:
            print("The available classes are:")
            for default_class in DEFAULTS:
                print(default_class["class"])
        for default_class in DEFAULTS:
            if default_class["class"] == args.info:
                print(f"The parameters and defaults for class {args.info} are: ")
                pp = pprint.PrettyPrinter(indent=4)
                pp.pprint(default_class)
        exit(0)
    
    # get config file info
    config_data = extract_data(args.config)
    if args.output != 'default':
        root_name = args.output
    elif "root name" in config_data.keys():
        root_name = config_data["root name"]
    else:
        root_name = "geometry"
    
    if args.destination != 'default':
        destination = args.destination
    elif "destination" in config_data.keys():
        destination = config_data["destination"]
    else:
        destination = './'
    if not destination.endswith("/"):
        destination = destination + "/"
    
    export_geometries = config_data["export geometry"] if "export geometry" in config_data.keys() else ["cubit"]
    if type(export_geometries) is not list:
        export_geometries = [export_geometries]
    export_mesh = config_data["export mesh"] if "export mesh" in config_data.keys() else []
    if type(export_mesh) is not list:
        export_mesh = [export_mesh]
    # get exodus options if specified in the mesh formats
    if "exodus" in export_mesh:
        if "exodus options" in config_data.keys():
            exodus_options = config_data["exodus options"]
            large_exodus = "large exodus" in exodus_options.keys() and exodus_options["large exodus"] == "true"
            hdf5 = "HDF5" in exodus_options.keys() and exodus_options["HDF5"] == "true"
        else:
            large_exodus = False
            hdf5 = False

    maker = GeometryMaker()
    maker.print_parameter_logs = True
    maker.track_components = False
    maker.file_to_merged_geometry(args.file)

    export_name = destination + root_name
    for export_type in export_geometries:
        maker.export(export_type, export_name)
    # only mesh if export mesh format(s) given
    if len(export_mesh) > 0:
        maker.tetmesh()
        for export_type in export_mesh:
            if export_type == "exodus":
                maker.export_exodus(export_name, large_exodus, hdf5)
            else:
                maker.export(export_type, export_name)

