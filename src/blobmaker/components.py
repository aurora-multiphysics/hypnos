from blobmaker.constants import BLOB_CLASSES
from blobmaker.generic_classes import CubismError, CubitInstance, cmd, cubit
from blobmaker.cubit_functions import to_volumes, to_bodies, get_last_geometry, subtract, cmd_geom
from blobmaker.geometry import make_cylinder_along, make_prism_along, Vertex, make_surface, hypotenuse, arctan, Line
import numpy as np


class ExternalComponent(CubitInstance):
    '''Track components imported externally'''
    def __init__(self, cid: int, geometry_type: str) -> None:
        super().__init__(cid, geometry_type)


class SimpleComponent:
    '''Base class for simple components. 
    These are intended to be the smallest functional unit of a single material.
    They may comprise of multiple volumes/ may not be 'simple' geometrically
    '''
    def __init__(self, classname, json_object: dict):
        self.subcomponents = []
        self.classname = classname
        self.identifier = classname
        self.geometry, self.material, self.origin = self.__get_top_level_info(json_object)
        self.check_sanity()

        self.add_to_subcomponents(self.make_geometry())
        if not self.origin == Vertex(0):
            self.move(self.origin)

    def __get_top_level_info(self, json_object: dict):
        '''Get top-level information and ensure proper types

        :param json_object: Input json-formatted info
        :type json_object: dict
        :return: Geometry, material, and origin
        :rtype: dict, str, Vertex
        '''
        if "geometry" not in json_object.keys():
            raise CubismError(f"Component {self.classname} requires geometry")
        elif type(json_object["geometry"]) is not dict:
            raise TypeError("Geometry info should be represented as a dictionary")
        elif "material" not in json_object.keys():
            raise CubismError(f"Component {self.classname} requires a material")
        elif type(json_object["material"]) is not str:
            raise TypeError("Material should be given as a string")
        origin = json_object["origin"] if "origin" in json_object.keys() else Vertex(0)
        if type(origin) is list:
            origin = Vertex(origin[0], origin[1], origin[2])
        elif type(origin) is not Vertex:
            raise TypeError("Origin should be represented using a Vertex")
        return json_object["geometry"], json_object["material"], origin

    def add_to_subcomponents(self, subcomponents: CubitInstance | list[CubitInstance]):
        '''Add geometry/ies to subcomponents attribute

        :param subcomponents: Geometry or geometries
        :type subcomponents: CubitInstance | list[CubitInstance]
        '''
        if isinstance(subcomponents, CubitInstance):
            self.subcomponents.append(subcomponents)
        elif type(subcomponents) is list:
            for subcomponent in subcomponents:
                if isinstance(subcomponent, CubitInstance):
                    self.subcomponents.append(subcomponent)

    def make_geometry(self):
        '''create geometry in cubit. if the class is a blob, make it.'''
        if self.classname in BLOB_CLASSES:
            return self.__create_cubit_blob(self.geometry)
        else:
            raise CubismError("Wrong class name somewhere?: " + self.classname)

    def convert_to_3d_vector(self, dim):
        if type(dim) is int:
            return_vector = [dim for i in range(3)]
        elif len(dim) == 1:
            return_vector = [dim[0] for i in range(3)]
        elif len(dim) == 3:
            return_vector = dim
        else:
            raise CubismError("thickness should be either a 1D or 3D vector (or scalar)")
        return return_vector

    def __create_cubit_blob(self, geometry: dict):
        '''create cube (if scalar/1D) or cuboid (if 3D) with dimensions.
        Rotate it about the y-axis, x-axis, y-axis if euler_angles are specified.
        Move it to position if specified'''
        # setup variables
        dims = self.convert_to_3d_vector(geometry["dimensions"])
        pos = geometry["position"] if "position" in geometry.keys() else [0, 0, 0]
        euler_angles = geometry["euler_angles"] if "euler_angles" in geometry.keys() else [0, 0, 0]
        # create a cube or cuboid.
        blob = cubit.brick(dims[0], dims[1], dims[2])
        cid = cubit.get_last_id("volume")
        # orientate according to euler angles
        axis_list = ['y', 'x', 'y']
        for i in range(3):  # hard-coding in 3D?
            if not euler_angles[i] == 0:
                cmd(f'rotate volume {cid} angle {euler_angles[i]} about {axis_list[i]}')
        # move to specified position
        cubit.move(blob, pos)
        # return instance for further manipulation
        return CubitInstance(cid, "volume")

    def as_bodies(self):
        '''Convert subcomponent references to references to their owning bodies'''
        self.subcomponents = to_bodies(self.subcomponents)

    def as_volumes(self):
        '''Convert any references to bodies in the subcomponents
        to references to their composing volumes'''
        self.subcomponents = to_volumes(self.subcomponents)

    def get_subcomponents(self) -> list[CubitInstance]:
        return self.subcomponents

    def get_parameters(self, parameters: list):
        return [self.geometry[parameter] for parameter in parameters]

    def move(self, vector: Vertex):
        for subcomponent in self.subcomponents:
            if isinstance(subcomponent, CubitInstance):
                cmd(f"{str(subcomponent)} move {str(vector)}")

    def extract_parameters(self, parameters):
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

    def check_sanity(self):
        pass

    def set_mesh_size(self, size: int):
        for subcomponent in self.get_subcomponents():
            cmd(f"{subcomponent.geometry_type} {subcomponent.cid} size {size}")
    
    def volume_id_string(self):
        self.as_volumes()
        return " ".join([str(subcomponent.cid) for subcomponent in self.get_subcomponents()]) 


