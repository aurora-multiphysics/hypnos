from blobmaker.default_params import FIRST_WALL
from blobmaker.cubit_functions import cmd
from blobmaker.geometry_maker import GeometryMaker
import cubit

def test_first_wall(pytestconfig):
    cubit.reset()
    gold_dir = pytestconfig.rootpath / "tests" / "gold"
    first_wall_path = gold_dir / "sample_first_wall.json"
    
    maker = GeometryMaker()
    maker.design_tree = FIRST_WALL
    stray_volumes = set(cubit.get_entities("volume"))
    cmd(f'import cubit "{first_wall_path}"')
    post_import_volumes = cubit.get_entities("volume")
    gold_volumes = post_import_volumes.difference(stray_volumes)
    maker.make_geometry()
    maker.imprint_and_merge()
    maker_volumes = set(cubit.get_entities("volume")).difference(post_import_volumes)
    
    