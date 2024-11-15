from hypnos.cubit_functions import reset_cubit
from hypnos.parsing import extract_data, Args
from hypnos.default_params import DEFAULTS
from hypnos.geometry_maker import make_everything, GeometryMaker
import pprint
import argparse


if __name__ == '__coreformcubit__':
    reset_cubit()
    make_everything(extract_data("sample_blanket.json"))
elif __name__ == "__main__":
    # accept command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--file", type=str, help="Name of json file describing geometry")
    parser.add_argument("-i", "--info", type=str, help="Get info on available classes")
    parser.add_argument("-c", "--config", type=str, help="Name of config json file")
    args = parser.parse_args()
    args = Args(args.file, args.config, info=args.info)

    if args.info:
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

    maker = GeometryMaker(args.config, args.filename)
    maker.export_from_config()
