BREEDER_UNIT = {
    "class": "breeder unit",
    "materials": {
        "pin": "Steel",
        "pressure tube": "Steel",
        "multiplier": "Beryllium",
        "coolant": "Helium",
        "breeder": "KALOS",
        "filter disk": "SteelMaybe"
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
        "pressure tube length": 420,
        "multiplier length": 420,
        "multiplier side": 72
    }
}

FIRST_WALL = {
    "class": "first wall",
    "material": "Tungsten",
    "geometry": {
        "inner width": 1480,
        "outer width": 1600,
        "bluntness": 100,
        "length": 500,
        "thickness": 30,
        "height": 625
    }
}

BLANKET_SHELL = {
    "class": "blanket shell",
    "geometry": {
        "pin spacing": 135,
        "vertical offset": 0,
        "horizontal offset": 0
    },
    "components": [
        BREEDER_UNIT,
        FIRST_WALL
    ]
}

BLANKET_RING = {
    "class": "blanket ring",
    "geometry": {
        "minimum radius": 580
    },
    "components": [
        {
    "class": "blanket shell",
    "geometry": {
        "pin spacing": 135,
        "vertical offset": 0,
        "horizontal offset": 0
    },
    "components": [
        {
            "class": "first wall",
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
        {
            "class": "breeder unit",
            "materials": {
                "pin": "Steel",
                "pressure tube": "Steel",
                "multiplier": "Beryllium",
                "coolant": "Helium",
                "breeder": "KALOS",
                "filter disk": "SteelMaybe"
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
    ]
}
    ]
}

DEFAULTS = [BREEDER_UNIT, FIRST_WALL, BLANKET_SHELL, BLANKET_RING]