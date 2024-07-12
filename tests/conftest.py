import pytest
import cubit

# initialise cubit once
@pytest.fixture(scope="session", autouse=True)
def initialise():
    return cubit.init([])

# cleanup after every test
@pytest.fixture(autouse=True)
def reset():
    yield 0
    cubit.reset()
