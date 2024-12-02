'''
components.py
author(s): Sid Mungale

Simple Components
These are components that contain a volume/s made of a single material

(c) Copyright UKAEA 2024
'''

from hypnos.generic_classes import CubismError, CubitInstance, cmd
from hypnos.cubit_functions import (
    to_volumes,
    to_bodies,
    subtract,
    )
from hypnos.geometry import (
    make_cylinder_along,
    Vertex,
    make_surface,
    hypotenuse,
    arctan,
    Line,
    blunt_corners,
    rotate,
    sweep_about,
    sweep_along,
    create_brick
    )
import numpy as np
from abc import ABC, abstractmethod


class ExternalComponent(CubitInstance):
    '''Track components imported externally'''
    def __init__(self, cid: int, geometry_type: str) -> None:
        super().__init__(cid, geometry_type)


class ComponentBase(ABC):
    '''Common base for Components and Assemblies'''
    def __init__(self, classname, params: dict):
        self._classname = classname
        self.identifier = classname
        self.geometry = params["geometry"] if "geometry" in params.keys() else None
        self.material = params["material"] if "material" in params.keys() else None
        self.origin = Vertex(0)
        if "origin" in params.keys():
            origin = params["origin"]
            if isinstance(origin, Vertex):
                self.origin = origin
            elif type(origin) is list:
                self.origin = Vertex(*origin)
        self.check_sanity()

    @property
    def classname(self):
        return self._classname

    @classname.setter
    def classname(self, new_classname):
        if type(new_classname) is str:
            return new_classname
        else:
            print("classname must be a string")

    @classname.deleter
    def classname(self):
        del self._classname

    @classmethod
    def from_classname(cls, classname, params):
        for toplvl in cls.__subclasses__():
            for construct_lvl in toplvl.__subclasses__():
                if construct_lvl.classname == classname:
                    return construct_lvl(params)

    def check_sanity(self):
        '''Check whether the parameters supplied to this instance are physical
        '''
        pass

    @abstractmethod
    def get_geometries(self) -> list[CubitInstance]:
        '''Get contained geometries

        Returns
        -------
        list[CubitInstance]
            list of geometries
        '''
        pass

    def move(self, vector: Vertex):
        if type(vector) is tuple:
            for geom in self.get_geometries():
                geom.move(vector)
        elif isinstance(vector, Vertex):
            for geom in self.get_geometries():
                geom.move((vector.x, vector.y, vector.z))

    def rotate(self, angle: float, origin: Vertex = Vertex(0, 0, 0), axis: Vertex = Vertex(0, 0, 1)):
        '''Rotate geometries about a given axis

        Parameters
        ----------
        angle : float
            Angle to rotate by IN DEGREES
        origin : Vertex
            Point to rotate about, by default 0, 0, 0
        axis : Vertex, optional
            axis to rotate about, by default z-axis
        '''
        if origin == "origin":
            origin = self.origin

        rotate(self.get_geometries(), angle, origin, axis)

    def set_mesh_size(self, size: int):
        for geom in self.get_geometries():
            cmd(f"{str(geom)} size {size}")


