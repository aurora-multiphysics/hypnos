from blobmaker.generic_classes import CubismError, CubitInstance, cubit, cmd


def initialise_cubit():
    '''Wrapper for initialising cubit'''
    cubit.init(['cubit', '-nojournal'])


def reset_cubit():
    cmd("reset")


def get_last_geometry(geometry_type: str):
    '''Get last geometry of given type

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
    pre_id = cubit.get_last_id(id_type)
    cmd(command)
    post_id = cubit.get_last_id(id_type)
    if pre_id == post_id:
        if not id_type == "group":
            raise CubismError(f"no new {id_type} created, last id: {pre_id}")
        # material tracking function depends on this btw
        return False
    elif id_type == "group":
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
    id_string = ""
    for geometry in geometry_list:
        id_string += f"{geometry.cid} "
    return id_string


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
            copied_list.append(component.copy_cubit_instance())
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
        if isinstance(component, CubitInstance):
            if component.geometry_type == "body":
                for volume_id in all_volumes_that_exist:
                    if cubit.get_owning_body("volume", volume_id) == component.cid:
                        return_list.append(CubitInstance(volume_id, "volume"))
            else:
                return_list.append(component)
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
    all_surfaces_that_exist = cubit.get_entities("surface")
    volumes_list = to_volumes(component_list)
    return_list = []
    for component in volumes_list:
        if component.geometry_type == "volume":
            for surface_id in all_surfaces_that_exist:
                if cubit.get_owning_volume("surface", surface_id) == component.cid:
                    return_list.append(CubitInstance(surface_id, "surface"))
        else:
            return_list.append(component)
    return return_list


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

# unionise is in Assemblies.py as it needs to know about the
# ComplexComponent and Assembly classes
