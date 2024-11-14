'''
constants.py
author(s): Sid Mungale

Global constants

(c) Copyright UKAEA 2024
'''

# required components for assemblies to be generated
NEUTRON_TEST_FACILITY_REQUIREMENTS = ["RoomAssembly", "SourceAssembly"]
BLANKET_REQUIREMENTS = ["BreederComponent", "StructureComponent"]
ROOM_REQUIREMENTS = ["BlanketComponent", "SurroundingWallsComponent"]
BLANKET_SHELL_REQUIREMENTS = ["FirstWallComponent", "PinAssembly"]
HCPB_BLANKET_REQUIREMENTS = [
    "FirstWallComponent",
    "PinAssembly",
    "FrontRib",
    "BackRib",
    "CoolantOutletPlenum"
    ]

# LEGACY - currently only supports exclusive, inclusive, and overlap
FACILITY_MORPHOLOGIES = ["exclusive", "inclusive", "overlap", "wall"]