class SimpleComponent(ComponentBase):
    '''Base class for simple components.
    These are intended to be the smallest functional unit of a single material.
    They may comprise multiple volumes/ may not be 'simple' geometrically.
    '''
    def __init__(self, classname, json_object):
        super().__init__(classname, json_object)
        self.subcomponents = []
        self.add_to_subcomponents(self.make_geometry())
        if not self.origin == Vertex(0):
            self.move(self.origin)

    def get_geometries(self) -> list[CubitInstance]:
        return self.subcomponents

    @abstractmethod
    def make_geometry(self) -> list[CubitInstance]:
        '''Make this instance in cubit

        Returns
        -------
        list[CubitInstance]
            list of created geometries
        '''
        pass

    def add_to_subcomponents(self, subcomponents: list[CubitInstance]):
        '''Add geometries to self.subcomponents

        Parameters
        ----------
        subcomponents : CubitInstance | list[CubitInstance]
            geometry/ies to add
        '''
        if isinstance(subcomponents, CubitInstance):
            self.subcomponents.append(subcomponents)
        elif type(subcomponents) is list:
            for subcomponent in subcomponents:
                if isinstance(subcomponent, CubitInstance):
                    self.subcomponents.append(subcomponent)

    def as_bodies(self):
        '''Convert geometries to references to their owning bodies'''
        self.subcomponents = to_bodies(self.subcomponents)

    def as_volumes(self):
        '''Convert any references to bodies in the subcomponents
        to references to their composing volumes'''
        self.subcomponents = to_volumes(self.subcomponents)

    def extract_parameters(self, parameters) -> dict:
        '''Get values of geometrical parameters.

        Parameters
        ----------
        parameters : list | dict
            list - get corresponding values of parameters,
            i.e. returned dict will look like {key : value}
            dict - {search_key : output_key},
            i.e. returned dict will look like {output_key : value}

        Returns
        -------
        dict
            key-value pairs as described above
        '''
        out_dict = {}
        if type(parameters) is list:
            for parameter in parameters:
                out_dict[parameter] = self.geometry[parameter]
        elif type(parameters) is dict:
            for fetch_parameter, out_parameter in parameters.items():
                out_dict[out_parameter] = self.geometry[fetch_parameter]
        else:
            raise CubismError(f"parameters type not recognised: {type(parameters)}")
        return out_dict

    def volume_id_string(self):
        '''Space-separated string of volume IDs.

        Returns
        -------
        str
            volume ID string
        '''
        self.as_volumes()
        return " ".join([str(cmp.cid) for cmp in self.get_geometries() if cmp.geometry_type == "volume"])


class CladdingComponent(SimpleComponent):
    def __init__(self, json_object):
        super().__init__("cladding", json_object)

    def check_sanity(self):
        geom = self.geometry
        offset_slope = hypotenuse(geom["offset"], geom["outer cladding"] + geom["breeder chamber thickness"] + geom["inner cladding"])
        if "bluntness" in self.geometry.keys():
            if geom["bluntness"] >= offset_slope/2:
                raise ValueError("cladding bluntness larger than offset surface")
            elif geom["bluntness"] >= geom["outer length"]:
                raise ValueError("cladding bluntness larger than outer length")
            elif geom["bluntness"] >= geom["inner length"]:
                raise ValueError("cladding bluntness larger than inner length")
        else:
            if geom["inner bluntness"] + geom["outer bluntness"] >= offset_slope:
                raise ValueError("cladding bluntness larger than offset surface")
            elif geom["inner bluntness"] >= geom["inner length"]:
                raise ValueError("cladding inner bluntness larger than inner length")
            elif geom["outer bluntness"] >= geom["outer length"]:
                raise ValueError("cladding outer bluntness larger than outer length")

    def make_geometry(self):
        # get params
        geometry = self.geometry
        outer_length = geometry["outer length"]
        inner_length = geometry["inner length"]
        offset = geometry["offset"]
        if "bluntness" in geometry.keys():
            inner_bluntness = geometry["bluntness"]
            outer_bluntness = geometry["bluntness"]
        else:
            inner_bluntness = geometry["inner bluntness"]
            outer_bluntness = geometry["outer bluntness"]
        coolant_inlet_radius = geometry["coolant inlet radius"]
        inner_cladding = geometry["inner cladding"]
        breeder_chamber_thickness = geometry["breeder chamber thickness"]
        outer_cladding = geometry["outer cladding"]
        purge_duct_thickness = geometry["purge duct thickness"]
        purge_duct_cladding = geometry["purge duct cladding"]
        purge_duct_offset = geometry["purge duct offset"]
        distance_to_step = geometry["distance to step"]
        distance_to_disk = geometry["distance to disk"]
        # helpful calculations
        step_thickness = purge_duct_thickness + purge_duct_cladding
        inner_less_purge_thickness = inner_cladding - step_thickness
        net_thickness = inner_cladding + breeder_chamber_thickness + outer_cladding
        slope_angle = arctan(net_thickness, offset)

        cladding_vertices = list(np.zeros(10))
        # set up points of face-to-sweep
        cladding_vertices[0] = Vertex(0, inner_less_purge_thickness)
        cladding_vertices[1] = Vertex(0)

        cladding_vertices[2] = Vertex(-inner_length)
        cladding_vertices[3] = cladding_vertices[2] + Vertex(offset, net_thickness)
        cladding_vertices[4] = cladding_vertices[3] + Vertex(outer_length)
        cladding_vertices[5] = cladding_vertices[3] + Vertex(outer_length, -outer_cladding)

        cladding_vertices[6] = cladding_vertices[3] + Vertex(outer_cladding * np.tan(slope_angle/2), -outer_cladding)
        cladding_vertices[7] = cladding_vertices[2] + Vertex(inner_cladding/np.tan(slope_angle) + outer_cladding/np.sin(slope_angle), inner_cladding)

        cladding_vertices[9] = cladding_vertices[0] + Vertex(-distance_to_step)
        cladding_vertices[8] = cladding_vertices[9] + Vertex(0, step_thickness)

        cladding_vertices, tangent_idx = blunt_corners(
            cladding_vertices,
            [2, 7, 3, 6],
            [inner_bluntness, inner_bluntness, outer_bluntness, outer_bluntness]
            )

        surface_to_sweep = make_surface(cladding_vertices, tangent_idx)
        cladding = sweep_about(
            surface_to_sweep,
            point=Vertex(0, -coolant_inlet_radius)
        )

        duct_vertices = list(np.zeros(4))
        duct_vertices[0] = cladding_vertices[0] + Vertex(-purge_duct_offset, purge_duct_thickness)
        duct_vertices[1] = cladding_vertices[0] + Vertex(-distance_to_disk, purge_duct_thickness)
        duct_vertices[2] = duct_vertices[1] + Vertex(0, purge_duct_cladding)
        duct_vertices[3] = duct_vertices[0] + Vertex(0, purge_duct_cladding)

        duct_surface = make_surface(duct_vertices, [])
        duct = sweep_about(
            duct_surface,
            point=Vertex(0, -coolant_inlet_radius)
        )

        # realign with origin
        cladding.move((inner_length, coolant_inlet_radius, 0))
        duct.move((inner_length, coolant_inlet_radius, 0))
        return [cladding, duct]


