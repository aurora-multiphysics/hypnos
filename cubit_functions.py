from generic_classes import *

def cubit_cmd_check(cmd: str, id_type: str):
    '''Perform cubit command and check whether a new entity has been created

    :param cmd: command to run
    :type cmd: str
    :param id_type: type of entity to check for
    :type id_type: str
    :return: id of new entity/ false
    :rtype: int/ bool
    '''
    pre_id = cubit.get_last_id(id_type)
    cubit.cmd(cmd)
    post_id = cubit.get_last_id(id_type)
    if pre_id == post_id:
        # material tracking function depends on this btw
        return False
    else:
        return GenericCubitInstance(post_id, id_type)

# functions to delete and copy lists of GenericCubitInstances
def delete_instances(component_list: list):
    '''Deletes cubit instances of all GenericCubitInstance objects in list'''
    for component in component_list:
        if isinstance(component, GenericCubitInstance):
            component.destroy_cubit_instance()

def copy_instances(component_list: list):
    '''Returns a list of copied GenericCubitInstances'''
    copied_list = []
    for component in component_list:
        if isinstance(component, GenericCubitInstance):
            copied_list.append(component.copy_cubit_instance())
        else:
            raise CubismError("All components are not instances :(")

# THIS IS VERY SILLY WHY DO I HAVE TO DO THIS

def to_owning_body(component: GenericCubitInstance):
    '''
    accepts GenericCubitInstance and returns GenericCubitInstance of owning body
    '''
    if isinstance(component, GenericCubitInstance):
        if component.cid == "body":
            return component
        else:
            return GenericCubitInstance(cubit.get_owning_body(component.geometry_type, component.cid), "body")
    raise CubismError("Did not recieve a GenericCubicInstance")

def get_bodies_and_volumes_from_group(group_id: int):
    '''Find bodies and volumes at the top-level of a group.

    :param group_id: ID of group
    :type group_id: int
    :return: list of bodies and volumes as GenericCubitInstances
    :rtype: list
    '''
    instance_list = []
    body_ids= cubit.get_group_bodies(group_id)
    for body_id in body_ids:
        instance_list.append(GenericCubitInstance(body_id, "body"))
    volume_ids= cubit.get_group_volumes(group_id)
    for volume_id in volume_ids:
        instance_list.append(GenericCubitInstance(volume_id, "volume"))
    return instance_list

def remove_overlaps_between_generic_cubit_instance_lists(from_list: list, tool_list: list):
    '''Remove overlaps between cubit instances of two lists of components'''
    from_volumes = from_bodies_to_volumes(from_list)
    tool_volumes = from_bodies_to_volumes(tool_list)
    # check each pair
    for from_volume in from_volumes:
        for tool_volume in tool_volumes:
            # if there is an overlap, remove it
            if isinstance(from_volume, GenericCubitInstance) & isinstance(tool_volume, GenericCubitInstance):
                if not (cubit.get_overlapping_volumes([from_volume.cid, tool_volume.cid]) == ()):
                    # i have given up on my python api dreams. we all return to cubit ccl in the end.
                    cubit.cmd(f"remove overlap volume {tool_volume.cid} {from_volume.cid} modify volume {from_volume.cid}")

def from_bodies_to_volumes(component_list: list):
    '''
    Turns references to bodies into references to their children volumes.
    Accepts list of GenericCubitInstances.
    Returns list of GenericCubitInstances.
    '''
    all_volumes_that_exist= cubit.get_entities("volume")
    return_list= []
    for component in component_list:
        if isinstance(component, GenericCubitInstance):
            if component.geometry_type == "body":
                for volume_id in all_volumes_that_exist:
                    if cubit.get_owning_body("volume", volume_id) == component.cid:
                        return_list.append(GenericCubitInstance(volume_id, "volume"))
            else:
                return_list.append(component)
        else:
            return_list.append(component)
    return return_list

def from_bodies_and_volumes_to_surfaces(component_list: list):
    '''
    Turns references to bodies and volumes into references to their children surfaces.
    Accepts list of GenericCubitInstances.
    Returns list of GenericCubitInstances.
    '''
    all_surfaces_that_exist = cubit.get_entities("surface")
    volumes_list= from_bodies_to_volumes(component_list)
    return_list = []
    for component in volumes_list:
        if isinstance(component, GenericCubitInstance):
            if component.geometry_type == "volume":
                for surface_id in all_surfaces_that_exist:
                    if cubit.get_owning_volume("surface", surface_id) == component.cid:
                        return_list.append(GenericCubitInstance(surface_id, "surface"))
            else:
                return_list.append(component)
        else:
            return_list.append(component)
    return return_list

def from_everything_to_bodies(component_list: list):
    bodies_list = []
    for component in component_list:
        if isinstance(component, GenericCubitInstance):
            if component.geometry_type == "body":
                if component.cid not in [i.cid for i in bodies_list]:
                    bodies_list.append(component)
            else:
                owning_body_id = cubit.get_owning_body(component.geometry_type, component.cid)
                if owning_body_id not in [i.cid for i in bodies_list]:
                    bodies_list.append(GenericCubitInstance(owning_body_id, "body"))
    return bodies_list

# unionise is in Assemblies.py as it needs to know about the ComplexComponent and Assembly classes