from hypnos.tracking import Tracker
from hypnos.assemblies import PinAssembly
from hypnos.default_params import PIN
from hypnos.geometry_maker import GeometryMaker
import cubit
import pytest


@pytest.fixture
def maker():
    '''geometrymaker with tracked blocks and sidesets for a pin'''
    cubit.reset()
    maker = GeometryMaker()
    maker.constructed_geometry = [PinAssembly(PIN)]
    maker.imprint_and_merge()
    maker.track_components_and_materials()
    return maker


@pytest.fixture
def tracker(maker):
    '''materialstracker of a tracked pin
    '''
    return maker.materials_tracker


# MaterialsTracker tests
def test_reset():
    tracker = Tracker()
    tracker.components = ["test"]
    tracker.blocks = ["test"]
    tracker.sidesets = ["test"]
    tracker.materials = {"test"}
    tracker.material_boundaries = ["test"]
    tracker.materials_to_sidesets = {"test": "test"}
    tracker.types_to_sidesets = {"test": "test"}
    tracker.external_separator = "++"
    tracker.internal_separator = "++"

    tracker.reset()

    assert tracker.components == []
    assert tracker.blocks == []
    assert tracker.sidesets == []
    assert tracker.materials == set()
    assert tracker.material_boundaries == []
    assert tracker.materials_to_sidesets == {}
    assert tracker.types_to_sidesets == {}
    assert tracker.external_separator == "_"
    assert tracker.internal_separator == "---"


def test_extract_components():
    tracker = Tracker()
    pin = PinAssembly(PIN)
    components = pin.get_all_components()
    tracker.extract_components(pin)

    assert tracker.materials == set(PIN["materials"].values())
    assert tracker.components == components


def exo_name(entity_type: str, cid: int):
    return cubit.get_exodus_entity_name(entity_type, cid)


def get_exo_names(exo_type: str):
    if exo_type == "sideset":
        id_list = cubit.get_sideset_id_list()
    elif exo_type == "block":
        id_list = cubit.get_block_id_list()
    else:
        raise ValueError("exo_type must be either 'block' or 'sideset'")
    return [exo_name(exo_type, cid) for cid in id_list]


def test_track_boundaries(maker):
    # just to help with type hints
    assert isinstance(maker, GeometryMaker)

    # check whether sidesets are as expected
    sidesets = set(get_exo_names("sideset"))
    assert sidesets == set(maker.tracker.sidesets)
    assert sidesets == {
        'cladding0_filter_lid0',
        'cladding0_air',
        'cladding0_coolant0',
        'breeder0_cladding0',
        'cladding0_purge_gas0',
        'cladding0_filter_disk0',
        'pressure_tube0_air',
        'multiplier0_pressure_tube0',
        'coolant0_pressure_tube0',
        'multiplier0_air',
        'breeder0_filter_disk0',
        'breeder0_filter_lid0',
        'filter_disk0_air',
        'filter_lid0_purge_gas0',
        'coolant0_air',
        'purge_gas0_air'
        }

    # check whether blocks are as expected
    blocks = set(get_exo_names("block"))
    assert blocks == set(maker.tracker.blocks)
    assert blocks == {
        'filter_lid0',
        'multiplier0',
        'cladding0',
        'breeder0',
        'purge_gas0',
        'pressure_tube0',
        'filter_disk0',
        'coolant0'
        }


def test_make_boundary_name():
    tracker = Tracker()
    int_sep = tracker.internal_separator
    ext_sep = tracker.external_separator
    boundary_name = tracker.make_boundary_name
    assert boundary_name(['test']) == f"test{ext_sep}air"
    assert boundary_name(['epic', 'name']) == f"epic{ext_sep}name"
    assert boundary_name(['test'], True) == f"test{int_sep}air"
    assert boundary_name(['epic', 'name'], True) == f"epic{int_sep}name"


def group_dict() -> dict:
    cubitlike = list(cubit.group_names_ids())
    dictlike = {name: value for (name, value) in cubitlike}
    return dictlike


def get_subgroup_names(grp_name: str) -> set:
    group_map = group_dict()
    inverted_map = {value: key for key, value in group_map.items()}
    id_list = list(cubit.get_group_groups(group_map[grp_name]))
    name_list = [inverted_map[gp_id] for gp_id in id_list]
    return set(name_list)


def test_organise_into_groups(maker):
    assert isinstance(maker, GeometryMaker)
    tracker = maker.tracker

    groups = group_dict().keys()
    assert "materials" in groups
    assert "simple_components" in groups
    assert "component_boundaries" in groups
    assert "material_boundaries" in groups

    materials = get_subgroup_names("materials")
    simple_comps = get_subgroup_names("simple_components")
    comp_boundaries = get_subgroup_names("component_boundaries")
    mat_boundaries = get_subgroup_names("material_boundaries")

    assert materials == tracker.materials
    pin_components = maker.constructed_geometry[0].get_all_components()
    comp_names = {comp.identifier for comp in pin_components}
    assert simple_comps == comp_names
    assert mat_boundaries == set(tracker.material_boundaries)
    assert comp_boundaries == set(tracker.sidesets)