class PinCoolant(SimpleComponent):
    def __init__(self, json_object: dict):
        super().__init__("coolant", json_object)

    def make_geometry(self):
        geometry = self.geometry
        inner_length = geometry["inner length"]
        if "bluntness" in geometry.keys():
            inner_bluntness = geometry["bluntness"]
            outer_bluntness = geometry["bluntness"]
        else:
            inner_bluntness = geometry["inner bluntness"]
            outer_bluntness = geometry["outer bluntness"]
        offset = geometry["offset"]
        pressure_tube_length = geometry["pressure tube length"]
        pressure_tube_radius = geometry["pressure tube radius"]
        pressure_tube_gap = geometry["pressure tube gap"]
        cladding_thickness = geometry["cladding thickness"]
        inlet_radius = geometry["coolant inlet radius"]

        coolant_vertices = list(np.zeros(8))

        coolant_vertices[0] = Vertex(0)
        coolant_vertices[1] = Vertex(0, inlet_radius)

        coolant_vertices[2] = Vertex(-inner_length, inlet_radius)
        coolant_vertices[3] = coolant_vertices[2] + Vertex(offset, cladding_thickness)
        coolant_vertices[4] = coolant_vertices[3] + Vertex(pressure_tube_length-(offset+pressure_tube_gap))

        coolant_vertices[7] = coolant_vertices[0] + Vertex(-(inner_length+pressure_tube_gap))
        coolant_vertices[6] = coolant_vertices[7] + Vertex(0, pressure_tube_radius)
        coolant_vertices[5] = coolant_vertices[6] + Vertex(pressure_tube_length)

        coolant_vertices, tangent_idx = blunt_corners(
            coolant_vertices,
            [2, 3],
            [inner_bluntness, outer_bluntness]
        )

        surface_to_sweep = make_surface(coolant_vertices, tangent_idx)
        coolant = sweep_about(surface_to_sweep)

        # realign with origin
        coolant.move((inner_length+pressure_tube_gap, 0, 0))
        return coolant


class PressureTubeComponent(SimpleComponent):
    def __init__(self, json_object):
        super().__init__("pressure_tube", json_object)

    def make_geometry(self):
        length = self.geometry["length"]
        outer_radius = self.geometry["outer radius"]
        thickness = self.geometry["thickness"]

        subtract_vol = make_cylinder_along(outer_radius-thickness, length-thickness)
        subtract_vol.move((0, 0, -thickness/2))
        cylinder = make_cylinder_along(outer_radius, length)

        tube = subtract([cylinder], [subtract_vol])[0]
        rotate(tube, -90, axis=Vertex(0, 1))
        tube.move((length/2, 0, 0))

        return tube


