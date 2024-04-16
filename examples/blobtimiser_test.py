from pathlib import Path
from blobmaker import GeometryMaker

mesh_filepath = Path("ex02.e")
parameters = {
    "geometry/outer length": 350,
    "geometry/multiplier length": 350,
}

# Generate trial geometry.
geometry = GeometryMaker()
geometry.parse_json(str("./examples/sample_pin.json"))
geometry.change_params(parameters)
geometry.make_geometry()
geometry.imprint_and_merge()

# Generate mesh and export to file.
geometry.set_mesh_size(4)
geometry.tetmesh()
geometry.export_mesh(
    str(mesh_filepath.name),
    str(mesh_filepath.parent),
)
geometry.reset_cubit()