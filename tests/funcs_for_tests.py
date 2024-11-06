'''
Functions used in tests
'''

from blobmaker.geometry_maker import GeometryMaker
from blobmaker.generic_classes import (
    cmd,
    CubitInstance
)
from blobmaker.cubit_functions import union
import cubit


def get_union_volumes(goldfile: str, maker_tree: dict):
    '''Get the volumes of the gold file geometry, geometry from a design tree,
    and their union

    :param goldfile: gold filepath
    :type goldfile: str
    :param maker_tree: design tree
    :type maker_tree: dict
    :return: volume values
    :rtype: tuple[int]
    '''

    # instantiate maker in case cubit.init() changes anything
    maker = GeometryMaker()

    # import gold file, get its volumes
    stray_vol_ids = vols()
    cmd(f'import cubit "{goldfile}"')
    post_import_vol_ids = vols()
    gold_vol_ids = post_import_vol_ids.difference(stray_vol_ids)

    # make geometry, get its volumes
    maker.design_tree = maker_tree
    maker.make_geometry()
    maker_vol_ids = vols().difference(post_import_vol_ids)

    # union of all gold volumes, all maker volumes
    gold_union = union([CubitInstance(vol_id, "volume") for vol_id in list(gold_vol_ids)])
    maker_union = union([CubitInstance(vol_id, "volume") for vol_id in list(maker_vol_ids)])

    gold_volume = sum([vol.handle.volume() for vol in gold_union])
    maker_volume = sum([vol.handle.volume() for vol in maker_union])

    # union of above 2 unions
    net_union = union(gold_union + maker_union)
    net_volume = sum([vol.handle.volume() for vol in net_union])

    return gold_volume, maker_volume, net_volume


def vols() -> set:
    '''Get all IDs for volumes that currently exist in cubit.

    Returns
    -------
    set
        volume IDs
    '''
    return set(cubit.get_entities("volume"))