class FilterLidComponent(SimpleComponent):
    def __init__(self, json_object):
        super().__init__("filter_lid", json_object)

    def make_geometry(self):
        length = self.geometry["length"]
        outer_radius = self.geometry["outer radius"]
        thickness = self.geometry["thickness"]

        tube_vertices = list(np.zeros(4))
        tube_vertices[0] = Vertex(0, outer_radius)
        tube_vertices[1] = tube_vertices[0] + Vertex(length)
        tube_vertices[2] = tube_vertices[1] + Vertex(0, -thickness)
        tube_vertices[3] = tube_vertices[0] + Vertex(0, -thickness)

        tube_surface = make_surface(tube_vertices, [])
        tube = sweep_about(tube_surface)

        return tube


class PurgeGasComponent(SimpleComponent):
    def __init__(self, json_object):
        super().__init__("purge_gas", json_object)

    def make_geometry(self):
        length = self.geometry["length"]
        outer_radius = self.geometry["outer radius"]
        thickness = self.geometry["thickness"]

        tube_vertices = list(np.zeros(4))
        tube_vertices[0] = Vertex(0, outer_radius)
        tube_vertices[1] = tube_vertices[0] + Vertex(length)
        tube_vertices[2] = tube_vertices[1] + Vertex(0, -thickness)
        tube_vertices[3] = tube_vertices[0] + Vertex(0, -thickness)

        tube_surface = make_surface(tube_vertices, [])
        tube = sweep_about(tube_surface)

        return tube


class FilterDiskComponent(SimpleComponent):
    def __init__(self, json_object):
        super().__init__("filter_disk", json_object)

    def make_geometry(self):
        length = self.geometry["length"]
        outer_radius = self.geometry["outer radius"]
        thickness = self.geometry["thickness"]

        subtract_vol = make_cylinder_along(outer_radius-thickness, length)
        cylinder = make_cylinder_along(outer_radius, length)

        tube = subtract([cylinder], [subtract_vol])[0]
        rotate(tube, -90, axis=Vertex(0, 1))
        tube.move((length/2, 0, 0))

        return tube


class MultiplierComponent(SimpleComponent):
    def __init__(self, json_object):
        super().__init__("multiplier", json_object)

    def check_sanity(self):
        if self.geometry["side"] <= np.sqrt(4/3) * self.geometry["inner radius"]:
            raise ValueError("Multiplier side length not big enough to make multiplier around pressure tube")

    def make_geometry(self):
        inner_radius = self.geometry["inner radius"]
        length = self.geometry["length"]
        side_length = self.geometry["side"]

        subtract_vol = make_cylinder_along(inner_radius, length, "z")
        subtract_vol.move((0, 0, length/2))

        # hexagonal face
        face_vertex_positions = [Vertex(side_length).rotate(i*np.pi/3) for i in range(6)]
        face = make_surface(face_vertex_positions, [])
        hex_prism = sweep_along(face, Vertex(0, 0, length))

        multiplier = subtract([hex_prism], [subtract_vol])[0]
        rotate(multiplier, 90, axis=Vertex(0, 1))

        return multiplier


class PinBreeder(SimpleComponent):
    def __init__(self, json_object):
        super().__init__("breeder", json_object)

    def make_geometry(self):
        geometry = self.geometry
        inner_radius = geometry["inner radius"]
        outer_radius = geometry["outer radius"]
        if "bluntness" in geometry.keys():
            inner_bluntness = geometry["bluntness"]
            outer_bluntness = geometry["bluntness"]
        else:
            inner_bluntness = geometry["inner bluntness"]
            outer_bluntness = geometry["outer bluntness"]
        length = self.geometry["length"]
        offset = self.geometry["offset"]

        thickness = outer_radius - inner_radius

        breeder_vertices = list(np.zeros(4))
        breeder_vertices[0] = Vertex(length)
        breeder_vertices[1] = Vertex(0)
        breeder_vertices[2] = Vertex(offset, thickness)
        breeder_vertices[3] = Vertex(length, thickness)

        breeder_vertices, tangent_idx = blunt_corners(
            breeder_vertices,
            [1, 2],
            [inner_bluntness, outer_bluntness]
        )

        breeder_face = make_surface(breeder_vertices, tangent_idx)
        breeder = sweep_about(breeder_face, point=Vertex(0, -inner_radius))
        breeder.move((0, inner_radius, 0))

        return breeder


