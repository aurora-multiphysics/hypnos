'''Global constants'''

# required components for assemblies to be generated
NEUTRON_TEST_FACILITY_REQUIREMENTS = ["room", "source"]
BLANKET_REQUIREMENTS = ["breeder", "structure"]
ROOM_REQUIREMENTS = ["blanket", "surrounding_walls"]
BLANKET_SHELL_REQUIREMENTS = ["first_wall", "pin"]
HCPB_BLANKET_REQUIREMENTS = [
    "first_wall",
    "pin",
    "front_rib",
    "back_rib",
    "coolant_outlet_plenum"
    ]

# LEGACY - classes according to what make_geometry subfunction(?) needs to be called
BLOB_CLASSES = ["complex", "breeder", "structure", "air"]
ROOM_CLASSES = ["surrounding_walls"]
WALL_CLASSES = ["wall"]

# LEGACY - currently only supports exclusive, inclusive, and overlap
FACILITY_MORPHOLOGIES = ["exclusive", "inclusive", "overlap", "wall"]

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
    "pin": "PinAssembly",
    "cladding": "CladdingComponent",
    "pressure_tube": "PressureTubeComponent",
    "multiplier": "MultiplierComponent",
    "first_wall": "FirstWallComponent",
    "blanket_shell": "BlanketShellAssembly",
    "blanket_ring": "BlanketRingAssembly",
    "HCPB_blanket": "HCPBBlanket"
}
