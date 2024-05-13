import pytest
import cubit
from blobmaker.components import SimpleComponent

@pytest.fixture(scope="session", autouse=True)
def initialise():
    return cubit.init([])

@pytest.fixture(scope="module")
def geometry_json():
    return {
        "material": "Steel",
        "geometry": {
            "dimensions": 5
        },
        "origin": [10, 0, 0]
    }

@pytest.fixture(scope="function")
def simple_component(geometry_json):
    cubit.reset()
    return SimpleComponent("air", geometry_json)