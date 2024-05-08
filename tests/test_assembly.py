import pytest
from blobmaker.assemblies import GenericComponentAssembly
from blobmaker.components import SimpleComponent

@pytest.fixture()
def gca(simple_component):
    gca = GenericComponentAssembly("test_class")
    gca.components = [simple_component]
    return gca

class TestGenericAssembly:
    def test_get_handles_from_class(self, gca: GenericComponentAssembly):
        comp = gca.get_handles_from_class([SimpleComponent])
        assert comp[0].centroid() == (10, 0, 0)