class FirstWallComponent(SimpleComponent):
    def __init__(self, json_object):
        super().__init__("first_wall", json_object)

    def check_sanity(self):
        if self.geometry["bluntness"] >= self.geometry["inner width"]/2:
            raise ValueError("Bluntness too large")
        offset = (self.geometry["outer width"]-self.geometry["inner width"])/2
        if self.geometry["bluntness"] >= hypotenuse(offset, self.geometry["length"]):
            raise ValueError("Bluntness larger than side wall")

    def make_geometry(self):
        geometry = self.geometry
        inner_width = geometry["inner width"]
        outer_width = geometry["outer width"]
        bluntness = geometry["bluntness"] if "bluntness" in geometry.keys() else 0
        length = geometry["length"]
        thickness = geometry["thickness"]
        sidewall_thickness = geometry["sidewall thickness"]
        height = geometry["height"]

        channel_spacing = geometry["channel spacing"]
        channel_width = geometry["channel width"]

        offset = (outer_width - inner_width)/2
        slope_angle = arctan(length, offset)
        sidewall_horizontal = sidewall_thickness/np.sin(slope_angle)

        # need less vertices when bluntness = 0 so treat as a special case
        vertices = list(np.zeros(8))
        vertices[0] = Vertex(0, 0)

        vertices[1] = Vertex(offset, length)
        vertices[2] = vertices[1] + Vertex(inner_width)

        vertices[3] = vertices[0] + Vertex(outer_width)
        vertices[4] = vertices[3] + Vertex(-sidewall_horizontal)

        vertices[5] = vertices[2] + Vertex(-sidewall_horizontal) + Vertex(thickness/np.tan(slope_angle), -thickness, 0)
        vertices[6] = vertices[1] + Vertex(sidewall_horizontal) + Vertex(-thickness/np.tan(slope_angle), -thickness, 0)
        vertices[7] = vertices[0] + Vertex(sidewall_horizontal)

        channel_ref = self.make_channel_volume(vertices)

        vertices, tangent_idx = blunt_corners(
            vertices,
            [1, 2, 5, 6],
            [bluntness for i in range(4)]
        )

        face_to_sweep = make_surface(vertices, tangent_idx)

        # line up sweep direction along y axis
        face_to_sweep.move((-outer_width/2, 0, 0))
        rotate(face_to_sweep, 90, axis=Vertex(1))
        first_wall = sweep_along(face_to_sweep, Vertex(0, height))

        no_of_channels = (height - channel_spacing) // (channel_spacing + channel_width)
        for i in range(no_of_channels):
            channel = channel_ref.copy()
            if i % 2 == 0:
                cmd(f"{channel} reflect 1 0 0")
            channel.move([0, i*(channel_spacing + channel_width) + channel_spacing, 0])
            first_wall = subtract([first_wall], [channel])[0]
        channel_ref.destroy_cubit_instance()
        return first_wall

    def make_channel_volume(self, fw_verts):
        # vertices should be the pre-blunted first wall vertices (length 8)
        geometry = self.geometry
        # get first wall params
        fw_inner_width = geometry["inner width"]
        fw_outer_width = geometry["outer width"]
        fw_length = geometry["length"]
        offset = (fw_outer_width - fw_inner_width)/2
        bluntness = geometry["bluntness"] if "bluntness" in geometry.keys() else 0
        # get channel params
        width = geometry["channel width"]
        back_manifold_offset = geometry["channel back manifold offset"]
        back_manifold_width = geometry["channel back manifold width"]
        front_manifold_offset = geometry["channel front manifold offset"]
        front_manifold_width = geometry["channel front manifold width"]
        depth = geometry["channel depth"]
        padding = geometry["channel padding"]
        # useful unit vectors
        out_right = Vertex(fw_length, offset).unit()
        out_left = Vertex(-fw_length, offset).unit()
        slope_right = Vertex(-offset, fw_length).unit()
        slope_left = Vertex(offset, fw_length).unit()
        # reference positions
        channel_top = fw_verts[1].y - depth
        # construct channel vertices
        verts = [Vertex(0) for i in range(12)]
        verts[0] = Line(slope_left, fw_verts[7]).vertex_at(y=back_manifold_offset) + (padding * slope_left)
        verts[2] = Line(slope_left, fw_verts[1]-out_left*depth).vertex_at(y=channel_top)
        verts[1] = Line(slope_left, verts[2]).vertex_at(y=verts[0].y)
        verts[3] = Line(slope_right, fw_verts[2]-out_right*depth).vertex_at(y=channel_top)
        verts[5] = Line(slope_right, fw_verts[4]).vertex_at(y=front_manifold_offset) + (padding * slope_right)
        verts[4] = Line(slope_right, verts[3]).vertex_at(y=verts[5].y)
        verts[6] = verts[5] + slope_right * (front_manifold_width - 2*padding)
        verts[8] = Line(slope_right, verts[3]-out_right*width).vertex_at(y=channel_top-width)
        verts[7] = Line(slope_right, verts[8]).vertex_at(y=verts[6].y)
        verts[9] = Line(slope_left, verts[2]-out_left*width).vertex_at(y=channel_top-width)
        verts[11] = verts[0] + slope_left * (back_manifold_width - 2*padding)
        verts[10] = Line(slope_left, verts[9]).vertex_at(y=verts[11].y)

        verts, tangent_idx = blunt_corners(
            verts,
            [2, 3, 8, 9],
            [bluntness for i in range(4)]
        )

        # make into surface and sweep to make volume
        channel_face = make_surface(verts, tangent_idx)
        channel_face.move((-fw_outer_width/2, 0, 0))
        rotate(channel_face, 90, axis=Vertex(1))
        channel = sweep_along(channel_face, Vertex(0, width))

        return channel


