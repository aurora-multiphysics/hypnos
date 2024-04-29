import pytest
import cubit

@pytest.fixture(scope="session", autouse=True)
def initialise():
    return cubit.init([])
