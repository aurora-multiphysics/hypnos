'''
default_params.py
author(s): Sid Mungale

default parameter dictionaries

(c) Copyright UKAEA 2024
'''

PIN = {
    "class": "PinAssembly",
    "material": {
        "cladding": "EUROFER",
        "pressure tube": "EUROFER",
        "multiplier": "Beryllium",
        "coolant": "Helium",
        "breeder": "KALOS",
        "filter disk": "EUROFER",
        "filter lid": "Perf_Steel",
        "purge gas": "H_He"
    },
    "geometry": {
        "outer length": 370,
        "inner length": 500,
        "offset": 60,
        "bluntness": 5,
        "inner cladding": 6,
        "outer cladding": 3,
        "breeder chamber thickness": 16,
        "coolant inlet radius": 8,
        "filter disk thickness": 10,
        "pressure tube gap": 20,
        "pressure tube outer radius": 40,
        "pressure tube thickness": 1,
        "pressure tube length": 400,
        "multiplier length": 385,
        "multiplier side": 72,
        "purge duct thickness": 1,
        "purge duct cladding": 2,
        "purge duct offset": 30,
        "filter lid length": 300
    }
}

FIRST_WALL = {
    "class": "FirstWallComponent",
    "material": "Tungsten",
    "geometry": {
        "inner width": 1480,
        "outer width": 1600,
        "bluntness": 100,
        "length": 1000,
        "thickness": 30,
        "sidewall thickness": 25,
        "height": 625,
        "channel width": 10,
        "channel back manifold offset": 100,
        "channel back manifold width": 159,
        "channel front manifold offset": 269,
        "channel front manifold width": 159,
        "channel padding": 10,
        "channel depth": 10,
        "channel spacing": 10
    }
}

BLANKET_SHELL = {
    "class": "BlanketShellAssembly",
    "geometry": {
        "pin spacing": 135,
        "vertical offset": 0,
        "horizontal offset": 0
    },
    "components": {
        "PinAssembly": PIN,
        "FirstWallComponent": FIRST_WALL
    }
}

BLANKET_RING = {
    "class": "BlanketRingAssembly",
    "geometry": {
        "minimum radius": 580
    },
    "components": {
        "BlanketShellAssembly": {
            "class": "BlanketShellAssembly",
            "geometry": {
                "pin spacing": 135,
                "vertical offset": 0,
                "horizontal offset": 0
            },
            "components": {
                "FirstWallComponent": {
                    "class": "FirstWallComponent",
                    "material": "Tungsten",
                    "geometry": {
                        "inner width": 480,
                        "outer width": 600,
                        "bluntness": 0,
                        "length": 500,
                        "thickness": 30,
                        "height": 580
                    }
                },
                "PinAssembly": {
                    "class": "PinAssembly",
                    "material": {
                            "cladding": "EUROFER",
                            "pressure tube": "EUROFER",
                            "multiplier": "Beryllium",
                            "coolant": "Helium",
                            "breeder": "KALOS",
                            "filter disk": "EUROFER"
                        },
                    "geometry": {
                        "outer length": 370,
                        "inner length": 500,
                        "offset": 60,
                        "bluntness": 5,
                        "inner cladding": 6,
                        "outer cladding": 3,
                        "breeder chamber thickness": 16,
                        "coolant inlet radius": 8,
                        "filter disk thickness": 10,
                        "pressure tube gap": 20,
                        "pressure tube outer radius": 40,
                        "pressure tube thickness": 1,
                        "pressure tube length": 300,
                        "multiplier length": 200,
                        "multiplier side": 72
                    }
                }
            }
        }
    }
}

HCPB_BLANKET = {
    "class": "HCPBBlanket",
    "geometry": {
        "pin spacing": 135,
        "pin vertical offset": 0,
        "pin horizontal offset": 0,
        "front rib positions": [
            3,
            7
        ],
        "PG front plate thickness": 5,
        "PG mid plate thickness": 5,
        "PG mid plate gap": 20,
        "PG back plate thickness": 15,
        "rib connection height": 10,
        "rib connection width": 10,
        "rib side channel gap": 107,
        "rib side channel vertical margin": 50,
        "coolant outlet plenum gap": 30,
        "separator plate gap": 30,
        "separator plate thickness": 10,
        "FW backplate thickness": 100
    },
    "components": {
        "PinAssembly": {
            "class": "PinAssembly",
            "material": {
                "cladding": "EUROFER",
                "pressure tube": "EUROFER",
                "multiplier": "Beryllium",
                "coolant": "Helium",
                "breeder": "KALOS",
                "filter disk": "EUROFER",
                "filter lid": "Perf_Steel",
                "purge gas": "H_He"
            },
            "geometry": {
                "outer length": 370,
                "inner length": 500,
                "offset": 60,
                "bluntness": 5,
                "inner cladding": 6,
                "outer cladding": 3,
                "breeder chamber thickness": 16,
                "coolant inlet radius": 8,
                "filter disk thickness": 10,
                "pressure tube gap": 20,
                "pressure tube outer radius": 40,
                "pressure tube thickness": 1,
                "pressure tube length": 400,
                "multiplier length": 385,
                "multiplier side": 72,
                "purge duct thickness": 1,
                "purge duct cladding": 2,
                "purge duct offset": 30,
                "filter lid length": 300
            }
        },
        "FirstWallComponent": {
            "class": "FirstWallComponent",
            "material": "Tungsten",
            "geometry": {
                "inner width": 1480,
                "outer width": 1600,
                "bluntness": 100,
                "length": 1000,
                "thickness": 30,
                "sidewall thickness": 25,
                "height": 625,
                "channel width": 10,
                "channel back manifold offset": 100,
                "channel back manifold width": 159,
                "channel front manifold offset": 269,
                "channel front manifold width": 159,
                "channel padding": 10,
                "channel depth": 10,
                "channel spacing": 10
            }
        },
        "FrontRib": {
            "class": "FrontRib",
            "geometry": {
                "thickness": 30,
                "side channel width": 10,
                "side channel height": 10,
                "side channel horizontal offset": 0
            }
        },
        "BackRib": {
            "class": "BackRib",
            "geometry": {
                "thickness": 60,
                "side channel width": 10,
                "side channel height": 10,
                "side channel horizontal offset": 70
            }
        },
        "CoolantOutletPlenum": {
            "class": "CoolantOutletPlenum",
            "geometry": {
                "length": 120,
                "width": 1000,
                "thickness": 15
            }
        }
    }
}

DEFAULTS = [PIN, FIRST_WALL, BLANKET_SHELL, BLANKET_RING, HCPB_BLANKET]
