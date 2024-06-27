from blobmaker.generic_classes import CubismError, CubitInstance, cubit, cmd


def initialise_cubit():
    '''Wrapper for initialising cubit'''
    cubit.init(['cubit', '-nojournal'])


def reset_cubit():
    cmd("reset")


def get_last_geometry(geometry_type: str):
    '''Get last created geometry of given type

    :param geometry_type: type of geometry to search for.
    :type geometry_type: str
    :return: geometry
    :rtype: CubitInstance
    '''
    geom_id = cubit.get_last_id(geometry_type)
    return CubitInstance(geom_id, geometry_type)


def cmd_check(command: str, id_type: str):
    '''Perform cubit command and check whether a new entity has been created.
    If this is a geometry return CubitInstance, if a group then the group id.

    :param cmd: command to run
    :type cmd: str
    :param id_type: type of entity to check for
    :type id_type: str
    :return: geometry/ id/ false
    :rtype: CubitInstance/ int/ bool
    '''
    if id_type == "group" and float(cubit.get_version()) > 2023.8:
        pre_id = cubit.get_next_group_id() - 1
        cmd(command)
        post_id = cubit.get_next_group_id() - 1
    else:
        pre_id = cubit.get_last_id(id_type)
        cmd(command)
        post_id = cubit.get_last_id(id_type)
    if pre_id == post_id:
        if not id_type == "group":
            raise CubismError(f"no new {id_type} created, last id: {pre_id}")
        # material tracking function depends on this btw
        return False
    elif id_type == "group" and type(post_id) is int:
        return post_id
    else:
        return CubitInstance(post_id, id_type)


def get_id_string(geometry_list: list[CubitInstance]):
    '''Convert list of CubitInstances to a string of space-separated IDs.

    :param geometry_list: list to convert
    :type geometry_list: list[CubitInstance]
    :return: string of IDs
    :rtype: str
    '''
    return " ".join([str(geometry.cid) for geometry in geometry_list])


# functions to delete and copy lists
def delete_instances(component_list: list):
    '''Deletes cubit instances of all geometries

    :param component_list: List of geometries
    :type component_list: list[CubitInstance]
    '''
    for component in component_list:
        if isinstance(component, CubitInstance):
            component.destroy_cubit_instance()


def copy_geometries(geometry_list: list):
    '''Copy geometries

    :param component_list: List of geometries
    :type component_list: list[CubitInstance]
    :raises CubismError: All items in list are not geometries
    '''
    copied_list = []
    for component in geometry_list:
        if isinstance(component, CubitInstance):
            copied_list.append(component.copy())
        else:
            raise CubismError("All items in list are not geometries :(")
    return copied_list


# THIS IS VERY SILLY WHY DO I HAVE TO DO THIS
def to_owning_body(geometry: CubitInstance):
    '''Convert entity reference to a reference to it's parent body

    :param geometry: Physical entity to convert
    :type component: CubitInstance
    :return: Parent body entity
    :rtype: CubitInstance
    '''
    assert isinstance(geometry, CubitInstance)
    if geometry.cid == "body":
        return geometry
    else:
        return CubitInstance(cubit.get_owning_body(geometry.geometry_type, geometry.cid), "body")


def get_bodies_and_volumes_from_group(group_id: int):
    '''Find bodies and volumes at the top-level of a group.

    :param group_id: ID of group
    :type group_id: int
    :return: list of bodies and volumes as GenericCubitInstances
    :rtype: list
    '''
    instance_list = []
    body_ids = cubit.get_group_bodies(group_id)
    for body_id in body_ids:
        instance_list.append(CubitInstance(body_id, "body"))
    volume_ids = cubit.get_group_volumes(group_id)
    for volume_id in volume_ids:
        instance_list.append(CubitInstance(volume_id, "volume"))
    return instance_list


def remove_overlaps_between_geometries(from_list: list[CubitInstance], tool_list: list[CubitInstance]):
    '''Remove overlaps between lists of geometries

    :param from_list: List of geometries from which the overlap will be subtracted
    :type from_list: list[CubitInstance]
    :param tool_list: List of geometries kept as is
    :type tool_list: list[CubitInstance]
    '''
    from_volumes = to_volumes(from_list)
    tool_volumes = to_volumes(tool_list)
    # check each pair
    for from_volume in from_volumes:
        for tool_volume in tool_volumes:
            # if there is an overlap, remove it
            if not (cubit.get_overlapping_volumes([from_volume.cid, tool_volume.cid]) == ()):
                cmd(f"remove overlap volume {tool_volume.cid} {from_volume.cid} modify volume {from_volume.cid}")