class CylindricalComponent(SimpleComponent):
    """A generic cylindrical component of a single material.
    """
    def __init__(self, classname: str, material: str,  radius: float,
                 length: float, axis: str):
        """Initialise a class instance.

        Parameters
        ----------
        classname : str
            Name to be used to label the component.
        material : str
            The cylinder's material, expressed as a string.
        radius : float
            The cylinder's radius in metres.
        length : float
            The cylinder's length in metres.
        axis : str
            The orientation axis of the cylinder (the dimension to which its
            length is parallel). Expressed as "x", "y", "z".
        """
        parameter_dict = {
            "material": material,
            "radius": radius,
            "length": length,
            "axis": axis,
        }
        super().__init__(classname, parameter_dict)

    def make_geometry(self):
        """Generate the component geometry.

        Returns
        -------
        volume : CubitInstance
            The constructed component geometry.
        """
        # Get parameters.
        radius = self.geometry["radius"]
        length = self.geometry["length"]
        axis = self.geometry["axis"]

        # Make geometry.
        volume = make_cylinder_along(radius, length, axis)

        return volume


class CylindricalLayerComponent(SimpleComponent):
    """A generic cylindrical layer component comprised of a single material
    surrounding a central void.
    """
    def __init__(self, classname: str, material: str, inner_radius: float,
                 thickness: float, length: float, axis: str):
        """Initialise a class instance.

        Parameters
        ----------
        classname : str
            Name to be used to label the component.
        material : str
            The cylindrical layer's material.
        inner_radius : float
            The cylindrical layer's inner radius in metres.
        thickness : float
            The cylindrical layer's thickness in metres.
        length : float
            The cylindrical layer's length in metres.
        axis : str
            The orientation axis of the cylindrical layer (the dimension to
            which its length is parallel). Can be either "x", "y", "z".
        """
        parameter_dict = {
            "material": material,
            "inner_radius": inner_radius,
            "thickness": thickness,
            "length": length,
            "axis": axis,
        }
        super().__init__(classname, parameter_dict)

    def make_geometry(self):
        """Generate the component geometry.

        Returns
        -------
        volume : CubitInstance
            The constructed component geometry.
        """
        # Get parameters.
        inner_radius = self.geometry["inner_radius"]
        thickness = self.geometry["thickness"]
        outer_radius = inner_radius + thickness
        length = self.geometry["length"]
        axis = self.geometry["axis"]

        # Make geometry.
        positive_volume = make_cylinder_along(outer_radius, length, axis)
        negative_volume = make_cylinder_along(inner_radius, length, axis)
        volume = subtract(positive_volume, negative_volume)

        return volume


class PolygonalPrismComponent(SimpleComponent):
    """A generic polygonal prism component of a single material.
    """
    def __init__(self, classname: str, material: str, polygon_sides: int,
                 radius: float, length: float, axis: str):
        """Initialise a class instance.

        Parameters
        ----------
        classname : str
            Name to be used to label the component.
        material : str
            The prism's material, expressed as a string.
        polygon_sides : int
            The prism's number of sides, e.g. 6 for a hexagonal prism.
        radius : float
            The prism's radius in metres.
        length : float
            The prism's length in metres.
        axis : str
            The orientation axis of the prism (the dimension to which its
            length is parallel). Can be either "x", "y", "z".
        """
        parameter_dict = {
            "material": material,
            "polygon sides": polygon_sides,
            "radius": radius,
            "length": length,
            "axis": axis,
        }
        super().__init__(classname, parameter_dict)

    def make_geometry(self):
        """Generate the component geometry.

        Returns
        -------
        volume : CubitInstance
            The constructed component geometry.
        """
        # Get parameters.
        polygon_sides = self.geometry["polygon sides"]
        radius = self.geometry["radius"]
        length = self.geometry["length"]
        axis = self.geometry["axis"]

        # Make geometry.
        volume = make_prism_along(polygon_sides, radius, length, axis)

        return volume


class PolygonalPrismLayerComponent(SimpleComponent):
    """A generic polygonal prism layer component of a single material
    surrounding a central void.
    """
    def __init__(self, classname: str, material: str, polygon_sides: int,
                 inner_radius: float, radial_thickness: float, length: float,
                 axis: str):
        """Initialise a class instance.

        Parameters
        ----------
        classname : str
            Name to be used to label the component.
        material : str
            The prism layer's material, expressed as a string.
        polygon_sides : int
            The prism layer's number of sides, e.g. 6 for a hexagonal prism.
        inner_radius : float
            The prism layer's inner radius in metres.
        thickness : float
            The prism layer's thickness in metres.
        length : float
            The prism layer's length in metres.
        axis : str
            The orientation axis of the prism (the dimension to which its
            length is parallel). Can be either "x", "y", "z".
        """
        parameter_dict = {
            "material": material,
            "polygon sides": polygon_sides,
            "inner radius": inner_radius,
            "radial thickness": radial_thickness,
            "length": length,
            "axis": axis,
        }
        super().__init__(classname, parameter_dict)

    def make_geometry(self):
        """Generate the component geometry.

        Returns
        -------
        volume : CubitInstance
            The constructed component geometry.
        """
        # Get parameters.
        polygon_sides = self.geometry["polygon sides"]
        inner_radius = self.geometry["inner_radius"]
        thickness = self.geometry["thickness"]
        outer_radius = inner_radius + thickness
        length = self.geometry["length"]
        axis = self.geometry["axis"]

        # Make geometry.
        positive_volume = make_prism_along(polygon_sides, outer_radius, length, axis)
        negative_volume = make_cylinder_along(inner_radius, length, axis)
        volume = subtract(positive_volume, negative_volume)

        return volume