class Plate(SimpleComponent):
    def __init__(self, classname, json_object: dict, plate_type, pin_positions=[[]]):
        self.plate_type = plate_type
        self.pin_pos = pin_positions
        super().__init__(classname, json_object)

    def __get_back_vertices(self):
        if self.plate_type != "mid":
            extension = self.geometry["extension"]
        front_length = self.geometry["length"]
        right_position = front_length/2 + extension if self.plate_type in ["right", "full"] else front_length/2
        left_position = -(front_length/2 + extension) if self.plate_type in ["left", "full"] else -front_length/2
        return left_position, right_position

    def make_geometry(self):
        thickness = self.geometry["thickness"]
        front_length = self.geometry["length"]
        height = self.geometry["height"]
        back_left_position, back_right_position = self.__get_back_vertices()

        plate_vertices = [Vertex(0) for i in range(4)]
        plate_vertices[0] = Vertex(-front_length/2, 0, thickness)
        plate_vertices[1] = Vertex(front_length/2, 0, thickness)
        plate_vertices[2] = Vertex(back_right_position)
        plate_vertices[3] = Vertex(back_left_position)

        face_to_sweep = make_surface(plate_vertices, [])
        plate = sweep_along(face_to_sweep, Vertex(0, height))
        plate.move((self.origin.x, 0, 0))
        plate = self.__make_holes(plate)
        plate.move((-self.origin.x, 0, 0))

        return to_volumes([plate])

    def __make_holes(self, plate: CubitInstance):
        plate_thickness = self.geometry["thickness"]
        hole_radius = self.geometry["hole radius"]

        for row in self.pin_pos:
            for position in row:
                hole_position = (position.x, position.y, 0)
                hole_to_be = make_cylinder_along(hole_radius, plate_thickness*3)
                hole_to_be.move(hole_position)
                plate = subtract([plate], [hole_to_be])[0]
        return plate


class BZBackplate(Plate):
    def __init__(self, json_object: dict, pin_positions):
        super().__init__("BZ_backplate", json_object, "full", pin_positions)