def to_volumes(geometry_list: list) -> list[CubitInstance]:
    '''Turns references to bodies into references to their children volumes.

    :param component_list: List of geometries
    :type component_list: list[CubitInstance]
    :return: List of converted geometries
    :rtype: list[CubitInstance]
    '''
    all_volumes_that_exist = cubit.get_entities("volume")
    return_list = []
    for component in geometry_list:
        if isinstance(component, CubitInstance) and component.geometry_type == "body":
            for volume_id in all_volumes_that_exist:
                if cubit.get_owning_body("volume", volume_id) == component.cid:
                    return_list.append(CubitInstance(volume_id, "volume"))
        else:
            return_list.append(component)
    return return_list


def to_surfaces(component_list: list[CubitInstance]) -> list[CubitInstance]:
    '''Turns geometries referencing bodies and volumes into
     geometries referencing their children surfaces.

    :param component_list: List of geometries
    :type component_list: list[CubitInstance]
    :return: List of converted geometries
    :rtype: list[CubitInstance]
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
        else:
            return_list.append(component)
    return_list.extend([CubitInstance(surf_id, "surface") for surf_id in surf_ids])
    return list(set(return_list))


def to_bodies(component_list: list) -> list[CubitInstance]:
    '''Turns references to entities into references to their parent bodies.

    :param component_list: List of geometries
    :type component_list: list[CubitInstance]
    :return: List of converted geometries
    :rtype: list[CubitInstance]
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


def get_entities_from_group(group_identifier: int | str, entity_type: str) -> list[int]:
    '''Get specified cubit entity IDs from cubit group

    :param group_identifier: ID or name of group
    :type group_identifier: int | str
    :param entity_type: Name of entity type
    :type entity_type: str
    :return: list of cubit IDs
    :rtype: list[int]
    '''
    if type(group_identifier) is str:
        group_identifier = cubit.get_id_from_name(group_identifier)
        if group_identifier == 0:
            raise CubismError("could not find group corresponding to name")
    if entity_type == "surface":
        return cubit.get_group_surfaces(group_identifier)
    elif entity_type == "volume":
        return cubit.get_group_volumes(group_identifier)
    elif entity_type == "body":
        return cubit.get_group_bodies(group_identifier)
    elif entity_type == "vertex":
        return cubit.get_group_vertices(group_identifier)
    elif entity_type == "group":
        return cubit.get_group_groups(group_identifier)
    else:
        raise CubismError(f"Entity type {entity_type} not recognised")

def add_to_new_entity(entity_type: str, name: str, thing_type: str, things_to_add):
    '''Create a new group, block, or sideset. Add entities or groups to it.

    :param entity_type: group | block | sideset
    :type entity_type: str
    :param name: Name to give group/ block/ sideset
    :type name: str
    :param thing_type: Type of entity to add
    :type thing_type: str
    :param things_to_add: List or string of corresponding IDs
    :type things_to_add: list[int] | str
    '''
    if entity_type in ["block", "sideset"]:
        entity_id = cubit.get_next_block_id() if entity_type == "block" else cubit.get_next_sideset_id()
        cmd(f"create {entity_type} {entity_id}")
        cmd(f"{entity_type} {entity_id} name '{name}'")
    elif entity_type == "group":
        entity_id = cmd_check(f"create group '{name}'", "group")
        if entity_id == 0:
            entity_id = cubit.get_id_from_name(name)

    if isinstance(things_to_add, list):
        things_to_add = " ".join([str(thing) for thing in things_to_add])

    cmd(f"{entity_type} {entity_id} add {thing_type} {things_to_add}")


def subtract(subtract_from: list[CubitInstance], subtract: list[CubitInstance], destroy=True):
    '''Subtract some geometries from others.

    :param subtract_from: geometries to subtract from
    :type subtract_from: list[CubitInstance]
    :param subtract: geometries to be subtracted
    :type subtract: list[CubitInstance]
    :param destroy: whether or not to destroy original geometries, defaults to True
    :type destroy: bool
    :return: geometries resulting from subtraction
    :rtype: list[CubitInstance]
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

    :param geometries: Geometries to unite
    :type geometries: list[CubitInstance]
    :param destroy: whether to destroy the original geometries , defaults to True
    :type destroy: bool, optional
    :return: list of volumes created in union
    :rtype: list[CubitInstance]
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
