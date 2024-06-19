from blobmaker.generic_classes import CubismError
from blobmaker.cubit_functions import reset_cubit
from blobmaker.parsing import extract_data, get_format_extension
from blobmaker.default_params import DEFAULTS
from blobmaker.geometry_maker import make_everything, GeometryMaker
import pprint, argparse
from os.path import isfile
from pathlib import Path


if __name__ == '__coreformcubit__':
    reset_cubit()
    make_everything(extract_data("sample_blanket.json"))
elif __name__ == "__main__":
    # accept command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--file", type=str, help="Name of json file describing geometry", default="")
    parser.add_argument("-i", "--info", type=str, help="Get info on available classes", default='none')
    parser.add_argument("-o", "--output", type=str, help="Root name of output file", default='')
    parser.add_argument("-d", "--destination", type=str, help="Path of directory to generate output file in", default='')
    parser.add_argument("-c", "--config", type=str, help="Name of config json file")
    parser.add_argument("-g", "--geometry", type=str, help="Names of formats to export geometry to", default='')
    parser.add_argument("-m", "--mesh", type=str, help="Name of formats to export mesh to", default='')
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

    # get config file info, CLI > config > default
    config_data = extract_data(args.config) if args.config else {}

    if args.file != "":
        filename = args.file
        filename_source = 'CLI flag'
    elif "file" in config_data.keys():
        filename = config_data["file"]
        filename_source = 'config file'
    else:
        filename = "examples/sample_pin.json"
        filename_source = 'default value'
    print(f"input file name set to {filename} from {filename_source}")

    if args.output != '':
        root_name = args.output
        root_name_source = 'CLI flag'
    elif "root name" in config_data.keys():
        root_name = config_data["root name"]
        root_name_source = 'config file'
    else:
        root_name = "geometry"
        root_name_source = 'default value'
    print(f"output file root name set to {root_name} from {root_name_source}")

    if args.destination != '':
        destination = args.destination
        destination_source = 'CLI flag'
    elif "destination" in config_data.keys():
        destination = config_data["destination"]
        destination_source = 'config file'
    else:
        destination = './'
        destination_source = 'default value'
    if not destination.endswith("/"):
        destination = destination + "/"
    print(f'output file destination set to {destination} from {destination_source}')

    if args.mesh != '':
        export_mesh = str(args.mesh).split(' ')
        mesh_source = 'CLI flag'
    elif "export mesh" in config_data.keys():
        export_mesh = config_data["export mesh"]
        mesh_source = "config file"
    else:
        # dont mesh by default
        export_mesh = []
        mesh_source = False

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

    if args.geometry != '':
        export_geometries = str(args.geometry).split(' ')
        geometry_source = 'CLI flag'
    elif "export geometry" in config_data.keys():
        export_geometries = config_data["export geometry"]
        if type(export_geometries) is str:
            export_geometries = " ".split(export_geometries)
        geometry_source = 'config file'
    elif not export_mesh:
        # only set default if no mesh export provided
        export_geometries = ['cubit']
        geometry_source = 'default value'
    else:
        export_geometries = []
        geometry_source = False

    if geometry_source:
        print(f"geometry export formats set to {', '.join(export_geometries)} from {geometry_source}")
    else:
        print("No geometry will be exported")
    if mesh_source:
        print(f"mesh export formats set to {', '.join(export_mesh)} from {mesh_source}")
    else:
        print("No mesh will be exported")
    
    
    scaling = config_data["output scale exponent"] if "output scale exponent" in config_data.keys() else 0

    filepath = Path(destination, root_name)
    for export_type in export_geometries + export_mesh:
        export_filename = filepath.with_suffix(get_format_extension(export_type))
        if export_filename.exists():
            raise CubismError(f"File {export_filename} already exists.")

    
    scaling = config_data["output scale exponent"] if "output scale exponent" in config_data.keys() else 0

    maker = GeometryMaker()
    maker.print_parameter_logs = True
    maker.track_components = False
    maker.file_to_merged_geometry(filename)
    maker.exp_scale(scaling)

    for export_type in export_geometries:
        maker.export(export_type, str(filepath))
    # only mesh if export mesh format(s) given
    if len(export_mesh) > 0:
        maker.tetmesh()
        for export_type in export_mesh:
            if export_type.lower() == "exodus":
                maker.export_exodus(export_name, large_exodus, hdf5)
            else:
                maker.export(export_type, str(filepath))

