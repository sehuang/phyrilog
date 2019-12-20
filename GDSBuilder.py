import gdspy as gp
import re
from collections import defaultdict

class LayerMap:
    """Python representation of layermap"""
    def __init__(self, mapfile):
        self.map = defaultdict(dict)
        with open(mapfile) as mapfile:
            line_list = [line.rstrip('\n') for line in mapfile]

        line_list = self._strip_comments(line_list)
        for line in line_list:
            layer, purpose, layer_num, dtype_num = line.split()
            self.map[layer][purpose] = (int(layer_num), int(dtype_num))

    def _strip_comments(self, line_list):
        """Removes comments and empty lines from lines."""
        new_line_list = []
        for line in line_list:
            if re.search("#", line):
                continue
            elif re.match("(?![\s\S])", line):
                continue
            else:
                new_line_list.append(line)
        return new_line_list


class GDSBuilder:
    """API for ease of building a GDS file using gdspy"""
    def __init__(self, gds_library, layermap: LayerMap = None, mapfile: str = None):
        if not layermap:
            if not mapfile:
                raise FileNotFoundError("Please specify a .layermap file or LayerMap object.")
            self.layermap = LayerMap(mapfile)
        else:
            self.layermap = layermap
        self.gdsii = gds_library

    def get_layer_dtype_tuple(self, layer, purpose = None):
        if not layer:
            raise ValueError("Must define layer stream number.")
        if purpose:
            return self.layermap.map[layer][purpose]
        else:
            return list(self.layermap.map[layer].values())[0][0] # this is a hack to get the layer number only. Not sure if needed

    def make_shape_from_phy(self, phy_obj):
        layer = phy_obj.layer
        coords = phy_obj.coords
        shape = []
        for purpose in phy_obj.purpose:
            map_tuple = self.get_layer_dtype_tuple(layer, purpose)
            if purpose in ['drawing', 'pin', 'blockage']:
                shape.append(self.make_polygon(coords, tuple=map_tuple))
            elif purpose in ['label']:
                shape.append(self.make_label(coords, phy_obj.text, layer))
            else:
                pass

        return shape

    def make_polygon(self, coords, layer=None, purpose=None, tuple=None):
        if tuple:
            layer_num = tuple[0]
            datatype = tuple[1]
        else:
            layer_num, datatype = self.get_layer_dtype_tuple(layer, purpose)
        corner1 = (coords[0], coords[1])
        corner2 = (coords[2], coords[3])
        return gp.Rectangle(corner1, corner2, layer_num, datatype)

    def make_label(self, coords, text, layer):
        purpose = 'label'
        layer_num = self.get_layer_dtype_tuple(layer)
        # centroid = [round(((coords[0] + coords[2]) / 2), 3), round((coords[1] + coords[3]) / 2, 3)]
        name = text
        return gp.Label(text, coords, layer=layer_num)

    def scale_all(self, cell, scale_factor):
        for polygon in cell.polygons:
            polygon.scale(scale_factor)
        for label in cell.labels:
            label.position = label.position * scale_factor

class GDSDesign:
    """Wrapper around gdspy description of the design"""
    def __init__(self, phy_design, layermap_file):
        self.phy_design = phy_design
        self.specs = phy_design.specs
        self.gdsii = gp.GdsLibrary(phy_design.name, unit=phy_design.specs.data['units'],
                                   precision=phy_design.specs.data['precision'])
        self.gds_builder = GDSBuilder(self.gdsii, mapfile=layermap_file)
        self.top_cell = gp.Cell(phy_design.name, exclude_from_current=True)
        # Fixme: Figure out why GDSLibrary is remembering cells between instances
        self.gdsii.add(self.top_cell, overwrite_duplicate=True)


    def add_polygons(self, cell = None):
        if not cell:
            cell = self.top_cell
        phy = self.phy_design
        polygons = []

        for phy_obj in phy.phys_objs:
            for obj in phy_obj.phys_objs:
                polygons += self.gds_builder.make_shape_from_phy(obj)

        cell.add(polygons)

    def finish_gdsii(self, scale_factor = 1):
        self.gds_builder.scale_all(self.top_cell, scale_factor)

    def write_gdsfile(self, filename):
        filename = str(filename) if not isinstance(filename, str) else filename
        self.gdsii.write_gds(filename)


    ## This thing is too fancy to make rn
    # def extract_cells(self):
    # 	phy = self.phy_design
    # 	self.cell_library = set()
    # 	for polygon_type, polygon in phy.polygons.items():
    # 		for phy_obj in polygon.values():
    # 			for layer in phy_obj.phys_map.values():

