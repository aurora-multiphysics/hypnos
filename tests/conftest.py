import pytest
import cubit
from hypnos.generic_classes import CubitInstance


# initialise cubit once
@pytest.fixture(scope="session", autouse=True)
def initialise():
    return cubit.init([])


# cleanup after every test
@pytest.fixture(autouse=True)
def reset():
    yield 0
    cubit.reset()


@pytest.fixture(scope='function')
def brick():
    cubit.brick(1, 1, 1)
    return CubitInstance(1, "body")
