from GDSBuilder import *
from LEFBuilder import *
from verilog2phy import *

class PHYBBox(PHYObject):
    def __init__(self, layers, left_x, bot_y, x_width, y_width):
        super().__init__("BBOX")
        self.type = 'OBS'
        for layer in layers:
            self.add_rect(layer, left_x, bot_y, left_x + x_width, bot_y + y_width)

    def add_rect(self, layer, left_x=0, bot_y=0, right_x=0, top_y=0):
        if layer in self.phys_map.keys():
            self.phys_map[layer].append = [round(left_x, 3), round(bot_y, 3), round(right_x, 3), round(top_y, 3)]
        else:
            self.phys_map[layer] = [[round(left_x, 3), round(bot_y, 3), round(right_x, 3), round(top_y, 3)]]

class BBoxPHY(PHYDesign):
    """Black-boxed LEF object. This class describes LEF stuff"""

    def __init__(self, verilog_module, techfile, spec_dict=None):
        super().__init__(verilog_module, techfile, spec_dict)

        self.add_pin_objects()
        self.add_pg_pin_objects()
        self.build_design_repr()

    def define_design_boundaries(self):
        # TODO: This part needs to be refactored with the specs dict
        if self.x_width:
            x_width = self.x_width
        elif self.y_width:
            x_width = self.y_width * self.aspect_ratio[1] / self.aspect_ratio[0]
        else:
            x_width = None  # Wait until later to figure this out

        if self.y_width:
            y_width = self.y_width
        elif self.x_width:
            y_width = self.x_width * self.aspect_ratio[0] / self.aspect_ratio[1]
        else:
            y_width = None  # Wait until later to figure this out

        self.pin_sides_dict = {'left': [],
                               'right': [],
                               'top': [],
                               'bottom': []}
        for pin in self.pins.values():
            self.pin_sides_dict[pin.side].append(pin)
        for pg_pin in self.pg_pins.values():
            self.pin_sides_dict[pg_pin.side].append(pg_pin)
        min_y_pins = max(len(self.pin_sides_dict['left']), len(self.pin_sides_dict['right']))
        min_x_pins = max(len(self.pin_sides_dict['top']), len(self.pin_sides_dict['bottom']))

        h_pin_width = self.metals[self.specs['pins']['h_layer']]['min_width']
        v_pin_width = self.metals[self.specs['pins']['v_layer']]['min_width']
        h_pin_pitch = self.metals[self.specs['pins']['h_layer']]['pitch']
        v_pin_pitch = self.metals[self.specs['pins']['v_layer']]['pitch']
        min_y_dim = (min_y_pins * h_pin_width) + ((min_y_pins - 1) * h_pin_pitch) if min_y_pins > 0 else (
                min_y_pins * h_pin_width)
        min_x_dim = (min_x_pins * v_pin_width) + ((min_x_pins - 1) * v_pin_pitch) if min_x_pins > 0 else (
                min_x_pins * v_pin_width)

        if not x_width:
            x_width = min_x_dim
        if not y_width:
            y_width = min_y_dim
        if x_width == 0 and y_width > 0:
            x_width = y_width * self.specs['aspect_ratio'][1]
        if y_width == 0 and x_width > 0:
            y_width = x_width * self.specs['aspect_ratio'][0]
        if self.specs['pin_margin']:
            x_width = x_width + v_pin_pitch
            y_width = y_width + h_pin_pitch
        self.bbox_x_width = round(x_width, 3)
        self.bbox_y_width = round(y_width, 3)
        self.bbox_left_margin = round(max([pin.x_width for pin in self.pin_sides_dict['left']], default=0), 3)
        self.bbox_right_margin = round(max([pin.x_width for pin in self.pin_sides_dict['right']], default=0), 3)
        self.bbox_top_margin = round(max([pin.y_width for pin in self.pin_sides_dict['top']], default=0), 3)
        self.bbox_bot_margin = round(max([pin.y_width for pin in self.pin_sides_dict['bottom']], default=0), 3)
        self.x_width = round(self.bbox_x_width + self.bbox_left_margin + self.bbox_right_margin, 3)
        self.y_width = round(self.bbox_y_width + self.bbox_top_margin + self.bbox_bot_margin, 3)

    def place_pins(self, start_corner, side_dict, orientation):
        for pin in side_dict:
            layer = pin.layer
            pin_width = self.metals[layer]['min_width']
            pin_pitch = self.metals[layer]['pitch']
            if pin.center:
                if orientation == 'horizontal':
                    start_corner[1] = round(pin.center - pin_width/2, 3)
                else:
                    start_corner[0] = round(pin.center - pin_width / 2, 3)
            pin.add_rect(layer, start_corner[0], start_corner[1])
            if layer == 'h_layer':
                start_corner[1] = round(start_corner[1] + pin_width + pin_pitch, 3)
            else:
                start_corner[0] = round(start_corner[0] + pin_width + pin_pitch, 3)

    def build_design_repr(self):
        origin = [0, 0]
        h_pin_width = self.metals[self.specs['pins']['h_layer']]['min_width']
        v_pin_width = self.metals[self.specs['pins']['v_layer']]['min_width']
        h_pin_pitch = self.metals[self.specs['pins']['h_layer']]['pitch']
        v_pin_pitch = self.metals[self.specs['pins']['v_layer']]['pitch']
        bbox_bot_left_corner = [self.bbox_left_margin, self.bbox_bot_margin]
        bbox_top_right_corner = [self.x_width - self.bbox_right_margin, self.y_width - self.bbox_top_margin]
        if self.specs['pin_margin']:
            x_corr = v_pin_pitch / 2
            y_corr = h_pin_pitch / 2
        else:
            x_corr = 0
            y_corr = 0

        self.pin_place_start_corners = {}
        self.pin_place_start_corners['left'] = [bbox_bot_left_corner[0],
                                                round(
                                                    round((self.bbox_bot_margin + y_corr) / h_pin_width) * h_pin_pitch,
                                                    3)]
        self.pin_place_start_corners['right'] = [bbox_top_right_corner[0],
                                                 round(
                                                     round((self.bbox_bot_margin + y_corr) / h_pin_width) * h_pin_pitch,
                                                     3)]
        self.pin_place_start_corners['bottom'] = [round(round((bbox_bot_left_corner[0] + x_corr) / v_pin_width), 3), 0]
        self.pin_place_start_corners['top'] = [round(round((bbox_top_right_corner[0] + x_corr) / v_pin_width), 3),
                                               self.y_width]

        bbox_layers = []
        for layer in self.metals:
            if layer not in self.specs['exclude_layers']:
                bbox_layers.append(layer)
        self.bboxes = {
            'BBOX': PHYBBox(bbox_layers, bbox_bot_left_corner[0], bbox_bot_left_corner[1], self.bbox_x_width,
                            self.bbox_y_width)}
        self.polygons['bboxes'] = self.bboxes

        for side in self.pin_sides_dict.keys():
            orientation = 'horizontal' if side == 'left' or side == 'right' else 'vertical'
            self.place_pins(self.pin_place_start_corners[side], self.pin_sides_dict[side], orientation)