class SurroundingWallsComponent(SimpleComponent):
    '''Surrounding walls, filled with air'''
    def __init__(self, json_object: dict):
        super().__init__("surrounding_walls", json_object)

        # fill room with air
        self.air_material = json_object["air"]
        self.air = AirComponent(self.geometry, self.air_material) if self.air_material != "none" else False

    def is_air(self):
        '''Does this room have air in it?'''
        return isinstance(self.air, AirComponent)

    def air_as_volumes(self):
        '''reference air as volume entities instead of body entities'''
        if self.is_air():
            self.air.as_volumes()

    def get_air_subcomponents(self):
        return self.air.get_subcomponents()

    def make_geometry(self):
        '''create 3d room with outer dimensions dimensions (int or list) and thickness (int or list)'''
        # get variables
        outer_dims = self.convert_to_3d_vector(self.geometry["dimensions"])
        thickness = self.convert_to_3d_vector(self.geometry["thickness"])
        # create room
        subtract_vol = cubit.brick(outer_dims[0]-2*thickness[0], outer_dims[1]-2*thickness[1], outer_dims[2]-2*thickness[2])
        block = cubit.brick(outer_dims[0], outer_dims[1], outer_dims[2])
        cubit.subtract([subtract_vol], [block])
        room_id = cubit.get_last_id("volume")
        return CubitInstance(room_id, "volume")


class AirComponent(SimpleComponent):
    '''Air, stored as body'''
    def __init__(self, json_object: dict):
        super().__init__("air", json_object)
        # cubit subtract only keeps body ID invariant, so i will store air as a body
        self.as_bodies()


class BreederComponent(SimpleComponent):
    def __init__(self, json_object):
        super().__init__("breeder", json_object)


class StructureComponent(SimpleComponent):
    def __init__(self, json_object):
        super().__init__("structure", json_object)

