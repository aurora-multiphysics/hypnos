# components in assemblies to be generated
NEUTRON_TEST_FACILITY_REQUIREMENTS = ["room", "source"]
NEUTRON_TEST_FACILITY_ADDITIONAL = []
BLANKET_REQUIREMENTS = ["breeder", "structure"]
BLANKET_ADDITIONAL = ["coolant", "multiplier"]
ROOM_REQUIREMENTS = ["blanket", "surrounding_walls"]
ROOM_ADDITIONAL = ["wall"]

# classes according to what make_geometry subfunction(?) needs to be called
BLOB_CLASSES = ["complex", "breeder", "structure", "air"]
ROOM_CLASSES = ["surrounding_walls"]
WALL_CLASSES = ["wall"]

# currently only supports exclusive, inclusive, and overlap
FACILITY_MORPHOLOGIES= ["exclusive", "inclusive", "overlap", "wall"]

# mapping from json class names to python class names
CLASS_MAPPING = {
    "complex": "ComplexComponent",
    "external": "ExternalComponentAssembly",
    "source": "SourceAssembly",
    "neutron test facility": "NeutronTestFacility",
    "blanket": "BlanketAssembly",
    "room": "RoomAssembly",
    "surrounding_walls": "SurroundingWallsComponent",
    "breeder": "BreederComponent",
    "structure": "StructureComponent",
    "breeder unit": "BreederUnitAssembly",
    "pin": "PinComponent",
    "pressure tube": "PressureTubeComponent",
    "multiplier": "MultiplierComponent",
    "first wall": "FirstWallComponent"
}