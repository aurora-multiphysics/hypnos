Blobmaker is a parametric geometry engine to create meshes for structures involved in the analysis of breeder blankets.

Requirements:
A coreform cubit license
Python 3 (along with the cubit library)

Usage:
Blobmaker uses json files to describe parameters of a component.
Components are represented by json objects "{ }", using the "class" key to select a specific component type.
Json files containing a json object describing a component (ex. hcpb_breeder_unit.json) can be used where such a json object is expected by using a string with the file name (ex. {"class": "blanket" ... "components" : \["hpcb_breeder_unit.json"]})

Examples of usage are given in sample json files