class PurgeGasPlate(SimpleComponent):
    def __init__(self, classname, json_object: dict, rib_positions: list[Vertex], rib_thickness: int, plate_hole_positions: list):
        self.hole_pos = plate_hole_positions
        self.rib_pos = [i.x for i in rib_positions]
        self.rib_pos.sort()
        self.rib_thickness = rib_thickness
        super().__init__(classname, json_object)

    def make_geometry(self):
        plates = []

        left_plate_json = self.__make_side_plate_json(0)
        plates.extend(Plate(self.classname+"_left", left_plate_json, "left", self.hole_pos[0]).get_geometries())

        for i in range(len(self.rib_pos)-1):
            mid_plate_json = self.__make_mid_plate_json(i)
            plates.extend(Plate(self.classname+"_mid", mid_plate_json, "mid", self.hole_pos[i+1]).get_geometries())

        right_plate_json = self.__make_side_plate_json(-1)
        plates.extend(Plate(self.classname+"_right", right_plate_json, "right", self.hole_pos[-1]).get_geometries())

        return plates

    def __make_side_plate_json(self, rib_index):
        total_length = self.geometry["length"]
        geometry = self.extract_parameters(["thickness", "height", "extension", "hole radius"])
        geometry["length"] = (total_length/2 - np.abs(self.rib_pos[rib_index])) - self.rib_thickness/2
        origin = Vertex((geometry["length"] - total_length)/2) if rib_index == 0 else Vertex((-geometry["length"] + total_length)/2)
        return {"geometry": geometry, "material": self.material, "origin": origin}

    def __make_mid_plate_json(self, left_rib_index):
        geometry = self.extract_parameters(["thickness", "height", "extension", "hole radius"])
        geometry["length"] = np.abs(self.rib_pos[left_rib_index] - self.rib_pos[left_rib_index+1]) - self.rib_thickness
        origin = Vertex((self.rib_pos[left_rib_index] + self.rib_pos[left_rib_index+1])/2)
        return {"geometry": geometry, "material": self.material, "origin": origin}


