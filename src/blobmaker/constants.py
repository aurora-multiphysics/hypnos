# components in assemblies to be generated
NEUTRON_TEST_FACILITY_REQUIREMENTS = ["room", "source"]
BLANKET_REQUIREMENTS = ["breeder", "structure"]
ROOM_REQUIREMENTS = ["blanket", "surrounding_walls"]
BLANKET_SHELL_REQUIREMENTS = ["first_wall", "breeder_unit"]
HCPB_BLANKET_REQUIREMENTS = ["first_wall", "breeder_unit", "front_rib", "back_rib", "coolant_outlet_plenum"]

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
    "neutron_test_facility": "NeutronTestFacility",
    "blanket": "BlanketAssembly",
    "room": "RoomAssembly",
    "surrounding_walls": "SurroundingWallsComponent",
    "breeder": "BreederComponent",
    "structure": "StructureComponent",
    "breeder_unit": "BreederUnitAssembly",
    "pin": "PinComponent",
    "pressure_tube": "PressureTubeComponent",
    "multiplier": "MultiplierComponent",
    "first_wall": "FirstWallComponent",
    "blanket_shell": "BlanketShellAssembly",
    "blanket_ring": "BlanketRingAssembly",
    "HCPB_blanket":"HCPBBlanket"
}

# components requiring only geometry and material parameters
STANDARD_COMPONENTS = ["first wall", "multiplier", "pressure tube", "pin", "structure", "breeder", ]

# some flags because i am lazy
IMPRINT_AND_MERGE = True
MESH = False