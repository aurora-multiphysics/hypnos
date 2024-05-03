import pytest
import cubit

@pytest.fixture(scope="session", autouse=True)
def initialise():
    return cubit.init([])

@pytest.fixture(scope="function", autouse=True)
def reset():
    return cubit.reset()