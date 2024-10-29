'''
cubit_functions.py
author(s): Sid Mungale

Wrappers for functions/ processes in cubit

Functions
---------
get_last_geometry: get last created geometry of given type
cmd_geom: create geometrical entity and ensure existence
cmd_group: create cubit group and ensure existence
get_id_string: format cubit entity IDs into a string
to_owning_body: convert geometry to owning body
to_bodies: convert geometries to owning bodies
to_volumes: convert bodies to composing volumes
to_surfaces: convert bodies and volumes to composing surfaces
get_entities_from_group: Get geometries belonging to a group
add_to_new_entity: Create group/ block/ sideset and add entities
subtract: subtract a set of geometries from another
union: take the union of a set of geometries

(c) Copyright UKAEA 2024
'''

from blobmaker.generic_classes import (
    CubismError,
    CubitInstance,
    cubit,
    cmd
    )


def initialise_cubit():
    '''Initialise an instance of cubit'''
    cubit.init(['cubit', '-nojournal'])


def reset_cubit():
    cmd("reset")


def get_last_geometry(geometry_type: str) -> CubitInstance:
    '''Get last created geometry of given type

    Parameters
    ----------
    geometry_type : str
        Type of geometry

    Returns
    -------
    CubitInstance
        Last created geometry
    '''
    geom_id = cubit.get_last_id(geometry_type)
    return CubitInstance(geom_id, geometry_type)


def cmd_geom(command: str, geom_type: str) -> CubitInstance:
    '''Create a geometry in cubit.
    Raise an error if creation fails.

    Parameters
    ----------
    command : str
        Cubit command to create geoemtry
    geom_type : str
        Type of geometry intended to create

    Returns
    -------
    CubitInstance
        Created geometry

    Raises
    ------
    CubismError
        If geometry type is not recognised.
        If specified geometry type is not created.
    '''
    if geom_type not in ["vertex", "curve", "surface", "volume", "body"]:
        raise CubismError(f"Geometry type not recognised: {geom_type}")
    pre_id = cubit.get_last_id(geom_type)
    cmd(command)
    post_id = cubit.get_last_id(geom_type)
    if pre_id == post_id:
        raise CubismError(f"no new {geom_type} created, last id created: {pre_id}")
    return CubitInstance(post_id, geom_type)


def cmd_group(command: str) -> int:
    '''Create cubit group.
    Return 0 if group already exists.

    Parameters
    ----------
    command : str
        Cubit command to create group

    Returns
    -------
    int
        ID of created group, or 0
    '''
    pre_id = cubit.get_next_group_id() - 1
    cmd(command)
    post_id = cubit.get_next_group_id() - 1
    if pre_id == post_id:
        return 0
    return post_id


def get_id_string(geometry_list: list[CubitInstance]) -> str:
    '''Convert list of geometries to a string of space-separated IDs.

    Parameters
    ----------
    geometry_list : list[CubitInstance]
        Geometries

    Returns
    -------
    str
        String of space-separated IDs
    '''
    return " ".join([str(geometry.cid) for geometry in geometry_list])


def to_owning_body(geometry: CubitInstance) -> CubitInstance:
    '''Convert geometry to a reference to it's parent body.
    (All geometries like volumes, surfaces, etc. in cubit are
    part of 'body' entities)

    Parameters
    ----------
    geometry : CubitInstance
        Geometry to convert

    Returns
    -------
    CubitInstance
        Parent body
    '''
    assert isinstance(geometry, CubitInstance)
    if geometry.geometry_type == "body":
        return geometry
    else:
        return CubitInstance(cubit.get_owning_body(geometry.geometry_type, geometry.cid), "body")


def to_bodies(component_list: list[CubitInstance]) -> list[CubitInstance]:
    '''Turns geometries (surfaces, volumes, etc.) into references
    to their parent bodies.

    Parameters
    ----------
    component_list : list[CubitInstance]
        list of geometries

    Returns
    -------
    list[CubitInstance]
        list of parent bodies
    '''
    bodies_list = []
    for component in component_list:
        if isinstance(component, CubitInstance):
            if component.geometry_type == "body":
                if component.cid not in [i.cid for i in bodies_list]:
                    bodies_list.append(component)
            else:
                owning_body_id = cubit.get_owning_body(component.geometry_type, component.cid)
                if owning_body_id not in [i.cid for i in bodies_list]:
                    bodies_list.append(CubitInstance(owning_body_id, "body"))
    return bodies_list


def to_volumes(geometry_list: list[CubitInstance]) -> list[CubitInstance]:
    '''Turns bodies into references to their children volumes.
    (All volumes in cubit are owned by 'body' entities)

    Parameters
    ----------
    geometry_list : list[CubitInstance]
        list of bodies

    Returns
    -------
    list[CubitInstance]
        list of children volumes
    '''
    all_volumes_that_exist = cubit.get_entities("volume")
    vol_ids = set([])
    return_list = []

    for component in geometry_list:
        if isinstance(component, CubitInstance) and component.geometry_type == "body":
            for volume_id in all_volumes_that_exist:
                if cubit.get_owning_body("volume", volume_id) == component.cid:
                    vol_ids.add(volume_id)
        elif isinstance(component, CubitInstance) and component.geometry_type == "volume":
            vol_ids.add(component.cid)
        else:
            return_list.append(component)
    return_list.extend([CubitInstance(vol_id, "volume") for vol_id in vol_ids])
    return return_list


