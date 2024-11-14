from hypnos.components import SimpleComponent
from hypnos.geometry import create_brick
from hypnos.geometry_maker import GeometryMaker


class CustomComponent(SimpleComponent):
    def __init__(self, params):
        super().__init__("custom", params)

    def check_sanity(self):
        length = self.geometry["length"]
        height = self.geometry["height"]
        if length < 0 or height < 0:
            raise ValueError("parameters must be positive")

    def make_geometry(self):
        length = self.geometry["length"]
        height = self.geometry["height"]
        brick = create_brick({"dimensions": [length, length, height]})
        return brick


maker = GeometryMaker([CustomComponent])
maker.file_to_tracked_geometry("3custom_component.json")
maker.tetmesh()
maker.export(rootname="custom_geometry")
