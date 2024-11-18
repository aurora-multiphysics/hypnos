'''
constants.py
author(s): Sid Mungale

Global constants

(c) Copyright UKAEA 2024
'''

# required components for assemblies to be generated
HCPB_BLANKET_REQUIREMENTS = [
    "first_wall",
    "pin",
    "front_rib",
    "back_rib",
    "coolant_outlet_plenum"
    ]


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
