# components in assemblies to be generated
NEUTRON_TEST_FACILITY_REQUIREMENTS = ["room", "source"]
BLANKET_REQUIREMENTS = ["breeder", "structure"]
ROOM_REQUIREMENTS = ["blanket", "surrounding_walls"]
BLANKET_SHELL_REQUIREMENTS = ["first_wall", "pin"]
HCPB_BLANKET_REQUIREMENTS = ["first_wall", "pin", "front_rib", "back_rib", "coolant_outlet_plenum"]

# classes according to what make_geometry subfunction(?) needs to be called
BLOB_CLASSES = ["complex", "breeder", "structure", "air"]
ROOM_CLASSES = ["surrounding_walls"]
WALL_CLASSES = ["wall"]

# currently only supports exclusive, inclusive, and overlap
FACILITY_MORPHOLOGIES = ["exclusive", "inclusive", "overlap", "wall"]

# components requiring only geometry and material parameters
STANDARD_COMPONENTS = ["first wall", "multiplier", "pressure tube", "pin", "structure", "breeder", ]
