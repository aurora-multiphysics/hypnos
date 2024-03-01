BREEDER_UNIT = {
    "class": "breeder_unit",
    "materials": {
        "pin": "EUROFER",
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
    "class": "first_wall",
    "material": "Tungsten",
    "geometry": {
        "inner width": 1480,
        "outer width": 1600,
        "bluntness": 100,
        "length": 500,
        "thickness": 30,
        "sidewall thickness": 25,
        "height": 625
    }
}

BLANKET_SHELL = {
    "class": "blanket_shell",
    "geometry": {
        "pin spacing": 135,
        "vertical offset": 0,
        "horizontal offset": 0
    },
    "components": {
        "breeder_unit": BREEDER_UNIT,
        "first_wall": FIRST_WALL
    }
}

BLANKET_RING = {
    "class": "blanket_ring",
    "geometry": {
        "minimum radius": 580
    },
    "components": {
    "blanket_shell": {
    "class": "blanket_shell",
    "geometry": {
        "pin spacing": 135,
        "vertical offset": 0,
        "horizontal offset": 0
    },
    "components": {
        "first_wall": {
            "class": "first_wall",
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
        "breeder_unit": {
            "class": "breeder_unit",
            "materials": {
                "pin": "EUROFER",
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
    "class": "HCPB_blanket",
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
        "breeder_unit": BREEDER_UNIT,
        "first_wall": FIRST_WALL,
        "front_rib": {
            "class": "front_rib",
            "geometry": {
                "thickness": 30,
                "side channel width": 10,
                "side channel height": 10,
                "side channel horizontal offset": 0
            }
        },
        "back_rib": {
            "class": "back_rib",
            "geometry": {
                "thickness": 60,
                "side channel width": 10,
                "side channel height": 10,
                "side channel horizontal offset": 70
            }
        },
        "coolant_outlet_plenum": {
            "class": "coolant_outlet_plenum",
            "geometry": {
                "length": 120,
                "width": 1000,
                "thickness": 15
            }
        }
    }
}

DEFAULTS = [BREEDER_UNIT, FIRST_WALL, BLANKET_SHELL, BLANKET_RING, HCPB_BLANKET]