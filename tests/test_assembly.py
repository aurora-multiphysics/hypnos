import pytest
from blobmaker.assemblies import GenericComponentAssembly
from blobmaker.components import SimpleComponent

@pytest.fixture()
def gca(simple_component):
    gca = GenericComponentAssembly("test_class")
    gca.components = [simple_component]
    return gca