class BBoxLEFBuilder(LEFBuilder):

    def __init__(self, phy_design, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.make_lef_dict(phy_design)

    def make_lef_dict(self, phy_design: PHYDesign):
        pg_pins = phy_design.pg_pins
        pins = phy_design.pins
        bbox = phy_design.bboxes
        name = phy_design.name
        class_line = "CLASS CORE"
        header_lines = self.add_lef_header(version=5.6)
        origin_line = f"ORIGIN {phy_design.specs['origin'][0]} {phy_design.specs['origin'][1]}"
        size_line = f"SIZE {phy_design.x_width} BY {phy_design.y_width}"
        sym_line = f"SYMMETRY {phy_design.specs['symmetry']}"
        site_line = f"SITE {phy_design.specs['site']}"

        self.lines += header_lines
        self.lines += '\n'

        # Macro lines
        macro_lines = [class_line, origin_line, size_line, sym_line, site_line]

        macro_block = self.add_block('MACRO', phy_design.name, lines=macro_lines)
        for pin_name, pin in pg_pins.items():
            macro_block.add_pgpin(pin_name, pin)
        for pin_name, pin in pins.items():
            macro_block.add_pin(pin_name, pin)
        for bbox in bbox.values():
            macro_block.add_bbox_obs(bbox.phys_map)