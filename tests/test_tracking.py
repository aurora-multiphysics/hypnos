from blobmaker.tracking import MaterialsTracker
from blobmaker.geometry_maker import GeometryMaker
import cubit

# MaterialsTracker tests

def test_extract_components():
    maker = GeometryMaker()
    maker.design_tree = {"class": "pin"}
    maker.fill_design_tree()
    maker.make_tracked_geometry()

    track = MaterialsTracker()
    track.extract_components()