def to_surfaces(component_list: list[CubitInstance]) -> list[CubitInstance]:
    '''Turns bodies and volumes into geometries referencing
    their children surfaces.
    (All surfaces and volumes in cubit are owned by 'body' entities)

    Parameters
    ----------
    component_list : list[CubitInstance]
        list of bodies and/or volumes

    Returns
    -------
    list[CubitInstance]
        list of surfaces
    '''
    # convert any stray bodies to volumes
    volumes_list = to_volumes(component_list)
    return_list = []
    surf_ids = set([])

    for component in volumes_list:
        if component.geometry_type == "volume":
            # get surfaces belonging to volume
            surfs = cubit.volume(component.cid).surfaces()
            surf_ids = surf_ids.union({surf.id() for surf in surfs})
        elif component.geometry_type == "surface":
            surf_ids.union({component.cid})

    return_list.extend([CubitInstance(surf_id, "surface") for surf_id in surf_ids])
    return return_list


def get_entities_from_group(group_identifier: int | str, entity_type: str) -> list[int]:
    '''Get cubit entity IDs from cubit group

    Parameters
    ----------
    group_identifier : int | str
        group ID or name
    entity_type : str
        group/ surface/ volume/ etc

    Returns
    -------
    list[int]
        list of IDs

    Raises
    ------
    CubismError
        Group ID/ name not recognised
        Entity type not recognised
    '''
    if type(group_identifier) is str:
        group_identifier = cubit.get_id_from_name(group_identifier)
        if group_identifier == 0:
            raise CubismError("could not find group corresponding to name")
    if entity_type == "surface":
        return list(cubit.get_group_surfaces(group_identifier))
    elif entity_type == "volume":
        return list(cubit.get_group_volumes(group_identifier))
    elif entity_type == "body":
        return list(cubit.get_group_bodies(group_identifier))
    elif entity_type == "vertex":
        return list(cubit.get_group_vertices(group_identifier))
    elif entity_type == "curve":
        return list(cubit.get_group_curves(group_identifier))
    elif entity_type == "group":
        return list(cubit.get_group_groups(group_identifier))
    else:
        raise CubismError(f"Entity type {entity_type} not recognised")


def add_to_new_entity(entity_type: str, name: str, thing_type: str, things_to_add):
    '''Create a new group, block, or sideset.
    Add entities or groups to it.

    Parameters
    ----------
    entity_type : str
        group/ block/ sideset
    name : str
        Name of group/block/sideset
    thing_type : str
        What to add to entity
    things_to_add : int/ list[int]
        IDs of said thing
    '''
    if entity_type in ["block", "sideset"]:
        entity_id = cubit.get_next_block_id() if entity_type == "block" else cubit.get_next_sideset_id()
        cmd(f"create {entity_type} {entity_id}")
        cmd(f"{entity_type} {entity_id} name '{name}'")
    elif entity_type == "group":
        entity_id = cmd_group(f"create group '{name}'")
        if entity_id == 0:
            entity_id = cubit.get_id_from_name(name)

    if isinstance(things_to_add, list):
        things_to_add = " ".join([str(thing) for thing in things_to_add])
    elif type(things_to_add) is int:
        things_to_add = str(things_to_add)

    cmd(f"{entity_type} {entity_id} add {thing_type} {things_to_add}")


def subtract(subtract_from: list[CubitInstance], subtract: list[CubitInstance], destroy=True) -> list[CubitInstance]:
    '''Subtract some geometries from others.

    Parameters
    ----------
    subtract_from : list[CubitInstance]
        Geometries to be subtracted from
    subtract : list[CubitInstance]
        Geometries to subtract
    destroy : bool, optional
        whether to destroy original geometries, by default True

    Returns
    -------
    list[CubitInstance]
        list of subtracted geometries
    '''
    from_ids = {body.cid for body in to_bodies(subtract_from)}
    subtract_from = [body.handle for body in to_bodies(subtract_from)]
    subtract = [body.handle for body in to_bodies(subtract)]
    pre_ids = set(cubit.get_entities("body"))
    if destroy:
        cubit.subtract(subtract, subtract_from)
        post_ids = set(cubit.get_entities("body"))

        common_body_ids = post_ids.intersection(from_ids)
        new_ids = post_ids.difference(pre_ids)

        subtract_ids = list(common_body_ids.union(new_ids))
    else:
        cubit.subtract(subtract, subtract_from, keep_old_in=True)
        post_ids = set(cubit.get_entities("body"))

        subtract_ids = list(post_ids.difference(pre_ids))
    return [CubitInstance(sub_id, "body") for sub_id in subtract_ids]


def union(geometries: list[CubitInstance], destroy=True):
    '''Take the union of a list of geometries

    Parameters
    ----------
    geometries : list[CubitInstance]
        list of geometries to union
    destroy : bool, optional
        whether to destroy original , by default True

    Returns
    -------
    list[CubitInstance]
        list of union'd geometries
    '''
    as_vols = to_volumes(geometries)
    vol_ids = {vol.cid for vol in as_vols}
    vol_id_string = " ".join(str(vol_id) for vol_id in list(vol_ids))
    if destroy:
        cmd(f"unite volume {vol_id_string}")
        all_vols = set(cubit.get_entities("volume"))
        # the created union can have a volume ID(s) from the set of all volumes union'd
        created_vol = list(vol_ids.intersection(all_vols))
    else:
        pre_vols = set(cubit.get_entities("volume"))
        cmd(f"unite volume {vol_id_string} keep")
        post_vols = set(cubit.get_entities("volume"))
        # the created union will have a new volume ID(s)
        created_vol = list(post_vols.difference(pre_vols))
    return [CubitInstance(vol, "volume") for vol in created_vol]

# unionise is in Assemblies.py as it needs to know about the
# ComplexComponent and Assembly classes