class WallComponent(SimpleComponent):
    def __init__(self, json_object):
        super().__init__("wall", json_object)

    def make_geometry(self):
        # get variables
        # wall
        geometry = self.geometry
        thickness = geometry["wall thickness"]
        plane = geometry["wall plane"] if "wall plane" in geometry.keys() else "x"
        pos = geometry["wall position"] if "wall position" in geometry.keys() else 0
        # hole
        hole_pos = geometry["wall hole position"] if "wall hole position" in geometry.keys() else [0, 0]
        hole_radius = geometry["wall hole radius"]
        # wall fills room
        room_dims = self.convert_to_3d_vector(geometry["dimensions"])
        room_thickness = self.convert_to_3d_vector(geometry["thickness"])
        wall_dims = [room_dims[i]-2*room_thickness[i] for i in range(3)]

        # volume to subtract to create a hole
        cmd(f"create cylinder height {thickness} radius {hole_radius}")
        subtract_vol = CubitInstance(cubit.get_last_id("volume"), "volume")

        # depending on what plane the wall needs to be in, create wall + make hole at right place
        if plane == "x":
            cubit.brick(thickness, wall_dims[1], wall_dims[2])
            wall = CubitInstance(cubit.get_last_id("volume"), "volume")
            cmd(f"rotate volume {subtract_vol.cid} angle 90 about Y")
            cmd(f"move volume {subtract_vol.cid} y {hole_pos[1]} z {hole_pos[0]}")
        elif plane == "y":
            cubit.brick(wall_dims[0], thickness, wall_dims[2])
            wall = CubitInstance(cubit.get_last_id("volume"), "volume")
            cmd(f"rotate volume {subtract_vol.cid} angle 90 about X")
            cmd(f"move volume {subtract_vol.cid} x {hole_pos[0]} z {hole_pos[1]}")
        elif plane == "z":
            cubit.brick(wall_dims[0], wall_dims[1], thickness)
            wall = CubitInstance(cubit.get_last_id("volume"), "volume")
            cmd(f"move volume {subtract_vol.cid} x {hole_pos[0]} y {hole_pos[1]}")
        else:
            raise CubismError("unrecognised plane specified")

        cmd(f"subtract volume {subtract_vol.cid} from volume {wall.cid}")
        # move wall
        cmd(f"move volume {wall.cid} {plane} {pos}")

        return CubitInstance(wall.cid, wall.geometry_type)


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

        
        if inner_bluntness != 0 and outer_bluntness != 0:
            cladding_vertices = list(np.zeros(14))

            # set up points of face-to-sweep
            cladding_vertices[0] = Vertex(0, inner_less_purge_thickness)
            cladding_vertices[1] = Vertex(0)

            inner_cladding_ref1 = Vertex(-inner_length)
            cladding_vertices[2] = inner_cladding_ref1 + Vertex(inner_bluntness)
            cladding_vertices[3] = inner_cladding_ref1 + Vertex(inner_bluntness).rotate(slope_angle)

            outer_cladding_ref1 = inner_cladding_ref1 + Vertex(offset, net_thickness)
            cladding_vertices[4] = outer_cladding_ref1 + Vertex(outer_bluntness).rotate(slope_angle-np.pi)
            cladding_vertices[5] = outer_cladding_ref1 + Vertex(outer_bluntness)

            cladding_vertices[6] = outer_cladding_ref1 + Vertex(outer_length)
            cladding_vertices[7] = outer_cladding_ref1 + Vertex(outer_length, -outer_cladding)

            outer_cladding_ref2 = outer_cladding_ref1 + Vertex(outer_cladding * np.tan(slope_angle/2), -outer_cladding)
            cladding_vertices[8] = outer_cladding_ref2 + Vertex(outer_bluntness)
            cladding_vertices[9] = outer_cladding_ref2 + Vertex(outer_bluntness).rotate(slope_angle-np.pi)

            inner_cladding_ref2 = inner_cladding_ref1 + Vertex(inner_cladding/np.tan(slope_angle) + outer_cladding/np.sin(slope_angle), inner_cladding)
            cladding_vertices[10] = inner_cladding_ref2 + Vertex(inner_bluntness).rotate(slope_angle)
            cladding_vertices[11] = inner_cladding_ref2 + Vertex(inner_bluntness)

            cladding_vertices[13] = cladding_vertices[0] + Vertex(-distance_to_step)
            cladding_vertices[12] = cladding_vertices[13] + Vertex(0, step_thickness)

            surface_to_sweep = make_surface(cladding_vertices, [2, 4, 8, 10])
        elif outer_bluntness != 0:
            cladding_vertices = list(np.zeros(12))

            # set up points of face-to-sweep
            cladding_vertices[0] = Vertex(0, inner_less_purge_thickness)
            cladding_vertices[1] = Vertex(0)
            cladding_vertices[2] = Vertex(-inner_length)
            inner_cladding_ref1 = cladding_vertices[2]

            outer_cladding_ref1 = inner_cladding_ref1 + Vertex(offset, net_thickness)
            cladding_vertices[3] = outer_cladding_ref1 + Vertex(outer_bluntness).rotate(slope_angle-np.pi)
            cladding_vertices[4] = outer_cladding_ref1 + Vertex(outer_bluntness)

            cladding_vertices[5] = outer_cladding_ref1 + Vertex(outer_length)
            cladding_vertices[6] = outer_cladding_ref1 + Vertex(outer_length, -outer_cladding)

            outer_cladding_ref2 = outer_cladding_ref1 + Vertex(outer_cladding * np.tan(slope_angle/2), -outer_cladding)
            cladding_vertices[7] = outer_cladding_ref2 + Vertex(outer_bluntness)
            cladding_vertices[8] = outer_cladding_ref2 + Vertex(outer_bluntness).rotate(slope_angle-np.pi)

            cladding_vertices[9] = cladding_vertices[2] + Vertex(inner_cladding/np.tan(slope_angle) + outer_cladding/np.sin(slope_angle), inner_cladding)

            cladding_vertices[11] = cladding_vertices[0] + Vertex(-distance_to_step)
            cladding_vertices[10] = cladding_vertices[11] + Vertex(0, step_thickness)

            surface_to_sweep = make_surface(cladding_vertices, [3, 7])

        elif inner_bluntness != 0:
            cladding_vertices = list(np.zeros(12))

            # set up points of face-to-sweep
            cladding_vertices[0] = Vertex(0, inner_less_purge_thickness)
            cladding_vertices[1] = Vertex(0)

            inner_cladding_ref1 = Vertex(-inner_length)
            cladding_vertices[2] = inner_cladding_ref1 + Vertex(inner_bluntness)
            cladding_vertices[3] = inner_cladding_ref1 + Vertex(inner_bluntness).rotate(slope_angle)

            cladding_vertices[4] = inner_cladding_ref1 + Vertex(offset, net_thickness)
            outer_cladding_ref1 = cladding_vertices[4]

            cladding_vertices[5] = outer_cladding_ref1 + Vertex(outer_length)
            cladding_vertices[6] = outer_cladding_ref1 + Vertex(outer_length, -outer_cladding)

            cladding_vertices[7] = outer_cladding_ref1 + Vertex(outer_cladding * np.tan(slope_angle/2), -outer_cladding)

            inner_cladding_ref2 = inner_cladding_ref1 + Vertex(inner_cladding/np.tan(slope_angle) + outer_cladding/np.sin(slope_angle), inner_cladding)
            cladding_vertices[8] = inner_cladding_ref2 + Vertex(inner_bluntness).rotate(slope_angle)
            cladding_vertices[9] = inner_cladding_ref2 + Vertex(inner_bluntness)

            cladding_vertices[11] = cladding_vertices[0] + Vertex(-distance_to_step)
            cladding_vertices[10] = cladding_vertices[11] + Vertex(0, step_thickness)

            surface_to_sweep = make_surface(cladding_vertices, [2, 8])
        else:
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

            surface_to_sweep = make_surface(cladding_vertices, [])

        cmd(f"sweep surface {surface_to_sweep.cid} axis 0 {-coolant_inlet_radius} 0 1 0 0 angle 360")
        cladding = get_last_geometry("volume")

        duct_vertices = list(np.zeros(4))
        duct_vertices[0] = cladding_vertices[0] + Vertex(-purge_duct_offset, purge_duct_thickness)
        duct_vertices[1] = cladding_vertices[0] + Vertex(-distance_to_disk, purge_duct_thickness)
        duct_vertices[2] = duct_vertices[1] + Vertex(0, purge_duct_cladding)
        duct_vertices[3] = duct_vertices[0] + Vertex(0, purge_duct_cladding)

        duct_surface = make_surface(duct_vertices, [])
        cmd(f"sweep surface {duct_surface.cid} axis 0 {-coolant_inlet_radius} 0 1 0 0 angle 360")
        duct = get_last_geometry("volume")

        # realign with origin
        cubit.move(cladding.handle, [inner_length, coolant_inlet_radius, 0])
        cubit.move(duct.handle, [inner_length, coolant_inlet_radius, 0])
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

        slope_angle = np.arctan(cladding_thickness / offset)

        if inner_bluntness != 0 and outer_bluntness != 0:
            coolant_vertices = list(np.zeros(10))

            coolant_vertices[0] = Vertex(0)
            coolant_vertices[1] = Vertex(0, inlet_radius)

            inner_cladding_ref1 = Vertex(-inner_length, inlet_radius)
            coolant_vertices[2] = inner_cladding_ref1 + Vertex(inner_bluntness)
            coolant_vertices[3] = inner_cladding_ref1 + Vertex(inner_bluntness).rotate(slope_angle)

            outer_cladding_ref1 = inner_cladding_ref1 + Vertex(offset, cladding_thickness)
            coolant_vertices[4] = outer_cladding_ref1 + Vertex(outer_bluntness).rotate(slope_angle-np.pi)
            coolant_vertices[5] = outer_cladding_ref1 + Vertex(outer_bluntness)
            coolant_vertices[6] = outer_cladding_ref1 + Vertex(pressure_tube_length-(offset+pressure_tube_gap))

            coolant_vertices[9] = coolant_vertices[0] + Vertex(-(inner_length+pressure_tube_gap))
            coolant_vertices[8] = coolant_vertices[9] + Vertex(0, pressure_tube_radius)
            coolant_vertices[7] = coolant_vertices[8] + Vertex(pressure_tube_length)

            surface_to_sweep = make_surface(coolant_vertices, [2, 4])
        elif outer_bluntness != 0:
            coolant_vertices = list(np.zeros(9))

            coolant_vertices[0] = Vertex(0)
            coolant_vertices[1] = Vertex(0, inlet_radius)

            coolant_vertices[2] = Vertex(-inner_length, inlet_radius)
            inner_cladding_ref1 = coolant_vertices[2]

            outer_cladding_ref1 = inner_cladding_ref1 + Vertex(offset, cladding_thickness)
            coolant_vertices[3] = outer_cladding_ref1 + Vertex(outer_bluntness).rotate(slope_angle-np.pi)
            coolant_vertices[4] = outer_cladding_ref1 + Vertex(outer_bluntness)
            coolant_vertices[5] = outer_cladding_ref1 + Vertex(pressure_tube_length-(offset+pressure_tube_gap))

            coolant_vertices[8] = coolant_vertices[0] + Vertex(-(inner_length+pressure_tube_gap))
            coolant_vertices[7] = coolant_vertices[8] + Vertex(0, pressure_tube_radius)
            coolant_vertices[6] = coolant_vertices[7] + Vertex(pressure_tube_length)

            surface_to_sweep = make_surface(coolant_vertices, [3])
        elif inner_bluntness != 0:
            coolant_vertices = list(np.zeros(9))

            coolant_vertices[0] = Vertex(0)
            coolant_vertices[1] = Vertex(0, inlet_radius)

            inner_cladding_ref1 = Vertex(-inner_length, inlet_radius)
            coolant_vertices[2] = inner_cladding_ref1 + Vertex(inner_bluntness)
            coolant_vertices[3] = inner_cladding_ref1 + Vertex(inner_bluntness).rotate(slope_angle)

            coolant_vertices[4] = inner_cladding_ref1 + Vertex(offset, cladding_thickness)
            outer_cladding_ref1 = coolant_vertices[4]

            coolant_vertices[5] = outer_cladding_ref1 + Vertex(pressure_tube_length-(offset+pressure_tube_gap))

            coolant_vertices[8] = coolant_vertices[0] + Vertex(-(inner_length+pressure_tube_gap))
            coolant_vertices[7] = coolant_vertices[8] + Vertex(0, pressure_tube_radius)
            coolant_vertices[6] = coolant_vertices[7] + Vertex(pressure_tube_length)

            surface_to_sweep = make_surface(coolant_vertices, [2])
        else:
            coolant_vertices = list(np.zeros(8))

            coolant_vertices[0] = Vertex(0)
            coolant_vertices[1] = Vertex(0, inlet_radius)

            coolant_vertices[2] = Vertex(-inner_length, inlet_radius)
            coolant_vertices[3] = coolant_vertices[2] + Vertex(offset, cladding_thickness)
            coolant_vertices[4] = coolant_vertices[3] + Vertex(pressure_tube_length-(offset+pressure_tube_gap))

            coolant_vertices[7] = coolant_vertices[0] + Vertex(-(inner_length+pressure_tube_gap))
            coolant_vertices[6] = coolant_vertices[7] + Vertex(0, pressure_tube_radius)
            coolant_vertices[5] = coolant_vertices[6] + Vertex(pressure_tube_length)

            surface_to_sweep = make_surface(coolant_vertices, [])

        cmd(f"sweep surface {surface_to_sweep.cid} axis 0 0 0 1 0 0 angle 360")
        coolant = get_last_geometry("volume")
        # realign with origin
        cubit.move(coolant.handle, [inner_length+pressure_tube_gap, 0, 0])
        return coolant