class Rib(SimpleComponent):
    def __init__(self, classname, json_object: dict):
        super().__init__(classname, json_object)

    def check_sanity(self):
        if self.geometry["side channel width"] >= self.geometry["length"]:
            raise ValueError("Rib side channel wider than rib")
        elif self.geometry["side channel height"] >= self.geometry["height"]:
            raise ValueError("Rib side channel height taller than rib")
        elif self.geometry["side channel height"] + self.geometry["side channel gap"] + 2*self.geometry["side channel vertical margin"] > self.geometry["height"]:
            raise ValueError("Gap between side channels/ vertical margin too big")
        elif self.geometry["side channel vertical margin"]*2 + self.geometry["side channel height"] > self.geometry["height"]:
            raise ValueError("side channel vertical margins too big")
        elif 2*self.geometry["connection height"] > self.geometry["side channel vertical margin"]:
            raise ValueError("connection height larger than vertical margin")
        elif self.geometry["connection height"] > self.geometry["side channel gap"]:
            raise ValueError("Rib connections overlapping, connection height too large")

    def make_geometry(self):
        height = self.geometry["height"]
        length = self.geometry["length"]
        thickness = self.geometry["thickness"]

        structure = create_brick(thickness, height, length)
        structure.move((0, height/2, -length/2))

        structure, number_of_channels = self.__make_side_channels(structure)
        rib = self.make_rib_connections(structure, number_of_channels)

        return to_volumes([rib])

    def __make_side_channels(self, structure: CubitInstance):

        structure_height = self.geometry["height"]
        length = self.geometry["thickness"]
        width = self.geometry["side channel width"]
        height = self.geometry["side channel height"]
        gap = self.geometry["side channel gap"]
        z_offset = self.geometry["side channel horizontal offset"]
        y_margin = self.geometry["side channel vertical margin"]

        accessible_height = structure_height - 2*y_margin
        spacing = gap + height
        number_of_channels = (accessible_height // spacing) + 1
        y_margin += (accessible_height - (number_of_channels-1)*spacing)/2

        channel_dims = Vertex(length, height, width)
        structure = self.tile_channels_vertically(structure, channel_dims, number_of_channels, y_margin, z_offset, spacing)

        return structure, number_of_channels

    def make_rib_connections(self, structure: CubitInstance, number_of_channels: int):
        height = self.geometry["connection height"]
        length = self.geometry["length"] - self.geometry["side channel horizontal offset"]
        connection_dims = Vertex(self.geometry["connection width"], height, length)

        z_offset = self.geometry["side channel horizontal offset"] + self.geometry["side channel width"]
        spacing = self.geometry["side channel gap"] + self.geometry["side channel height"]
        y_margin = (self.geometry["height"] + self.geometry["side channel height"] - (height + (number_of_channels-1)*spacing))/2

        structure = self.tile_channels_vertically(structure, connection_dims, number_of_channels, y_margin, z_offset, spacing)

        return structure

    def tile_channels_vertically(self, structure: CubitInstance, channel_dims: Vertex, number_of_channels: int, y_margin: int, z_offset: int, spacing: int):
        for i in range(number_of_channels):
            hole_to_be = create_brick(channel_dims.x, channel_dims.y, channel_dims.z)
            hole_to_be.move((0, channel_dims.y/2, -channel_dims.z/2))
            hole_to_be.move((0, y_margin+i*spacing, -z_offset))
            structure = subtract([structure], [hole_to_be])[0]

        return structure


class FrontRib(Rib):
    def __init__(self, json_object: dict):
        super().__init__("front_rib", json_object)


class BackRib(Rib):
    def __init__(self, json_object: dict):
        super().__init__("back_rib", json_object)

    def make_rib_connections(self, structure: CubitInstance, number_of_channels: int):
        height = self.geometry["connection height"]
        # runs from connection point with front rib to the side channel
        length = self.geometry["side channel horizontal offset"]
        connection_dims = Vertex(self.geometry["connection width"], height, length)

        # this is 0 to connect to the front ribs
        z_offset = 0
        spacing = self.geometry["side channel gap"] + self.geometry["side channel height"]
        y_margin = (self.geometry["height"] + self.geometry["side channel height"] - (height + (number_of_channels-1)*spacing))/2

        structure = self.tile_channels_vertically(structure, connection_dims, number_of_channels, y_margin, z_offset, spacing)

        return structure


class CoolantOutletPlenum(SimpleComponent):
    def __init__(self, json_object: dict, rib_positions: list[Vertex], rib_thickness):
        self.rib_pos = [i.x for i in rib_positions]
        self.rib_pos.sort()
        self.rib_thickness = rib_thickness
        super().__init__("coolant_outlet_plenum", json_object)

    def check_sanity(self):
        if self.geometry["length"] <= 2*self.geometry["thickness"]:
            raise ValueError("Coolant outlet plenum 'thickness' calculated inward from width, width too small")

    def make_geometry(self):
        height = self.geometry["height"]
        length = self.geometry["length"]
        thickness = self.geometry["thickness"]
        width = self.geometry["width"]
        plenum = []

        plenum.append(self.__make_side_plenum(self.rib_pos[0] - self.rib_thickness/2,-width/2, length, height, thickness))
        plenum.append(self.__make_side_plenum(self.rib_pos[-1] + self.rib_thickness/2, width/2, length, height, thickness))

        for i in range(len(self.rib_pos)-1):
            plenum.extend(self.__make_mid_plates(self.rib_pos[i] + self.rib_thickness/2, self.rib_pos[i+1] - self.rib_thickness/2, length, height, thickness))
        return plenum

    def __make_mid_plates(self, start_x, end_x, length, height, thickness):
        front_plate = list(np.zeros(4))
        front_plate[0] = Vertex(start_x)
        front_plate[1] = Vertex(end_x)
        front_plate[2] = front_plate[1] + Vertex(0, 0, -thickness)
        front_plate[3] = front_plate[0] + Vertex(0, 0, -thickness)

        face_to_sweep = make_surface(front_plate, [])
        front_plate = sweep_along(face_to_sweep, Vertex(0, height))

        back_plate = list(np.zeros(4))
        back_plate[0] = Vertex(start_x, 0, -length)
        back_plate[1] = Vertex(end_x, 0, -length)
        back_plate[2] = back_plate[1] + Vertex(0, 0, thickness)
        back_plate[3] = back_plate[0] + Vertex(0, 0, thickness)

        face_to_sweep = make_surface(back_plate, [])
        back_plate = sweep_along(face_to_sweep, Vertex(0, height))

        return [front_plate, back_plate]

    def __make_side_plenum(self, start_x, end_x, length, height, thickness):
        side = list(np.zeros(8))
        side[0] = Vertex(start_x)
        side[1] = Vertex(end_x)
        side[2] = Vertex(end_x, 0, -length)
        side[3] = Vertex(start_x, 0, -length)

        side[4] = side[3] + Vertex(0, 0, thickness)
        side[5] = side[2] + Vertex(0, 0, thickness)
        side[6] = side[1] + Vertex(0, 0, -thickness)
        side[7] = side[0] + Vertex(0, 0, -thickness)
        face_to_sweep = make_surface(side, [1, 5])
        plenum = sweep_along(face_to_sweep, Vertex(0, height))

        return plenum


class SeparatorPlate(PurgeGasPlate):
    def __init__(self, json_object: dict, rib_positions: list[Vertex], rib_thickness: int):
        super().__init__(
            "separator_plate", json_object, rib_positions, rib_thickness, [[[]] for i in rib_positions]
            )


class FWBackplate(Plate):
    def __init__(self, json_object: dict):
        super().__init__("FW_backplate", json_object, "full")