class PressureTubeComponent(SimpleComponent):
    def __init__(self, json_object):
        super().__init__("pressure_tube", json_object)

    def make_geometry(self):
        length = self.geometry["length"]
        outer_radius = self.geometry["outer radius"]
        thickness = self.geometry["thickness"]

        subtract_vol = cmd_geom(f"create cylinder height {length-thickness} radius {outer_radius-thickness}", "volume")
        cmd(f"volume {subtract_vol.cid} move 0 0 {-thickness/2}")
        cylinder = cmd_geom(f"create cylinder height {length} radius {outer_radius}", "volume")

        cmd(f"subtract volume {subtract_vol.cid} from volume {cylinder.cid}")
        tube = get_last_geometry("volume")
        cmd(f"rotate volume {tube.cid} about Y angle -90")
        cmd(f"volume {tube.cid} move {length/2} 0 0")

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
        cmd(f"sweep surface {tube_surface.cid} axis 0 0 0 1 0 0 angle 360")
        tube = get_last_geometry("volume")

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
        cmd(f"sweep surface {tube_surface.cid} axis 0 0 0 1 0 0 angle 360")
        tube = get_last_geometry("volume")

        return tube


class FilterDiskComponent(SimpleComponent):
    def __init__(self, json_object):
        super().__init__("filter_disk", json_object)

    def make_geometry(self):
        length = self.geometry["length"]
        outer_radius = self.geometry["outer radius"]
        thickness = self.geometry["thickness"]

        subtract_vol = cmd_geom(f"create cylinder height {length} radius {outer_radius-thickness}", "volume")
        cylinder = cmd_geom(f"create cylinder height {length} radius {outer_radius}", "volume")

        cmd(f"subtract volume {subtract_vol.cid} from volume {cylinder.cid}")
        tube = get_last_geometry("volume")
        cmd(f"rotate volume {tube.cid} about Y angle -90")
        cmd(f"volume {tube.cid} move {length/2} 0 0")
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
        cmd(f"volume {subtract_vol.cid} move 0 0 {length/2}")

        # hexagonal face
        face_vertex_positions = [Vertex(side_length).rotate(i*np.pi/3) for i in range(6)]
        face = make_surface(face_vertex_positions, [])
        cmd(f"sweep surface {face.cid} vector 0 0 1 distance {length}")
        hex_prism = get_last_geometry("volume")

        cmd(f"subtract volume {subtract_vol.cid} from volume {hex_prism.cid}")
        multiplier = get_last_geometry("volume")
        cmd(f"rotate volume {multiplier.cid} about Y angle 90")

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
        slope_angle = np.arctan(thickness / offset)

        if inner_bluntness != 0 and outer_bluntness != 0:
            breeder_vertices = list(np.zeros(6))
            breeder_vertices[0] = Vertex(length)
            breeder_vertices[1] = Vertex(inner_bluntness)
            breeder_vertices[2] = Vertex(inner_bluntness).rotate(slope_angle)

            outer_ref = Vertex(offset, thickness)
            breeder_vertices[3] = outer_ref + Vertex(outer_bluntness).rotate(slope_angle-np.pi)
            breeder_vertices[4] = outer_ref + Vertex(outer_bluntness)
            breeder_vertices[5] = Vertex(length, thickness)

            surface_to_sweep = make_surface(breeder_vertices, [1, 3])
        elif outer_bluntness != 0:
            breeder_vertices = list(np.zeros(5))
            breeder_vertices[0] = Vertex(length)
            breeder_vertices[1] = Vertex(0)

            outer_ref = Vertex(offset, thickness)
            breeder_vertices[2] = outer_ref + Vertex(outer_bluntness).rotate(slope_angle-np.pi)
            breeder_vertices[3] = outer_ref + Vertex(outer_bluntness)
            breeder_vertices[4] = Vertex(length, thickness)

            surface_to_sweep = make_surface(breeder_vertices, [2])
        elif inner_bluntness != 0:
            breeder_vertices = list(np.zeros(5))
            breeder_vertices[0] = Vertex(length)
            breeder_vertices[1] = Vertex(inner_bluntness)
            breeder_vertices[2] = Vertex(inner_bluntness).rotate(slope_angle)

            breeder_vertices[3] =  Vertex(offset, thickness)
            breeder_vertices[4] = Vertex(length, thickness)

            surface_to_sweep = make_surface(breeder_vertices, [1])
        else:
            breeder_vertices = list(np.zeros(4))
            breeder_vertices[0] = Vertex(length)
            breeder_vertices[1] = Vertex(0)
            breeder_vertices[2] = Vertex(offset, thickness)
            breeder_vertices[3] = Vertex(length, thickness)

            surface_to_sweep = make_surface(breeder_vertices, [])
        cmd(f"sweep surface {surface_to_sweep.cid} axis 0 {-inner_radius} 0 1 0 0 angle 360")
        breeder = get_last_geometry("volume")
        cubit.move(breeder.handle, [0, inner_radius, 0])

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
        bluntness = geometry["bluntness"]
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
        if bluntness == 0:
            vertices = list(np.zeros(8))
            vertices[0] = Vertex(0, 0)

            vertices[1] = Vertex(offset, length)
            vertices[2] = vertices[1] + Vertex(inner_width)

            vertices[3] = vertices[0] + Vertex(outer_width)
            vertices[4] = vertices[3] + Vertex(-sidewall_horizontal)

            vertices[5] = vertices[2] + Vertex(-sidewall_horizontal) + Vertex(thickness/np.tan(slope_angle), -thickness, 0)
            vertices[6] = vertices[1] + Vertex(sidewall_horizontal) + Vertex(-thickness/np.tan(slope_angle), -thickness, 0)
            vertices[7] = vertices[0] + Vertex(sidewall_horizontal)

            face_to_sweep = make_surface(vertices, [])
        else:
            vertices = [Vertex(0) for i in range(12)]
            vertices[0] = Vertex(0)

            left_ref = Vertex(offset, length)
            vertices[1] = left_ref + Vertex(bluntness).rotate(slope_angle-np.pi)
            vertices[2] = left_ref + Vertex(bluntness)

            right_ref = left_ref + Vertex(inner_width)
            vertices[3] = right_ref + Vertex(-bluntness)
            vertices[4] = right_ref + Vertex(bluntness).rotate(-slope_angle)

            vertices[5] = vertices[0] + Vertex(outer_width)
            vertices[6] = vertices[5] + Vertex(-sidewall_horizontal)

            right_ref_inner = right_ref + Vertex(-sidewall_horizontal) + Vertex(thickness/np.tan(slope_angle), -thickness, 0)
            vertices[7] = right_ref_inner + Vertex(bluntness).rotate(-slope_angle)
            vertices[8] = right_ref_inner + Vertex(-bluntness)

            left_ref_inner = left_ref + Vertex(sidewall_horizontal) + Vertex(-thickness/np.tan(slope_angle), -thickness, 0)
            vertices[9] = left_ref_inner + Vertex(bluntness)
            vertices[10] = left_ref_inner + Vertex(bluntness).rotate(slope_angle-np.pi)

            vertices[11] = vertices[0] + Vertex(sidewall_horizontal)

            face_to_sweep = make_surface(vertices, [1, 3, 7, 9])

        # line up sweep direction along y axis
        cmd(f"surface {face_to_sweep.cid} move -{outer_width/2} 0 0")
        cmd(f"surface {face_to_sweep.cid} rotate 90 about x")
        cmd(f"sweep surface {face_to_sweep.cid} vector 0 1 0 distance {height}")
        first_wall = get_last_geometry("volume")

        no_of_channels = (height - channel_spacing) // (channel_spacing + channel_width)
        for i in range(no_of_channels):
            channel = self.make_channel_volume(vertices)
            if i%2 == 0:
                cmd(f"{channel} reflect 1 0 0")
            channel.move([0, i*(channel_spacing + channel_width) + channel_spacing, 0])
            first_wall = subtract([first_wall], [channel])[0]

        # cubit.move(first_wall.cubitInstance, [0,0,length])
        return first_wall
    
    def make_channel_volume(self, vertices):
        geometry = self.geometry
        # get first wall params
        inner_width = geometry["inner width"]
        outer_width = geometry["outer width"]
        length = geometry["length"]
        offset = (outer_width - inner_width)/2

        # get channel params
        channel_width = geometry["channel width"]
        channel_back_manifold_offset = geometry["channel back manifold offset"]
        channel_back_manifold_width = geometry["channel back manifold width"]
        channel_front_manifold_offset = geometry["channel front manifold offset"]
        channel_front_manifold_width = geometry["channel front manifold width"]
        channel_depth = geometry["channel depth"]
        channel_padding = geometry["channel padding"]
        # useful unit vectors
        out_right = Vertex(length, offset).unit()
        out_left = Vertex(-length, offset).unit()
        slope_right = Vertex(-offset, length).unit()
        slope_left = Vertex(offset, length).unit()
        # construct channel vertices
        channel_vertices = [Vertex(0) for i in range(16)]
        channel_vertices[0] = Line(slope_left, vertices[11]).vertex_at(y=channel_back_manifold_offset) + (channel_padding * slope_left)
        channel_vertices[2] = vertices[1] - out_left * channel_depth
        channel_vertices[1] = Line(slope_left, channel_vertices[2]).vertex_at(y= channel_vertices[0].y)
        channel_vertices[3] = vertices[2] - Vertex(0, channel_depth)
        channel_vertices[4] = vertices[3] - Vertex(0, channel_depth)
        channel_vertices[5] = vertices[4] - out_right * channel_depth
        channel_vertices[7] = Line(slope_right, vertices[6]).vertex_at(y=channel_front_manifold_offset) + (channel_padding * slope_right)
        channel_vertices[6] = Line(slope_right, channel_vertices[5]).vertex_at(y=channel_vertices[7].y)
        channel_vertices[8] = channel_vertices[7] + (channel_front_manifold_width - 2*channel_padding) * slope_right
        channel_vertices[10] = channel_vertices[5] - (channel_width * out_right)
        channel_vertices[9] = Line(slope_right, channel_vertices[10]).vertex_at(y=channel_vertices[8].y)
        channel_vertices[11] = channel_vertices[4] - Vertex(0, channel_width)
        channel_vertices[12] = channel_vertices[3] - Vertex(0, channel_width)
        channel_vertices[13] = channel_vertices[2] - channel_width * out_left
        channel_vertices[15] = channel_vertices[0] + (channel_back_manifold_width - 2*channel_padding) * slope_left
        channel_vertices[14] = Line(slope_left, channel_vertices[13]).vertex_at(y= channel_vertices[15].y)
        # make into surface and sweep surface to make volume
        channel_to_sweep = make_surface(channel_vertices, [2, 4, 10, 12])
        cmd(f"surface {channel_to_sweep.cid} move -{outer_width/2} 0 0")
        cmd(f"surface {channel_to_sweep.cid} rotate 90 about x")
        cmd(f"sweep surface {channel_to_sweep.cid} vector 0 1 0 distance {channel_width}")
        channel = get_last_geometry("volume")

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
        cmd(f"sweep surface {face_to_sweep.cid} vector 0 1 0 distance {height}")
        plate = get_last_geometry("body")
        cmd(f"{str(plate)} move {self.origin.x} 0 0")
        plate = self.__make_holes(plate)
        cmd(f"{str(plate)} move {Vertex(-self.origin.x).x} 0 0")
        return to_volumes([plate])

    def __make_holes(self, plate: CubitInstance):
        plate_thickness = self.geometry["thickness"]
        hole_radius = self.geometry["hole radius"]

        for row in self.pin_pos:
            for position in row:
                hole_position = Vertex(position.x, position.y, 0)
                hole_to_be = cmd_geom(f"create cylinder radius {hole_radius} height {plate_thickness*3}", "volume")
                cmd(f"{hole_to_be.geometry_type} {hole_to_be.cid} move {str(hole_position)}")
                cmd(f"subtract {hole_to_be.geometry_type} {hole_to_be.cid} from {plate.geometry_type} {plate.cid}")
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
        plates.extend(Plate(self.classname+"_left", left_plate_json, "left", self.hole_pos[0]).get_subcomponents())

        for i in range(len(self.rib_pos)-1):
            mid_plate_json = self.__make_mid_plate_json(i)
            plates.extend(Plate(self.classname+"_mid", mid_plate_json, "mid", self.hole_pos[i+1]).get_subcomponents())

        right_plate_json = self.__make_side_plate_json(-1)
        plates.extend(Plate(self.classname+"_right", right_plate_json, "right", self.hole_pos[-1]).get_subcomponents())

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

        structure = cmd_geom(f"create brick x {thickness} y {height} z {length}", "body")
        cmd(f"{structure.geometry_type} {structure.cid} move 0 {height/2} {-length/2}")

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
            hole_to_be = cmd_geom(f"create brick x {channel_dims.x} y {channel_dims.y} z {channel_dims.z}", "volume")
            hole_name = str(hole_to_be)
            cmd(f"{hole_name} move 0 {channel_dims.y/2} {-channel_dims.z/2}")
            cmd(f"{hole_name} move 0 {y_margin + i*spacing} {-z_offset}")
            cmd(f"subtract {hole_name} from {str(structure)}")

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
        cmd(f"sweep surface {face_to_sweep.cid} vector 0 1 0 distance {height}")
        front_plate = get_last_geometry("volume")

        back_plate = list(np.zeros(4))
        back_plate[0] = Vertex(start_x, 0, -length)
        back_plate[1] = Vertex(end_x, 0, -length)
        back_plate[2] = back_plate[1] + Vertex(0, 0, thickness)
        back_plate[3] = back_plate[0] + Vertex(0, 0, thickness)

        face_to_sweep = make_surface(back_plate, [])
        cmd(f"sweep surface {face_to_sweep.cid} vector 0 1 0 distance {height}")
        back_plate = get_last_geometry("volume")

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
        cmd(f"sweep surface {face_to_sweep.cid} vector 0 1 0 distance {height}")
        plenum = get_last_geometry("volume")
        return plenum


class SeparatorPlate(PurgeGasPlate):
    def __init__(self, json_object: dict, rib_positions: list[Vertex], rib_thickness: int):
        super().__init__(
            "separator_plate", json_object, rib_positions, rib_thickness, [[[]] for i in rib_positions]
            )


class FWBackplate(Plate):
    def __init__(self, json_object: dict):
        super().__init__("FW_backplate", json_object, "full")
